import pandas as pd
from .base import Strategy

class RSICross(Strategy):
    def __init__(self, low=30, high=70, period=14):
        self.low, self.high, self.period = low, high, period
    def decide(self, ohlcv_df):
        if len(ohlcv_df) < self.period + 2: return "HOLD"
        delta = ohlcv_df['close'].diff()
        gain = (delta.clip(lower=0)).rolling(self.period).mean()
        loss = (-delta.clip(upper=0)).rolling(self.period).mean().abs()
        rs = gain / (loss.replace(0, 1e-9))
        rsi = 100 - (100 / (1 + rs))
        last, prev = rsi.iloc[-1], rsi.iloc[-2]
        if prev < self.low and last >= self.low:  return "BUY"
        if prev > self.high and last <= self.high: return "SELL"
        return "HOLD"
