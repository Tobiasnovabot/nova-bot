#!/usr/bin/env bash
set -euo pipefail
dur=$((60*120))              # 120 min
end=$((SECONDS+dur))
mkdir -p runtime
log="runtime/soak_metrics.log"
: > "$log"

trades_start=0
[ -f runtime/trades.jsonl ] && trades_start=$(wc -l < runtime/trades.jsonl || echo 0)

echo "Running soak for $dur seconds..."
while [ $SECONDS -lt $end ]; do
  ts=$(date -Is)
  curl -s localhost:9124/metrics | awk -v ts="$ts" '
    /novax_ultra_(universe_size|strategy_signals_total|trades_total|equity|pnl_)/ {print ts, $0}
  ' | tee -a "$log" >/dev/null
  sleep 30
done

echo "---- SUMMARY ----"
trades_end=0
[ -f runtime/trades.jsonl ] && trades_end=$(wc -l < runtime/trades.jsonl || echo 0)
echo "New trades during soak: $((trades_end - trades_start))"
echo "Last metrics snapshot:"
tail -n 20 "$log"
