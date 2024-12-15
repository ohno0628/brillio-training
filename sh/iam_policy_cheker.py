import boto3
import json
import sys
from botocore.exceptions import BotoCoreError, ClientError

def get_managed_policies(user_name):
    """ユーザーにアタッチされたマネージドポリシーを取得"""
    iam_client = boto3.client('iam')
    response = iam_client.list_attached_user_policies(UserName=user_name)
    return response.get('AttachedPolicies', [])

def get_inline_policies(user_name):
    """ユーザーに設定されたインラインポリシーを取得"""
    iam_client = boto3.client('iam')
    response = iam_client.list_user_policies(UserName=user_name)
    inline_policies = []
    for policy_name in response.get('PolicyNames', []):
        policy = iam_client.get_user_policy(UserName=user_name, PolicyName=policy_name)
        inline_policies.append({policy_name: policy['PolicyDocument']})
    return inline_policies

def get_user_groups(user_name):
    """ユーザーが所属しているグループを取得"""
    iam_client = boto3.client('iam')
    response = iam_client.list_groups_for_user(UserName=user_name)
    return [group['GroupName'] for group in response.get('Groups', [])]

def get_group_policies(group_name):
    """グループにアタッチされたポリシーを取得"""
    iam_client = boto3.client('iam')
    response = iam_client.list_attached_group_policies(GroupName=group_name)
    return response.get('AttachedPolicies', [])

def main():
    """ローカル実行用エントリポイント"""
    if len(sys.argv) != 2:
        print("Usage: python script.py <IAM User Name>")
        sys.exit(1)
    
    user_name = sys.argv[1]
    try:
        result = {}
        result['ManagedPolicies'] = get_managed_policies(user_name)
        result['InlinePolicies'] = get_inline_policies(user_name)
        
        groups = get_user_groups(user_name)
        result['Groups'] = groups
        
        group_policies = {}
        for group in groups:
            group_policies[group] = get_group_policies(group)
        result['GroupPolicies'] = group_policies

        # 結果を出力
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (BotoCoreError, ClientError) as error:
        print(f"Error: {error}")
        sys.exit(1)

if __name__ == "__main__":
    main()

