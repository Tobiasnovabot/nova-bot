import json, time, math
from pathlib import Path
from typing import Dict, List

STATS = Path("/home/nova/nova-bot/state/strat_stats.json")
STATS.parent.mkdir(parents=True, exist_ok=True)

def _load()->dict:
    try: return json.loads(STATS.read_text())
    except: return {}

def _save(d:dict)->None:
    tmp=STATS.with_suffix(".tmp"); tmp.write_text(json.dumps(d, separators=(",",":"))); tmp.replace(STATS)

def update_perf(pnl_by_strategy:Dict[str,float], alpha:float=0.2)->None:
    """EMA på PnL og Sharpe-approks. Oppdateres hver tick."""
    d=_load()
    for name, pnl in pnl_by_strategy.items():
        s=d.get(name, {"ema_pnl":0.0,"ema_var":1e-6,"count":0,"last_ts":0})
        # enkel ema
        s["ema_pnl"] = (1-alpha)*s["ema_pnl"] + alpha*pnl
        # varians-EMA for pseudo-Sharpe
        s["ema_var"] = (1-alpha)*s["ema_var"] + alpha*(pnl*pnl)
        s["count"] += 1
        s["last_ts"] = time.time()
        d[name]=s
    _save(d)

def get_weights(top_k:int=20, min_count:int=10)->Dict[str,float]:
    """Returner vekt pr strategi basert på ema_pnl / sqrt(ema_var)."""
    d=_load()
    scored=[]
    for name,s in d.items():
        if s.get("count",0) < min_count: 
            continue
        denom = math.sqrt(max(1e-8, s["ema_var"]))
        score = s["ema_pnl"]/denom
        scored.append((name, max(-5.0, min(5.0, score))))
    # sorter, velg topp K, normaliser positive og negative separat
    scored.sort(key=lambda x: x[1], reverse=True)
    chosen = scored[:top_k]
    if not chosen: return {}
    # mappe score → vekt i [0..2] rundt 1
    maxabs = max(abs(s) for _,s in chosen) or 1.0
    weights = {n: (1.0 + s/maxabs) for n,s in chosen}
    return weights
