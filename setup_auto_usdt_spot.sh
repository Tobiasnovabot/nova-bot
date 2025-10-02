#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}

# --- 0) Sikkerhetskopier engine-run ---
mkdir -p backups
ts=$(date +%Y%m%d-%H%M%S)
cp -n nova/engine/run.py "backups/run.py.$ts.bak" || true

# --- 1) Legg til nytt hjelpe-modul for AUTO_USDT (spot/swap) ---
mkdir -p nova/engine
cat > nova/engine/watch_auto.py <<'PY'
import os, time
from typing import List
from pathlib import Path
import json
import ccxt

def _pick_top_usdt(top_n: int, market_type: str = "spot") -> List[str]:
    market_type = (market_type or "spot").lower()
    ex = ccxt.binance()
    ex.options = {'defaultType': 'spot' if market_type == 'spot' else 'swap'}
    markets = ex.load_markets()

    symbols = []
    for m in markets.values():
        if not m.get('active'):
            continue
        if m.get('quote') != 'USDT':
            continue
        mtype = m.get('type') or ('swap' if m.get('contract') else 'spot')
        if market_type == 'spot' and mtype != 'spot':
            continue
        if market_type == 'swap':
            if mtype != 'swap':
                continue
            if not m.get('contract'):
                continue
            if m.get('linear') is not True:
                continue
        symbols.append(m['symbol'])

    try:
        tickers = ex.fetch_tickers(symbols)
        symbols = sorted(
            [s for s in symbols if s in tickers],
            key=lambda s: -(tickers[s].get('quoteVolume') or 0)
        )
    except Exception:
        symbols = sorted(symbols)

    return symbols[:top_n]

def _resolve_watchlist_from_env() -> List[str]:
    wl_env = (os.getenv("WATCHLIST", "") or "").strip().upper()
    top_n = int(os.getenv("WATCH_TOP_N", os.getenv("TOP_N", "100")) or "100")
    market_type = (os.getenv("WATCH_MARKET", "spot") or "spot").lower()

    data_dir = os.getenv("NOVA_HOME", "${NOVA_HOME:-/home/nova/nova-bot}/data")
    state_p = Path(data_dir) / "state.json"
    state_p.parent.mkdir(parents=True, exist_ok=True)

    try:
        st = json.loads(state_p.read_text() or "{}")
    except Exception:
        st = {}

    # eksplisitt watch fra state overstyrer AUTO
    watch_from_state = st.get("watch") or []
    if watch_from_state:
        return [w.strip().upper() for w in watch_from_state if w.strip()]

    if wl_env in ("AUTO_USDT", "*USDT", "AUTO"):
        uc = st.setdefault("universe_cache", {"ts": 0, "type": market_type, "symbols": []})
        fresh = (uc.get("type") == market_type) and (len(uc.get("symbols", [])) >= min(10, top_n//2)) and ((time.time() - uc.get("ts", 0)) < 3600)
        if not fresh:
            syms = _pick_top_usdt(top_n, market_type=market_type)
            uc["ts"] = int(time.time())
            uc["type"] = market_type
            uc["symbols"] = syms
            try:
                state_p.write_text(json.dumps(st, separators=(",",":")))
            except Exception:
                pass
            return syms
        else:
            return uc.get("symbols", [])[:top_n]
    else:
        if not wl_env:
            return ["BTC/USDT","ETH/USDT"]
        return [s.strip().upper() for s in wl_env.split(",") if s.strip()]
PY

# --- 2) Sørg for at run.py importerer vår helper (idempotent) ---
if ! grep -q "from nova.engine.watch_auto import _resolve_watchlist_from_env" nova/engine/run.py; then
  # Sett inn import rett etter første import-blokk
  awk '
    BEGIN{done=0}
    {
      print $0
      if (!done && $0 ~ /^import /) {
        # vent til import-blokken er ferdig (tom linje etter imports)
      }
    }
    END{}
  ' nova/engine/run.py > /tmp/run.py.tmp1

  # Enklere: legg import øverst hvis ikke finnes
  { echo "from nova.engine.watch_auto import _resolve_watchlist_from_env"; cat nova/engine/run.py; } > /tmp/run.py.tmp2
  mv /tmp/run.py.tmp2 nova/engine/run.py
fi

# --- 3) Erstatt watchlist-bygging til å bruke _resolve_watchlist_from_env() ---
# erstatt kjente linjer om watchlist (robust: hvis finnes)
sed -i 's/watchlist = full\[:top_n\]/watchlist = _resolve_watchlist_from_env()/' nova/engine/run.py || true
sed -i 's/watchlist = _parse_watchlist(.*/watchlist = _resolve_watchlist_from_env()/' nova/engine/run.py || true

# Hvis ingenting ble erstattet, prøv å injisere rett før engine-print
if ! grep -q "_resolve_watchlist_from_env()" nova/engine/run.py; then
  # Sett inn "watchlist = _resolve_watchlist_from_env()" like før print-linja med watchN
  sed -i '/print(f"\[engine\].*watchN=/i watchlist = _resolve_watchlist_from_env()' nova/engine/run.py
fi

# --- 4) Miljø og state for AUTO_USDT spot topp-300 ---
grep -q '^NOVA_HOME=' .env || echo 'NOVA_HOME=${NOVA_HOME:-/home/nova/nova-bot}/data' >> .env
sed -i '/^WATCHLIST=/d;/^WATCH_MARKET=/d;/^TOP_N=/d;/^WATCH_TOP_N=/d;/^ENGINE_LOOP_SEC=/d' .env
cat >> .env <<EOF
WATCHLIST=AUTO_USDT
WATCH_MARKET=spot
TOP_N=300
WATCH_TOP_N=300
ENGINE_LOOP_SEC=10
EOF

python3 - <<'PY'
import json, pathlib, time
p = pathlib.Path('data/state.json'); p.parent.mkdir(parents=True, exist_ok=True)
s = {}
if p.exists():
    try: s = json.loads(p.read_text() or "{}")
    except Exception as e:
s = {}
s["mode"]="paper"; s["bot_enabled"]=True; s.setdefault("risk_level",5)
s["watch"]=[]  # tving AUTO_USDT via cache
s["universe_cache"]={"ts":0,"type":"spot","symbols":[]}
p.write_text(json.dumps(s,separators=(",",":")))
print("state.json oppdatert for AUTO_USDT spot 300.")
PY

# --- 5) Restart tjenesten ---
sudo systemctl restart novax.service

echo
echo "==> Kjør self-check:"
echo "   ~/nova-bot/selfcheck_auto_usdt.sh"