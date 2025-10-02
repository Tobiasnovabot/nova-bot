import os, json, time, pathlib, math, argparse
import ccxt
from .metrics import trade as m_trade

DUST = 1e-12

class BinanceLiveBroker:
    def __init__(self, quote: str = "USDC"):
        self.quote = quote.upper()
        self.ex = ccxt.binance({
            "apiKey": os.getenv("BINANCE_KEY", ""),
            "secret": os.getenv("BINANCE_SECRET", ""),
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
            "timeout": 10000,
        })
        # Spot-markeder
        self.ex.load_markets()
        pathlib.Path("runtime").mkdir(exist_ok=True)

        # State som ultra_runner forventer
        self.state = {
            "equity": 0.0,      # settes av ultra_runner
            "positions": {},    # {"ETH/USDC": base_qty, ...}
        }
        # Sync posisjoner ved oppstart
        try:
            self.sync_positions()
        except Exception:
            pass

    # ---------- utils ----------
    def _sym(self, s: str) -> str:
        # "binance:ETH/USDC" -> "ETH/USDC"
        return s.split(":", 1)[-1]

    def _filters(self, sym_spot: str) -> dict:
        m = self.ex.market(sym_spot)
        filters_list = m.get("info", {}).get("filters", []) or []
        filters = {f.get("filterType"): f for f in filters_list if isinstance(f, dict)}
        lot = filters.get("LOT_SIZE", {}) or {}
        notional = (filters.get("NOTIONAL") or filters.get("MIN_NOTIONAL") or {}) or {}
        step = float(lot.get("stepSize", "0.000001") or "0.000001")
        min_qty = float(lot.get("minQty", "0") or "0")
        min_notional = float(notional.get("minNotional", "5") or "5")
        return {"step": step, "min_qty": min_qty, "min_notional": min_notional}

    def _floor_to_step(self, qty: float, step: float) -> float:
        if step <= 0:
            return float(qty)
        return float(math.floor(float(qty) / step) * step)

    # ---------- data ----------
    def last_price(self, symbol: str) -> float:
        t = self.ex.fetch_ticker(self._sym(symbol))
        return float(t.get("last") or t.get("close") or 0.0)

    def fetch_equity_quote(self) -> float:
        """Kun fri saldo i quote – sanity, ikke total equity."""
        try:
            bal = self.ex.fetch_balance()
            b = bal.get(self.quote, {}) or {}
            return float(b.get("free") or 0.0)
        except Exception as e:
            print("[broker_live] equity fetch error:", e, flush=True)
            return 0.0

    def holdings(self) -> dict:
        """Ikke-nulle beholdninger (free+used/locked) pr valuta."""
        bal = self.ex.fetch_balance()
        out = {}
        for ccy, row in (bal or {}).items():
            if not isinstance(row, dict):
                continue
            free = float(row.get("free") or 0.0)
            used = float(row.get("used") or row.get("locked") or 0.0)
            tot = free + used
            if tot > DUST:
                out[ccy.upper()] = {"free": free, "locked": used, "total": tot}
        return out

    def _px_quote(self, base: str) -> float:
        """Pris for BASE i valgt quote. Fallback via USDT hvis trengs."""
        base = base.upper()
        quote = self.quote
        if base == quote:
            return 1.0
        # Direkte BASE/QUOTE
        try:
            return float(self.ex.fetch_ticker(f"{base}/{quote}")["last"])
        except Exception:
            pass
        # Fallback via USDT
        try:
            px_base_usdt = float(self.ex.fetch_ticker(f"{base}/USDT")["last"])
            if quote == "USDT":
                return px_base_usdt
            px_usdt_quote = float(self.ex.fetch_ticker(f"USDT/{quote}")["last"])
            return px_base_usdt * px_usdt_quote
        except Exception:
            return 0.0

    def total_equity_quote(self) -> float:
        """Total porteføljeverdi (free+locked) i self.quote, mark-to-market."""
        bals = self.holdings()
        eq = 0.0
        for ccy, r in bals.items():
            px = self._px_quote(ccy)
            if px > 0:
                eq += r["total"] * px
        return eq

    def positions_summary(self, top: int = 10) -> list[str]:
        """Kompakt liste for logger."""
        bals = self.holdings()
        rows = []
        for ccy, r in bals.items():
            if ccy == self.quote:
                continue
            px = self._px_quote(ccy)
            val = r["total"] * px
            if val > 0:
                rows.append((val, f"{ccy}:{r['total']:.8f}@{px:.6g}≈{val:.2f} {self.quote}"))
        rows.sort(reverse=True)
        return [x[1] for x in rows[:top]]

    def count_open_positions(self) -> int:
        """Antall aktive coins (≠ quote) med > DUST og gyldig BASE/QUOTE-marked."""
        bals = self.holdings()
        n = 0
        for ccy, r in bals.items():
            if ccy == self.quote:
                continue
            if r["total"] <= DUST:
                continue
            sym = f"{ccy}/{self.quote}"
            if sym in self.ex.markets:
                n += 1
        return n

    def sync_positions(self):
        """Bygg state['positions'] ut fra live balanse (kun non-quote)."""
        bals = self.holdings()
        pos = {}
        for ccy, r in bals.items():
            if ccy == self.quote:
                continue
            sym = f"{ccy}/{self.quote}"
            if sym in self.ex.markets and r["total"] > DUST:
                pos[sym] = r["total"]
        self.state["positions"] = pos

    # ---------- sizing helpers ----------
    def qty_for_notional(self, symbol: str, price: float, desired_notional: float) -> float:
        """
        Returnerer gyldig qty (stepSize-justert) som tilfredsstiller minNotional/minQty.
        Returnerer 0.0 hvis ikke mulig.
        """
        sym_spot = self._sym(symbol)
        f = self._filters(sym_spot)
        price = float(price or 0.0)
        if price <= 0:
            return 0.0

        target_notional = max(float(desired_notional), f["min_notional"])
        raw_qty = target_notional / price
        qty = self._floor_to_step(raw_qty, f["step"])
        if qty < f["min_qty"]:
            qty = self._floor_to_step(f["min_qty"] + f["step"], f["step"])

        # bump stegvis til notional-kravet oppfylles (sikkerhetsgrense)
        if qty * price < f["min_notional"]:
            for _ in range(1000):
                qty = self._floor_to_step(qty + f["step"], f["step"])
                if qty * price >= f["min_notional"] and qty >= f["min_qty"]:
                    break

        return qty if (qty > 0 and qty * price >= f["min_notional"] and qty >= f["min_qty"]) else 0.0

    # ---------- trading ----------
    def execute(self, symbol: str, side: str, qty: float, price_hint: float | None = None):
        sym_spot = self._sym(symbol)
        side = side.lower().strip()
        if side not in ("buy", "sell"):
            raise ValueError(f"Invalid side: {side}")

        price = float(price_hint or self.last_price(symbol) or 0.0)
        if price <= 0:
            raise RuntimeError(f"Price unavailable for {sym_spot}")

        f = self._filters(sym_spot)
        qty = self._floor_to_step(float(qty), f["step"])

        # Sørg for at minNotional oppfylles
        if qty * price < f["min_notional"]:
            qty = self.qty_for_notional(symbol, price, f["min_notional"])

        if qty <= 0:
            raise RuntimeError(f"Qty too small for {sym_spot} (minNotional={f['min_notional']})")

        # Enkel balanse-sjekk (quote for buy, base for sell)
        bal = self.ex.fetch_balance()
        base, _quote_ccy = sym_spot.split("/")
        if side == "buy":
            free_quote = float((bal.get(self.quote) or {}).get("free") or 0.0)
            need_quote = qty * price * 1.001  # buffer for fee
            if free_quote + 1e-9 < need_quote:
                raise RuntimeError(f"Insufficient {self.quote}: have {free_quote:.6f}, need {need_quote:.6f}")
        else:
            free_base = float((bal.get(base) or {}).get("free") or 0.0)
            if free_base + 1e-12 < qty:
                raise RuntimeError(f"Insufficient {base}: have {free_base:.8f}, need {qty:.8f}")

        try:
            order = self.ex.create_order(sym_spot, "market", side, qty)
            print(f"[broker_live] executed {side} {qty} {sym_spot}", flush=True)

            # Oppdater enkel posisjons-state
            if side == "buy":
                self.state["positions"][sym_spot] = self.state["positions"].get(sym_spot, 0.0) + float(qty)
            else:
                self.state["positions"][sym_spot] = max(
                    0.0, self.state["positions"].get(sym_spot, 0.0) - float(qty)
                )

            # metrics + logg
            m_trade(side)
            rec = {
                "ts": time.time(),
                "live": True,
                "exchange": "binance",
                "symbol": sym_spot,
                "side": side,
                "qty": float(qty),
                "order": order,
            }
            with open("runtime/trades.jsonl", "a") as f:
                f.write(json.dumps(rec) + "\n")

            return order

        except Exception as e:
            print(f"[broker_live] execute error {sym_spot} {side}: {e}", flush=True)
            raise

    # ---------- flatten / emergency stop ----------
    def flatten_all(self, max_symbols: int = 500) -> list[dict]:
        """
        Selg ALT av non-quote beholdning til quote med MARKET-ordre.
        Returnerer liste av ordre-responser.
        """
        bals = self.holdings()
        orders = []
        for ccy, r in list(bals.items())[:max_symbols]:
            if ccy == self.quote or r["total"] <= DUST:
                continue
            sym = f"{ccy}/{self.quote}"
            if sym not in self.ex.markets:
                continue
            # selg kun det som er "free" (unngå locked)
            free_base = float(r["free"])
            if free_base <= DUST:
                continue
            f = self._filters(sym)
            qty = self._floor_to_step(free_base, f["step"])
            if qty <= 0:
                continue
            # sjekk minNotional via pris
            px = self._px_quote(ccy)
            if px <= 0:
                continue
            if qty * px < f["min_notional"]:
                # forsøk bump ett steg
                qty2 = self._floor_to_step(qty + f["step"], f["step"])
                if qty2 * px >= f["min_notional"]:
                    qty = qty2
                else:
                    continue
            try:
                od = self.execute(sym, "sell", qty, px)
                orders.append(od)
            except Exception as e:
                print(f"[broker_live] flatten error {sym}: {e}", flush=True)
        # refresh state
        try:
            self.sync_positions()
        except Exception:
            pass
        return orders


# CLI: brukbar for "stop" (flatten)
def _cli():
    parser = argparse.ArgumentParser(description="Binance live broker helpers")
    sub = parser.add_subparsers(dest="cmd")

    p_flat = sub.add_parser("flatten", help="Sell all non-quote holdings to quote")
    p_flat.add_argument("--quote", default=os.getenv("QUOTE", "USDC"), help="Quote currency (default from QUOTE env)")

    p_eq = sub.add_parser("equity", help="Print total equity in quote")
    p_eq.add_argument("--quote", default=os.getenv("QUOTE", "USDC"))

    p_pos = sub.add_parser("positions", help="Print positions summary")
    p_pos.add_argument("--quote", default=os.getenv("QUOTE", "USDC"))
    p_pos.add_argument("--top", type=int, default=20)

    args = parser.parse_args()
    quote = args.quote

    br = BinanceLiveBroker(quote=quote)
    if args.cmd == "flatten":
        out = br.flatten_all()
        print(json.dumps({"flattened": len(out)}, default=str))
    elif args.cmd == "equity":
        print(f"{br.total_equity_quote():.6f}")
    elif args.cmd == "positions":
        print(", ".join(br.positions_summary(args.top)))
    else:
        parser.print_help()

if __name__ == "__main__":
    _cli()
