#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/e2e_generation32/test_runner.py
======================================
Master Test Runner for Generation 32 Opaque-Box E2E Test Suite.

Executes Tiers 1 through 4 across all 9 features:
- Tier 1: Feature Coverage in Isolation (F1 - F9)
- Tier 2: Boundary, Corner Case, & Adversarial Verification
- Tier 3: Cross-Feature Multi-Module Integration
- Tier 4: Real-World Mesh Workloads & Consensus Lifecycles

Features:
- Colorized ANSI console output with execution duration in milliseconds
- Selective tier execution (--tier 1 2 3 4 or --all)
- Feature-specific filtering (--feature F1..F9)
- Machine-readable JSON execution summary export (--json-output <path>)
- Strict process exit code fidelity (0 on 100% pass, 1 on any failure)
"""

import os
import sys
import json
import time
import argparse
import unittest
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# ANSI Escape Sequences
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Test Modules
from tests.e2e_generation32 import (
    tier1_feature_tests,
    tier2_boundary_tests,
    tier3_cross_feature_tests,
    tier4_real_world_tests,
)


class CustomJSONTestResult(unittest.TestResult):
    """Custom TestResult capturing timing, tier breakdowns, and failure details."""

    def __init__(self, verbosity: int = 1):
        super().__init__()
        self.verbosity = verbosity
        self.successes: List[unittest.TestCase] = []
        self.test_timings: Dict[str, float] = {}
        self._start_time: float = 0.0

    def startTest(self, test: unittest.TestCase):
        super().startTest(test)
        self._start_time = time.perf_counter()
        if self.verbosity > 1:
            sys.stdout.write(f"  • {test.id()} ... ")
            sys.stdout.flush()

    def addSuccess(self, test: unittest.TestCase):
        super().addSuccess(test)
        elapsed = time.perf_counter() - self._start_time
        self.test_timings[test.id()] = elapsed
        self.successes.append(test)
        if self.verbosity > 1:
            sys.stdout.write(f"{GREEN}PASS{RESET} ({elapsed*1000:.1f}ms)\n")
        elif self.verbosity == 1:
            sys.stdout.write(f"{GREEN}.{RESET}")
            sys.stdout.flush()

    def addFailure(self, test: unittest.TestCase, err):
        super().addFailure(test, err)
        elapsed = time.perf_counter() - self._start_time
        self.test_timings[test.id()] = elapsed
        if self.verbosity > 1:
            sys.stdout.write(f"{RED}FAIL{RESET} ({elapsed*1000:.1f}ms)\n")
        elif self.verbosity == 1:
            sys.stdout.write(f"{RED}F{RESET}")
            sys.stdout.flush()

    def addError(self, test: unittest.TestCase, err):
        super().addError(test, err)
        elapsed = time.perf_counter() - self._start_time
        self.test_timings[test.id()] = elapsed
        if self.verbosity > 1:
            sys.stdout.write(f"{RED}ERROR{RESET} ({elapsed*1000:.1f}ms)\n")
        elif self.verbosity == 1:
            sys.stdout.write(f"{RED}E{RESET}")
            sys.stdout.flush()

    def addSkip(self, test: unittest.TestCase, reason: str):
        super().addSkip(test, reason)
        if self.verbosity > 1:
            sys.stdout.write(f"{YELLOW}SKIP{RESET} ({reason})\n")
        elif self.verbosity == 1:
            sys.stdout.write(f"{YELLOW}S{RESET}")
            sys.stdout.flush()


def iterate_tests(suite: unittest.TestSuite):
    """Recursively yield individual test cases from a test suite."""
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from iterate_tests(item)
        else:
            yield item


def build_suite(selected_tiers: List[int], feature_filter: Optional[str] = None) -> unittest.TestSuite:
    """Build test suite based on selected tiers and optional feature filter."""
    loader = unittest.defaultTestLoader
    master_suite = unittest.TestSuite()

    tier_modules = {
        1: tier1_feature_tests,
        2: tier2_boundary_tests,
        3: tier3_cross_feature_tests,
        4: tier4_real_world_tests,
    }

    for tier in sorted(selected_tiers):
        if tier not in tier_modules:
            continue
        mod = tier_modules[tier]
        suite = loader.loadTestsFromModule(mod)

        if feature_filter:
            filtered_suite = unittest.TestSuite()
            f_tag = feature_filter.lower()
            for test in iterate_tests(suite):
                test_name = test.id().lower()
                if f"_{f_tag}_" in test_name or f"_{f_tag}" in test_name or f"{f_tag}_" in test_name or f"_{f_tag}" in test.id():
                    filtered_suite.addTest(test)
            master_suite.addTest(filtered_suite)
        else:
            master_suite.addTest(suite)

    return master_suite


def run_tests(
    selected_tiers: List[int],
    feature_filter: Optional[str] = None,
    verbosity: int = 1,
    json_output_path: Optional[str] = None,
) -> int:
    """Execute tests and return process exit code (0 for pass, 1 for fail)."""
    suite = build_suite(selected_tiers, feature_filter)
    total_tests = suite.countTestCases()

    print(f"\n{BOLD}{CYAN}========================================================================{RESET}")
    print(f"{BOLD}{CYAN} Lauburu Sovereign Mesh Generation 32 E2E Test Suite Runner{RESET}")
    print(f"{BOLD}{CYAN} Zero-Mock, Tri-Proof & Opaque-Box Methodology Compliant{RESET}")
    print(f"{BOLD}{CYAN}========================================================================{RESET}")
    print(f"Selected Tiers  : {', '.join(str(t) for t in selected_tiers)}")
    if feature_filter:
        print(f"Feature Filter  : {feature_filter.upper()}")
    print(f"Total Discovered: {total_tests} test cases\n")

    result = CustomJSONTestResult(verbosity=verbosity)
    start_time = time.perf_counter()
    suite.run(result)
    duration = time.perf_counter() - start_time

    if verbosity == 1:
        print("\n")

    num_passed = len(result.successes)
    num_failed = len(result.failures)
    num_errors = len(result.errors)
    num_skipped = len(result.skipped)

    print(f"{BOLD}Execution Summary:{RESET}")
    print(f"  • Total Tests Run : {result.testsRun}")
    print(f"  • Passed          : {GREEN}{num_passed}{RESET}")
    print(f"  • Failed          : {RED if num_failed > 0 else GREEN}{num_failed}{RESET}")
    print(f"  • Errors          : {RED if num_errors > 0 else GREEN}{num_errors}{RESET}")
    print(f"  • Skipped         : {YELLOW if num_skipped > 0 else GREEN}{num_skipped}{RESET}")
    print(f"  • Total Duration  : {duration:.3f} seconds\n")

    if result.failures:
        print(f"{BOLD}{RED}--- FAILURES ({len(result.failures)}) ---{RESET}")
        for test, tb in result.failures:
            print(f"\n{BOLD}{RED}[FAIL] {test.id()}{RESET}")
            print(tb)

    if result.errors:
        print(f"{BOLD}{RED}--- ERRORS ({len(result.errors)}) ---{RESET}")
        for test, tb in result.errors:
            print(f"\n{BOLD}{RED}[ERROR] {test.id()}{RESET}")
            print(tb)

    is_success = result.wasSuccessful()
    status_str = "PASSED" if is_success else "FAILED"

    report_data = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "generation": 32,
        "status": status_str,
        "exit_code": 0 if is_success else 1,
        "selected_tiers": selected_tiers,
        "feature_filter": feature_filter,
        "total_discovered": total_tests,
        "tests_run": result.testsRun,
        "passed": num_passed,
        "failed": num_failed,
        "errors": num_errors,
        "skipped": num_skipped,
        "duration_seconds": round(duration, 4),
        "failures": [{"test": test.id(), "traceback": tb} for test, tb in result.failures],
        "errors_list": [{"test": test.id(), "traceback": tb} for test, tb in result.errors],
    }

    if json_output_path:
        out_p = Path(json_output_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        print(f"JSON execution report exported to: {out_p}")

    print(f"{BOLD}Final Result: {GREEN if is_success else RED}{status_str}{RESET} (Exit Code: {0 if is_success else 1})\n")
    return 0 if is_success else 1


def main():
    parser = argparse.ArgumentParser(description="Lauburu Generation 32 Master E2E Test Runner")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4], action="append", help="Select specific tier (1-4)")
    parser.add_argument("--all", action="store_true", help="Run all 4 tiers (default)")
    parser.add_argument("--feature", type=str, choices=[f"F{i}" for i in range(1, 10)] + [f"f{i}" for i in range(1, 10)], help="Filter by feature (F1-F9)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose per-test output")
    parser.add_argument("--json-output", type=str, help="Path to export JSON execution summary")

    args = parser.parse_args()

    if args.tier:
        selected_tiers = sorted(list(set(args.tier)))
    else:
        selected_tiers = [1, 2, 3, 4]

    verbosity = 2 if args.verbose else 1
    exit_code = run_tests(
        selected_tiers=selected_tiers,
        feature_filter=args.feature,
        verbosity=verbosity,
        json_output_path=args.json_output,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
