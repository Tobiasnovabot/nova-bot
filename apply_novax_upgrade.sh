#!/usr/bin/env bash
set -euo pipefail

ROOT="$(pwd)"
backup_dir="z_backup_ultra_$(date -Is | tr ':' '-')"
echo "==> Backup til $backup_dir"
mkdir -p "$backup_dir"
tar -C "$ROOT" -czf "$backup_dir/repo_backup.tgz" .

echo "==> Mapper"
mkdir -p nova/engine nova/learn runtime logs metrics ~/.config/systemd/user

echo "==> requirements.txt"
touch requirements.txt
addreq(){ grep -q "^$1" requirements.txt || echo "$1" >> requirements.txt; }
addreq "ccxt>=4.3.89"
addreq "prometheus-client>=0.20.0"
addreq "pandas>=2.2.2"
addreq "numpy>=2.0.0"

echo "==> nova/engine/exchanges.py"
cat > nova/engine/exchanges.py <<'PY'
import os
import ccxt
from typing import Dict, Any, List

def make_clients(names: List[str]) -> Dict[str, Any]:
    out={}
    for name in names:
        n=name.strip().lower()
        if not n or n not in ccxt.exchanges: 
            continue
        klass=getattr(ccxt, n)
        kw={}
        if n=='binance':
            kw=dict(apiKey=os.getenv('BINANCE_KEY',''), secret=os.getenv('BINANCE_SECRET',''))
            if os.getenv('BINANCE_TESTNET')=='1':
                kw['options']={'defaultType':'future'}
                klass=ccxt.binanceusdm
        if n=='okx':
            kw=dict(apiKey=os.getenv('OKX_KEY',''), secret=os.getenv('OKX_SECRET',''), password=os.getenv('OKX_PASSWORD',''))
        c=klass(kw); c.enableRateLimit=True
        out[n]=c
    return out

def load_universe(clients: Dict[str,Any], quote='USDT', top_n=50, min_vol_usd=200000):
    universe=[]
    for ex, c in clients.items():
        try:
            markets=c.load_markets()
            rows=[]
            for m in markets.values():
                if not m.get('active'): 
                    continue
                if not m.get('spot'): 
                    continue
                sym=m['symbol']
                if not sym.endswith('/'+quote): 
                    continue
                info=m.get('info',{})
                vol=float(info.get('quoteVolume',0) or info.get('vol24h',0) or 0)
                if vol<=0:
                    try:
                        t=c.fetch_ticker(sym)
                        vol=float(t.get('quoteVolume',0) or 0)
                    except Exception:
                        vol=0
                rows.append((vol, sym))
            rows.sort(reverse=True)
            for vol,sym in rows[:top_n]:
                if vol>=min_vol_usd:
                    universe.append((ex,sym))
        except Exception:
            continue
    return universe
PY

echo "==> nova/engine/sizer.py"
cat > nova/engine/sizer.py <<'PY'
import numpy as np
def atr_size(equity_usdt: float, price: float, atr: float, risk_frac=0.005, max_leverage=1.0, min_usd=10.0) -> float:
    if price<=0 or atr<=0 or equity_usdt<=0: return 0.0
    dollar_risk = equity_usdt * risk_frac
    stop_dist = max(atr*2.0, price*0.01)
    qty = dollar_risk / stop_dist
    usd_exposure = qty * price
    usd_cap = equity_usdt * max_leverage * 0.2
    usd_final = max(min(usd_exposure, usd_cap), min_usd)
    return usd_final / price

def kelly_adjust(winrate: float, rr: float, base_frac=0.5):
    if rr<=0: return base_frac
    p=winrate; q=1-p
    k = (p - q/rr)
    k = max(-1.0, min(1.0, k))
    return max(0.1, min(0.9, base_frac*(0.5 + 0.5*k)))
PY

echo "==> nova/engine/pyramid.py"
cat > nova/engine/pyramid.py <<'PY'
def plan_pyramids(entry_price: float, atr: float, steps=3, step_mult=1.0):
    if entry_price<=0 or atr<=0 or steps<=0: return []
    return [entry_price + (i+1)*atr*step_mult for i in range(steps)]
PY

echo "==> nova/engine/risk_guard.py"
cat > nova/engine/risk_guard.py <<'PY'
class RiskGuard:
    def __init__(self, daily_dd_limit=0.05, max_positions=10):
        self.daily_dd_limit=daily_dd_limit
        self.max_positions=max_positions
        self.day_start_equity=None
        self.hard_block=False
        self.block_reason=''

    def start_day(self, equity):
        self.day_start_equity=float(equity)
        self.hard_block=False
        self.block_reason=''

    def check(self, equity, open_positions:int):
        if self.hard_block: return False, self.block_reason
        if self.day_start_equity:
            dd = 1.0 - float(equity)/self.day_start_equity
            if dd>=self.daily_dd_limit:
                self.hard_block=True
                self.block_reason=f"Daily DD hit: {dd:.2%}"
                return False, self.block_reason
        if open_positions>=self.max_positions:
            return False, "Position cap"
        return True, ""
PY

echo "==> nova/engine/metrics_ultra.py"
cat > nova/engine/metrics_ultra.py <<'PY'
from prometheus_client import Gauge, Counter, start_http_server
_ultra_up = Gauge('novax_ultra_up', 'Ultra runner up')
_ultra_err = Counter('novax_ultra_errors', 'Ultra runner errors')
_ultra_equity = Gauge('novax_ultra_equity', 'Equity in USDT')
_ultra_open = Gauge('novax_ultra_open_positions', 'Open positions count')
_ultra_universe = Gauge('novax_ultra_universe_size', 'Tracked pairs')

def start(port=9113):
    start_http_server(port)
    _ultra_up.set(1)

def set_equity(v): _ultra_equity.set(v)
def set_open(n): _ultra_open.set(n)
def set_universe(n): _ultra_universe.set(n)
def error(): _ultra_err.inc()
PY

echo "==> nova/engine/ultra_runner.py"
cat > nova/engine/ultra_runner.py <<'PY'
import os, time, json, signal
import numpy as np
from typing import Dict
from .exchanges import make_clients, load_universe
from .sizer import atr_size, kelly_adjust
from .pyramid import plan_pyramids
from .risk_guard import RiskGuard
from .metrics_ultra import start as metrics_start, set_equity, set_open, set_universe, error as metrics_err

def calc_atr(ohlcv, n=14):
    if len(ohlcv)<n+1: return None
    trs=[]
    for i in range(1, n+1):
        o,h,l,c,v=ohlcv[-i]
        pc=ohlcv[-i-1][4]
        tr=max(h-l, abs(h-pc), abs(l-pc))
        trs.append(tr)
    return float(np.mean(trs)) if trs else None

def load_equity():
    try:
        with open('equity.json','r') as f: 
            d=json.load(f); return float(d.get('equity_usdt', 1000))
    except Exception:
        return float(os.getenv('EQUITY_USDT','1000'))

def save_trade(rec: dict):
    os.makedirs('runtime', exist_ok=True)
    with open('runtime/trades.jsonl','a') as f: 
        f.write(json.dumps(rec, ensure_ascii=False)+'\n')

def main():
    metrics_start(int(os.getenv('ULTRA_METRICS_PORT','9113')))
    equity = load_equity()
    set_equity(equity)
    rg = RiskGuard(daily_dd_limit=float(os.getenv('DAILY_DD_LIMIT','0.05')),
                   max_positions=int(os.getenv('MAX_POSITIONS','10')))
    rg.start_day(equity)

    names=os.getenv('EXCHANGE','binance,okx').split(',')
    clients=make_clients(names)

    universe = load_universe(clients, quote=os.getenv('QUOTE','USDT'),
                             top_n=int(os.getenv('TOP_N','80')),
                             min_vol_usd=int(os.getenv('MIN_VOL_USD','200000')))
    set_universe(len(universe))

    open_positions={}
    winrate=0.5; rr=1.2
    base_risk=float(os.getenv('RISK_FRAC','0.005'))
    scan_limit=int(os.getenv('SCAN_LIMIT','60'))
    trail=float(os.getenv('TRAIL_PCT','0.03'))
    take_min=float(os.getenv('TAKE_MIN','0.02'))

    print(f"[ultra] start equity={equity:.2f} pairs={len(universe)}")

    stop=False
    def _stop(*_): 
        nonlocal stop; stop=True
    signal.signal(signal.SIGINT,_stop); signal.signal(signal.SIGTERM,_stop)

    while not stop:
        try:
            set_open(len(open_positions))
            if int(time.time()) % 3600 < 5:
                universe = load_universe(clients, quote=os.getenv('QUOTE','USDT'),
                                         top_n=int(os.getenv('TOP_N','80')),
                                         min_vol_usd=int(os.getenv('MIN_VOL_USD','200000')))
                set_universe(len(universe))

            for ex,sym in universe[:scan_limit]:
                c=clients[ex]
                try:
                    ohl = c.fetch_ohlcv(sym, timeframe='5m', limit=80)
                    closes=[x[4] for x in ohl]
                    price=float(closes[-1])
                    sma20=float(np.mean(closes[-20:]))
                    mom=(price/closes[-7]-1.0) if closes[-7]>0 else 0.0

                    if (ex,sym) not in open_positions:
                        if price>sma20 and mom>0.01:
                            atr = calc_atr(ohl) or price*0.01
                            frac=kelly_adjust(winrate, rr, base_frac=1.0)*base_risk
                            qty = atr_size(equity, price, atr, risk_frac=frac, max_leverage=float(os.getenv('MAX_LEV','1.0')))
                            if qty>0:
                                ok,reason = rg.check(equity, len(open_positions))
                                if not ok: 
                                    continue
                                try:
                                    c.create_order(sym,'market','buy', qty)
                                except Exception:
                                    continue
                                pyramids=plan_pyramids(price, atr, steps=int(os.getenv('PYRAMID_STEPS','3')),
                                                       step_mult=float(os.getenv('PYRAMID_ATR_MULT','1.0')))
                                open_positions[(ex,sym)]={'qty':qty,'entry':price,'targets':pyramids,'peak':price}
                                save_trade({'t':time.time(),'ex':ex,'sym':sym,'side':'buy','qty':qty,'price':price,'type':'entry'})
                    else:
                        pos=open_positions[(ex,sym)]
                        pos['peak']=max(pos['peak'], price)
                        # pyramids
                        if pos['targets'] and price>=pos['targets'][0]:
                            add_qty = pos['qty']*float(os.getenv('PYRAMID_ADD_FRAC','0.5'))
                            try:
                                c.create_order(sym,'market','buy', add_qty)
                                pos['qty']+=add_qty
                                pos['targets']=pos['targets'][1:]
                                save_trade({'t':time.time(),'ex':ex,'sym':sym,'side':'buy','qty':add_qty,'price':price,'type':'pyramid'})
                            except Exception:
                                pass
                        # trailing exit
                        entry=pos['entry']; peak=pos['peak']
                        if entry>0 and (peak-entry)/entry>=take_min:
                            stop_price = peak*(1.0-trail)
                            if price<=stop_price:
                                qty=pos['qty']
                                try:
                                    c.create_order(sym,'market','sell', qty)
                                except Exception:
                                    pass
                                pnl=(price-entry)/entry
                                if pnl>0: winrate = 0.9*winrate + 0.1*1.0
                                else:     winrate = 0.9*winrate
                                rr = 0.9*rr + 0.1*max(0.5, abs(pnl)*10)
                                save_trade({'t':time.time(),'ex':ex,'sym':sym,'side':'sell','qty':qty,'price':price,'type':'exit','pnl':pnl})
                                del open_positions[(ex,sym)]
                except Exception:
                    metrics_err()
                    continue

            set_equity(equity)
            time.sleep(float(os.getenv('LOOP_DELAY','5')))
        except Exception:
            metrics_err()
            time.sleep(1)

if __name__=='__main__':
    main()
PY

echo "==> systemd unit"
cat > ~/.config/systemd/user/nova-engine-ultra.service <<'UNIT'
[Unit]
Description=NOVAX Ultra Engine
After=network-online.target

[Service]
WorkingDirectory=%h/nova-bot
Environment=MODE=ultra
Environment=EXCHANGE=binance,okx
Environment=QUOTE=USDT
Environment=TOP_N=120
Environment=MIN_VOL_USD=200000
Environment=RISK_FRAC=0.005
Environment=MAX_POSITIONS=12
Environment=DAILY_DD_LIMIT=0.06
Environment=PYRAMID_STEPS=3
Environment=PYRAMID_ATR_MULT=1.0
Environment=PYRAMID_ADD_FRAC=0.5
Environment=TRAIL_PCT=0.03
Environment=TAKE_MIN=0.02
Environment=LOOP_DELAY=5
Environment=ULTRA_METRICS_PORT=9113
ExecStart=%h/nova-bot/.venv/bin/python -u nova/engine/ultra_runner.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
UNIT

echo "==> README-ultra.md"
cat > README-ultra.md <<'MD'
Ultra-runner: dynamisk univers (Binance+OKX), ATR-sizing + Kelly, pyramidering,
daglig DD-vakt, enkel læring av winrate/rr, metrics på :9113.
Start: python -u nova/engine/ultra_runner.py
MD

echo "==> Ferdig"
