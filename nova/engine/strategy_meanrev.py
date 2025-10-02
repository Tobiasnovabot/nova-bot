def decide(ticker: dict, trail_pct: float, take_min: float):
    px = float(ticker.get('last') or ticker.get('close') or 0)
    hi = float(ticker.get('high') or 0)
    lo = float(ticker.get('low') or 0)
    if px <= 0 or hi <= 0:
        return None
    mid = (hi + lo) / 2.0
    # kjøp når pris under midt og snur opp igjen (proxy: close > low*1.005)
    if px > 0 and lo > 0 and px < mid and px >= lo * 1.005:
        return {"side":"buy","trail_pct":trail_pct*0.8,"take_min":take_min*0.8,"price":px}
    return None
