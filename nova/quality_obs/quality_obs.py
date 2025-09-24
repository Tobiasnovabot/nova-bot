#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
import math, json, time
from typing import Dict, Any, Optional, Sequence, Tuple
import numpy as np
import pandas as pd
from pathlib import Path

from nova.core_boot.core_boot import NOVA_HOME, now_oslo
from nova.stateio.stateio import read_json_atomic, write_json_atomic

# ---------- Data quality ----------

def _psi(p: np.ndarray, q: np.ndarray, eps: float = 1e-12) -> float:
    p = np.clip(p, eps, 1.0)
    q = np.clip(q, eps, 1.0)
    return float(np.sum((p - q) * np.log(p / q)))

def _hist_proportions(x: np.ndarray, bins: int = 10) -> Tuple[np.ndarray, np.ndarray]:
    if x.size == 0 or np.allclose(x.max(), x.min()):
        # ensartet eller tom -> alt i én bøtte
        return np.array([1.0]), np.array([x.min(), x.max()+1e-9])
    hist, edges = np.histogram(x, bins=bins)
    prop = hist / max(1, hist.sum())
    return prop.astype(float), edges

def data_quality_metrics(df: pd.DataFrame, *, baseline_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Returnerer nøkkel-metrikker:
      freshness_sec (krever 'ts' kolonne med epoch-sec eller iso),
      completeness_ratio (andel ikke-NaN),
      psi_per_col (drift mot lagret baseline), ks_proxy (enkel distanse).
    Oppdaterer baseline hvis mangler.
    """
    out: Dict[str, Any] = {"freshness_sec": None, "completeness_ratio": None, "psi_per_col": {}, "ks_proxy": {}}
    n = len(df)
    if "ts" in df.columns and n > 0:
        try:
            ts = pd.to_datetime(df["ts"]).astype("int64") // 10**9
            freshness = time.time() - float(ts.iloc[-1])
            out["freshness_sec"] = float(max(0.0, freshness))
        except Exception:
            out["freshness_sec"] = None

    # completeness (andel ikke-NaN over alle felter)
    if n > 0:
        total = float(df.shape[0] * df.shape[1])
        non_na = float(df.notna().sum().sum())
        out["completeness_ratio"] = non_na / total if total > 0 else 1.0
    else:
        out["completeness_ratio"] = 0.0

    # baseline-filsti
    bpath = baseline_path or (NOVA_HOME / "data" / "dq_baseline.json")
    b = read_json_atomic(bpath, default={}) or {}
    changed = False

    # PSI + KS-proxy for numeriske kolonner
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    for c in num_cols:
        x = pd.Series(df[c], dtype=float).dropna().to_numpy()
        if x.size < 5:
            out["psi_per_col"][c] = None
            out["ks_proxy"][c] = None
            continue
        prop_cur, edges = _hist_proportions(x, bins=10)
        key = f"{c}::edges"
        if key not in b or f"{c}::prop" not in b:
            # init baseline
            b[key] = edges.tolist()
            b[f"{c}::prop"] = prop_cur.tolist()
            changed = True
            out["psi_per_col"][c] = 0.0
            out["ks_proxy"][c] = 0.0
        else:
            # re-bucket current to baseline edges for PSI sammenligning
            edges_b = np.array(b[key], dtype=float)
            hist, _ = np.histogram(x, bins=edges_b)
            prop_reb = hist / max(1, hist.sum())
            prop_base = np.array(b[f"{c}::prop"], dtype=float)
            out["psi_per_col"][c] = _psi(prop_reb, prop_base)
            # KS-proxy: maksimal absolutt differanse
            out["ks_proxy"][c] = float(np.max(np.abs(prop_reb - prop_base)))

    if changed:
        write_json_atomic(bpath, b, backup=False)
    return out

# ---------- Edge dashboard ----------

def edge_dashboard_snapshot(metrics: Dict[str, Any]) -> Path:
    """
    Lagrer snapshot til logs/edge_dashboard.json (append JSONL + siste state).
    """
    logs = NOVA_HOME / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    jline = {"ts": now_oslo().isoformat(), **metrics}
    # append JSONL
    jsonl = logs / "edge_dashboard.jsonl"
    with jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(jline, ensure_ascii=False) + "\n")
    # siste state for enkel visualisering
    latest = logs / "edge_dashboard.json"
    write_json_atomic(latest, jline, backup=False)
    return latest

# ---------- Canary presets ----------

def canary_presets_decide(control: Dict[str, float], canary: Dict[str, float], *,
                          tol_drawdown_pct: float = 2.0,
                          tol_hitrate_drop: float = 0.10,
                          min_trades: int = 20) -> Dict[str, Any]:
    """
    Enkelt beslutningsregel:
      - hvis canary n_trades < min_trades -> hold
      - hvis canary dd_pct > control dd_pct + tol_drawdown_pct -> rollback
      - hvis canary hit_rate < control*(1 - tol_hitrate_drop) -> rollback
      - ellers promote hvis canary net_pnl > control net_pnl
    Returnerer {'decision': 'hold|rollback|promote', 'why': str}
    """
    c = {k: float(control.get(k, 0.0)) for k in ("net_pnl","hit_rate","dd_pct","n_trades")}
    a = {k: float(canary.get(k, 0.0)) for k in ("net_pnl","hit_rate","dd_pct","n_trades")}
    if a["n_trades"] < min_trades:
        return {"decision":"hold","why":"insufficient_trades"}
    if a["dd_pct"] > c["dd_pct"] + tol_drawdown_pct:
        return {"decision":"rollback","why":"drawdown_exceeds_tolerance"}
    if a["hit_rate"] < max(0.0, c["hit_rate"] * (1.0 - tol_hitrate_drop)):
        return {"decision":"rollback","why":"hit_rate_drop"}
    if a["net_pnl"] > c["net_pnl"]:
        return {"decision":"promote","why":"net_pnl_better"}
    return {"decision":"hold","why":"no_clear_advantage"}