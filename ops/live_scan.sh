#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}
source ./.env 2>/dev/null || true
source ./ops/lib.sh 2>/dev/null || true

# Vis journal (trades/signaler) i ett panel og topp-bevegelser i et annet (CTRL+C for å avslutte)
echo "== Live journal (trades/signaler) =="
( journalctl -u novax.service -f -o cat | grep -E 'paper|entry|exit|filled|trade|signal|watchN|engine' ) &
JPID=$!

cleanup(){ kill $JPID 2>/dev/null || true; }
trap cleanup EXIT

while true; do
  echo "----- $(date '+%H:%M:%S') topp-bevegelser (5m) -----"
  python3 - <<'PY'
import ccxt, statistics
ex=ccxt.binance()
m=ex.load_markets()
usdt=[s for s,v in m.items() if v.get('quote')=='USDT' and v.get('active')]
out=[]
for sym in usdt[:120]:
    try:
        o=ex.fetch_ohlcv(sym,'5m',limit=3)
        if len(o)<3: continue
        p0=o[-2][4]; p1=o[-1][4]
        ch=((p1-p0)/p0)*100 if p0 else 0
        out.append((ch,sym,round(p1,8)))
    except Exception as e:
pass
out.sort(reverse=True)
print("TOP GAINERS:")
for ch,sym,px in out[:10]:
    print(f"{sym:12} {ch:+6.2f}%  last={px}")
print("\nTOP LOSERS:")
for ch,sym,px in out[-10:]:
    print(f"{sym:12} {ch:+6.2f}%  last={px}")
PY
  sleep 20
done