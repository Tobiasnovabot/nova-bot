#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, random
from pathlib import Path

try:
    from .bandit import reset_bandit, ensure_strats, choose_strat, bandit_update, get_bandit_state
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.bandit.bandit import reset_bandit, ensure_strats, choose_strat, bandit_update, get_bandit_state

def main() -> int:
    random.seed(42)
    reset_bandit()
    ensure_strats(["A", "B"])

    # A vinner ofte, B taper ofte
    for _ in range(200):
        bandit_update({"strat":"A", "reward": +1.0, "atr_pct": 1.0, "symbol":"BTC/USDT"})
    for _ in range(200):
        bandit_update({"strat":"B", "reward": -1.0, "atr_pct": 1.0, "symbol":"BTC/USDT"})

    # Velg 200 ganger; A skal dominere klart
    wins_A = 0
    for _ in range(200):
        c = choose_strat({"candidates":["A","B"]})
        if c == "A":
            wins_A += 1

    assert wins_A >= 160, f"For få valg av A ({wins_A}/200)"

    st = get_bandit_state()
    a = st["strats"]["A"]
    b = st["strats"]["B"]
    # Posterior: E[p]=alpha/(alpha+beta)
    Ea = a["alpha"] / (a["alpha"] + a["beta"])
    Eb = b["alpha"] / (b["alpha"] + b["beta"])
    assert Ea > Eb, "Posterior endret ikke i riktig retning"

    print("bandit selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
