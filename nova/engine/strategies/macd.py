from . import Strategy, register
from .indicators import EMA
@register("macd")
class MACDStrategy(Strategy):
    def __init__(self, params):
        super().__init__(params)
        self.fast=EMA(int(self.params.get("fast",12)))
        self.slow=EMA(int(self.params.get("slow",26)))
        self.sig = EMA(int(self.params.get("signal",9)))
    def on_bar(self, bar):
        p=bar["close"]; macd=self.fast.update(p)-self.slow.update(p); s=self.sig.update(macd)
        side="buy" if macd>s else "sell" if macd<s else "flat"
        score=(macd - s)
        return {"symbol":bar["symbol"],"side":side,"score":float(score)}
