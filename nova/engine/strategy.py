def decide(ticker: dict, trail_pct: float, take_min: float):
    px=float(ticker.get('last') or ticker.get('close') or 0)
    hi=float(ticker.get('high',0)); lo=float(ticker.get('low',0))
    if px<=0: return None
    rng=max(hi-lo,1e-8); bias=(px-lo)/rng if rng>0 else 0.0
    if bias>0.75: return {"side":"buy","trail_pct":trail_pct,"take_min":take_min,"price":px}
    return None
