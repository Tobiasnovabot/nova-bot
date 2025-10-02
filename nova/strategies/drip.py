# nova/strategies/drip.py
import time, os

# konfig via env
DRIP_PAIR  = os.getenv("DRIP_PAIR",  "binance:ETH/USDC")
DRIP_SECS  = float(os.getenv("DRIP_SECS", "600"))   # hvert 10. min
DRIP_EDGE  = float(os.getenv("DRIP_EDGE", "0.0"))   # ingen prisbetingelse; ren tidsdrypp

_last_ts = 0.0
_flip    = 1  # +1 buy, -1 sell

def signal(symbol: str, price: float, broker) -> int:
    """Returner +1/-1 hver DRIP_SECS kun for DRIP_PAIR. 0 ellers."""
    global _last_ts, _flip
    if symbol != DRIP_PAIR:
        return 0
    now = time.time()
    if now - _last_ts >= DRIP_SECS:
        _last_ts = now
        s = _flip
        _flip = -_flip
        return s
    return 0
