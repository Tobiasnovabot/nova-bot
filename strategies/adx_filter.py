def setup(cfg): return {"len": cfg.get("adx_len",14), "min": cfg.get("adx_min",18.0)}
def _tr(o,i): 
    return max(o[i][2]-o[i][3], abs(o[i][2]-o[i-1][4]), abs(o[i][3]-o[i-1][4]))
def signal(t,o,p):
    n=p["len"]
    if len(o)<n+2: return ("hold", {"adx_ok": True})
    trs=[_tr(o,i) for i in range(1,len(o))]
    tr=sum(trs[-n:])/n if len(trs)>=n else 0.0
    if tr<=0: return ("hold", {"adx_ok": False})
    up=sum(max(0.0, o[i][2]-o[i-1][2]) for i in range(1,len(o)))/n
    dn=sum(max(0.0, o[i-1][3]-o[i][3]) for i in range(1,len(o)))/n
    dip=100*(up/max(tr,1e-9)); dim=100*(dn/max(tr,1e-9))
    dx=100*abs(dip-dim)/max((dip+dim),1e-9)
    return ("hold", {"adx_ok": dx>=p["min"], "adx": dx})
