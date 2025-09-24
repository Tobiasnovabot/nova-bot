#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
from nova import paths as NPATH
import json, time
from typing import Dict, Any, Tuple, List
from pathlib import Path

from nova.core_boot.core_boot import NOVA_HOME, now_oslo
from nova.stateio.stateio import (
    read_json_atomic, write_json_atomic,
    load_equity, snapshot_equity
)

_HEAL_PARAMS = {
    "lock_stale_sec": 3600,
    "equity_stale_sec": 3600,
}

def _path(p: str) -> Path:
    return NOVA_HOME / p

def health_snapshot() -> Dict[str, Any]:
    data_dir = _path("data")
    logs_dir = _path("logs")
    state_p = data_dir / NPATH.STATE.as_posix()
    trades_p = data_dir / NPATH.TRADES.as_posix()
    equity_p = data_dir / NPATH.EQUITY.as_posix()
    lock_p = NOVA_HOME / "nova.lock"
    log_run = logs_dir / "run.out"

    state = read_json_atomic(state_p, default={}) or {}
    trades = read_json_atomic(trades_p, default=[]) or []
    eq = load_equity()

    now_ts = now_oslo().timestamp()
    eq_ts = now_ts
    if eq:
        # bruk siste snapshot tid hvis finnes, ellers now
        eq_ts = now_ts
    lock_age = None
    if lock_p.exists():
        lock_age = now_ts - lock_p.stat().st_mtime

    health = {
        "paths": {
            "state": state_p.exists(),
            "trades": trades_p.exists(),
            "equity": equity_p.exists(),
            "log_run": log_run.exists(),
            "lock": lock_p.exists(),
        },
        "counts": {"trades": len(trades), "equity_snaps": len(eq)},
        "lock_age_sec": lock_age,
        "equity_fresh_sec": None,
        "bot_enabled": bool(state.get("bot_enabled", True)),
    }

    # equity freshness (bruk fil mtime)
    if equity_p.exists():
        health["equity_fresh_sec"] = now_ts - equity_p.stat().st_mtime
    else:
        health["equity_fresh_sec"] = None
    return health

def auto_heal(health: Dict[str, Any]) -> Dict[str, Any]:
    actions: List[str] = []
    data_dir = _path("data"); data_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = _path("logs"); logs_dir.mkdir(parents=True, exist_ok=True)

    # lag tomme filer ved behov
    if not health["paths"]["state"]:
        write_json_atomic(data_dir / NPATH.STATE.as_posix(), {"bot_enabled": True, "pnl_day": 0.0})
        actions.append("init_state")
    if not health["paths"]["trades"]:
        write_json_atomic(data_dir / NPATH.TRADES.as_posix(), [])
        actions.append("init_trades")
    if not health["paths"]["equity"]:
        snapshot_equity(0.0, pnl_day=0.0)
        actions.append("init_equity")
    if not health["paths"]["log_run"]:
        (_path("logs") / "run.out").write_text("", encoding="utf-8")
        actions.append("init_log")

    # stale lock → fjern
    if health["paths"]["lock"] and health.get("lock_age_sec") is not None:
        if health["lock_age_sec"] > _HEAL_PARAMS["lock_stale_sec"]:
            try:
                (_path("nova.lock")).unlink()
                actions.append("remove_stale_lock")
            except Exception:
                actions.append("lock_remove_fail")

    # stale equity → nytt snapshot
    ef = health.get("equity_fresh_sec")
    if ef is None or (isinstance(ef, (int,float)) and ef > _HEAL_PARAMS["equity_stale_sec"]):
        snapshot_equity(health.get("equity_last", 0.0) or 0.0, pnl_day=0.0)
        actions.append("refresh_equity")

    return {"healed": actions}

# -------- Chaos testing --------

def inject_chaos(scenario: str, seconds: int) -> Dict[str, Any]:
    """
    scenario: 'cpu', 'io', 'api_fail', 'latency'
    """
    info = {
        "scenario": scenario,
        "until": now_oslo().timestamp() + max(0, int(seconds)),
        "ts": now_oslo().isoformat(),
    }
    write_json_atomic(_path("logs") / "chaos.json", info, backup=False)
    return info

def chaos_status() -> Dict[str, Any]:
    return read_json_atomic(_path("logs") / "chaos.json", default={}) or {}

# -------- Explainability --------

def explain_decision(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    ctx:
      symbol, features:{...}, gates:{name:bool}, costs_bps, expected_edge_bps
      chosen: 'buy'|'sell'|'hold'
    """
    gates = ctx.get("gates", {})
    feats = ctx.get("features", {})
    passed = [k for k,v in gates.items() if v]
    failed = [k for k,v in gates.items() if not v]
    edge = float(ctx.get("expected_edge_bps", 0.0))
    cost = float(ctx.get("costs_bps", 0.0))
    decision = ctx.get("chosen", "hold")
    rationale = []
    if failed:
        rationale.append(f"blocked_by={','.join(failed)}")
    if edge <= cost:
        rationale.append(f"edge<=cost ({edge:.1f}<={cost:.1f})")
    else:
        rationale.append(f"edge>cost ({edge:.1f}>{cost:.1f})")
    return {
        "symbol": ctx.get("symbol"),
        "decision": decision,
        "passed_gates": passed,
        "failed_gates": failed,
        "edge_bps": edge,
        "cost_bps": cost,
        "top_features": sorted(feats.items(), key=lambda kv: abs(float(kv[1])), reverse=True)[:5],
        "why": "; ".join(rationale),
        "ts": now_oslo().isoformat(),
    }