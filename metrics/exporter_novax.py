#!/usr/bin/env python3
import os
import os, json, time, pathlib
from http.server import BaseHTTPRequestHandler, HTTPServer

DATA = pathlib.Path(os.getenv("NOVA_HOME", "/home/nova/nova-bot/data"))
EQ  = DATA / "equity.json"
ST  = DATA / "state.json"
TR  = DATA / "trades.json"

def _jload(p, default):
    try:
        return json.loads(p.read_text() or json.dumps(default))
    except Exception:
        return default

def scrape():
    eq  = _jload(EQ, [])
    st  = _jload(ST, {})
    tr  = _jload(TR, [])

    equity = (eq[-1].get("equity_usd") if eq and isinstance(eq[-1], dict) else
              st.get("equity_usd", 0.0))
    mode   = st.get("mode","paper")
    exch   = os.getenv("EXCHANGE","binance")
    watch  = st.get("watch", [])
    uni    = st.get("universe_cache",{}).get("symbols", [])
    hb_ts  = st.get("last_tick_ts", 0)
    bot_on = 1 if st.get("bot_enabled", False) else 0
    pos_n  = len(st.get("positions", {}))
    tr_n   = len(tr)
    pnl_last = 0.0
    if tr and isinstance(tr[-1], dict):
        pnl_last = float(tr[-1].get("pnl", 0) or 0)

    # Prometheus exposition
    lines = []
    def s(k, v, help="", typ="gauge", labels=None):
        if help:
            lines.append(f"# HELP {k} {help}")
        if typ:
            lines.append(f"# TYPE {k} {typ}")
        lab = labels or {}
        if lab:
            kv = ",".join(f'{kk}="{vv}"' for kk,vv in lab.items())
            lines.append(f"{k}{{{kv}}} {v}")
        else:
            lines.append(f"{k} {v}")

    base = {"exchange":exch, "mode":mode}
    now = int(time.time())

    s("novax_equity_usd", equity, "Account equity in USD", labels=base)
    s("novax_bot_enabled", bot_on, "Bot enabled flag (1/0)", labels=base)
    s("novax_positions_open", pos_n, "Open positions count", labels=base)
    s("novax_watch_count", len(watch) if watch else len(uni), "Symbols watched", labels=base)
    s("novax_trades_total", tr_n, "Total trades recorded", labels=base)
    s("novax_last_trade_pnl", pnl_last, "PNL of last trade", labels=base)
    s("novax_engine_heartbeat_ts", hb_ts, "Last engine tick timestamp (s)", labels=base)
    s("novax_exporter_ts", now, "Exporter timestamp (s)", labels=base)

    return "\n".join(lines) + "\n"

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_response(404); self.end_headers(); return
        body = scrape().encode()
        self.send_response(200)
        self.send_header("Content-Type","text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def main():
    port = int(os.getenv("NOVAX_METRICS_PORT","9108"))
    srv = HTTPServer(("127.0.0.1", port), H)
    srv.serve_forever()

if __name__ == "__main__":
    main()