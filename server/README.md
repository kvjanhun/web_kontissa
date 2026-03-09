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

## Deploying changes

```bash
scp server/deploy-site.sh  kvjanhun@erez.ac:/home/kvjanhun/Projects/web_kontissa/deploy-site.sh
scp server/health-alert.sh kvjanhun@erez.ac:/home/kvjanhun/scripts/health-alert.sh
```
