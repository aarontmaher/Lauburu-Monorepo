#!/usr/bin/env python3
"""
E2E Test Runner for Autonomous 24/7 AI Training Optimization Engine.

Supports:
- Tier filtering via `--tier` / `-t` (1, 2, 3, 4, all)
- Structured JSON output via `--json`
- Verbose output via `--verbose` / `-v`
- Pass/fail exit code semantics (exit 0 on 100% pass, non-zero on any failure)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import unittest
from dataclasses import asdict, dataclass, field
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class TestCaseResult:
    """Individual test case execution result."""
    test_id: str
    tier: str
    feature_or_category: str
    description: str
    status: str  # PASS, FAIL, ERROR, SKIP
    duration_sec: float
    error_message: Optional[str] = None


@dataclass
class TierSummary:
    """Summary statistics for a single test tier."""
    tier: str
    name: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    duration_sec: float = 0.0

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total * 100.0) if self.total > 0 else 0.0


@dataclass
class E2ETestRunSummary:
    """Aggregated summary of entire E2E test run."""
    total_tests: int = 0
    total_passed: int = 0
    total_failed: int = 0
    total_errors: int = 0
    total_skipped: int = 0
    total_duration_sec: float = 0.0
    all_passed: bool = False
    tier_summaries: Dict[str, TierSummary] = field(default_factory=dict)
    test_results: List[TestCaseResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tests": self.total_tests,
            "total_passed": self.total_passed,
            "total_failed": self.total_failed,
            "total_errors": self.total_errors,
            "total_skipped": self.total_skipped,
            "total_duration_sec": round(self.total_duration_sec, 4),
            "all_passed": self.all_passed,
            "tier_summaries": {k: asdict(v) for k, v in self.tier_summaries.items()},
            "test_results": [asdict(r) for r in self.test_results],
        }


class CustomTestResult(unittest.TestResult):
    """Custom test result collector capturing durations and metadata."""

    def __init__(self, tier_name: str, verbose: bool = False):
        super().__init__()
        self.tier_name = tier_name
        self.verbose = verbose
        self.results: List[TestCaseResult] = []
        self._test_start_time: float = 0.0

    def startTest(self, test: unittest.TestCase) -> None:
        super().startTest(test)
        self._test_start_time = time.time()
        if self.verbose:
            sys.stdout.write(f"  [RUNNING] {test.id()} ... ")
            sys.stdout.flush()

    def addSuccess(self, test: unittest.TestCase) -> None:
        super().addSuccess(test)
        dur = time.time() - self._test_start_time
        feature = getattr(test, "FEATURE", getattr(test, "CATEGORY", "General"))
        doc = (test.shortDescription() or test._testMethodName or "").strip()
        self.results.append(TestCaseResult(
            test_id=test.id(),
            tier=self.tier_name,
            feature_or_category=str(feature),
            description=doc,
            status="PASS",
            duration_sec=dur,
        ))
        if self.verbose:
            sys.stdout.write(f"PASS ({dur:.3f}s)\n")
            sys.stdout.flush()

    def addFailure(self, test: unittest.TestCase, err: Tuple[Any, Any, Any]) -> None:
        super().addFailure(test, err)
        dur = time.time() - self._test_start_time
        feature = getattr(test, "FEATURE", getattr(test, "CATEGORY", "General"))
        doc = (test.shortDescription() or test._testMethodName or "").strip()
        err_msg = self._exc_info_to_string(err, test)
        self.results.append(TestCaseResult(
            test_id=test.id(),
            tier=self.tier_name,
            feature_or_category=str(feature),
            description=doc,
            status="FAIL",
            duration_sec=dur,
            error_message=err_msg,
        ))
        if self.verbose:
            sys.stdout.write(f"FAIL ({dur:.3f}s)\n")
            sys.stdout.flush()

    def addError(self, test: unittest.TestCase, err: Tuple[Any, Any, Any]) -> None:
        super().addError(test, err)
        dur = time.time() - self._test_start_time
        feature = getattr(test, "FEATURE", getattr(test, "CATEGORY", "General"))
        doc = (test.shortDescription() or test._testMethodName or "").strip()
        err_msg = self._exc_info_to_string(err, test)
        self.results.append(TestCaseResult(
            test_id=test.id(),
            tier=self.tier_name,
            feature_or_category=str(feature),
            description=doc,
            status="ERROR",
            duration_sec=dur,
            error_message=err_msg,
        ))
        if self.verbose:
            sys.stdout.write(f"ERROR ({dur:.3f}s)\n")
            sys.stdout.flush()

    def addSkip(self, test: unittest.TestCase, reason: str) -> None:
        super().addSkip(test, reason)
        dur = time.time() - self._test_start_time
        feature = getattr(test, "FEATURE", getattr(test, "CATEGORY", "General"))
        doc = (test.shortDescription() or test._testMethodName or "").strip()
        self.results.append(TestCaseResult(
            test_id=test.id(),
            tier=self.tier_name,
            feature_or_category=str(feature),
            description=doc,
            status="SKIP",
            duration_sec=dur,
            error_message=reason,
        ))
        if self.verbose:
            sys.stdout.write(f"SKIP ({reason})\n")
            sys.stdout.flush()


TIER_MODULE_MAP = {
    "1": ("Tier 1", "Feature Coverage (F1-F17)", "tests.e2e.test_tier1_features"),
    "2": ("Tier 2", "Boundary & Stress Analysis", "tests.e2e.test_tier2_boundaries"),
    "3": ("Tier 3", "Cross-Feature Interactions", "tests.e2e.test_tier3_cross_feature"),
    "4": ("Tier 4", "Real-World Scenarios", "tests.e2e.test_tier4_real_world"),
}


def parse_tier_selection(tier_arg: str) -> List[str]:
    """Parse --tier argument into list of tier keys ('1', '2', '3', '4')."""
    arg = tier_arg.strip().lower()
    if arg in ("all", "all_tiers", "*"):
        return ["1", "2", "3", "4"]

    selected = []
    tokens = [t.strip() for t in arg.split(",") if t.strip()]
    for tok in tokens:
        clean = tok.replace("tier", "").strip()
        if clean in TIER_MODULE_MAP:
            if clean not in selected:
                selected.append(clean)
        else:
            raise ValueError(f"Unknown tier identifier: '{tok}'. Must be one of 1, 2, 3, 4, or 'all'.")

    return sorted(selected)


def run_tier_suite(
    tier_key: str, verbose: bool = False
) -> Tuple[TierSummary, List[TestCaseResult]]:
    """Loads and executes a single tier's test suite."""
    tier_num, tier_name, module_name = TIER_MODULE_MAP[tier_key]
    
    loader = unittest.TestLoader()
    try:
        suite = loader.loadTestsFromName(module_name)
    except Exception as e:
        # Module import error
        err_res = TestCaseResult(
            test_id=f"{module_name}.import",
            tier=tier_num,
            feature_or_category="Import",
            description=f"Import module {module_name}",
            status="ERROR",
            duration_sec=0.0,
            error_message=f"Failed to import test module {module_name}: {e}",
        )
        sum_err = TierSummary(
            tier=tier_num,
            name=tier_name,
            total=1,
            errors=1,
        )
        return sum_err, [err_res]

    result_collector = CustomTestResult(tier_name=tier_num, verbose=verbose)
    start_time = time.time()
    suite.run(result_collector)
    duration = time.time() - start_time

    total = len(result_collector.results)
    passed = sum(1 for r in result_collector.results if r.status == "PASS")
    failed = sum(1 for r in result_collector.results if r.status == "FAIL")
    errors = sum(1 for r in result_collector.results if r.status == "ERROR")
    skipped = sum(1 for r in result_collector.results if r.status == "SKIP")

    summary = TierSummary(
        tier=tier_num,
        name=tier_name,
        total=total,
        passed=passed,
        failed=failed,
        errors=errors,
        skipped=skipped,
        duration_sec=duration,
    )
    return summary, result_collector.results


def print_text_summary(summary: E2ETestRunSummary, verbose: bool = False) -> None:
    """Renders formatted test summary table to standard output."""
    print("\n" + "=" * 80)
    print(" 🚀 AUTONOMOUS 24/7 AI TRAINING ENGINE — E2E TEST EXECUTION SUMMARY")
    print("=" * 80)
    print(f"{'Tier':<10} {'Name':<35} {'Total':<8} {'Pass':<8} {'Fail':<8} {'Err':<8} {'Time (s)':<10}")
    print("-" * 80)

    for tier_key, t_sum in sorted(summary.tier_summaries.items()):
        print(
            f"{t_sum.tier:<10} {t_sum.name:<35} {t_sum.total:<8} "
            f"{t_sum.passed:<8} {t_sum.failed:<8} {t_sum.errors:<8} {t_sum.duration_sec:<10.2f}"
        )

    print("-" * 80)
    status_str = "✅ ALL TIERS PASSED" if summary.all_passed else "❌ FAILURES DETECTED"
    print(
        f"{'TOTAL':<10} {'All Selected Tiers':<35} {summary.total_tests:<8} "
        f"{summary.total_passed:<8} {summary.total_failed:<8} {summary.total_errors:<8} "
        f"{summary.total_duration_sec:<10.2f}"
    )
    print("=" * 80)
    print(f"Status: {status_str} | Pass Rate: {(summary.total_passed / summary.total_tests * 100.0) if summary.total_tests > 0 else 0.0:.1f}%")
    print("=" * 80 + "\n")

    # If any failures or errors, print details
    failed_or_error_tests = [r for r in summary.test_results if r.status in ("FAIL", "ERROR")]
    if failed_or_error_tests:
        print("\n" + "!" * 80)
        print(f" ⚠️ FAILURE / ERROR DETAILS ({len(failed_or_error_tests)} items):")
        print("!" * 80)
        for idx, item in enumerate(failed_or_error_tests, 1):
            print(f"\n[{idx}] {item.tier} - {item.test_id} ({item.status})")
            print(f"    Feature: {item.feature_or_category} | Description: {item.description}")
            if item.error_message:
                for line in item.error_message.strip().splitlines()[-10:]:
                    print(f"    | {line}")
        print("!" * 80 + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="E2E Test Runner for Autonomous 24/7 AI Training Optimization Engine"
    )
    parser.add_argument(
        "--tier", "-t",
        default="all",
        help="Specify tiers to run (e.g. '1', '2', '3', '4', '1,2', 'all'). Default: 'all'",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit test run results as structured JSON to stdout",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable detailed progress and test-by-test output",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Optional file path to write JSON test report",
    )

    args = parser.parse_args()

    selected_tiers = parse_tier_selection(args.tier)
    if not args.json:
        print(f"\n[E2E Runner] Starting test execution for Tiers: {selected_tiers} ...")

    run_summary = E2ETestRunSummary()
    start_total = time.time()

    for tier_key in selected_tiers:
        tier_info = TIER_MODULE_MAP[tier_key]
        if not args.json and not args.verbose:
            print(f"  -> Running {tier_info[0]}: {tier_info[1]} ...", end=" ", flush=True)

        t_sum, t_results = run_tier_suite(tier_key, verbose=args.verbose)
        run_summary.tier_summaries[tier_key] = t_sum
        run_summary.test_results.extend(t_results)

        run_summary.total_tests += t_sum.total
        run_summary.total_passed += t_sum.passed
        run_summary.total_failed += t_sum.failed
        run_summary.total_errors += t_sum.errors
        run_summary.total_skipped += t_sum.skipped

        if not args.json and not args.verbose:
            tier_status = "PASS" if (t_sum.failed == 0 and t_sum.errors == 0) else "FAIL"
            print(f"[{tier_status}] ({t_sum.passed}/{t_sum.total} passed in {t_sum.duration_sec:.2f}s)")

    run_summary.total_duration_sec = time.time() - start_total
    run_summary.all_passed = (
        run_summary.total_tests > 0
        and run_summary.total_failed == 0
        and run_summary.total_errors == 0
    )

    if args.json:
        json_output = json.dumps(run_summary.to_dict(), indent=2)
        print(json_output)
    else:
        print_text_summary(run_summary, verbose=args.verbose)

    if args.output:
        out_p = Path(args.output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(run_summary.to_dict(), f, indent=2)
        if not args.json:
            print(f"[E2E Runner] Report written to: {out_p}")

    return 0 if run_summary.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
