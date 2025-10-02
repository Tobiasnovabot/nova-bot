_ema={}; _alpha=0.2
def signal(symbol, price, broker):
    if price is None: return 0
    ema=_ema.get(symbol, price)
    ema=_alpha*price+(1-_alpha)*ema
    _ema[symbol]=ema
    if price<ema*0.9985: return 1
    if price>ema*1.0015: return -1
    return 0
