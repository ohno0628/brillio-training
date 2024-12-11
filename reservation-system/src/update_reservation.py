import os
import json
import boto3
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    # TABLE_NAME環境変数の有無をチェック
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

    # pathParametersのチェック
    if "pathParameters" not in event or "id" not in event["pathParameters"]:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Missing 'id' in pathParameters"})
        }

    reservation_id = event["pathParameters"]["id"]

    # リクエストボディのJSONパースとエラーハンドリング
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Invalid JSON in request body"})
        }
    
    
    # 必須フィールドチェック
    # (ここでは更新時もreservationIdは必須であり、idが指定されているのでそれを使う)
    body["reservationId"] = reservation_id

    # DynamoDB更新処理のエラーハンドリング
    try:
        table.put_item(Item=body)
    except ClientError as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Failed to update reservation", "details": str(e)})
        }

    # 正常終了
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": "Reservation updated", "reservationId": reservation_id})
    }