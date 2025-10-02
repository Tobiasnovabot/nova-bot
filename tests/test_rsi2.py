import pytest
from nova.strategies.rsi2 import StrategyRSI2

def test_has_constants():
    s = StrategyRSI2()
    assert isinstance(s.NAME, str)
    assert isinstance(s.TF, str)