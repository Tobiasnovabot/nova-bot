from __future__ import annotations
def scale_factor(trades_ok:int, pnl_usd:float)->float:
    if trades_ok < 10: return 0.2
    if pnl_usd   < 0:  return 0.2
    if trades_ok < 30: return 0.5
    return 1.0