import math
def _sma(x,n): 
    if len(x)<n: return []
    out=[]; s=sum(x[:n]); out.append(s/n)
    for i in range(n,len(x)): s+=x[i]-x[i-n]; out.append(s/n)
    return [None]*(n-1)+out
def _stdev(x, m, n):
    import math
    out=[None]*(n-1)
    for i in range(n-1, len(x)):
        win=x[i-n+1:i+1]; mu=m[i]
        if mu is None: out.append(None); continue
        out.append(math.sqrt(sum((v-mu)**2 for v in win)/n))
    return out
def setup(cfg): return {"n": cfg.get("bb_len",20), "k": cfg.get("bb_k",2.0)}
def signal(t, o, p):
    c=[x[4] for x in o][-300:]; n=p["n"]; k=p["k"]
    if len(c)<n: return ("hold", {})
    ma=_sma(c,n); sd=_stdev(c,ma,n)
    up=[(ma[i]+k*sd[i]) if ma[i] and sd[i] else None for i in range(len(c))]
    dn=[(ma[i]-k*sd[i]) if ma[i] and sd[i] else None for i in range(len(c))]
    px=c[-1]; up1=up[-1]; dn1=dn[-1]
    if up1 and px>up1: return ("buy", {"bb": "up"})
    if dn1 and px<dn1: return ("sell", {"bb": "down"})
    return ("hold", {})
