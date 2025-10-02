from abc import ABC, abstractmethod
class Strategy(ABC):
    @abstractmethod
    def decide(self, ohlcv_df): ...
