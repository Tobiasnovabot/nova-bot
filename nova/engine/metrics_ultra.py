from prometheus_client import Gauge, Counter, start_http_server
import os, pathlib

_ultra_up = Gauge('novax_ultra_up','Ultra runner up')
_ultra_err = Counter('novax_ultra_errors','Ultra runner errors')
_ultra_equity = Gauge('novax_ultra_equity','Equity USDT')
_ultra_open = Gauge('novax_ultra_open_positions','Open positions')
_ultra_universe = Gauge('novax_ultra_universe_size','Tracked pairs')

def start(port=9113):
    chosen = int(os.getenv('ULTRA_METRICS_PORT', port))
    pathlib.Path('runtime').mkdir(parents=True, exist_ok=True)
    with open('runtime/ultra_metrics_port','w') as f: f.write(str(chosen))
    print(f"[ultra] metrics_port={chosen}", flush=True)
    start_http_server(chosen, addr="127.0.0.1")
    _ultra_up.set(1)

def set_equity(v): _ultra_equity.set(v)
def set_open(n): _ultra_open.set(n)
def set_universe(n):
    _ultra_universe.set(n)
    print(f"[ultra] universe size = {n}", flush=True)
    pathlib.Path('runtime').mkdir(parents=True, exist_ok=True)
    with open('runtime/universe_size','w') as f: f.write(str(n))
def error(): _ultra_err.inc()
