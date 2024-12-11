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

    # pathParametersの存在確認
    if "pathParameters" not in event or "id" not in event["pathParameters"]:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Missing 'id' in pathParameters"})
        }

    reservation_id = event["pathParameters"]["id"]

    # 削除対象のアイテムが存在するか確認
    try:
        resp = table.get_item(Key={"reservationId": reservation_id})
    except ClientError as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Failed to access DynamoDB", "details": str(e)})
        }

    item = resp.get("Item")
    if not item:
        # 対象アイテムが存在しない場合
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "Reservation not found"})
        }

    # アイテムが存在する場合、削除実行
    try:
        table.delete_item(Key={"reservationId": reservation_id})
    except ClientError as e:
        # DynamoDB操作失敗時
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Failed to delete reservation", "details": str(e)})
        }

    # 正常終了
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": "Reservation deleted"})
    }
