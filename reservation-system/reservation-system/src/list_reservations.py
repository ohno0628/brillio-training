import os
import json
import boto3
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    # 環境変数チェック
    TABLE_NAME = os.environ.get("TABLE_NAME")
    if not TABLE_NAME:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "TABLE_NAME environment variable is not set"})
        }

    # dynamodb = boto3.resource('dynamodb')
    # table = dynamodb.Table(TABLE_NAME)
    ENDPOINT_URL = "http://localhost:8000"
    dynamodb = boto3.resource('dynamodb', endpoint_url=ENDPOINT_URL)
    table_name = os.environ.get("TABLE_NAME", "ReservationsTable")
    table = dynamodb.Table(table_name)

    # 全レコードスキャン（サンプル用途）
    try:
        resp = table.scan()
    except ClientError as e:
        # DynamoDBアクセスエラー時
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Failed to retrieve reservations", "details": str(e)})
        }

    items = resp.get("Items", [])

    # 正常終了
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(items)
    }
