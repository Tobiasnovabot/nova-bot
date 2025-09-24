def setup(cfg): return {"n": cfg.get("vwap_n",48), "th": cfg.get("vwap_th",0.003)}
def signal(t,o,p):
    w=o[-p["n"]:] if len(o)>=p["n"] else o
    if len(w)<10: return ("hold",{})
    num=0.0; den=0.0
    for ts,op,hi,lo,cl,vol in w:
        tp=(hi+lo+cl)/3.0; v=vol or 0.0
        num+=tp*v; den+=v
    if den<=0: return ("hold",{})
    vwap=num/den; last=w[-1][4]
    dev=(last-vwap)/vwap
    if dev<=-p["th"]: return ("buy", {"dev":dev})
    if dev>= p["th"]: return ("sell", {"dev":dev})
    return ("hold",{})
