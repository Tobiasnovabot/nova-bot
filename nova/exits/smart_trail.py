#!/usr/bin/env python3
from __future__ import annotations
from typing import Tuple

def smart_trail(entry_px: float, last_px: float, atr: float,
                arm_rr: float = 1.0, trail_k: float = 1.2,
                to_breakeven_rr: float = 0.6) -> Tuple[float, float]:
    """
    Returnerer (stop_px, take_px).
    - Arm trailing først når R>=arm_rr
    - Trail-avstand = trail_k * ATR
    - Flytt til break-even når R>=to_breakeven_rr
    """
    rr = (last_px - entry_px) / max(1e-9, atr)
    stop = entry_px - 1.0 * atr  # init
    if rr >= to_breakeven_rr:
        stop = max(stop, entry_px)  # BE
    if rr >= arm_rr:
        stop = max(stop, last_px - trail_k * atr)
    take = entry_px + 3.0 * atr   # enkel TP
    return float(stop), float(take)