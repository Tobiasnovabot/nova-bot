from typing import Dict, Type, Any, List
_registry: Dict[str, Type['Strategy']] = {}

def register(name: str):
    def deco(cls):
        _registry[name] = cls
        cls.strategy_name = name
        return cls
    return deco

def available_strategies() -> List[str]:
    return sorted(_registry.keys())

class Strategy:
    def __init__(self, params: Dict[str, Any]):
        self.params = params or {}
    def on_bar(self, bar: Dict[str, Any]) -> Dict[str, Any]:
        """Returner signal: {'symbol': str, 'side': 'buy'|'sell'|'flat', 'score': float}"""
        raise NotImplementedError
