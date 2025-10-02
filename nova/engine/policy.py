from __future__ import annotations
import json, os, time
from typing import Dict, List
from pathlib import Path
from nova.bandit.contextual import ContextualBandit
from nova.regime.detector import RegimeDetector

REGIME_MAP_PATH = Path("config/strategies.regimes.json")

_bandit = ContextualBandit(decay=float(os.getenv("BANDIT_DECAY","0.97")),
                           eps_floor=float(os.getenv("BANDIT_EPS","0.02")))
_regime = RegimeDetector()

def _load_regime_map()->Dict[str,List[str]]:
    if REGIME_MAP_PATH.exists():
        return json.loads(REGIME_MAP_PATH.read_text())
    return {"trend":[], "meanrev":[], "highvol":[], "lowvol":[]}

_REGIME_ALLOW = _load_regime_map()

def choose(symbol:str, candidates:List[str], ctx:Dict[str,float])->str:
    """
    Velger én strategi fra 'candidates' gitt kontekst.
    Filtrerer på regime allowlist først. Faller tilbake til første kandidat.
    """
    if not candidates:
        raise ValueError("candidates is empty")
    regime = _regime.classify({
        "atr_z": ctx.get("atr_z", 0.0),
        "trend": ctx.get("trend", 0.0),
    })
    allow = _REGIME_ALLOW.get(regime, []) or candidates
    pool = [s for s in candidates if s in allow] or candidates
    try:
        pick = _bandit.choose(pool, {
            "atr_pct": ctx.get("atr_pct", 0.0),
            "spread_bp": ctx.get("spread_bp", 0.0),
            "trend": ctx.get("trend", 0.0),
            "hour": ctx.get("hour", 0.0),
            "funding_bp": ctx.get("funding_bp", 0.0),
            "lambda_slip": ctx.get("lambda_slip", 0.3),
            "lambda_hold": ctx.get("lambda_hold", 0.05),
        })
        return pick
    except Exception:
        return pool[0]

def reward(strat:str, ctx:Dict[str,float], reward:float)->None:
    _bandit.update(strat, {
        "atr_pct": ctx.get("atr_pct", 0.0),
        "spread_bp": ctx.get("spread_bp", 0.0),
        "trend": ctx.get("trend", 0.0),
        "hour": ctx.get("hour", 0.0),
        "funding_bp": ctx.get("funding_bp", 0.0),
        "lambda_slip": ctx.get("lambda_slip", 0.3),
        "lambda_hold": ctx.get("lambda_hold", 0.05),
        "slippage_bp": ctx.get("slippage_bp", 0.0),
        "hold_hrs": ctx.get("hold_hrs", 0.0),
    }, reward)

def snapshot()->Dict[str,float]:
    return _bandit.snapshot()
