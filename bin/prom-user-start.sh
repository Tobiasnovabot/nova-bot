#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p _data/tsdb
nohup /usr/bin/prometheus \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path="$PWD/_data/tsdb" \
  --web.listen-address=127.0.0.1:19090 \
  > /tmp/prom-user.out 2>&1 & echo $! > /tmp/prom-user.pid
echo "USER Prometheus -> 19090 (pid $(cat /tmp/prom-user.pid))"