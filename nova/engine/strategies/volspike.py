from collections import deque
from . import Strategy, register
@register("volspike")
class VolumeSpikeStrategy(Strategy):
    def __init__(self, params):
        super().__init__(params)
        self.n=int(self.params.get("window",50)); self.buf=deque(maxlen=self.n)
        self.mult=float(self.params.get("mult",2.0))
    def on_bar(self, bar):
        v=float(bar["volume"]); self.buf.append(v)
        if len(self.buf)<self.n: return {"symbol":bar["symbol"],"side":"flat","score":0.0}
        avg=sum(self.buf)/len(self.buf)
        side="buy" if v>self.mult*avg else "flat"
        score=(v/avg)-1.0
        return {"symbol":bar["symbol"],"side":side,"score":float(score)}
