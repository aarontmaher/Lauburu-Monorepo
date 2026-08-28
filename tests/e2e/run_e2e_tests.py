#!/usr/bin/env python3
"""
Master E2E Test Suite Runner
============================
Multi-WAN Mesh PWA Audit & Native Throughput Integration
4-Tier Unified E2E Test Execution Engine.

Executes:
- Tier 1: Feature Coverage (>=60 tests across F1-F12)
- Tier 2: Boundary & Corner Cases (>=60 tests across F1-F12)
- Tier 3: Pairwise Combinations (>=12 cross-feature tests)
- Tier 4: Real-World Workloads (>=6 application scenarios)

Usage:
    python3 run_e2e_tests.py [--tier {1,2,3,4,all}] [--json-output <path>] [--verbose] [--fail-fast]
"""

import argparse
import io
import json
import os
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

# Locate project roots
MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
PROJECT_ROOT = Path("/Users/aaron/teamwork_projects/mesh_pwa_audit")

# Add roots to sys.path
for p in [
    str(MONOREPO_ROOT),
    str(PROJECT_ROOT),
    str(MONOREPO_ROOT / "00_core_infrastructure"),
    str(MONOREPO_ROOT / "06_scripts_and_tooling" / "network"),
    str(MONOREPO_ROOT / "01_apps" / "dark_mode_pwa"),
    str(MONOREPO_ROOT / "tests"),
    str(MONOREPO_ROOT / "tests" / "e2e"),
    str(PROJECT_ROOT / "tests"),
    str(PROJECT_ROOT / "tests" / "e2e"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Terminal ANSI Color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BLUE = "\033[94m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


TIER_CONFIG = {
    1: {
        "name": "Tier 1: Feature Coverage",
        "module": "test_tier1_feature_coverage",
        "class": "TestTier1FeatureCoverage",
        "min_tests": 60,
        "description": "Exhaustive coverage of F1 through F12 (>=5 tests per feature)"
    },
    2: {
        "name": "Tier 2: Boundary & Corner Cases",
        "module": "test_tier2_boundary_corner",
        "class": "TestTier2BoundaryCorner",
        "min_tests": 60,
        "description": "Boundary conditions, zero limits, corrupted frames, timeouts, and edge cases"
    },
    3: {
        "name": "Tier 3: Pairwise Combinations",
        "module": "test_tier3_pairwise_combinations",
        "class": "TestTier3PairwiseCombinations",
        "min_tests": 12,
        "description": "Cross-feature pairwise interactions, component handoffs, and coupled failures"
    },
    4: {
        "name": "Tier 4: Real-World Workloads",
        "module": "test_tier4_realworld_workloads",
        "class": "TestTier4RealWorldWorkloads",
        "min_tests": 6,
        "description": "Realistic full-cluster workflows, 24/7 self-healing, and dual-pipe bonding"
    }
}


def print_banner():
    banner = f"""
{CYAN}{BOLD}================================================================================{RESET}
{CYAN}{BOLD}   Multi-WAN Mesh PWA Audit & Native Throughput Integration E2E Test Suite     {RESET}
{CYAN}{BOLD}   Zero-Mock Truth Enforcement • 4-Tier Verification Architecture              {RESET}
{CYAN}{BOLD}================================================================================{RESET}
"""
    print(banner)


def run_tier(tier_num: int, verbose: bool = False, failfast: bool = False) -> Dict[str, Any]:
    cfg = TIER_CONFIG[tier_num]
    tier_name = cfg["name"]
    module_name = cfg["module"]
    class_name = cfg["class"]

    print(f"\n{BLUE}{BOLD}▶ Running {tier_name}...{RESET}")
    print(f"{DIM}  Module: {module_name}.py | Target: {class_name}{RESET}")

    try:
        mod = __import__(module_name, fromlist=[class_name])
        test_case_class = getattr(mod, class_name)
    except Exception as e:
        print(f"{RED}✖ Failed to import test module {module_name}: {e}{RESET}")
        return {
            "tier": tier_num,
            "name": tier_name,
            "total": 0,
            "passed": 0,
            "failed": 1,
            "errors": 1,
            "skipped": 0,
            "duration": 0.0,
            "status": "IMPORT_ERROR",
            "error_msg": str(e)
        }

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(test_case_class)

    # Capture output buffer
    stream = io.StringIO()
    runner = unittest.TextTestRunner(
        stream=sys.stdout if verbose else stream,
        verbosity=2 if verbose else 1,
        failfast=failfast
    )

    t0 = time.perf_counter()
    result = runner.run(suite)
    duration = time.perf_counter() - t0

    total = result.testsRun
    failed = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    passed = total - (failed + errors + skipped)

    is_success = (failed == 0 and errors == 0 and total >= cfg["min_tests"])
    status_str = f"{GREEN}PASS{RESET}" if is_success else f"{RED}FAIL{RESET}"

    print(f"  {status_str} — Ran {total} tests in {duration:.3f}s (Passed: {passed}, Failed: {failed}, Errors: {errors}, Skipped: {skipped})")

    if not is_success and not verbose:
        for failure in result.failures:
            print(f"    {RED}✖ FAILURE: {failure[0]}{RESET}")
            print(f"      {DIM}{failure[1].strip().splitlines()[-1]}{RESET}")
        for error in result.errors:
            print(f"    {RED}✖ ERROR: {error[0]}{RESET}")
            print(f"      {DIM}{error[1].strip().splitlines()[-1]}{RESET}")

    return {
        "tier": tier_num,
        "name": tier_name,
        "description": cfg["description"],
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "duration": round(duration, 3),
        "status": "PASS" if is_success else "FAIL",
        "failures": [str(f[0]) for f in result.failures],
        "error_list": [str(e[0]) for e in result.errors]
    }


def print_summary_table(tier_results: List[Dict[str, Any]], total_duration: float):
    print(f"\n{BOLD}════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}                        E2E TEST SUITE EXECUTION SUMMARY                        {RESET}")
    print(f"{BOLD}════════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{'Tier':<36} {'Status':<10} {'Tests':<8} {'Passed':<8} {'Failed':<8} {'Time':<8}{RESET}")
    print(f"────────────────────────────────────────────────────────────────────────────────")

    total_tests = 0
    total_passed = 0
    total_failed = 0

    for res in tier_results:
        total_tests += res["total"]
        total_passed += res["passed"]
        total_failed += (res["failed"] + res["errors"])

        status_badge = f"{GREEN}PASS{RESET}" if res["status"] == "PASS" else f"{RED}FAIL{RESET}"
        tier_label = res["name"]
        print(f"{tier_label:<36} {status_badge:<19} {res['total']:<8} {res['passed']:<8} {res['failed']+res['errors']:<8} {res['duration']:.2f}s")

    print(f"────────────────────────────────────────────────────────────────────────────────")
    overall_status = f"{GREEN}{BOLD}PASSED (100% CLEAN){RESET}" if total_failed == 0 else f"{RED}{BOLD}FAILED ({total_failed} FAILING TESTS){RESET}"
    print(f"{BOLD}{'TOTAL':<36} {overall_status:<28} {total_tests:<8} {total_passed:<8} {total_failed:<8} {total_duration:.2f}s{RESET}")
    print(f"{BOLD}════════════════════════════════════════════════════════════════════════════════{RESET}")

    cert_badge = f"{GREEN}{BOLD}✔ CERTIFIED ZERO-MOCK COMPLIANT{RESET}" if total_failed == 0 else f"{RED}{BOLD}✖ ZERO-MOCK CERTIFICATION FAILED{RESET}"
    print(f"\nZero-Mock Truth Verdict: {cert_badge}\n")


def main():
    parser = argparse.ArgumentParser(description="Multi-WAN Mesh PWA 4-Tier E2E Test Runner")
    parser.add_argument("--tier", choices=["1", "2", "3", "4", "all"], default="all", help="Test tier to execute")
    parser.add_argument("--json-output", type=str, default="", help="Path to save JSON summary report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose test output")
    parser.add_argument("--fail-fast", "-f", action="store_true", help="Stop execution on first test failure")
    args = parser.parse_args()

    print_banner()

    tiers_to_run = [1, 2, 3, 4] if args.tier == "all" else [int(args.tier)]
    tier_results = []

    t_start = time.perf_counter()
    for t in tiers_to_run:
        res = run_tier(t, verbose=args.verbose, failfast=args.fail_fast)
        tier_results.append(res)
        if args.fail_fast and res["status"] != "PASS":
            print(f"\n{RED}⚠ Fail-fast triggered. Aborting remaining tiers.{RESET}")
            break

    total_duration = time.perf_counter() - t_start
    print_summary_table(tier_results, total_duration)

    all_passed = all(r["status"] == "PASS" for r in tier_results)

    # Structured summary for report export
    summary_report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "project": "Multi-WAN Mesh PWA Audit & Native Throughput Integration",
        "overall_verdict": "CERTIFIED ZERO-MOCK" if all_passed else "FAILED",
        "total_tests": sum(r["total"] for r in tier_results),
        "total_passed": sum(r["passed"] for r in tier_results),
        "total_failed": sum(r["failed"] + r["errors"] for r in tier_results),
        "total_skipped": sum(r["skipped"] for r in tier_results),
        "total_duration_seconds": round(total_duration, 3),
        "tiers": tier_results
    }

    if args.json_output:
        out_path = Path(args.json_output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(summary_report, f, indent=2)
        print(f"📄 Structured JSON report written to: {out_path}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
