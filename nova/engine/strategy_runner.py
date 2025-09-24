from typing import Dict, Any, List
from .strategies import _registry  # registry
from .strategies import sma, ema, macd, rsi, breakout, meanrev, momentum, volspike, bbands, ai_predict  # noqa
from .voter import decide
from .persist import atomic_write_json, rotate, load_json

class StrategyRunner:
    def __init__(self, params: Dict[str, Any], metrics=None, broker=None):
        self.params = params or {}
        self.metrics = metrics
        self.broker = broker
        self.state = load_json(self.params.get("state_path","/home/nova/nova-bot/state.json"), {})
        self.trades_path = self.params.get("trades_path","/home/nova/nova-bot/trades.json")
        self.state_path  = self.params.get("state_path","/home/nova/nova-bot/state.json")
        self.equity_path = self.params.get("equity_path","/home/nova/nova-bot/equity.json")

        self.strategies = []
        strat_cfg: Dict[str, Dict] = self.params.get("strategies", {})
        for name, cfg in strat_cfg.items():
            if name in _registry and (cfg or {}).get("enabled", True):
                inst = _registry[name]((cfg or {}).get("params", {}))
                inst.NAME = getattr(inst, "NAME", name)
                self.strategies.append(inst)
                if self.metrics: self.metrics.strategy_enabled.labels(strategy=inst.NAME).set(1)

        if self.metrics:
            self.metrics.strategy_count.set(len(self.strategies))

        self.state.setdefault("strategies", {})
        for s in self.strategies:
            self.state["strategies"].setdefault(s.NAME, {"signals":0})

    def on_bar(self, bar: Dict[str, Any]) -> Dict[str, Any]:
        sigs: List[Dict[str, Any]] = []
        for s in self.strategies:
            try:
                out = s.on_bar(bar) or {}
                out.setdefault("signal","flat")
                out.setdefault("score", 0.0)
                out.setdefault("conf", 1.0)
                out["strategy"] = getattr(s, "NAME", s.__class__.__name__)
                sigs.append(out)
                name = out["strategy"]
                self.state["strategies"].setdefault(name, {"signals":0})
                self.state["strategies"][name]["signals"] += 1
                if self.metrics: self.metrics.signals_by_strategy.labels(strategy=name).inc()
            except Exception:
                if self.metrics: self.metrics.strategy_errors_total.inc()

        vote = decide(sigs)

        # velg ansvarlig strategi for trade: topp |score| som støtter action
        chosen = None
        if vote.get("action") in ("buy","sell"):
            same_dir = [s for s in sigs if s.get("signal")==vote["action"]]
            if same_dir:
                chosen = max(same_dir, key=lambda x: abs(float(x.get("score",1.0))))
                chosen = chosen.get("strategy")

        self.state.setdefault("last_signals", [])
        self.state["last_signals"] = (self.state["last_signals"] + sigs)[-50:]
        if self.metrics:
            self.metrics.signals_total.inc(len(sigs))
            self.metrics.last_vote_score.set(vote.get("score",0.0))

        # hvis broker finnes, utfør handel og oppdater equity/pnl/exposure
        if self.broker:
            equity, pnl_total, exposure = self.broker.on_signal(bar, vote.get("action","flat"), chosen)
            if self.metrics:
                self.metrics.equity_total.set(equity)
                self.metrics.pnl_total.set(pnl_total)
                self.metrics.positions_exposure.set(exposure)

        return vote

    def persist_tick(self, equity: float, pnl_total: float) -> None:
        eq = load_json(self.equity_path, [])
        eq.append({"t": self._now(), "equity": equity, "pnl_total": pnl_total})
        if len(eq)%50==0: rotate(self.equity_path, keep=20)
        atomic_write_json(self.equity_path, eq)
        if len((self.state or {}))%20==0: rotate(self.state_path, keep=20)
        atomic_write_json(self.state_path, self.state)

    @staticmethod
    def _now():
        import time
        return int(time.time())
