#!/usr/bin/env python3
"""
================================================================================
TRI-VAULT STORAGE UPGRADES - 4-TIER E2E TEST RUNNER HARNESS
================================================================================
Executes the comprehensive E2E test suite across all 4 tiers:
- Tier 1: Feature Coverage (Daemon, R2 Config, Delta Lake, HF mmap, Obsidian Vectorizer)
- Tier 2: Boundary & Corner Cases (Empty files, missing paths, debouncing, corrupted inputs)
- Tier 3: Cross-Feature Combinations (End-to-end sync, edit invalidation, deletion, concurrency)
- Tier 4: Real-World Scenarios (Full batch sync across all 59 live Obsidian notes)
"""
from __future__ import annotations

import os
import sys
import time
import subprocess
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
PYTHON_EXE = REPO_ROOT.parent / "lora_datasets" / ".venv" / "bin" / "python3"
if not PYTHON_EXE.exists():
    PYTHON_EXE = Path(sys.executable)


def run_tier(tier_num: int, filename: str, description: str) -> bool:
    print(f"\n{'=' * 80}")
    print(f"▶ EXECUTING TIER {tier_num}: {description.upper()}")
    print(f"  Target File: {filename}")
    print(f"{'=' * 80}")

    test_path = SCRIPT_DIR / filename
    start_time = time.time()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)

    proc = subprocess.run(
        [
            str(PYTHON_EXE),
            "-m", "pytest",
            "-v",
            "--tb=short",
            str(test_path)
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=False
    )
    duration = time.time() - start_time
    status = "PASSED" if proc.returncode == 0 else "FAILED"
    print(f"Tier {tier_num} Result: [{status}] (Duration: {duration:.2f}s)")
    return proc.returncode == 0


def main():
    print("""
    ╔═══════════════════════════════════════════════════════════════════════╗
    ║       LAUBURU MONOREPO - TRI-VAULT STORAGE UPGRADES E2E SUITE         ║
    ║               4-Tier Requirement-Driven Test Harness                  ║
    ╚═══════════════════════════════════════════════════════════════════════╝
    """)
    tiers = [
        (1, "test_tier1_features.py", "Feature Coverage & Interface Contracts"),
        (2, "test_tier2_boundaries.py", "Boundary, Corner & Adversarial Cases"),
        (3, "test_tier3_combinations.py", "Cross-Feature End-to-End Combinations"),
        (4, "test_tier4_realworld_scenarios.py", "Real-World 59-Note Live Vault Batch Sync"),
    ]

    results = []
    total_start = time.time()

    for num, fname, desc in tiers:
        success = run_tier(num, fname, desc)
        results.append((num, desc, success))
        if not success:
            print(f"\n❌ Execution halted on Tier {num} failure.")
            break

    total_duration = time.time() - total_start
    all_passed = all(r[2] for r in results) and len(results) == len(tiers)

    print(f"\n{'=' * 80}")
    print("                      E2E TEST EXECUTION SUMMARY                       ")
    print(f"{'=' * 80}")
    for num, desc, success in results:
        status_icon = "✅ PASS" if success else "❌ FAIL"
        print(f"  Tier {num}: {desc:<45} [{status_icon}]")

    print(f"{'=' * 80}")
    print(f"Total Execution Time: {total_duration:.2f}s")
    print(f"Final Suite Status:   {'🎉 ALL 4 TIERS PASSED (100% SUCCESS)' if all_passed else '❌ TEST FAILURES DETECTED'}")
    print(f"{'=' * 80}\n")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
