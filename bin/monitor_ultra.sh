#!/usr/bin/env bash
set -euo pipefail
M=$(curl -s localhost:9124/metrics)
echo "== Service & univers =="
echo "$M" | grep -E '^novax_ultra_(up|universe_size)'
echo "== Strategier enablet =="
echo "$M" | grep -E '^novax_ultra_strategy_enabled' || true
echo "== Signals/Trades/PnL/Equity =="
echo "$M" | grep -E '^novax_ultra_(strategy_signals_total|trades_total|pnl_total|pnl_unrealized|equity)' || true
echo "== Siste trades =="
tail -n 10 runtime/trades.jsonl 2>/dev/null || echo "Ingen trades logget ennå"
