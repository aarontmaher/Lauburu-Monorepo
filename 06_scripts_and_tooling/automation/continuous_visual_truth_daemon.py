#!/usr/bin/env python3
"""
Continuous Screen Lens Visual Truth Inspector Daemon
Subsystem: 06_scripts_and_tooling/automation
Governed by: Rule #0 (Zero-Mock), Rule #7 (Screen Lens Telemetry), Rule #9 (Background Daemon Governance)

Continuously audits active UI dashboards (Port 4000 Console Hub), captures
visual proofs via Playwright, validates zero mock data, and appends empirical
observations to Obsidian Tri-Vault (SCREEN_LENS_LIVE_OBSERVATIONS.md).
"""
import os
import sys
import time
import json
from pathlib import Path
from playwright_truth_auditor import run_visual_truth_audit

OBSIDIAN_OBSERVATIONS = Path("/Volumes/Lauburu-Monorepo/obsidian_vault/APPS_AND_FEATURES/SCREEN_LENS_LIVE_OBSERVATIONS.md")
CYCLE_INTERVAL_SECONDS = 600  # Run every 10 minutes

def append_to_obsidian(results: dict):
    if not OBSIDIAN_OBSERVATIONS.parent.exists():
        OBSIDIAN_OBSERVATIONS.parent.mkdir(parents=True, exist_ok=True)

    timestamp = results.get("timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    url = results.get("url", "http://127.0.0.1:4000")
    title = results.get("page_title", "Console Lauburu")
    tabs = len(results.get("interactive_tabs", []))
    clicked = len(results.get("clicked_elements", []))
    console_errors = len(results.get("console_errors", []))
    failed_reqs = len(results.get("failed_requests", []))
    zero_mock = "PASSED (Zero-Mock Verified)" if not results.get("zero_mock_compliance", {}).get("has_simulated_data") else "FAILED"
    shots_count = len(results.get("screenshots", []))

    entry = (
        f"\n### [{timestamp}] Screen Lens Sovereign Visual Truth Inspection\n"
        f"- **Target**: `{url}` (`{title}`)\n"
        f"- **Interactive Elements Audited**: `{tabs} tabs / {clicked} click-throughs executed`\n"
        f"- **Console Health**: `Errors: {console_errors}` | `Failed Network Requests: {failed_reqs}`\n"
        f"- **Zero-Mock Status**: `{zero_mock}`\n"
        f"- **Visual Proofs**: `{shots_count} full-page screenshots recorded to Tri-Vault`\n"
    )

    try:
        with open(OBSIDIAN_OBSERVATIONS, "a", encoding="utf-8") as f:
            f.write(entry)
        print(f"[{timestamp}] Appended visual audit entry to Obsidian Vault.")
    except Exception as e:
        print(f"[{timestamp}] Failed to append to Obsidian: {e}", file=sys.stderr)

def main():
    print("🚀 Starting Continuous Screen Lens Visual Truth Inspector Daemon (Pillar IV)...")
    while True:
        try:
            print(f"[{time.strftime('%H:%M:%S')}] Executing Playwright Visual Truth Audit...")
            results = run_visual_truth_audit("http://127.0.0.1:4000")
            append_to_obsidian(results)
        except Exception as e:
            print(f"Audit cycle error: {e}", file=sys.stderr)

        time.sleep(CYCLE_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
