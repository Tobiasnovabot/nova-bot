from __future__ import annotations
import os, time, random
from typing import Dict, List
from math import isfinite

try:
    import ccxt  # type: ignore
except Exception:
    ccxt = None

def _to_pair(sym:str)->str:
    # BTCUSDT -> BTC/USDT
    if "/" in sym or "-" in sym: return sym
    return f"{sym[:-4]}/{sym[-4:]}"

def fetch_last_prices(symbols:List[str])->Dict[str,float]:
    ex = os.getenv("EXCHANGE","binance").lower()
    if ccxt is None:
        # fallback pseudo-priser
        r=random.Random(int(time.time())//5)
        return {s: abs(r.uniform(50,70000)) for s in symbols}
    if ex=="binance":
        exx = ccxt.binance({"enableRateLimit": True})
    elif ex=="okx":
        exx = ccxt.okx({"enableRateLimit": True})
    else:
        exx = ccxt.binance({"enableRateLimit": True})
    out={}
    for s in symbols:
        pair = _to_pair(s)
        try:
            t = exx.fetch_ticker(pair)
            px = float(t["last"])
            if not isfinite(px): raise ValueError
            out[s]=px
        except Exception:
            # siste kjente eller fallback random
            out[s]=out.get(s, random.uniform(50,70000))
    return out

def fetch_ohlcv(symbol:str, limit:int=240, tf:str="1m")->List[List[float]]:
    # [ [ts, open, high, low, close, vol], ... ]
    if ccxt is None:
        r=random.Random(42+hash(symbol)%1000)
        base=r.uniform(80,65000); series=[]
        for i in range(limit):
            ch=r.uniform(-0.01,0.01); close=base*(1+ch); high=max(base,close)*(1+r.uniform(0,0.003))
            low=min(base,close)*(1-r.uniform(0,0.003)); vol=abs(r.gauss(1,0.2))*100
            series.append([int(time.time()*1000), base, high, low, close, vol]); base=close
        return series
    ex = os.getenv("EXCHANGE","binance").lower()
    pair = symbol if "/" in symbol or "-" in symbol else f"{symbol[:-4]}/{symbol[-4:]}"
    try:
        if ex=="binance":
            exx=ccxt.binance({"enableRateLimit": True})
        elif ex=="okx":
            exx=ccxt.okx({"enableRateLimit": True})
        else:
            exx=ccxt.binance({"enableRateLimit": True})
        return exx.fetch_ohlcv(pair, timeframe=tf, limit=limit)
    except Exception:
        return fetch_ohlcv(symbol, limit=limit, tf=tf) if ccxt is None else []
