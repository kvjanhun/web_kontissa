#!/bin/bash

cd /home/kvjanhun/Projects/web_kontissa || exit 1

source /home/kvjanhun/.config/site-alerts.env

LOCK_FILE="/tmp/erezac-deploy.lock"
DEPLOY_FLAG="/tmp/erezac-deploying.flag"
WEB_CONTAINER="web_kontissa-web-1"
HEALTH_URL="http://127.0.0.1:8080/api/meta"

send_telegram() {
  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    -d "text=$1" \
    -d "parse_mode=HTML" > /dev/null 2>&1
}

fail() {
  send_telegram "❌ <b>Deploy failed</b>
Stage: <code>$1</code>
Commit: <code>$(git log -1 --pretty=%h 2>/dev/null || echo unknown)</code> $(git log -1 --pretty=%s 2>/dev/null)
Time: $(date "+%Y-%m-%d %H:%M")"
  exit 1
}

wait_for_web_health() {
  for _ in {1..45}; do
    STATUS=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$WEB_CONTAINER" 2>/dev/null || echo missing)
    if [ "$STATUS" = "healthy" ]; then
      return 0
    fi
    sleep 2
  done
  return 1
}

exec 9>"$LOCK_FILE"
flock -n 9 || fail "deploy lock"
touch "$DEPLOY_FLAG"
trap 'rm -f "$DEPLOY_FLAG"' EXIT

export GIT_SSH_COMMAND="ssh -i /home/kvjanhun/.ssh/webhook_deploy_key -o IdentitiesOnly=yes"
echo "Pulling latest changes from GitHub..."
git pull origin main || fail "git pull"

# Refresh the home-content snapshot from the live database so `nuxt generate`
# (inside the Docker build) bakes current content for first paint / SEO. Runs in
# the still-running web container, writing to the shared /app/data volume (which
# is bind-mounted to ./app/data on the host). Best effort: on the first deploy of
# this feature, or before the one-off DB migration, the tables may not exist yet
# — in that case we keep the committed snapshot (the client also re-fetches live
# content at runtime, so visitors always see current data either way).
echo "Refreshing home-content snapshot from the database (best effort)..."
if docker ps --format '{{.Names}}' | grep -q "^${WEB_CONTAINER}$" \
   && docker exec "$WEB_CONTAINER" python scripts/export_home_content.py --out /app/data/home-content.snapshot.json \
   && [ -s app/data/home-content.snapshot.json ]; then
  mv app/data/home-content.snapshot.json frontend/locales/home-content.snapshot.json
  echo "Snapshot refreshed from the database."
else
  rm -f app/data/home-content.snapshot.json
  echo "Snapshot export skipped; using the committed snapshot."
fi

echo "Rebuilding Docker container..."
docker compose up --build -d || fail "docker compose"

echo "Waiting for web container health..."
wait_for_web_health || fail "container health"

echo "Verifying local HTTP health..."
curl -fsS --max-time 10 "$HEALTH_URL" > /dev/null || fail "local health check"

COMMIT_MSG=$(git log -1 --pretty=%s)
COMMIT_HASH=$(git log -1 --pretty=%h)
send_telegram "🚀 <b>Deployed successfully</b>
<code>${COMMIT_HASH}</code> ${COMMIT_MSG}
Site: https://erez.ac"

echo "Deploy complete."
