from nova.strategies.base import StrategyBase

class Strategy_SMA_1h(StrategyBase):
    NAME = "sma_1h"
    TF = "1h"
    def on_bar(self, ctx):
        rsi = ctx.ta.rsi(14)
        if rsi < 30:
            ctx.buy()
        elif rsi > 70:
            ctx.sell()