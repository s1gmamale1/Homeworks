# Telegram Connectivity Test

## What it does
`test_telegram.sh` sends a test message to a Telegram chat in 30 seconds. Use it to verify Telegram connectivity after configuring the bot token.

## How to use
1. Set environment variables:
   ```bash
   export TELEGRAM_BOT_TOKEN=<your_bot_token>
   export TELEGRAM_CHAT_ID=<your_chat_id>
   ```
2. Run: `bash scripts/test_telegram.sh`
3. Expected output: JSON response with `"ok":true` and message ID.

## Finding your chat ID
- Start a chat with your Telegram bot.
- In the chat, send any message.
- Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates` (replace `<TOKEN>` with your bot token).
- Look for `"chat":{"id":<number>,...}` — that number is your chat ID.

## Common errors
- `TELEGRAM_BOT_TOKEN not set`: export the token first.
- `{"ok":false,"error_code":401,"description":"Unauthorized"}`: bot token is invalid.
- `{"ok":false,"error_code":400,"description":"Bad Request"}`: chat ID is missing or invalid.
