#!/usr/bin/env python3
from __future__ import annotations
from typing import Dict, Any
from datetime import datetime, timezone, timedelta, timezone
from nova.stateio.stateio import load_state, save_state

def mark_stopout(sym: str, minutes: int = 60) -> None:
    s = load_state() or {}
    cd = s.get("cooldown", {})
    until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    cd[sym] = until.isoformat()
    s["cooldown"] = cd
    save_state(s)

def cooldown_ok(sym: str) -> bool:
    s = load_state() or {}
    cd = s.get("cooldown", {})
    iso = cd.get(sym)
    if not iso: return True
    try:
        until = datetime.fromisoformat(iso)
    except Exception:
        return True
    return datetime.now(timezone.utc) >= until