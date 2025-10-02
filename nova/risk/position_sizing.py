import os, math, time
from typing import Dict, Tuple, Optional, List

# Les konfig fra env (med defaults)
UNIT_RISK_PCT       = float(os.getenv("UNIT_RISK_PCT","0.5"))   # % av equity pr trade (ved stop-hit)
MAX_SYMBOL_PCT      = float(os.getenv("MAX_SYMBOL_PCT","5"))     # maks % av equity i ett symbol
ATR_LOOKBACK        = int(os.getenv("ATR_LOOKBACK","14"))
ATR_K               = float(os.getenv("ATR_K","2.0"))            # stop = ATR_K * ATR
DEFAULT_STOP_PCT    = float(os.getenv("DEFAULT_STOP_PCT","1.5")) # fallback hvis ATR mangler (i %)
RISK_MIN            = int(os.getenv("RISK_MIN","1"))
RISK_MAX            = int(os.getenv("RISK_MAX","10"))

def clamp(v, lo, hi): return max(lo, min(hi, v))

def unit_risk_pct_for_level(level:int)->float:
    # skaler lineært mellom 40% og 160% av UNIT_RISK_PCT
    lvl = clamp(level, RISK_MIN, RISK_MAX)
    scale = 0.4 + (lvl-1) * (1.6-0.4)/(RISK_MAX-RISK_MIN if RISK_MAX>RISK_MIN else 1)
    return UNIT_RISK_PCT * scale

def atr_from_ohlcv(ohlcv: List[List[float]]) -> Optional[float]:
    # ohlcv: [ts, open, high, low, close, vol]
    if not ohlcv or len(ohlcv) < ATR_LOOKBACK+1:
        return None
    trs = []
    for i in range(1, len(ohlcv)):
        _,o1,h1,l1,c1,_ = ohlcv[i]
        _,o0,h0,l0,c0,_ = ohlcv[i-1]
        tr = max(h1-l1, abs(h1-c0), abs(l1-c0))
        trs.append(tr)
    trN = trs[-ATR_LOOKBACK:]
    return sum(trN)/len(trN) if trN else None

def compute_size(price: float, equity_usd: float, risk_level:int, atr: Optional[float]=None) -> Dict[str,float]:
    risk_pct = unit_risk_pct_for_level(risk_level) / 100.0
    stop_pct = (ATR_K * atr / price) if (atr and price>0) else (DEFAULT_STOP_PCT/100.0)
    stop_pct = max(stop_pct, 0.002)  # min 0.2% for numerisk stabilitet

    # Notional via risikomodell (Kelly-light)
    notional_risk = (equity_usd * risk_pct) / stop_pct
    # Hard cap per symbol
    notional_cap  = equity_usd * (MAX_SYMBOL_PCT/100.0)
    notional      = min(notional_risk, notional_cap)

    qty = notional / price if price>0 else 0.0
    return {
        "price": price,
        "risk_pct": risk_pct*100.0,
        "stop_pct": stop_pct*100.0,
        "notional_usd": notional,
        "qty": qty,
        "cap_usd": notional_cap
    }
