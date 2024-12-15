import boto3
import json

def list_iam_users():
    client = boto3.client('iam')
    users = client.list_users()
    return users

if __name__ == "__main__":
    result = list_iam_users()
    # datetimeなどのオブジェクトを文字列化してJSON整形する
    print(json.dumps(result, indent=4, default=str))
