#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT/"data"/"liquidity_gate.json"

def load_gate():
    try:
        j=json.loads(GATE.read_text())
        blocked=set(j.get("blocked") or [])
        reason=j.get("reason") or {}
        return blocked, reason
    except Exception:
        return set(), {}

def is_blocked(symbol: str):
    blocked, reason = load_gate()
    if symbol in blocked:
        return True, reason.get(symbol, "blocked")
    return False, ""
