def _ema(vals, n):
    if len(vals)<n: return []
    k=2/(n+1); out=[sum(vals[:n])/n]
    for v in vals[n:]: out.append(out[-1]+k*(v-out[-1]))
    return [None]*(n-1)+out
def setup(cfg): return {"ema": cfg.get("kc_ema",20), "mult": cfg.get("kc_mult",1.5)}
def signal(t,o,p):
    if len(o)<p["ema"]+2: return ("hold",{})
    closes=[x[4] for x in o]; ema=_ema(closes, p["ema"])
    trs=[(c[2]-c[3]) for c in o]  # high-low
    atr=sum(trs[-p["ema"]:])/p["ema"] if len(trs)>=p["ema"] else None
    if not ema or ema[-1] is None or not atr: return ("hold",{})
    up=ema[-1]+p["mult"]*atr; dn=ema[-1]-p["mult"]*atr; last=closes[-1]
    if last>up: return ("buy", {"kc":"up"})
    if last<dn: return ("sell", {"kc":"down"})
    return ("hold",{})
