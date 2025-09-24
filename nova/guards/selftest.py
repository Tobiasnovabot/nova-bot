#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

try:
    from .guards import update_drawdown, pretrade_checks, reset_daily, set_params
    from .guards import _GUARD  # type: ignore
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.guards.guards import update_drawdown, pretrade_checks, reset_daily, set_params
    from nova.guards.guards import _GUARD  # type: ignore

def main() -> int:
    # Stramme parametre for rask test og ingen stille timer
    reset_daily()
    set_params(day_loss_hard_usd=10.0, cooldown_min=5, loss_streak_max=3, loss_cooldown_min=2, quiet_hours=[])

    # Før DD-hit: OK
    ok, why = pretrade_checks({})
    assert ok, f"Skulle vært OK før DD, fikk: {why}"

    # Delvis tap: fortsatt OK
    update_drawdown(-6.0)
    ok, why = pretrade_checks({})
    assert ok, f"Skulle fortsatt vært OK, fikk: {why}"

    # Hit hard dagstap: skal blokke (day_loss_hard eller cooldown)
    update_drawdown(-5.0)  # sum -11
    ok, why = pretrade_checks({})
    assert not ok and why in ("day_loss_hard", "cooldown"), f"Forventet blokk, fikk: {ok},{why}"

    # Ny dag: nullstill PnL og cooldown -> skal være OK
    reset_daily()
    ok, why = pretrade_checks({})
    assert ok, f"Skulle være OK etter reset_daily, fikk: {why}"

    print("guards selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
