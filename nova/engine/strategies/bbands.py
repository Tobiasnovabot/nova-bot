from math import sqrt
from collections import deque
from . import Strategy, register
@register("bbands")
class BollingerStrategy(Strategy):
    def __init__(self, params):
        super().__init__(params)
        self.n=int(self.params.get("window",20)); self.k=float(self.params.get("k",2.0))
        self.buf=deque(maxlen=self.n)
    def on_bar(self, bar):
        c=float(bar["close"]); self.buf.append(c)
        if len(self.buf)<self.n: return {"symbol":bar["symbol"],"side":"flat","score":0.0}
        m=sum(self.buf)/self.n
        var=sum((x-m)*(x-m) for x in self.buf)/self.n
        sd=sqrt(var); upper=m+self.k*sd; lower=m-self.k*sd
        side="sell" if c>upper else "buy" if c<lower else "flat"
        score=(m-c)/max(sd,1e-9)
        return {"symbol":bar["symbol"],"side":side,"score":float(score)}
