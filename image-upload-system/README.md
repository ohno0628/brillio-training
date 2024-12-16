# 画像アップロードアプリ構築 ーEC2手動構築

## **前提**

---

## **全体の構成概要**

### 必要なAWSリソース

1. **VPCとサブネット**:

   - パブリックとプライベートサブネットを利用。
   - CIDR: `192.168.0.0/24`。

2. **EC2インスタンス**:

   - Flaskアプリケーションをホスティング。

3. **RDS**:

   - MySQLで画像情報（タイトル、説明、ファイルパス）を保存。

4. **S3**:

   - 画像ファイルを保存。

5. **ALB**:

   - EC2インスタンスへの負荷分散と公開エンドポイント。

6. **セキュリティグループ**:

   - 各リソース間の通信を制御。

未実装
<!-- ---

## **1. AWSリソースの手動作成**

### **1.1. VPCとサブネット**

#### **VPCの作成**:

1. AWS管理コンソールで「VPC」を開き、新しいVPCを作成。
2. CIDRブロック: `192.168.0.0/24`。

#### **サブネットの作成**:

1. **パブリックサブネット**:
   - CIDRブロック: `192.168.0.0/27`。
2. **プライベートサブネット**:
   - CIDRブロック: `192.168.0.64/27`。

#### **インターネットゲートウェイの設定**:

1. VPCにインターネットゲートウェイをアタッチ。
2. ルートテーブルに「0.0.0.0/0」のルートを追加。

--- -->

### **1.2. EC2インスタンスの作成**

#### **EC2インスタンスの起動**:

1. AMI: Amazon Linux 2。
2. インスタンスタイプ: t2.micro。
3. キーペア: 新しいキーペアを作成してダウンロード。

#### **セキュリティグループの設定**:

1. ポート22 (SSH): 自分のIPアドレスに限定 (例: `curl ifconfig.me` で取得可能なグローバルIPを指定)。
2. ポート80 (HTTP): すべてのIPを許可。

#### **Webサーバーのセットアップ**:

```bash
sudo yum update -y
sudo yum install -y python3 git pip
sudo pip3 install flask boto3 pymysql
```

### **MySQLクライアントのインストール**

Amazon Linux 2023環境でMysqlクライアントを入れるには以下、手順を実施する必要がある。

1. MySQLリポジトリを追加:

   ```bash
   sudo dnf -y install https://dev.mysql.com/get/mysql80-community-release-el9-1.noarch.rpm
   ```

2. 必要なパッケージをインストール:

   ```bash
   sudo dnf -y install mysql mysql-community-client
   ```

3. インストールが成功したことを確認:

   ```bash
   mysql --version
   ```

4. MySQLクライアントを使用してRDSインスタンスに接続:

   ```bash
   mysql -h <RDS_ENDPOINT> -u <USERNAME> -p
   ```

#### **アプリケーションディレクトリの作成**:

```bash
mkdir -p ~/flask-app
cd ~/flask-app
```

### **1.3. S3の設定**

#### **S3バケットの作成**:

1. バケット名: `image-upload-app-bucket-<ユニークな識別子>`。
2. パブリックアクセス設定: すべて無効。

#### **バケットポリシーの設定**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::image-upload-app-bucket-<ユニークな識別子>/*"
    }
  ]
}
```

### **1.4. RDSの作成**

#### **RDSインスタンス作成の詳細な手順**:

1. **データベースエンジンの選択**:

   - **MySQL**を選択。
   - 他の選択肢にはPostgreSQL、MariaDB、Amazon Auroraなどがあります。

2. **インスタンスクラスの設定**:

   - デフォルトでは`db.t2.micro`を選択。
   - 高性能が必要な場合は`db.m5.large`などを選択。

3. **ストレージタイプの選択**:

   - 汎用SSD (`gp3`) を推奨。
   - プロビジョンド IOPS SSD (`io2`) は高いIOPSが必要な場合に選択可能。

4. **ストレージサイズの設定**:

   - 最低20GBで開始。
   - 必要に応じて拡張可能。

5. **高可用性の設定**:

   - **マルチAZ配置**: 商用環境の場合は有効に。
   - 今回、学習目的のため無効のまま。

6. **パブリックアクセスの設定**:

   - **無効**にしてセキュリティを確保。

7. **VPCとサブネットの選択**:

   - アプリケーションのVPCを選択し、プライベートサブネットを設定。

8. **セキュリティグループの設定**:

   - EC2インスタンスからのアクセスを許可するセキュリティグループを設定。

9. **バックアップとモニタリングの設定**:

   - 自動バックアップ: 必要に応じて1～35日間設定。
   - 拡張モニタリング: 商用環境では有効にする。
   - 今回、ともに無効で問題ない。

10. **メンテナンスウィンドウの設定**:

    - トラフィックの少ない時間帯に設定。
    - 今回、ともに無効で問題ない。
---

#### **RDSインスタンスの起動**:

1. データベースエンジン: MySQL。
2. インスタンスタイプ: db.t2.micro。
3. パブリックアクセス: 無効。
4. セキュリティグループ: EC2インスタンスからのアクセスを許可。

#### **テーブル作成**

1. EC2からMySQLに接続:

   ```bash
   mysql -h <RDS_ENDPOINT> -u <USERNAME> -p
   ```

2. スキーマとテーブルの作成:

   ```sql
   CREATE DATABASE image_app;
   USE image_app;
   CREATE TABLE images (
       id INT AUTO_INCREMENT PRIMARY KEY,
       title VARCHAR(255) NOT NULL,
       description TEXT,
       file_path VARCHAR(255) NOT NULL
   );
   ```

3. 作成されたデータベースを確認:

   ```sql
   SHOW DATABASES;
   ```

   - `image_app` がリストに表示されることを確認。

4. テーブルの確認:

   ```sql
   SHOW TABLES;
   ```

   - `images` がリストに表示されることを確認。

5. テーブルスキーマの確認:

   ```sql
   DESCRIBE images;
   ```

   - `id`, `title`, `description`, `file_path` が含まれていることを確認。



## **2. Flaskアプリケーションの作成**

### **2.1. Flaskアプリのコード**

#### **`flaskアプリ`のアップロード**:
`flask-app`配下に`app.py`を配置

```
from flask import Flask, request, jsonify, render_template
import boto3
import pymysql

app = Flask(__name__)

# AWSリソース設定
S3_BUCKET = 'image-upload-app-bucket-ohno'
s3 = boto3.client('s3')

# RDS接続設定
connection = pymysql.connect(
    host='database-1.c3ieg4gami7e.ap-northeast-1.rds.amazonaws.com',
    user='admin',
    password='Ohno!3340',
    database='image_app'
～～～～～～～～～～～～～～～～
```

#### **アプリの起動**:

```bash
python3 app.py
```

**動作確認：**

ブラウザで以下のURLにアクセスします：
```
http://<パブリックIP>:8080
```

## **3. フロントエンドの構築**

### **3.1. HTMLとCSS、JSの準備**

#### **`index.html`**:
ファイルを準備して`flask-app/templates/`に配置
```
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Image Upload App</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <h1>Image Upload App</h1>
～～～～～～～～～～～～～～～～
```
#### **`style.css`**:
ファイルを準備して`flask-app/static/`に配置
```
body {
    font-family: Arial, sans-serif;
    margin: 20px;
}
h1 {
    color: #333;
～～～～～～～～～～～～～～～～
```


#### **`script.js`**:
ファイルを準備して`flask-app/static/`に配置
```
document.getElementById('uploadForm').addEventListener('submit', async (event) => {
    event.preventDefault();

    const formData = new FormData();
    formData.append('title', document.getElementById('title').value);
    formData.append('description', document.getElementById('description').value);
    formData.append('file', document.getElementById('file').files[0]);

    const response = await fetch('/upload', {
        method: 'POST',
        body: formData,
    });
～～～～～～～～～～～～～～～～
```

## **4. 動作確認**

1. **画像アップロードの確認**:

   - `/upload`エンドポイントに対して、POSTリクエストを送信（タイトル、説明、画像を添付）。
   - 例: Postmanやブラウザフォームを使用。

2. **画像リストの取得**:

   - `/images`エンドポイントにアクセスし、登録済みの画像リストを取得。

---
## 5. アプリの自動起動設定

### Gunicornのインストールと起動

`gunicorn`はFlaskアプリケーションを本番運用する際によく使われるWSGIサーバです。

```bash
pip install gunicorn
```
アプリケーションを起動するには以下コマンドを実行
```
gunicorn -w 4 -b 0.0.0.0:8080 app:app
```
* `-w 1`:ワーカー数を指定
* `-b 0.0.0.0:8080`:ホストとポートを指定

### systemdでのGunicorn管理
`systemd`を使用してGunicorn（Flaskアプリ）をサービスとして管理することで、自動起動設定、サービスとして扱うことを可能とする。

1. **サービスファイルの作成**
`/etc/systemd/system/flask-app.service`というファイルを作成

```bash
sudo nano /etc/systemd/system/flask-app.service

以下の内容を記載
[Unit]
Description=Gunicorn instance to serve Flask App
After=network.target

[Service]
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/flask-app
ExecStart=/usr/local/bin/gunicorn -w 4 -b 0.0.0.0:8080 app:app

[Install]
WantedBy=multi-user.target
```

2. **サービスを有効化**
設定読み込み、サービスを有効化・起動
```
sudo systemctl daemon-reload
sudo systemctl enable flask-app
sudo systemctl start flask-app
```

3. **サービスの状態確認**
正常性確認
```
sudo systemctl status flask-app
```


### おまけ
現在、app.pyにDB情報を直接記述しているが、ハードコーディングには様々なリスクとデメリットがあります。


**セキュリティリスク**：パスワード漏洩、平文での保持
**運用リスク**：メンテナンス性の低下やトレーサビリティの欠如


#### **ハードコーディングの代替案**
1. 環境変数の使用
   - 認証情報を環境変数として管理し、コード内で取得する。
   - 環境ごとに異なる設定を簡単に切り替え可能。
2. 外部設定ファイルの使用
   - 設定情報を`config.ini`や`.env`ファイルに保存し、アプリケーションで読み込む。
   - ファイルのアクセス権を厳密に制御（例: `chmod 600`）。
3. AWS Secrets ManagerやParameter Storeの利用
   - AWSが提供するマネージドサービスで認証情報を安全に管理。
   - アクセス権限をIAMロールで制御。

1.2についてはそういうやり方もあるんだぐらいでいったん良いです。
利用する場合は、管理方法には十分注意が必要となります。

#### **Secrets Managerにデータベース情報を保持**
1. Secrets Managerで以下のキーバリュー情報を登録：
   ```
   "host": "<RDSエンドポイント>"
   "username": "<username>",
   "password": "<password>",
   "database": "image_app"
   ```

2. IAMロールの設定：
   - EC2インスタンスにSecrets Managerの権限を付与
   
      `secretsmanager:GetSecretValue`権限を付与。

3. `app.py`を修正：
   - Secrets Managerから情報を取得するよう修正：
      ```
         session = boto3.session.Session()
      client = session.client(service_name='secretsmanager', region_name='ap-northeast-1')

      secret_name = "your-secret-name"
      secret = json.loads(client.get_secret_value(SecretId=secret_name)['SecretString'])

      connection = pymysql.connect(
         host=secret['host'],
         user=secret['username'],
         password=secret['password'],
         database=secret['database']
      )
      ```



### 実技として
- ALBの設定
- Web/APサーバを2台構成にしてトラフィックが分かれることの確認
- HTTPS化
- サブネットやセキュリティグループをきれいにする。

とりあえずの構成図と目指す形の構成図を用意


ALB -ACM
参考手順
[自己証明書の作成](../tips/AWS/ACM.md)

EC2もしくはローカルで実行
```
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```
対話の設定は適当でよい
- key.pem：秘密鍵
- cert.pem：証明書

1. ACMを開く
2. インポートを選択
   - **証明書：**`cert.pem`の内容を貼り付け
   - **秘密鍵：**`key.pem`の内容を貼り付け
3. インポートをクリック
4. 

[ロードバランサーの設定](../tips/AWS/LB.md)

リスナーの設定方法

HTTPからHTTPSへのリダイレクト設定

自己著名証明書（俗にいうオレオレ証明）はブラウザ警告が出るが無視して
テストとしては問題ない。
HTTPでアクセスしてリダイレクトされていることが確認できればOK

DBへのアクセスをや指定方法を直書きやめる



同じソースでコンテナ化
各リソース（VPC、S3、EC2、RDS）を段階的にCFn化。