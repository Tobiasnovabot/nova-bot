def setup(cfg): return {"period": cfg.get("rsi_period", 14), "lo": 30, "hi": 70}
def signal(ticker, ohlc, params):
    closes=[c[4] for c in ohlc][-200:] if ohlc else []
    n=params["period"]
    if len(closes)<=n+1: return ("hold", {})
    gains=[]; losses=[]
    for i in range(-n,0):
        diff=closes[i]-closes[i-1]
        gains.append(max(diff,0)); losses.append(max(-diff,0))
    avg_g = sum(gains)/n; avg_l = sum(losses)/n or 1e-9
    rs = avg_g/avg_l; rsi = 100 - (100/(1+rs))
    if rsi<params["lo"]: return ("buy", {"reason":"rsi_low","rsi":rsi})
    if rsi>params["hi"]: return ("sell", {"reason":"rsi_high","rsi":rsi})
    return ("hold", {})
