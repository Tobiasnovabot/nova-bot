import os
from typing import List, Dict, Any, Tuple

# signal schema forventet per strategi:
# { "strategy":"SMA", "signal":"buy|sell|flat", "score":float(-1..1), "conf":float(0..1) }

BUY, SELL, FLAT = "buy", "sell", "flat"

def _norm_score(sig: Dict[str, Any]) -> float:
    s = float(sig.get("score", 0.0))
    c = float(sig.get("conf", 1.0))
    s = max(-1.0, min(1.0, s))
    c = max(0.0, min(1.0, c))
    # vekt = confidence; uten score -> bruk retning
    if "score" not in sig or abs(s) < 1e-9:
        if sig.get("signal") == BUY: s = 1.0
        elif sig.get("signal") == SELL: s = -1.0
        else: s = 0.0
    return s * c

def _majority(signals: List[Dict[str, Any]]) -> Tuple[str, float, Dict[str,int]]:
    up = sum(1 for s in signals if (s.get("signal") == BUY))
    dn = sum(1 for s in signals if (s.get("signal") == SELL))
    fl = sum(1 for s in signals if (s.get("signal") == FLAT))
    if up > dn and up >= fl: return BUY, 1.0, {"up":up,"down":dn,"flat":fl}
    if dn > up and dn >= fl: return SELL,-1.0, {"up":up,"down":dn,"flat":fl}
    return FLAT, 0.0, {"up":up,"down":dn,"flat":fl}

def _score_weighted(signals: List[Dict[str, Any]], th_buy=0.2, th_sell=-0.2) -> Tuple[str, float, Dict[str,float]]:
    wsum = 0.0
    for s in signals: wsum += abs(_norm_score(s))
    if wsum == 0: return FLAT, 0.0, {"agg":0.0}
    agg = sum(_norm_score(s) for s in signals) / wsum
    if agg >= th_buy:  return BUY,  agg, {"agg":agg}
    if agg <= th_sell: return SELL, agg, {"agg":agg}
    return FLAT, agg, {"agg":agg}

def decide(signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    mode = os.getenv("NOVAX_VOTER", "score").lower()  # "score" | "majority" | "auto"
    mode = mode if mode in ("score","majority","auto") else "score"
    # tomt -> flat
    if not signals: return {"action": FLAT, "score": 0.0, "meta": {"mode":mode,"reason":"no_signals"}}

    if mode in ("score","auto"):
        action, score, meta = _score_weighted(signals)
        if action != FLAT or mode == "score":
            return {"action": action, "score": float(score), "meta": {"mode":"score","**":meta}}

    # fallback til majority
    action, score, meta = _majority(signals)
    return {"action": action, "score": float(score), "meta": {"mode":"majority","**":meta}}
