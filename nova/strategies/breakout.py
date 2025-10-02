def breakout_signal(prices, lookback=20):
    out={}
    for sym, series in prices.items():
        if len(series)<lookback+1: out[sym]=0; continue
        hh=max(series[-lookback-1:-1]); ll=min(series[-lookback-1:-1])
        out[sym]= 1 if series[-1]>hh else (-1 if series[-1]<ll else 0)
    return out
