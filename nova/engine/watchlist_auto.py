from __future__ import annotations
import os

def resolve_watchlist(ex, env_watchlist: str | None, top_n: int = 300):
    """
    Støtter:
      - Komma-separert liste 'BTC/USDT,ETH/USDT'
      - 'AUTO_USDT' -> henter topp /USDT-markeder (volum-basert)
      - Kan kombineres: 'AUTO_USDT,BTC/USDT'
    """
    wl_raw = (env_watchlist or "").strip()
    if not wl_raw:
        return []

    # Direkte liste?
    if "AUTO_USDT" not in wl_raw:
        return [s.strip() for s in wl_raw.split(",") if s.strip()]

    # AUTO_USDT
    try:
        markets = ex.load_markets()
    except Exception:
        markets = getattr(ex, "markets", {}) or {}

    cands = []
    for sym, m in (markets or {}).items():
        if not isinstance(sym, str) or "/USDT" not in sym:
            continue
        is_spot = bool(m.get("spot", True))
        if not is_spot and not m.get("linear", False):
            continue
        vol = (
            float(m.get("info", {}).get("quoteVolume", 0))
            if isinstance(m.get("info"), dict) else
            float(m.get("quoteVolume", 0) or 0)
        )
        cands.append((vol, sym))

    cands.sort(reverse=True)
    picked = [sym for _, sym in cands[: int(os.getenv("TOP_N", str(top_n))) ]]

    extras = [s.strip() for s in wl_raw.split(",") if s.strip() and s != "AUTO_USDT"]
    # unike, stabil rekkefølge
    return list(dict.fromkeys(picked + extras))