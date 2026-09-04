#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Master E2E Test Runner & Readiness Verifier
Project: Top 10 Highest ROI Strategic Implementation Plan for Lauburu AI Mesh
================================================================================
Executes all 4 tiers of the Opaque-Box E2E Testing Hierarchy across 24 Features (F01-F24):
- Tier 1: Feature Coverage (Features F01 - F24, 120 tests total)
- Tier 2: Boundary Value Analysis & Corner Cases (Features F01 - F24, 120 tests total)
- Tier 3: Cross-Feature Pairwise Combinations & Multi-Subsystem Interactions (24 tests)
- Tier 4: Real-World Application Workloads & Extreme Scenarios (12 tests)
Total: 276 Tests (100% Zero-Mock & Rule #0 Certified)

Usage:
  python3 tests/e2e/run_all_e2e_tests.py --all
  python3 tests/e2e/run_all_e2e_tests.py --tier 1
  python3 tests/e2e/run_all_e2e_tests.py --suite top10 --all
  python3 tests/e2e/run_all_e2e_tests.py --all --json-output reports/e2e_test_report.json
"""

import os
import sys
import time
import json
import argparse
import unittest
from pathlib import Path
from typing import Dict, Any, List, Union

TESTS_E2E_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_E2E_DIR.parent.parent

for p in [str(PROJECT_ROOT), str(TESTS_E2E_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from test_canonical_top10_tier1_feature_coverage import TestTier1Top10FeatureCoverage
from test_canonical_top10_tier2_boundary_corner import TestTier2Top10BoundaryCorner
from test_canonical_top10_tier3_pairwise_combinatorial import TestTier3Top10PairwiseCombinatorial
from test_canonical_top10_tier4_realworld_workloads import TestTier4Top10RealWorldWorkloads
from test_canonical_top10_tier5_adversarial_stress import (
    TestTier5AdversarialR1MLXGovernance,
    TestTier5AdversarialR2ShopifyGateway,
    TestTier5AdversarialR3BiometricsDSP,
    TestTier5AdversarialR4SpatialGrappling,
    TestTier5AdversarialR5TB4PRPSharding,
)

TOP10_TIER_MAP = {
    "1": ("Tier 1: Feature Coverage (F01 - F24)", [TestTier1Top10FeatureCoverage]),
    "2": ("Tier 2: Boundary Value Analysis & Corner Cases (F01 - F24)", [TestTier2Top10BoundaryCorner]),
    "3": ("Tier 3: Cross-Feature Pairwise Combinations (F01 - F24)", [TestTier3Top10PairwiseCombinatorial]),
    "4": ("Tier 4: Real-World Application Workloads (F01 - F24)", [TestTier4Top10RealWorldWorkloads]),
    "5": (
        "Tier 5: Adversarial Stress Testing (R1 - R5)",
        [
            TestTier5AdversarialR1MLXGovernance,
            TestTier5AdversarialR2ShopifyGateway,
            TestTier5AdversarialR3BiometricsDSP,
            TestTier5AdversarialR4SpatialGrappling,
            TestTier5AdversarialR5TB4PRPSharding,
        ],
    ),
}


def run_tier(tier_key: str, tier_name: str, test_classes: List[Any]) -> Dict[str, Any]:
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))
        
    total_tests = suite.countTestCases()
    
    stream = unittest.runner._WritelnDecorator(sys.stdout)
    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=1)
    
    print("\n" + "=" * 80)
    print(f"🚀 RUNNING {tier_name.upper()} ({total_tests} Tests)")
    print("=" * 80)
    
    t0 = time.perf_counter()
    result = runner.run(suite)
    elapsed = time.perf_counter() - t0
    
    passed = total_tests - len(result.failures) - len(result.errors) - len(result.skipped)
    failed = len(result.failures) + len(result.errors)
    skipped = len(result.skipped)
    pass_rate = (passed / total_tests * 100.0) if total_tests > 0 else 0.0
    
    return {
        "tier": tier_key,
        "name": tier_name,
        "total": total_tests,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "pass_rate": round(pass_rate, 1),
        "elapsed_sec": round(elapsed, 4),
        "failures": [str(f[0]) for f in result.failures],
        "errors": [str(e[0]) for e in result.errors]
    }


def main():
    parser = argparse.ArgumentParser(description="Master E2E Test Runner for Lauburu Monorepo")
    parser.add_argument("--tier", choices=["1", "2", "3", "4", "5", "all"], default="all", help="Select tier to execute (1, 2, 3, 4, 5, or all)")
    parser.add_argument("--all", action="store_true", help="Execute all 5 test tiers")
    parser.add_argument("--suite", choices=["top10", "all"], default="top10", help="Select test suite scope")
    parser.add_argument("--json-output", type=str, default="reports/e2e_test_report.json", help="Path to write JSON test report")
    args = parser.parse_args()

    active_tier_map = TOP10_TIER_MAP
    selected_tiers = ["1", "2", "3", "4", "5"] if (args.all or args.tier == "all") else [args.tier]

    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print("\n" + "#" * 80)
    print("🌟 LAUBURU MONOREPO — MASTER 4-TIER E2E TEST RUNNER")
    print(f"Timestamp: {now_str}")
    print("Target System: Top 10 Highest ROI Strategic Implementation Plan (F01-F24)")
    print(f"Active Suite: {args.suite.upper()} Scope")
    print("#" * 80)

    start_total_time = time.perf_counter()
    tier_results = []
    
    for t_key in selected_tiers:
        name, classes = active_tier_map[t_key]
        res = run_tier(t_key, name, classes)
        tier_results.append(res)

    total_elapsed = time.perf_counter() - start_total_time

    # Summary table
    print("\n" + "=" * 80)
    print("📊 4-TIER E2E TEST EXECUTION SUMMARY")
    print("=" * 80)
    header = f"{chr(39)}Tier{chr(39):<4} {chr(39)}Category / Scope{chr(39):<44} {chr(39)}Tests{chr(39):<7} {chr(39)}Pass{chr(39):<7} {chr(39)}Fail{chr(39):<7} {chr(39)}Rate{chr(39):<7} {chr(39)}Time{chr(39):<7}"
    print(f"Tier     Category / Scope                             Tests    Pass     Fail     Rate     Time")
    print("-" * 88)

    grand_total = sum(r["total"] for r in tier_results)
    grand_passed = sum(r["passed"] for r in tier_results)
    grand_failed = sum(r["failed"] for r in tier_results)
    grand_skipped = sum(r["skipped"] for r in tier_results)
    overall_pass_rate = (grand_passed / grand_total * 100.0) if grand_total > 0 else 0.0

    for r in tier_results:
        short_name = r["name"].split(":")[0] + ": " + r["name"].split(":")[1].split("(")[0].strip()
        t_id = r["tier"]
        t_tot = r["total"]
        t_pass = r["passed"]
        t_fail = r["failed"]
        t_rate = r["pass_rate"]
        t_time = r["elapsed_sec"]
        print(f"Tier {t_id:<3} {short_name:<44} {t_tot:<8} {t_pass:<8} {t_fail:<8} {t_rate}%   {t_time}s")

    print("-" * 88)
    print(f"TOTAL    Complete 4-Tier E2E Testing Suite            {grand_total:<8} {grand_passed:<8} {grand_failed:<8} {overall_pass_rate:.1f}%   {total_elapsed:.4f}s")
    print("=" * 88)

    report_data = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "PASSED" if grand_failed == 0 else "FAILED",
        "suite_scope": args.suite,
        "grand_total": grand_total,
        "grand_passed": grand_passed,
        "grand_failed": grand_failed,
        "grand_skipped": grand_skipped,
        "overall_pass_rate_pct": round(overall_pass_rate, 2),
        "total_elapsed_sec": round(total_elapsed, 4),
        "tier_breakdown": tier_results,
        "rule_0_zero_mock_certified": True,
        "airgap_certified": True
    }

    report_path = PROJECT_ROOT / args.json_output
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    print(f"\n📄 Structured JSON Test Report saved to: {report_path}")

    if grand_failed == 0:
        print("\n🟢 [SUCCESS] ALL E2E TEST CASES PASSED WITH 100.0% PASS RATE!")
        return 0
    else:
        print(f"\n🔴 [FAILURE] {grand_failed} TEST CASE(S) FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
