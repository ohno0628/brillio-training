# AWS SAM を用いた予約システム構築手順まとめ

本ドキュメントでは、AWS SAMを活用してDynamoDBをバックエンドとしたシンプルな予約システムを構築・テストし、本番環境へデプロイ。
デプロイしたAPI Gateway + Lambda + DynamoDBで構成されています。  
フロントエンド(HTML,CSS,JS)はS3静的ウェブサイトホスティングを用いて公開します。

**あくまでAWSサービスを使った構築イメージをつかむための手順でセキュリティフル無視なので作成後は必ず削除する。非公開とすること！！**

## 前提条件

- AWS CLI、SAM CLIがインストール済みであること
- AWSアカウントと適切なIAM権限があること
- Python 3.9 ランタイムに対応したローカル開発環境があること
- （ローカルテスト用に）Docker環境が整っていること

## AWS環境構成図

![alt text](./images/reservation-system-AWS.jpg "構成図")


## SAMプロジェクト構成
```
reservation-system/
├── README.md (本ドキュメント)
├── src/
│   ├─ create_reservation.py
│   ├─ get_reservation.py
│   ├─ update_reservation.py
│   ├─ delete_reservation.py
│   ├─ list_reservations.py
├
├── template.yaml
├
├─ env.json
```

## 画面イメージ
デプロイ後のWeb画面イメージ

![alt text](./images/Screen_Image.jpg "Web画面")


`template.yaml`では以下を定義します。  
- DynamoDBテーブル `ReservationsTable`
- `CreateReservationFunction`, `GetReservationFunction`, `UpdateReservationFunction`, `DeleteReservationFunction`, `ListReservationsFunction` の5つのLambda関数
- 各FunctionをトリガーするAPI Gateway (パス: `/reservations`など)
- `TABLE_NAME` 環境変数をLambda関数から参照可能にする設定

## SAMプロジェクトのビルド

**SAMプロジェクトの初期化（初回のみ）**

対話的なプロンプトに従い、`template.yaml`等が作成される。

```
sam init
```

ソースコード・テンプレートが準備できたら以下を実行します。

```
sam build
```

これで`template.yaml`に基づき、Lambda用のパッケージが`.aws-sam/build`配下に生成されます。

## ローカルでのテスト (オプション)
### ローカルDynamoDBの準備

1. DynamoDB Local起動

```
docker run -p 8000:8000 amazon/dynamodb-local
```

2. テーブル作成
```
aws dynamodb create-table \
    --table-name ReservationsTable \
    --attribute-definitions AttributeName=reservationId,AttributeType=S \
    --key-schema AttributeName=reservationId,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --endpoint-url http://localhost:8000 \
    --region ap-northeast-1
```
`env.json`などで`TABLE_NAME`を設定して、ローカルで`sam local start-api`実行時にLambdaへ環境変数を渡す。


### SAMローカル起動
```
sam local start-api --env-vars env.json
```

- `http://127.0.0.1:3000`でAPIが起動
- curlコマンドでPOST /reservationsなどを実行し、ローカル環境での動作を確認
  ```
  curlの実行例を記載
  ```

### 本番用へのコード修正とデプロイ
ローカルで確認後、本番環境用に以下を修正

- `endpoint_url`や`aws_access_key_id/aws_secret_access_key`の削除（デフォルト設定に戻す）
- `dynamodb = boto3.resource('dynamodb')` のみでアクセス可能な状態
- 認証なし公開で良いかといったデプロイ時の質問に対応できるようにする

1. 再ビルド
```
sam build
```

2. デプロイ
```
sam deploy --guided --region ap-northeast-1

実行時に対話プロンプト内容(下記はあくまで学習用の環境での参考)
Stack Name [reservation-system]:例: `reservation-system`
AWS Region [ap-northeast-1]:空欄のままENTER
Confirm changes before deploy [Y/n]:y
Allow SAM CLI IAM role creation [Y/n]:y
Disable rollback [y/N]:n
CreateReservationFunction has no authentication. Is this okay? [y/N]:y
GetReservationFunction has no authentication. Is this okay? [y/N]: y　←　FuncitionCodeの数だけ聞かれる
Save arguments to configuration file [Y/n]:y
SAM configuration file [samconfig.toml]:空欄のままENTER
SAM configuration environment [default]:空欄のままENTER
Deploy this changeset? [y/N]:y
```


```
ログに表示されるOutputsの以下項目がアクセスURLとなる。
Outputs                                                                            -----------------------------------------------------------------------------------
Key                 ApiUrl                                                                                                                                                                
Description         API endpoint URL                                                                                                                                                      
Value               https://<XXXXXXXX>.ap-northeast-1.amazonaws.com/Prod/reservations                                                                       -----------------------------------------------------------------------------------
```

### 本番環境での動作確認 (curl)

**予約作成 (POST)**
```
curl -X POST -H "Content-Type: application/json" \
  -d '{"resourceName":"一番館","time":"2024-12-11T10:00"}' \
  https://<XXXXXXXX>.ap-northeast-1.amazonaws.com/Prod/reservations
```

**予約取得 (GET)**
```
curl https://<XXXXXXXX>.ap-northeast-1.amazonaws.com/Prod/reservations/ <reservationId>
```

**予約更新 (PUT)**
```
curl -X PUT -H "Content-Type: application/json" \
  -d '{"resourceName":"弐番館,"time":"2024-12-12T10:00"}' \
  https://<XXXXXXXX>.ap-northeast-1.amazonaws.com/Prod/reservations/<reservationId>
```

**予約削除 (DELETE)**
```
curl -X DELETE \
  https://<XXXXXXXX>.ap-northeast-1.amazonaws.com/Prod/reservations/<reservationId>
```

**一覧取得 (GET)**
```
curl https://<XXXXXXXX>.ap-northeast-1.amazonaws.com/Prod/reservations
```

### 静的サイトホスティング

#### 手順概要
1. **S3バケット作成**
2. **バケットポリシーでパブリックアクセスを許可** (本来CloudFront経由であるべきは触れないこと)
3. **静的ウェブサイトホスティング有効化**  
4. **HTML/CSS/JSファイルをアップロード**
5. **S3ウェブサイトエンドポイントURLでブラウザからアクセス可能**


#### 詳細手順
1. S3バケット作成
```
ユニークである必要があるため適宜名前は変更すること

aws s3 mb s3://my-reservation-frontend
```
2. パブリックアクセス許可設定
- S3コンソールでmy-reservation-frontendバケットを開く
- Permissionsタブ → Public access settings(ブロックパブリックアクセス)をオフ

  セキュリティがばポイント

- バケットポリシーで`GetObject`許可を追加 (以下は例):
```
json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-reservation-frontend/*"
    }
  ]
}

```

3. フロントエンドファイルのアップロード
`frontend/`配下の`index.html`,`style.css`,`app.js`をS3にアップロード

```
aws s3 sync frontend/ s3://my-reservation-frontend/
```

4. 静的ウェブサイトホスティング有効化
- S3コンソールでmy-reservation-frontendバケットを開く
- 「プロパティ」タブの静的ウェブサイトホスティングから編集から以下を設定
   - 静的ウェブサイトホスティングを有効にする。
   - インデックスドキュメントに`index.html`を指定
- エンドポイントURLが表示されるため、そこからWebアクセス可能となる。
画面が表示されればGoal


#### ポイント
- CROS設定について

  フロントエンド（S3）とバックエンド（APIゲートウェイ）は異なるオリジンを持つためCROS設定が必要 `template.yaml`の`AllowOrigin: "'*'"`が該当箇所にあたる
  ```
    MyReservationApi:
    Type: AWS::Serverless::Api
    Properties:
      Name: MyReservationApi
      StageName: Prod
      Cors:
        AllowMethods: "'GET,POST,PUT,DELETE,OPTIONS'"
        AllowHeaders: "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
        AllowOrigin: "'*'"
        AllowCredentials: "'false'"
  ```
[オリジン（Origin）とCORSの関係を学ぶ](https://zenn.dev/reds/articles/7b6c0c2ec4599a)

- 本番運用の場合
  
  - 通常、パブリックに直接S3エンドポイントを公開せず、CloudFrontを前段に置きHTTPS対応を行うことが一般的
  - 現状、誰でも入れる状態となるため、認証の機構を入れる。
  - バケットポリシーをやCROS設定を`'*'`にせず最小限とすることでセキュリティリスクを軽減

### トラブルシューティング
詰まるポイントはローカルテスト部分ぐらい
XXXXXXXX

### まとめ
XXXXXXXX


残タスク
前提となる環境構築手順は別途準備
