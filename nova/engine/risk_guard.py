import time, json, os, pathlib

def clamp_positions(open_positions: int, max_positions: int) -> bool:
    return open_positions < max_positions

def trip_daily_dd(current_dd: float, limit: float) -> bool:
    return current_dd >= limit

def read_equity_default(default=0.0):
    try: return float(json.load(open('runtime/equity.json'))['equity'])
    except Exception: return float(os.getenv('EQUITY_USDT', default or 0.0))

def daily_dd_breached(limit: float) -> bool:
    # enkel placeholder – kan utvides med reell PnL sporing
    return False
