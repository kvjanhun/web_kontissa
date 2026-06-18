#!/bin/sh
set -eu

SOURCE_DIR="/etc/grafana/provisioning/alerting-source"
TARGET_DIR="/tmp/grafana-provisioning/alerting"

mkdir -p "$TARGET_DIR"
cp "$SOURCE_DIR"/*.yaml "$TARGET_DIR"/

sed -i "s/__TELEGRAM_CHAT_ID__/${TELEGRAM_CHAT_ID}/g" "$TARGET_DIR/contact-points.yaml"

exec /run.sh
