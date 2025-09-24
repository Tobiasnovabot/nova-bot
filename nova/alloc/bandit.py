# Thompson Sampling for per-strategi allokering.
# Inndata: stats per strategi (wins, losses, total_pnl)
# Utdata: vekter (sum=1) med max endring per dag.

import json, os, math, random, time

def thompson_sample_alpha_beta(alpha, beta):
    # enkel Beta-sampling uten numpy (rejection via gamma er overkill her)
    # approx: bruk random.betavariate hvis tilgjengelig
    return random.betavariate(alpha, beta)

def compute_weights(stats, prev_weights=None, max_step=0.05, floor=0.02, ceil=0.5):
    """
    stats: dict[strategy] = {"wins":int, "losses":int, "total_pnl":float}
    prev_weights: dict[strategy]->float  (for jevn justering)
    """
    samples={}
    # Sample sannsynlighet for "suksess", boost med PnL (positiv -> høyere alpha)
    for strat, s in stats.items():
        w = int(s.get("wins",0))
        l = int(s.get("losses",0))
        pnl = float(s.get("total_pnl",0.0))
        alpha = 1 + w + max(0.0, pnl/abs(pnl) if pnl!=0 else 0.0)  # liten dytt for +PnL
        beta  = 1 + l + max(0.0, -pnl/abs(pnl) if pnl!=0 else 0.0) # liten dytt for -PnL
        samples[strat] = thompson_sample_alpha_beta(alpha, beta)

    tot = sum(samples.values()) or 1.0
    raw = {k: v/tot for k,v in samples.items()}

    # myk overgang fra forrige vekter
    if prev_weights:
        adj={}
        for k in raw:
            old = prev_weights.get(k, 1.0/len(raw))
            delta = max(-max_step, min(max_step, raw[k]-old))
            adj[k] = old + delta
        raw = adj

    # klipp og normaliser
    clipped={k: max(floor, min(ceil, v)) for k,v in raw.items()}
    s=sum(clipped.values()) or 1.0
    weights={k: v/s for k,v in clipped.items()}
    return weights

def save_weights(path, weights):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w") as f:
        json.dump({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "weights": weights}, f, indent=2)
