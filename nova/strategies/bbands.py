from .util import sma, stddev
def bbands_signal(prices, n=20, k=2.0):
    out={}
    for sym, series in prices.items():
        m=sma(series,n); sd=stddev(series,n)
        if m is None or sd is None: out[sym]=0; continue
        upper=m+k*sd; lower=m-k*sd; last=series[-1]
        out[sym]= 1 if last<lower else (-1 if last>upper else 0)
    return out
