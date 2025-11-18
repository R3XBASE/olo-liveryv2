#!/bin/bash

# Set Webhook Script
# Usage: ./scripts/set_webhook.sh

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if BOT_TOKEN is set
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ BOT_TOKEN not set. Please set it in .env file"
    exit 1
fi

# Check if VERCEL_URL is set
if [ -z "$VERCEL_URL" ]; then
    echo "❌ VERCEL_URL not set. Please set it in .env file"
    exit 1
fi

echo "🔄 Setting webhook..."
echo "Bot Token: ${BOT_TOKEN:0:10}..."
echo "Webhook URL: $VERCEL_URL/api/index.py"

# Set webhook
response=$(curl -s -X POST \
  "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"$VERCEL_URL/api/index.py\"}")

echo ""
echo "Response:"
echo $response | python3 -m json.tool

# Get webhook info
echo ""
echo "🔍 Verifying webhook..."
curl -s "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo" | python3 -m json.tool
