#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import Dict, Any

from nova.stateio.stateio import snapshot_equity

# ---------------- Fees & Slippage ----------------

def _bps_to_frac(bps: float) -> float:
    return float(bps) / 10_000.0

def apply_fees_slip(fill: Dict[str, Any]) -> Dict[str, Any]:
    """
    Berik et fill med fees og slippage og returner nytt dict.
    Input:
      side: 'buy'|'sell'
      qty: float
      price: float           # børspris
      maker: bool            # True=maker, False=taker (valgfri)
      fee_bps: float         # overstyr bps (valgfri)
      maker_fee_bps: float   # default 10 bps
      taker_fee_bps: float   # default 10 bps
      slip_bps: float        # default 15 bps
    Output-felter lagt til:
      notional, fee_usd, slip_bps, eff_price, gross_usd, net_usd
        - buy: net_usd = kostnad (positiv)
        - sell: net_usd = inntekt (positiv)
    """
    side = str(fill["side"]).lower()
    assert side in ("buy", "sell")
    qty = float(fill["qty"])
    px = float(fill["price"])

    maker = bool(fill.get("maker", False))
    maker_fee_bps = float(fill.get("maker_fee_bps", 10.0))
    taker_fee_bps = float(fill.get("taker_fee_bps", 10.0))
    fee_bps = float(fill.get("fee_bps", maker_fee_bps if maker else taker_fee_bps))
    slip_bps = float(fill.get("slip_bps", 15.0))

    notional = qty * px
    fee_usd = notional * _bps_to_frac(fee_bps)

    # modellér slippage som prisjustering
    if side == "buy":
        eff_price = px * (1.0 + _bps_to_frac(slip_bps))
        gross_usd = qty * eff_price
        net_usd = gross_usd + fee_usd  # kostnad
    else:
        eff_price = px * (1.0 - _bps_to_frac(slip_bps))
        gross_usd = qty * eff_price
        net_usd = max(0.0, gross_usd - fee_usd)  # inntekt

    out = dict(fill)
    out.update({
        "notional": notional,
        "fee_usd": fee_usd,
        "slip_bps": slip_bps,
        "eff_price": eff_price,
        "gross_usd": gross_usd,
        "net_usd": net_usd,
    })
    return out

# ---------------- Equity snapshot ----------------

def snap_equity(equity_usdt: float, pnl_day: float = None):
    """Wrapper til stateio.snapshot_equity()."""
    return snapshot_equity(float(equity_usdt), pnl_day=pnl_day)

# ---------------- Intern PnL-ledger (brukes i tester) ----------------

@dataclass
class _Pos:
    qty: float = 0.0
    avg: float = 0.0  # gj.sn. kost inkl. fees/slip
    realized: float = 0.0

class _PnLLedger:
    """
    Enkel posisjonsbok for én symbol.
    - update(fill): oppdater posisjon og realized PnL.
    - mtm(last): beregn unrealized.
    """
    def __init__(self):
        self.pos = _Pos()

    def update(self, fill: Dict[str, Any]):
        f = apply_fees_slip(fill)
        q = float(f["qty"])
        side = f["side"].lower()
        if side == "buy":
            # øk posisjon, øk kost-basert avg
            total_cost = self.pos.avg * self.pos.qty + f["net_usd"]
            new_qty = self.pos.qty + q
            self.pos.avg = total_cost / new_qty if new_qty > 0 else 0.0
            self.pos.qty = new_qty
        else:
            # selg: realized = inntekt - avg*qty
            proceeds = f["net_usd"]
            realized = proceeds - self.pos.avg * q
            self.pos.realized += realized
            self.pos.qty -= q
            if self.pos.qty <= 1e-12:
                self.pos.qty = 0.0
                # beholder avg for referanse

    def mtm(self, last_price: float) -> Dict[str, float]:
        unreal = (last_price - self.pos.avg) * self.pos.qty
        return {"realized": self.pos.realized, "unrealized": unreal, "qty": self.pos.qty, "avg": self.pos.avg}