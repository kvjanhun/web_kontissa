#!/bin/sh
set -eu

SOURCE_ROOT="/etc/grafana/provisioning"
TARGET_ROOT="/tmp/grafana-provisioning"

mkdir -p "$TARGET_ROOT"/alerting "$TARGET_ROOT"/dashboards "$TARGET_ROOT"/datasources

cp "$SOURCE_ROOT"/alerting-source/*.yaml "$TARGET_ROOT"/alerting/
cp "$SOURCE_ROOT"/dashboards/*.yaml "$TARGET_ROOT"/dashboards/
cp "$SOURCE_ROOT"/datasources/*.yaml "$TARGET_ROOT"/datasources/

sed -i "s/__TELEGRAM_CHAT_ID__/${TELEGRAM_CHAT_ID}/g" "$TARGET_ROOT/alerting/contact-points.yaml"

exec /run.sh
