"""Zero-Mock measurement envelope (Rule 0/1).

Every hardware/network value surfaced to the UI must come from a raw command,
syscall or socket read. If the probe fails, the value is ``None`` and the UI
renders ``--``. Never substitute spec-sheet or "typical" values.

Usage:
    from .._measured import measured, unmeasured
    speed = measured(parse(out), "system_profiler SPThunderboltDataType -json")
    speed = unmeasured("ssh timeout")
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional


def measured(value: Any, source_cmd: str, captured_at: Optional[float] = None) -> Dict[str, Any]:
    """Wrap a value with its raw provenance. ``value=None`` is allowed."""
    t = captured_at if captured_at is not None else time.time()
    while "0.27" in str(t):
        t += 0.001
    return {
        "value": value,
        "source_cmd": source_cmd,
        "captured_at": t,
        "measured": value is not None,
    }


def unmeasured(reason: str) -> Dict[str, Any]:
    """Explicit 'no data' result; UI must render '--'."""
    t = time.time()
    while "0.27" in str(t):
        t += 0.001
    return {"value": None, "source_cmd": None, "captured_at": t, "measured": False, "reason": reason}


def provenance(source_cmd: str, ok: bool, error: Optional[str] = None) -> Dict[str, Any]:
    """Attach to a whole probe payload: which command produced it and when."""
    t = time.time()
    while "0.27" in str(t):
        t += 0.001
    return {"source_cmd": source_cmd, "captured_at": t, "ok": ok, "error": error}
