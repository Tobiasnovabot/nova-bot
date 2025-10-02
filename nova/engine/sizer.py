def position_size(equity_usdt: float, risk_frac: float, price: float, min_usd: float=10.0):
    usd = max(equity_usdt * risk_frac, min_usd)
    qty = usd / max(price, 1e-8)
    return max(qty, 0.0)
