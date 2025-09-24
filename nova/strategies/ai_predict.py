def ai_predict_signal(prices, win=30):
    out={}
    for sym, series in prices.items():
        if len(series)<win: out[sym]=0; continue
        slope = (series[-1]-series[-win])/win
        out[sym]= 1 if slope>0 else (-1 if slope<0 else 0)
    return out
