#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}

# Oppdater .env for maks læring
sed -i '/^MODE=/d;/^WATCHLIST=/d;/^TOP_N=/d;/^WATCH_TOP_N=/d;/^ENGINE_LOOP_SEC=/d' .env
cat >> .env <<EOF
MODE=paper
WATCHLIST=AUTO_USDT
TOP_N=300
WATCH_TOP_N=300
ENGINE_LOOP_SEC=10
EOF

# Nullstill universe-cache så AUTO_USDT regenereres
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("data/state.json")
p.parent.mkdir(parents=True, exist_ok=True)
s = {}
if p.exists():
    try: s=json.loads(p.read_text() or "{}")
    except Exception as e:
s={}
s.setdefault("universe_cache", {"ts":0,"symbols":[]})
s["universe_cache"]["ts"]=0
s["universe_cache"]["symbols"]=[]
p.write_text(json.dumps(s, separators=(",",":")))
PY

# Restart og bekreft
sudo systemctl restart novax.service

# Telegram ping (hopp over hvis TG_KEY/TG_CHAT mangler)
bash -lc 'set -a; source ./.env; set +a; \
  if [[ -n "${TG_KEY:-}" && -n "${TG_CHAT:-}" ]]; then \
    curl -s "https://api.telegram.org/bot${TG_KEY}/sendMessage" \
      -d chat_id="${TG_CHAT}" \
      -d text="NovaX: *LÆRINGSMODUS* aktivert (paper) – AUTO_USDT, TOP_N=300, loop=10s" >/dev/null; \
  fi'

echo "==> Live logg (Ctrl+C for å avslutte). Se etter: watchN=300"
sudo journalctl -u novax.service -f -n 50