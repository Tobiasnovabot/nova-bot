from .util import sma
def sma_signal(prices, fast=20, slow=50):
    out={}
    for sym, series in prices.items():
        f=sma(series, fast); s=sma(series, slow)
        out[sym]= 1 if (f and s and f>s) else (-1 if (f and s and f<s) else 0)
    return out
