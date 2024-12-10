#!/bin/bash

# ヘルプオプション
if [ "$1" = "--help" ]; then
    echo "Usage: $0 <log-group-name> <start-date> <end-date> <pattern>"
    echo "Example: $0 /aws/lambda/my-function 'YYYY-MM-DD HH:MM:SS' 'YYYY-MM-DD HH:MM:SS' ERROR"
    echo "Description: This script filters logs from the specified log group in CloudWatch."
    exit 0
fi

LOG_GROUP_NAME=$1
START_DATE=$2
END_DATE=$3
PATTERN=${4:-"ERROR"} # デフォルトで"ERROR"を検索

# 引数のバリデーション
if [ -z "$LOG_GROUP_NAME" ] || [ -z "$START_DATE" ] || [ -z "$END_DATE" ]; then
    echo "Error: Missing required arguments."
    echo "Usage: $0 <log-group-name> <start-date> <end-date> <pattern>"
    exit 1
fi

# 日付フォーマットの検証
if ! date -d "$START_DATE" >/dev/null 2>&1 || ! date -d "$END_DATE" >/dev/null 2>&1; then
    echo "Error: Invalid date format. Use 'YYYY-MM-DD HH:MM:SS'."
    exit 1
fi

# 日付をエポックミリ秒に変換
start_time=$(date -d "$START_DATE" +%s%3N)
end_time=$(date -d "$END_DATE" +%s%3N)

# AWS CLIコマンドの実行
aws logs filter-log-events \
    --log-group-name "$LOG_GROUP_NAME" \
    --start-time "$start_time" \
    --end-time "$end_time" \
    --filter-pattern "$PATTERN" || {
    echo "Error: Failed to retrieve logs."
    exit 1
}
