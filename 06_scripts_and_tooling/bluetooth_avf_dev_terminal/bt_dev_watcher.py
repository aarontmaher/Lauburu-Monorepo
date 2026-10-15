#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Live Hot-Reload File & Config Watcher for `tmux --dev` and `zellij --dev`
=========================================================================
Subsystem: 06_scripts_and_tooling/bluetooth_avf_dev_terminal/bt_dev_watcher.py

Runs in the companion watcher pane of `tmux --dev` or `zellij --dev`:
1. Watches `bt_serial_commands.py`, `bt_serial_ui.py`, `bt_serial_state.py`,
   `bt_serial_terminal.py`, `~/.tmux.conf`, and `bt_serial_dev.kdl`.
2. Validates Python AST syntax on every save and prints live diff/reload logs.
3. Automatically runs `tmux source-file ~/.tmux.conf` when `.tmux.conf` changes.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict

SCRIPT_DIR = Path(__file__).resolve().parent
STATE_JSON_PATH = Path("/tmp/bt_serial_live_state.json")


def sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:10]
    except Exception:
        return "----------"


def main() -> int:
    watched = [
        SCRIPT_DIR / "bt_serial_commands.py",
        SCRIPT_DIR / "bt_serial_ui.py",
        SCRIPT_DIR / "bt_serial_terminal.py",
        SCRIPT_DIR / "bt_serial_state.py",
        SCRIPT_DIR / "bt_serial_dev.kdl",
        Path.home() / ".tmux.conf",
    ]

    hashes: Dict[Path, str] = {}
    for p in watched:
        if p.exists():
            hashes[p] = sha256_file(p)

    print("\033[1;36m━━ 🔥 HOT-RELOAD WATCHER (--DEV) ━━\033[0m")
    for p, h in hashes.items():
        print(f" \033[32m•\033[0m {p.name:<22} \033[90m[{h[:8]}]\033[0m")
    print("\033[90m─────────────────────────────────────\033[0m")
    print("\033[33m💡 Save any file or run `bt-patch`!\033[0m")
    sys.stdout.flush()

    last_reload_seen = 0

    try:
        while True:
            for p in watched:
                if not p.exists():
                    continue
                cur_hash = sha256_file(p)
                old_hash = hashes.get(p)
                if old_hash is None:
                    hashes[p] = cur_hash
                    continue
                if cur_hash != old_hash:
                    hashes[p] = cur_hash
                    ts = time.strftime("%H:%M:%S")
                    if p.suffix == ".py":
                        try:
                            src = p.read_text(encoding="utf-8")
                            ast.parse(src, filename=str(p))
                            print(
                                f"\033[1;32m[{ts}] ⚡ {p.name} updated ({old_hash} -> {cur_hash}) | AST Syntax: OK -> Hot-Reload Triggered!\033[0m"
                            )
                        except SyntaxError as se:
                            print(
                                f"\033[1;31m[{ts}] ⚠️  {p.name} Syntax Error at L{se.lineno}:{se.offset}: {se.msg} (Crash Shield Active)\033[0m"
                            )
                    elif p.name == ".tmux.conf" and os.environ.get("TMUX"):
                        subprocess.run(["tmux", "source-file", str(p)], check=False)
                        print(f"\033[1;36m[{ts}] 🔄 Auto-reloaded ~/.tmux.conf into active tmux session!\033[0m")
                    else:
                        print(f"\033[1;35m[{ts}] 📝 {p.name} modified ({old_hash} -> {cur_hash})\033[0m")
                    sys.stdout.flush()

            if STATE_JSON_PATH.exists():
                try:
                    st = json.loads(STATE_JSON_PATH.read_text(encoding="utf-8"))
                    rc = int(st.get("reload_count", 0))
                    if rc > last_reload_seen:
                        last_reload_seen = rc
                        ts = time.strftime("%H:%M:%S")
                        print(
                            f"\033[1;33m[{ts}] ✅ Terminal Confirmed Hot-Reload #{rc} ({st.get('last_reload_file')}) in {st.get('last_reload_ms')}ms\033[0m"
                        )
                        sys.stdout.flush()
                except Exception:
                    pass

            time.sleep(0.25)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
