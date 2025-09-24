from nova import paths as NPATH
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, json
from pathlib import Path

try:
    from .security_compliance import (
        store_key, get_key, rotate_key,
        start_confirm, finalize_confirm,
        audit_log, export_tax_csv,
    )
    from nova.core_boot.core_boot import NOVA_HOME, now_oslo
    from nova.stateio.stateio import read_json_atomic, write_json_atomic
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.security_compliance.security_compliance import (
        store_key, get_key, rotate_key,
        start_confirm, finalize_confirm,
        audit_log, export_tax_csv,
    )
    from nova.core_boot.core_boot import NOVA_HOME, now_oslo
    from nova.stateio.stateio import read_json_atomic, write_json_atomic

def main() -> int:
    # --- Key vault ---
    store_key("BINANCE_KEY", "abc123")
    assert get_key("BINANCE_KEY") == "abc123"
    rotate_key("BINANCE_KEY", "def456")
    assert get_key("BINANCE_KEY") == "def456"

    # --- 2-step confirm ---
    rec = start_confirm("risk_level_change", role="admin", ttl_sec=60, meta={"to": 9})
    bad = finalize_confirm(rec["token"], role="viewer")
    assert bad["ok"] is False and bad["why"] == "wrong_role"
    ok = finalize_confirm(rec["token"], role="admin")
    assert ok["ok"] is True and ok["action"] == "risk_level_change"

    # --- audit log ---
    audit_log("unit_test_event", {"k": 1})
    audit_p = NOVA_HOME / "logs" / "audit.jsonl"
    assert audit_p.exists()
    last = audit_p.read_text(encoding="utf-8").strip().splitlines()[-1]
    j = json.loads(last)
    assert j["event"] == "unit_test_event"

    # --- seed trades for export ---
    trades = [
        {
            "ts": f"{now_oslo().year}-01-02T10:00:00+00:00",
            "sym": "BTC/USDT",
            "side": "buy",
            "qty": 0.1,
            "price": 30000.0,
            "fee": 1.2,
            "pnl_real": 0.0,
        },
        {
            "ts": f"{now_oslo().year}-03-04T11:00:00+00:00",
            "sym": "BTC/USDT",
            "side": "sell",
            "qty": 0.1,
            "price": 33000.0,
            "fee": 1.3,
            "pnl_real": 250.0,
        },
    ]
    write_json_atomic(NOVA_HOME / "data" / NPATH.TRADES.as_posix(), trades, backup=False)

    # --- export CSV ---
    out = export_tax_csv(now_oslo().year)
    assert out.exists() and out.suffix == ".csv" and out.stat().st_size > 0
    head = out.read_text(encoding="utf-8").splitlines()[0]
    assert head.startswith("ts,symbol,side,qty,price,fee_usd,pnl_real")

    print("security_compliance selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
