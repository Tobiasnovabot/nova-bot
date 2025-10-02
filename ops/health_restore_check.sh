#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}
echo "== HEALTH-CHECK (post-restore) =="

echo "-- systemd --"
systemctl is-active --quiet novax.service && echo "PASS: novax.service aktiv" || { echo "FAIL: novax.service"; exit 1; }

echo "-- .env --"
grep -E '^(EXCHANGE|MODE|WATCHLIST|TOP_N|NOVA_HOME|TG_)=' .env || true

echo "-- Binance ping --"
python3 - <<'PY'
import ccxt; ex=ccxt.binance(); t=ex.fetch_ticker('BTC/USDT'); print("PASS: ticker ok", t['last'])
PY

echo "-- data/ write --"
python3 - <<'PY'
from pathlib import Path; p=Path('data/_write_test'); p.write_text('ok'); print('PASS: wrote', p); p.unlink()
PY

echo "-- engine-log --"
sudo journalctl -u novax.service -n 30 --no-pager | sed -n '1,30p'
echo "== DONE =="