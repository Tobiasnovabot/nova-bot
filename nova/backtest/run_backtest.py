import os, json, math, time
from pathlib import Path
from datetime import datetime, timezone, timezone, timedelta
from typing import List, Dict
import ccxt

# gjenbruk strategier
from strategies import ema_cross, rsi_reversion, breakout

OUT_DIR = Path("reports"); OUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE = Path("data/ohlcv"); CACHE.mkdir(parents=True, exist_ok=True)

def load_ohlcv(ex, symbol: str, timeframe: str, days: int) -> List[List[float]]:
    since = int((time.time() - days*86400) * 1000)
    key = f"{symbol.replace('/','_')}_{timeframe}_{days}d.json"
    cache_f = CACHE / key
    if cache_f.exists():
        try: return json.loads(cache_f.read_text())
        except: pass
    data = ex.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=2000)
    cache_f.write_text(json.dumps(data))
    return data

def run(signals, ohlc, fee=0.001, start_usdt=1000.0, risk_frac=0.02):
    balance = {"USDT": start_usdt}
    pos = None  # {"entry":p, "qty":q}
    trades = []
    equity = []
    for i, c in enumerate(ohlc):
        ts, o, h, l, cl, vol = c
        # bygg ticker-lignende dict for strategi API
        ticker = {"last": cl, "close": cl}
        votes = 0.0
        for name, params, fn, w in signals:
            act, meta = fn(ticker, ohlc[:i+1], params)
            if act == "buy": votes += w
            elif act == "sell": votes -= w
        # enkel router
        if pos is None and votes > 0.8:
            stake = balance["USDT"] * risk_frac
            if stake > 5:
                qty = stake / cl
                cost = stake * (1+fee)
                if balance["USDT"] >= cost:
                    balance["USDT"] -= cost
                    pos = {"entry": cl, "qty": qty}
                    trades.append({"ts": ts, "side": "buy", "price": cl, "qty": qty})
        elif pos is not None and votes < -0.8:
            proceeds = pos["qty"] * cl
            proceeds -= proceeds * fee
            pnl = (cl - pos["entry"]) * pos["qty"] - (pos["entry"]*pos["qty"]*fee) - (cl*pos["qty"]*fee)
            balance["USDT"] += proceeds
            trades.append({"ts": ts, "side": "sell", "price": cl, "qty": pos["qty"], "pnl": pnl})
            pos = None
        # mark-to-market
        eq = balance["USDT"] + (pos["qty"]*cl if pos else 0.0)
        equity.append({"ts": ts, "equity": eq})
    # lukk ev. posisjon ved slutt
    if pos:
        cl = ohlc[-1][4]
        proceeds = pos["qty"] * cl
        proceeds -= proceeds * fee
        pnl = (cl - pos["entry"]) * pos["qty"] - (pos["entry"]*pos["qty"]*fee) - (cl*pos["qty"]*fee)
        balance["USDT"] += proceeds
        trades.append({"ts": ohlc[-1][0], "side":"sell","price":cl,"qty":pos["qty"],"pnl":pnl})
        pos=None
        eq = balance["USDT"]; equity.append({"ts": ohlc[-1][0], "equity": eq})

    # metrikker
    eq_vals = [x["equity"] for x in equity]
    ret = (eq_vals[-1] - eq_vals[0]) / eq_vals[0] if eq_vals else 0.0
    peak, dd_max = -1e18, 0.0
    for v in eq_vals:
        peak = max(peak, v)
        dd = (peak - v) / peak if peak>0 else 0.0
        dd_max = max(dd_max, dd)
    wins = sum(1 for t in trades if t["side"]=="sell" and t.get("pnl",0)>0)
    losses = sum(1 for t in trades if t["side"]=="sell" and t.get("pnl",0)<=0)
    res = {
        "start_usdt": start_usdt,
        "end_usdt": eq_vals[-1] if eq_vals else start_usdt,
        "return": ret,
        "max_drawdown": dd_max,
        "trades_closed": wins+losses,
        "winrate": wins / max(1, wins+losses),
        "fees_assumed": fee,
    }
    return res, trades, equity

def main():
    ex_name = os.getenv("EXCHANGE","binance").lower()
    symbol = os.getenv("BT_SYMBOL", "BTC/USDT")
    timeframe = os.getenv("BT_TF", "1h")
    days = int(os.getenv("BT_DAYS", "90"))
    start_usdt = float(os.getenv("BT_START", "1000"))
    fee = float(os.getenv("BT_FEE", "0.001"))
    risk_frac = float(os.getenv("BT_RISK", "0.02"))

    cls = getattr(ccxt, ex_name)
    ex = cls({"enableRateLimit": True, "options": {"defaultType":"spot"}})
    print(f"download {symbol} {timeframe} {days}d ...")
    ohlc = load_ohlcv(ex, symbol, timeframe, days)

    cfg = {"ema_fast":12,"ema_slow":26,"rsi_period":14,"bo_lookback":50}
    signals = [
        ("ema", ema_cross.setup(cfg), ema_cross.signal, 1.0),
        ("rsi", rsi_reversion.setup(cfg), rsi_reversion.signal, 0.8),
        ("bo" , breakout.setup(cfg), breakout.signal, 0.6),
    ]
    res, trades, equity = run(signals, ohlc, fee=fee, start_usdt=start_usdt, risk_frac=risk_frac)

    # skriv rapport
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base = f"{symbol.replace('/','_')}_{timeframe}_{days}d_{ts}"
    (OUT_DIR / f"{base}_summary.json").write_text(json.dumps(res, indent=2))
    (OUT_DIR / f"{base}_trades.json").write_text(json.dumps(trades, indent=2))
    (OUT_DIR / f"{base}_equity.json").write_text(json.dumps(equity, indent=2))
    print(json.dumps(res, indent=2))
    print(f"reports written to reports/{base}_*.json")

if __name__ == "__main__":
    main()
