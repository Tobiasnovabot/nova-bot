#!/usr/bin/env python3
from __future__ import annotations
from typing import List, Tuple

def plan_twap(total_qty: float, slices: int = 4, min_slice: float = 0.0) -> List[float]:
    """
    Del opp ordre i like store skiver. Returnerer liste av del-qty.
    """
    if slices <= 1: return [total_qty]
    q = max(total_qty / slices, min_slice)
    parts = [q]*(slices-1)
    parts.append(max(0.0, total_qty - q*(slices-1)))
    return parts

def adaptive_slices(spread_bps: float, book_depth_usd: float) -> int:
    """
    Flere slices ved bred spread / liten depth.
    """
    s = 2
    if spread_bps > 12: s += 1
    if book_depth_usd < 5000: s += 1
    return min(8, max(2, s))