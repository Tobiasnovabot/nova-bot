#!/usr/bin/env bash
set -euo pipefail

echo "== 1) Nullstiller gamle trades =="
cp runtime/trades.jsonl runtime/trades.jsonl.bak.$(date +%s) 2>/dev/null || true
: > runtime/trades.jsonl

echo "== 2) Restart ultra-runner =="
systemctl --user reset-failed nova-engine-ultra.service || true
systemctl --user restart nova-engine-ultra.service
sleep 5

echo "== 3) Aktiverer strategier =="
curl -s -X POST http://127.0.0.1:8008/strategy/momentum/enable | jq .
curl -s -X POST http://127.0.0.1:8008/strategy/meanrev/enable | jq .

echo "== 4) Sjekker hvilke strategier som er aktivert =="
curl -s http://127.0.0.1:8008/strategies | jq .

echo "== 5) Starter overvåking =="
echo "   - Trades logges live fra runtime/trades.jsonl"
echo "   - Metrics for trades_total overvåkes hvert 10. sekund"
echo "Trykk Ctrl+C for å stoppe"

# Kjør to monitorer i parallelle vinduer
( tail -f runtime/trades.jsonl & )
watch -n 10 "curl -s localhost:9124/metrics | grep novax_ultra_trades_total"
