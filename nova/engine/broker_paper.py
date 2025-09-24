from typing import Dict, Any, Tuple
from .trade_log import append_trade
import os
class PaperBroker:
    def __init__(self, cash: float = 100_000.0, trades_path="/home/nova/nova-bot/trades.json", metrics=None):
        self.symbol="BTCUSDT"; self.pos=0; self.entry=0.0; self.cash=cash
        self.last_price=0.0; self.realized=0.0; self.trades_path=trades_path
        self.m = metrics; self.strategy_label = os.getenv("NOVAX_VOTER","VOTER")
    def _mtm_equity(self, price: float)->float:
        return self.cash + self.realized + ((price-self.entry)*self.pos if self.pos!=0 else 0.0)
    def on_signal(self, bar: Dict[str,Any], side: str)->Tuple[float,float,float]:
        price=float(bar["close"]); self.last_price=price
        if side=="flat" and self.pos!=0: self._close(price)
        elif side=="buy" and self.pos<=0:
            if self.pos==-1: self._close(price)
            self._open(price,+1)
        elif side=="sell" and self.pos>=0:
            if self.pos==+1: self._close(price)
            self._open(price,-1)
        eq=self._mtm_equity(price); pnl= self.realized + ((price-self.entry)*self.pos if self.pos!=0 else 0.0)
        return float(eq), float(pnl), float(abs(self.pos))
    def _open(self, price: float, direction: int):
        if self.pos!=0: return
        self.pos=direction; self.entry=price
        append_trade(self.trades_path, {"type":"open","symbol":self.symbol,"side":"long" if direction>0 else "short","price":price})
    def _close(self, price: float):
        if self.pos==0: return
        pnl=(price-self.entry)*self.pos; self.realized+=pnl
        if self.m:
            lbl=self.strategy_label
            if pnl>0:
                self.m.strategy_trades_total.labels(lbl,"win").inc()
                self.m.strategy_pnl_pos_total.labels(lbl).inc(pnl)
            elif pnl<0:
                self.m.strategy_trades_total.labels(lbl,"loss").inc()
                self.m.strategy_pnl_neg_total.labels(lbl).inc(abs(pnl))
            else:
                self.m.strategy_trades_total.labels(lbl,"flat").inc()
        append_trade(self.trades_path, {"type":"close","symbol":self.symbol,"side":"long" if self.pos>0 else "short","price":price,"pnl":pnl})
        self.pos=0; self.entry=0.0
