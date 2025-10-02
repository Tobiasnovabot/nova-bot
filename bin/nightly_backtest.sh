#!/usr/bin/env bash
set -euo pipefail
API="http://127.0.0.1:8008/backtest/run"
SYM=("BTC/USDT" "ETH/USDT" "SOL/USDT" "BNB/USDT")
for s in "${SYM[@]}"; do
  for strat in momentum meanrev; do
    curl -s -X POST "$API?symbol=$(python3 - <<PY
s="$s"
print(s.replace("/", "%2F"))
PY
)&exchange=binance&timeframe=15m&days=7&strategy=$strat" >/dev/null || true
  done
done
echo "[nightly_backtest] done $(date)"
