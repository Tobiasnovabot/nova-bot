#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

LOG="runtime/longrun_$(date +%Y%m%d_%H%M%S).log"
echo "== Longrun log -> $LOG ==" | tee -a "$LOG"
echo "Started: $(date)" | tee -a "$LOG"

# header
{
  echo "env: STRAT_SET=$(grep -E '^STRAT_SET=' .env | cut -d= -f2)  LOOP_DELAY=$(grep -E '^LOOP_DELAY=' .env | cut -d= -f2)"
  echo "pairs: $(curl -s http://127.0.0.1:8008/pairs | jq 'length' 2>/dev/null || echo '?')"
} | tee -a "$LOG"

for i in {1..120}; do
  echo "==== $(date) ====" | tee -a "$LOG"
  curl -s localhost:9124/metrics | grep -E '^novax_ultra_(up|universe_size|equity|pnl_total|pnl_unrealized|strategy_signals_total|trades_total)' | tee -a "$LOG"
  tail -n 5 runtime/trades.jsonl 2>/dev/null | tee -a "$LOG" || true
  sleep 60
done

echo "Finished: $(date)" | tee -a "$LOG"
