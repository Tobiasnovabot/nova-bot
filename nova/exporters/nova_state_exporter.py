#!/usr/bin/env python3
import json, sys
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from prometheus_client import Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST

STATE=Path("state.json"); EQUITY=Path("equity.json"); TRADES=Path("trades.json")
MEM_DIR=Path("data/memory"); WATCH=Path("data/watchlist.json")

reg=CollectorRegistry()
g_equity = Gauge("novax_equity_usdt","Equity i USDT", registry=reg)
g_pnl_total = Gauge("novax_pnl_total","Akkumulert PnL", registry=reg)
g_pos_open = Gauge("novax_positions_open","Antall åpne posisjoner", registry=reg)
g_trades_total = Gauge("novax_trades_total","Totalt antall trades", registry=reg)
g_exposure = Gauge("novax_exposure_frac","Andel kapital investert", registry=reg)
g_heartbeat = Gauge("novax_engine_heartbeat","Heartbeat teller", registry=reg)
g_balance = Gauge("novax_balance","Balanse per asset", ["asset"], registry=reg)
g_pos_symbol = Gauge("novax_pos_qty","Åpen posisjon qty", ["symbol"], registry=reg)
g_edge_symbol = Gauge("novax_symbol_edge","Lærings-edge per symbol", ["symbol"], registry=reg)
g_bandit_alpha = Gauge("novax_bandit_alpha","Bandit alpha", ["arm"], registry=reg)
g_bandit_beta  = Gauge("novax_bandit_beta","Bandit beta", ["arm"], registry=reg)
g_bandit_w     = Gauge("novax_bandit_weight","Bandit weight (global mean)", ["arm"], registry=reg)
g_strat_vote   = Gauge("novax_strat_vote","Siste stemmescore per strategi", ["arm"], registry=reg)
g_uni_symbol = Gauge("novax_universe_member","Univers-medlem=1", ["symbol"], registry=reg)
g_uni_size = Gauge("novax_universe_size","Antall symbols i univers", registry=reg)

def _rj(p, d): 
    try: return json.loads(Path(p).read_text())
    except: return d

def collect_safe():
    import json
    from nova.engine import bandit
    import math
    try:
        st=_rj(STATE, {"positions":{}, "balance":{"USDT":0}})
        eq=_rj(EQUITY, [])
        tr=_rj(TRADES, [])
        last_eq = (eq[-1] if isinstance(eq,list) and eq else {"equity_usdt": float(st.get("balance",{}).get("USDT",0)), "pnl_total":0.0})
        g_equity.set(float(last_eq["equity_usdt"]))
        g_pnl_total.set(float(last_eq.get("pnl_total",0.0)))
        g_pos_open.set(sum(1 for v in st.get("positions",{}).values() if v.get("status")=="open"))
        g_trades_total.set(len(tr))
        # exposure
        # extras_pyr
        try:
            import json, os
            st=json.loads(open("state.json").read()) if os.path.exists("state.json") else {}
            layers=0; trails=0
            for v in (st.get("positions") or {}).values():
                layers += int(v.get("layers",0))
                if float(v.get("trail",0))>0: trails+=1
            g_pyr.set(layers); g_trails.set(trails)
        except Exception:
            pass
        # exposure = sum(open_value)/equity
        q='USDT'
        eq=float(st.get('balance',{}).get(q,0))
        invested=0.0
        for ssym,p in (st.get('positions') or {}).items():
            if p.get('status')=='open': invested += float(p.get('qty',0))*float(p.get('entry',0))
        eq=max(eq, invested)
        frac = invested/max(eq,1e-9)
        g_exposure.set(frac)
        for a,v in (st.get("balance") or {}).items():
            if isinstance(v,(int,float)): g_balance.labels(asset=a).set(float(v))
        for s,p in (st.get("positions") or {}).items():
            if p.get("status")=="open": g_pos_symbol.labels(symbol=s).set(float(p.get("qty",0.0)))
        if MEM_DIR.exists():
            for mp in MEM_DIR.glob("*.json"):
                try:
                    d=json.loads(mp.read_text()); sym=mp.stem.replace("_","/")
                    g_edge_symbol.labels(symbol=sym).set(float(d.get("edge",0.0)))
                except: pass
        # bandit global
        # ensure defaults
        for arm in ['ema','rsi','bo','macd','bb','mr','vwap','kc']:
            g_bandit_alpha.labels(arm=arm).set(1.0)
            g_bandit_beta.labels(arm=arm).set(1.0)
            g_bandit_w.labels(arm=arm).set(1.0)
        try:
            snap = bandit.snapshot_global()
            for arm,(a,b) in snap.items():
                g_bandit_alpha.labels(arm=arm).set(float(a))
                g_bandit_beta.labels(arm=arm).set(float(b))
                w = 0.5 + (float(a)/(float(a)+float(b)))
                g_bandit_w.labels(arm=arm).set(w)
        except Exception:
            pass
        # strat votes
        try:
            import json, os
            sv=json.loads(open("data/strat_votes.json").read()) if os.path.exists("data/strat_votes.json") else {"votes":{}}
            for arm,val in (sv.get("votes") or {}).items():
                g_strat_vote.labels(arm=arm).set(float(val))
        except Exception:
            pass
                # strat votes (robust)
        try:
            import json, os
            sv = {}
            if os.path.exists("data/strat_votes.json"):
                sv=json.loads(open("data/strat_votes.json").read())
            votes = sv.get("votes", sv) if isinstance(sv, dict) else {}
            if isinstance(votes, dict):
                for arm,val in votes.items():
                    try: g_strat_vote.labels(arm=str(arm)).set(float(val))
                    except Exception: pass
        except Exception:
            pass
# universe
        uni=_rj(WATCH, {}).get("chosen", [])
        g_uni_size.set(len(uni))
        for item in uni:
            sym = item["symbol"] if isinstance(item, dict) else str(item)
            g_uni_symbol.labels(symbol=sym).set(1)
        g_heartbeat.inc()
    except Exception:
        g_heartbeat.inc()

class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): sys.stdout.write("exporter: "+(fmt%args)+"\n")
    def do_GET(self):
        if self.path!="/metrics": self.send_response(404); self.end_headers(); return
        collect_safe(); out=generate_latest(reg)
        self.send_response(200); self.send_header("Content-Type", CONTENT_TYPE_LATEST)
        self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)

if __name__=="__main__":
    srv=ThreadingHTTPServer(("0.0.0.0",9108), H)
    print("nova_state_exporter listening on :9108", flush=True); srv.serve_forever()
