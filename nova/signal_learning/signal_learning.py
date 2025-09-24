#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

# ---------- Meta-labeling ----------
def meta_labeling(entries: pd.Series, exits: pd.Series, pnl: pd.Series, *, thr: float = 0.0) -> pd.Series:
    """
    Meta-labeling:
      1 = god trade (pnl > thr), 0 = dårlig trade
    entries/exits: bool-serier som markerer trades
    pnl: PnL pr trade (samme index som exits)
    """
    labels = pd.Series(0, index=pnl.index, dtype=int)
    labels[(exits) & (pnl > thr)] = 1
    return labels

# ---------- Bayesisk tuning ----------
def bayes_tune_threshold(successes: int, fails: int, *, prior_a: float = 1.0, prior_b: float = 1.0) -> float:
    """
    Enkel Beta-Bayes oppdatering.
    Returnerer forventet suksessrate etter oppdatering.
    """
    a = prior_a + successes
    b = prior_b + fails
    return float(a / (a + b))

# ---------- Orderbook-kø modell ----------
def ob_queue_fill_prob(placed: int, queue: int, cancels: int, *, lookahead: int = 1) -> float:
    """
    Estimer sannsynlighet for at en ordre blir fylt gitt OB-kø.
    placed: vår ordre-størrelse
    queue: volum foran oss i køen
    cancels: estimert andel av queue som kanselleres
    lookahead: antall trade-størrelser vi "ser" fremover (proxy).
    """
    eff_front = max(0.0, queue - cancels)
    if placed <= 0: 
        return 0.0
    # sannsynlighet = hvor mye av front som forventes fylt vs vårt
    prob = min(1.0, (lookahead * placed) / (placed + eff_front))
    return float(prob)