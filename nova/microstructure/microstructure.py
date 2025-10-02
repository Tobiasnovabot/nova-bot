#!/usr/bin/env python3
from __future__ import annotations
from typing import Dict, Tuple

_PARAMS = {"min_depth_usd": 100_000.0, "max_spread_bps": 20.0, "cost_margin": 1.15}
def set_params(min_depth_usd=None, max_spread_bps=None, cost_margin=None):
    if min_depth_usd is not None: _PARAMS["min_depth_usd"]=float(min_depth_usd)
    if max_spread_bps is not None: _PARAMS["max_spread_bps"]=float(max_spread_bps)
    if cost_margin is not None: _PARAMS["cost_margin"]=float(cost_margin)

def compute_spread_bps(book: Dict[str, float]) -> float:
    bid=float(book["bid"]); ask=float(book["ask"]); mid=(bid+ask)/2.0
    if mid<=0: return 1e9
    return (ask-bid)/mid*10_000.0

def _cost_bps(book: Dict[str, float]) -> float:
    fee=float(book.get("fee_bps",10.0)); slip=float(book.get("slip_bps",15.0)); spr=compute_spread_bps(book)
    return fee+slip+spr

def micro_ok(sym: str, book: Dict[str, float], atr: float) -> Tuple[bool,str]:
    if float(book.get("depth_usd",0.0)) < _PARAMS["min_depth_usd"]: return False,"depth"
    spr_bps = compute_spread_bps(book)
    if spr_bps > _PARAMS["max_spread_bps"]: return False,"spread"
    # kost-gate: ATR må slå kostnader
    cost = _cost_bps(book) * _PARAMS["cost_margin"]
    atr_bps = (float(atr)/float(book["ask"])) * 10_000.0
    if atr_bps <= cost: return False,"cost_gate"
    return True,"ok"

def adjust_for_spread(qty: float) -> float:
    return max(0.0, float(qty))