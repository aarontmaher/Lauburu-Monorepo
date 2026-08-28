#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Canonical Port Web-TUI Server (textual-web bridge)
Version: 1.0.0-CANONICAL

Serves the Canonical Port TUI directly over WebSockets and HTTP via textual-web,
allowing browser-based access on http://localhost:8088 without needing Next.js or Flutter.
"""

import os
import sys
import subprocess
from pathlib import Path

MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
TUI_DIR = MONOREPO_ROOT / "01_apps/canonical_port/tui"
APP_PATH = TUI_DIR / "canonical_tui.py"

def main():
    print("=" * 80)
    print("🌐 LAUBURU CANONICAL WEB-TUI BRIDGE")
    print("=" * 80)
    print(f"Target TUI Application: {APP_PATH}")
    print("Starting Web-TUI server on http://127.0.0.1:8088 ...")
    
    # Run textual-web or fallback python run
    cmd = [
        sys.executable, "-m", "textual", "serve",
        str(APP_PATH),
        "-p", "8088",
        "-h", "0.0.0.0"
    ]
    
    try:
        subprocess.run(cmd, cwd=str(TUI_DIR))
    except KeyboardInterrupt:
        print("\nWeb-TUI stopped.")
    except Exception as e:
        print(f"Error starting Web-TUI: {e}")

if __name__ == "__main__":
    main()
"""
