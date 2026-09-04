#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Master E2E Test Suite Runner
Project: End-to-End Autonomous AI Training, Storage & RAM Mesh Engine
================================================================================
4-Tier Unified Opaque-Box E2E Test Execution Engine:
- Tier 1: Feature Coverage (100 tests across F1-F20, >=5 tests/feature)
- Tier 2: Boundary Value Analysis & Corner Cases (45 tests across F1-F20)
- Tier 3: Cross-Feature Pairwise Combinations (28 interaction tests)
- Tier 4: Real-World Multi-Step Application Scenarios (12 workload scenarios)

Usage:
    python3 tests/e2e/run_e2e_tests.py [--tier {1,2,3,4,all}] [--json-output <path>] [--verbose]
    pytest tests/e2e/ -v
"""

import os
import sys
import time
import json
import argparse
import unittest
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

TESTS_E2E_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_E2E_DIR.parent.parent

for p in [
    str(PROJECT_ROOT),
    str(TESTS_E2E_DIR),
    str(PROJECT_ROOT / "00_core_infrastructure"),
    str(PROJECT_ROOT / "02_ai_models_and_inference"),
    str(PROJECT_ROOT / "02_ai_models_and_inference" / "benchmarks"),
    str(PROJECT_ROOT / "02_ai_models_and_inference" / "sharding_daemon"),
    str(PROJECT_ROOT / "03_biometrics_and_telemetry"),
    str(PROJECT_ROOT / "04_data_and_memory"),
    str(PROJECT_ROOT / "06_scripts_and_tooling"),
    str(PROJECT_ROOT / "06_scripts_and_tooling" / "automation"),
    str(PROJECT_ROOT / "06_scripts_and_tooling" / "canonical_sync_engine"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

from test_tier1_feature_coverage import TestTier1FeatureCoverage
from test_tier2_boundary_corner import TestTier2BoundaryCorner
from test_tier3_cross_feature import TestTier3CrossFeature
from test_tier4_real_world_scenarios import TestTier4RealWorldScenarios


TIER_CONFIG = {
    1: {
        "name": "Tier 1: Comprehensive Feature Coverage (F1-F20)",
        "module": "test_tier1_feature_coverage.py",
        "class": TestTier1FeatureCoverage,
        "target": 100
    },
    2: {
        "name": "Tier 2: Boundary Value Analysis & Corner Cases",
        "module": "test_tier2_boundary_corner.py",
        "class": TestTier2BoundaryCorner,
        "target": 35
    },
    3: {
        "name": "Tier 3: Cross-Feature Pairwise Combinations",
        "module": "test_tier3_cross_feature.py",
        "class": TestTier3CrossFeature,
        "target": 25
    },
    4: {
        "name": "Tier 4: Real-World Application Workload Scenarios",
        "module": "test_tier4_real_world_scenarios.py",
        "class": TestTier4RealWorldScenarios,
        "target": 10
    }
}


def run_e2e_suite(tiers: List[int], verbose: bool = True, json_output_path: Optional[str] = None) -> bool:
    print("=" * 80)
    print("🚀 LAUBURU E2E TEST ENGINE: Autonomous AI Training, Storage & RAM Mesh")
    print("=" * 80)

    overall_start = time.perf_counter()
    results = {}
    total_passed = 0
    total_failed = 0
    total_errors = 0
    total_tests = 0

    for tier_num in tiers:
        cfg = TIER_CONFIG[tier_num]
        print(f"\n📦 Executing {cfg['name']}...")
        suite = unittest.TestLoader().loadTestsFromTestCase(cfg["class"])
        stream = sys.stdout if verbose else open(os.devnull, "w")
        runner = unittest.TextTestRunner(stream=stream, verbosity=2 if verbose else 0)
        
        t0 = time.perf_counter()
        test_result = runner.run(suite)
        elapsed = time.perf_counter() - t0

        passed = test_result.testsRun - len(test_result.failures) - len(test_result.errors)
        failed = len(test_result.failures)
        errors = len(test_result.errors)

        total_passed += passed
        total_failed += failed
        total_errors += errors
        total_tests += test_result.testsRun

        results[f"tier_{tier_num}"] = {
            "name": cfg["name"],
            "tests_run": test_result.testsRun,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "elapsed_sec": round(elapsed, 3),
            "status": "PASSED" if test_result.wasSuccessful() else "FAILED"
        }
        print(f"   -> Result: {passed}/{test_result.testsRun} passed in {elapsed:.2f}s ({'✅ PASS' if test_result.wasSuccessful() else '❌ FAIL'})")

    overall_elapsed = time.perf_counter() - overall_start
    all_success = total_failed == 0 and total_errors == 0

    print("\n" + "=" * 80)
    print(f"🏁 SUMMARY: {total_passed}/{total_tests} tests passed across {len(tiers)} tiers in {overall_elapsed:.2f}s")
    print(f"   Status: {'🎉 100% ALL TESTS PASSED' if all_success else '❌ FAILURES DETECTED'}")
    print("=" * 80)

    if json_output_path:
        report = {
            "project": "End-to-End Autonomous AI Training, Storage & RAM Mesh Engine",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "errors": total_errors,
            "elapsed_sec": round(overall_elapsed, 3),
            "all_passed": all_success,
            "tiers": results
        }
        Path(json_output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(json_output_path).write_text(json.dumps(report, indent=2))
        print(f"📄 Report written to {json_output_path}")

    return all_success


def main():
    parser = argparse.ArgumentParser(description="Run E2E test suites for Lauburu Mesh Engine")
    parser.add_argument("--tier", choices=["1", "2", "3", "4", "all"], default="all", help="Tier to execute")
    parser.add_argument("--json-output", type=str, default=None, help="Path to write JSON test report")
    parser.add_argument("--quiet", action="store_true", help="Quiet output")
    args = parser.parse_args()

    if args.tier == "all":
        tiers = [1, 2, 3, 4]
    else:
        tiers = [int(args.tier)]

    success = run_e2e_suite(tiers=tiers, verbose=not args.quiet, json_output_path=args.json_output)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
