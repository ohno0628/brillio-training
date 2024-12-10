#!/bin/bash

USER_NAME=$1

if [ -z "$USER_NAME" ]; then
  echo "Usage: $0 <IAM User Name>"
  exit 1
fi

echo "### ユーザーにアタッチされたマネージドポリシー ###"
aws iam list-attached-user-policies --user-name "$USER_NAME" \
  --query "AttachedPolicies[*].[PolicyName, PolicyArn]" --output table

echo "### ユーザーに設定されたインラインポリシー ###"
INLINE_POLICIES=$(aws iam list-user-policies --user-name "$USER_NAME" --query "PolicyNames" --output text)
if [ -n "$INLINE_POLICIES" ]; then
  for policy in $INLINE_POLICIES; do
    echo "ポリシー名: $policy"
    aws iam get-user-policy --user-name "$USER_NAME" --policy-name "$policy" \
      --query "PolicyDocument.Statement" --output json
  done
else
  echo "インラインポリシーなし (ユーザー $USER_NAME にインラインポリシーが割り当てられていません)"
fi

echo "### グループにアタッチされたポリシー ###"
# 修正: `readarray` を使用して `GROUPS` を配列として正確に取得
readarray -t GROUPS < <(aws iam list-groups-for-user --user-name "$USER_NAME" --query "Groups[*].GroupName" --output text)

if [ ${#GROUPS[@]} -eq 0 ]; then
  echo "ユーザー $USER_NAME はグループに所属していません。"
else
  for group in "${GROUPS[@]}"; do
    echo "グループ: $group"
    aws iam list-attached-group-policies --group-name "$group" \
      --query "AttachedPolicies[*].[PolicyName, PolicyArn]" --output table || {
        echo "Error: グループ $group のポリシーを取得できませんでした。"
      }
  done
fi

echo "### ロール引き受け権限 (sts:AssumeRole) の確認 ###"
AccountID=$(aws sts get-caller-identity --query "Account" --output text)

aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::$AccountID:user/$USER_NAME \
  --action-names sts:AssumeRole --output table
