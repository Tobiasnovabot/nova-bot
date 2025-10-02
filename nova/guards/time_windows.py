#!/usr/bin/env python3
from __future__ import annotations
from datetime import datetime, timezone, timezone
from typing import List, Tuple

def in_windows(now: datetime, windows: List[Tuple[int,int]]) -> bool:
    """windows: liste av (start_hour, end_hour) lokaltid; wrap støttes (22,3)."""
    h = now.hour
    for a,b in windows:
        if a==b: return True
        if a < b and (a <= h < b): return True
        if a > b and (h >= a or h < b): return True
    return False