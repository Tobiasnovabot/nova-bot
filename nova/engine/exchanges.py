import os
import ccxt
from typing import Dict, Any, List

def _get_env(*names: str) -> str:
    for n in names:
        v = os.getenv(n)
        if v: return v
    return ""

def make_clients(names: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for name in names:
        n = name.strip().lower()
        if not n or n not in ccxt.exchanges:
            continue
        klass = getattr(ccxt, n)
        kw: Dict[str, Any] = {}

        if n == "binance":
            kw = {
                "apiKey": _get_env("BINANCE_APIKEY", "BINANCE_KEY"),
                "secret": _get_env("BINANCE_SECRET"),
                "options": {"defaultType": "spot"},
            }
        elif n == "okx":
            kw = {
                "apiKey": _get_env("OKX_APIKEY", "OKX_KEY"),
                "secret": _get_env("OKX_SECRET"),
                "password": _get_env("OKX_PASSPHRASE", "OKX_PASSWORD"),
            }

        c = klass(kw)
        c.enableRateLimit = True
        c.timeout = 20000

        # Valgfri privat-sjekk (logger, men stopper ikke)
        try:
            if c.has.get("fetchBalance"):
                c.fetch_balance()
        except Exception as e:
            print(f"[keys] {n}: invalid or blocked ({e})", flush=True)

        out[n] = c
    return out

def _f(x, d=0.0):
    try:
        return float(x)
    except Exception:
        return d

def load_universe(clients: Dict[str, Any], quote: str = "USDT", top_n: int = 120, min_vol_usd: float = 20000) -> List[str]:
    universe: List[str] = []
    for ex in clients.keys():
        try:
            pub = getattr(ccxt, ex)({})
            pub.enableRateLimit = True
            pub.timeout = 10000

            markets = pub.load_markets()
            spot = [
                m["symbol"]
                for m in markets.values()
                if m.get("active") and m.get("spot") and m["symbol"].endswith("/" + quote)
            ]
            print(f"[universe] {ex}: spot_syms={len(spot)}", flush=True)

            try:
                tickers = pub.fetch_tickers(spot)
                print(f"[universe] {ex}: bulk tickers={len(tickers)}", flush=True)
            except Exception as e:
                print(f"[universe] {ex}: fetch_tickers failed: {e}", flush=True)
                tickers = {}

            rows = []
            for sym in spot:
                info = markets.get(sym, {}).get("info", {})
                vol = _f(info.get("quoteVolume", 0) or info.get("vol24h", 0) or 0)
                if vol <= 0 and sym in tickers:
                    t = tickers.get(sym, {})
                    vol = _f(t.get("quoteVolume", 0) or 0)
                if vol <= 0:
                    try:
                        t1 = pub.fetch_ticker(sym)
                        last = _f(t1.get("last") or t1.get("close") or 0)
                        basevol = _f(t1.get("baseVolume", 0))
                        vol = last * basevol
                    except Exception:
                        vol = 0.0
                if vol > 0:
                    rows.append((vol, f"{ex}:{sym}"))

            rows.sort(reverse=True)
            for vol, s in rows[:top_n]:
                if vol >= min_vol_usd:
                    universe.append(s)
        except Exception as e:
            print(f"[universe] {ex}: ERROR {e}", flush=True)
    return universe
