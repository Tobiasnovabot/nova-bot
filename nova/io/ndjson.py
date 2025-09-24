from __future__ import annotations
import json
from pathlib import Path
from typing import Iterator, Union, TextIO

def read_lines(path: Union[str, Path, TextIO]) -> Iterator[dict]:
    """Les NDJSON trygt. Hopper over blanke linjer og skriver feil til ValueError."""
    if hasattr(path, "read"):
        f = path  # type: ignore
        for ln in f:
            s = ln.strip()
            if not s:
                continue
            yield json.loads(s)
        return
    p = Path(path)
    if not p.exists():
        return
    with p.open("r", encoding="utf-8") as f:
        for ln in f:
            s = ln.strip()
            if not s:
                continue
            yield json.loads(s)
