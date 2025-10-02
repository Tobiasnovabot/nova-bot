import os, time, math, json
from pathlib import Path
from typing import List, Tuple, Dict
import ccxt
import pandas as pd
import numpy as np

def fetch_ohlcv(exchange:str, symbol:str, timeframe:str='1h', since_ms:int=None, limit:int=1500) -> pd.DataFrame:
    klass = getattr(ccxt, exchange)
    c = klass({})
    c.enableRateLimit = True
    c.timeout = 15000
    raw = c.fetch_ohlcv(symbol, timeframe=timeframe, since=since_ms, limit=limit)
    cols = ['ts','open','high','low','close','volume']
    df = pd.DataFrame(raw, columns=cols)
    df['ts'] = pd.to_datetime(df['ts'], unit='ms', utc=True)
    return df

def strat_momentum(df: pd.DataFrame) -> pd.DataFrame:
    # breakout over 24h høy + enkel trailing
    d = df.copy()
    d['hi24'] = d['high'].rolling(24, min_periods=24).max().shift(1)
    d['signal'] = (d['close'] > d['hi24']).astype(int)  # 1 = long, 0 = flat
    return d

def strat_meanrev(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d['ma'] = d['close'].rolling(24, min_periods=24).mean()
    d['std'] = d['close'].rolling(24, min_periods=24).std()
    d['lb'] = d['ma'] - 2*d['std']
    d['ub'] = d['ma'] + 2*d['std']
    # long når under lower band, exit når tilbake over ma
    sig = np.zeros(len(d))
    pos = 0
    for i in range(len(d)):
        if pos==0 and i>0 and d['close'].iat[i] < d['lb'].iat[i]:
            pos = 1
        elif pos==1 and d['close'].iat[i] > d['ma'].iat[i]:
            pos = 0
        sig[i] = pos
    d['signal'] = sig
    return d

def simulate(df: pd.DataFrame, equity0: float=1000.0, risk_frac: float=0.003,
             fee_bps: float=5, slip_bps: float=5) -> Tuple[pd.DataFrame, Dict]:
    d = df.copy()
    fee = fee_bps/1e4; slip = slip_bps/1e4
    eq = equity0
    pos = 0.0
    entry = 0.0
    qty = 0.0
    trades = []
    pnl_series = []

    for i in range(len(d)):
        px = float(d['close'].iat[i])
        sig = int(d['signal'].iat[i] or 0)

        # exit
        if pos>0 and sig==0:
            fill = px*(1-slip)*(1-fee)
            pnl = (fill-entry)*qty
            eq += pnl
            trades.append({'ts':str(d['ts'].iat[i]), 'side':'sell', 'price':fill, 'qty':qty, 'pnl':pnl})
            pos = 0.0; qty=0.0; entry=0.0

        # enter
        if pos==0 and sig==1:
            usd = max(eq*risk_frac, 10.0)
            qty = usd / max(px, 1e-8)
            fill = px*(1+slip)*(1+fee)
            entry = fill
            pos = 1.0
            trades.append({'ts':str(d['ts'].iat[i]), 'side':'buy', 'price':fill, 'qty':qty, 'pnl':0.0})

        # mark-to-market
        if pos>0:
            unreal = (px-entry)*qty
        else:
            unreal = 0.0
        pnl_series.append(unreal)

    d['unrealized'] = pnl_series + [0.0]*(len(d)-len(pnl_series))
    d['equity'] = eq + d['unrealized']
    d['position'] = (d['signal']>0).astype(int)

    # metrics
    realized = sum(t['pnl'] for t in trades)
    wins = [t for t in trades if t['side']=='sell' and t['pnl']>0]
    losses = [t for t in trades if t['side']=='sell' and t['pnl']<=0]
    winrate = (len(wins)/max(1,len(wins)+len(losses)))
    dd = (d['equity'].cummax()-d['equity']).max() / max(1.0, equity0)
    ret = d['equity'].iloc[-1] / equity0 - 1.0
    # enkel Sharpe på bar-returns
    rets = d['equity'].pct_change().replace([np.inf,-np.inf], np.nan).dropna()
    sharpe = float(np.mean(rets)/max(np.std(rets),1e-9))*np.sqrt(24*365) if len(rets)>3 else 0.0

    summary = dict(
        equity_start=equity0, equity_end=float(d['equity'].iloc[-1]),
        realized=float(realized), trades=len(losses)+len(wins),
        winrate=float(winrate), max_dd=float(dd), ret=float(ret), sharpe=float(sharpe)
    )
    return d, summary

def run_backtest(symbol="BTC/USDT", exchange="binance", timeframe="1h",
                 days=30, strategy="momentum", outdir="runtime/backtests",
                 equity0=1000.0, risk_frac=0.003) -> Dict:
    Path(outdir).mkdir(parents=True, exist_ok=True)
    since_ms = int((time.time() - days*86400)*1000)
    df = fetch_ohlcv(exchange, symbol, timeframe, since_ms)
    if strategy == "momentum":
        df2 = strat_momentum(df)
    elif strategy == "meanrev":
        df2 = strat_meanrev(df)
    else:
        raise ValueError("unknown strategy")
    sim, summary = simulate(df2, equity0=equity0, risk_frac=risk_frac)
    base = f"{symbol.replace('/','-')}_{strategy}_{timeframe}_{days}d"
    csv_path = f"{outdir}/{base}.csv"
    json_path = f"{outdir}/{base}.json"
    sim.to_csv(csv_path, index=False)
    Path(json_path).write_text(json.dumps(summary, indent=2))
    return {"csv": csv_path, "summary": summary}

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="BTC/USDT")
    ap.add_argument("--exchange", default="binance")
    ap.add_argument("--timeframe", default="1h")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--strategy", choices=["momentum","meanrev"], default="momentum")
    ap.add_argument("--equity0", type=float, default=1000.0)
    ap.add_argument("--risk", type=float, default=0.003)
    args = ap.parse_args()
    res = run_backtest(args.symbol, args.exchange, args.timeframe, args.days, args.strategy, equity0=args.equity0, risk_frac=args.risk)
    print(json.dumps(res, indent=2))
