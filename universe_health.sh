#!/usr/bin/env bash
set -euo pipefail
echo "== Universe Builder Health =="
systemctl status novax-universe-builder.timer --no-pager | sed -n '1,8p'
echo
systemctl status novax-universe-builder.service --no-pager | sed -n '1,12p'
echo
echo "-- Siste 50 linjer --"
sudo journalctl -u novax-universe-builder.service -n 50 --no-pager
echo
echo "-- Nåværende universe_cache --"
python3 - <<'PY'
import json, pathlib
p=pathlib.Path('data/state.json')
s=json.loads(p.read_text() or "{}")
u=s.get('universe_cache',{})
print("ts:", u.get("ts"))
print("count:", len(u.get("symbols",[])))
print("first 20:", ", ".join((u.get("symbols") or [])[:20]))
PY

# -- post-filter mot trading-børs + autofyll til TOP_N
if [ -x ./tools/universe_postfilter.py ]; then
  echo "[universe_health] postfilter..."
  python ./tools/universe_postfilter.py || true
  CNT=$(jq -r '.symbols|length' data/universe.json 2>/dev/null || echo 0)
  TARGET="${TOP_N:-300}"
  if [ "$CNT" -lt "$TARGET" ]; then
    MSG="Universe under mål etter filter: $CNT/$TARGET"
    [ -x ./alerts/trade_to_tg.sh ] && ./alerts/trade_to_tg.sh "$MSG" || echo "$MSG"
  fi
fi