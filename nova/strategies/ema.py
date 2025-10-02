from .util import ema
def ema_signal(prices, fast=12, slow=26):
    out={}
    for sym, series in prices.items():
        f=ema(series, fast); s=ema(series, slow)
        out[sym]= 1 if (f and s and f>s) else (-1 if (f and s and f<s) else 0)
    return out
