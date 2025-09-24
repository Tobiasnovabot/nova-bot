def setup(cfg): return {"lookback": cfg.get("bo_lookback", 50), "pullback": 0.003}
def signal(ticker, ohlc, params):
    if not ohlc or len(ohlc)<params["lookback"]+1: return ("hold", {})
    highs=[x[2] for x in ohlc][-params["lookback"]-1:-1]
    lows =[x[3] for x in ohlc][-params["lookback"]-1:-1]
    last=ohlc[-1][4]
    if last > max(highs)*(1+params["pullback"]): return ("buy", {"reason":"breakout"})
    if last < min(lows )*(1-params["pullback"]): return ("sell", {"reason":"breakdown"})
    return ("hold", {})
