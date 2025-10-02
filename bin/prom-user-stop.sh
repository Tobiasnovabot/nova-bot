#!/usr/bin/env bash
set -euo pipefail
pkill -f 'web.listen-address=127.0.0.1:19090' || true
rm -f /tmp/prom-user.pid
echo "USER Prometheus stopped."