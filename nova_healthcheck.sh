#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot} || { echo "FAIL: ${NOVA_HOME:-/home/nova/nova-bot} mangler"; exit 1; }

echo "== NovaX HEALTHCHECK =="
echo "Host: $(hostname)  User: $(whoami)  Uptime: $(uptime -p)"
echo

# 1) systemd-tjenesten
echo "== systemd =="
if systemctl is-active --quiet novax.service; then
  echo "PASS: novax.service er aktiv"
else
  echo "FAIL: novax.service er ikke aktiv"; systemctl status novax.service --no-pager || true
fi
echo

# 2) .env
echo "== .env =="
if [[ -f .env ]]; then
  grep -E '^(EXCHANGE|MODE|NOVA_HOME|WATCHLIST|TOP_N|WATCH_TOP_N|ENGINE_LOOP_SEC|TG_ON|TG_KEY|TG_CHAT)=' .env || true
else
  echo "FAIL: .env finnes ikke"
fi
echo

# 3) venv + pakker
echo "== venv/pakker =="
if [[ -x ./.venv/bin/python ]]; then
  ./.venv/bin/python - <<'PY'
import sys
ok=1
def chk(mod):
    try:
        m=__import__(mod)
        v=getattr(m,'__version__','?')
        print(f"PASS: import {mod} ({v})")
    except Exception as e:
        print(f"FAIL: import {mod} -> {e}")
        return 0
    return 1
ok &= chk('ccxt')
ok &= chk('requests')
ok &= chk('telegram')
sys.exit(0 if ok else 1)
PY
else
  echo "FAIL: .venv/python mangler"
fi
echo

# 4) Telegram API (spam-fri: bare getMe)
echo "== Telegram =="
set +e
source ./.env 2>/dev/null || true
set -e
if [[ -n "${TG_KEY:-}" ]]; then
  RES=$(curl -s "https://api.telegram.org/bot${TG_KEY}/getMe")
  echo "$RES" | grep -q '"ok":true' && echo "PASS: TG getMe OK" || { echo "FAIL: TG getMe"; echo "$RES"; }
else
  echo "WARN: TG_KEY ikke satt"
fi
echo

# 5) CCXT børs-tilkobling (ticker)
echo "== Exchange =="
./.venv/bin/python - <<'PY'
import os, sys
import ccxt
ex=os.getenv("EXCHANGE","binance").lower()
try:
    if ex=='binance':
        e=ccxt.binance({'apiKey':os.getenv('BINANCE_KEY'), 'secret':os.getenv('BINANCE_SECRET'), 'enableRateLimit':True})
    elif ex=='okx':
        e=ccxt.okx({'apiKey':os.getenv('OKX_KEY'), 'secret':os.getenv('OKX_SECRET'), 'password':os.getenv('OKX_PASSWORD'), 'enableRateLimit':True})
    else:
        raise RuntimeError(f"Unsupported {ex}")
    t=e.fetch_ticker('BTC/USDT')
    b=t.get('bid'); a=t.get('ask')
    if b is not None and a is not None:
        print(f"PASS: {e.id} fetch_ticker BTC/USDT bid={b} ask={a}")
    else:
        print("FAIL: fetch_ticker uten bid/ask")
except Exception as e:
    print("FAIL:", e)
    sys.exit(1)
PY
echo

# 6) Data/skrivetilgang
echo "== Data/skrivetilgang =="
DATA_DIR="${NOVA_HOME:-${NOVA_HOME:-/home/nova/nova-bot}/data}"
echo "DATA_DIR=$DATA_DIR"
mkdir -p "$DATA_DIR" "$DATA_DIR/logs" "$DATA_DIR/backups" "$DATA_DIR/learning"
touch "$DATA_DIR/equity.json" "$DATA_DIR/state.json" "$DATA_DIR/logs/healthcheck.log" 2>/dev/null || true
if [[ -w "$DATA_DIR/equity.json" && -w "$DATA_DIR/state.json" ]]; then
  echo "PASS: kan skrive equity.json/state.json"
else
  echo "FAIL: kan ikke skrive til data-filer"
fi
echo "equity.json: $(stat -c '%y %sB' "$DATA_DIR/equity.json" 2>/dev/null || echo 'mangler')"
echo "state.json : $(stat -c '%y %sB' "$DATA_DIR/state.json"  2>/dev/null || echo 'mangler')"
echo

# 7) state.json valid + watch
echo "== state.json =="
./.venv/bin/python - <<'PY'
import json, os, pathlib
p=pathlib.Path(os.getenv('NOVA_HOME','${NOVA_HOME:-/home/nova/nova-bot}/data'))/'state.json'
try:
    s=json.loads(p.read_text() or '{}')
    wl=s.get('watch',[])
    print("PASS: state.json er gyldig JSON")
    print("watch:", ",".join(wl) if wl else "(tom)")
except Exception as e:
    print("WARN: state.json ikke lesbar/gyldig ->", e)
PY
echo

# 8) Siste engine-logger inkl. watchN
echo "== journalctl (siste 80 linjer) =="
sudo journalctl -u novax.service -n 80 --no-pager | tail -n +1
echo

# 9) Oppsummering (enkel)
echo "== Oppsummering =="
echo "Hvis du ser PASS på punktene over + watchN=300 i engine-linjene, er alt OK."
echo "Feil? Kopiér relevant FAIL/WARN-seksjon og send den her."