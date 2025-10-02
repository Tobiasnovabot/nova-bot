from nova import paths as NPATH
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, time, os
from pathlib import Path

try:
    from .bot_intel import health_snapshot, auto_heal, inject_chaos, chaos_status, explain_decision
    from nova.core_boot.core_boot import NOVA_HOME
    from nova.stateio.stateio import snapshot_equity, read_json_atomic
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.bot_intel.bot_intel import health_snapshot, auto_heal, inject_chaos, chaos_status, explain_decision
    from nova.core_boot.core_boot import NOVA_HOME
    from nova.stateio.stateio import snapshot_equity, read_json_atomic

def main() -> int:
    # Rydd og simuler manglende filer
    data = NOVA_HOME / "data"
    logs = NOVA_HOME / "logs"
    (data / NPATH.STATE.as_posix()).unlink(missing_ok=True)
    (data / NPATH.TRADES.as_posix()).unlink(missing_ok=True)
    (data / NPATH.EQUITY.as_posix()).unlink(missing_ok=True)
    (logs / "run.out").unlink(missing_ok=True)

    # Lag gammel lock og sett mtime langt tilbake
    lockp = NOVA_HOME / "nova.lock"
    lockp.parent.mkdir(parents=True, exist_ok=True)
    lockp.write_text("lock", encoding="utf-8")
    old = time.time() - 7200  # 2 timer gammelt
    try:
        os.utime(lockp, (old, old))
    except Exception:
        pass  # enkelte FS kan blokkere; auto_heal vil da ikke fjerne

    # Health + heal
    h = health_snapshot()
    healed = auto_heal(h)["healed"]

    # Init-filer må være opprettet
    assert "init_state" in healed and "init_trades" in healed and "init_equity" in healed and "init_log" in healed
    # Lock skal være fjernet ved stale, ellers rapportert forsøk
    assert any(x in healed for x in ("remove_stale_lock", "lock_remove_fail")), f"Heal actions: {healed}"

    # Chaos
    info = inject_chaos("latency", 1)
    st = chaos_status()
    assert st.get("scenario") == "latency"

    # Explainability
    exp = explain_decision({
        "symbol":"BTC/USDT",
        "features":{"rsi": 65, "ema_slope": 0.02, "vol_spike": -0.3},
        "gates":{"guards": True, "micro": True, "cost_gate": False},
        "costs_bps": 25.0,
        "expected_edge_bps": 20.0,
        "chosen":"hold",
    })
    assert exp["decision"] == "hold"
    assert "edge<=cost" in exp["why"]

    print("bot_intel selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
