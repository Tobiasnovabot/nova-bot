#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}

# --- sett AUTO_USDT + TOP_N=300 + raskere loop ---
sed -i '/^WATCHLIST=/d;/^TOP_N=/d;/^WATCH_TOP_N=/d;/^ENGINE_LOOP_SEC=/d' .env
cat >> .env <<EOF
WATCHLIST=AUTO_USDT
TOP_N=300
WATCH_TOP_N=300
ENGINE_LOOP_SEC=10
EOF

# --- nullstill universe-cache i state.json uten jq ---
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("data/state.json")
if p.exists():
    s = json.loads(p.read_text() or "{}")
    s.setdefault("universe_cache", {"ts":0,"symbols":[]})
    s["universe_cache"]["ts"] = 0
    s["universe_cache"]["symbols"] = []
    p.write_text(json.dumps(s, separators=(",",":")))
PY

# --- restart tjenesten (bot + tg kjører inne i engine) ---
sudo systemctl restart novax.service

echo "==> Live logg (Ctrl+C for å avslutte). Se etter: watchN=300"
sudo journalctl -u novax.service -f -n 50