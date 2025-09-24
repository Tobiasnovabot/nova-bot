#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
from nova import paths as NPATH
import json, time, hashlib
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from nova.core_boot.core_boot import NOVA_HOME, now_oslo
from nova.stateio.stateio import read_json_atomic, write_json_atomic
from nova.pnl_costs.pnl_costs import apply_fees_slip

# ---------- WHAT-IF TRADE ----------

def what_if_trade(side: str, entry: float, qty: float, stop: float, tp: float,
                  prob_tp: float, fee_bps: float = 10.0, slip_bps: float = 10.0) -> Dict[str, float]:
    """
    Enkel 1-leg trade med ett av to utfall: TP eller STOP.
    Returnerer EV, R, PnL_tp, PnL_stop (USD).
    """
    side = side.lower()
    assert side in ("buy","sell")
    assert qty >= 0 and entry > 0
    prob_tp = max(0.0, min(1.0, float(prob_tp)))

    def _fill(price: float, s: str):
        return apply_fees_slip({"side": s, "qty": qty, "price": price, "maker": False,
                                "taker_fee_bps": fee_bps, "slip_bps": slip_bps})

    if side == "buy":
        buy = _fill(entry, "buy")
        sell_tp = _fill(tp, "sell")
        sell_st = _fill(stop, "sell")
        pnl_tp = (sell_tp["eff_price"] - buy["eff_price"]) * qty - (buy["fee_usd"] + sell_tp["fee_usd"])
        pnl_st = (sell_st["eff_price"] - buy["eff_price"]) * qty - (buy["fee_usd"] + sell_st["fee_usd"])
    else:
        sell = _fill(entry, "sell")
        buy_tp = _fill(tp, "buy")
        buy_st = _fill(stop, "buy")
        pnl_tp = (sell["eff_price"] - buy_tp["eff_price"]) * qty - (sell["fee_usd"] + buy_tp["fee_usd"])
        pnl_st = (sell["eff_price"] - buy_st["eff_price"]) * qty - (sell["fee_usd"] + buy_st["fee_usd"])

    ev = prob_tp * pnl_tp + (1.0 - prob_tp) * pnl_st
    risk = abs(pnl_st) if pnl_st < 0 else 0.0
    R = (ev / risk) if risk > 0 else 0.0
    return {"EV_usd": float(ev), "R": float(R), "PnL_tp": float(pnl_tp), "PnL_stop": float(pnl_st)}

# ---------- DIAGNOSTICS ----------

def diag_snapshot() -> Dict[str, Any]:
    """
    Lettvekts diagnostikk: filer, størrelser, data-ferskhet, siste equity.
    """
    data = NOVA_HOME / "data"; logs = NOVA_HOME / "logs"
    state_p = data / NPATH.STATE.as_posix(); trades_p = data / NPATH.TRADES.as_posix(); equity_p = data / NPATH.EQUITY.as_posix()
    now_ts = time.time()
    out: Dict[str, Any] = {
        "ts": now_oslo().isoformat(),
        "paths": { "state": state_p.exists(), "trades": trades_p.exists(), "equity": equity_p.exists() },
        "sizes": {},
        "fresh_sec": {},
        "bot_enabled": None,
        "ok": True,
    }
    for p in (state_p, trades_p, equity_p, logs / "run.out"):
        k = p.name
        if p.exists():
            out["sizes"][k] = p.stat().st_size
            out["fresh_sec"][k] = now_ts - p.stat().st_mtime
        else:
            out["sizes"][k] = None
            out["fresh_sec"][k] = None
            out["ok"] = False
    st = read_json_atomic(state_p, default={}) or {}
    out["bot_enabled"] = bool(st.get("bot_enabled", True))
    return out

# ---------- CONFIG VERSIONING ----------

_CFG_DIR = NOVA_HOME / "config"
_CFG_DIR.mkdir(parents=True, exist_ok=True)
_INDEX = _CFG_DIR / "versions.json"

def _hash_obj(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

def cfg_save(tag: str, cfg: Dict[str, Any]) -> Path:
    """
    Lagre en konfig snapshot under config/<tag>.json og oppdater index.
    """
    _CFG_DIR.mkdir(parents=True, exist_ok=True)
    path = _CFG_DIR / f"{tag}.json"
    write_json_atomic(path, cfg, backup=False)
    idx = read_json_atomic(_INDEX, default={}) or {}
    idx[tag] = {"ts": now_oslo().isoformat(), "hash": _hash_obj(cfg), "path": str(path)}
    write_json_atomic(_INDEX, idx, backup=False)
    return path

def cfg_load(tag: str) -> Dict[str, Any]:
    idx = read_json_atomic(_INDEX, default={}) or {}
    rec = idx.get(tag)
    if not rec:
        return {}
    return read_json_atomic(Path(rec["path"]), default={}) or {}

def cfg_diff(tag_a: str, tag_b: str) -> Dict[str, Any]:
    a = cfg_load(tag_a); b = cfg_load(tag_b)
    added = {k: b[k] for k in b.keys() - a.keys()}
    removed = {k: a[k] for k in a.keys() - b.keys()}
    changed = {k: {"a": a[k], "b": b[k]} for k in a.keys() & b.keys() if a[k] != b[k]}
    return {"added": added, "removed": removed, "changed": changed}