from .sma import sma_signal
from .ema import ema_signal
from .macd import macd_signal
from .rsi import rsi_signal
from .breakout import breakout_signal
from .mean_reversion import meanrev_signal
from .momentum import momentum_signal
from .volume_spike import volspike_signal
from .bbands import bbands_signal
from .ai_predict import ai_predict_signal

STRATEGIES = {
    "sma": sma_signal,
    "ema": ema_signal,
    "macd": macd_signal,
    "rsi": rsi_signal,
    "breakout": breakout_signal,
    "mean_reversion": meanrev_signal,
    "momentum": momentum_signal,
    "volume_spike": volspike_signal,
    "bbands": bbands_signal,
    "ai_predict": ai_predict_signal
}
