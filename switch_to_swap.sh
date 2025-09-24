#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}

sed -i 's/^WATCH_MARKET=.*/WATCH_MARKET=swap/' .env || true
grep -q '^WATCH_MARKET=' .env || echo 'WATCH_MARKET=swap' >> .env

python3 - <<'PY'
import json, pathlib
p=pathlib.Path('data/state.json'); s={}
if p.exists():
    try: s=json.loads(p.read_text() or "{}")
    except Exception as e:
s={}
s["watch"]=[]  # tving AUTO_USDT
s["universe_cache"]={"ts":0,"type":"swap","symbols":[]}
p.write_text(json.dumps(s,separators=(",",":")))
print("Byttet til AUTO_USDT swap; cache tømt.")
PY

sudo systemctl restart novax.service

echo
echo "==> Kjør self-check:"
echo "   ~/nova-bot/selfcheck_auto_usdt.sh"