from .util import ema
def macd_signal(prices, fast=12, slow=26, sig=9):
    out={}
    for sym, series in prices.items():
        efast=ema(series, fast); eslow=ema(series, slow)
        if efast is None or eslow is None: out[sym]=0; continue
        macd=efast-eslow
        signal = macd*(2/(sig+1))  # enkel proxy
        hist = macd - signal
        out[sym]= 1 if hist>0 else (-1 if hist<0 else 0)
    return out
