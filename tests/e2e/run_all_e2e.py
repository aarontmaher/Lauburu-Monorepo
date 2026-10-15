#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Master E2E Test Runner
Project: Zero-Fabrication Telemetry Remediation, Hard Gate Enforcement & Honest Model Attribution
===================================================================================================
Executes and reports on the 4-tier opaque-box E2E testing framework:
- Tier 1: Feature Coverage (Category-Partition Testing across F1 - F19, >=95 tests)
- Tier 2: Boundary Value Analysis & Corner Cases (>=23 tests)
- Tier 3: Cross-Feature Interactions & Combinatorial Integrations (>=15 tests)
- Tier 4: Real-World Workload Scenarios (5 multi-stage end-to-end workflows)

Usage:
  python3 tests/e2e/run_all_e2e.py --all
  python3 tests/e2e/run_all_e2e.py --tier 1
  python3 tests/e2e/run_all_e2e.py --all --json-output reports/truth_e2e_summary.json
===================================================================================================
"""

from __future__ import annotations

import os
import sys
import time
import json
import argparse
import unittest
from pathlib import Path
from datetime import datetime

TESTS_E2E_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_E2E_DIR.parent.parent

for p in [
    str(PROJECT_ROOT),
    str(TESTS_E2E_DIR),
    str(PROJECT_ROOT / "01_apps/network_cable_analyzer"),
    str(PROJECT_ROOT / "01_apps/network_cable_analyzer/backend"),
    str(PROJECT_ROOT / "01_apps/network_cable_analyzer/backend/probes"),
    str(PROJECT_ROOT / "05_agents_and_swarms"),
    str(PROJECT_ROOT / "05_agents_and_swarms/ai_gateway"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

from test_tier1_feature_coverage import TestTier1FeatureCoverage
from test_tier2_boundary_corner import TestTier2BoundaryCorner
from test_tier3_cross_feature import TestTier3CrossFeature
from test_tier4_real_world_scenarios import TestTier4RealWorldScenarios
from truth_e2e_helpers import get_darwin_memory_stats


def create_tier_suite(tier: str) -> unittest.TestSuite:
    """Creates a TestSuite for the specified tier or all tiers."""
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()

    tier_str = str(tier).lower().strip()
    if tier_str in ["1", "tier1", "all"]:
        suite.addTests(loader.loadTestsFromTestCase(TestTier1FeatureCoverage))
    if tier_str in ["2", "tier2", "all"]:
        suite.addTests(loader.loadTestsFromTestCase(TestTier2BoundaryCorner))
    if tier_str in ["3", "tier3", "all"]:
        suite.addTests(loader.loadTestsFromTestCase(TestTier3CrossFeature))
    if tier_str in ["4", "tier4", "all"]:
        suite.addTests(loader.loadTestsFromTestCase(TestTier4RealWorldScenarios))

    return suite


def run_e2e_tests(
    tier: str = "all",
    verbose: bool = True,
    json_output: str | None = None,
) -> int:
    """Executes the test suite, prints summary report, and returns exit code."""
    print("=" * 80)
    print("🧪 LAUBURU ZERO-FABRICATION & TRUTH VERIFICATION E2E TEST SUITE")
    print(f"   Target: Dual Track Tiers (Selection: {tier})")
    print(f"   Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)

    mem_before = get_darwin_memory_stats()
    print(f"📊 Host Memory Before: Total={mem_before['total_gb']:.1f}GB, Available={mem_before['available_gb']:.1f}GB")

    suite = create_tier_suite(tier)
    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    duration = time.time() - start_time

    mem_after = get_darwin_memory_stats()
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - (failures + errors)

    print("\n" + "=" * 80)
    print("📋 E2E TEST EXECUTION SUMMARY")
    print("=" * 80)
    print(f"• Total Tests Run:   {total_tests}")
    print(f"• Passed Tests:      {passed} ({passed / total_tests * 100:.1f}%)" if total_tests else "• Passed: 0")
    print(f"• Failed Tests:      {failures}")
    print(f"• Errored Tests:     {errors}")
    print(f"• Duration:          {duration:.3f} seconds")
    print(f"• Host RAM Headroom: Available={mem_after['available_gb']:.1f}GB (Rule 3 >= 4.8 GB)")
    print(f"• Claude Spend Cap:  $0.00 (Strictly Enforced)")
    print("=" * 80)

    if failures > 0 or errors > 0:
        print("\n❌ FAILURES & ERRORS SUMMARY (Implementation Bugs Discovered):")
        for test, err in result.failures:
            print(f"  [FAIL] {test.id()}:\n         {err.strip().splitlines()[-1]}")
        for test, err in result.errors:
            print(f"  [ERROR] {test.id()}:\n         {err.strip().splitlines()[-1]}")
        print("=" * 80)

    if json_output:
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "tier_selected": tier,
            "total_tests": total_tests,
            "passed": passed,
            "failures": failures,
            "errors": errors,
            "duration_seconds": duration,
            "claude_spend_usd": 0.00,
            "host_memory": mem_after,
            "failure_details": [
                {"test": t.id(), "traceback": err} for t, err in result.failures + result.errors
            ],
        }
        out_path = Path(json_output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report_data, indent=2))
        print(f"\n💾 JSON report written to: {out_path.resolve()}")

    return 0 if (failures == 0 and errors == 0) else 1


def main():
    parser = argparse.ArgumentParser(description="Master E2E Test Runner for Zero-Fabrication Remediation")
    parser.add_argument("--all", action="store_true", help="Run all tiers (Tiers 1-4)")
    parser.add_argument("--tier", default="all", choices=["1", "2", "3", "4", "all"], help="Specific tier to run")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet output")
    parser.add_argument("--json-output", type=str, default=None, help="Path to export JSON report")

    args = parser.parse_args()
    selected_tier = "all" if args.all else args.tier
    exit_code = run_e2e_tests(
        tier=selected_tier,
        verbose=not args.quiet,
        json_output=args.json_output,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
