#!/usr/bin/env python3
from __future__ import annotations

def kelly_fraction(win_prob: float, win_loss_ratio: float, cap: float=0.08) -> float:
    """
    Enkel Kelly: f* = p - (1-p)/R. Caps til <= cap (8% default).
    """
    p = max(0.0, min(1.0, win_prob))
    R = max(1e-6, win_loss_ratio)
    f = p - (1 - p) / R
    return max(0.0, min(cap, f))

def kelly_qty_scale(prob: float, r: float) -> float:
    f = kelly_fraction(prob, r)
    return 0.5 + f  # 0.5–1.08x typisk