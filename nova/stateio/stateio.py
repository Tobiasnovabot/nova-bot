#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
"""
stateio: global state, equity og trades m/ sikre writes og backup-rotasjon.
Filer: NOVA_HOME/data/{state.json, trades.json, equity.json}
"""
from nova import paths as NPATH
import os, time
from pathlib import Path
from typing import Dict, Any, List

from nova.core_boot.core_boot import (
    NOVA_HOME, now_oslo,
    read_json_atomic, write_json_atomic, rotate_backups, ensure_nova_home
)

DATA_DIR = (NOVA_HOME / "data")
STATE_PATH  = DATA_DIR / NPATH.STATE.as_posix()
TRADES_PATH = DATA_DIR / NPATH.TRADES.as_posix()
EQUITY_PATH = DATA_DIR / NPATH.EQUITY.as_posix()

def default_state() -> Dict[str, Any]:
    return {
        "mode": "paper",
        "day": now_oslo().date().isoformat(),
        "pnl_day": 0.0,
        "pnl_total": 0.0,
        "positions": {},          # sym -> {qty, avg, unrealized}
        "trades_head": 0,         # antall lagrede trades (for rask len)
        "params": {},             # key->val
        "bandit": {},             # strat stats
        "risk_level": 1,
        "bot_enabled": True,
        "slippage_model": {"bps": 2.0},
        "sym_score": {},          # sym->score
        "loss_streak": {"global":0, "per_sym":{}},
        "universe_cache": {"ts": 0, "symbols": []},
    }

def _ensure_dirs():
    ensure_nova_home()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

# -------- state --------
def load_state() -> Dict[str, Any]:
    _ensure_dirs()
    st = read_json_atomic(STATE_PATH, default=None)
    if not isinstance(st, dict):
        st = default_state()
        write_json_atomic(STATE_PATH, st, backup=False)
    # garanter obligatoriske felt
    base = default_state()
    for k,v in base.items():
        if k not in st:
            st[k] = v
    return st

def save_state(state: Dict[str, Any]) -> None:
    _ensure_dirs()
    write_json_atomic(STATE_PATH, state, backup=True)

# -------- trades --------
def load_trades() -> List[Dict[str, Any]]:
    _ensure_dirs()
    arr = read_json_atomic(TRADES_PATH, default=[])
    return arr if isinstance(arr, list) else []

def save_trades(trades: List[Dict[str, Any]]) -> None:
    _ensure_dirs()
    write_json_atomic(TRADES_PATH, trades, backup=True)

def append_trade(tr: Dict[str, Any]) -> None:
    """
    Append én trade. Beriker med iso-tid hvis mangler.
    tr eksempel: {sym, side, qty, price, fee, slip_bps, pnl_real}
    """
    _ensure_dirs()
    trades = load_trades()
    if "ts" not in tr:
        tr["ts"] = now_oslo().isoformat()
    trades.append(tr)
    write_json_atomic(TRADES_PATH, trades, backup=True)

# -------- equity --------
def load_equity() -> List[Dict[str, Any]]:
    _ensure_dirs()
    arr = read_json_atomic(EQUITY_PATH, default=[])
    return arr if isinstance(arr, list) else []

def save_equity(eqs: List[Dict[str, Any]]) -> None:
    _ensure_dirs()
    write_json_atomic(EQUITY_PATH, eqs, backup=True)

def snapshot_equity(equity_usdt: float, pnl_day: float = None) -> Dict[str, Any]:
    """
    Legg til ett equity-snapshot. Returnerer posten.
    """
    snap = {
        "ts": now_oslo().isoformat(),
        "equity_usdt": float(equity_usdt),
    }
    if pnl_day is not None:
        snap["pnl_day"] = float(pnl_day)
    arr = load_equity()
    arr.append(snap)
    write_json_atomic(EQUITY_PATH, arr, backup=True)
    return snap

# -------- backups --------
def backup_state_and_trades(keep: int = 7) -> int:
    """
    Roter .bak for state og trades. Returnerer totalt slettet.
    """
    deleted = 0
    deleted += rotate_backups(STATE_PATH, keep=keep)
    deleted += rotate_backups(TRADES_PATH, keep=keep)
    return deleted