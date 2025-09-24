#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from pathlib import Path
import sys

try:
    from .signals import build_signals
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.signals.signals import build_signals

def _mk_df(n=240, seed=7):
    rng = np.random.default_rng(seed)
    # Baseline svakt opp (100 -> 120)
    base = np.linspace(100.0, 120.0, n)
    noise = rng.normal(0, 0.03, n)
    close = base + noise

    # PUMP for entry: sterk opp i vindu [150:170)
    pump_start, pump_end = 150, 170
    close[pump_start:pump_end] += np.linspace(0.0, 5.0, pump_end - pump_start)

    # DUMP for exit: nedgang i vindu [200:230)
    dump_start, dump_end = 200, 230
    close[dump_start:dump_end] -= np.linspace(0.0, 8.0, dump_end - dump_start)

    # Open = forrige close, High/Low ±0.2
    open_ = np.r_[close[0], close[:-1]]
    high  = close + 0.2
    low   = close - 0.2

    # Volum: høyere i pump for å trigge momentum-gate
    vol = np.full(n, 1000.0)
    vol[pump_start:pump_end] = 4000.0
    vol[-1] = 2000.0

    return pd.DataFrame({"open":open_, "high":high, "low":low, "close":close, "volume":vol})

def main() -> int:
    df = _mk_df()
    # HTF: glatt 30 for HTF-filter
    htf = df.copy()
    htf["close"] = pd.Series(df["close"]).rolling(30, min_periods=1).mean()

    # Gates-kontekst: la ML-gate være lett å passere, equity-MA opp
    ctx = {
        "htf_df": htf,
        "ml_score": 0.9,
        "ml_threshold": 0.2,
        "equity_ma_up": True,
    }

    saw_entry = False
    saw_exit = False

    # Iterer fremover og let etter minst én entry og én exit
    for i in range(40, len(df)):
        res = build_signals(df.iloc[:i].copy(), ctx)
        if res["entry"]:
            saw_entry = True
        if res["exit"]:
            saw_exit = True
        if saw_entry and saw_exit:
            break

    assert saw_entry, "Ingen entry generert"
    assert saw_exit,  "Ingen exit generert"
    print("signals selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
