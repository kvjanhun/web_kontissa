#!/bin/bash
set -e

cd /home/kvjanhun/Projects/web_kontissa || exit 1

source /home/kvjanhun/.config/site-alerts.env

send_telegram() {
  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    -d "text=$1" \
    -d "parse_mode=HTML" > /dev/null 2>&1
}

trap 'trap - ERR; send_telegram "❌ <b>Deploy failed</b>
Commit: <code>$(git log -1 --pretty=%h 2>/dev/null || echo unknown)</code> $(git log -1 --pretty=%s 2>/dev/null)
Time: $(date "+%Y-%m-%d %H:%M")"; exit 1' ERR

export GIT_SSH_COMMAND="ssh -i /home/kvjanhun/.ssh/webhook_deploy_key -o IdentitiesOnly=yes"
echo "Pulling latest changes from GitHub..."
git pull origin main

echo "Rebuilding Docker container..."
docker compose up --build -d

COMMIT_MSG=$(git log -1 --pretty=%s)
COMMIT_HASH=$(git log -1 --pretty=%h)
send_telegram "🚀 <b>Deployed successfully</b>
<code>${COMMIT_HASH}</code> ${COMMIT_MSG}
Site: https://erez.ac"

echo "Deploy complete."
