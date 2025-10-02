#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
import time
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Tuple

# ---------- Redundant data feed (primær + fallback) ----------

class RedundantFeed:
    """
    Wrapper for to datakilder. get(sym, i) prøver primary, faller til fallback.
    Statistikk i .stats: {'primary_ok':int, 'fallback_used':int, 'errors':int}
    """
    def __init__(self, primary: Callable[[str, int], Tuple[Any, Any]],
                 fallback: Callable[[str, int], Tuple[Any, Any]]):
        self.primary = primary
        self.fallback = fallback
        self.stats = {"primary_ok": 0, "fallback_used": 0, "errors": 0}

    def get(self, symbol: str, upto_i: int) -> Tuple[Any, Any]:
        try:
            out = self.primary(symbol, upto_i)
            self.stats["primary_ok"] += 1
            return out
        except Exception:
            try:
                out = self.fallback(symbol, upto_i)
                self.stats["fallback_used"] += 1
                return out
            except Exception:
                self.stats["errors"] += 1
                raise

# ---------- Venue failover per symbol ----------

class FailoverRouter:
    """
    Enkelt failoverkart per symbol: venues = ['binance','okx'].
    mark_down(venue) → rutes bort til annen venue inntil mark_up().
    """
    def __init__(self, symbols: Iterable[str], venues: Iterable[str]):
        self.symbols = list(symbols)
        self.venues = list(venues)
        self.down: Dict[str, bool] = {v: False for v in self.venues}
        # preferanse-rekkefølge per symbol (kan utvides senere)
        self.pref: Dict[str, List[str]] = {s: list(self.venues) for s in self.symbols}

    def mark_down(self, venue: str): self.down[str(venue)] = True
    def mark_up(self, venue: str): self.down[str(venue)] = False

    def pick(self, symbol: str) -> Optional[str]:
        for v in self.pref.get(symbol, self.venues):
            if not self.down.get(v, False):
                return v
        return None  # alt nede

# ---------- Latency SLO (signal→ordre→fill) ----------

class LatencySLO:
    """
    Overvåker latency mot budsjett i millisekunder.
    use: with slo.timer() as done: ...; dt_ms = done()
    """
    def __init__(self, budget_ms: float):
        self.budget_ms = float(budget_ms)
        self.breaches = 0
        self.samples = 0
        self.last_ms: Optional[float] = None

    def timer(self):
        t0 = time.perf_counter()
        def _done() -> float:
            dt = (time.perf_counter() - t0) * 1000.0
            self.samples += 1
            self.last_ms = dt
            if dt > self.budget_ms:
                self.breaches += 1
            return dt
        return _TimerCtx(_done)

    def ok(self) -> bool:
        return self.breaches == 0

class _TimerCtx:
    def __init__(self, fin: Callable[[], float]): self._fin = fin
    def __enter__(self): return self._fin
    def __exit__(self, exc_type, exc, tb): self._fin()

# ---------- Replay-harness ----------

class ReplayHarness:
    """
    Replayer en sekvens av (symbol, candle_dict, book_dict).
    iterate(upto=None) -> iterator over elementene i rekkefølge.
    """
    def __init__(self, events: List[Tuple[str, Dict[str, Any], Dict[str, Any]]]):
        self.events = list(events)

    def iterate(self, upto: Optional[int] = None) -> Iterator[Tuple[str, Dict[str, Any], Dict[str, Any]]]:
        k = len(self.events) if upto is None else min(upto, len(self.events))
        for i in range(k):
            yield self.events[i]

# ---------- Simulert børs for tester ----------

class SimExchange:
    """
    Enkel spot-simulator. Setter quote via set_quote(bid, ask).
    market_buy(qty) fyller på ask; market_sell(qty) på bid.
    Holder posisjon og cash for PnL.
    """
    def __init__(self, cash_usdt: float = 10_000.0):
        self.cash = float(cash_usdt)
        self.qty = 0.0
        self.avg = 0.0
        self.bid = 0.0
        self.ask = 0.0
        self.trades: List[Dict[str, Any]] = []

    def set_quote(self, bid: float, ask: float):
        self.bid = float(bid); self.ask = float(ask)

    def equity(self, last: Optional[float] = None) -> float:
        px = float(last if last is not None else (self.bid + self.ask)/2.0 if self.bid and self.ask else 0.0)
        return self.cash + self.qty * px

    def market_buy(self, qty: float):
        if qty <= 0 or self.ask <= 0: return None
        cost = qty * self.ask
        self.cash -= cost
        self.avg = (self.avg * self.qty + cost) / (self.qty + qty) if (self.qty + qty) > 0 else 0.0
        self.qty += qty
        t = {"side":"buy","qty":qty,"price":self.ask,"ts":time.time()}
        self.trades.append(t)
        return t

    def market_sell(self, qty: float):
        if qty <= 0 or self.bid <= 0: return None
        qty = min(qty, self.qty)
        proceeds = qty * self.bid
        self.cash += proceeds
        self.qty -= qty
        t = {"side":"sell","qty":qty,"price":self.bid,"ts":time.time()}
        self.trades.append(t)
        return t