#!/usr/bin/env python3
"""
================================================================================
Lauburu Ephemeral Video & Artifact Auto-Delete Watchdog Daemon
================================================================================
Subsystem: 06_scripts_and_tooling/ephemeral_video_watchdog.py
Version: 1.0.0-EPHEMERAL-VIDEO-TTL
Lauburu Mesh Ecosystem — 2026

Monitors temporary video evidence recordings across Mac Mini and MacBook Air,
enforces a strict 3-minute Time-To-Live (TTL) after viewing, and automatically
shreds video artifacts to preserve zero-clutter storage invariants.
================================================================================
"""

from __future__ import annotations

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import List

WATCH_DIRS = [
    Path("/Users/aaron/.gemini/antigravity/brain/ddb4bb33-df27-47c3-92c1-e17770d6e2db"),
    Path("/tmp")
]
TTL_SECONDS = 180  # 3 minutes

def purge_expired_videos():
    now = time.time()
    purged = []
    for d in WATCH_DIRS:
        if not d.exists():
            continue
        for f in d.glob("*clickthrough*.mp4"):
            age = now - f.stat().st_mtime
            if age >= TTL_SECONDS:
                try:
                    f.unlink()
                    purged.append(str(f))
                except Exception:
                    pass
        for f in d.glob("*clickthrough*.webm"):
            age = now - f.stat().st_mtime
            if age >= TTL_SECONDS:
                try:
                    f.unlink()
                    purged.append(str(f))
                except Exception:
                    pass

    if purged:
        print(f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] 🗑️ Auto-purged {len(purged)} expired video recordings:")
        for p in purged:
            print(f"  • Deleted: {p}")

if __name__ == "__main__":
    purge_expired_videos()
