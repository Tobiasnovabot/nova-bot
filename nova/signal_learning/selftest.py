#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import pandas as pd
import numpy as np
from pathlib import Path

try:
    from .signal_learning import meta_labeling, bayes_tune_threshold, ob_queue_fill_prob
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.signal_learning.signal_learning import meta_labeling, bayes_tune_threshold, ob_queue_fill_prob

def main() -> int:
    # Meta-labeling
    idx = pd.RangeIndex(5)
    entries = pd.Series([1,0,1,0,1], index=idx, dtype=bool)
    exits =   pd.Series([0,1,0,1,1], index=idx, dtype=bool)
    pnl =     pd.Series([0.0, 0.2, -0.1, 0.5, 0.05], index=idx)
    labels = meta_labeling(entries, exits, pnl, thr=0.0)
    assert labels.sum() >= 1 and labels.iloc[-1] == 1  # siste er >0

    # Bayes-tuning
    post = bayes_tune_threshold(8, 2, prior_a=1, prior_b=1)
    assert 0.7 < post < 0.9

    # OB-kø
    p = ob_queue_fill_prob(placed=10, queue=50, cancels=20, lookahead=5)
    assert 0.0 <= p <= 1.0 and p > 0.0

    print("signal_learning selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
