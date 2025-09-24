from nova.exchange import build_exchange
import argparse, json, pathlib, os
from nova.risk.position_sizing import compute_size, atr_from_ohlcv, ATR_LOOKBACK
def fetch_ohlcv(symbol:str, tf="1h", limit=ATR_LOOKBACK+50):
    try:
        import ccxt
        ex=build_exchange()
        return ex.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
    except Exception:
        return []
def last_price_from_ohlcv(ohlcv):
    try: return float(ohlcv[-1][4])
    except Exception: return 0.0

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("symbol")
    ap.add_argument("--equity", type=float, default=10000.0)
    ap.add_argument("--risk", type=int, default=5)
    ap.add_argument("--tf", default="1h")
    args=ap.parse_args()

    o=fetch_ohlcv(args.symbol, args.tf)
    atr=atr_from_ohlcv(o)
    px = last_price_from_ohlcv(o)
    out=compute_size(px, args.equity, args.risk, atr)
    print(json.dumps({"symbol":args.symbol,"equity":args.equity,"risk":args.risk,"atr":atr,**out}, separators=(",",":")))