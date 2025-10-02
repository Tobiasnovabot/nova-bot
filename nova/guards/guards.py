#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
import time
from typing import Dict, Any, Optional, Tuple

from nova.core_boot.core_boot import now_oslo

# Global guard-tilstand
_GUARD: Dict[str, Any] = {
    "day": None,
    "pnl_day": 0.0,
    "cooldown_until": 0.0,
    "news_halt_until": 0.0,
    "safe_mode": False,
    "loss_streak": {"global": 0, "per_sym": {}},
    "params": {
        # hard dagstap + cooldown
        "day_loss_hard_usd": 100.0,
        "cooldown_min": 30,
        # loss-streak demper
        "loss_streak_max": 3,
        "loss_cooldown_min": 10,
        # time/session (Oslo)
        "quiet_hours": [(3, 6)],  # blokkér fra 03 til 06
        # BTC guard
        "btc_ret_5m_thr": -0.03,  # -3% på 5m
        # stablecoin depeg
        "depeg_thr": 0.005,       # 0.5%
        # safety
        "max_spread_bps": 40.0,   # 0.40%
        "data_stale_max_s": 30.0,
    },
}

def _now_ts() -> float:
    return now_oslo().timestamp()

def reset_daily() -> None:
    d = now_oslo().date().isoformat()
    _GUARD["day"] = d
    _GUARD["pnl_day"] = 0.0
    _GUARD["cooldown_until"] = 0.0
    _GUARD["news_halt_until"] = _GUARD.get("news_halt_until", 0.0)
    _GUARD["loss_streak"]["global"] = 0
    _GUARD["loss_streak"]["per_sym"] = {}

def _ensure_today():
    d = now_oslo().date().isoformat()
    if _GUARD["day"] != d:
        reset_daily()

def set_params(**kwargs) -> None:
    _GUARD["params"].update(kwargs)

def set_safe_mode(on: bool) -> None:
    _GUARD["safe_mode"] = bool(on)

def start_news_halt(minutes: int) -> None:
    _GUARD["news_halt_until"] = _now_ts() + max(0, int(minutes)) * 60

def note_trade_result(symbol: str, pnl_usd: float) -> None:
    _ensure_today()
    ls = _GUARD["loss_streak"]
    if pnl_usd < 0:
        ls["global"] += 1
        ls["per_sym"][symbol] = ls["per_sym"].get(symbol, 0) + 1
    elif pnl_usd > 0:
        ls["global"] = 0
        ls["per_sym"][symbol] = 0

def update_drawdown(pnl_delta_usd: float) -> None:
    _ensure_today()
    _GUARD["pnl_day"] += float(pnl_delta_usd)
    hard = -abs(_GUARD["params"]["day_loss_hard_usd"])
    if _GUARD["pnl_day"] <= hard:
        mins = int(_GUARD["params"]["cooldown_min"])
        _GUARD["cooldown_until"] = _now_ts() + mins * 60

# ---- interne gates ----
def _gate_safe_mode() -> Tuple[bool,str]:
    return (False, "safe_mode") if _GUARD["safe_mode"] else (True, "")

def _gate_news() -> Tuple[bool,str]:
    return (False, "news_halt") if _now_ts() < _GUARD["news_halt_until"] else (True, "")

def _gate_cooldown() -> Tuple[bool,str]:
    return (False, "cooldown") if _now_ts() < _GUARD["cooldown_until"] else (True, "")

def _gate_dayloss() -> Tuple[bool,str]:
    hard = -abs(_GUARD["params"]["day_loss_hard_usd"])
    return (False, "day_loss_hard") if _GUARD["pnl_day"] <= hard else (True, "")

def _gate_time_session() -> Tuple[bool,str]:
    h = now_oslo().hour
    for start, end in _GUARD["params"]["quiet_hours"]:
        if start <= h < end:
            return (False, f"quiet_hours_{start}-{end}")
    return (True, "")

def _gate_loss_streak(ctx: Dict[str, Any]) -> Tuple[bool,str]:
    mx = int(_GUARD["params"]["loss_streak_max"])
    if _GUARD["loss_streak"]["global"] >= mx:
        _GUARD["cooldown_until"] = max(_GUARD["cooldown_until"], _now_ts() + int(_GUARD["params"]["loss_cooldown_min"]) * 60)
        return (False, "loss_streak_global")
    sym = ctx.get("symbol")
    if sym:
        per = _GUARD["loss_streak"]["per_sym"].get(sym, 0)
        if per >= mx:
            _GUARD["cooldown_until"] = max(_GUARD["cooldown_until"], _now_ts() + int(_GUARD["params"]["loss_cooldown_min"]) * 60)
            return (False, "loss_streak_symbol")
    return (True, "")

def _gate_btc_guard(ctx: Dict[str, Any]) -> Tuple[bool,str]:
    thr = float(_GUARD["params"]["btc_ret_5m_thr"])
    r = float(ctx.get("btc_ret_5m", 0.0))
    return (False, "btc_guard") if r <= thr else (True, "")

def _gate_depeg(ctx: Dict[str, Any]) -> Tuple[bool,str]:
    depeg_thr = float(_GUARD["params"]["depeg_thr"])
    stables: Dict[str,float] = ctx.get("stables", {}) or {}
    for k, px in stables.items():
        if px is None:
            continue
        if abs(float(px) - 1.0) > depeg_thr:
            return (False, f"depeg_{k}")
    return (True, "")

def _gate_safety(ctx: Dict[str, Any]) -> Tuple[bool,str]:
    spread_bps = float(ctx.get("spread_bps", 0.0))
    max_spread = float(_GUARD["params"]["max_spread_bps"])
    if spread_bps > max_spread:
        return (False, "spread_high")
    stale_s = float(ctx.get("data_stale_s", 0.0))
    if stale_s > float(_GUARD["params"]["data_stale_max_s"]):
        return (False, "data_stale")
    if ctx.get("ws_down"):
        return (False, "ws_down")
    if ctx.get("funding_spike"):
        return (False, "funding_spike")
    return (True, "")

# ---- offentlig API ----
def pretrade_checks(ctx: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    """
    ctx (valgfri):
      symbol, btc_ret_5m, stables={USDT:1.0,...}, spread_bps, data_stale_s, ws_down, funding_spike
    """
    ctx = ctx or {}
    _ensure_today()

    for gate in (_gate_safe_mode, _gate_news, _gate_cooldown, _gate_dayloss, _gate_time_session):
        ok, why = gate()
        if not ok:
            return (False, why)

    for gate in (_gate_loss_streak, _gate_btc_guard, _gate_depeg, _gate_safety):
        ok, why = gate(ctx)
        if not ok:
            return (False, why)

    return (True, "")