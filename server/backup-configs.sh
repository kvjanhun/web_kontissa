#!/bin/bash
# Backs up server configuration files to Backblaze B2.
# Requires rclone configured with a remote named "b2".
# Schedule via cron: 0 4 * * * /home/kvjanhun/scripts/backup-configs.sh
set -e

BACKUP_DIR="/tmp/server-config-backup"
rm -rf "$BACKUP_DIR"
mkdir -p "$BACKUP_DIR/nginx" "$BACKUP_DIR/systemd"

# Nginx
cp -r /etc/nginx/conf.d/* "$BACKUP_DIR/nginx/" 2>/dev/null || true
cp /etc/nginx/nginx.conf "$BACKUP_DIR/nginx/" 2>/dev/null || true

# Crontab (kvjanhun's, not root's)
crontab -u kvjanhun -l > "$BACKUP_DIR/crontab.txt" 2>/dev/null || true

# Systemd custom services
cp /etc/systemd/system/webhook.service "$BACKUP_DIR/systemd/" 2>/dev/null || true
cp /etc/systemd/system/node_exporter.service "$BACKUP_DIR/systemd/" 2>/dev/null || true

# iptables
iptables-save > "$BACKUP_DIR/iptables.rules" 2>/dev/null || true

# Sync to B2
rclone --config /home/kvjanhun/.config/rclone/rclone.conf sync "$BACKUP_DIR" b2:erezac-db-backup/server-configs/

rm -rf "$BACKUP_DIR"
