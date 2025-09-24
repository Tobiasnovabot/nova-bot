from prometheus_client import Gauge, Counter

class Metrics:
    def __init__(self, registry):
        # Må settes FØR metrikker lages:
        self.reg = registry

        # Basis/engine
        self.up                     = Gauge('novax_up', 'exporter up flag', registry=self.reg)
        self.engine_heartbeat_total = Counter('novax_engine_heartbeat_total', 'engine heartbeats', registry=self.reg)
        self.engine_lag_seconds     = Gauge('novax_engine_lag_seconds', 'engine loop duration', registry=self.reg)
        self.equity_total           = Gauge('novax_equity_total', 'total equity', registry=self.reg)
        self.pnl_total              = Gauge('novax_pnl_total', 'cumulative pnl', registry=self.reg)
        self.positions_exposure     = Gauge('novax_positions_exposure', 'gross exposure [-1..1]', registry=self.reg)
        self.last_vote_score        = Gauge('novax_last_vote_score', 'last vote score', registry=self.reg)

        # Strategier – status/telling
        self.strategy_count         = Gauge('novax_strategy_count', 'loaded strategies', registry=self.reg)
        self.strategy_enabled       = Gauge('novax_strategy_enabled', 'strategy enabled flag', ['strategy'], registry=self.reg)

        # Signaler / feil
        self.signals_total          = Counter('novax_signals_total', 'total signals produced', registry=self.reg)
        self.signals_by_strategy    = Counter('novax_signals_by_strategy_total', 'signals by strategy', ['strategy'], registry=self.reg)
        self.strategy_errors_total  = Counter('novax_strategy_errors_total', 'strategy runner errors', registry=self.reg)

        # Trades/PnL per strategi
        self.strategy_trades_total  = Counter('novax_strategy_trades_total', 'trades by strategy and outcome', ['strategy','outcome'], registry=self.reg)
        self.strategy_pnl_pos_total = Counter('novax_strategy_pnl_pos_total', 'positive pnl per strategy', ['strategy'], registry=self.reg)
        self.strategy_pnl_neg_total = Counter('novax_strategy_pnl_neg_total', 'negative pnl per strategy (abs)', ['strategy'], registry=self.reg)
