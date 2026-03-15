#!/bin/bash
# Backs up server configuration files to Backblaze B2.
# Requires rclone configured with a remote named "b2".
# Schedule via cron: 0 4 * * * /home/kvjanhun/scripts/backup-configs.sh
set -e

BACKUP_DIR="/tmp/server-config-backup"
rm -rf "$BACKUP_DIR"
mkdir -p "$BACKUP_DIR/nginx" "$BACKUP_DIR/systemd"

# Nginx
cp -r /etc/nginx/conf.d/* "$BACKUP_DIR/nginx/" 2>/dev/null
cp /etc/nginx/nginx.conf "$BACKUP_DIR/nginx/" 2>/dev/null

# Crontab
crontab -l > "$BACKUP_DIR/crontab.txt" 2>/dev/null

# Systemd custom services
cp /etc/systemd/system/webhook.service "$BACKUP_DIR/systemd/" 2>/dev/null
cp /etc/systemd/system/node_exporter.service "$BACKUP_DIR/systemd/" 2>/dev/null

# iptables
iptables-save > "$BACKUP_DIR/iptables.rules" 2>/dev/null

# Sync to B2
rclone sync "$BACKUP_DIR" b2:erezac-db-backup/server-configs/

rm -rf "$BACKUP_DIR"
