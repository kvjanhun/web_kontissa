#!/bin/bash
# Pull the AbuseIPDB blocklist into an ipset and DROP those IPs at the host
# firewall (INPUT), so known-bad actors are blocked before they reach nginx.
#
# Companion to fail2ban: fail2ban *reports* our bans to AbuseIPDB, this script
# *consumes* AbuseIPDB's aggregated, confidence-scored blocklist. Public traffic
# to nginx (80/443) is filtered in the INPUT chain, and app container ports are
# 127.0.0.1-only, so an INPUT DROP blocks listed IPs at the edge.
#
# Requires: curl, ipset, iptables. ABUSEIPDB_API_KEY in the env file (shared
# with the fail2ban abuseipdb action and the Telegram alert scripts).
# Runs as root (ipset/iptables) via cron:
#   30 4 * * * /home/kvjanhun/scripts/abuseipdb-blocklist.sh
#
# Deployed to: /home/kvjanhun/scripts/abuseipdb-blocklist.sh
set -euo pipefail

ENV_FILE="${ABUSEIPDB_ENV_FILE:-/home/kvjanhun/.config/site-alerts.env}"
# shellcheck disable=SC1090
[ -f "$ENV_FILE" ] && . "$ENV_FILE"

: "${ABUSEIPDB_API_KEY:?ABUSEIPDB_API_KEY not set (add it to $ENV_FILE)}"

# High confidence only; keeps the set small and within the free-tier blacklist
# quota with a single daily pull. Verify your AbuseIPDB plan permits the
# blacklist endpoint and what result cap applies.
CONFIDENCE="${ABUSEIPDB_CONFIDENCE_MINIMUM:-90}"
SET_NAME="abuseipdb"
TMP_SET="${SET_NAME}-tmp"
IPSET_PERSIST="${ABUSEIPDB_IPSET_PERSIST:-/etc/ipset.conf}"

LIST_FILE="$(mktemp)"
trap 'rm -f "$LIST_FILE"' EXIT

# 1. Fetch the blocklist (one IP per line).
curl -fsSG https://api.abuseipdb.com/api/v2/blacklist \
  --data-urlencode "confidenceMinimum=${CONFIDENCE}" \
  -H "Key: ${ABUSEIPDB_API_KEY}" \
  -H "Accept: text/plain" \
  -o "$LIST_FILE"

# Refuse to wipe the live set on an empty/garbled response.
if [ ! -s "$LIST_FILE" ]; then
  echo "abuseipdb-blocklist: empty response, leaving existing set untouched" >&2
  exit 1
fi

# 2. Build a temp set and swap it in atomically (no flush gap where IPs leak in).
ipset create "$SET_NAME" hash:ip family inet hashsize 4096 maxelem 262144 -exist
ipset create "$TMP_SET"  hash:ip family inet hashsize 4096 maxelem 262144 -exist
ipset flush "$TMP_SET"

while IFS= read -r ip; do
  case "$ip" in
    ''|\#*) continue ;;   # blank / comment
    *:*)    continue ;;   # IPv6 — skip (inet set; revisit with a v6 set later)
  esac
  ipset add "$TMP_SET" "$ip" -exist
done < "$LIST_FILE"

ipset swap "$TMP_SET" "$SET_NAME"
ipset destroy "$TMP_SET"

# 3. Ensure a single DROP rule exists early in INPUT (idempotent).
if ! iptables -C INPUT -m set --match-set "$SET_NAME" src -j DROP 2>/dev/null; then
  iptables -I INPUT 1 -m set --match-set "$SET_NAME" src -j DROP
fi

# 4. Persist for reboot (paired with an ipset-restore-on-boot unit; see
#    server/fail2ban/README.md).
ipset save > "$IPSET_PERSIST"

COUNT="$(ipset list "$SET_NAME" | grep -c '^[0-9]' || true)"
echo "abuseipdb-blocklist: loaded ${COUNT} IPv4 addresses (confidenceMinimum=${CONFIDENCE})"
