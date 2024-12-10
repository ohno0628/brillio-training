# AWS CLI Commands

## AWS CLI 概要
- AWS CLI を使用して各サービスを操作するための便利なコマンド集。
- **目的**: 運用効率化、トラブルシューティングの迅速化。

## 出力形式を指定
AWS CLIの出力形式はConfig設定時に指定した形式で出力される。
`--output`により明示的に出力形式を指定することが可能

- `json` 
- `table` 
- `text` 


## CloudWatch
<details>
<summary>クリックして展開</summary>
### 基本構文
```
aws logs [COMMAND] --[OPTION] <VALUE>
```

- `COMMAND`: 実行するサブコマンド（例: describe-log-groups, get-log-events）
- `OPTION`: コマンドのオプション（例: -log-group-name-prefix）
- `VALUE`: 指定する値

### CloudWatchログをフィルタして確認
特定の文字列を含むログを検索
```
aws logs filter-log-events --log-group-name <LogGroupName> --filter-pattern "ERROR"
```

### ロググループをリアルタイム表示
新しいログをリアルタイム表示

```
aws logs tail --follow --filter 'ERROR' --format short  <LogGroupName> 
```

### 対象のロググループ/ストリーム検索

ロググループを検索
```
aws logs describe-log-groups --query "logGroups[*].logGroupName" --output table
```

ログストリームを検索

最新のログストリームを取得
```
aws logs describe-log-streams --log-group-name <LogGroupName> order-by LastEventTime --descending --limit 10
```

ストリーム名に特定パターンが含まれる場合のフィルタリング
```
aws logs describe-log-streams --log-group-name <LogGroupName> --query "logStreams[?contains(logStreamName, '<フィルタ文字列>')].[logStreamName]"
```
</details>

## S3
<details>
<summary>クリックして展開</summary>
### 基本構文
```
aws s3 [COMMAND] [OPTIONS]
```
- `COMMAND`: 実行するサブコマンド（例: ls,cp,mv）
- `OPTIONS`: オプション（例: --recursive, --exclude）

　
### S3バケット確認
S3バケット一覧表示
```
aws s3 ls
```

対象バケット一覧表示
```
aws s3 ls s3://<バケット名>/
```

再帰的にgrep条件でオブジェクトを抽出
```
aws s3 ls s3://<バケット名>/ --recursive | grep "\.tsv"
```
日付による降順ソート
```
aws s3 ls s3://<バケット名>/ --recursive |sort -k1,2 -r| tail -n 10
```

### S3オブジェクトのコピー

S3およびローカル間でのコピー
```
aws s3 cp [コピー元(localパス/S3 URI)] [コピー先(localパス/S3 URI)]
```

パスに`-`を指定することで標準出力
```
aws s3 cp s3://<バケット名>/<オブジェクト> -
```

Zip化されているログ（trailやCFのログ）等ダウンロードすることなく確認可能
```
aws s3 cp s3://<バケット名>/<オブジェクト>.gz - | zless
aws s3 cp s3://<バケット名>/<オブジェクト>.gz - | gunzip | grep "文字列"
```

### S3オブジェクトの削除
単一オブジェクトの削除
```
aws s3 rm s3://<バケット名>/<オブジェクト>
```

ディレクトリごと削除
```
aws s3 rm s3://<バケット名>/<オブジェクト>/ --recursive
```

ディレクトリごと削除
```
aws s3 rm s3://<バケット名>/<オブジェクト>/ --recursive
```
特定ファイル名のみ削除
```
aws s3 rm s3://<バケット名>/<オブジェクト>/ --exclude "*" --include "*.tsv" --recursive
```
**詳細**
- `--exclde "*"`:すべてのファイルを削除対象から除外
- `--include "*.tsv"`:指定の拡張子のみを削除対象に含める

※bashに渡して`grep`,`awk`等を使ってローカル処理も可能だが、大量データを扱う場合
AWS CLI使うほうが効率的
</details>


## IAM
<details>
<summary>クリックして展開</summary>
IAMロールにアタッチされているポリシー一覧を表示

```
aws iam list-attached-role-policies --role-name RoleName
```
</details>

## Lambda
<details>
<summary>クリックして展開</summary>
Lambda関数をローカルにダウンロード

```
aws lambda get-function --function-name LambdaFunctionName --query 'Code.Location' --output text | wget -O lambda_function.zip -

```

Lambda関数に設定している環境変数を表示
```
aws lambda get-function-configuration --function-name YourLambdaFunctionName --query 'Environment.Variables'
```
</details>


## その他
AWS CLIの設定確認

CLIコマンドのデバッグ情報を表示

利用中のAWSリージョンを表示