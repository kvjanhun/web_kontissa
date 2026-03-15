# Observability Stack

Logging and hardware monitoring for erez.ac, running on a self-hosted Intel NUC.

## Components

- **Grafana** — Dashboard UI, accessible at `https://erez.ac/logs/`
- **Loki** — Log aggregation (14-day retention)
- **Promtail** — Log collection from nginx, systemd journal, and Grafana
- **Prometheus** — Metrics storage (14-day retention, 500MB cap)
- **node_exporter** — Host hardware metrics (CPU, memory, disk, network)

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

## Dashboard

The **System Overview** dashboard is auto-provisioned from `dashboards/overview.json`.

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
| `promtail-config.yaml` | Log scrape targets and label configuration |
| `prometheus.yml` | Scrape config for node_exporter (30s interval) |
| `grafana-datasources.yaml` | Loki + Prometheus datasource provisioning |
| `grafana-dashboards.yaml` | Dashboard auto-provisioning from JSON files |
| `dashboards/overview.json` | System Overview dashboard definition |

## Resource Budget

| Service | Memory | CPU |
|---------|--------|-----|
| Loki | 256 MB | — |
| Promtail | 128 MB | — |
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
