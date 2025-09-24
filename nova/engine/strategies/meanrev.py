from . import Strategy, register
from .indicators import SMA
@register("meanrev")
class MeanReversionStrategy(Strategy):
    def __init__(self, params):
        super().__init__(params)
        self.n=int(self.params.get("window",50)); self.sma=SMA(self.n)
    def on_bar(self, bar):
        c=float(bar["close"]); m=self.sma.update(c)
        dev=(c-m)/max(abs(m),1e-9)
        side="sell" if dev>float(self.params.get("z_hi",0.02)) else "buy" if dev<float(self.params.get("z_lo",-0.02)) else "flat"
        return {"symbol":bar["symbol"],"side":side,"score":float(-dev)}
