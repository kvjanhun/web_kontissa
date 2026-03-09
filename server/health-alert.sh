#!/bin/bash
source /home/kvjanhun/.config/site-alerts.env

CONTAINER="web_kontissa-web-1"
FLAG_FILE="/tmp/site-unhealthy.flag"

send_telegram() {
  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    -d "text=$1" \
    -d "parse_mode=HTML" > /dev/null 2>&1
}

STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER" 2>/dev/null)
[ -z "$STATUS" ] && STATUS="missing"

if [ "$STATUS" != "healthy" ]; then
  if [ ! -f "$FLAG_FILE" ]; then
    send_telegram "⚠️ <b>erez.ac is down</b>
Status: <code>${STATUS}</code>
Time: $(date '+%Y-%m-%d %H:%M')
Container: ${CONTAINER}"
    touch "$FLAG_FILE"
  fi
else
  if [ -f "$FLAG_FILE" ]; then
    DOWN_SINCE=$(stat -c %Y "$FLAG_FILE" 2>/dev/null || stat -f %m "$FLAG_FILE")
    DOWNTIME_MIN=$(( ($(date +%s) - DOWN_SINCE) / 60 ))
    send_telegram "✅ <b>erez.ac is back up</b>
Downtime: ~${DOWNTIME_MIN} minutes"
    rm -f "$FLAG_FILE"
  fi
fi
