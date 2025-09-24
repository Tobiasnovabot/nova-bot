def _ema(vals, n):
    if len(vals)<n: return []
    k=2/(n+1); out=[sum(vals[:n])/n]
    for v in vals[n:]: out.append(out[-1]+k*(v-out[-1]))
    return [None]*(n-1)+out
def setup(cfg): return {"fast":cfg.get("macd_fast",12), "slow":cfg.get("macd_slow",26), "sig":cfg.get("macd_sig",9)}
def signal(tick, ohlc, p):
    c=[x[4] for x in ohlc][-400:]
    if len(c)<p["slow"]+p["sig"]: return ("hold", {})
    f=_ema(c,p["fast"]); s=_ema(c,p["slow"])
    macd=[(a-b) if a and b else None for a,b in zip(f,s)]
    sig=_ema([m for m in macd if m is not None], p["sig"]); sig=[None]*(len(macd)-len(sig))+sig
    if macd[-2] is not None and sig[-2] is not None:
        cu = macd[-2] <= sig[-2] and macd[-1] > sig[-1]
        cd = macd[-2] >= sig[-2] and macd[-1] < sig[-1]
        if cu: return ("buy", {"macd":macd[-1]})
        if cd: return ("sell", {"macd":macd[-1]})
    return ("hold", {})
