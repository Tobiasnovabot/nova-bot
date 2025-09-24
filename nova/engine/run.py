import os, time, random, errno, json
from prometheus_client import start_http_server, CollectorRegistry
from .metrics_init import Metrics
from .strategy_runner import StrategyRunner
from .broker_paper import PaperBroker

def fetch_next_bar():
    p = 100 + random.uniform(-0.5, 0.5)
    return {"symbol":"BTCUSDT","open":p,"high":p*1.001,"low":p*0.999,"close":p,"volume":random.uniform(10,100),"ai_score":random.uniform(-1,1)}

def main():
    reg = CollectorRegistry()
    port = int(os.getenv("NOVAX_METRICS_PORT", "9112"))
    try:
        start_http_server(port, addr="127.0.0.1", registry=reg)
        print(f"[metrics] serving on http://127.0.0.1:{port}/metrics", flush=True)
    except OSError as e:
        import errno as _errno
        if e.errno == _errno.EADDRINUSE:
            print(f"[metrics] port {port} in use, skipping server start", flush=True)
        else:
            raise

    m = Metrics(reg); m.up.set(1)

    params = {
        "strategies": json.load(open("/home/nova/nova-bot/config/strategies.json")),
        "state_path": "/home/nova/nova-bot/state.json",
        "trades_path": "/home/nova/nova-bot/trades.json",
        "equity_path": "/home/nova/nova-bot/equity.json"
    }
    runner = StrategyRunner(params, metrics=m)
    broker = PaperBroker(metrics=m)  # viktig: gir KPI-metrics
    lbl = broker.strategy_label
    m.strategy_trades_total.labels(lbl,"win").inc(0)
    m.strategy_trades_total.labels(lbl,"loss").inc(0)
    m.strategy_trades_total.labels(lbl,"flat").inc(0)
    m.strategy_pnl_pos_total.labels(lbl).inc(0)
    m.strategy_pnl_neg_total.labels(lbl).inc(0)
    lbl = broker.strategy_label
    m.strategy_trades_total.labels(lbl,"win").inc(0)
    m.strategy_trades_total.labels(lbl,"loss").inc(0)
    m.strategy_trades_total.labels(lbl,"flat").inc(0)
    m.strategy_pnl_pos_total.labels(lbl).inc(0)
    m.strategy_pnl_neg_total.labels(lbl).inc(0)
    lbl = broker.strategy_label
    m.strategy_trades_total.labels(lbl,"win").inc(0)
    m.strategy_trades_total.labels(lbl,"loss").inc(0)
    m.strategy_trades_total.labels(lbl,"flat").inc(0)
    m.strategy_pnl_pos_total.labels(lbl).inc(0)
    m.strategy_pnl_neg_total.labels(lbl).inc(0)
    lbl = broker.strategy_label
    m.strategy_trades_total.labels(lbl,"win").inc(0)
    m.strategy_trades_total.labels(lbl,"loss").inc(0)
    m.strategy_trades_total.labels(lbl,"flat").inc(0)
    m.strategy_pnl_pos_total.labels(lbl).inc(0)
    m.strategy_pnl_neg_total.labels(lbl).inc(0)

    while True:
        t0 = time.time()
        bar = fetch_next_bar()
        vote = runner.on_bar(bar)

        # mappe vote -> side
        
        # (test fjernet)
        side = vote.get("side") or ("buy" if vote.get("score",0)>0 else ("sell" if vote.get("score",0)<0 else "flat"))


        equity, pnl_total, exposure = broker.on_signal(bar, side)
        m.pnl_total.set(pnl_total)
        m.equity_total.set(equity)
        m.positions_exposure.set(exposure)

        m.engine_heartbeat_total.inc()
        m.engine_lag_seconds.set(time.time() - t0)
        time.sleep(1.0)

if __name__ == "__main__":
    main()
