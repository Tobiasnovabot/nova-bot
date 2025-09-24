#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
import itertools, math, random
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, Iterable, Optional

import numpy as np
import pandas as pd

from nova.indicators.indicators import ema, atr as atr_wilder
from nova.pnl_costs.pnl_costs import apply_fees_slip

# ---------- Broker ----------

@dataclass
class _Pos:
    qty: float = 0.0
    avg: float = 0.0

class PaperBroker:
    def __init__(self, fee_bps: float = 10.0, slip_bps: float = 15.0, cash_usdt: float = 10_000.0):
        self.fee_bps = float(fee_bps)
        self.slip_bps = float(slip_bps)
        self.cash = float(cash_usdt)
        self.pos = _Pos()
        self.trades: List[Dict[str, Any]] = []
        self.realized = 0.0

    def position(self) -> float:
        return self.pos.qty

    def equity(self, last: float) -> float:
        return self.cash + self.pos.qty * last

    def buy(self, qty: float, price: float):
        if qty <= 0: return
        f = apply_fees_slip({"side":"buy","qty":qty,"price":price,"maker":False,"taker_fee_bps":self.fee_bps,"slip_bps":self.slip_bps})
        self.cash -= f["net_usd"]
        total_cost = self.pos.avg * self.pos.qty + f["net_usd"]
        self.pos.qty += qty
        self.pos.avg = total_cost / max(self.pos.qty, 1e-12)
        self.trades.append({"side":"buy","qty":qty,"price":price,"eff_price":f["eff_price"],"fee":f["fee_usd"]})

    def sell(self, qty: float, price: float):
        if qty <= 0: return
        qty = min(qty, self.pos.qty)
        f = apply_fees_slip({"side":"sell","qty":qty,"price":price,"maker":False,"taker_fee_bps":self.fee_bps,"slip_bps":self.slip_bps})
        self.cash += f["net_usd"]
        pnl = (f["eff_price"] - self.pos.avg) * qty - f["fee_usd"]
        self.realized += pnl
        self.pos.qty -= qty
        if self.pos.qty <= 1e-12:
            self.pos.qty = 0.0
        self.trades.append({"side":"sell","qty":qty,"price":price,"eff_price":f["eff_price"],"fee":f["fee_usd"],"pnl":pnl})

# ---------- Splits ----------

def walk_forward_splits(n: int, train: int, test: int, purge: int = 0) -> List[Tuple[range, range]]:
    out = []
    start = 0
    while start + train + purge + test <= n:
        tr = range(start, start + train)
        te = range(start + train + purge, start + train + purge + test)
        out.append((tr, te))
        start += test
    return out

def purged_kfold_splits(n: int, k: int, purge: int = 0) -> List[Tuple[range, range]]:
    fold = n // k
    out = []
    for i in range(k):
        te_start = i * fold
        te_end = te_start + fold if i < k - 1 else n
        tr1 = range(0, max(0, te_start - purge))
        tr2 = range(min(n, te_end + purge), n)
        # representerer train som to ranges; for enkelhet returner bare test her
        out.append((tr1, range(te_start, te_end)))
    return out

# ---------- Strategy (EMA cross + ATR stop/TP) ----------

def _prep(df: pd.DataFrame, p_fast: int, p_slow: int, atr_p: int) -> pd.DataFrame:
    out = df.copy()
    out["ema_f"] = ema(out["close"], p_fast)
    out["ema_s"] = ema(out["close"], p_slow)
    out["atr"] = atr_wilder(out["high"], out["low"], out["close"], atr_p)
    out["cross_up"] = (out["ema_f"].shift(1) <= out["ema_s"].shift(1)) & (out["ema_f"] > out["ema_s"])
    out["cross_dn"] = (out["ema_f"].shift(1) >= out["ema_s"].shift(1)) & (out["ema_f"] < out["ema_s"])
    return out

def _size_from_risk(usd_risk: float, stop_dist: float) -> float:
    if stop_dist <= 1e-12: return 0.0
    return max(0.0, usd_risk / stop_dist)

def _run_core(df: pd.DataFrame, params: Dict[str, Any], seed: int = 42) -> Dict[str, Any]:
    random.seed(seed); np.random.seed(seed)
    fee_bps = float(params.get("fee_bps", 10.0))
    slip_bps = float(params.get("slip_bps", 10.0))
    risk_usd = float(params.get("risk_usd", 100.0))
    atr_k = float(params.get("atr_k_stop", 2.0))
    tp_R = float(params.get("tp_R", 2.0))
    pfast = int(params.get("ema_fast", 12))
    pslow = int(params.get("ema_slow", 26))
    patr = int(params.get("atr_p", 14))

    data = _prep(df, pfast, pslow, patr)
    broker = PaperBroker(fee_bps=fee_bps, slip_bps=slip_bps, cash_usdt=float(params.get("cash0", 10_000.0)))

    entry_px = None
    stop_px = None
    tp_px = None
    equity_curve = []

    for i in range(max(pslow, patr) + 2, len(data)):
        row = data.iloc[i]
        px_open = float(df["open"].iloc[i])
        px_high = float(df["high"].iloc[i])
        px_low  = float(df["low"].iloc[i])
        px_close= float(df["close"].iloc[i])
        atrv = float(row["atr"] or 0.0)

        # manage open position
        if broker.position() > 0:
            # stop or TP intrabar
            hit_stop = stop_px is not None and px_low <= stop_px
            hit_tp   = tp_px   is not None and px_high >= tp_px

            if hit_stop and hit_tp:
                # assume best for test determinisme: TP first
                hit_stop = False

            if hit_stop:
                broker.sell(broker.position(), stop_px)
                entry_px = stop_px = tp_px = None
            elif hit_tp:
                broker.sell(broker.position(), tp_px)
                entry_px = stop_px = tp_px = None
            elif bool(row["cross_dn"]):
                broker.sell(broker.position(), px_close)
                entry_px = stop_px = tp_px = None

        # entries
        if broker.position() == 0 and bool(row["cross_up"]) and atrv > 0:
            stop_dist = atr_k * atrv
            qty = _size_from_risk(risk_usd, stop_dist)
            if qty > 0:
                broker.buy(qty, px_close)
                entry_px = px_close
                stop_px = entry_px - stop_dist
                tp_px = entry_px + tp_R * stop_dist

        equity_curve.append(broker.equity(px_close))

    trades = broker.trades
    net_pnl = broker.realized
    wins = sum(1 for t in trades if t.get("pnl", 0.0) > 0)
    sells = [t for t in trades if t["side"] == "sell"]
    hit_rate = wins / max(1, len(sells))
    avg_trade = (sum(t.get("pnl", 0.0) for t in sells) / max(1, len(sells))) if sells else 0.0

    eq = np.array(equity_curve, dtype=float)
    rets = np.diff(eq) / np.clip(eq[:-1], 1e-12, None)
    sharpe_light = float(np.mean(rets) / (np.std(rets) + 1e-12)) if len(rets) > 5 else 0.0

    return {
        "equity_curve": equity_curve,
        "trades": trades,
        "metrics": {
            "net_pnl": float(net_pnl),
            "hit_rate": float(hit_rate),
            "avg_trade": float(avg_trade),
            "sharpe_light": float(sharpe_light),
            "n_trades": int(len(sells)),
            "equity_end": float(eq[-1] if len(eq) else broker.cash),
        },
    }

# ---------- Public API ----------

def run_backtest(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    cfg: {
      'df': DataFrame[open,high,low,close,volume],
      'params': {...}, 'seed': int
    }
    """
    df = cfg["df"]
    params = dict(cfg.get("params", {}))
    seed = int(cfg.get("seed", 42))
    return _run_core(df, params, seed)

def grid_search(df: pd.DataFrame, grid: Dict[str, Iterable], seed: int = 42) -> Dict[str, Any]:
    """
    Brute-force grid på EMA/ATR/risiko-parametre. Returnerer best + leaderboard.
    """
    keys = list(grid.keys())
    best = None
    board: List[Tuple[float, Dict[str, Any]]] = []
    for vals in itertools.product(*[grid[k] for k in keys]):
        params = {k: v for k, v in zip(keys, vals)}
        res = _run_core(df, params, seed)
        score = res["metrics"]["net_pnl"]
        board.append((score, params))
        if best is None or score > best[0]:
            best = (score, params)
    board.sort(key=lambda x: x[0], reverse=True)
    return {"best": {"score": best[0], "params": best[1]}, "leaderboard": board[:10]}
