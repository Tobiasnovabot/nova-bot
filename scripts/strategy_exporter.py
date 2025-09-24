#!/usr/bin/env python3
import os, json, glob
from http.server import HTTPServer, BaseHTTPRequestHandler
from prometheus_client import CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST, Gauge

BASE="/home/nova/nova-bot"
DATA=os.path.join(BASE,"data")
ARCH=os.path.join(BASE,"archives")
STATS_OUT=os.path.join(DATA,"strategy_stats.json")

reg=CollectorRegistry()
STRAT_PNL = Gauge("novax_strategy_pnl_total","Cumulative PnL by strategy", ["strategy"], registry=reg)
WIN_G     = Gauge("novax_trades_win_total_gauge","Wins (gauge mirror)",     ["strategy"], registry=reg)
LOSS_G    = Gauge("novax_trades_loss_total_gauge","Losses (gauge mirror)",  ["strategy"], registry=reg)

def iter_trades_from_blob(blob):
    # Tillat format:
    # 1) {"trades": [ {...}, {...} ]}
    # 2) [ {...}, {...} ]
    if isinstance(blob, dict) and isinstance(blob.get("trades"), list):
        for t in blob["trades"]:
            if isinstance(t, dict): yield t
    elif isinstance(blob, list):
        for t in blob:
            if isinstance(t, dict): yield t

def load_all_trades():
    files=[os.path.join(DATA,"trades.json")] + sorted(glob.glob(os.path.join(ARCH,"trades_*.json")))
    for fp in files:
        try:
            with open(fp) as f:
                blob=json.load(f)
            for t in iter_trades_from_blob(blob):
                yield t
        except Exception:
            continue

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_response(404); self.end_headers(); return

        wins, losses, pnls = {}, {}, {}
        for t in load_all_trades():
            s=str(t.get("strategy","unknown"))
            p=float(t.get("pnl",0.0))
            pnls[s]=pnls.get(s,0.0)+p
            if p>0: wins[s]=wins.get(s,0)+1
            elif p<0: losses[s]=losses.get(s,0)+1

        # Skriv stats-fil for andre prosesser
        try:
            with open(STATS_OUT,"w") as f:
                all_keys=set().union(wins.keys(), losses.keys(), pnls.keys())
                json.dump({s:{"wins":wins.get(s,0),"losses":losses.get(s,0),"total_pnl":pnls.get(s,0.0)} for s in all_keys},
                          f, indent=2)
        except Exception:
            pass

        # Oppdater Prometheus (Gauges gir idempotent scraping)
        for s,v in pnls.items():   STRAT_PNL.labels(strategy=s).set(v)
        for s,c in wins.items():   WIN_G.labels(strategy=s).set(c)
        for s,c in losses.items(): LOSS_G.labels(strategy=s).set(c)

        body=generate_latest(reg)
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPE_LATEST)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def main():
    addr=("127.0.0.1", 9113)
    httpd=HTTPServer(addr, Handler)
    print(f"strategy_exporter: serving http://{addr[0]}:{addr[1]}/metrics")
    httpd.serve_forever()

if __name__=="__main__": main()
