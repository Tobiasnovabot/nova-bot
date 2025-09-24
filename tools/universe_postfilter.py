#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
U = ROOT / "data" / "universe.json"
TARGET = int(os.getenv("TOP_N", "300"))
QUOTE = os.getenv("QUOTE", "USDT").upper()
EXNAME = os.getenv("TRADING_EXCHANGE", os.getenv("EXCHANGE", "binance")).lower()

def load_symbols():
    if not U.exists(): return []
    try:
        data = json.loads(U.read_text())
        if isinstance(data, dict): data = data.get("symbols", [])
        # de-dupe men behold rekkefølge
        seen, out = set(), []
        for s in data:
            if s not in seen:
                seen.add(s); out.append(s)
        return out
    except Exception:
        return []

def save_symbols(symbols):
    U.write_text(json.dumps({"symbols": symbols}, ensure_ascii=False, indent=2))

def main():
    base = load_symbols()
    try:
        import ccxt
    except Exception as e:
        # ingen ccxt – bare lagre base
        save_symbols(base); print(f"universe_postfilter: ccxt missing: {e}", file=sys.stderr); return

    ex = getattr(ccxt, EXNAME)()
    ex.load_markets()
    # gyldige spot USDT symboler
    valid = []
    for s, m in ex.markets.items():
        if m.get("spot") and s.endswith(f"/{QUOTE}") and (m.get("active") is not False):
            valid.append(s)
    valid_set = set(valid)

    # 1) filtrer eksisterende til gyldige
    filtered = [s for s in base if s in valid_set]

    # 2) hvis under TARGET, fyll på med mest likvide kandidater
    if len(filtered) < TARGET:
        # prioriter med tickers volum hvis mulig
        try:
            tick = ex.fetch_tickers(valid)
            # bruk quoteVolume eller baseVolume*last
            scored = []
            for s in valid:
                t = tick.get(s, {})
                qv = t.get("quoteVolume") or 0
                if not qv:
                    bv = t.get("baseVolume") or 0
                    last = t.get("last") or 0
                    qv = (bv or 0) * (last or 0)
                scored.append((qv or 0, s))
            scored.sort(reverse=True)
            ordered = [s for _, s in scored]
        except Exception:
            # fallback: alfabetisk
            ordered = sorted(valid)

        pick = []
        chosen = set(filtered)
        for s in ordered:
            if s not in chosen:
                pick.append(s); chosen.add(s)
                if len(filtered) + len(pick) >= TARGET:
                    break
        filtered += pick

    save_symbols(filtered)
    print(f"universe_postfilter: {len(filtered)}/{TARGET} symbols for {EXNAME} {QUOTE}")

if __name__ == "__main__":
    main()
