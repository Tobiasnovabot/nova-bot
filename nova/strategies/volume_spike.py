def volspike_signal(volumes, n=20, mult=2.0):
    out={}
    for sym, series in volumes.items():
        if len(series)<n+1: out[sym]=0; continue
        avg=sum(series[-n-1:-1])/n
        out[sym]= 1 if series[-1] > mult*avg else 0
    return out
