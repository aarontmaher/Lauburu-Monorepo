#!/usr/bin/env python3
"""
NotebookLM & Gemini Spark Browser & Staging Bridge
===================================================
Subsystem: 06_scripts_and_tooling/
Automates staging of compiled knowledge source bundles, manages Google Drive
synchronization triggers, and controls browser session initialization across
macOS host and mesh peripheral nodes (MacBook Air).
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
COMPILER_SCRIPT = REPO_ROOT / "04_data_and_memory" / "notebooklm_knowledge_compiler.py"
SOURCES_DIR = REPO_ROOT / "04_data_and_memory" / "notebooklm_sources"
MBA_HOST = "macbook-air"
MBA_USER = "aaronmaher"


class NotebookLMChromeBridge:
    """Coordinates local browser and cross-node staging for NotebookLM and Gemini Spark."""

    def __init__(self):
        self.sources_dir = SOURCES_DIR

    def compile_sources(self) -> None:
        """Executes the knowledge compiler to produce up-to-date source bundles."""
        print("🔨 Compiling canonical knowledge source bundles...")
        subprocess.run([sys.executable, str(COMPILER_SCRIPT)], check=True)

    def stage_local_desktop(self) -> Path:
        """Copies the primary master context pack to the host Desktop."""
        master_src = REPO_ROOT / "07_docs_and_architecture" / "GEMINI_NOTEBOOK_AND_SPARK_CANONICAL_CONTEXT_PACK.md"
        desktop_dst = Path(os.path.expanduser("~/Desktop")) / master_src.name
        if master_src.exists():
            shutil.copy2(master_src, desktop_dst)
            print(f"✅ Staged master context pack to Local Desktop: {desktop_dst}")
        return desktop_dst

    def stage_macbook_air(self) -> bool:
        """Transfers compiled sources to the MacBook Air node over Tailscale SSH."""
        print(f"📡 Syncing knowledge bundles to MacBook Air ({MBA_HOST})...")
        master_src = REPO_ROOT / "07_docs_and_architecture" / "GEMINI_NOTEBOOK_AND_SPARK_CANONICAL_CONTEXT_PACK.md"
        try:
            # Stage master pack
            subprocess.run(
                ["scp", "-o", "ConnectTimeout=4", str(master_src), f"{MBA_HOST}:/Users/{MBA_USER}/Desktop/"],
                capture_output=True, timeout=10.0, check=True
            )
            # Stage all 5 sources to MBA Documents/notebooklm_sources/
            subprocess.run(
                ["ssh", "-o", "ConnectTimeout=4", MBA_HOST, f"mkdir -p /Users/{MBA_USER}/Documents/notebooklm_sources"],
                capture_output=True, timeout=10.0, check=True
            )
            subprocess.run(
                f"scp -o ConnectTimeout=4 {self.sources_dir}/*.md {MBA_HOST}:/Users/{MBA_USER}/Documents/notebooklm_sources/",
                shell=True, capture_output=True, timeout=15.0, check=True
            )
            print("✅ Successfully staged all source bundles on MacBook Air.")
            return True
        except Exception as e:
            print(f"⚠️ MacBook Air sync skipped or offline: {e}")
            return False

    def open_browser_sessions(self, target: str = "both") -> None:
        """Opens NotebookLM and Gemini Spark in Google Chrome / Safari."""
        urls = ["https://notebooklm.google.com", "https://gemini.google.com"]
        if target in ("local", "both"):
            print("🌐 Opening NotebookLM & Gemini Spark on Local Host...")
            for u in urls:
                subprocess.run(["open", "-a", "Google Chrome", u], capture_output=True)

        if target in ("mba", "both"):
            print(f"🌐 Opening NotebookLM & Gemini Spark on MacBook Air ({MBA_HOST})...")
            try:
                subprocess.run(
                    ["ssh", "-o", "ConnectTimeout=4", MBA_HOST, "open 'https://notebooklm.google.com' && open 'https://gemini.google.com'"],
                    capture_output=True, timeout=10.0
                )
            except Exception:
                pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NotebookLM & Gemini Spark Chrome Bridge")
    parser.add_argument("--compile", action="store_true", help="Recompile all source bundles")
    parser.add_argument("--stage", action="store_true", help="Stage files on local Desktop and MacBook Air")
    parser.add_argument("--open", action="store_true", help="Open browser sessions to NotebookLM & Gemini")
    parser.add_argument("--all", action="store_true", help="Execute complete compilation, staging, and browser launch")
    args = parser.parse_args()

    bridge = NotebookLMChromeBridge()
    if args.all or (not args.compile and not args.stage and not args.open):
        bridge.compile_sources()
        bridge.stage_local_desktop()
        bridge.stage_macbook_air()
        bridge.open_browser_sessions()
    else:
        if args.compile:
            bridge.compile_sources()
        if args.stage:
            bridge.stage_local_desktop()
            bridge.stage_macbook_air()
        if args.open:
            bridge.open_browser_sessions()
