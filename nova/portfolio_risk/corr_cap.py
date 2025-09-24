#!/usr/bin/env python3
from __future__ import annotations
from typing import Dict, Any, List, Tuple
import math

def _norm(v: List[float]) -> float: return math.sqrt(sum(x*x for x in v)) or 1.0

def corr_cap_ok(active_betas: Dict[str, float],
                new_sym: str, new_beta: float,
                max_dot_frac: float = 0.55) -> Tuple[bool, str]:
    """
    Enkelt “dot product”-vern: summer β·w for aktive eksponeringer.
    Hvis projeksjon av ny posisjon på eksisterende “risikoretning” > terskel, avvis.
    active_betas: {sym: beta mot “krypto-risiko” (f.eks. mot BTC/USDT)}
    new_beta: beta for nytt symbol
    """
    if not active_betas: return True, "ok"
    # Vekt lik USD-andel for enkelhet (her antar vi alle like – juster om du har faktiske weights)
    b = list(active_betas.values())
    vnorm = _norm(b)
    dot = (sum(b) / vnorm) * (new_beta / 1.0)  # skalert projeksjon
    return (abs(dot) <= max_dot_frac), ("ok" if abs(dot) <= max_dot_frac else "corr_gate")