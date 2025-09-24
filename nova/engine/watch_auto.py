from nova.exchange import build_exchange
import os
from nova import paths as NPATH
import os, json, time
from pathlib import Path
from typing import List
import ccxt

def _pick_top_usdt(top_n:int, market_type:str)->List[str]:
    ex = build_exchange()
    ex.options = {'defaultType': 'spot' if market_type=='spot' else 'swap'}
    mkts = ex.load_markets()
    syms=[]
    for m in mkts.values():
        if not m.get('active'): continue
        if m.get('quote')!='USDT': continue
        mtype = m.get('type') or ('swap' if m.get('contract') else 'spot')
        if market_type=='spot':
            if mtype!='spot': continue
        else:  # swap
            if mtype!='swap' or not m.get('contract') or m.get('linear') is not True: continue
        syms.append(m['symbol'])
    try:
        t = ex.fetch_tickers(syms)
        syms = sorted([s for s in syms if s in t], key=lambda s: -(t[s].get('quoteVolume') or 0))
    except Exception:
        syms = sorted(syms)
    return syms[:top_n]

def resolve_symbols()->List[str]:
    wl = (os.getenv("WATCHLIST","") or "").strip().upper()
    top_n = int(os.getenv("WATCH_TOP_N", os.getenv("TOP_N","300")) or "300")
    market = (os.getenv("WATCH_MARKET","spot") or "spot").lower()
    # Direkte liste
    if wl and wl not in ("AUTO","AUTO_USDT","AUTO_USDT_SPOT","AUTO_SPOT","*","*USDT"):
        return [s.strip().upper() for s in wl.split(",") if s.strip()]
    # AUTO_USDT
    return _pick_top_usdt(top_n, "spot" if market!="swap" else "swap")

def refresh_auto_watch(nova_home:str|None=None)->List[str]:
    nova_home = nova_home or os.getenv("NOVA_HOME", "/home/nova/nova-bot/data")
    p = Path(nova_home)/NPATH.STATE.as_posix()
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        st = json.loads(p.read_text() or "{}")
    except Exception:
        st = {}
    syms = resolve_symbols()
    st.setdefault("mode", os.getenv("MODE","paper"))
    st.setdefault("bot_enabled", True)
    st["watch"] = syms
    st["universe_cache"] = {"ts": int(time.time()), "type": (os.getenv("WATCH_MARKET","spot") or "spot"), "symbols": syms}
    p.write_text(json.dumps(st, separators=(",",":")))
    return syms

if __name__=="__main__":
    syms = refresh_auto_watch()
    print("watchN=", len(syms))
    print(", ".join(syms[:20]))