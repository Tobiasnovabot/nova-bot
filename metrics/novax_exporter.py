from __future__ import annotations
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import json, time
STATE=Path("/home/nova/nova-bot/state")
def jload(n, d): 
    p=STATE/f"{n}.json"
    try: return json.loads(p.read_text())
    except: return d
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path!="/metrics":
            self.send_response(404); self.end_headers(); return
        eq=jload("equity", {"equity":0,"pnl_total":0,"equity_high":0})
        pos=jload("positions", {"positions":{},"prices":{},"avg_cost":{}})
        sig=jload("signals", {})
        rt=jload("runtime", {"ts":0,"strategy_count":0})
        stats=jload("strat_stats", {})
        trades=jload("trades", [])
        # risk: gross exposure ratio
        equity=float(eq.get("equity",0.0)) or 1.0
        gross=0.0
        for s,qty in (pos.get("positions") or {}).items():
            px=float((pos.get("prices") or {}).get(s,0.0))
            gross+=abs(float(qty))*px
        gross_ratio=gross/equity
        # drawdown
        eq_hi=float(eq.get("equity_high", equity))
        dd=0.0 if eq_hi<=0 else (eq_hi-equity)/eq_hi
        # metrics
        L=[]
        L.append("novax_up 1")
        L.append(f"novax_runtime_timestamp {rt.get('ts',0)}")
        L.append(f"novax_strategy_count {rt.get('strategy_count',0)}")
        L.append(f"novax_equity_total {equity}")
        L.append(f"novax_pnl_total {float(eq.get('pnl_total',0.0))}")
        L.append(f"novax_trades_total {len(trades)}")
        L.append(f"novax_drawdown {dd}")
        L.append(f"novax_gross_exposure_ratio {gross_ratio}")
        # per symbol
        for s,px in (pos.get("prices") or {}).items():
            qty=float((pos.get("positions") or {}).get(s,0.0))
            L.append(f'novax_last_price{{symbol="{s}"}} {float(px)}')
            L.append(f'novax_position_qty{{symbol="{s}"}} {qty}')
        # signals
        buys=sells=holds=0
        for strat, per in (sig or {}).items():
            for sym,val in per.items():
                iv=int(val)
                buys+= iv>0; sells+= iv<0; holds+= iv==0
                L.append(f'novax_signal{{strategy="{strat}",symbol="{sym}"}} {iv}')
        L.append(f'novax_signal_total{{type="buy"}} {buys}')
        L.append(f'novax_signal_total{{type="sell"}} {sells}')
        L.append(f'novax_signal_total{{type="hold"}} {holds}')
        # strategy stats
        for strat,s in (stats or {}).items():
            pnl=float(s.get("pnl_realized",0.0)); t=int(s.get("trades",0))
            w=int(s.get("wins",0)); l=int(s.get("losses",0)); winrate=0.0 if t==0 else w/t
            ema=float(s.get("ema_pnl",0.0)); var=float(s.get("ema_var",1e-6)); sharpe=0.0 if var<=0 else (ema/(var**0.5))
            L.append(f'novax_strategy_pnl{{strategy="{strat}"}} {pnl}')
            L.append(f'novax_strategy_trades{{strategy="{strat}"}} {t}')
            L.append(f'novax_strategy_wins{{strategy="{strat}"}} {w}')
            L.append(f'novax_strategy_losses{{strategy="{strat}"}} {l}')
            L.append(f'novax_strategy_winrate{{strategy="{strat}"}} {winrate}')
            L.append(f'novax_strategy_sharpe{{strategy="{strat}"}} {sharpe}')
            enabled = jload("strat_enabled", {})
            for strat2,val in (enabled or {}).items():
                L.append(f"novax_strategy_enabled{strategy=\"{strat2}\"} {int(val)}")
        L.append(f"novax_exporter_scrape_ts {time.time()}")
        out="\n".join(L)+"\n"
        self.send_response(200); self.send_header("Content-Type","text/plain; version=0.0.4")
        self.send_header("Content-Length",str(len(out))); self.end_headers(); self.wfile.write(out.encode())
if __name__=="__main__":
    HTTPServer(("127.0.0.1",9112), H).serve_forever()
