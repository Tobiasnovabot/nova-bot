from nova import paths as NPATH
#!/usr/bin/env python3
"""
Nova – Full system selfcheck
Kjører tester på alle moduler + systemd + state.
"""

import importlib, os, sys, json, pathlib, time

RESULTS = []

def check(label, func):
    try:
        func()
        RESULTS.append(f"PASS  {label}")
    except Exception as e:
        RESULTS.append(f"FAIL  {label} -> {type(e).__name__}: {e}")

# 1) Python + venv
def check_python():
    assert sys.version_info >= (3, 12)
    assert "venv" in sys.prefix or ".venv" in sys.prefix

check("Python 3.12+ & venv aktiv", check_python)

# 2) Miljøvariabler
def check_env():
    for k in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "MODE", "EXCHANGE"]:
        assert os.getenv(k), f"{k} not set"

check("Miljøvariabler (.env)", check_env)


def check_tg():
    from nova.notify import send as tg_send
    res = tg_send("🔔 Selfcheck ping")
    assert res.get("ok"), res



# 4) Engine import & watchdog
def check_engine_import():
    import nova.engine.run, nova.engine.watchdog
    assert hasattr(nova.engine.run, "main")

check("Engine import", check_engine_import)

# 5) Guards
def check_guards():
    from nova.guards import slip_liq_guard, oracle
    assert slip_liq_guard.slip_liq_ok(100, 100, 20)
    assert oracle.cross_ok(100, 101, tol_bps=200)

check("Guards (slippage/oracle)", check_guards)

# 6) Risk / Canary
def check_risk():
    from nova.risk import canary
    f = canary.scale_factor(5, 0)
    assert 0 <= f <= 1

check("Risk (canary)", check_risk)

# 7) Devops breaker
def check_breaker():
    from nova.devops import error_breaker
    assert error_breaker.ok()
    error_breaker.hit()
    assert isinstance(error_breaker.ok(), bool)

check("Devops error_breaker", check_breaker)

# 8) Orders lifecycle
def check_orders():
    import nova.orders.lifecycle as lc
    assert hasattr(lc, "place_and_confirm")

check("Orders lifecycle", check_orders)

# 9) Alerts
def check_alerts():
    import nova.alerts.alerts as al
    al.info("ℹ️ Alerts modul OK")

check("Alerts modul", check_alerts)

# 10) Telemetry heartbeat
def check_hb():
    from nova.telemetry import heartbeat
    t0 = time.time()
    t1 = heartbeat.heartbeat(t0, t0-301, every=300)
    assert t1 >= t0

check("Telemetry heartbeat", check_hb)

# 11) State og trades.json
def check_state_and_trades():
    from nova.stateio import stateio
    s = stateio.load_state()
    p = pathlib.Path(os.getenv("NOVA_HOME", "/tmp/nova_home/nova")) / NPATH.TRADES.as_posix()
    assert p.exists(), "trades.json missing"
    data = json.loads(p.read_text() or "[]")
    assert isinstance(data, list)

check("State & trades.json", check_state_and_trades)

# Resultater
print("\n".join(RESULTS))
