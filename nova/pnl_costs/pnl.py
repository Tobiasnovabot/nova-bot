#!/usr/bin/env python3
from __future__ import annotations
from nova import paths as NPATH
from typing import Dict, Any
def apply_fees_slip(fill: Dict[str, Any], fee_bps: float | None=None, slip_bps: float | None=None) -> Dict[str, Any]:
    side=fill["side"]; px=float(fill["price"]); qty=float(fill["qty"])
    fee_bps=float(fee_bps if fee_bps is not None else fill.get("fee_bps",10.0))
    slip_bps=float(slip_bps if slip_bps is not None else fill.get("slip_bps",15.0))
    signed=1 if side=="buy" else -1
    fee=abs(qty*px)*fee_bps/10_000.0
    eff=px + signed*(px*slip_bps/10_000.0)
    out=dict(fill); out["eff_price"]=eff; out["fee"]=fee; return out
def snapshot_equity(equity_usd: float, pnl_day: float=0.0) -> None:
    try:
        import json, os, time
        os.makedirs("nova/data", exist_ok=True)
        path=NPATH.EQUITY.as_posix(); xs=[]
        if os.path.exists(path):
            with open(path,"r") as f: xs=json.load(f)
        xs.append({"ts": int(time.time()), "equity": float(equity_usd), "pnl_day": float(pnl_day)})
        with open(path,"w") as f: json.dump(xs, f)
    except Exception: pass