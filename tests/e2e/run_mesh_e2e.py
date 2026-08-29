#!/usr/bin/env python3
"""
Master E2E Test Runner for Lauburu Mesh Ecosystem & Qwen Math Specialist.
========================================================================
Executes and reports on the 4-tier Opaque-Box E2E Testing Framework:
- Tier 1: Feature Coverage (R1 WireGuard/Speedify, R2 Matrix Benchmarks, R3 Qwen Math)
- Tier 2: Boundary Value Analysis & Corner Cases
- Tier 3: Pairwise Cross-Feature Combinations
- Tier 4: Real-World Workload Scenarios

Usage:
  python3 tests/e2e/run_mesh_e2e.py --all
  python3 tests/e2e/run_mesh_e2e.py --tier 1
  python3 tests/e2e/run_mesh_e2e.py --all --json-output reports/mesh_e2e_report.json
"""

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
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(TESTS_E2E_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_E2E_DIR))

from test_mesh_routing_and_benchmarks_e2e import (
    TestTier1FeatureCoverage,
    TestTier2BoundaryCornerCases,
    TestTier3CrossFeatureCombinations,
    TestTier4RealWorldScenarios
)


def create_tier_suite(tier: str) -> unittest.TestSuite:
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    
    if tier in ['1', 'tier1', 'all']:
        suite.addTests(loader.loadTestsFromTestCase(TestTier1FeatureCoverage))
    if tier in ['2', 'tier2', 'all']:
        suite.addTests(loader.loadTestsFromTestCase(TestTier2BoundaryCornerCases))
    if tier in ['3', 'tier3', 'all']:
        suite.addTests(loader.loadTestsFromTestCase(TestTier3CrossFeatureCombinations))
    if tier in ['4', 'tier4', 'all']:
        suite.addTests(loader.loadTestsFromTestCase(TestTier4RealWorldScenarios))
        
    return suite


def main():
    parser = argparse.ArgumentParser(description='Lauburu Mesh 4-Tier E2E Master Test Runner')
    parser.add_argument('--tier', choices=['1', '2', '3', '4', 'all'], default='all',
                        help='Tier to execute (1, 2, 3, 4, or all)')
    parser.add_argument('--all', action='store_true', help='Run all tiers')
    parser.add_argument('--json-output', type=str, default=None,
                        help='Path to export JSON test execution report')
    parser.add_argument('-v', '--verbose', action='store_true', default=True,
                        help='Verbose test output')
    args = parser.parse_args()

    tier_selection = 'all' if args.all else args.tier
    suite = create_tier_suite(tier_selection)
    
    print('=' * 80)
    print('🌐 LAUBURU MESH & QWEN MATH — 4-TIER E2E MASTER TEST RUNNER')
    print('=' * 80)
    print(f'Timestamp:       {datetime.now().isoformat()}')
    print(f'Selected Tier:   Tier {tier_selection.upper()}')
    print(f'Test Count:      {suite.countTestCases()} total test cases')
    print('=' * 80)
    
    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
    result = runner.run(suite)
    duration = time.time() - start_time
    
    total_ran = result.testsRun
    failures_count = len(result.failures)
    errors_count = len(result.errors)
    skipped_count = len(result.skipped)
    passed_count = total_ran - failures_count - errors_count - skipped_count
    pass_rate = (passed_count / max(1, (total_ran - skipped_count))) * 100.0
    
    print('=' * 80)
    print('📊 E2E EXECUTION SUMMARY')
    print('=' * 80)
    print(f'Total Tests Executed: {total_ran}')
    print(f'Passed:               {passed_count} ({pass_rate:.1f}%)')
    print(f'Failures:             {failures_count}')
    print(f'Errors:               {errors_count}')
    print(f'Skipped:              {skipped_count}')
    print(f'Execution Time:       {duration:.3f}s')
    print('=' * 80)
    
    if args.json_output:
        out_path = Path(args.json_output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "target": "Lauburu Mesh Ecosystem (R1, R2, R3)",
            "selected_tier": tier_selection,
            "total_executed": total_ran,
            "passed": passed_count,
            "failed": failures_count,
            "errors": errors_count,
            "skipped": skipped_count,
            "pass_rate_pct": round(pass_rate, 2),
            "duration_sec": round(duration, 3),
            "failures": [{"test": str(f[0]), "error": str(f[1])} for f in result.failures],
            "errors_detail": [{"test": str(e[0]), "error": str(e[1])} for e in result.errors],
            "status": "PASSED" if failures_count == 0 and errors_count == 0 else "FAILED"
        }
        with open(out_path, "w") as f:
            json.dump(report_data, f, indent=2)
        print(f'Exported JSON report to {out_path}')
        
    sys.exit(0 if failures_count == 0 and errors_count == 0 else 1)


if __name__ == "__main__":
    main()
