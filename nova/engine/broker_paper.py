import json, time, pathlib
from typing import Dict, Any
from .metrics import inc_trade, set_open, set_realized_pnl, set_unrealized_pnl

class PaperBroker:
    def __init__(self, slippage_bps=5, fee_bps=5):
        self.slippage_bps = slippage_bps
        self.fee_bps = fee_bps
        self.state = {
            "equity": 1000.0,
            "positions": {},     # sym -> {"qty": float, "avg": float}
            "realized": 0.0
        }
        pathlib.Path("runtime").mkdir(exist_ok=True)
        # start equity fra fil om finnes
        p = pathlib.Path("runtime/equity.json")
        if p.exists():
            try:
                self.state["equity"] = float((json.loads(p.read_text()) or {}).get("equity", 1000.0))
            except Exception:
                pass

    def _fee(self, notional: float) -> float:
        return abs(notional) * (self.fee_bps/10000.0)

    def execute(self, symbol: str, side: str, qty: float, price: float):
        """Enkel market-paper fill med avg.price-posisjon og realisert PnL, samt logging/metrics."""
        qty = float(qty)
        price = float(price)
        if price <= 0 or qty <= 0:
            return

        # slippage
        slip = price * (self.slippage_bps/10000.0)
        px = price + slip if side == "buy" else price - slip
        notional = qty * px
        fee = self._fee(notional)

        pos = self.state["positions"].get(symbol, {"qty": 0.0, "avg": 0.0})
        realized = 0.0

        if side == "buy":
            new_qty = pos["qty"] + qty
            if new_qty <= 0:
                pos = {"qty": 0.0, "avg": 0.0}
            else:
                pos["avg"] = (pos["avg"]*pos["qty"] + px*qty)/new_qty
                pos["qty"] = new_qty
        else:  # sell
            sell_qty = min(qty, max(pos["qty"], 0.0))
            if sell_qty > 0:
                realized += (px - pos["avg"]) * sell_qty
                pos["qty"] -= sell_qty
                if pos["qty"] <= 1e-12:
                    pos = {"qty": 0.0, "avg": 0.0}

        self.state["positions"][symbol] = pos
        self.state["realized"] += realized - fee
        self.state["equity"] += realized - fee

        # persist equity
        try:
            pathlib.Path("runtime").mkdir(exist_ok=True)
            pathlib.Path("runtime/equity.json").write_text(json.dumps({"equity": self.state["equity"]}))
        except Exception:
            pass

        # metrics
        try:
            inc_trade(side)
            set_open(len([s for s,v in self.state["positions"].items() if abs(v.get("qty",0.0)) > 0]))
            set_realized_pnl(self.state["realized"])
            set_unrealized_pnl(self.unrealized_pnl())
        except Exception:
            pass

        # logg
        try:
            with open("runtime/trades.jsonl","a") as f:
                f.write(json.dumps({
                    "ts": time.time(),
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "price": px,
                    "fee": fee,
                    "realized": realized
                })+"\n")
        except Exception:
            pass

    def unrealized_pnl(self) -> float:
        # enkel placeholder (0) – kan utvides med prishenting
        return 0.0
