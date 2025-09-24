from __future__ import annotations
import math, json, time
from dataclasses import dataclass, field
from typing import Dict, Tuple, List
import numpy as np

# Diskret kontekst-bucket for stabilitet (unngår tunge biblioteker)
def _bucket(ctx: Dict[str, float]) -> Tuple[int, int, int, int, int]:
    # kvantiser relevante features
    atr = float(ctx.get("atr_pct", 0.0))           # ATR/price in %
    spr = float(ctx.get("spread_bp", 0.0))         # spread i bp
    trd = float(ctx.get("trend", 0.0))             # [-1,1]
    tod = float(ctx.get("hour", 0.0))              # 0..23
    fund= float(ctx.get("funding_bp", 0.0))        # perp funding i bp
    # bins
    b_atr = int(np.clip(math.floor(atr*10), 0, 30))       # 0..3% -> 0..30
    b_spr = int(np.clip(math.floor(spr/2), 0, 50))        # 0..100bp -> 0..50
    b_trd = int(np.clip(math.floor((trd+1)*5), 0, 10))    # -1..1 -> 0..10
    b_tod = int(np.clip(math.floor(tod), 0, 23))          # 0..23
    b_fnd = int(np.clip(math.floor((fund+50)/5), 0, 40))  # -50..150bp
    return (b_atr, b_spr, b_trd, b_tod, b_fnd)

@dataclass
class Posterior:
    n:int=0
    mean:float=0.0
    m2:float=0.0   # sum of squares for variance (Welford)
    last_ts:float=field(default_factory=time.time)

    def update(self, r: float, decay: float=1.0) -> None:
        # eksponentiell glemsel på aggregerte stats
        if decay < 1.0 and self.n>0:
            self.m2 *= decay
            # juster mean mot 0 med liten vekting for å unngå drift
            self.mean *= decay
        self.n += 1
        delta = r - self.mean
        self.mean += delta/self.n
        self.m2 += delta*(r - self.mean)
        self.last_ts = time.time()

    def sample(self) -> float:
        # Thompson: trekk fra Normal(mean, s/sqrt(n)), s fra varians-estimat
        var = (self.m2/(self.n-1)) if self.n > 1 else 1.0
        std = math.sqrt(max(var, 1e-8))/max(math.sqrt(self.n), 1.0)
        return float(np.random.normal(self.mean, std))

class ContextualBandit:
    def __init__(self, decay:float=0.97, eps_floor:float=0.02):
        self.decay = decay
        self.eps = eps_floor
        # key = (strategy_name, bucket_tuple)
        self.post: Dict[Tuple[str, Tuple[int,int,int,int,int]], Posterior] = {}

    def _key(self, strat:str, ctx:Dict[str,float]):
        return (strat, _bucket(ctx))

    def choose(self, strategies: List[str], ctx: Dict[str,float]) -> str:
        if not strategies: 
            raise ValueError("no strategies")
        # epsilon-gulv for eksplorasjon
        if np.random.rand() < self.eps:
            return np.random.choice(strategies)
        scores=[]
        for s in strategies:
            k=self._key(s, ctx)
            p=self.post.get(k, Posterior())
            scores.append((p.sample(), s))
        scores.sort(reverse=True, key=lambda x: x[0])
        return scores[0][1]

    def update(self, strat: str, ctx: Dict[str,float], reward: float) -> None:
        # reward-shaping: straff slippage/hold om gitt i ctx
        r = float(reward)
        r -= float(ctx.get("lambda_slip", 0.3)) * float(ctx.get("slippage_bp", 0.0))/100.0
        r -= float(ctx.get("lambda_hold", 0.05)) * float(ctx.get("hold_hrs", 0.0))
        k=self._key(strat, ctx)
        p=self.post.get(k)
        if p is None:
            p=Posterior()
            self.post[k]=p
        p.update(r, decay=self.decay)

    def snapshot(self) -> Dict[str, float]:
        # nyttig for telemetry
        return { f"{s}|{b}": v.mean for (s,b),v in self.post.items() }

