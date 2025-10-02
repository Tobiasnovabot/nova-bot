# nova/engine/broker_live.py
import os, json, time, pathlib
import ccxt
from .metrics import trade as m_trade

class BinanceLiveBroker:
    def __init__(self, quote: str = "USDC"):
        self.quote = quote
        self.ex = ccxt.binance({
            "apiKey": os.getenv("BINANCE_KEY", ""),
            "secret": os.getenv("BINANCE_SECRET", ""),
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
            "timeout": 10000,
        })
        # <- Viktig: ingen param her!
        self.ex.load_markets()
        pathlib.Path("runtime").mkdir(exist_ok=True)

    def _sym(self, s: str) -> str:
        # "binance:ETH/USDC" -> "ETH/USDC"
        return s.split(":", 1)[-1]

    def last_price(self, symbol: str) -> float:
        t = self.ex.fetch_ticker(self._sym(symbol))
        return float(t.get("last") or t.get("close") or 0.0)

    def fetch_equity_quote(self) -> float:
        bal = self.ex.fetch_balance()
        b = bal.get(self.quote, {}) or {}
        return float(b.get("free") or 0.0)

    def _amt_prec(self, mkt: dict, amount: float) -> float:
        return float(self.ex.amount_to_precision(mkt["symbol"], amount))

    def execute(self, symbol: str, side: str, qty: float, price_hint: float | None = None):
        sym = self._sym(symbol)
        mkt = self.ex.market(sym)
        amt = self._amt_prec(mkt, qty)
        order = self.ex.create_order(sym, "market", side, amt)
        # metrics + enkel logg
        m_trade(side)
        rec = {
            "ts": time.time(),
            "live": True,
            "exchange": "binance",
            "symbol": sym,
            "side": side,
            "qty": amt,
            "order": order,
        }
        with open("runtime/trades.jsonl", "a") as f:
            f.write(json.dumps(rec) + "\n")
        return order
