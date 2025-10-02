from nova.bandit.contextual import ContextualBandit
import numpy as np, random
np.random.seed(7); random.seed(7)

bandit = ContextualBandit(decay=0.97, eps_floor=0.0)
strats = ["A","B","C"]
# Kontekst med lav spread og moderat trend favoriserer B (syntetisk)
wins=0
for t in range(1000):
    ctx={"atr_pct":0.01,"spread_bp":6,"trend":0.5,"hour":12,"funding_bp":0.0}
    pick = bandit.choose(strats, ctx)
    # Lag syntetisk reward: B best, A middels, C dårlig
    r = {"A": np.random.normal(0.01,0.02),
         "B": np.random.normal(0.03,0.02),
         "C": np.random.normal(-0.005,0.02)}[pick]
    bandit.update(pick, ctx, r)
    wins += (pick=="B")
print("BANDIT_OK picks_B=", wins, "of", 1000, "mean_B_est=", bandit.snapshot().get("B|"+str((0,3,7,12,10)), 0.0))
