from . import Strategy, register
@register("rsi")
class RSIStrategy(Strategy):
    def __init__(self, params):
        super().__init__(params)
        self.n=int(self.params.get("n",14))
        self.alpha=2/(self.n+1); self.g=None; self.l=None; self.prev=None
        self.ovb=float(self.params.get("overbought",70)); self.ovs=float(self.params.get("oversold",30))
    def on_bar(self, bar):
        p=float(bar["close"])
        if self.prev is None: self.prev=p; return {"symbol":bar["symbol"],"side":"flat","score":0.0}
        ch=p-self.prev; self.prev=p
        g=max(ch,0); l=max(-ch,0)
        self.g = g if self.g is None else (1-self.alpha)*self.g + self.alpha*g
        self.l = l if self.l is None else (1-self.alpha)*self.l + self.alpha*l
        rs=(self.g/(self.l+1e-9)); rsi=100-100/(1+rs)
        side="sell" if rsi>self.ovb else "buy" if rsi<self.ovs else "flat"
        score=(50-rsi)/50.0
        return {"symbol":bar["symbol"],"side":side,"score":float(score)}
