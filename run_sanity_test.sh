#!/usr/bin/env bash
set -euo pipefail
cd ~/nova-bot

echo "== 0) Forbered runtime =="
mkdir -p runtime nova/engine/strategies
printf '{"equity": 1000.0}\n' > runtime/equity.json
: > runtime/trades.jsonl || true

echo "== 1) sanity-strategi som alltid gir signal =="
cat > nova/engine/strategies/sanity.py <<'PY'
# sanity.py – enkel verifikasjon
import random
def signal(symbol, price, broker):
    return 1 if random.random() < 0.5 else -1
PY

echo "== 2) Sett STRAT_SET=sanity og LOOP_DELAY=2 i .env =="
grep -q '^STRAT_SET=' .env && sed -i 's/^STRAT_SET=.*/STRAT_SET=sanity/' .env || echo 'STRAT_SET=sanity' >> .env
grep -q '^LOOP_DELAY=' .env && sed -i 's/^LOOP_DELAY=.*/LOOP_DELAY=2/' .env || echo 'LOOP_DELAY=2' >> .env

echo "== 3) Sørg for auto-exec i ultra_runner når signal != 0 =="
if ! grep -q 'auto-exec paper trade (patched)' nova/engine/ultra_runner.py; then
  tmp=$(mktemp)
  awk '
    {print}
    /inc_strategy_signal\(name\)/ && !p {
      print "                        # auto-exec paper trade (patched)"
      print "                        side = \"buy\" if sig > 0 else \"sell\""
      print "                        try:"
      print "                            broker.execute(sym, side, 0.001, price)"
      print "                        except Exception as e:"
      print "                            m_err(); alert(\"broker_error\", {\"sym\": sym, \"err\": str(e)})"
      p=1
    }
  ' nova/engine/ultra_runner.py > "$tmp" && mv "$tmp" nova/engine/ultra_runner.py
fi

echo "== 4) Rens pycache =="
find nova -name '*.pyc' -delete || true
find nova -type d -name '__pycache__' -exec rm -rf {} + || true

echo "== 5) Restart ultra-runner (paper) =="
systemctl --user restart nova-engine-ultra.service
sleep 8

echo "== 6) Metrikker =="
curl -s localhost:9124/metrics | grep -E 'novax_ultra_(up|universe_size|strategy_signals_total|trades_total|pnl_total|pnl_unrealized|equity)' || true

echo "== 7) Siste trades (paper) =="
tail -n 10 runtime/trades.jsonl || echo "Ingen trades logget ennå"

echo
echo "Tips:"
echo "watch -n 5 'curl -s localhost:9124/metrics | grep -E \"novax_ultra_(strategy_signals_total|trades_total|pnl_total|pnl_unrealized)\"'"
echo "tail -f runtime/trades.jsonl"
