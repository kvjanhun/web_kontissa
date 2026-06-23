# fail2ban + AbuseIPDB

Automated intrusion response for **erez.ac** and **sanakenno.fi**, both fronted by
the single host nginx on the Intel NUC. fail2ban watches the nginx JSON logs and the
systemd journal, bans abusive IPs at the host firewall, and reports them to AbuseIPDB.
A companion script consumes AbuseIPDB's blocklist to pre-emptively drop known-bad IPs.

This replaces manual triage: the Grafana scanner-burst / 429-burst alerts used to
*notify* you (with an AbuseIPDB lookup link to check by hand); fail2ban now *acts* and
*reports*, and those alerts are kept only as high-threshold backstops.

## Why it runs on the host (not in Docker)

nginx and sshd are host services, their logs are host files / journald, and the
firewall is host iptables. fail2ban needs all three, so it runs as a host systemd
service — same rationale as node_exporter. Bans go in the **INPUT** chain, which is
where public traffic to nginx (80/443) is filtered. App container ports bind to
`127.0.0.1` only, so an INPUT DROP blocks attackers before they reach nginx; Docker's
own `DOCKER-USER`/`FORWARD` chains are irrelevant here.

`remote_addr` in the `kontissa_json` access log is the real client IP (nginx is the
public TLS edge, no CDN/proxy in front), so the filters key on it directly with no
X-Forwarded-For trust problem.

## Files

| Repo file | Host path | Purpose |
|-----------|-----------|---------|
| `fail2ban.d/logging.conf` | `/etc/fail2ban/fail2ban.d/logging.conf` | `logtarget = SYSTEMD-JOURNAL` so bans flow to Loki/Grafana |
| `jail.d/kontissa.conf` | `/etc/fail2ban/jail.d/kontissa.conf` | All jails, `ignoreip`, `banaction`, AbuseIPDB categories |
| `filter.d/kontissa-nginx-probe.conf` | `/etc/fail2ban/filter.d/` | Scanner/probe paths (`.env`, `wp-`, `.php`, …) |
| `filter.d/kontissa-nginx-auth.conf` | `/etc/fail2ban/filter.d/` | 401/403 on `/api/auth\|login\|admin` |
| `filter.d/kontissa-nginx-429.conf` | `/etc/fail2ban/filter.d/` | 429 floods (excl. `/logs/`) |
| `action.d/abuseipdb.local.example` | *(template)* | Build `/etc/fail2ban/action.d/abuseipdb.local` from this with the real key |
| `../abuseipdb-blocklist.sh` | `/home/kvjanhun/scripts/abuseipdb-blocklist.sh` | Daily blocklist → ipset → INPUT DROP |

## Jails

| Jail | Bans when | bantime | AbuseIPDB cat |
|------|-----------|---------|---------------|
| `kontissa-nginx-probe` | 3 scanner-probe hits in 10m (excl. `/logs/`) | 1d (escalates to 1w) | 21 |
| `kontissa-nginx-auth` | 5× 401/403 on auth/admin in 10m | 1h | 18,21 |
| `kontissa-nginx-429` | 20× 429 in 5m (excl. `/logs/`) | 1h | 21 |
| `nginx-limit-req` | _disabled_ — its only zone is `grafana_limit` (the `/logs/` dashboard = you) | — | — |
| `sshd` | 4 SSH auth failures | 1h | — (see note) |
| `recidive` | banned 5× in a day | 1w | 18 |

All three web filters exclude the Grafana `/logs/` subpath, because Grafana legitimately
serves asset URLs containing `/plugins/`, `/vendor/`, and bursts that trip the
`grafana_limit` rate limit — none of which should ever be treated as an attack. Relying
on `ignoreip` is not enough here: your dashboard traffic can reach nginx as a non-LAN
address (remote access, or hairpin NAT presenting your public IP), so the *filters*
themselves must not match it.

`ignoreip` covers `127.0.0.1/8 ::1 172.16.0.0/12 <LAN_CIDR>` — the Docker bridges
(`172.16.0.0/12`) keep container health checks and the dog crawler from ever being
banned, and `<LAN_CIDR>` is your private LAN range. The server's own public IP is
deliberately omitted (it's dynamic, and the host never appears as `remote_addr` on a
filtered path). `sshd` rarely fires because SSH is firewall-restricted to the LAN, which
is in `ignoreip`; it's defense-in-depth only and intentionally has no AbuseIPDB report
(we don't report LAN IPs).

`bantime.increment` is on globally, so repeat offenders escalate (1h → 2h → … → 1w).

## Setup (one-time, on the NUC)

```bash
# 1. Install (EPEL provides fail2ban on RHEL). ipset is for the consume list.
sudo dnf install -y epel-release
sudo dnf install -y fail2ban ipset

# 2. Deploy the config (see server/README.md for the full scp block)
sudo scp server/fail2ban/fail2ban.d/logging.conf  kvjanhun@erez.ac:/etc/fail2ban/fail2ban.d/logging.conf
sudo scp server/fail2ban/jail.d/kontissa.conf      kvjanhun@erez.ac:/etc/fail2ban/jail.d/kontissa.conf
sudo scp server/fail2ban/filter.d/*.conf           kvjanhun@erez.ac:/etc/fail2ban/filter.d/

# 3. Fill the host-only <LAN_CIDR> placeholder in /etc/fail2ban/jail.d/kontissa.conf
#    with your private LAN range (e.g. a /24). No public IP — it's dynamic and
#    provides no real benefit here (see the ignoreip note below).

# 4. Verify the firewall backend BEFORE starting (see "Firewall backend" below).

# 5. AbuseIPDB key — add to the shared env file and create the host-only action:
echo 'ABUSEIPDB_API_KEY="<key>"' | sudo tee -a /home/kvjanhun/.config/site-alerts.env
sudo install -m 600 /dev/null /etc/fail2ban/action.d/abuseipdb.local
# edit it to hold the [Init] block from abuseipdb.local.example with the real key

# 6. Confirm the packaged AbuseIPDB action exists, then start fail2ban
test -f /etc/fail2ban/action.d/abuseipdb.conf
sudo systemctl enable --now fail2ban
fail2ban-client status

# 7. Consume script + cron (root)
sudo scp server/abuseipdb-blocklist.sh kvjanhun@erez.ac:/home/kvjanhun/scripts/abuseipdb-blocklist.sh
sudo chmod 755 /home/kvjanhun/scripts/abuseipdb-blocklist.sh
sudo /home/kvjanhun/scripts/abuseipdb-blocklist.sh   # first run
sudo crontab -e   # add:
#   @reboot     /home/kvjanhun/scripts/abuseipdb-blocklist.sh
#   30 4 * * *  /home/kvjanhun/scripts/abuseipdb-blocklist.sh
```

The `@reboot` cron rebuilds the ipset and re-adds the INPUT DROP after a reboot, which
sidesteps the iptables/ipset boot-ordering problem (a `-m set` rule can't load before
its set exists). `ipset save` to `/etc/ipset.conf` plus `systemctl enable ipset` is an
alternative, but `@reboot` is simpler and self-healing.

## Firewall backend (verify first!)

```bash
firewall-cmd --state 2>/dev/null   # "running" => firewalld is active
iptables --version                 # "(nf_tables)" vs "(legacy)"
```

- **firewalld running** → change `banaction`/`banaction_allports` in
  `jail.d/kontissa.conf` to `firewallcmd-ipset` so fail2ban doesn't fight firewalld.
- **raw iptables/nftables** (this host — it manages `iptables -I INPUT` directly and
  backs up `iptables-save`) → keep `iptables-multiport` / `iptables-allports`; they work
  through the `iptables-nft` shim. **Wrong choice = bans silently don't apply.**

## Verify

```bash
# Filters parse and capture <HOST> from the JSON logs (do this before trusting them):
fail2ban-regex /var/log/nginx/erez.ac.access.log /etc/fail2ban/filter.d/kontissa-nginx-probe.conf
fail2ban-regex /var/log/nginx/erez.ac.access.log /etc/fail2ban/filter.d/kontissa-nginx-auth.conf
fail2ban-regex /var/log/nginx/erez.ac.access.log /etc/fail2ban/filter.d/kontissa-nginx-429.conf

fail2ban-client status                       # all jails listed
fail2ban-client status kontissa-nginx-probe  # files watched + banned count

# Live ban test from a NON-ignored host:
#   curl https://erez.ac/wp-login.php   (repeat past maxretry)
# then confirm the ban + firewall rule + that AbuseIPDB got the report:
sudo iptables -L INPUT -n | grep -i drop
journalctl -u fail2ban.service --since "10 min ago" | grep -iE "ban|report"

# Consume list:
sudo /home/kvjanhun/scripts/abuseipdb-blocklist.sh
sudo ipset list abuseipdb | head
sudo iptables -L INPUT -n | grep match-set
```

Bans also appear in Grafana → System Overview → **Fail2ban Activity** panel (sourced
from the journal via Alloy → Loki). Routine bans are dashboard-only — no Telegram.

## Rollback / unblock

```bash
fail2ban-client set <jail> unbanip <ip>   # clear one ban
fail2ban-client unban <ip>                # clear across all jails
sudo systemctl stop fail2ban              # disable banning entirely
sudo iptables -D INPUT -m set --match-set abuseipdb src -j DROP   # drop the consume rule
sudo ipset destroy abuseipdb
```

Self-lockout risk is low: SSH is LAN-only and the LAN is in `ignoreip`, so fail2ban
can't lock you out of SSH; LAN/console access remains the recovery path.

## Notes / caveats

- **JSON-log filters**: the access log is JSON, not combined format, so the custom
  filters match JSON fields and set no line anchors (fail2ban strips the matched
  `datepattern` first). The `fail2ban-regex` dry-run is the source of truth that they
  work. Field order in `kontissa_json` is fixed, which keeps the regexes stable.
- **AbuseIPDB blacklist quota**: free accounts have a limited daily blacklist quota.
  One daily pull at `confidenceMinimum=90` stays well inside it and keeps the ipset
  small. Verify your plan permits the blacklist endpoint and its result cap.
- **AbuseIPDB privacy**: never report private IPs (covered by `ignoreip` + AbuseIPDB's
  own rejection) and keep the report comment generic — see `abuseipdb.local.example`.
- **IPv6**: the consume script handles IPv4 only (`hash:ip family inet`); it skips IPv6
  entries. Add a second set + `ip6tables` rule if IPv6 abuse becomes relevant.
