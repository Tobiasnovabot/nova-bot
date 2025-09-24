def should_rollback(day_pnl_pct: float, hit_breakers: int) -> bool:
    return (day_pnl_pct or 0.0) < -0.02 and (hit_breakers or 0) >= 2

def rollback(params: dict) -> dict:
    r = dict(params or {})
    r["risk_level"] = max(1, int(r.get("risk_level", 5)) - 1)
    r["twap"] = False
    return r
