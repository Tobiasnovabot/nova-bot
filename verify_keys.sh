#!/usr/bin/env bash
set -euo pipefail

KEYS=~/.config/novax/keys.yml
SERVICE=nova-engine-ultra.service

[[ -f "$KEYS" ]] || { echo "❌ Fant ikke $KEYS"; exit 1; }
printf "🔐 Bruker %s (perm: " "$KEYS"; stat -c '%a' "$KEYS"; printf ")\n"

# Maskert visning av nøkler (kun start/slutt-tegn)
python3 - <<'PY'
import os, yaml, textwrap, pathlib, sys
p = pathlib.Path(os.path.expanduser("~/.config/novax/keys.yml"))
try:
    d = yaml.safe_load(p.read_text())
except Exception as e:
    print(f"❌ YAML-feil i {p}: {e}")
    sys.exit(2)
def mask(v):
    if not isinstance(v, str): return "<?>"
    if len(v)<=8: return "*"*len(v)
    return v[:4]+"…" + v[-4:]
for ex in ("binance","okx"):
    if ex in d:
        row = d[ex]
        print(f"  [{ex}] apiKey={mask(row.get('apiKey',''))}  secret={mask(row.get('secret',''))}  pass={mask(row.get('password',''))}")
print("✅ YAML lastet.")
PY

# ccxt helsesjekk (privat endepunkt)
python3 - <<'PY'
import sys, yaml, os
try:
    import ccxt
except Exception as e:
    print("❌ ccxt ikke installert i miljøet. Installer med: pip install ccxt")
    sys.exit(3)

with open(os.path.expanduser("~/.config/novax/keys.yml")) as f:
    keys = yaml.safe_load(f)

ok_all = True

def test_binance(k):
    ex = ccxt.binance({
        "apiKey": k["apiKey"],
        "secret": k["secret"],
        "enableRateLimit": True,
        "options": {"defaultType": "spot"},
    })
    # privat kall bekrefter signering
    ex.fetch_balance(params={"recvWindow": 5000})

def test_okx(k):
    ex = ccxt.okx({
        "apiKey": k["apiKey"],
        "secret": k["secret"],
        "password": k.get("password",""),
        "enableRateLimit": True,
    })
    ex.fetch_balance()

for name, fn in (("binance", test_binance), ("okx", test_okx)):
    if name not in keys: 
        print(f"ℹ️  {name}: ikke konfigurert i keys.yml")
        continue
    try:
        fn(keys[name])
        print(f"✅ {name}: privat API OK (fetch_balance)")
    except Exception as e:
        ok_all = False
        print(f"❌ {name}: FEIL i privat API – {type(e).__name__}: {e}")

sys.exit(0 if ok_all else 4)
PY

echo "🔄 Restart service…"
systemctl --user restart "$SERVICE"
sleep 6

echo "📈 Universe & keys i logg:"
journalctl --user -u "$SERVICE" -n 80 --no-pager | grep -E '^\[keys\]|\[universe\]|params|metrics_port' || true

echo "📊 Metrics:"
curl -s localhost:9124/metrics | grep -E '^novax_ultra_(up|universe_size|strategy_enabled)' || true
