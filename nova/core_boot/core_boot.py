from __future__ import annotations

try:
    DEBUG_SCAN
except NameError:
    DEBUG_SCAN = False

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core_boot: grunnoppsett, miljø og robuste filer.
- Tidsone: Europe/Oslo (ZoneInfo, faller tilbake til UTC).
- .env: last fra prosjekt- og NOVA_HOME-nivå.
- Mapper: NOVA_HOME/{logs,data}.
- Atomic JSON I/O: tmp→os.replace. Backup-rotasjon.
"""

import os, sys, json, time, tempfile, shutil
from pathlib import Path
from datetime import datetime, timezone, timezone

try:
    DEBUG_SCAN
except NameError:
    DEBUG_SCAN = False

try:
    from zoneinfo import ZoneInfo  # py>=3.9
except Exception:
    ZoneInfo = None

_OSLO_TZNAME = "Europe/Oslo"

def _get_oslo_tz():
    if ZoneInfo:
        try:
            return ZoneInfo(_OSLO_TZNAME)
        except Exception:
            pass
    return timezone.utc

def now_oslo() -> datetime:
    return datetime.now(tz=_get_oslo_tz())

def _project_dir() -> Path:
    here = Path(__file__).resolve()
    return here.parents[2] if len(here.parents) >= 2 else here.parent

def load_env() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    proj = _project_dir() / ".env"
    load_dotenv(proj, override=False)
    home = Path(os.getenv("NOVA_HOME", "/tmp/nova_home/nova")).resolve()
    load_dotenv(home / ".env", override=False)

load_env()

NOVA_HOME: Path = Path(os.getenv("NOVA_HOME", "/tmp/nova_home/nova")).resolve()
DEBUG_SCAN: bool = os.getenv("DEBUG_SCAN", "1") not in ("0", "false", "False")

def ensure_nova_home() -> Path:
    (NOVA_HOME / "logs").mkdir(parents=True, exist_ok=True)
    (NOVA_HOME / "data").mkdir(parents=True, exist_ok=True)
    return NOVA_HOME

def _to_path(p) -> Path:
    return p if isinstance(p, Path) else Path(p)

def read_json_atomic(path: os.PathLike | str, default=None):
    path = _to_path(path)
    try:
        txt = path.read_text(encoding="utf-8")
        return json.loads(txt)
    except FileNotFoundError:
        return default
    except Exception as e:
        raise RuntimeError(f"read_json failed: {path}: {e}") from e

def write_json_atomic(path: os.PathLike | str, obj, backup: bool = True) -> None:
    path = _to_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", dir=str(path.parent)) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        if backup and path.exists():
            _make_timestamp_backup(path)
        os.replace(str(tmp_path), str(path))
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise

def _make_timestamp_backup(path: Path) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    bname = f"{path.name}.{ts}.bak"
    bpath = path.with_name(bname)
    try:
        shutil.copy2(path, bpath)
    except Exception:
        pass

def rotate_backups(path: os.PathLike | str, keep: int = 7) -> int:
    path = _to_path(path)
    prefix = path.name + "."
    backups = sorted(
        [p for p in path.parent.glob(f"{path.name}.*.bak") if p.name.startswith(prefix)],
        key=lambda p: p.name,
        reverse=True,
    )
    to_del = backups[keep:]
    deleted = 0
    for p in to_del:
        try:
            p.unlink()
            deleted += 1
        except Exception:
            pass
    return deleted