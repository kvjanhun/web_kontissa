# Server

How erez.ac is deployed and how its database is backed up and restored.

**Host configuration lives in the `nuc` repo** (`~/Projects/nuc`): nginx
vhosts, fail2ban, the deploy webhook, systemd units, cron jobs, and the health
and blocklist scripts. Its README is the map of what runs on the machine and
which repo owns what.

What is still here, and why:

- `deploy-site.sh` — deploys *this* application. It stays in this repo because
  the `git pull` it performs also updates the script itself, so it always
  matches the code it is deploying.
- `observability/` — Loki, Alloy, Prometheus, Grafana, and Litestream configs.
  These are host-level in spirit, but their containers are still defined in
  this repo's `docker-compose.yml` and mount these paths. See the known seam in
  `~/Projects/nuc/README.md`.

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

### `scripts/prune_pageview_events.py` (in-container)

Drops `PageViewEvent` rows past the 90-day window `/api/pageviews/events` can serve.
Nothing in the request path prunes, so without this the table grows forever and gets
replicated to B2 by Litestream along with everything else.

Unlike the scripts above this one is **not** deployed to `/home/kvjanhun/scripts/` — it
ships inside the web image and runs via `docker exec`, so it picks up the mounted data
volume and the container's `DATABASE_URI`.

**Scheduled via:** `crontab -l` (runs as kvjanhun — needs docker group access)
```
0 5 * * 0 /usr/bin/docker exec web_kontissa-web-1 python scripts/prune_pageview_events.py
```

Absolute `/usr/bin/docker` matters: cron's `PATH` is minimal and a bare `docker` will not
resolve. Weekly is ample for a 90-day window; 04:00 and 04:30 are already taken by
the `nuc` repo's backup and blocklist jobs.

Always dry-run first — it reports the count without deleting:
```bash
docker exec web_kontissa-web-1 python scripts/prune_pageview_events.py --dry-run
```

## Configuration

`deploy-site.sh` sources `/home/kvjanhun/.config/site-alerts.env` for Telegram
credentials, as do the host scripts in the `nuc` repo. This file lives only on
the server and is never committed to any repo.

```bash
# /home/kvjanhun/.config/site-alerts.env
TELEGRAM_BOT_TOKEN="..."
TELEGRAM_CHAT_ID="..."
ABUSEIPDB_API_KEY="..."   # used by the nuc repo's blocklist script and fail2ban action
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

Application changes deploy themselves: push to `main`, CI runs, the webhook
fires `deploy-site.sh`, and the CI job polls until the live site serves the
pushed commit.

`deploy-site.sh` itself is pulled by the deploy it performs, so it needs no
manual copy. The only file here that is installed by hand is the observability
config, and only when its containers are restarted:

```bash
cd ~/Projects/web_kontissa && git pull && docker compose up -d
```

For host configuration — nginx, fail2ban, cron scripts, systemd units — see
the runbook in `~/Projects/nuc/OPERATIONS.md`.
