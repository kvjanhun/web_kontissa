# Observability Stack

Logging and hardware monitoring for erez.ac, running on a self-hosted Intel NUC.

## Components

- **Grafana** — Dashboard UI, accessible at `https://erez.ac/logs/`
- **Loki** — Log aggregation (14-day retention)
- **Grafana Alloy** — Log collection from nginx, systemd journal, and Grafana
- **Prometheus** — Metrics storage (14-day retention, 500MB cap)
- **node_exporter** — Host hardware metrics (CPU, memory, disk, network)
- **Grafana Alerting** — Loki-backed nginx alerts routed to Telegram

## Setup

### 1. Install node_exporter on the host

```bash
curl -LO https://github.com/prometheus/node_exporter/releases/download/v1.9.0/node_exporter-1.9.0.linux-amd64.tar.gz
tar xzf node_exporter-1.9.0.linux-amd64.tar.gz
sudo cp node_exporter-1.9.0.linux-amd64/node_exporter /usr/local/bin/
rm -rf node_exporter-1.9.0.linux-amd64*

sudo tee /etc/systemd/system/node_exporter.service << 'EOF'
[Unit]
Description=Prometheus Node Exporter
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/node_exporter --web.listen-address=0.0.0.0:9100
Restart=always
User=nobody

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now node_exporter
```

### 2. Firewall

Allow Docker containers to reach node_exporter:

```bash
sudo iptables -I INPUT -s 172.18.0.0/16 -p tcp --dport 9100 -j ACCEPT
```

Port 9100 is not exposed externally — only reachable from the Docker bridge network and localhost.

### 3. Start the stack

```bash
docker compose up -d
```

All observability services are defined in the project root `docker-compose.yml`.

### 4. Telegram alerting

Grafana provisions a Telegram contact point from
`alerting/contact-points.yaml`. It reads `TELEGRAM_BOT_TOKEN` and
`TELEGRAM_CHAT_ID` from the Grafana container environment. On the production
NUC, only the Grafana service loads `/home/kvjanhun/.config/site-alerts.env`
through `env_file`, so the existing deploy alert secrets also feed Grafana
without exposing them to the app containers.

This is server-only plumbing. A laptop `docker compose up` will need either that
same env file path or a temporary local override; the production path is the one
that matters.

The provisioned policy routes Grafana alerts to `telegram-critical`. Because
Grafana treats the notification policy tree as one resource, keep policy edits
in `alerting/notification-policies.yaml` rather than changing the UI by hand.

Provisioned alerts:

| Alert | Source | Fires when |
|-------|--------|------------|
| Nginx error log activity | Loki nginx error logs | Either site writes to its nginx error log |
| Nginx upstream failure | Loki nginx error logs | nginx logs upstream connection/timeout failures |
| Nginx 5xx spike | Loki nginx JSON access logs | More than 3 5xx responses per vhost in 5 minutes |
| Nginx scanner burst | Loki nginx JSON access logs | One IP sends more than 300 common scanner/probe requests to one vhost in 5 minutes, sustained for 5 minutes |
| Auth/admin suspicious response | Loki nginx JSON access logs | Any 401, 403, or 429 on app auth/admin paths |
| Nginx 429 burst | Loki nginx JSON access logs | One IP receives more than 5 rate-limit responses from one vhost in 5 minutes |
| Host root disk free space low | Prometheus node_exporter | `/` free space stays below 15% for 10 minutes |

Scanner alerts include the source IP in the alert labels/description and add
lookup links for Shodan, Censys Search, and AbuseIPDB. No external enrichment API
is called by Grafana.

## Dashboard

The **System Overview** dashboard is auto-provisioned from `dashboards/overview.json`. `dashboards/sanakenno.json` is also provisioned here because Sanakenno runs in separate containers on the same NUC and writes to this shared Loki instance.

| Section | Source | Data |
|---------|--------|------|
| CPU / Memory / Disk gauges | Prometheus | node_exporter metrics |
| CPU & Memory over time | Prometheus | node_exporter metrics |
| Network I/O | Prometheus | node_exporter metrics |
| Disk I/O | Prometheus | node_exporter metrics |
| Filesystem free space | Prometheus | node_exporter metrics |
| Nginx traffic | Loki | nginx access/error logs |
| Application errors/warnings | Loki | Flask structured JSON logs (all exception handlers log via structlog) |
| Security events | Loki | Failed logins (Flask, SSH, Grafana) |

## Configuration

| File | Purpose |
|------|---------|
| `loki-config.yaml` | Loki storage, retention (14d), compaction settings |
| `alloy-config.alloy` | Log scrape targets and label configuration |
| `prometheus.yml` | Scrape config for node_exporter (30s interval) |
| `grafana-datasources.yaml` | Loki + Prometheus datasource provisioning |
| `grafana-dashboards.yaml` | Dashboard auto-provisioning from JSON files |
| `render-grafana-alerting.sh` | Copies Grafana provisioning files into `/tmp/grafana-provisioning` and renders the Telegram chat id placeholder |
| `alerting/contact-points.yaml` | Telegram contact point provisioning |
| `alerting/notification-policies.yaml` | Grafana notification routing |
| `alerting/nginx-alerts.yaml` | Loki-backed shared nginx/security alert rules |
| `alerting/system-alerts.yaml` | Prometheus-backed host alert rules |
| `dashboards/overview.json` | System Overview dashboard definition |
| `dashboards/sanakenno.json` | Shared Sanakenno traffic and application log dashboard |

## Nginx JSON Logs

`server/nginx-observability.conf` defines the shared `kontissa_json` access-log
format. The live file must be installed as
`/etc/nginx/conf.d/00-observability.conf`, before the vhost files that reference
the format. Both `erez.ac.conf` and `sanakenno.fi.conf` write JSON access logs
with fields such as `host`, `remote_addr`, `request_uri`, `status`,
`upstream_status`, and `user_agent`.

Grafana log panels still display these as normal log lines. Loki queries can add
`| json` to parse the fields for filters, grouping, tables, and alerts. Alert
queries extract the JSON `host` field as `vhost` so it does not collide with the
Alloy stream label `host=nuc`.

## Resource Budget

| Service | Memory | CPU |
|---------|--------|-----|
| Loki | 256 MB | — |
| Alloy | 128 MB | — |
| Prometheus | 128 MB | 0.25 |
| Grafana | 256 MB | 0.5 |
| node_exporter | ~15 MB | negligible |
| **Total** | **~783 MB** | **0.75 cores** |

## Troubleshooting

```bash
# Check if Prometheus can scrape node_exporter
curl -s localhost:9090/api/v1/targets | python3 -c "
import sys, json
t = json.load(sys.stdin)['data']['activeTargets'][0]
print(t['health'], t.get('lastError', ''))
"

# Check Loki health
docker compose logs loki --tail 10

# Check Grafana startup
docker compose logs grafana --tail 10

# Reset Grafana (fixes provisioning conflicts after version changes)
docker compose down grafana
docker volume rm web_kontissa_grafana_data
docker compose up -d
```
