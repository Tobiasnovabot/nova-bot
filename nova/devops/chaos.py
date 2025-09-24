import os, random
def chaos_on() -> bool: return os.getenv("NOVA_CHAOS", "0") == "1"
def maybe_chaos(label: str, df):
    """1% sjanse til å forstyrre siste close ±2% (kun ved CHAOS=1)."""
    if not chaos_on() or df is None or not len(df):
        return df
    if random.random() < 0.01 and "close" in df.columns:
        df = df.copy()
        df.loc[df.index[-1], "close"] *= (1.0 + random.uniform(-0.02, 0.02))
    return df
