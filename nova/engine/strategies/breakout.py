from collections import deque
from . import Strategy, register
@register("breakout")
class BreakoutStrategy(Strategy):
    def __init__(self, params):
        super().__init__(params)
        self.n=int(self.params.get("window",20))
        self.h=deque(maxlen=self.n); self.l=deque(maxlen=self.n)
    def on_bar(self, bar):
        h=float(bar["high"]); l=float(bar["low"]); c=float(bar["close"])
        self.h.append(h); self.l.append(l)
        if len(self.h)<self.n: return {"symbol":bar["symbol"],"side":"flat","score":0.0}
        hh=max(self.h); ll=min(self.l)
        side="buy" if c>hh else "sell" if c<ll else "flat"
        score=(c - (hh+ll)/2)/max(abs((hh-ll)/2),1e-9)
        return {"symbol":bar["symbol"],"side":side,"score":float(score)}
