from nova.strategies.base import StrategyBase

class StrategyRSI2(StrategyBase):
    NAME = "rsi2"
    TF = "5m"
    def on_bar(self, ctx):
        rsi = ctx.ta.rsi(7)
        if rsi < 28:
            ctx.buy()
        elif rsi > 72:
            ctx.sell()