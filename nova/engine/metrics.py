from prometheus_client import start_http_server, Gauge, Counter

_G_STARTED = False

G_UP         = Gauge('novax_ultra_up', 'Engine up')
G_UNIVERSE   = Gauge('novax_ultra_universe_size', 'Tracked pairs')
G_EQUITY     = Gauge('novax_ultra_equity', 'Equity')
G_OPEN       = Gauge('novax_ultra_open_positions', 'Open positions')
G_UNREAL     = Gauge('novax_ultra_pnl_unrealized', 'Unrealized PnL')
G_REAL       = Gauge('novax_ultra_pnl_realized', 'Realized PnL')

G_SCAN_PAIRS = Gauge('novax_ultra_scan_pairs', 'Pairs scanned per loop')
C_PAIR_EVALS = Counter('novax_ultra_pair_evals_total', 'Total pair evals')
C_LOOPS      = Counter('novax_ultra_loops_total', 'Main loop iterations')

C_SIG        = Counter('novax_ultra_strategy_signals_total', 'Signals', ['strategy'])
C_TRADES     = Counter('novax_ultra_trades_total', 'Trades', ['side'])
G_STRAT_EN   = Gauge('novax_ultra_strategy_enabled', 'Strategy enabled', ['strategy'])

def start(port:int = 9124):
    global _G_STARTED
    if not _G_STARTED:
        start_http_server(port)
        _G_STARTED = True
    G_UP.set(1.0)

def set_universe(n:int):         G_UNIVERSE.set(float(n))
def set_equity(x:float):         G_EQUITY.set(float(x))
def set_open(n:int):             G_OPEN.set(float(n))
def set_unrealized_pnl(x:float): G_UNREAL.set(float(x))
def set_realized_pnl(x:float):   G_REAL.set(float(x))

def set_scan_pairs(n:int):       G_SCAN_PAIRS.set(float(n))      # <– nødvendig navn

def inc_pair_eval(n:int=1):      C_PAIR_EVALS.inc(n)
def add_pair_evals(n:int=1):     C_PAIR_EVALS.inc(n)             # <– alias som koden spør etter
def inc_loop(n:int=1):           C_LOOPS.inc(n)

def set_strategy_enabled(name:str, on:bool):
    G_STRAT_EN.labels(strategy=name).set(1.0 if on else 0.0)

def inc_strategy_signal(name:str):
    C_SIG.labels(strategy=name).inc()

def trade(side:str):
    C_TRADES.labels(side=side).inc()

def inc_trade(side:str):         # alias for gammel import
    trade(side)

def error():
    pass
