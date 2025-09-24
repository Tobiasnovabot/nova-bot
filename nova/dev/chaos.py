from __future__ import annotations
import os, random
def chaos_on() -> bool: return os.getenv("NOVA_CHAOS","0")=="1"
def maybe_chaos(label: str, df):
    if not chaos_on(): return df
    try:
        if hasattr(df,"columns") and "close" in df.columns and len(df):
            df = df.copy()
            if random.random()<0.01:
                import random as R
                df.loc[df.index[-1],"close"] *= (1.0 + R.uniform(-0.02,0.02))
    except Exception: pass
    return df