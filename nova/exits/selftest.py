#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from pathlib import Path
import sys

try:
    from .exits import compute_stop_take
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.exits.exits import compute_stop_take

def _mk_uptrend(n=200, start=100.0, step=0.5):
    close = start + np.arange(n)*step
    high  = close + 0.2
    low   = close - 0.2
    return pd.DataFrame({"high":high, "low":low, "close":close})

def main() -> int:
    df = _mk_uptrend()
    entry = df["close"].iloc[5]
    prev_stop = None
    prev_be = False
    stops = []

    # Aggressive param for klar bevegelse og arming=0
    params = {
        "trail_k": 2.0,
        "arm_atr": 0.0,
        "be_arm_atr": 0.0,
        "min_trail_bps": 20.0,
        "debounce_bps": 1.0,
        "struct_look": 10,
        "chandelier_k": 3.0,
        "use_close_for_trail": True,
        "tp_R": [1.0, 2.0, 3.0],
        "tp_frac": [0.3, 0.3, 0.4],
        "time_stop_bars": 80,
        "add_atr": [0.5, 1.0],
    }

    for i in range(15, len(df)):
        ctx = {
            "side": "long",
            "entry": float(entry),
            "bars": df.iloc[:i].copy(),
            "atr": 1.0,                # konstant ATR for test
            "prev_stop": prev_stop,
            "prev_be_armed": prev_be,
            "pyramided": 0,
            "params": params,
        }
        out = compute_stop_take(ctx)
        stop = out["stop"]
        assert stop is not None
        # stop skal alltid være under close
        assert stop < df["close"].iloc[i-1]
        # monotoni: ikke ned
        if prev_stop is not None:
            assert stop >= prev_stop - 1e-12
        prev_stop = stop
        prev_be = out["meta"]["be_armed"]
        stops.append(stop)

    # verifiser at vi faktisk flyttet stop flere ganger
    assert len(np.unique(np.round(stops, 6))) > 5, "stop flytter seg for sjelden"

    print("exits selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
