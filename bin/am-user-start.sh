#!/usr/bin/env bash
set -euo pipefail
BIN="/usr/bin/prometheus-alertmanager"; [ -x "$BIN" ] || BIN="/usr/bin/alertmanager"
exec nohup "$BIN" \
  --config.file=/etc/alertmanager/alertmanager.yml \
  --storage.path=/tmp/am-data \
  --web.listen-address=127.0.0.1:9097 \
  --cluster.listen-address=127.0.0.1:9098 \
  > /tmp/alertmanager.out 2>&1 &