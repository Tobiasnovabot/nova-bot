import os, sys, threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APP_UP = Gauge("novax_app_up", "App liveness flag")
STRATS_TOTAL = Gauge("novax_strategies_total", "Number of discovered strategies")
SIGNALS = Counter("novax_signals_total", "Signals emitted", ["name"])
ORDERS  = Counter("novax_orders_total",  "Orders placed",  ["exchange","side"])
ERRORS  = Counter("novax_errors_total",  "Errors",         ["where"])

_METRICS_STARTED=False
_HEALTH_STARTED=False

def start_metrics_server(port=None):
    # explicit HTTP exporter
    global _METRICS_STARTED
    if _METRICS_STARTED:
        print(f"[metrics] already initialized (:{port or 'env'})", flush=True); return
    port = int(port or os.getenv("METRICS_PORT","9111"))
    try:
        start_http_server(port, addr="0.0.0.0")
        print(f"[metrics] serving on 0.0.0.0:{port}", flush=True)
    except OSError as e:
        print(f"[metrics] already running on :{port} ({e})", flush=True)
    APP_UP.set(1); _METRICS_STARTED=True

class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/health"):
            self.send_response(200); self.send_header("Content-Type","text/plain"); self.end_headers(); self.wfile.write(b"ok")
        else:
            self.send_response(404); self.end_headers()
    def log_message(self, *a, **k): return

def start_health_server(port=None):
    global _HEALTH_STARTED
    if _HEALTH_STARTED:
        print(f"[health] already initialized (:{port or 'env'})", flush=True); return
    port = int(port or os.getenv("HEALTH_PORT","8088"))
    def _run():
        try:
            srv=ThreadingHTTPServer(("0.0.0.0",port),_HealthHandler); srv.allow_reuse_address=True
            print(f"[health] serving on 0.0.0.0:{port}", flush=True); srv.serve_forever()
        except Exception as e:
            print(f"[health] failed: {e}", flush=True)
    threading.Thread(target=_run, name="health-http", daemon=True).start(); _HEALTH_STARTED=True

def inc_signal(name:str): SIGNALS.labels(name=name).inc()
def inc_order(exchange:str, side:str): ORDERS.labels(exchange=exchange, side=side).inc()
def inc_error(where:str): ERRORS.labels(where=where).inc()

def discover_strategies(strat_dir: Path):
    try:
        if not strat_dir.exists():
            print(f"[strategies] directory missing: {strat_dir}", flush=True)
            STRATS_TOTAL.set(0); return []
        parent=strat_dir.parent
        if str(parent) not in sys.path: sys.path.insert(0, str(parent))
        files=sorted(p for p in strat_dir.rglob("*.py") if p.name!="__init__.py")
        STRATS_TOTAL.set(len(files)); ok=fail=0; names=[]
        import importlib.util
        for p in files:
            mod_name=".".join(p.relative_to(parent).with_suffix("").parts)
            try:
                spec=importlib.util.spec_from_file_location(mod_name,p); m=importlib.util.module_from_spec(spec)
                assert spec and spec.loader; spec.loader.exec_module(m)
                ok+=1; names.append(mod_name); print(f"[Strategy loaded] {mod_name}", flush=True)
            except Exception as e:
                fail+=1; print(f"[Strategy FAILED] {mod_name}: {e}", flush=True)
        print(f"[strategies] loaded={ok} failed={fail} total={len(files)}", flush=True); return names
    except Exception as e:
        inc_error("discover_strategies"); print(f"[strategies] fatal: {e}", flush=True); return []
