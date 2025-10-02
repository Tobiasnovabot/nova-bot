#!/usr/bin/env python3
from __future__ import annotations
from typing import Dict, Any, Tuple
from collections import deque
from nova.notify import send as tg_send

_HISTORY = deque(maxlen=200)

def record_fill(symbol: str, side: str, px_plan: float, px_fill: float,
                fee_usd: float, usd: float) -> None:
    slip_bps = (px_fill - px_plan) / px_plan * (10000 if side.lower()=="buy" else -10000)
    fee_bps = (fee_usd / usd * 10000) if usd>0 else 0.0
    _HISTORY.append((symbol, slip_bps, fee_bps))

def slip_params() -> Tuple[float, float]:
    """Returner (slip_bps_p95, fee_bps_avg) til tuning/varsler."""
    if not _HISTORY: return 0.0, 0.0
    s = sorted(abs(x[1]) for x in _HISTORY)
    p95 = s[int(len(s)*0.95)-1] if len(s)>=5 else s[-1]
    fee = sum(x[2] for x in _HISTORY)/len(_HISTORY)
    return p95, fee

def slip_guard(adapt=True, warn_p95_bps=35.0) -> Dict[str, Any]:
    p95, fee = slip_params()
    try:
        if p95 > warn_p95_bps:
            tg_send(f"⚠️ Høy slippage p95≈{p95:.1f}bps (fee≈{fee:.1f}bps)")
    except Exception:
        pass
    # kan eksponere adaptive parametre til engine (f.eks. strammere spread-gate, lavere qty)
    adj = {}
    if adapt and p95 > warn_p95_bps:
        adj["spread_gate_bps"] = min( max(p95*1.2, 15.0), 60.0)
        adj["qty_scale"] = 0.8
    return {"p95_bps": p95, "fee_bps": fee, "adjust": adj}