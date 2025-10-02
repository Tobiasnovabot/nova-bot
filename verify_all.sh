# ===== verify_all.sh =====
set -euo pipefail
cd ~/nova-bot

echo "== A) Service & univers =="
curl -s localhost:9124/metrics | grep -E '^novax_ultra_(up|universe_size)'

echo "== B) Strategier enablet =="
curl -s localhost:9124/metrics | grep -E '^novax_ultra_strategy_enabled'

echo "== C) API sanity =="
echo -n "pairs: "; curl -s http://127.0.0.1:8008/pairs | jq 'length' || echo "NA"
curl -s http://127.0.0.1:8008/status | jq .

echo "== D) Signals/Trades nå =="
m="$(curl -s localhost:9124/metrics)"
echo "$m" | grep -E '^novax_ultra_strategy_signals_total' || true
echo "$m" | grep -E '^novax_ultra_trades_total' || true
echo "$m" | grep -E '^novax_ultra_(pnl_total|pnl_unrealized|equity)$' || true

SIG_CNT="$(echo "$m" | grep -c '^novax_ultra_strategy_signals_total' || true)"
TRD_CNT="$(echo "$m" | grep -c '^novax_ultra_trades_total' || true)"

if [ "${SIG_CNT:-0}" -eq 0 ] || [ "${TRD_CNT:-0}" -eq 0 ]; then
  echo "== E) Ingen bevegelse -> kort sanity-test =="
  mkdir -p nova/engine/strategies
  cat > nova/engine/strategies/sanity.py <<'PY'
_n = 0
def signal(symbol, price, broker):
    global _n
    _n += 1
    return 1 if _n % 2 else -1
PY

  # midlertidig bytt til sanity
  sed -i 's/^STRAT_SET=.*/STRAT_SET=sanity/' .env
  find nova -name '*.pyc' -delete || true
  find nova -type d -name '__pycache__' -exec rm -rf {} + || true
  mkdir -p runtime; rm -f runtime/trades.jsonl; echo '{"equity":1000.0}' > runtime/equity.json

  systemctl --user restart nova-engine-ultra.service
  sleep 8

  echo "== F) Bekreft økende signals/trades (sanity) =="
  for i in 1 2 3 4; do
    m="$(curl -s localhost:9124/metrics)"
    echo "$m" | grep -E '^novax_ultra_strategy_signals_total' || true
    echo "$m" | grep -E '^novax_ultra_trades_total' || true
    sleep 3
  done

  echo "== G) Tilbake til momentum,meanrev =="
  sed -i 's/^STRAT_SET=.*/STRAT_SET=momentum,meanrev/' .env
  systemctl --user restart nova-engine-ultra.service
  sleep 8
fi

echo "== H) Endelig status =="
curl -s localhost:9124/metrics | grep -E '^novax_ultra_(up|universe_size|strategy_enabled)'
curl -s localhost:9124/metrics | grep -E '^novax_ultra_(strategy_signals_total|trades_total|pnl_total|pnl_unrealized|equity)$' || true

echo "== I) Siste trades =="
tail -n 20 runtime/trades.jsonl || echo "Ingen trades logget (enda)"
# ===== /verify_all.sh =====
