#!/usr/bin/env bash
set -euo pipefail

STATE="data/state.json"

POS=$(jq -r '
  if (.positions|type)=="array" then (.positions|length)
  elif (.positions|type)=="object" then (to_entries|map(select(.value|tostring|test("^(closed|flat|0)$")|not))|length)
  else (.positions//0) end
' "$STATE" 2>/dev/null || echo 0)

TRADES=$(grep -m1 -A1 'novax_trades_closed_total' metrics/novax_trades.prom 2>/dev/null | tail -n1 | awk '{print $2+0}')

cat <<METRICS
# HELP novax_positions_open Current open positions
# TYPE novax_positions_open gauge
novax_positions_open $POS

# HELP novax_trades_closed_total Total closed trades
# TYPE novax_trades_closed_total counter
novax_trades_closed_total $TRADES
METRICS