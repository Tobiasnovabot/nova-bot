# REGISTER_STRATEGIES
REGISTERED = []

from nova.strategies.sma_5m import Strategy_SMA_5m
REGISTERED.append(Strategy_SMA_5m())
from nova.strategies.sma_1h import Strategy_SMA_1h
REGISTERED.append(Strategy_SMA_1h())
from nova.strategies.sma_15m import Strategy_SMA_15m
REGISTERED.append(Strategy_SMA_15m())

from nova.strategies.sma_cross import StrategySMACross
REGISTERED.append(StrategySMACross())
from nova.strategies.rsi2 import StrategyRSI2
REGISTERED.append(StrategyRSI2())
