#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}
echo "== sizing quick test =="
source .venv/bin/activate
python - <<'PY'
from nova.tools.size_cli import fetch_ohlcv, last_price_from_ohlcv
from nova.risk.position_sizing import compute_size, atr_from_ohlcv
sym="BTC/USDT"; eq=10000.0; rl=5
o=fetch_ohlcv(sym,"1h",100)
atr=atr_from_ohlcv(o)
px=last_price_from_ohlcv(o)
S=compute_size(px, eq, rl, atr)
print("sizing:", {"sym":sym,"px":px,"atr":atr,**S})
PY

echo "== exposure guard simulation =="
python - <<'PY'
import json, pathlib, time
p=pathlib.Path('data/state.json'); p.parent.mkdir(exist_ok=True, parents=True)
s={"equity_usd":10000.0,"bot_enabled":True,"risk_level":5,
   "positions":{"BTC/USDT":{"qty":0.2,"price":50000},"ETH/USDT":{"qty":2,"price":2500}}}
p.write_text(json.dumps(s,separators=(",",":")))
print("state init:", s)
PY

./nova_exposure_guard.sh || true
python - <<'PY'
import json; print("post-guard state:", json.load(open('data/state.json')))
PY

echo "== breach test (oversize BTC) =="
python - <<'PY'
import json, pathlib
s=json.load(open('data/state.json'))
# simuler kraftig prisoppgang -> større eksponering
s["positions"]["BTC/USDT"]["price"]=80000
open('data/state.json','w').write(json.dumps(s,separators=(",",":")))
PY
./nova_exposure_guard.sh || true
python - <<'PY'
import json; st=json.load(open('data/state.json'))
print("post-breach state.bot_enabled:", st.get("bot_enabled"))
PY