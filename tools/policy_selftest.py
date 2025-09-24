import os, random, numpy as np
os.environ.setdefault("PYTHONWARNINGS","ignore")
from nova.engine.policy import choose, reward, snapshot

np.random.seed(11); random.seed(11)
cands = ["trend_pullback","atr_breakout","range_reversion"]
ctx = {"atr_pct":0.012,"spread_bp":6,"trend":0.55,"hour":13,"funding_bp":0.0}
wins=0
for _ in range(500):
    pick = choose("BTC/USDT", cands, ctx)
    r = {"trend_pullback": np.random.normal(0.03,0.02),
         "atr_breakout":  np.random.normal(0.015,0.02),
         "range_reversion": np.random.normal(0.0,0.02)}[pick]
    reward(pick, ctx, float(r))
    wins += (pick=="trend_pullback")
print("POLICY_OK picks_trend_pullback=", wins, "of 500")
print("SNAP_KEYS", len(snapshot()))
