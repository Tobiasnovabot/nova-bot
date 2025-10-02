#!/usr/bin/env python3
from __future__ import annotations
from typing import Dict, Any, Tuple

def score_sentiment(features: Dict[str, float]) -> float:
    """
    features: {"fg_index": 0..100, "news_bias": -1..1, "vol_spike": 0..1}
    """
    fg = float(features.get("fg_index", 50.0))  # 0..100
    nb = float(features.get("news_bias", 0.0))  # -1..1
    vs = float(features.get("vol_spike", 0.0))  # 0..1
    # enkel aggregat: skaler FGI til -0.5..+0.5, add news, minus vol_spike
    return (fg-50.0)/100.0 + nb - 0.5*vs

def guard_sentiment(score: float, min_score: float=-0.25) -> Tuple[bool,str]:
    if score < min_score:
        return False, "sentiment_veto"
    return True, ""