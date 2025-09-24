import math
def setup(cfg): return {"fast": cfg.get("ema_fast", 12), "slow": cfg.get("ema_slow", 26)}
def _ema(vals, n):
    if not vals or len(vals)<n: return None
    k=2/(n+1); e=vals[0]
    for v in vals[1:]: e = v*k + e*(1-k)
    return e
def signal(ticker, ohlc, params):
    closes=[c[4] for c in ohlc][-200:] if ohlc else []
    if len(closes)<max(params["fast"], params["slow"]): return ("hold", {})
    efast=_ema(closes, params["fast"]); eslow=_ema(closes, params["slow"])
    if efast is None or eslow is None: return ("hold", {})
    gap=(efast-eslow)/eslow if eslow else 0.0
    if gap>0.002: return ("buy", {"reason":"ema_up","edge":gap})
    if gap<-0.002: return ("sell", {"reason":"ema_down","edge":gap})
    return ("hold", {})
