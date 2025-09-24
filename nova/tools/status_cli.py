#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
from nova import paths as NPATH
import json, sys
from pathlib import Path
from datetime import datetime, timezone, timezone
from typing import Any, Dict, List, Optional

try:
    from nova.core_boot.core_boot import NOVA_HOME, now_oslo
except Exception:
    from pathlib import Path as _P
    NOVA_HOME = _P.home() / ".nova" / "nova"
    def now_oslo():
        return datetime.now(timezone.utc)

DATA = Path(NOVA_HOME) / "data"
STATE_P = DATA / NPATH.STATE.as_posix()
TRADES_P = DATA / NPATH.TRADES.as_posix()
EQUITY_P = DATA / NPATH.EQUITY.as_posix()

def _read(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default

def _parse_ts(s: str) -> Optional[datetime]:
    try:
        # ISO 8601; håndter evt. Z
        s = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None

def _today_bounds():
    now = now_oslo()
    # bruk UTC for robust filtrering
    utc_now = datetime.now(timezone.utc)
    start = utc_now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start, end

def main() -> int:
    st: Dict[str, Any] = _read(STATE_P, {})
    trades: List[Dict[str, Any]] = _read(TRADES_P, [])
    equity: List[Dict[str, Any]] = _read(EQUITY_P, [])

    eq = float(st.get("equity_usd", 0.0) or 0.0)
    pnl_total = float(st.get("pnl_total", 0.0) or 0.0)
    positions = st.get("positions", {}) if isinstance(st.get("positions"), dict) else {}
    open_pos = sum(1 for p in positions.values() if p)

    # bandit “minne”
    bandit = st.get("bandit_state", st.get("bandit", {}))
    fav = None
    if isinstance(bandit, dict) and bandit:
        # prøv å finne høyest mean/alpha-beta
        best_key, best_score = None, -1.0
        for k, v in bandit.items():
            try:
                # støtt både {mean: x} og {alpha: a, beta: b}
                mean = float(v.get("mean")) if isinstance(v, dict) and "mean" in v else None
                if mean is None and isinstance(v, dict) and "alpha" in v and "beta" in v:
                    a, b = float(v["alpha"]), float(v["beta"])
                    mean = a / (a + b) if (a + b) > 0 else 0.0
                if mean is None: continue
                if mean > best_score:
                    best_key, best_score = k, mean
            except Exception:
                continue
        fav = f"{best_key} ({best_score:.3f})" if best_key is not None else None

    # dagens trades og PnL
    t0, t1 = _today_bounds()
    trades_today = 0
    pnl_day = 0.0
    for tr in trades:
        ts = tr.get("ts") or tr.get("time") or tr.get("timestamp")
        dt = _parse_ts(str(ts)) if ts is not None else None
        if dt is None:
            continue
        # normaliser til UTC hvis naive
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if t0 <= dt <= t1:
            trades_today += 1
            try:
                pnl_day += float(tr.get("pnl_real", 0.0) or 0.0)
            except Exception:
                pass

    # simple equity snapshot info
    eq_pts = len(equity)

    # print
    print("=== NOVA status ===")
    print(f"mode={st.get('mode','?')} enabled={st.get('bot_enabled')}")
    print(f"equity={eq:.2f}  pnl_day={pnl_day:.2f}  pnl_total={pnl_total:.2f}")
    print(f"trades_today={trades_today}  equity_points={eq_pts}  open_positions={open_pos}")
    if fav:
        print(f"bandit_fav={fav}")
    else:
        print("bandit_fav=<n/a>")
    wl = st.get("watch", [])
    if isinstance(wl, list) and wl:
        show = ",".join(wl[:12])
        more = f"+{max(0,len(wl)-12)}" if len(wl) > 12 else ""
        print(f"watch={show} {more}".rstrip())

    return 0

if __name__ == "__main__":
    raise SystemExit(main())