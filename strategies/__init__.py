from . import macd, bb_breakout, meanrev_z, vwap_pullback, keltner_breakout, adx_filter
try:
    from . import ema_cross, rsi_reversion, breakout
except Exception:
    class _Dummy:
        @staticmethod
        def setup(cfg): return {}
        @staticmethod
        def signal(t,o,p): return ("hold",{})
    ema_cross=_Dummy; rsi_reversion=_Dummy; breakout=_Dummy
