from __future__ import annotations
import importlib, pkgutil, inspect
from types import ModuleType
from typing import Dict, Callable, Any

EXCLUDE = {"__init__", "base", "util", "loader"}

def _as_signal(mod: ModuleType) -> dict[str, Callable[[dict[str, Any]|None], int]]:
    out={}
    # 1) Klassebasert: finn subclasses av StrategyBase/Strategy med NAME og signal()
    try:
        from .base import StrategyBase, Strategy  # type: ignore
        classes = []
        for _,obj in inspect.getmembers(mod, inspect.isclass):
            if obj.__module__ != mod.__name__: 
                continue
            if any(base.__name__ in {"StrategyBase","Strategy"} for base in obj.__mro__):
                classes.append(obj)
        for cls in classes:
            name = getattr(cls, "NAME", cls.__name__.lower())
            try:
                inst = cls()
                if callable(getattr(inst, "signal", None)):
                    out[name] = inst.signal
            except Exception:
                pass
    except Exception:
        pass
    # 2) Funksjonsbasert: modul-attributt "signal" med valgfri NAME
    fn = getattr(mod, "signal", None)
    if callable(fn):
        name = getattr(mod, "NAME", mod.__name__.split(".")[-1])
        out[name] = fn
    # 3) Enkle navngitte funksjoner (rsi_signal, macd_signal, etc.)
    for nm,fn2 in inspect.getmembers(mod, inspect.isfunction):
        if nm.endswith("_signal"):
            strat = nm.replace("_signal","")
            out[strat] = fn2
    return out

def load_strategies(package: str="nova.strategies", strat_max: int|None=None) -> Dict[str, Callable]:
    mod = importlib.import_module(package)
    out={}
    for m in pkgutil.iter_modules(mod.__path__):  # type: ignore
        name=m.name
        if name in EXCLUDE: 
            continue
        try:
            sub = importlib.import_module(f"{package}.{name}")
            sigs = _as_signal(sub)
            for k,v in sigs.items():
                out[k]=v
                if strat_max and len(out)>=strat_max:
                    return out
        except Exception:
            continue
    return out
