# Observability Stack

## Architecture

```
node_exporter (host :9100) → Prometheus (container :9090) → Grafana (container :3000)
nginx logs + journald + grafana logs → Alloy (container) → Loki (container :3100) → Grafana
Flask app → Docker Loki driver → Loki → Grafana
```

All services run in Docker Compose except node_exporter, which runs directly on the RHEL host for accurate hardware metrics.

## Services

| Service | Image | Memory Limit | CPU Limit | Purpose |
|---------|-------|-------------|-----------|---------|
| loki | grafana/loki:3.6.7 | 256m | — | Log storage (30-day retention) |
| alloy | grafana/alloy:v1.17.0 | 128m | — | Log collection (nginx, journald, grafana logs) |
| prometheus | prom/prometheus:v3.3.0 | 128m | 0.25 | Metrics storage (14-day / 500MB cap) |
| grafana | grafana/grafana:12.4.1 | 256m | 0.5 | Dashboard UI at /logs/ subpath |
| node_exporter | v1.9.0 (host binary) | ~15MB | — | Host hardware metrics |

## Configuration Files

- `loki-config.yaml` — TSDB store, filesystem backend, 30-day retention, compaction every 1h with 10 workers
- `alloy-config.alloy` — Scrapes nginx logs, systemd journal (max_age 12h), and grafana file logs. Alloy state is persisted to `alloy_data`.
- `prometheus.yml` — Scrapes node_exporter at `172.18.0.1:9100` (Docker Compose network gateway) every 30s
- `grafana-datasources.yaml` — Provisions Loki (default) and Prometheus datasources
- `grafana-dashboards.yaml` — Auto-provisions dashboards from `dashboards/` directory
- `alerting/` — Provisions Grafana alerting: Telegram contact point, notification policy, and nginx log alert rules
- `dashboards/overview.json` — System Overview dashboard (see below)
- `dashboards/dog.json` — Dog Show Logs dashboard for `/dog` API and crawler logs
- `dashboards/sanakenno.json` — Sanakenno traffic and application logs from the shared Loki instance

## Dashboard: System Overview

**Top row** — Gauges: CPU %, Memory %, Disk %, Uptime
**Middle rows** — Time series: CPU & Memory over time, Network I/O, Disk I/O, Filesystem free space
**Bottom rows** — Logs: Nginx traffic, erez.ac errors/warnings (Flask JSON logs, unstructured web container errors, nginx 5xx/error logs), Security events (failed logins, auth/admin 401/403/429, scanner probes, rate limits, SSH, Grafana)

Refresh interval: 60s. Default time range: 6h.

## Dashboard: Dog Show Logs

`dashboards/dog.json` tracks `/dog` operational logs from Loki:

- Crawler log rate, Showlink request rate, result cache completions, and warnings/errors
- Crawler pass/result-cache event timelines grouped by structured `event`
- `/api/dog` and `/dog` request rate and p95 duration from Flask request logs
- Focused log panels for crawler passes, result-cache jobs, Showlink requests, dog API requests, and dog warnings/errors

Refresh interval: 60s. Default time range: 24h.

## Flask Structured Logging

- `structlog` with `JSONRenderer` outputs to stdout, captured by Docker's Loki logging driver
- `before_request` binds context: `path`, `method`, `ip` (from X-Forwarded-For)
- `after_request` logs every request with `status` and `duration_ms`
- Silent exception handlers in `health.py`, `weather.py`, and `utils.py` log errors/warnings instead of swallowing them silently — all appear in Grafana's erez.ac errors/warnings panel

## Grafana Alerting

- Telegram contact point: `alerting/contact-points.yaml`, using `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` from the Grafana container environment
- Notification template: `alerting/templates.yaml`, uses a compact plaintext Telegram body with only the alert status/count, alert name, summary, key labels, and Grafana open/silence links
- Notification policy: `alerting/notification-policies.yaml`, routes provisioned Grafana alerts to `telegram-critical`
- Rules: `alerting/nginx-alerts.yaml`
  - Shared unexpected nginx error-log burst detection for `erez.ac` and `sanakenno.fi`
  - Shared upstream failure detection from nginx error logs, excluding Grafana `/logs/` restart noise. Uses a `[2m]` count window with `for: 3m` so a brief web-container restart during deploy (upstream down < ~1 min) does not page, while a sustained outage still alerts within ~3 min.
  - Shared 5xx spike detection from JSON nginx access logs grouped by extracted `vhost`, excluding Grafana `/logs/`. Same `[2m]` / `for: 3m` deploy tolerance as the upstream rule (502/503s from a deploy restart are ignored).
  - Shared scanner-burst detection grouped by extracted `vhost` and `remote_addr`, excluding Grafana `/logs/`
  - Shared auth/admin suspicious-response detection for 401/403/429 on app auth/admin paths
  - Shared 429 burst detection grouped by extracted `vhost` and `remote_addr`
- Rules: `alerting/system-alerts.yaml`
  - Host root disk free space below 15% for 10 minutes
- The Grafana Compose service loads `/home/kvjanhun/.config/site-alerts.env` directly through `env_file`, so production deploys pass the existing Telegram alert secrets into Grafana without committing them or exposing them to app containers.

## Nginx Structured Logs

- `server/nginx-observability.conf` must be deployed to `/etc/nginx/conf.d/00-observability.conf`.
- Both nginx vhost files use `access_log ... kontissa_json` and return 404 for common scanner probe paths so `.env`, `.git`, WordPress/PHP, and similar requests do not fall through to app/SPA 200 responses.
- Grafana/Loki log panels can still render the JSON as log lines; queries use `| json` when filtering or grouping by `server_name`, `remote_addr`, `request_uri`, `status`, or upstream fields. Alert queries extract JSON `server_name` as `vhost` to avoid direct-IP Host labels and colliding with Alloy's `host=nuc` stream label.

## Networking

- All ports bound to `127.0.0.1` — no external exposure
- Grafana accessed via nginx reverse proxy at `https://erez.ac/logs/`
- Prometheus scrapes node_exporter via Docker Compose network gateway (`172.18.0.1`)
- Firewall rule allows Docker bridge (172.18.0.0/16) to reach host port 9100

## Key Decisions

- **node_exporter on host** (not containerized) — more accurate hardware metrics, avoids mounting /proc and /sys
- **Prometheus remains separate from Alloy** — keeps metrics storage simple while Alloy handles host log collection
- **No cAdvisor** — overkill for 5 containers on a personal site
- **Docker Loki logging driver** for Flask — avoids file-based log collection for the main app
- **Image versions pinned** — prevents surprise breaking changes on rebuild
- **No Loki healthcheck** — Loki's distroless image has no shell or curl; `depends_on` for Grafana, Alloy, and web uses plain `service_started` semantics (the default when no condition is specified)

## Maintenance

```bash
# Seed node_exporter after fresh OS install
sudo systemctl enable --now node_exporter

# Reset Grafana (if provisioning conflicts after version bump)
docker compose down grafana && docker volume rm web_kontissa_grafana_data && docker compose up -d

# Check Prometheus targets
curl -s localhost:9090/api/v1/targets | python3 -m json.tool

# Check Loki health
docker compose logs loki --tail 10
```
