from .util import sma, stddev
def meanrev_signal(prices, n=20, z=1.0):
    out={}
    for sym, series in prices.items():
        m=sma(series,n); sd=stddev(series,n)
        if m is None or sd is None or sd==0: out[sym]=0; continue
        last=series[-1]; zscore=(last-m)/sd
        out[sym]= -1 if zscore>z else (1 if zscore<-z else 0)
    return out
