"""Safe stub for exchange factory to unblock engine start.
Keep API shape: build(name: str = "null", **kwargs) -> object."""
from typing import Any

class _NullExchange:
    def __init__(self, **kwargs: Any) -> None:
        self.params = dict(kwargs)
    def ping(self) -> bool:
        return True

def build(name: str = "null", **kwargs: Any) -> _NullExchange:
    _ = kwargs.pop("mode", None)  # accept/ignore mode to keep signature stable
    return _NullExchange(**kwargs)
