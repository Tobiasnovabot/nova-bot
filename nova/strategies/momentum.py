def momentum_signal(prices, look=10):
    out={}
    for sym, series in prices.items():
        if len(series)<look+1: out[sym]=0; continue
        out[sym]= 1 if series[-1]>series[-look-1] else (-1 if series[-1]<series[-look-1] else 0)
    return out
