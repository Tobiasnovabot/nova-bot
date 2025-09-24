from collections import deque
from . import Strategy, register
@register("momentum")
class MomentumStrategy(Strategy):
    def __init__(self, params):
        super().__init__(params)
        self.n=int(self.params.get("lookback",20)); self.buf=deque(maxlen=self.n)
    def on_bar(self, bar):
        c=float(bar["close"]); self.buf.append(c)
        if len(self.buf)<self.n: return {"symbol":bar["symbol"],"side":"flat","score":0.0}
        ret=c/self.buf[0]-1.0
        side="buy" if ret>0 else "sell" if ret<0 else "flat"
        return {"symbol":bar["symbol"],"side":side,"score":float(ret)}
