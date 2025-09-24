#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Selftest for stateio:
- Init default state
- Save/load state
- Append trades + backup-rotasjon
- Equity snapshot
"""
import os, sys, time
from pathlib import Path

try:
    from .stateio import (
        STATE_PATH, TRADES_PATH, EQUITY_PATH,
        default_state, load_state, save_state,
        load_trades, save_trades, append_trade,
        load_equity, save_equity, snapshot_equity,
        backup_state_and_trades
    )
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.stateio.stateio import (
        STATE_PATH, TRADES_PATH, EQUITY_PATH,
        default_state, load_state, save_state,
        load_trades, save_trades, append_trade,
        load_equity, save_equity, snapshot_equity,
        backup_state_and_trades
    )

def main() -> int:
    test_home = Path(f"/tmp/nova_home/stateio_test-{os.getpid()}").resolve()
    os.environ["NOVA_HOME"] = str(test_home)
    (test_home / "data").mkdir(parents=True, exist_ok=True)

    # state
    st = load_state()
    assert isinstance(st, dict) and st["mode"] == "paper"
    st["risk_level"] = 3
    save_state(st)
    st2 = load_state()
    assert st2["risk_level"] == 3

    # trades
    save_trades([])
    for i in range(9):
        append_trade({"sym":"BTC/USDT","side":"buy","qty":0.001,"price":25000+i,"fee":0.01,"slip_bps":2.5,"pnl_real":0.0})
        time.sleep(0.002)
    tr = load_trades()
    assert len(tr) == 9

    # equity
    eq = load_equity()
    n0 = len(eq)
    snapshot_equity(1000.0, pnl_day=0.0)
    eq2 = load_equity()
    assert len(eq2) == n0 + 1 and "equity_usdt" in eq2[-1]

    # backups rotering
    # tving frem flere backuper
    for _ in range(6):
        st["risk_level"] += 1
        save_state(st)
        time.sleep(0.002)
    deleted = backup_state_and_trades(keep=3)
    assert deleted >= 1

    print("stateio selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
