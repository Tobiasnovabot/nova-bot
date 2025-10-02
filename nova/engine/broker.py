from __future__ import annotations
from pathlib import Path
import json, time, os, math
from typing import Dict, List, Optional
from .persist import update_on_trade

STATE = Path("/home/nova/nova-bot/state"); STATE.mkdir(parents=True, exist_ok=True)

def _rj(p:Path,d): 
    try: return json.loads(p.read_text())
    except: return d
def _wj(p:Path,o): p.write_text(json.dumps(o,separators=(",",":")))

class PaperBroker:
    def __init__(self, symbols:List[str]):
        self.symbols=symbols
        self.fee_bps=float(os.getenv("FEE_BPS","5"))
        self.slip_bps=float(os.getenv("SLIPPAGE_BPS","5"))
        self.max_alloc=float(os.getenv("MAX_ALLOC","0.25"))
        self.max_gross=float(os.getenv("MAX_GROSS_EXPOSURE","1.0"))  # 1.0 = 100% av likviditet
        self.stop_pct=float(os.getenv("STOP_PCT","0.1"))             # 10% under snittkost
        self.trim_warn=float(os.getenv("DRAWDOWN_TRIM_WARN","0.10"))
        self.trim_crit=float(os.getenv("DRAWDOWN_TRIM_CRIT","0.20"))
        # state
        self.pos=_rj(STATE/"positions.json",
            {"positions": {s:0.0 for s in symbols}, "prices": {s:0.0 for s in symbols}, "avg_cost":{s:0.0 for s in symbols}})
        self.eq=_rj(STATE/"equity.json", {"equity": 100000.0, "pnl_total": 0.0, "equity_high": 100000.0})
        self.trades=_rj(STATE/"trades.json", [])
        self.last_strength: Dict[str,float]={s:0.0 for s in symbols}

    def mark_prices(self, last_prices:Dict[str,float]):
        self.pos["prices"].update({s: float(last_prices[s]) for s in last_prices})

    def _portfolio_value(self)->float:
        v=float(self.eq["equity"])
        for s,qty in self.pos["positions"].items():
            v += float(qty) * float(self.pos["prices"].get(s,0.0))
        return v

    def _gross_exposure(self)->float:
        gross=0.0
        for s,qty in self.pos["positions"].items():
            gross += abs(float(qty))*float(self.pos["prices"].get(s,0.0))
        return gross

    def _alloc_for(self, sym:str, strength:float, dd:float)->float:
        # auto-nedparing ved drawdown
        dd_scale = 1.0
        if dd >= self.trim_crit: dd_scale = 0.25
        elif dd >= self.trim_warn: dd_scale = 0.5
        s=abs(strength)
        base = self.max_alloc * (s*s) * dd_scale
        return max(0.0, min(base, self.max_alloc))

    def _exec(self, sym:str, dqty:float, px:float, who:str, weights:Optional[Dict[str,float]]=None):
        if abs(dqty)<1e-12 or px<=0: return None
        slip = px*(1 + (self.slip_bps/1e4) * (1 if dqty>0 else -1))
        fee = abs(dqty*slip) * (self.fee_bps/1e4)
        self.eq["equity"] -= dqty*slip + fee
        prev_qty = float(self.pos["positions"].get(sym,0.0))
        avg_cost = float(self.pos["avg_cost"].get(sym,0.0))
        new_qty = prev_qty + dqty
        realized_pnl = 0.0
        # realisert PnL når vi reduserer posisjon
        if prev_qty!=0 and (prev_qty>0 and dqty<0 or prev_qty<0 and dqty>0):
            close_qty = -dqty if prev_qty>0 else dqty  # positiv mengde som lukkes
            # kun long støttes i paper nå
            if prev_qty>0:
                realized_pnl = float(close_qty)*(slip - avg_cost) - fee
                update_on_trade(sym, realized_pnl, weights or {})
        # oppdater gj.snitt-kost for long når vi øker posisjon
        if new_qty>0 and dqty>0:
            notional_old = prev_qty*avg_cost
            notional_add = dqty*slip
            self.pos["avg_cost"][sym] = (notional_old + notional_add)/new_qty
        # nullstill avg_cost når posisjonen lukkes
        if new_qty<=1e-12:
            self.pos["avg_cost"][sym]=0.0
            new_qty=0.0
        self.pos["positions"][sym]=float(new_qty)
        tr={"ts": time.time(),"symbol": sym,"qty": dqty,"price": slip,"fee": fee,"who": who,"weights": weights or {}}
        self.trades.append(tr)
        return tr

    def _apply_stops(self):
        for sym in self.symbols:
            qty=float(self.pos["positions"].get(sym,0.0))
            if qty<=0: continue
            px=float(self.pos["prices"].get(sym,0.0)) or 0.0
            ac=float(self.pos["avg_cost"].get(sym,0.0)) or 0.0
            if px>0 and ac>0 and px < ac*(1.0 - self.stop_pct):
                # selg alt
                self._exec(sym, -qty, px, "stop", weights={"stop":1.0})

    def rebalance(self, final:Dict[str,int], strength:Dict[str,float], weights_by_symbol:Dict[str,Dict[str,float]]):
        # priser må være markert
        port_before=self._portfolio_value()
        # per-symbol stops før nye handler
        self._apply_stops()
        # tegnet drawdown og auto-nedparing
        eq_now=self._portfolio_value()
        self.eq["equity_high"]=max(float(self.eq.get("equity_high",eq_now)), eq_now)
        dd = 0.0 if self.eq["equity_high"]<=0 else (self.eq["equity_high"]-eq_now)/self.eq["equity_high"]
        # kalkuler mål allokering og håndhev global gross
        target_notional: Dict[str,float]={}
        for sym in self.symbols:
            px=float(self.pos["prices"].get(sym,0.0)) or 0.0
            sig=int(final.get(sym,0))
            alloc = self._alloc_for(sym, strength.get(sym,0.0), dd) if sig==1 else 0.0
            target_notional[sym] = float(self.eq["equity"]) * alloc if px>0 else 0.0
        # skaler ned hvis mål bryter MAX_GROSS_EXPOSURE
        gross_target = sum(target_notional.values())
        gross_cap = float(self.eq["equity"]) * self.max_gross
        scale = 1.0 if gross_target<=gross_cap or gross_target<=0 else gross_cap/gross_target
        for sym in target_notional:
            target_notional[sym]*=scale
        # utfør handler
        for sym in self.symbols:
            px=float(self.pos["prices"].get(sym,0.0)) or 0.0
            if px<=0: continue
            cur=float(self.pos["positions"].get(sym,0.0))
            tgt_qty = target_notional[sym]/px
            d=tgt_qty - cur
            if cur + d < 0: d = -cur
            w = weights_by_symbol.get(sym,{})
            self._exec(sym, d, px, "rebalance", weights=w)
            self.last_strength[sym]=strength.get(sym,0.0)
        port_after=self._portfolio_value()
        self.eq["equity_high"]=max(float(self.eq.get("equity_high", port_after)), port_after)
        self.eq["pnl_total"]=port_after - 100000.0
        _wj(STATE/"positions.json", self.pos)
        _wj(STATE/"equity.json", self.eq)
        _wj(STATE/"trades.json", self.trades)
        ret = 0.0 if port_before<=0 else (port_after-port_before)/port_before
        return port_after, ret, dd
