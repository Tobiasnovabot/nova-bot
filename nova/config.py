import os

def _f(name, dflt): return float(os.getenv(name, dflt))
def _i(name, dflt): return int(os.getenv(name, dflt))

# Risiko
MAX_GROSS_EXPOSURE   = _f("MAX_GROSS_EXPOSURE", 1.0)     # 1.0 = 100% av equity
STOP_PCT             = _f("STOP_PCT", 0.02)              # 2% per-symbol stop
DRAWDOWN_TRIM_WARN   = _f("DRAWDOWN_TRIM_WARN", 0.10)    # reduser størrelse ved 10% DD
DRAWDOWN_TRIM_CRIT   = _f("DRAWDOWN_TRIM_CRIT", 0.20)    # sterk reduksjon ved 20% DD

# Auto-deaktivering av strategier
STRAT_DISABLE_WINRATE = _f("STRAT_DISABLE_WINRATE", 0.45)
STRAT_DISABLE_SHARPE  = _f("STRAT_DISABLE_SHARPE", 0.0)
STRAT_MIN_TRADES      = _i("STRAT_MIN_TRADES", 30)

# Størrelses-trimming ved drawdown
def dd_size_multiplier(drawdown: float) -> float:
    if drawdown >= DRAWDOWN_TRIM_CRIT: return 0.25
    if drawdown >= DRAWDOWN_TRIM_WARN: return 0.5
    return 1.0
