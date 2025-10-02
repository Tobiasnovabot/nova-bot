#!/usr/bin/env bash
set -euo pipefail
echo "== Event Bus Health =="
systemctl status novax-event-tap.service --no-pager | sed -n '1,15p'
echo
echo "-- Siste 40 logglinjer (event tap) --"
sudo journalctl -u novax-event-tap.service -n 40 --no-pager
echo
echo "-- Siste 10 events.jsonl --"
tail -n 10 ${NOVA_HOME:-/home/nova/nova-bot}/data/logs/events.jsonl || true
echo
echo "-- trades.json (antall + siste) --"
python3 - <<'PY'
import json, pathlib
p=pathlib.Path('${NOVA_HOME:-/home/nova/nova-bot}/data/trades.json')
try:
    a=json.loads(p.read_text() or "[]")
    print("trades:", len(a))
    if a:
        last=a[-1]; keep={k:last.get(k) for k in ("ts","sym","side","qty","price","pnl","status")}
        print("last:", keep)
except Exception as e:
    print("trades: (ingen)", e)
PY