#!/bin/bash

# 各リージョンのインスタンスチェック関数
check_instances() {
  local region=$1
  # リージョン内のインスタンスを取得
  instance_count=$(aws ec2 describe-instances --region "$region" \
    --query "length(Reservations[*].Instances[*])" --output text 2>/dev/null)

  # AWS CLIコマンドの実行結果を確認
  if [ $? -ne 0 ]; then
    echo "$region: AWS CLIコマンドの実行に失敗しました。"
    return
  fi

  # インスタンス数に応じた出力
  if [ "$instance_count" -gt 0 ]; then
    echo "$region: $instance_count インスタンス"
  else
    echo "$region: インスタンスなし"
  fi
}

# 引数が指定されている場合、そのリージョンを処理
if [ $# -gt 0 ]; then
  for region in "$@"; do
    echo "指定されたリージョンを処理中: $region"
    check_instances "$region"
  done
  exit 0
fi

# 引数が指定されていない場合、全リージョンをチェック
regions=$(aws ec2 describe-regions --query "Regions[*].RegionName" --output text)

echo "各リージョンの結果:"
for region in $regions; do
  check_instances "$region"
done
