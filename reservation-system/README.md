# AWS SAM を用いた予約システム構築手順まとめ

本ドキュメントでは、AWS SAMを活用してDynamoDBをバックエンドとしたシンプルな予約システムを構築・テストし、本番環境へデプロイして`curl`での動作確認を行うまでの流れをまとめています。

## 前提条件

- AWS CLI、SAM CLIがインストール済みであること
- AWSアカウントと適切なIAM権限があること
- Python 3.9 ランタイムに対応したローカル開発環境があること
- （ローカルテスト用に）Docker環境が整っていること

## プロジェクト構成（例）


```plaintext
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

`template.yaml`では以下を定義します。  
- DynamoDBテーブル `ReservationsTable`
- `CreateReservationFunction`, `GetReservationFunction`, `UpdateReservationFunction`, `DeleteReservationFunction`, `ListReservationsFunction` の5つのLambda関数
- 各FunctionをトリガーするAPI Gateway (パス: `/reservations`など)
- `TABLE_NAME` 環境変数をLambda関数から参照可能にする設定

## SAMプロジェクトのビルド

ソースコード・テンプレートが準備できたら以下を実行します。

```bash
sam build
```

これでtemplate.yamlに基づき、Lambda用のパッケージが.aws-sam/build配下に生成されます。

## ローカルでのテスト (オプション)
### ローカルDynamoDBの準備
