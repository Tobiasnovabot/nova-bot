#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}

echo "== ENV =="
PID=$(pgrep -f 'nova.engine.run' | head -1 || true)
if [[ -n "${PID:-}" ]]; then
  sudo tr '\0' '\n' </proc/$PID/environ | grep -E '^(WATCHLIST|WATCH_MARKET|TOP_N|WATCH_TOP_N|NOVA_HOME)=' || true
else
  echo "WARN: fant ikke engine-prosess" >&2
fi

echo
echo "== ENGINE LOG =="
sudo journalctl -u novax.service -n 80 --no-pager | grep -E '\[engine\]|watchN=' || true

echo
echo "== CACHE (state.json) =="
python3 - <<'PY'
import json, pathlib
p=pathlib.Path('data/state.json')
try:
  s=json.loads(p.read_text() or "{}")
except Exception as e:
  print("FEIL: kan ikke lese state.json:", e); raise
uc=s.get("universe_cache",{})
print("cache_type:", uc.get("type"), "count:", len(uc.get("symbols",[])))
print("first 15:", ", ".join(uc.get("symbols",[])[:15]))
PY