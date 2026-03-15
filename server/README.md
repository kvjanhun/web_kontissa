# Server Scripts

Shell scripts that run on the production server (RHEL, Intel NUC at erez.ac).
These are not part of the application stack — they handle deployment and alerting.

## Files

### `deploy-site.sh`
Triggered by the GitHub webhook on every push to main. Pulls the latest code,
rebuilds the Docker container, and restarts the service. Sends a Telegram
notification on success or failure.

**Deployed to:** `/home/kvjanhun/Projects/web_kontissa/deploy-site.sh`
**Triggered by:** `webhook.service` (listens on port 9000, token-authenticated)

### `health-alert.sh`
Checks the Docker container health status every 5 minutes via cron. Sends a
Telegram alert when the container becomes unhealthy, and a recovery message
with approximate downtime when it comes back up. Uses a flag file
(`/tmp/site-unhealthy.flag`) to avoid alert spam.

**Deployed to:** `/home/kvjanhun/scripts/health-alert.sh`
**Scheduled via:** `crontab -l` (runs as kvjanhun)
```
*/5 * * * * /home/kvjanhun/scripts/health-alert.sh
```

## Configuration

Both scripts source `/home/kvjanhun/.config/site-alerts.env` for Telegram
credentials. This file lives only on the server and is never committed to the repo.

```bash
# /home/kvjanhun/.config/site-alerts.env
TELEGRAM_BOT_TOKEN="..."
TELEGRAM_CHAT_ID="..."
```

## Database Backup & Restore

Litestream continuously replicates `site.db` to Backblaze B2 (`erezac-db-backup` bucket, `eu-central-003` region). Config: `server/observability/litestream.yml`. Credentials in `.env` on the NUC (`B2_KEY_ID`, `B2_APP_KEY`).

### Restore from backup

```bash
# 1. Install litestream (if not available via Docker)
docker pull litestream/litestream:0.3

# 2. Stop the web container to avoid writes during restore
docker compose stop web

# 3. Restore the database
docker run --rm \
  -e LITESTREAM_ACCESS_KEY_ID="$B2_KEY_ID" \
  -e LITESTREAM_SECRET_ACCESS_KEY="$B2_APP_KEY" \
  -v /home/kvjanhun/Projects/web_kontissa/app/data:/data \
  litestream/litestream:0.3 \
  restore -o /data/site.db \
  -endpoint https://s3.eu-central-003.backblazeb2.com \
  s3://erezac-db-backup/site.db

# 4. Optionally restore to a specific point in time
#    (within the 72h WAL retention window)
docker run --rm \
  -e LITESTREAM_ACCESS_KEY_ID="$B2_KEY_ID" \
  -e LITESTREAM_SECRET_ACCESS_KEY="$B2_APP_KEY" \
  -v /home/kvjanhun/Projects/web_kontissa/app/data:/data \
  litestream/litestream:0.3 \
  restore -o /data/site.db \
  -endpoint https://s3.eu-central-003.backblazeb2.com \
  -timestamp "2026-03-15T12:00:00Z" \
  s3://erezac-db-backup/site.db

# 5. Restart everything
docker compose up -d
```

### Verify backup is working

```bash
# Check litestream logs
docker logs web_kontissa-litestream-1

# Browse the bucket in Backblaze dashboard or via B2 CLI
b2 ls erezac-db-backup site.db/
```

## Deploying changes

```bash
scp server/deploy-site.sh kvjanhun@erez.ac:/home/kvjanhun/Projects/web_kontissa/deploy-site.sh
scp server/health-alert.sh kvjanhun@erez.ac:/home/kvjanhun/scripts/health-alert.sh
```
