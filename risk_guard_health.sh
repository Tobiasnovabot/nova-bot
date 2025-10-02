#!/usr/bin/env bash
set -euo pipefail
echo "== Risk Guard Health =="
systemctl --no-pager status novax-risk-guard.service | sed -n '1,12p'
echo
echo "-- Last 40 lines --"
sudo journalctl -u novax-risk-guard.service -n 40 --no-pager
echo
echo "-- Guard state --"
STATE="${NOVA_HOME:-/home/nova/nova-bot}a/data/config/risk_guard_state.json"
STATE="${NOVA_HOME:-/home/nova/nova-bot}/data/config/risk_guard_state.json"
if [ -f "$STATE" ]; then
  cat "$STATE"
else
  echo "(no trips)"
fi