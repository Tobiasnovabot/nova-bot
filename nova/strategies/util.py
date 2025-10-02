import math
def sma(series, n):
    if len(series) < n: return None
    return sum(series[-n:])/n
def ema(series, n):
    if len(series) < n: return None
    k = 2/(n+1); e = sum(series[:n])/n
    for x in series[n:]: e = x*k + e*(1-k)
    return e
def stddev(series, n):
    if len(series) < n: return None
    seg = series[-n:]; m = sum(seg)/n
    var = sum((x-m)*(x-m) for x in seg)/n
    return math.sqrt(var)
