def _rsi(series, n=14):
    if len(series)<n+1: return None
    gains=losses=0.0
    for i in range(-n,0):
        ch=series[i]-series[i-1]
        gains += max(0,ch); losses += max(0,-ch)
    if losses==0: return 100.0
    rs=gains/losses
    return 100 - 100/(1+rs)
def rsi_signal(prices, low=30, high=70):
    out={}
    for sym, series in prices.items():
        r=_rsi(series)
        out[sym]= 1 if (r is not None and r<low) else (-1 if (r is not None and r>high) else 0)
    return out
