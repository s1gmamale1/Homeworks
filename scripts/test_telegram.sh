#!/bin/bash
#
# Test Telegram connectivity for NETS Homework Builder.
# Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.
#

set -e

# Check for required env vars
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "ERROR: TELEGRAM_BOT_TOKEN not set"
    echo "Set it: export TELEGRAM_BOT_TOKEN=<bot_token>"
    exit 1
fi

if [ -z "$TELEGRAM_CHAT_ID" ]; then
    echo "ERROR: TELEGRAM_CHAT_ID not set"
    echo "Set it: export TELEGRAM_CHAT_ID=<chat_id>"
    exit 1
fi

# Build test message with hostname and timestamp
HOSTNAME=$(hostname 2>/dev/null || echo "unknown")
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC" 2>/dev/null || echo "unknown")
MESSAGE="✅ NETS test message — $HOSTNAME $TIMESTAMP"

# Send the message via Telegram Bot API
RESPONSE=$(curl -sS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    -d "text=${MESSAGE}")

# Echo the response
echo "$RESPONSE"

# Check if the response contains "ok": true
if echo "$RESPONSE" | grep -q '"ok":true'; then
    exit 0
else
    exit 1
fi
