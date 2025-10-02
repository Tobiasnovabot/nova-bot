def cross_ok(ref_px: float, ex_px: float, tol_bps: int = 75) -> bool:
    """Kryssjekk mot referanse-orakel; avvis hvis avvik > tol_bps."""
    if ref_px <= 0 or ex_px <= 0:
        return True
    return abs(ref_px - ex_px) / ref_px * 1e4 <= tol_bps
