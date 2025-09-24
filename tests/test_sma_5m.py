import importlib

def test_strategy_imports():
    mod = importlib.import_module(f"nova.strategies.sma_5m")
    cls = getattr(mod, "Strategy_SMA_5m")
    s = cls()
    assert isinstance(s.NAME, str)
    assert isinstance(s.TF, str)