import importlib

def test_strategy_imports():
    mod = importlib.import_module(f"nova.strategies.sma_15m")
    cls = getattr(mod, "Strategy_SMA_15m")
    s = cls()
    assert isinstance(s.NAME, str)
    assert isinstance(s.TF, str)