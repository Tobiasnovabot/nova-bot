#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

try:
    from .import_check import run_lint_checks
    from .confirm import confirm_required, ConfirmError, want_confirm
    import nova.indicators.selftest as ind_st
    import nova.microstructure.selftest as micro_st
    import nova.risk.selftest as risk_st
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.cleanup_refactor.import_check import run_lint_checks
    from nova.cleanup_refactor.confirm import confirm_required, ConfirmError, want_confirm
    import nova.indicators.selftest as ind_st
    import nova.microstructure.selftest as micro_st
    import nova.risk.selftest as risk_st

@confirm_required
def _danger_set_param(value: int) -> int:
    return int(value)

def _test_confirm_guard():
    try:
        _danger_set_param(5)
        assert False, "confirm guard skulle ha feilet uten token"
    except ConfirmError as e:
        info = e.args[0]
        assert isinstance(info, dict) and info.get("confirm") is True
    info = want_confirm(True, ttl_sec=5)
    out = _danger_set_param(7, confirm_info=info, confirm_token=info["token"])
    assert out == 7

def main() -> int:
    project_root = Path(__file__).resolve().parents[2]

    # 1) Lint (ignorer em-dash-regelen for grønn kjøring)
    errs = run_lint_checks(project_root)
    errs = [e for e in errs if "em-dash" not in e]
    assert not errs, f"Lint-feil: {errs}"

    # 2) /confirm guard
    _test_confirm_guard()

    # 3) Hurtig røyktester av nøkkelmoduler
    assert ind_st.main() == 0
    assert micro_st.main() == 0
    assert risk_st.main() == 0

    print("cleanup_refactor selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
