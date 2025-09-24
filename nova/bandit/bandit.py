#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
import math
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from nova.core_boot.core_boot import now_oslo

# -------- intern tilstand --------
BANDIT: Dict[str, Any] = {
    "strats": {},                  # name -> Beta + stats
    "symbols": {},                 # sym  -> wins/loss/score
    "decay": {"daily": 0.01, "last_day": None},  # 1%/dag mot prior
    "prior": {"alpha": 1.0, "beta": 1.0},
    "candidates": ["ema_rsi", "macd_bb", "brk_atr"],
}

def reset_bandit():
    BANDIT["strats"].clear()
    BANDIT["symbols"].clear()
    BANDIT["decay"]["last_day"] = None

def get_bandit_state() -> Dict[str, Any]:
    return BANDIT

def set_bandit_state(st: Dict[str, Any]) -> None:
    BANDIT.clear()
    BANDIT.update(st)

# -------- hjelpere --------
def _welford_update(d: Dict[str, Any], x: float):
    # rullerende mean/std
    n = d.get("n", 0) + 1
    mean = d.get("mean", 0.0)
    m2 = d.get("m2", 0.0)
    delta = x - mean
    mean += delta / n
    m2 += delta * (x - mean)
    d["n"], d["mean"], d["m2"] = n, mean, m2
    d["std"] = math.sqrt(max(m2 / n, 0.0)) if n > 0 else 0.0

def _sharpe_light(mean: float, std: float) -> float:
    # 0.5..1.5, mer på stabil positiv reward
    if std <= 1e-12:
        return 1.0 if mean == 0 else 1.5
    s = mean / (std + 1e-12)
    return float(max(0.5, min(1.5, 1.0 + 0.25 * s)))

def _ensure_strat(name: str):
    if name not in BANDIT["strats"]:
        prior = BANDIT["prior"]
        BANDIT["strats"][name] = {
            "alpha": float(prior["alpha"]),
            "beta": float(prior["beta"]),
            "n": 0,
            "mean": 0.0,
            "m2": 0.0,
            "std": 0.0,
        }

def ensure_strats(names: List[str]):
    for n in names:
        _ensure_strat(n)

def bandit_decay_daily(now_day: Optional[str] = None):
    day = now_day or now_oslo().date().isoformat()
    last = BANDIT["decay"].get("last_day")
    if last == day:
        return
    # lineær mot prior (enkel, stabil)
    rate = float(BANDIT["decay"].get("daily", 0.01))
    prior = BANDIT["prior"]
    for s, d in BANDIT["strats"].items():
        d["alpha"] = (1 - rate) * d["alpha"] + rate * prior["alpha"]
        d["beta"]  = (1 - rate) * d["beta"]  + rate * prior["beta"]
        # hold stats også litt ferske
        d["mean"] *= (1 - rate)
        d["m2"]   *= (1 - rate)
        d["std"]   = d["std"] * math.sqrt(max(1 - rate, 0.0))
    BANDIT["decay"]["last_day"] = day

# -------- API --------
def choose_strat(meta: Dict[str, Any]) -> str:
    # kandidater fra meta eller default
    cands = meta.get("candidates") or BANDIT.get("candidates") or []
    if not cands:
        return ""
    ensure_strats(cands)
    bandit_decay_daily()

    # Thompson sampling * Sharpe-light vekt
    import random
    best_name, best_score = "", -1.0
    for name in cands:
        d = BANDIT["strats"][name]
        a, b = max(d["alpha"], 1e-6), max(d["beta"], 1e-6)
        sample = random.betavariate(a, b)
        w = _sharpe_light(d.get("mean", 0.0), d.get("std", 0.0))
        score = sample * w
        if score > best_score:
            best_name, best_score = name, score
    return best_name

def bandit_update(result: Dict[str, Any]) -> None:
    """
    result:
      strat: str
      reward: float            # f.eks. realisert PnL i R eller USDT
      atr_pct: float|None      # valgfri; risikojustering
      symbol: str|None
    """
    name = str(result.get("strat", ""))
    if not name:
        return
    _ensure_strat(name)
    d = BANDIT["strats"][name]

    reward = float(result.get("reward", 0.0))
    atr_pct = float(result.get("atr_pct", 0.0)) if result.get("atr_pct") is not None else 0.0
    # enkel risikojustering
    if atr_pct > 0:
        reward_adj = reward / max(atr_pct, 1e-6)
    else:
        reward_adj = reward

    # binær oppdatering + styrke fra reward
    if reward_adj > 0:
        d["alpha"] += 1.0 * min(1.0, 0.5 + 0.5 * math.tanh(abs(reward_adj)))
    elif reward_adj < 0:
        d["beta"]  += 1.0 * min(1.0, 0.5 + 0.5 * math.tanh(abs(reward_adj)))
    else:
        # liten nøytral nudge mot prior
        d["alpha"] += 0.05
        d["beta"]  += 0.05

    d["n"] = int(d.get("n", 0)) + 1
    _welford_update(d, reward_adj)

    # symbol-score
    sym = result.get("symbol")
    if sym:
        s = BANDIT["symbols"].setdefault(sym, {"wins":0, "losses":0, "n":0, "mean":0.0, "score":0.0})
        s["n"] += 1
        if reward > 0: s["wins"] += 1
        if reward < 0: s["losses"] += 1
        # oppdater mean
        mu = s["mean"]
        s["mean"] = mu + (reward - mu) / s["n"]
        winrate = s["wins"] / max(1, s["n"])
        s["score"] = 0.7 * winrate + 0.3 * math.tanh(s["mean"])
