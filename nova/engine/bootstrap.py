from __future__ import annotations
# Samler "early boot"-oppgaver for engine-prosessen.
import signal, sys
from nova.engine.watchdog import start_watchdog
from nova.stateio.stateio import save_state, load_state

def _graceful(_sig, _frm):
    try:
        s = load_state()
        s["engine_status"] = "stopping"
        save_state(s)
    finally:
        sys.exit(0)

def init_engine_process():
    """Kall denne helt i starten av nova.engine.run (før loopen).
       Returnerer stop-event for watchdog (kan ignoreres)."""
    signal.signal(signal.SIGTERM, _graceful)
    signal.signal(signal.SIGINT, _graceful)
    wd_stop = start_watchdog()
    return wd_stop