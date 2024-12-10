#!/bin/bash

# 利用可能なリージョンを取得
regions=$(aws ec2 describe-regions --query "Regions[*].RegionName" --output text)

echo "以下のリージョンに実インスタンスが存在します:"
for region in $regions; do
  # 各リージョンでインスタンスをチェック
  instance_count=$(aws ec2 describe-instances --region $region \
    --query "Reservations[*].Instances[*].[InstanceId]" \
    --output text | wc -l)

  if [ $instance_count -gt 0 ]; then
    echo "$region: $instance_count インスタンス"
  fi
done

