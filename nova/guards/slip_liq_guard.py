def slip_liq_ok(exp_px: float, fill_px: float, notional: float, slip_bps: int = 50) -> bool:
    """Simpel slippage-guard: avvis hvis avvik > slip_bps.
       (Bytt ut/utvid med faktisk orderbook-liq når tilgjengelig.)"""
    if notional < 10:
        return True
    if exp_px <= 0 or fill_px <= 0:
        return True
    slip = abs(fill_px - exp_px) / exp_px * 1e4
    return slip <= slip_bps
