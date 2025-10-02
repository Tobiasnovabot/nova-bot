#!/usr/bin/env bash
set -euo pipefail

echo "== 1) Nullstiller trades og equity =="
rm -f runtime/trades.jsonl
printf '{"equity": 1000.0}\n' > runtime/equity.json

echo "== 2) Restart ultra-runner i paper =="
systemctl --user restart nova-engine-ultra.service
sleep 5

echo "== 3) Aktiver strategier =="
curl -s -X POST http://127.0.0.1:8008/strategies/momentum/enable | jq .
curl -s -X POST http://127.0.0.1:8008/strategies/meanrev/enable | jq .

echo "== 4) Kjør en backtest for å garantere trades =="
curl -s -X POST \
  "http://127.0.0.1:8008/backtest/run?symbol=BTC/USDT&exchange=binance&timeframe=15m&days=1&strategy=momentum" | jq .

echo "== 5) Sjekk siste trades i runtime/trades.jsonl =="
tail -n 10 runtime/trades.jsonl || echo "Ingen trades logget!"

echo "== 6) Hent trades_total fra Prometheus metrics =="
curl -s localhost:9124/metrics | grep novax_ultra_trades_total

echo "== 7) Hent equity og PnL =="
curl -s localhost:9124/metrics | grep -E 'novax_ultra_equity|novax_ultra_pnl'
