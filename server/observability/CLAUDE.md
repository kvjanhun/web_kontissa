# Observability Stack

## Architecture

```
node_exporter (host :9100) → Prometheus (container :9090) → Grafana (container :3000)
nginx logs + journald + grafana logs → Promtail (container) → Loki (container :3100) → Grafana
Flask app → Docker Loki driver → Loki → Grafana
```

All services run in Docker Compose except node_exporter, which runs directly on the RHEL host for accurate hardware metrics.

## Services

| Service | Image | Memory Limit | CPU Limit | Purpose |
|---------|-------|-------------|-----------|---------|
| loki | grafana/loki:3.6.7 | 256m | — | Log storage (14-day retention) |
| promtail | grafana/promtail:3.3.2 | 128m | — | Log collection (nginx, journald, grafana logs) |
| prometheus | prom/prometheus:v3.3.0 | 128m | 0.25 | Metrics storage (14-day / 500MB cap) |
| grafana | grafana/grafana:12.4.1 | 256m | 0.5 | Dashboard UI at /logs/ subpath |
| node_exporter | v1.9.0 (host binary) | ~15MB | — | Host hardware metrics |

## Configuration Files

- `loki-config.yaml` — TSDB store, filesystem backend, 14-day retention, compaction every 1h with 10 workers
- `promtail-config.yaml` — Scrapes nginx logs, systemd journal (max_age 12h), grafana file logs. Position file persisted to `promtail_positions` volume.
- `prometheus.yml` — Scrapes node_exporter at `172.18.0.1:9100` (Docker Compose network gateway) every 30s
- `grafana-datasources.yaml` — Provisions Loki (default) and Prometheus datasources
- `grafana-dashboards.yaml` — Auto-provisions dashboards from `dashboards/` directory
- `dashboards/overview.json` — System Overview dashboard (see below)

## Dashboard: System Overview

**Top row** — Gauges: CPU %, Memory %, Disk %, Uptime
**Middle rows** — Time series: CPU & Memory over time, Network I/O, Disk I/O, Filesystem free space
**Bottom rows** — Logs: Nginx traffic, App errors/warnings (Flask JSON logs), Security events (failed logins from Flask, SSH, Grafana)

Refresh interval: 60s. Default time range: 6h.

## Flask Structured Logging

- `structlog` with `JSONRenderer` outputs to stdout, captured by Docker's Loki logging driver
- `before_request` binds context: `path`, `method`, `ip` (from X-Forwarded-For)
- `after_request` logs every request with `status` and `duration_ms`

## Networking

- All ports bound to `127.0.0.1` — no external exposure
- Grafana accessed via nginx reverse proxy at `https://erez.ac/logs/`
- Prometheus scrapes node_exporter via Docker Compose network gateway (`172.18.0.1`)
- Firewall rule allows Docker bridge (172.18.0.0/16) to reach host port 9100

## Key Decisions

- **node_exporter on host** (not containerized) — more accurate hardware metrics, avoids mounting /proc and /sys
- **Prometheus over Grafana Alloy** — simpler to add alongside existing Promtail than to replace it
- **No cAdvisor** — overkill for 5 containers on a personal site
- **Docker Loki logging driver** for Flask — avoids file-based log collection for the main app
- **Image versions pinned** — prevents surprise breaking changes on rebuild

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
