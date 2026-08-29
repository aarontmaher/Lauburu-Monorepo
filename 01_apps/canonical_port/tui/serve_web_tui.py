#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Canonical Port Web-TUI Server (textual-web bridge)
Version: 1.1.0-CANONICAL

Serves the Canonical Port TUI directly over WebSockets and HTTP via textual-web,
allowing browser-based access on http://localhost:8088 without needing Next.js or Flutter.
"""

import os
import sys
import subprocess
from pathlib import Path

TUI_DIR = Path(__file__).resolve().parent
CONFIG_PATH = TUI_DIR / "textual_web.toml"
VENV_BIN = TUI_DIR.parent / ".venv/bin/textual-web"

def main():
    print("=" * 80)
    print("🌐 LAUBURU CANONICAL WEB-TUI BRIDGE")
    print("=" * 80)
    port = os.environ.get("PORT", "8088")
    print(f"Directory: {TUI_DIR}")
    print(f"Configuration: {CONFIG_PATH}")
    print(f"Starting Web-TUI server on http://0.0.0.0:{port} (Local Mode) ...")
    
    # Determine executable: venv textual-web, system textual-web, or python -m textual_web.cli
    if VENV_BIN.exists() and os.access(VENV_BIN, os.X_OK):
        cmd = [str(VENV_BIN), "-c", str(CONFIG_PATH), "-e", "local"]
    elif subprocess.run(["which", "textual-web"], capture_output=True).returncode == 0:
        cmd = ["textual-web", "-c", str(CONFIG_PATH), "-e", "local"]
    else:
        cmd = [sys.executable, "-m", "textual_web.cli", "-c", str(CONFIG_PATH), "-e", "local"]
    
    try:
        subprocess.run(cmd, cwd=str(TUI_DIR))
    except KeyboardInterrupt:
        print("\nWeb-TUI stopped.")
    except Exception as e:
        print(f"Error starting Web-TUI: {e}")

if __name__ == "__main__":
    main()
