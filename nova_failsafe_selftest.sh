#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}

EQ=data/equity.json
ST=data/state.json

mkdir -p data
# lag start-state
python3 - <<'PY'
import json, pathlib
p=pathlib.Path('data/state.json')
s={"mode":"paper","equity_usd":1000.0,"bot_enabled":True,"risk_level":7,"positions":{},"watch":[]}
p.write_text(json.dumps(s,separators=(",",":")))
pathlib.Path('data/equity.json').write_text(json.dumps([{"ts":0,"equity_usd":1000.0}],separators=(",",":")))
print("INIT state=",s)
PY

echo "== baseline =="
./nova_failsafe.sh || true
jq -c '{bot_enabled:.bot_enabled,risk_level:.risk_level,equity_usd:.equity_usd}' data/state.json || cat data/state.json
tail -n 1 data/failsafe_state.json 2>/dev/null || true

echo "== simuler 5% dd (ingen tiltak) =="
python3 - <<'PY'
import json, pathlib
eq=pathlib.Path('data/equity.json')
a=json.loads(eq.read_text() or "[]")
a.append({"ts":1,"equity_usd":950.0})
eq.write_text(json.dumps(a,separators=(",",":")))
PY
./nova_failsafe.sh || true
jq -c '{bot_enabled:.bot_enabled,risk_level:.risk_level,equity_usd:.equity_usd}' data/state.json

echo "== simuler 9% dd (de-risk) =="
python3 - <<'PY'
import json, pathlib
eq=pathlib.Path('data/equity.json')
a=json.loads(eq.read_text() or "[]")
a.append({"ts":2,"equity_usd":910.0})
eq.write_text(json.dumps(a,separators=(",",":")))
PY
./nova_failsafe.sh || true
jq -c '{bot_enabled:.bot_enabled,risk_level:.risk_level,equity_usd:.equity_usd}' data/state.json

echo "== simuler 15% dd (pause bot) =="
python3 - <<'PY'
import json, pathlib
eq=pathlib.Path('data/equity.json')
a=json.loads(eq.read_text() or "[]")
a.append({"ts":3,"equity_usd":850.0})
eq.write_text(json.dumps(a,separators=(",",":")))
PY
./nova_failsafe.sh || true
jq -c '{bot_enabled:.bot_enabled,risk_level:.risk_level,equity_usd:.equity_usd}' data/state.json

echo "== simuler kill-switch (equity under min) =="
python3 - <<'PY'
import json, pathlib, os
min_eq=float(os.getenv("KILL_SWITCH_EQUITY_MIN_USD","300"))
eq=pathlib.Path('data/equity.json')
a=json.loads(eq.read_text() or "[]")
a.append({"ts":4,"equity_usd":min_eq-1})
eq.write_text(json.dumps(a,separators=(",",":")))
PY
./nova_failsafe.sh || true
jq -c '{bot_enabled:.bot_enabled,risk_level:.risk_level,equity_usd:.equity_usd}' data/state.json