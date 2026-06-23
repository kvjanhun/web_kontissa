# Server Scripts

Shell scripts that run on the production server (RHEL, Intel NUC at erez.ac).
These are not part of the application stack — they handle deployment and alerting.

## Files

### `deploy-site.sh`
Triggered by the GitHub webhook on every push to main. Pulls the latest code,
rebuilds the Docker container, and restarts the service. Sends a Telegram
notification on success or failure. Each step uses explicit `|| fail "<stage>"`
error handling — the failure message includes the stage name and commit info.
No `set -e` / ERR trap. A deploy lock prevents overlapping webhook runs, and
`/tmp/erezac-deploying.flag` suppresses transient health alerts while Docker is
rebuilding. The script waits for the web container to report healthy and verifies
`/api/meta` locally before sending the success notification.

**Deployed to:** `/home/kvjanhun/Projects/web_kontissa/deploy-site.sh`
**Triggered by:** `webhook.service` (listens on port 9000, token-authenticated)

### `health-alert.sh`
Combined health check for **both** erez.ac (`web_kontissa-web-1`) and
sanakenno.fi (`sanakenno-a` / `sanakenno-b`) — this repo owns the shared host
plumbing for both sites, so this single monitor replaces any per-site check.
Runs every 5 minutes via cron. Sends a Telegram alert when a container becomes
unhealthy and a recovery message with approximate downtime when it recovers.
Per-container flag files (`/tmp/<container>-unhealthy.flag`) avoid alert spam,
and Docker inspect is retried with a "missing" streak threshold so one transient
read does not page.

During a fresh deploy each site honors its own deploy flag (erez.ac:
`/tmp/erezac-deploying.flag`, written by `deploy-site.sh`); while that flag is
present and fresh, transient unhealthiness is suppressed. If the flag is older
than 30 minutes (`HEALTH_ALERT_DEPLOY_SUPPRESS_SECONDS`), alerts resume so a hung
deploy still pages you. This is what prevents the brief container-rebuild window
from firing a false "erez.ac is down" alert.

Mocked tests (no Docker/network/Telegram) live in `health-alert-test.sh`:
```bash
bash server/health-alert-test.sh all
```

**Deployed to:** `/home/kvjanhun/scripts/health-alert.sh`
**Scheduled via:** `crontab -l` (runs as kvjanhun)
```
*/5 * * * * /home/kvjanhun/scripts/health-alert.sh
```

### `erez.ac.conf`
Nginx virtual host configuration for erez.ac. Defines the HTTP→HTTPS redirect,
TLS settings, reverse proxy rules, and security headers (HSTS, X-Content-Type-Options,
X-Frame-Options, Referrer-Policy, Permissions-Policy). CSP is enforced. Common
scanner probe paths such as hidden dotfiles, PHP/ASP, and WordPress endpoints
return 404 before reaching the app fallback.

**Deployed to:** `/etc/nginx/conf.d/erez.ac.conf`

### `nginx-observability.conf`
Shared nginx observability config. Defines the `kontissa_json` access-log format
used by both `erez.ac` and `sanakenno.fi`, so Loki/Grafana can query nginx
events by `host`, `remote_addr`, `request_uri`, `status`, and upstream fields
instead of regexing combined-access-log text.

**Deployed to:** `/etc/nginx/conf.d/00-observability.conf`

### `sanakenno.fi.conf`
Nginx virtual host configuration for the separate Sanakenno deployment. The app
code lives in `~/Projects/sanakenno`, but the live host config is maintained
here with the other NUC nginx config. Common scanner probe paths return 404
before reaching the SPA fallback.

**Deployed to:** `/etc/nginx/conf.d/sanakenno.fi.conf`

### `fail2ban/` + `abuseipdb-blocklist.sh`
Automated intrusion response for **both** sites (host fail2ban service + AbuseIPDB
reporting and blocklist consumption). fail2ban watches the nginx JSON logs and the
journal, bans abusive IPs in the host iptables `INPUT` chain, and reports them to
AbuseIPDB; `abuseipdb-blocklist.sh` pulls AbuseIPDB's blocklist into an ipset and drops
those IPs pre-emptively. Bans flow to Grafana via the existing journal scrape (no
Telegram). Full operations notes, jail table, firewall-backend check, and verification:
**`server/fail2ban/README.md`**.

**Deployed to:** `/etc/fail2ban/{fail2ban.d,jail.d,filter.d}/…` and
`/home/kvjanhun/scripts/abuseipdb-blocklist.sh`
**Secret:** `ABUSEIPDB_API_KEY` in `site-alerts.env` + host-only
`/etc/fail2ban/action.d/abuseipdb.local` (never committed)

### `backup-configs.sh`
Backs up server configuration files (nginx, **fail2ban** minus the AbuseIPDB key,
kvjanhun + **root** crontabs, systemd services, **iptables and ipset** rules) to the same
Backblaze B2 bucket used for database backups. Uses `rclone` with a remote named `b2`.

**Deployed to:** `/home/kvjanhun/scripts/backup-configs.sh`
**Scheduled via:** `crontab -l` (runs as root)
```
0 4 * * * /home/kvjanhun/scripts/backup-configs.sh
```

**Setup (one-time on NUC):**
```bash
sudo dnf install rclone
rclone config
# Create a remote named "b2", type "b2", enter B2 key ID and app key
```

## Configuration

`deploy-site.sh` and `health-alert.sh` source `/home/kvjanhun/.config/site-alerts.env` for Telegram
credentials. This file lives only on the server and is never committed to the repo.

```bash
# /home/kvjanhun/.config/site-alerts.env
TELEGRAM_BOT_TOKEN="..."
TELEGRAM_CHAT_ID="..."
ABUSEIPDB_API_KEY="..."   # used by abuseipdb-blocklist.sh and the fail2ban abuseipdb action
```

## Database Backup & Restore

Litestream continuously replicates `site.db` to Backblaze B2 (`erezac-db-backup` bucket, `eu-central-003` region). The same sidecar also replicates Sanakenno's separate `~/Projects/sanakenno/server/data/sanakenno.db`; no backup container lives in the Sanakenno repo. Config: `server/observability/litestream.yml`. Credentials in `.env` on the NUC (`B2_KEY_ID`, `B2_APP_KEY`).

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
scp server/backup-configs.sh kvjanhun@erez.ac:/home/kvjanhun/scripts/backup-configs.sh
sudo scp server/nginx-observability.conf kvjanhun@erez.ac:/etc/nginx/conf.d/00-observability.conf
sudo scp server/erez.ac.conf kvjanhun@erez.ac:/etc/nginx/conf.d/erez.ac.conf && sudo nginx -t && sudo systemctl reload nginx
sudo scp server/sanakenno.fi.conf kvjanhun@erez.ac:/etc/nginx/conf.d/sanakenno.fi.conf && sudo nginx -t && sudo systemctl reload nginx

# fail2ban (see server/fail2ban/README.md for the one-time setup + firewall-backend check)
sudo scp server/fail2ban/fail2ban.d/logging.conf kvjanhun@erez.ac:/etc/fail2ban/fail2ban.d/logging.conf
sudo scp server/fail2ban/jail.d/kontissa.conf kvjanhun@erez.ac:/etc/fail2ban/jail.d/kontissa.conf
sudo scp server/fail2ban/filter.d/*.conf kvjanhun@erez.ac:/etc/fail2ban/filter.d/ && sudo fail2ban-client reload
scp server/abuseipdb-blocklist.sh kvjanhun@erez.ac:/home/kvjanhun/scripts/abuseipdb-blocklist.sh
```
