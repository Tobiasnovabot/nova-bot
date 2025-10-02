#!/usr/bin/env python3
from __future__ import annotations
def decide_role(last_peer_heartbeat: float, now: float, timeout_s: float=30.0) -> str:
    return "primary" if (now - last_peer_heartbeat) > float(timeout_s) else "standby"