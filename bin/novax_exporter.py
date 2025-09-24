#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, time, threading, random
from http.server import BaseHTTPRequestHandler, HTTPServer

# ---- konfig ----
PORT = int(os.getenv("NOVAX_EXPORTER_PORT", "9108"))
EXCHANGE = os.getenv("EXCHANGE", "binance")
MODE = os.getenv("MODE", "paper")

# ---- registry ----
REG = CollectorRegistry()

HB = Counter(
    "novax_engine_heartbeat_total",
    "Engine heartbeat ticks",
    ["exchange", "mode"],
    registry=REG,
)

RG_EVT = Counter(
    "novax_risk_guard_events_total",
    "Risk-guard events",
    ["exchange", "mode", "event"],
    registry=REG,
)

EQ = Gauge(
    "novax_equity_usd",
    "Equity i USD",
    ["exchange", "mode"],
    registry=REG,
)

BOT_ENABLED = Gauge(
    "novax_bot_enabled",
    "1 hvis bot er aktiv",
    ["exchange", "mode"],
    registry=REG,
)

WATCH = Gauge(
    "novax_watch_count",
    "Antall symbols i watchlist",
    ["exchange", "mode"],
    registry=REG,
)

# ---- demo-kilder (bytt til ekte state-lesing ved behov) ----
_equity = 10000.0
_bot_enabled = 1
_watch_n = 300

def _tick():
    global _equity
    while True:
        HB.labels(EXCHANGE, MODE).inc()
        # enkel drift for å synliggjøre endring
        _equity += random.uniform(-2.0, 2.0)
        EQ.labels(EXCHANGE, MODE).set(max(_equity, 0.0))
        BOT_ENABLED.labels(EXCHANGE, MODE).set(_bot_enabled)
        WATCH.labels(EXCHANGE, MODE).set(_watch_n)
        time.sleep(60)

# ---- HTTP handler for /metrics ----
class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_response(404); self.end_headers(); return
        data = generate_latest(REG)
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPE_LATEST)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

def main():
    # Prometheus klient sin egen HTTP-server er fin, men vi gir en enkel handler for kompatibilitet.
    # Start enten client-serveren ELLER vår, ikke begge. Vi kjører vår for kontrollert registry.
    srv = HTTPServer(("0.0.0.0", PORT), MetricsHandler)
    threading.Thread(target=_tick, daemon=True).start()
    print(f"[novax_exporter] listening on :{PORT} exchange={EXCHANGE} mode={MODE}")
    srv.serve_forever()

if __name__ == "__main__":
    main()
