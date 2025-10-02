def signal_from_ticker(t):
    # kjøp hvis +2% siste 24h, selg hvis -2% fra entry (tas i engine)
    pct = float(t.get("percentage") or 0.0)
    if pct >= 2.0:  # bullish momentum
        return "buy", {"reason":"pct_up"}
    return "hold", {}
