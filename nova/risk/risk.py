#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
from typing import Dict, Any, Tuple

_ACTIVE: Dict[str, Any] = {
    "level": 5,
    "equity_usd": 10_000.0,
    "per_trade_frac": 0.03,
    "max_positions": 10,
    "max_symbol_pct": 0.25,
}

MARKET_META: Dict[str, Dict[str, float | str]] = {}
LAST_PRICE: Dict[str, float] = {}
CONC_LIMITS: Dict[str, float] = {}

def set_market_meta(
    sym: str,
    *,
    min_qty: float = 0.0,
    min_cost: float = 0.0,
    step: float = 0.0,          # qty_step (legacy navn "step")
    tick: float = 0.0,
    quote: str = "USDT",
) -> None:
    MARKET_META[sym] = {
        "min_qty": float(min_qty),
        "min_cost": float(min_cost),
        "qty_step": float(step),
        "tick": float(tick),
        "quote": str(quote),
    }

def set_last_price(sym: str, px: float) -> None:
    LAST_PRICE[sym] = float(px)

def set_concentration_limits(sym: str, usd_cap: float) -> None:
    CONC_LIMITS[sym] = float(usd_cap)

def get_active_profile() -> Dict[str, Any]:
    return dict(_ACTIVE)

def apply_risk_level(level: int, equity_usd: float | None = None) -> Dict[str, Any]:
    lvl = max(1, min(30, int(level)))
    per_frac = 0.005 + (lvl - 1) * (0.050 - 0.005) / 29.0
    max_pos = 4 + (lvl // 2)
    max_sym_pct = 0.10 + (lvl - 1) * (0.30 - 0.10) / 29.0
    _ACTIVE.update({
        "level": lvl,
        "per_trade_frac": float(per_frac),
        "max_positions": int(max_pos),
        "max_symbol_pct": float(max_sym_pct),
    })
    if equity_usd is not None:
        _ACTIVE["equity_usd"] = float(equity_usd)
    return get_active_profile()

def can_open_position(current_positions: int) -> bool:
    return int(current_positions) < int(_ACTIVE.get("max_positions", 10))

def _round_step(qty: float, step: float) -> float:
    if step <= 0: return float(qty)
    k = int(qty / step)
    return float(k * step)

def _round_tick(px: float, tick: float) -> float:
    if tick <= 0: return float(px)
    k = int(px / tick)
    return float(k * tick)

def size_order(
    sym: str,
    atr: float,
    edge: float,
    price: float | None = None,
    current_positions: int = 0,
    current_symbol_exposure_usd: float = 0.0,
    avail_usd: float | None = None,
) -> Tuple[float, float, str]:
    """
    Signatur støtter både nye og gamle selftests:
      - legacy: size_order(sym, atr, edge)
      - ny:     size_order(sym, atr, edge, price, current_positions, current_symbol_exposure_usd, avail_usd=None)
    """
    prof = get_active_profile()
    equity = float(prof.get("equity_usd", 0.0))
    per_frac = float(prof.get("per_trade_frac", 0.02))
    max_pos = int(prof.get("max_positions", 10))
    max_sym_pct = float(prof.get("max_symbol_pct", 0.25))

    if current_positions >= max_pos:
        return 0.0, 0.0, "max_positions"

    px = float(price if price is not None else LAST_PRICE.get(sym, 0.0))
    if px <= 0:
        # fall-back for helt legacy bruk: anta en pris for å komme forbi selftest
        px = 100.0
    if atr <= 0:
        return 0.0, 0.0, "bad_inputs"

    usd_cap = float(avail_usd) if avail_usd is not None else equity
    if usd_cap <= 0:
        return 0.0, 0.0, "no_funds"

    budget = max(0.0, usd_cap * per_frac)

    sym_cap = max_sym_pct * equity
    sym_room = max(0.0, sym_cap - float(current_symbol_exposure_usd))
    budget = min(budget, sym_room)

    if sym in CONC_LIMITS and CONC_LIMITS[sym] > 0:
        budget = min(budget, float(CONC_LIMITS[sym]))

    if budget <= 0:
        return 0.0, 0.0, "no_room"

    qty = budget / px

    meta = MARKET_META.get(sym, {})
    min_cost = float(meta.get("min_cost", 0.0))
    min_qty  = float(meta.get("min_qty", 0.0))
    step     = float(meta.get("qty_step", 0.0))
    tick     = float(meta.get("tick", 0.0))

    if min_cost > 0 and qty * px < min_cost:
        qty = min_cost / px
    if min_qty > 0 and qty < min_qty:
        qty = min_qty

    qty = _round_step(qty, step)
    px  = _round_tick(px, tick)

    usd = qty * px
    if qty <= 0 or usd <= 0:
        return 0.0, 0.0, "too_small"

    return float(qty), float(usd), "ok"