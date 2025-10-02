#!/usr/bin/env python3
import json, os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HOST, PORT = "127.0.0.1", 9108
DATA = Path("data"); PROM = DATA/"metrics.prom"

def safe_json(p, default):
    try:
        t = Path(p).read_text()
        return json.loads(t) if t.strip() else default
    except Exception:
        return default

def render_metrics():
    try:
        if PROM.exists():
            try:
                txt = PROM.read_text()
                if txt.strip():
                    return txt if txt.endswith("\n") else txt + "\n"
            except Exception:
                pass
        state  = safe_json(DATA/"state.json", {})
        equity = safe_json(DATA/"equity.json", {"equity_usd": 10000})
        wl = state.get("watch", []) or []
        lines = []
        def m(name, value, labels=""):
            lines.append(f'{name}{{{labels}}} {value}' if labels else f'{name} {value}')
        m("novax_equity_usd", equity.get("equity_usd", 10000), 'exchange="binance",mode="paper"')
        m("novax_bot_enabled", 1, 'exchange="binance",mode="paper"')
        m("novax_watch_count", len(wl) or int(os.getenv("WATCH_TOP_N", "300")), 'exchange="binance",mode="paper"')
        return "\n".join(lines) + "\n"
    except Exception:
        # Siste skanse: alltid returner minst én linje
        return "novax_exporter_ok 1\n"

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path == "/health":
                body = b"ok\n"
                self.send_response(200)
                self.send_header("Content-Type","text/plain")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers(); self.wfile.write(body); return
            if self.path != "/metrics":
                self.send_response(404); self.end_headers(); return
            body = render_metrics().encode("utf-8", "ignore")
            self.send_response(200)
            self.send_header("Content-Type","text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)
        except Exception:
            # Aldri la klienten få tomt svar
            fallback = b"novax_exporter_ok 0\n"
            try:
                self.send_response(200)
                self.send_header("Content-Type","text/plain")
                self.send_header("Content-Length", str(len(fallback)))
                self.end_headers(); self.wfile.write(fallback)
            except Exception:
                pass
    def log_message(self, *a, **k): pass

if __name__ == "__main__":
    HTTPServer((HOST, PORT), H).serve_forever()
