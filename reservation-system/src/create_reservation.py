# import os
# import json
# import uuid
# import boto3
# from botocore.exceptions import ClientError

# ENDPOINT_URL = "http://dynamodb:8000"

# # ダミークレデンシャルとリージョン指定
# dynamodb = boto3.resource(
#     'dynamodb',
#     endpoint_url=ENDPOINT_URL,
#     region_name='ap-northeast-1',
#     aws_access_key_id='dummy',
#     aws_secret_access_key='dummy'
# )
# table = dynamodb.Table("ReservationsTable")

# def lambda_handler(event, context):
#     try:
#         body = json.loads(event.get("body", "{}"))
#     except json.JSONDecodeError:
#         return {
#             "statusCode": 400,
#             "headers": {"Content-Type": "application/json"},
#             "body": json.dumps({"error": "Invalid JSON in request body"})
#         }

#     if "resourceName" not in body or "time" not in body:
#         return {
#             "statusCode": 400,
#             "headers": {"Content-Type": "application/json"},
#             "body": json.dumps({"error": "Missing required field(s): resourceName, time"})
#         }

#     reservation_id = str(uuid.uuid4())
#     body["reservationId"] = reservation_id

#     try:
#         table.put_item(Item=body)
#     except ClientError as e:
#         return {
#             "statusCode": 500,
#             "headers": {"Content-Type": "application/json"},
#             "body": json.dumps({"error": "Failed to create reservation", "details": str(e)})
#         }

#     return {
#         "statusCode": 201,
#         "headers": {"Content-Type": "application/json"},
#         "body": json.dumps({"message": "Reservation created", "reservationId": reservation_id})
#     }


import os
import json
import uuid
import boto3
from botocore.exceptions import ClientError

TABLE_NAME = os.environ.get("TABLE_NAME")  # template.yamlで設定 or Lambdaの環境変数設定
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Invalid JSON in request body"})
        }

    if "resourceName" not in body or "time" not in body:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Missing required field(s): resourceName, time"})
        }

    reservation_id = str(uuid.uuid4())
    body["reservationId"] = reservation_id

    try:
        table.put_item(Item=body)
    except ClientError as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Failed to create reservation", "details": str(e)})
        }

    return {
        "statusCode": 201,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": "Reservation created", "reservationId": reservation_id})
    }
