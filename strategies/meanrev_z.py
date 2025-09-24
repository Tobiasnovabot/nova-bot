def setup(cfg): return {"n": cfg.get("mr_len",50), "z_buy": -1.0, "z_sell": 1.0}
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
def signal(t,o,p):
    c=[x[4] for x in o][-500:]; n=p["n"]
    if len(c)<n: return ("hold",{})
    ma=_sma(c,n); sd=_stdev(c,ma,n)
    mu=ma[-1]; s=sd[-1]
    if not mu or not s or s==0: return ("hold",{})
    z=(c[-1]-mu)/s
    if z<=p["z_buy"]: return ("buy", {"z":z})
    if z>=p["z_sell"]: return ("sell", {"z":z})
    return ("hold",{})
