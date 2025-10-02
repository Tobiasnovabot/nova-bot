from nova.strategies.base import StrategyBase

class StrategySMACross(StrategyBase):
    NAME = "sma_cross"
    TF = "15m"
    def on_bar(self, ctx):
        rsi = ctx.ta.rsi(14)
        if rsi < 30:
            ctx.buy()
        elif rsi > 70:
            ctx.sell()