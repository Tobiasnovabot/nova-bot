#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple

# -------- Factor attribution (OLS) --------
def factor_attribution(ret: pd.Series, factors: pd.DataFrame) -> Dict[str, Any]:
    """
    OLS: ret = a + B * factors + e
    Returnerer: {'alpha','betas':{f:beta},'r2','contrib':{f:beta*cov(f,ret)}}
    """
    df = pd.concat([ret.rename("y"), factors], axis=1).dropna()
    if len(df) < factors.shape[1] + 2:
        return {"alpha": 0.0, "betas": {}, "r2": 0.0, "contrib": {}}
    y = df["y"].to_numpy(dtype=float)
    X = df[factors.columns].to_numpy(dtype=float)
    X = np.column_stack([np.ones(len(X)), X])
    # OLS
    XtX = X.T @ X
    try:
        beta = np.linalg.solve(XtX, X.T @ y)
    except np.linalg.LinAlgError:
        beta = np.linalg.pinv(XtX) @ (X.T @ y)
    yhat = X @ beta
    resid = y - yhat
    ss_tot = np.sum((y - y.mean())**2)
    ss_res = np.sum(resid**2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    betas = {name: float(b) for name, b in zip(factors.columns, beta[1:])}
    contrib = {}
    for i, name in enumerate(factors.columns):
        contrib[name] = float(betas[name] * np.cov(df[name].values, y, ddof=1)[0,1])
    return {"alpha": float(beta[0]), "betas": betas, "r2": float(r2), "contrib": contrib}

# -------- Hedge ratio (variance-minimizing beta) --------
def hedge_ratio(y: pd.Series, x: pd.Series, *, ew_lambda: float = None) -> float:
    """
    Beta = cov(y,x)/var(x). Hvis ew_lambda settes (0<λ<1), bruk EWMA.
    """
    df = pd.concat([y.rename("y"), x.rename("x")], axis=1).dropna()
    if len(df) < 3:
        return 0.0
    if ew_lambda is None:
        vx = np.var(df["x"].values, ddof=1)
        cxy = np.cov(df["y"].values, df["x"].values, ddof=1)[0,1]
        return float(cxy / vx) if vx > 0 else 0.0
    # EWMA
    lam = float(ew_lambda)
    dy = df["y"].values
    dx = df["x"].values
    mx = 0.0; my = 0.0
    cov = 0.0; varx = 0.0
    wsum = 0.0
    w = 1.0
    for i in range(len(df)-1, -1, -1):
        wsum += w
        mx = (1 - w/wsum) * mx + (w/wsum) * dx[i]
        my = (1 - w/wsum) * my + (w/wsum) * dy[i]
        w *= lam
    w = 1.0
    for i in range(len(df)-1, -1, -1):
        cov = lam*cov + (1-lam) * (dx[i]-mx)*(dy[i]-my)
        varx = lam*varx + (1-lam) * (dx[i]-mx)*(dx[i]-mx)
    return float(cov / varx) if varx > 0 else 0.0

# -------- Kelly frontier (mean-variance approx) --------
def kelly_frontier(mu: np.ndarray, Sigma: np.ndarray, leverages: List[float] = None, *, nonneg: bool = True) -> Dict[str, Any]:
    """
    Approx: w* = Sigma^{-1} mu. Skaler langs leverages.
    nonneg=True klipper negative vekter til 0 og renormaliserer.
    Returnerer {'base':w*, 'curve':[(L, wL)]}
    """
    mu = np.asarray(mu, dtype=float).reshape(-1, 1)
    Sigma = np.asarray(Sigma, dtype=float)
    n = mu.shape[0]
    if leverages is None:
        leverages = [0.0, 0.5, 1.0, 1.5, 2.0]
    try:
        inv = np.linalg.inv(Sigma)
    except np.linalg.LinAlgError:
        inv = np.linalg.pinv(Sigma)
    w_star = (inv @ mu).reshape(-1)
    if nonneg:
        w_star = np.clip(w_star, 0.0, None)
    s = w_star.sum()
    if s > 0:
        w_star = w_star / s
    curve = []
    for L in leverages:
        wL = w_star * float(L)
        if nonneg and wL.sum() > 0:
            wL = wL / wL.sum() * L
        curve.append((float(L), wL))
    return {"base": w_star, "curve": curve}

# -------- Risk-premium scoring --------
def risk_premium_scores(df: pd.DataFrame) -> pd.Series:
    """
    Forventede kolonner: ['basis_bps','funding_rate','carry_bps','mom_bps']
    Z-score hvert felt og ta snitt -> score 0..1 etter sigmoide.
    """
    use_cols = [c for c in ["basis_bps","funding_rate","carry_bps","mom_bps"] if c in df.columns]
    if not use_cols:
        return pd.Series(dtype=float)
    Z = {}
    for c in use_cols:
        x = df[c].astype(float)
        m = x.mean(); s = x.std(ddof=0)
        Z[c] = (x - m) / (s if s > 0 else 1.0)
    Zdf = pd.DataFrame(Z)
    z = Zdf.mean(axis=1)
    score = 1.0 / (1.0 + np.exp(-z))  # 0..1
    return pd.Series(score, index=df.index, name="risk_premium_score")