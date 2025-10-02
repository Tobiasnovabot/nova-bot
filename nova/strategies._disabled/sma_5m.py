from nova.strategies.base import StrategyBase

class Strategy_SMA_5m(StrategyBase):
    NAME = "sma_5m"
    TF = "5m"
    def on_bar(self, ctx):
        rsi = ctx.ta.rsi(14)
        if rsi < 30:
            ctx.buy()
        elif rsi > 70:
            ctx.sell()