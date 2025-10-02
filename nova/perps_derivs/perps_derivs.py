#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
from typing import Dict, Any, Tuple

_PARAMS: Dict[str, float] = {
    "FUNDING_SPIKE_ABS": 0.005,   # 0.50% per funding interval => veto
    "BASIS_BPS_MAX": 200.0,       # |perp-spot|/spot in bps, over -> risikovarsel
    "CARRY_SIDE_CAP": 2.0,        # sikkerhet på carry PnL scaling
}

def set_params(**kw) -> None:
    for k, v in kw.items():
        if k in _PARAMS:
            _PARAMS[k] = float(v)

def check_perps_ok(ctx: Dict[str, Any]) -> Tuple[bool, str]:
    """
    ctx:
      funding_rate: float        # per 8h (typisk), signert
      interval_hours: float      # f.eks 8
      spot_px: float
      perps_px: float
    veto på funding-spike eller ekstrem basis.
    """
    f = float(ctx.get("funding_rate", 0.0))
    ivh = float(ctx.get("interval_hours", 8.0))
    # funding spike: absolutt sats over terskel
    if abs(f) >= _PARAMS["FUNDING_SPIKE_ABS"]:
        return (False, "funding_spike")
    # basis-vakt
    spot = float(ctx.get("spot_px", 0.0))
    perp = float(ctx.get("perps_px", 0.0))
    if spot > 0 and perp > 0:
        basis_bps = abs(perp - spot) / spot * 10_000.0
        if basis_bps > _PARAMS["BASIS_BPS_MAX"]:
            return (False, "basis_extreme")
    return (True, "")

def apply_carry_pnl(side: str, notional_usd: float, funding_rate: float, hours_held: float, ref_interval_hours: float = 8.0) -> float:
    """
    Beregn funding carry PnL for en åpen perp-posisjon.
      side: 'long' eller 'short'
      notional_usd: |pris*qty|
      funding_rate: sats per ref_interval_hours (signert; >0 betyr longs betaler)
      hours_held: hvor lenge posisjonen var åpen
    Returnerer: PnL i USD (positiv = tjent).
    """
    side = side.lower()
    sgn = 1.0 if side == "short" else -1.0  # når rate>0 betaler long -> negativ for long
    scale = max(0.0, min(hours_held / max(ref_interval_hours, 1e-9), _PARAMS["CARRY_SIDE_CAP"]))
    pnl = sgn * float(notional_usd) * float(funding_rate) * scale
    return float(pnl)

def basis_arbitrage_signal(spot_px: float, perps_px: float, thresh_bps: float = 30.0) -> Dict[str, Any]:
    """
    Enkel basis-arb skjelett:
      hvis perp > spot * (1 + thresh) -> short perp / long spot
      hvis perp < spot * (1 - thresh) -> long perp / short spot
    """
    if spot_px <= 0 or perps_px <= 0:
        return {"action": "none", "basis_bps": 0.0}
    basis_bps = (perps_px - spot_px) / spot_px * 10_000.0
    if basis_bps > thresh_bps:
        return {"action": "short_perp_long_spot", "basis_bps": basis_bps}
    if basis_bps < -thresh_bps:
        return {"action": "long_perp_short_spot", "basis_bps": basis_bps}
    return {"action": "none", "basis_bps": basis_bps}