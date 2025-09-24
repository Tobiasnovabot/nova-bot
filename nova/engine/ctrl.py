#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-

import os
from typing import Tuple, Dict, Any

from nova.stateio.stateio import load_state, save_state
from nova.risk.risk import apply_risk_level
from nova.notify import send as tg_send

_LAST: Dict[str, Any] = {"safe": None}

def _to_float(x, d=0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(d)

def engine_ctrl_tick() -> Tuple[int, str]:
    """
    Les "ctrl" fra state og:
      - Returner (loop_sec, action) der action ∈ {"", "stop", "once", "reload"}
      - Overstyr risk-level dynamisk (safe-mode + DD-cap)
      - (Valgfritt) overstyr mode i state ("paper"/"live")
    Kalles én gang per loop i engine.run.
    """
    s = load_state() or {}
    ctrl = dict(s.get("ctrl", {}) or {})

    # 1) Loop-hastighet
    loop_sec = int(ctrl.get("engine_loop_sec") or int(os.getenv("ENGINE_LOOP_SEC", "30") or 30))

    # 2) Mode-override (skriv til state; selve kobling mot exchange skjer i engine)
    mode_override = (ctrl.get("mode_override") or "").lower()
    if mode_override in ("paper", "live") and s.get("mode") != mode_override:
        s["mode"] = mode_override
        save_state(s)
        try: tg_send(f"⚙️ Engine mode → {mode_override}")
        except Exception: pass

    # 3) Safe-mode / DD-cap → effektivt risk-level
    eq = _to_float(s.get("equity_usd"), 0.0)
    dd_usd = _to_float(s.get("dd_day_usd"), 0.0)
    dd_pct = (dd_usd / eq * 100.0) if eq > 0 else 0.0

    ddcap = _to_float(ctrl.get("max_dd_day_pct"), 0.0)  # f.eks. 3.0
    safe_req = bool(ctrl.get("safe_mode", False))
    if ddcap and dd_pct <= -abs(ddcap):
        safe_req = True

    was_safe = _LAST.get("safe")
    if was_safe is None or was_safe != safe_req:
        _LAST["safe"] = safe_req
        try:
            tg_send("🟡 Safe-mode ON (risiko redusert)") if safe_req else tg_send("🟢 Safe-mode OFF (normal risiko)")
        except Exception:
            pass

    level = int(((s.get("risk") or {}).get("level") or 5))
    level_eff = max(1, level - (3 if safe_req else 0))
    apply_risk_level(level_eff, equity_usd=eq)

    # 4) Enkle engine-kommandoer
    action = ""
    cmd = (ctrl.get("engine_cmd") or "").lower()
    if cmd in ("stop", "once", "reload"):
        action = cmd
        ctrl["engine_cmd"] = ""
        s["ctrl"] = ctrl
        save_state(s)
        try:
            if action == "stop":   tg_send("⏹️ Engine: stop-kommando mottatt.")
            if action == "once":   tg_send("▶️ Engine: kjører én runde til, så stopper.")
            if action == "reload": tg_send("🔁 Engine: reload-kommando mottatt.")
        except Exception:
            pass

    return loop_sec, action