set -euo pipefail
cd ~/nova-bot

# ultra_runner (stabil + auto-exec ved signal)
cat > nova/engine/ultra_runner.py <<'PY'
import os, time, json, pathlib, traceback
from .metrics import (start as metrics_start, set_equity, set_open, set_universe,
    set_unrealized_pnl, set_strategy_enabled, inc_strategy_signal, error as m_err)
from .notify import send as alert
from .router import load_modules, parse_strat_set
from .strategy_toggle import load_overrides, is_enabled
from .exchanges import make_clients, load_universe
from .broker_paper import PaperBroker

def _read_equity_file():
    p = pathlib.Path('runtime/equity.json')
    if p.exists():
        try: return float((json.loads(p.read_text()) or {}).get('equity', 1000.0))
        except Exception: pass
    return 1000.0

def run_ultra():
    quote=os.getenv('QUOTE','USDT'); top_n=int(os.getenv('TOP_N','200'))
    min_vol=float(os.getenv('MIN_VOL_USD','2000')); limit=int(os.getenv('SCAN_LIMIT','200'))
    delay=float(os.getenv('LOOP_DELAY','5')); strat_set=os.getenv('STRAT_SET','momentum,meanrev')
    print(f"[ultra] params quote={quote} top_n={top_n} min_vol_usd={min_vol} scan_limit={limit}", flush=True)
    print(f"[ultra] metrics_port={os.getenv('ULTRA_METRICS_PORT','9124')}", flush=True)

    pathlib.Path('runtime').mkdir(exist_ok=True); metrics_start()
    broker=PaperBroker(); broker.state["equity"]=_read_equity_file()
    set_equity(broker.state["equity"]); set_open(len(broker.state.get("positions",{}))); set_unrealized_pnl(0.0)
    clients=make_clients(['binance'])
    mods=load_modules(parse_strat_set(strat_set))
    for n in mods: 
        try: set_strategy_enabled(n, True)
        except Exception: pass

    while True:
        try:
            load_overrides()
            pairs=load_universe(clients, quote=quote, top_n=top_n, min_vol_usd=min_vol)[:limit]
            set_universe(len(pairs))
            try:
                set_equity(broker.state["equity"])
                set_open(len(broker.state.get("positions",{})))
                set_unrealized_pnl(broker.unrealized_pnl())
            except Exception: pass

            for name, mod in mods.items():
                if not is_enabled(name): continue
                try: set_strategy_enabled(name, True)
                except Exception: pass
                for sym in pairs:
                    price=None
                    try: price=broker.last_price(sym)
                    except Exception: pass
                    if price is None:
                        price = 60000.0 if sym.endswith('BTC/USDT') else (3000.0 if sym.endswith('ETH/USDT') else 1.0)
                    sig=0
                    try:
                        sig=mod.signal(sym, price, broker)
                        if sig:
                            inc_strategy_signal(name)
                            side='buy' if sig>0 else 'sell'
                            try: broker.execute(sym, side, 0.001, price)
                            except Exception as e: m_err(); alert('broker_error', {'sym':sym,'err':str(e)})
                    except Exception as e:
                        m_err(); alert('strategy_error', {'strategy':name,'err':str(e)})
            time.sleep(delay)
        except Exception as e:
            m_err(); alert('ultra_runner_error', {'err':str(e), 'tb':traceback.format_exc()}); time.sleep(2)

if __name__=="__main__": run_ultra()
PY

# Strategier med signal()
mkdir -p nova/engine/strategies
printf "%s\n" "# pkg init" > nova/engine/strategies/__init__.py
cat > nova/engine/strategies/momentum.py <<'PY'
_last={}
def signal(symbol, price, broker):
    if price is None: return 0
    p0=_last.get(symbol); _last[symbol]=price
    if not p0: return 0
    ch=(price-p0)/p0
    if ch>0.003: return 1
    if ch<-0.003: return -1
    return 0
PY
cat > nova/engine/strategies/meanrev.py <<'PY'
_ema={}; _alpha=0.2
def signal(symbol, price, broker):
    if price is None: return 0
    ema=_ema.get(symbol, price)
    ema=_alpha*price+(1-_alpha)*ema
    _ema[symbol]=ema
    if price<ema*0.997: return 1
    if price>ema*1.003: return -1
    return 0
PY

# .env
sed -i 's/^STRAT_SET=.*/STRAT_SET=momentum,meanrev/' .env
sed -i 's/^LOOP_DELAY=.*/LOOP_DELAY=3/' .env

# Rydd + baseline runtime
find nova -name '*.pyc' -delete || true
find nova -type d -name '__pycache__' -exec rm -rf {} + || true
mkdir -p runtime; printf '{"equity": 1000.0}\n' > runtime/equity.json
rm -f runtime/trades.jsonl

# Precompile (fanger syntax)
python - <<'PY'
import compileall, sys
sys.exit(0 if compileall.compile_dir('nova', force=True, quiet=1) else 1)
PY

# Restart
systemctl --user restart nova-engine-ultra.service
sleep 8

# Sjekk
echo "-- metrics (up/universe/strategier) --"
curl -s localhost:9124/metrics | grep -E '^novax_ultra_(up|universe_size|strategy_enabled)'
echo "-- metrics (signals/trades/pnl/equity) --"
curl -s localhost:9124/metrics | grep -E '^novax_ultra_(strategy_signals_total|trades_total|pnl_total|pnl_unrealized|equity)' || true
