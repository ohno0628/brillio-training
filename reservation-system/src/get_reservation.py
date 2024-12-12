import os
import json
import boto3
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    # TABLE_NAME環境変数が設定されているかチェック
    TABLE_NAME = os.environ.get("TABLE_NAME")
    if not TABLE_NAME:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "TABLE_NAME environment variable is not set"})
        }

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME)

    # pathParametersの確認
    if "pathParameters" not in event or "id" not in event["pathParameters"]:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Missing 'id' in pathParameters"})
        }

    reservation_id = event["pathParameters"]["id"]

    # DynamoDBアクセス時のエラーハンドリング
    try:
        resp = table.get_item(Key={"reservationId": reservation_id})
    except ClientError as e:
        # DynamoDBアクセスエラー時には500エラーを返す
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Failed to access DynamoDB", "details": str(e)})
        }

    item = resp.get("Item")

    if not item:
        # アイテムが存在しない場合は404
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "Not found"})
        }

    # 正常時
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(item)
    }
