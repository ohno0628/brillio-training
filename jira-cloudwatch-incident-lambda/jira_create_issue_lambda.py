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

APP_ENV = os.getenv("APP_ENV", "dev")

http = urllib3.PoolManager(
    retries=Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
        ),
    timeout=Timeout(connect=3.0, read=8.0) 
)

# ==== Secrets Manager 設定 ====
# 環境変数から Secret 名を取得（なければデフォルト）
JIRA_SECRET_NAME = os.getenv("JIRA_SECRET_NAME", "jira/poc")

_secrets_client = boto3.client("secretsmanager")
_secret_cache = None  # 一度取得した secret をプロセス内でキャッシュ


REQUIRED_SECRET_KEYS = [
    "JIRA_BASE_URL",
    "JIRA_EMAIL",
    "JIRA_API_TOKEN",
    "JIRA_PROJECT_KEY",
]

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

def build_adf_description(
        alarm_name, new_state, reason, region,
        namespace, metric_name, lambda_name, message
):
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
            # === Raw SNS Message ===
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

def _build_description_text(alarm_name, new_state, reason, region, namespace, metric_name, lambda_name, message):

    parts = [
        "*Alarm Info*",
        f" - Name: {alarm_name}",
        f" - State: {new_state}",
        f" - Reason: {reason}",
        "",
        "*Metric Info*",
        f" - Namespace: {namespace}",
        f" - Metric: {metric_name}",
        f" - Region: {region}",
        f" - Lambda: {lambda_name or 'N/A'}",
        "",
        "*Raw SNS Message*",
        "```json",
        json.dumps(message, indent=2, ensure_ascii=False),
        "```",
        "",
        "----",
        "This issue was automatically created by AWS Lambda (CloudWatch Alarm → SNS → Lambda → Jira).",
    ]
    return "\n".join(parts)


# 重要度に応じてpriorityフィールドを追加するなどの拡張
def _decide_priority(alarm_name: str, metric_name: str) -> dict:
    # すべて小文字にしてから判定
    alarm_lower = (alarm_name or "").lower()
    metric_lower = (metric_name or "").lower()

    high_keywords_in_alarm =  ["critical", "prod", "5xx"]
    high_keywords_in_metric =  ["errors", "5xx_error_rate"] #一時的に""errors"を追加


    if any(k in alarm_lower for k in high_keywords_in_alarm):
        return {"name": "High"}

    if any(k in metric_lower for k in high_keywords_in_metric):
        return {"name": "High"}

    return {"name": "Medium"}


def _create_jira_issue(summary: str, description_adf: dict, metric_name: str) -> str:
    """
    Jira にインシデントチケットを1件作成し、Issue Key を返す。
    """
    secret = _load_jira_secret()

    # logger.info("Secret JIRA_PROJECT_KEY raw: %r", secret.get("JIRA_PROJECT_KEY"))
    # logger.info("Secret content keys: %s", list(secret.keys()))

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

    priority = _decide_priority(summary, metric_name)

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


def lambda_handler(event, context):
    """
    SNS → CloudWatchアラームのメッセージを受け取り、
    Jiraにインシデントチケットを作成するLambda。
    """
    logger.info("Received event: %s", json.dumps(event))

    # SNSは Records[].Sns.Message に文字列JSONを載せてくる
    for record in event.get("Records", []):
        sns = record.get("Sns", {})
        message_str = sns.get("Message", "{}")
        message = json.loads(message_str)

        # logger.info("=== Raw SNS Message ===\n%s\n====================", message_str)

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

        # Jiraの summary と description を組み立て
        summary = f"[CloudWatch Alarm] {alarm_name} is {new_state}"
        description_adf = build_adf_description(
            alarm_name, new_state, reason, region, namespace, metric_name, lambda_name, message
        )
        _create_jira_issue(summary, description_adf, metric_name)

    return {"status": "ok"}
