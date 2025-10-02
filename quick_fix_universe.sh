set -euo pipefail
cd ~/nova-bot

echo "== 1) Service EnvironmentFile =="
systemctl --user show nova-engine-ultra.service -p EnvironmentFile

echo "== 2) .env (kjerneverdier) =="
grep -E '^(EXCHANGE|QUOTE|TOP_N|MIN_VOL_USD|SCAN_LIMIT|LOOP_DELAY|STRAT_SET|ULTRA_METRICS_PORT)=' .env || true

echo "== 3) Nudge .env til sikre univers-verdier =="
sed -i 's/^MIN_VOL_USD=.*/MIN_VOL_USD=1000/' .env
sed -i 's/^TOP_N=.*/TOP_N=300/' .env
sed -i 's/^SCAN_LIMIT=.*/SCAN_LIMIT=150/' .env

echo "== 4) Restart engine =="
systemctl --user restart nova-engine-ultra.service
sleep 10

echo "== 5) Metrics (up/universe) =="
curl -s localhost:9124/metrics | grep -E '^novax_ultra_(up|universe_size)'

if curl -s localhost:9124/metrics | grep -q '^novax_ultra_universe_size 0'; then
  echo "== 6) Manual universe probe (samme kodebase) =="
  PYTHONPATH=$PWD .venv/bin/python - <<'PY'
from nova.engine.exchanges import make_clients, load_universe
c = make_clients(['binance'])
u = load_universe(c, quote='USDT', top_n=300, min_vol_usd=1000)
print("manual_universe_len=", len(u), "sample=", u[:8])
PY

  echo "== 7) Siste ultra-logger (universe-linjer) =="
  journalctl --user -u nova-engine-ultra.service -n 120 --no-pager | grep -E '\[ultra\]|universe|metrics_port' || true

  echo "== 8) Sjekk om flere prosesser kjører =="
  pgrep -af nova | xargs -r ps -fp
fi

echo "== 9) Strategier/trades nå =="
curl -s localhost:9124/metrics | grep -E '^novax_ultra_(strategy_enabled|strategy_signals_total|trades_total|pnl_total|pnl_unrealized|equity)'
