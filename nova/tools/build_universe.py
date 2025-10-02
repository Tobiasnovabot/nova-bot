from nova.exchange import build_exchange
import os
from nova import paths as NPATH
import os, json, time, pathlib, math
import ccxt

TOP_N = int(os.getenv("TOP_N", "300"))
NOVA_HOME = os.getenv("NOVA_HOME", "/home/nova/nova-bot/data")
STATE_P = pathlib.Path(NOVA_HOME) / NPATH.STATE.as_posix()
STATE_P.parent.mkdir(parents=True, exist_ok=True)

ex = build_exchange()  # Tving spot
tickers = ex.fetch_tickers()  # alle spot tickers

# Filtrer til USDT-par og aktive markeder
spot_usdt = {}
for sym, t in tickers.items():
    q = t.get("quote") or (t.get("symbol","").split("/")[-1] if "/" in t.get("symbol","") else None)
    if q != "USDT":
        continue
    # forsøk hente volum (ccxt normaliserer ofte 'quoteVolume', ellers ligger det i info)
    v = t.get("quoteVolume")
    if v is None:
        info = t.get("info", {})
        v = info.get("quoteVolume") or info.get("quoteVolume24h")
    try:
        v = float(v)
    except Exception:
        v = 0.0
    if not math.isfinite(v):
        v = 0.0
    spot_usdt[sym] = v

# Ranger og ta TOP_N
ranked = sorted(spot_usdt.keys(), key=lambda s: spot_usdt[s], reverse=True)[:TOP_N]

# Skriv til state.json -> universe_cache
state = {}
if STATE_P.exists():
    try:
        state = json.loads(STATE_P.read_text() or "{}")
    except Exception:
        state = {}
state.setdefault("universe_cache", {"ts": 0, "symbols": []})
state["universe_cache"]["ts"] = int(time.time())
state["universe_cache"]["symbols"] = ranked
STATE_P.write_text(json.dumps(state, separators=(",",":")))

print(f"[universe] spot USDT symbols={len(ranked)} TOP_N={TOP_N}")
print("[universe] first 15:", ", ".join(ranked[:15]))