import json
import os
import base64
import logging
import urllib3

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from urllib3 import Retry, Timeout


logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 環境名（dev, staging, prod など）を環境変数から取得　secresmanager のシークレット名に利用するなど
APP_ENV = os.getenv("APP_ENV", "dev")


# ==== HTTP クライアント（Jira呼び出し用）====
http = urllib3.PoolManager(
    retries=Retry(
        total=3,
        backoff_factor=0.5,                     # 0.5s, 1s, 2s... の間隔でリトライ
        status_forcelist=[500, 502, 503, 504],  # サーバーエラー時にリトライ
        ),
    timeout=Timeout(connect=3.0, read=8.0)      # タイムアウト設定（接続3秒、読み取り8秒）
)

# ==== Secrets Manager 設定 ====
# 環境変数から Secret 名を取得（なければデフォルト）
JIRA_SECRET_NAME = os.getenv("JIRA_SECRET_NAME", "jira/poc")

_secrets_client = boto3.client("secretsmanager")
_secret_cache = None  # 一度取得した secret をLambdaコンテナ内でキャッシュ

# ===== 必須シークレットキー一覧 =====
REQUIRED_SECRET_KEYS = [
    "JIRA_BASE_URL",
    "JIRA_EMAIL",
    "JIRA_API_TOKEN",
    "JIRA_PROJECT_KEY",
]


# incident = {
#     "source": "cloudwatch_alarm" or "stepfunctions",
#     "alarm_name": ...,
#     "new_state": ...,
#     "reason": ...,
#     "region": ...,
#     "namespace": ...,
#     "metric_name": ...,
#     "lambda_name": ...,
#     "timestamp": ...,
#     "raw_message": message,  # 元のJSONそのまま
# }


# ========= 1. ロガー / HTTP / Secrets =========

def _load_jira_secret() -> dict:
    """
    Secrets Manager から Jira 設定を取得し、プロセス内でキャッシュする。
    期待する Secret の JSON 例:

    {
      "JIRA_BASE_URL": "https://xxx.atlassian.net",
      "JIRA_EMAIL": "user@example.com",
      "JIRA_API_TOKEN": "xxxx...",
      "JIRA_PROJECT_KEY": "TEST",
      "JIRA_ISSUE_TYPE": "Incident"          # name 指定版
      // or "JIRA_ISSUE_TYPE_ID": "10001"    # id 指定版
    }
    """
    global _secret_cache
    if _secret_cache is not None:
        return _secret_cache

    try:
        res = _secrets_client.get_secret_value(SecretId=JIRA_SECRET_NAME)
        secret_str = res.get("SecretString", "{}")
        secret = json.loads(secret_str)

    except (BotoCoreError, ClientError) as e:
        logger.error(f"Failed to load secret {JIRA_SECRET_NAME}: {e}")
        raise RuntimeError(f"Could not retrieve secret {JIRA_SECRET_NAME}") from e

    # 必須キーが揃っているかチェック
    missing_keys = [key for key in REQUIRED_SECRET_KEYS if key not in secret]
    if missing_keys:
        logger.error(f"Missing required keys in secret {JIRA_SECRET_NAME}: {missing_keys}")
        raise RuntimeError(f"Missing required keys in secret {JIRA_SECRET_NAME}: {missing_keys}")

    # キャッシュして返す
    _secret_cache = secret
    logger.info(f"Loaded Jira config from Secrets Manager: {JIRA_SECRET_NAME}")
    return _secret_cache


def _jira_auth_header(secret: dict) -> dict:
    """
    Jira 用の Basic 認証ヘッダを作成
    """
    token = f"{secret['JIRA_EMAIL']}:{secret['JIRA_API_TOKEN']}"
    b64 = base64.b64encode(token.encode("utf-8")).decode("utf-8")
    return {
        "Authorization": f"Basic {b64}",
        "Content-Type": "application/json",
    }


# ===== 既存チケット検索（重複起票防止） =====
def _find_existing_issue_by_summary(secret: dict, summary: str) -> str | None:
    """
    指定した summary を持つ未解決の Jira Issue が存在するか検索し、
    存在すれば Issue Key を返す。なければ None を返す。
    """
    base_url = secret["JIRA_BASE_URL"].rstrip("/")
    project_key = secret["JIRA_PROJECT_KEY"]

    # statusCategory != Done で未解決チケットを絞り込む
    jql = (
        f'project = "{project_key}" '
        f' AND summary ~ "{summary}" '
        f'AND statusCategory != Done '
        f' ORDER BY created DESC'
    )

    url = f"{base_url}/rest/api/3/search/jql"
    payload = {
        "jql": jql,
        "maxResults": 1,
        "fields": ["key"],
    }


    headers = _jira_auth_header(secret)
    encoded_body = json.dumps(payload).encode("utf-8")

    logger.info("Searching existing Jira issue with JQL: %s", jql)
    resp = http.request("POST", url, headers=headers, body=encoded_body)

    if resp.status >= 300:
        # 重複チェックに失敗しても「起票自体は試みる」ため、ここで例外を投げるのではなくログだけのこしてNoneを返す
        try:
            body_str = resp.data.decode("utf-8")
        except Exception:
            body_str = str(resp.data)
        logger.error("Failed to search Jira issues: %s %s", resp.status, body_str)
        raise Exception(f"Jira API error: {resp.status}")

    data = json.loads(resp.data.decode("utf-8"))
    issues = data.get("issues", [])
    if not issues:
        return None

    return issues[0].get("key")


# ===== 既存チケットへのコメント用 ADF =====
def _build_comment_adf(
    summary: str,
    new_state: str,
    reason: str,
    timestamp: str,
    namespace: str,
    metric_name: str,
    region: str,
    lambda_name: str,
) -> dict:
    """
    Jira Cloud が期待する ADF(Atlassian Document Format) に変換。
    シンプルに「プレーンテキスト1段落」として送る。
    発報タイミング、State、Reason を含むコメントを作成
    """
    text_lines = [
        "*Alarm Fired Again*",
        f"- State: {new_state}",
        f"- Time: {timestamp}",
        f"- Lambda: {lambda_name or 'N/A'}",
        f"- Metric: {namespace} / {metric_name}",
        f"- Region: {region}",
        f"- Reason: {reason}",
        "",
        "This alarm was triggered again and appended by AWS Lambda.",
    ]

    # text = f"CloudWatch alarm '{summary}' fired again. Appended by AWS Lambda."
    # return {
    #     "type": "doc",
    #     "version": 1,
    #     "content": [
    #         {
    #             "type": "paragraph",
    #             "content": [{"type": "text", "text": text}],
    #         }
    #     ],
    # }
    # ADF の paragraph ノードに変換
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": line + "\n"} for line in text_lines]
            }
        ]
    }

#===== 既存チケットへのコメント追加 =====
def _add_comment_to_issue(secret: dict, issue_key: str, summary: str, new_state: str,
                          reason: str, timestamp: str, namespace: str, metric_name: str,
                          region: str, lambda_name: str) -> None:
    """
    既存の Jira 課題(issue_key)にコメントを1件追加する。
    """
    base_url = secret["JIRA_BASE_URL"].rstrip("/")
    url = f"{base_url}/rest/api/3/issue/{issue_key}/comment"

    body = {
        "body": _build_comment_adf(
            summary, new_state, reason, timestamp,
            namespace, metric_name, region, lambda_name
        )
    }

    headers = _jira_auth_header(secret)
    encoded_body = json.dumps(body).encode("utf-8")

    logger.info("Adding comment to existing issue %s", issue_key)
    resp = http.request("POST", url, body=encoded_body, headers=headers)

    if resp.status >= 300:
        try:
            body_str = resp.data.decode("utf-8")
        except Exception:
            body_str = str(resp.data)
        logger.error("Failed to add comment to issue %s: %s %s", issue_key, resp.status, body_str)
        # コメント失敗しても致命的ではないので、raise はせずログだけ残す
        return

    logger.info("Comment added to issue %s", issue_key)




# def _to_adf(text: str) -> dict:
#     """
#     Jira Cloud が期待する ADF(Atlassian Document Format) に変換。
#     シンプルに「プレーンテキスト1段落」として送る。
#     """
#     return {
#         "type": "doc",
#         "version": 1,
#         "content": [
#             {
#                 "type": "paragraph",
#                 "content": [{"type": "text", "text": text}],
#             }
#         ],
#     }



# ========= 2. 共通インシデント変換レイヤー =========

# ===== CloudWatch アラームインシデント変換レイヤー =====
def _build_incident_from_cloudwatch(message: dict, sns: dict) -> dict:
    """
    CloudWatch アラームの SNS メッセージから共通インシデント情報を組み立てる
    """
    alarm_name = message.get("AlarmName", "UnknownAlarm")
    new_state = message.get("NewStateValue", "UNKNOWN")
    reason = message.get("NewStateReason", "")
    region = message.get("Region", "unknown")
    trigger = message.get("Trigger", {})

    metric_name = trigger.get("MetricName", "Errors")
    namespace = trigger.get("Namespace", "AWS/Lambda")
    dimensions = trigger.get("Dimensions", [])

    lambda_name = None
    for d in dimensions:
        if d.get("name") == "FunctionName":
            lambda_name = d.get("value")

    timestamp = message.get("StateChangeTime") or sns.get("Timestamp", "")

    return {
        "source": "cloudwatch_alarm",
        "alarm_name": alarm_name,
        "new_state": new_state,
        "reason": reason,
        "region": region,
        "namespace": namespace,
        "metric_name": metric_name,
        "lambda_name": lambda_name,
        "timestamp": timestamp,
        "raw_message": message,
    }    

# ===== Step Functions インシデント変換レイヤー =====
def _build_incident_from_stepfunctions(message: dict, sns: dict) -> dict:
    """
    Step Functions の Execution Status Change イベントから共通インシデント情報を組み立てる。
    """
    detail = message.get("detail", {})

    # 代表的なフィールド
    state_machine_name = detail.get("name", "UnknownStateMachine")
    status = detail.get("status", "UNKNOWN")  # FAILED / RUNNING / SUCCEEDED ...
    error = detail.get("error") or detail.get("cause", "")

    region = message.get("region", "unknown")
    timestamp = message.get("time", "") or sns.get("Timestamp", "")

    # CloudWatch用のフィールドに寄せる
    alarm_name = state_machine_name
    new_state = status
    reason = error
    namespace = "AWS/States"
    metric_name = "ExecutionFailed" if status == "FAILED" else "ExecutionStatus"
    lambda_name = None  # ここはステートマシンなので空

    return {
        "source": "stepfunctions",
        "alarm_name": alarm_name,
        "new_state": new_state,
        "reason": reason,
        "region": region,
        "namespace": namespace,
        "metric_name": metric_name,
        "lambda_name": lambda_name,
        "timestamp": timestamp,
        "raw_message": message,
    }


def _build_incident(message: dict, sns: dict) -> dict:
    """
    SNS メッセージの中身から「どの種別のイベントか」を判定し、
    共通インシデント情報(dict)に変換する。
    将来的に ECS / Batch 等の種別を増やす場合はここに分岐を足す。
    """
    # CloudWatch Alarm 判定：AlarmName/NewStateValue があればほぼ確実にこれ
    if "AlarmName" in message and "NewStateValue" in message:
        return _build_incident_from_cloudwatch(message, sns)

    # Step Functions 判定：source/detail-type で判定
    source = message.get("source", "")
    detail_type = message.get("detail-type", "")

    if source == "aws.states" or "Step Functions Execution Status Change" in detail_type:
        return _build_incident_from_stepfunctions(message, sns)

    # どれにも当てはまらなかった場合は汎用的な形で入れておく（必要に応じて拡張）
    logger.warning("Unknown event type. Treat as generic incident. message=%s", message)

    region = message.get("region", "unknown")
    timestamp = message.get("time", "") or sns.get("Timestamp", "")

    return {
        "source": "unknown",
        "alarm_name": message.get("detail-type", "UnknownEvent"),
        "new_state": message.get("detail", {}).get("status", "UNKNOWN"),
        "reason": "",
        "region": region,
        "namespace": "Generic",
        "metric_name": "GenericEvent",
        "lambda_name": None,
        "timestamp": timestamp,
        "raw_message": message,
    }




# ===== Jira チケット本文（Description）用 ADF =====
def build_adf_description(
        alarm_name, new_state, reason, region,
        namespace, metric_name, lambda_name, message
) -> dict:
    """
    Jiraのdescriptionフィールド用にADF形式で組み立てる
    - Alarm Info
    - Metric Info
    - 生のSNSメッセージ（JSON）をコードブロックで格納
    """
    return {
        "type": "doc",
        "version": 1,
        "content": [
            
            # === Alarm Info ===
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Alarm Info"}]
            },
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": f"Name: {alarm_name}"}]
                            }
                        ]
                    },
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": f"State: {new_state}"}]
                            }
                        ]
                    },
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": f"Reason: {reason}"}]
                            }
                        ]
                    },
                ]
            },
            # === Metric Info ===
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Metric Info"}]
            },
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": f"Namespace: {namespace}"}]
                            }
                        ]
                    },
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": f"Metric: {metric_name}"}]
                            }
                        ]
                    },
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": f"Region: {region}"}]
                            }
                        ]
                    },
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": f"Lambda: {lambda_name or 'N/A'}"}]
                            }
                        ]
                    },
                ]
            },
            # === Raw SNS Message === 見にくいので必要な部分のみ抜粋するように変更も検討
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Raw SNS Message"}]
            },
            {
                "type": "codeBlock",
                "attrs": {"language": "json"},
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(message, indent=2, ensure_ascii=False)
                    }
                ]
            },

        ],
    }

# def _build_description_text(alarm_name, new_state, reason, region, namespace, metric_name, lambda_name, message):

#     parts = [
#         "*Alarm Info*",
#         f" - Name: {alarm_name}",
#         f" - State: {new_state}",
#         f" - Reason: {reason}",
#         "",
#         "*Metric Info*",
#         f" - Namespace: {namespace}",
#         f" - Metric: {metric_name}",
#         f" - Region: {region}",
#         f" - Lambda: {lambda_name or 'N/A'}",
#         "",
#         "*Raw SNS Message*",
#         "```json",
#         json.dumps(message, indent=2, ensure_ascii=False),
#         "```",
#         "",
#         "----",
#         "This issue was automatically created by AWS Lambda (CloudWatch Alarm → SNS → Lambda → Jira).",
#     ]
#     return "\n".join(parts)


# ===== 優先度決定ロジック =====
def _decide_priority(
    alarm_name: str,
    metric_name: str,
    reason: str | None = None,
    namespace: str | None = None,
    # new_state: str | None = None,
) -> dict:
    """
    アラーム名/メトリクス名/理由などのテキストに含まれるキーワードから
    Jiraの優先度をざっくり決定する。
    - CloudWatch Alarm / Step Functions などの種別は見ない
    実運用では適宜、キーワードは調整する。
    """
    text_blob = " ".join(
        s for s in[
            alarm_name or "",
            metric_name or "",
            reason or "",
            namespace or "",
            # new_state or "",
        ]
        if s
    ).lower()

    high_keywords  =  [
        "critical", "prod", "5xx",
        "production", "billing", "database",
        "failed", # 検証用に追加
    ]

    medium_keywords  = [
        "staging", "beta", "retry",
        "warning", "latency", "throttle"
    ]


    # 重要度に応じてpriorityフィールドを追加する
    # alarm_lower = (alarm_name or "").lower()
    # metric_lower = (metric_name or "").lower()

    # high_keywords_in_alarm =  ["critical", "prod", "5xx"]
    # high_keywords_in_metric =  ["errors", "5xx_error_rate"] #一時的に""errors"を追加


    if any(k in text_blob for k in high_keywords):
        return {"name": "High"}

    if any(k in text_blob for k in medium_keywords):
        return {"name": "Medium"}

    # どれにもマッチしなければデフォルトは Medium
    return {"name": "Medium"}

# ===== Jira Issue 作成 or コメント追記のメイン関数 =====
def _create_jira_issue(
    summary: str,
    description_adf: dict,
    metric_name: str,
    alarm_name: str,
    new_state: str,
    reason: str,
    timestamp: str,
    namespace: str,
    region: str,
    lambda_name: str,
) -> str:
    """
    Jira にインシデントチケットを1件作成し、Issue Key を返す。
    - 同じ summary を持つ未解決チケットが既に存在する場合は新規作成せず、コメントを追加してその Issue Key を返す。
    - 存在しない場合：
        - 新規チケットを作成し、その Issue Key を返す。
    """
    secret = _load_jira_secret()

    # logger.info("Secret JIRA_PROJECT_KEY raw: %r", secret.get("JIRA_PROJECT_KEY"))
    # logger.info("Secret content keys: %s", list(secret.keys()))

    # 1. 既存の未解決チケットを検索
    existing_issue_key = _find_existing_issue_by_summary(secret, summary)
    if existing_issue_key:
        logger.info("Skipping creating new issue. Use existing issue: %s", existing_issue_key)
        _add_comment_to_issue(secret, existing_issue_key, summary, 
                            new_state, reason,
                            timestamp, namespace,
                            metric_name, region,
                            lambda_name)
        return existing_issue_key

    # 2. 重複なければ新規チケット作成
    base_url = secret["JIRA_BASE_URL"].rstrip("/")
    project_key = secret["JIRA_PROJECT_KEY"]

    # issue type は id / name どちらでも対応できるようにする
    if "JIRA_ISSUE_TYPE_ID" in secret:
        issuetype = {"id": secret["JIRA_ISSUE_TYPE_ID"]}
    else:
        issuetype_name = secret.get("JIRA_ISSUE_TYPE", "Incident")
        issuetype = {"name": issuetype_name}
    
    labels = [
        "cloudwatch-auto",
        f"env-{APP_ENV}",
    ]

    url = f"{base_url}/rest/api/3/issue"
    

    priority = _decide_priority(
    alarm_name=alarm_name,
    metric_name=metric_name,
    reason=reason,
    namespace=namespace,
)

    fields = {
        "project": {"key": project_key},
        "summary": summary,
        "issuetype": issuetype,
        "labels": labels,
        "description": description_adf,
        }
    
    if priority:
        fields["priority"] = priority
    
    body = {"fields": fields}


    # logger.info("Jira request payload: %s", json.dumps(body, ensure_ascii=False))

    headers = _jira_auth_header(secret)
    encoded_body = json.dumps(body).encode("utf-8")

    logger.info("Creating Jira issue at %s with summary=%s", url, summary)
    resp = http.request("POST", url, body=encoded_body, headers=headers)

    if resp.status >= 300:
        # 失敗時はレスポンスボディもログに出す
        try:
            body_str = resp.data.decode("utf-8")
        except Exception:
            body_str = str(resp.data)
        logger.error("Failed to create Jira issue: %s %s", resp.status, body_str)
        raise Exception(f"Jira API error: {resp.status}")

    data = json.loads(resp.data.decode("utf-8"))
    key = data.get("key")
    logger.info("Created Jira issue: %s", key)
    return key


# ===== Lambda ハンドラー =====
def lambda_handler(event, context):
    """
    エントリポイント
    SNS → CloudWatchアラームのメッセージを受け取り、
    Jiraにインシデントチケットを作成 or コメントを追記する。
    """
    logger.info("Received event: %s", json.dumps(event))

    # SNSは Records[].Sns.Message に文字列JSONを載せてくる
    for record in event.get("Records", []):
        sns = record.get("Sns", {})
        message_str = sns.get("Message", "{}")
        message = json.loads(message_str)

        # 1. 共通インシデント情報に変換
        incident = _build_incident(message, sns)

        # logger.info("=== Raw SNS Message ===\n%s\n====================", message_str)

        # 2. インシデントから Jira 用の summary / description を組み立て
        alarm_name = incident["alarm_name"]
        new_state = incident["new_state"]
        reason = incident["reason"]
        region = incident["region"]
        namespace = incident["namespace"]
        metric_name = incident["metric_name"]
        lambda_name = incident["lambda_name"]
        timestamp = incident["timestamp"]
        raw_message = incident["raw_message"]

        # source 種別に応じて summary を少し変えたい場合はここで分岐
        if incident["source"] == "stepfunctions":
            summary = f"[StepFunctions] {alarm_name} status is {new_state}"
        else:
            # デフォルトは CloudWatch 風 summary
            summary = f"[CloudWatch Alarm] {alarm_name} is {new_state}"

        description_adf = build_adf_description(
            alarm_name,
            new_state,
            reason,
            region,
            namespace,
            metric_name,
            lambda_name,
            raw_message,
        )

        # 3. 既存チケットの重複チェック → コメント追記 or 新規作成
        _create_jira_issue(
            summary,
            description_adf,
            metric_name,
            alarm_name,
            new_state,
            reason,
            timestamp,
            namespace,
            region,
            lambda_name,
        )

    return {"status": "ok"}