#!/usr/bin/env python3
from __future__ import annotations

def regime_weights(regime: str) -> dict:
    """
    Returnerer vekter for signalfamilier gitt regime.
    regime: "bull", "bear", "chop"
    """
    if regime == "bull":  return {"trend": 1.00, "mr": 0.35, "breakout": 0.65}
    if regime == "bear":  return {"trend": 0.70, "mr": 0.20, "breakout": 0.30}
    return {"trend": 0.45, "mr": 0.65, "breakout": 0.30}  # chop

def blend_score(scores: dict, w: dict) -> float:
    """scores: {'trend':x,'mr':y,'breakout':z} → blandet score."""
    return (scores.get("trend",0)*w.get("trend",0)
          + scores.get("mr",0)*w.get("mr",0)
          + scores.get("breakout",0)*w.get("breakout",0))