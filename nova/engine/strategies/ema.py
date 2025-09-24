from . import Strategy, register
from .indicators import EMA
@register("ema")
class EMAStrategy(Strategy):
    def __init__(self, params):
        super().__init__(params)
        self.n_fast = int(self.params.get("n_fast", 12))
        self.n_slow = int(self.params.get("n_slow", 26))
        self.fast = EMA(self.n_fast); self.slow = EMA(self.n_slow)
    def on_bar(self, bar):
        p = bar["close"]
        f = self.fast.update(p); s = self.slow.update(p)
        side = "buy" if f>s else "sell" if f<s else "flat"
        score = (f-s)/max(abs(s),1e-9)
        return {"symbol": bar["symbol"], "side": side, "score": float(score)}
