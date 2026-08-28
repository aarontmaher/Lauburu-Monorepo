#!/usr/bin/env python3
"""
Unified E2E Test Runner
Continuous AI Arena & Lauburu Monorepo
======================================
Executes and reports on the 5-tier E2E testing framework:
- Tier 1: Feature Coverage (Category-Partition Testing across F1 - F9)
- Tier 2: Boundary Value Analysis & Corner Cases
- Tier 3: Pairwise Cross-Feature Combinations
- Tier 4: Real-World Workload Scenarios
- Tier 5: Adversarial Coverage Hardening (Extreme Concurrency, Byzantine Outputs, Socket Recovery, Tri-Vault Persistence)

Usage:
  python3 tests/e2e/run_all_e2e.py --all
  python3 tests/e2e/run_all_e2e.py --tier 5
  python3 tests/e2e/run_all_e2e.py --all --json-output reports/continuous_arena_e2e_report.json
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
sys.path.insert(0, str(TESTS_E2E_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

# Continuous AI Arena 5-Tier Test Suites
from test_continuous_ai_arena_4tier import (
    TestTier1FeatureCoverage as ArenaTier1Coverage,
    TestTier2BoundaryCornerCases as ArenaTier2Boundaries,
    TestTier3CrossFeatureCombinations as ArenaTier3Combinations,
    TestTier4RealWorldScenarios as ArenaTier4Workloads
)
from test_continuous_ai_arena_tier5_adversarial import (
    TestTier5AdversarialHardening as ArenaTier5Adversarial
)


def create_tier_suite(tier: str) -> unittest.TestSuite:
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    
    if tier in ['1', 'tier1', 'all']:
        suite.addTests(loader.loadTestsFromTestCase(ArenaTier1Coverage))
    if tier in ['2', 'tier2', 'all']:
        suite.addTests(loader.loadTestsFromTestCase(ArenaTier2Boundaries))
    if tier in ['3', 'tier3', 'all']:
        suite.addTests(loader.loadTestsFromTestCase(ArenaTier3Combinations))
    if tier in ['4', 'tier4', 'all']:
        suite.addTests(loader.loadTestsFromTestCase(ArenaTier4Workloads))
    if tier in ['5', 'tier5', 'all']:
        suite.addTests(loader.loadTestsFromTestCase(ArenaTier5Adversarial))
        
    return suite


def main():
    parser = argparse.ArgumentParser(description='Continuous AI Arena 5-Tier E2E Test Runner')
    parser.add_argument('--tier', choices=['1', '2', '3', '4', '5', 'all'], default='all',
                        help='Tier to execute (1, 2, 3, 4, 5, or all)')
    parser.add_argument('--all', action='store_true', help='Run all tiers')
    parser.add_argument('--json-output', type=str, default=None,
                        help='Path to export JSON test execution report')
    parser.add_argument('-v', '--verbose', action='store_true', default=True,
                        help='Verbose test output')
    args = parser.parse_args()

    tier_selection = 'all' if args.all else args.tier
    suite = create_tier_suite(tier_selection)
    
    print('=' * 80)
    print('⚔️  CONTINUOUS AI ARENA — 5-TIER E2E MASTER TEST RUNNER')
    print('=' * 80)
    print(f'Timestamp:       {datetime.now().isoformat()}')
    print(f'Selected Tier:   Tier {tier_selection.upper()}')
    print(f'Test Count:      {suite.countTestCases()} total test cases')
    print('-' * 80)
    
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
    print(f'Passed:               {passed_count}')
    print(f'Failures:             {failures_count}')
    print(f'Errors:               {errors_count}')
    print(f'Skipped:              {skipped_count}')
    print(f'Pass Rate:            {pass_rate:.2f}%')
    print(f'Duration:             {duration:.3f}s')
    print('=' * 80)
    
    if args.json_output:
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'tier': tier_selection,
            'total_tests': total_ran,
            'passed': passed_count,
            'failures': failures_count,
            'errors': errors_count,
            'skipped': skipped_count,
            'pass_rate_percent': round(pass_rate, 2),
            'duration_seconds': round(duration, 3),
            'status': 'PASSED' if (failures_count == 0 and errors_count == 0) else 'FAILED',
            'failures_details': [{'test': str(f[0]), 'trace': f[1]} for f in result.failures],
            'errors_details': [{'test': str(e[0]), 'trace': e[1]} for e in result.errors]
        }
        out_path = Path(args.json_output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2)
        print(f'📄 JSON test report written to: {out_path}')

    sys.exit(0 if (failures_count == 0 and errors_count == 0) else 1)


if __name__ == '__main__':
    main()
