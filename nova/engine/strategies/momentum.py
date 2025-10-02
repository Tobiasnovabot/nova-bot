_last={}
def signal(symbol, price, broker):
    if price is None: return 0
    p0=_last.get(symbol); _last[symbol]=price
    if not p0: return 0
    ch=(price-p0)/p0
    if ch>0.003: return 1
    if ch<-0.003: return -1
    return 0
