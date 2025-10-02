#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
from nova import paths as NPATH
import base64, json, os, time, hashlib, csv
from typing import Dict, Any, Optional
from pathlib import Path

from nova.core_boot.core_boot import NOVA_HOME, now_oslo
from nova.stateio.stateio import read_json_atomic, write_json_atomic

# -------- Key vault (enkel b64 + checksum; placeholder for ekte KMS) --------

_VAULT = NOVA_HOME / "data" / "keys.json"

def _ensure_dirs():
    (NOVA_HOME / "data").mkdir(parents=True, exist_ok=True)
    (NOVA_HOME / "logs").mkdir(parents=True, exist_ok=True)

def _encode(value: str) -> Dict[str, str]:
    raw = value.encode("utf-8")
    b64 = base64.b64encode(raw).decode("ascii")
    sha = hashlib.sha256(raw).hexdigest()
    return {"b64": b64, "sha256": sha}

def _decode(blob: Dict[str, str]) -> str:
    raw = base64.b64decode(blob["b64"].encode("ascii"))
    sha = hashlib.sha256(raw).hexdigest()
    if sha != blob.get("sha256"):
        raise ValueError("vault integrity check failed")
    return raw.decode("utf-8")

def store_key(name: str, value: str) -> None:
    _ensure_dirs()
    data = read_json_atomic(_VAULT, default={}) or {}
    data[name] = _encode(value)
    write_json_atomic(_VAULT, data, backup=True)

def get_key(name: str) -> Optional[str]:
    data = read_json_atomic(_VAULT, default={}) or {}
    if name not in data:
        return None
    return _decode(data[name])

def rotate_key(name: str, new_value: str) -> None:
    store_key(name, new_value)
    audit_log("key_rotate", {"name": name})

# -------- 2-step confirm (token + rolle + tidsvindu) --------

_CONFIRM_DB = NOVA_HOME / "data" / "confirms.json"

def start_confirm(action: str, *, role: str, ttl_sec: int = 120, meta: Dict[str, Any] | None = None) -> Dict[str, Any]:
    _ensure_dirs()
    db = read_json_atomic(_CONFIRM_DB, default={}) or {}
    tok = hashlib.sha1(f"{action}|{role}|{time.time()}|{os.getpid()}".encode()).hexdigest()[:16]
    rec = {
        "action": action,
        "role": role,
        "token": tok,
        "expires_at": time.time() + ttl_sec,
        "meta": meta or {},
        "created_at": now_oslo().isoformat(),
    }
    db[tok] = rec
    write_json_atomic(_CONFIRM_DB, db, backup=False)
    audit_log("confirm_start", {"action": action, "role": role})
    return rec

def finalize_confirm(token: str, *, role: str) -> Dict[str, Any]:
    db = read_json_atomic(_CONFIRM_DB, default={}) or {}
    rec = db.get(token)
    if not rec:
        return {"ok": False, "why": "not_found"}
    if role != rec["role"]:
        return {"ok": False, "why": "wrong_role"}
    if time.time() > float(rec["expires_at"]):
        return {"ok": False, "why": "expired"}
    # consume
    db.pop(token, None)
    write_json_atomic(_CONFIRM_DB, db, backup=False)
    audit_log("confirm_final", {"action": rec["action"], "role": role})
    return {"ok": True, "action": rec["action"], "meta": rec.get("meta", {})}

# -------- Audit logg (JSONL) --------

_AUDIT = NOVA_HOME / "logs" / "audit.jsonl"

def audit_log(event: str, meta: Dict[str, Any] | None = None) -> None:
    _ensure_dirs()
    rec = {"ts": now_oslo().isoformat(), "event": event, "meta": meta or {}}
    with _AUDIT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# -------- Skatte-/regnskapseksport (CSV) --------

def export_tax_csv(year: int, out_path: Optional[Path] = None) -> Path:
    """
    Leser trades.json og eksporterer enkel CSV for året.
    Kolonner: ts,symbol,side,qty,price,fee_usd,pnl_real
    """
    _ensure_dirs()
    trades_p = NOVA_HOME / "data" / NPATH.TRADES.as_posix()
    trades = read_json_atomic(trades_p, default=[]) or []
    rows = []
    for t in trades:
        ts = str(t.get("ts") or "")
        yr = 0
        try:
            yr = int(ts[:4])
        except Exception:
            pass
        if yr != int(year):
            continue
        rows.append([
            ts,
            t.get("sym") or t.get("symbol") or "",
            t.get("side",""),
            float(t.get("qty", 0.0) or 0.0),
            float(t.get("price", t.get("eff_price", 0.0)) or 0.0),
            float(t.get("fee", t.get("fee_usd", 0.0)) or 0.0),
            float(t.get("pnl_real", 0.0) or 0.0),
        ])
    if out_path is None:
        out_path = NOVA_HOME / "data" / f"tax_export_{year}.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ts","symbol","side","qty","price","fee_usd","pnl_real"])
        for r in rows:
            w.writerow(r)
    audit_log("tax_export", {"year": int(year), "rows": len(rows), "path": str(out_path)})
    return out_path