#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
import ast
from pathlib import Path
from typing import List, Tuple

# Enkle regler: numpy as np, pandas as pd. Ingen em-dashes i kilde.
_RULES = {
    "numpy": "np",
    "pandas": "pd",
}

def _scan_py(root: Path) -> List[Path]:
    return [p for p in root.rglob("*.py") if "/.venv/" not in str(p)]

def _check_import_aliases(tree: ast.AST) -> List[str]:
    errs: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                want = _RULES.get(n.name)
                if want and n.asname != want:
                    errs.append(f"import {n.name} as {want} expected")
        if isinstance(node, ast.ImportFrom):
            # OK å bruke from x import y
            pass
    return errs

def _check_bad_chars(code: str) -> List[str]:
    return ["em-dash found"] if "—" in code else []

def _find_dupe_symbols(root: Path, suspects: Tuple[str, ...]) -> List[str]:
    """Sjekk at kjente duplikate navn ikke finnes i flere filer."""
    hits = {s: [] for s in suspects}
    for p in _scan_py(root):
        try:
            src = p.read_text(encoding="utf-8")
            for s in suspects:
                if f"def {s}(" in src or f"class {s}(" in src:
                    hits[s].append(str(p))
        except Exception:
            continue
    errs = []
    for s, files in hits.items():
        if len(files) > 1:
            errs.append(f"duplicate symbol {s}: {files}")
    return errs

def run_lint_checks(project_root: Path) -> List[str]:
    errs: List[str] = []
    for p in _scan_py(project_root):
        try:
            src = p.read_text(encoding="utf-8")
            errs.extend(_check_bad_chars(src))
            tree = ast.parse(src)
            errs.extend(_check_import_aliases(tree))
        except SyntaxError as e:
            errs.append(f"syntax error {p}: {e}")
        except Exception as e:
            errs.append(f"read error {p}: {e}")
    # kjente historie-duplikater vi vil unngå
    errs.extend(_find_dupe_symbols(project_root, (
        "_pick_backtest_symbols",
        "_run_backtest_async",
        "dynamic_base_usdt",
        "compute_stop_floor",
    )))
    return errs