#!/usr/bin/env python3
from __future__ import annotations
from typing import Dict, Any, Tuple
from datetime import datetime, timezone, timezone
from nova.stateio.stateio import load_state, save_state
from nova.notify import send as tg_send

def _pct(a: float, b: float) -> float: return 100.0 * (a / b) if b else 0.0

def kill_switch_tick(dd_cap_day_pct: float = 5.0,
                     trail_lock_pct: float = 3.0) -> Tuple[bool, str]:
    """
    Returnerer (halt, reason).
    - dd_cap_day_pct: hard intradag DD-limit (stopp all ny trading)
    - trail_lock_pct: lås inn gevinster: hvis day PnL topper og faller mer enn X% fra toppen → stopp ny trading
    """
    s = load_state() or {}
    eq = float(s.get("equity_usd") or 0.0)
    pnl_day = float(s.get("pnl_day") or 0.0)
    dd_day = float(s.get("dd_day_usd") or 0.0)
    top = float(s.get("pnl_day_top") or pnl_day)

    # oppdater topp
    if pnl_day > top:
        top = pnl_day
        s["pnl_day_top"] = top
        save_state(s)

    # hard dd-cap
    if eq > 0 and _pct(dd_day, eq) <= -abs(dd_cap_day_pct):
        try: tg_send(f"🔴 Kill-switch: DD {dd_day:.2f} USD ({_pct(dd_day,eq):.2f}%) ≤ −{dd_cap_day_pct}%")
        except Exception: pass
        return True, "dd_cap"

    # trailing lock-in: drawdown fra intradag-topp
    if top > 0 and (top - pnl_day) / top * 100.0 >= trail_lock_pct:
        try: tg_send(f"🟠 Kill-switch: trail lock {trail_lock_pct}% (top={top:+.2f}, now={pnl_day:+.2f})")
        except Exception: pass
        return True, "trail_lock"

    return False, ""