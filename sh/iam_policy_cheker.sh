#!/bin/bash

USER_NAME=$1

if [ -z "$USER_NAME" ]; then
  echo "Usage: $0 <IAM User Name>"
  exit 1
fi

TMP_FILE="/tmp/awscli_user_policy_checker.tmp"
TMP_GROUP_FILE="/tmp/awscli_group_list.tmp"

# ヘッダーを一時ファイルに書き込む
echo "UserName Groups" > "$TMP_FILE"

# AWS CLIでグループ情報を取得
echo "Processing policies for user: $USER_NAME"
echo "$USER_NAME" > "$TMP_GROUP_FILE"
aws iam list-groups-for-user --user-name "$USER_NAME" --query "Groups[].[GroupName]" --output text >> "$TMP_GROUP_FILE"

# グループ情報を整形して一時ファイルに追記
cat "$TMP_GROUP_FILE" | tr "\n" " " | sed 's/$/\n/g' >> "$TMP_FILE"

# 整形して出力
column -t "$TMP_FILE"

echo ""
echo "### ユーザーにアタッチされたポリシー ###"
# マネージドポリシー
echo "  マネージドポリシー:"
aws iam list-attached-user-policies --user-name "$USER_NAME" \
  --query "AttachedPolicies[*].[PolicyName, PolicyArn]" --output table || {
  echo "    エラー: ユーザー $USER_NAME のマネージドポリシーを取得できませんでした。"
}

# インラインポリシー
echo "  インラインポリシー:"
INLINE_POLICIES=$(aws iam list-user-policies --user-name "$USER_NAME" --query "PolicyNames" --output text)
if [ -z "$INLINE_POLICIES" ]; then
  echo "    なし"
else
  for policy in $INLINE_POLICIES; do
    echo "    ポリシー名: $policy"
    aws iam get-user-policy --user-name "$USER_NAME" --policy-name "$policy" \
      --query "PolicyDocument.Statement" --output json || {
      echo "    エラー: ポリシー $policy の内容を取得できませんでした。"
    }
  done
fi

# グループごとのポリシーを取得
echo ""
echo "### グループにアタッチされたポリシー ###"
while IFS= read -r group; do
  if [ "$group" != "$USER_NAME" ]; then
    echo "グループ: $group"

    # マネージドポリシー
    echo "  マネージドポリシー:"
    aws iam list-attached-group-policies --group-name "$group" \
      --query "AttachedPolicies[*].[PolicyName, PolicyArn]" --output table || {
      echo "    エラー: グループ $group のマネージドポリシーを取得できませんでした。"
    }

    # インラインポリシー
    echo "  インラインポリシー:"
    INLINE_POLICIES=$(aws iam list-group-policies --group-name "$group" --query "PolicyNames" --output text)
    if [ -z "$INLINE_POLICIES" ]; then
      echo "    なし"
    else
      for policy in $INLINE_POLICIES; do
        echo "    ポリシー名: $policy"
        aws iam get-group-policy --group-name "$group" --policy-name "$policy" \
          --query "PolicyDocument.Statement" --output json || {
          echo "    エラー: ポリシー $policy の内容を取得できませんでした。"
        }
      done
    fi
    echo ""
  fi
done < "$TMP_GROUP_FILE"

# 一時ファイルを削除
rm -f "$TMP_FILE" "$TMP_GROUP_FILE"
