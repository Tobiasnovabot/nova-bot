import math, time
from pathlib import Path
import json
MEM_DIR=Path("data/memory"); MEM_DIR.mkdir(parents=True, exist_ok=True)

def _load_sym(sym):
    p = MEM_DIR / (sym.replace("/","_") + ".json")
    if not p.exists(): return {"wins":0,"losses":0,"edge":0.0,"last_ts":0,"max_dd":0.0}
    try: return json.loads(p.read_text())
    except: return {"wins":0,"losses":0,"edge":0.0,"last_ts":0,"max_dd":0.0}

def _save_sym(sym, d):
    p = MEM_DIR / (sym.replace("/","_") + ".json")
    p.write_text(json.dumps(d, indent=2))

def update_memory(symbol, realized_pnl):
    d=_load_sym(symbol)
    if realized_pnl>0: d["wins"]+=1
    elif realized_pnl<0: d["losses"]+=1
    d["edge"] = (d["wins"] - d["losses"]) / max(1, d["wins"]+d["losses"])
    d["last_ts"]=int(time.time())
    _save_sym(symbol,d)

def kelly_like(edge, payoff=1.0, cap=0.05, floor=0.005):
    if payoff<=0: payoff=1.0
    f = max(0.0, min(cap, edge/(1.0*payoff)))  # svært konservativ
    return max(floor, f)

def gate_daily_loss(equity_series, limit_frac=0.05):
    if not equity_series: return False
    # stopp hvis equity falt > limit siste 24t
    now=e=equity_series[-1]["equity_usdt"]
    hi=max(x["equity_usdt"] for x in equity_series[-1440:]) if len(equity_series)>0 else now
    return (hi - now) / max(1e-9, hi) > limit_frac
