#!/usr/bin/env bash
set -euo pipefail
MAX="${1:-500}"
MIN="${2:-10}"
ALLOW="${3:-0}"
cat <<INI | sudo tee /etc/systemd/system/novax.service.d/notional.conf >/dev/null
[Service]
Environment=ORDER_MIN_NOTIONAL_USD=${MIN}
Environment=ORDER_MAX_NOTIONAL_USD=${MAX}
Environment=ALLOW_NOTIONAL_BREACH=${ALLOW}
INI
sudo systemctl daemon-reload
sudo systemctl restart novax.service || true
systemctl show novax.service -p Environment | tr ' ' '\n' | grep ORDER_