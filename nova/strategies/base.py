from __future__ import annotations
from typing import Protocol, Dict

class StrategyProto(Protocol):
    NAME: str
    def signal(self, ohlcv: Dict[str, float] | None = None) -> int: ...

class StrategyBase:
    NAME = "base"
    def signal(self, ohlcv=None) -> int:
        return 0

# Bakoverkompatibilitet
Strategy = StrategyBase
