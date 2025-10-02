from datetime import datetime, timezone, timezone
import os
def utc_now_s() -> float: return datetime.now(timezone.utc).timestamp()
def is_fresh(ts_s: float | None, max_lag_s: float | None = None) -> bool:
    if ts_s is None: return False
    max_lag_s = float(os.getenv("NOVA_MAX_DATA_LAG_S", max_lag_s or 5))
    return (utc_now_s() - float(ts_s)) <= max_lag_s
