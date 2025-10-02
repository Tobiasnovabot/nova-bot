import json, time, math
from pathlib import Path

MEM_DIR = Path("data/memory")
WATCH_F = Path("data/watchlist.json")

def _load_edge(symbol:str)->float:
    p = MEM_DIR / (symbol.replace("/","_") + ".json")
    if not p.exists(): return 0.0
    try: return float(json.loads(p.read_text()).get("edge",0.0))
    except: return 0.0

def _safe(v, d=0.0):
    try: return float(v)
    except: return d

def _score_symbol(ex, symbol, tf="1h"):
    # Hent 200 candles for volatilitet og 24h momentum
    try:
        ohlc = ex.fetch_ohlcv(symbol, timeframe=tf, limit=200)
    except Exception:
        return None
    if not ohlc or len(ohlc) < 50: 
        return None
    closes = [c[4] for c in ohlc]
    last = closes[-1]
    # 24h (24 candles på 1h) momentum
    mom = (last - closes[-24]) / closes[-24] if len(closes) > 24 and closes[-24] else 0.0
    # enkel ATR-lignende volatilitet
    trs = [abs(c[2]-c[3]) for c in ohlc[-50:]]
    vol = sum(trs)/len(trs) if trs else 0.0
    # lærings-edge (fra minne)
    edge = _load_edge(symbol)
    # Høyere volum/momentum, lavere volatilitet, positiv edge
    # Normaliser grovt
    try:
        tick = ex.fetch_ticker(symbol)
        qv = _safe(tick.get("quoteVolume"), 0.0)
    except Exception:
        qv = 0.0
    vol_penalty = 1.0 / (1.0 + math.log10(max(vol, 1e-8))*2.0)
    score = (math.log10(qv+1.0)*0.4) + (mom*100*0.4) + (edge*0.2)
    score *= vol_penalty
    return {"symbol": symbol, "score": score, "mom": mom, "qv": qv, "vol": vol, "edge": edge}

def select_universe(ex, all_symbols, max_pairs=30, tf="1h"):
    results = []
    for s in all_symbols:
        r = _score_symbol(ex, s, tf=tf)
        if r is not None:
            results.append(r)
    results.sort(key=lambda x: x["score"], reverse=True)
    chosen = [r["symbol"] for r in results[:max_pairs]]
    meta = {"ts": int(time.time()), "max_pairs": max_pairs, "tf": tf,
            "chosen": results[:max_pairs]}
    WATCH_F.parent.mkdir(parents=True, exist_ok=True)
    WATCH_F.write_text(json.dumps(meta, indent=2))
    return chosen, results
