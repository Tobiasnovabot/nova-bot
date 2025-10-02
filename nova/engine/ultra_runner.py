import os, time, json, pathlib, traceback
from typing import Optional

from .metrics import (
    start as metrics_start,
    set_equity, set_open, set_universe, set_unrealized_pnl,
    set_strategy_enabled, inc_strategy_signal, set_scan_pairs,
    inc_pair_eval, inc_loop, error as m_err
)
from .notify import send as alert
from .router import load_modules, parse_strat_set
from .strategy_toggle import load_overrides, is_enabled
from .exchanges import make_clients, load_universe
from .broker_paper import PaperBroker

try:
    from .broker_live import BinanceLiveBroker  # valgfri live
except Exception:
    BinanceLiveBroker = None  # type: ignore

DUST = 1e-12
BAL_REFRESH_SECS = float(os.getenv('BAL_REFRESH_SECS', '30.0'))

def _read_equity_file() -> float:
    p = pathlib.Path('runtime/equity.json')
    if p.exists():
        try:
            return float((json.loads(p.read_text()) or {}).get('equity', 1000.0))
        except Exception:
            pass
    return 1000.0

def _count_open_positions_fallback(broker, quote: str) -> int:
    pos = broker.state.get("positions", {}) or {}
    n = 0
    for sym, qty in pos.items():
        try:
            if float(qty) <= DUST:
                continue
            base, q = sym.split("/")
            if q != quote or base == quote:
                continue
            n += 1
        except Exception:
            continue
    return n

def run_ultra():
    quote      = os.getenv('QUOTE', 'USDT').upper()
    top_n      = int(os.getenv('TOP_N', '300'))
    min_vol    = float(os.getenv('MIN_VOL_USD', '2000'))
    limit      = int(os.getenv('SCAN_LIMIT', '150'))
    delay      = float(os.getenv('LOOP_DELAY', '5'))
    strat_set  = os.getenv('STRAT_SET', 'momentum,meanrev')
    risk_frac  = float(os.getenv('RISK_FRAC', '0.01'))
    broker_mode = os.getenv('BROKER', 'paper').lower()

    print(f"[ultra] params quote={quote} top_n={top_n} min_vol_usd={min_vol} scan_limit={limit}", flush=True)
    print(f"[ultra] metrics_port={os.getenv('ULTRA_METRICS_PORT','9124')}", flush=True)

    pathlib.Path('runtime').mkdir(exist_ok=True)

    # Start metrics – tolerer port i bruk
    try:
        metrics_start()
    except OSError as e:
        if "Address already in use" in str(e):
            print("[metrics] already running on port, continuing", flush=True)
        else:
            raise

    # Markedsdata-klienter (public)
    clients = make_clients(['binance'])

    # Broker (live eller paper)
    if broker_mode == 'binance' and BinanceLiveBroker is not None:
        broker = BinanceLiveBroker(quote=quote)
        try:
            eq = float(broker.total_equity_quote())
        except Exception:
            eq = float(broker.fetch_equity_quote() or 0.0)
    else:
        broker = PaperBroker()
        eq = _read_equity_file()

    broker.state["equity"] = eq
    broker.state.setdefault("positions", {})
    # Open = antall coins ≠ quote
    if hasattr(broker, "count_open_positions"):
        set_open(broker.count_open_positions())
    else:
        set_open(_count_open_positions_fallback(broker, quote))
    set_equity(eq)
    set_unrealized_pnl(0.0)

    # Strategier
    mods = load_modules(parse_strat_set(strat_set))
    for n in mods:
        try:
            set_strategy_enabled(n, True)
        except Exception:
            pass

    last_bal_ts = 0.0

    while True:
        try:
            inc_loop()
            now = time.time()

            # Oppdater equity periodisk (mark-to-market for live)
            if broker_mode == 'binance' and (now - last_bal_ts >= BAL_REFRESH_SECS):
                try:
                    total = float(broker.total_equity_quote())
                    broker.state["equity"] = total
                    set_equity(total)
                    pos = ", ".join(broker.positions_summary(10))
                    if pos:
                        print(f"[positions] {pos}", flush=True)
                    print(f"[ultra] equity_mark_to_market({quote})={total:.6f}", flush=True)
                except Exception:
                    m_err()
                last_bal_ts = now

            load_overrides()

            # Universet
            pairs = load_universe(clients, quote=quote, top_n=top_n, min_vol_usd=min_vol)[:limit]
            set_universe(len(pairs))
            set_scan_pairs(len(pairs))
            if pairs:
                print("[scan] top10:", ", ".join(pairs[:10]), flush=True)
            print(f"[ultra] universe size = {len(pairs)}", flush=True)

            # Oppdater posisjons/PnL metrics
            try:
                if hasattr(broker, "count_open_positions"):
                    set_open(broker.count_open_positions())
                else:
                    set_open(_count_open_positions_fallback(broker, quote))
                if hasattr(broker, "unrealized_pnl"):
                    set_unrealized_pnl(broker.unrealized_pnl())
            except Exception:
                pass

            # Evaluer strategier
            for name, mod in mods.items():
                if not is_enabled(name):
                    continue
                try:
                    set_strategy_enabled(name, True)
                except Exception:
                    pass

                for sym in pairs:
                    inc_pair_eval()
                    # pris (fallback pr quote)
                    try:
                        price = broker.last_price(sym)
                    except Exception:
                        price = None
                    if price is None:
                        if sym.endswith(f'BTC/{quote}'):
                            price = 60000.0
                        elif sym.endswith(f'ETH/{quote}'):
                            price = 3000.0
                        else:
                            price = 1.0

                    # signal og utførelse
                    try:
                        sig = mod.signal(sym, price, broker)
                        if not sig:
                            continue
                        inc_strategy_signal(name)
                        side = 'buy' if sig > 0 else 'sell'

                        equity   = float(broker.state.get("equity", 0.0))
                        notional = max(0.0, equity * risk_frac)
                        qty      = max(0.0, notional / float(price))

                        if qty > 0.0:
                            broker.execute(sym, side, qty, price)
                    except Exception as e:
                        m_err()
                        alert('strategy_error', {'strategy': name, 'err': str(e)})

            time.sleep(delay)

        except Exception as e:
            m_err()
            alert('ultra_runner_error', {'err': str(e), 'tb': traceback.format_exc()})
            time.sleep(2)

if __name__ == "__main__":
    run_ultra()
