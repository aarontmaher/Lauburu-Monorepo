#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified E2E Test Runner for Sovereign Lens Bootstrapper & Graph Orchestrator.
Supports running all tiers, specific tiers, and emitting detailed Text, JSON, and TAP reports.
"""

import os
import sys
import time
import json
import argparse
import unittest
from pathlib import Path
from typing import Dict, List, Any, Optional

SUITE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = SUITE_ROOT.parent.parent

for p in [str(PROJECT_ROOT), str(SUITE_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)


class TestResultCollector(unittest.TestResult):
    """Custom TestResult that collects structured execution data for TAP and JSON reporting."""
    __test__ = False

    def __init__(self, stream=None, descriptions=None, verbosity=1):
        super().__init__(stream, descriptions, verbosity)
        self.results: List[Dict[str, Any]] = []
        self._test_start_time = 0.0

    def startTest(self, test):
        super().startTest(test)
        self._test_start_time = time.time()

    def addSuccess(self, test):
        super().addSuccess(test)
        elapsed = time.time() - self._test_start_time
        self.results.append({
            "test_id": test.id(),
            "name": test._testMethodName,
            "class": test.__class__.__name__,
            "status": "PASS",
            "duration_sec": round(elapsed, 4),
            "error": None
        })

    def addFailure(self, test, err):
        super().addFailure(test, err)
        elapsed = time.time() - self._test_start_time
        self.results.append({
            "test_id": test.id(),
            "name": test._testMethodName,
            "class": test.__class__.__name__,
            "status": "FAIL",
            "duration_sec": round(elapsed, 4),
            "error": self._exc_info_to_string(err, test)
        })

    def addError(self, test, err):
        super().addError(test, err)
        elapsed = time.time() - self._test_start_time
        self.results.append({
            "test_id": test.id(),
            "name": test._testMethodName,
            "class": test.__class__.__name__,
            "status": "ERROR",
            "duration_sec": round(elapsed, 4),
            "error": self._exc_info_to_string(err, test)
        })

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        elapsed = time.time() - self._test_start_time
        self.results.append({
            "test_id": test.id(),
            "name": test._testMethodName,
            "class": test.__class__.__name__,
            "status": "SKIP",
            "duration_sec": round(elapsed, 4),
            "error": str(reason)
        })


def discover_tier_suites(tier: Optional[int] = None) -> unittest.TestSuite:
    """Discovers test suites based on tier filter."""
    loader = unittest.TestLoader()
    combined_suite = unittest.TestSuite()

    tier_dirs = {
        1: SUITE_ROOT / "tier1_feature_coverage",
        2: SUITE_ROOT / "tier2_boundary_cases",
        3: SUITE_ROOT / "tier3_cross_feature",
        4: SUITE_ROOT / "tier4_real_world",
    }

    targets = [tier_dirs[tier]] if tier in tier_dirs else list(tier_dirs.values())

    for target_dir in targets:
        if target_dir.exists():
            suite = loader.discover(
                start_dir=str(target_dir),
                pattern="test_*.py",
                top_level_dir=str(SUITE_ROOT)
            )
            combined_suite.addTests(suite)

    return combined_suite


def format_tap(collector: TestResultCollector) -> str:
    """Formats test results as Test Anything Protocol (TAP) version 13 stream."""
    lines = ["TAP version 13", f"1..{len(collector.results)}"]
    for idx, r in enumerate(collector.results, 1):
        status = "ok" if r["status"] == "PASS" else "not ok"
        directive = f" # SKIP {r['error']}" if r["status"] == "SKIP" else ""
        lines.append(f"{status} {idx} - {r['test_id']} ({r['duration_sec']}s){directive}")
        if r["status"] in ("FAIL", "ERROR"):
            lines.append("  ---")
            lines.append(f"  message: {r['status']}")
            err_lines = (r['error'] or "").strip().split("\n")
            lines.append("  traceback: |")
            for el in err_lines:
                lines.append(f"    {el}")
            lines.append("  ...")
    return "\n".join(lines)


def format_json_report(collector: TestResultCollector, total_elapsed: float) -> str:
    """Formats structured JSON execution report."""
    summary = {
        "timestamp": int(time.time()),
        "total_tests": len(collector.results),
        "passed": sum(1 for r in collector.results if r["status"] == "PASS"),
        "failed": sum(1 for r in collector.results if r["status"] == "FAIL"),
        "errors": sum(1 for r in collector.results if r["status"] == "ERROR"),
        "skipped": sum(1 for r in collector.results if r["status"] == "SKIP"),
        "total_duration_sec": round(total_elapsed, 4),
        "all_passed": (len(collector.failures) == 0 and len(collector.errors) == 0),
        "tests": collector.results
    }
    return json.dumps(summary, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Unified E2E Test Runner for Sovereign Lens Bootstrapper & Graph Orchestrator"
    )
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4], default=None,
                        help="Specific tier to run (1=Feature, 2=Boundary, 3=Cross-Feature, 4=Real-World)")
    parser.add_argument("--format", choices=["text", "json", "tap"], default="text",
                        help="Output format (default: text)")
    parser.add_argument("--output", type=str, default=None,
                        help="Optional file path to write results")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose output")
    args = parser.parse_args()

    suite = discover_tier_suites(args.tier)
    collector = TestResultCollector()

    start_time = time.time()
    suite.run(collector)
    total_elapsed = time.time() - start_time

    output_str = ""
    if args.format == "json":
        output_str = format_json_report(collector, total_elapsed)
    elif args.format == "tap":
        output_str = format_tap(collector)
    else:
        # Standard human-readable summary
        passed = sum(1 for r in collector.results if r["status"] == "PASS")
        failed = sum(1 for r in collector.results if r["status"] == "FAIL")
        errors = sum(1 for r in collector.results if r["status"] == "ERROR")
        skipped = sum(1 for r in collector.results if r["status"] == "SKIP")
        total = len(collector.results)

        lines = [
            "=" * 78,
            f"SOVEREIGN LENS BOOTSTRAPPER E2E TEST RUNNER",
            f"Tier: {'All Tiers (1-4)' if args.tier is None else f'Tier {args.tier}'}",
            "=" * 78,
        ]

        if args.verbose or failed > 0 or errors > 0:
            for r in collector.results:
                symbol = "✓" if r["status"] == "PASS" else ("✗" if r["status"] in ("FAIL", "ERROR") else "○")
                lines.append(f"[{symbol} {r['status']}] {r['test_id']} ({r['duration_sec']}s)")
                if r["error"] and args.verbose:
                    lines.append(f"    {r['error'].strip().replace(chr(10), chr(10) + '    ')}")

        lines.extend([
            "-" * 78,
            f"Ran {total} tests in {total_elapsed:.4f}s",
            f"Passed: {passed} | Failed: {failed} | Errors: {errors} | Skipped: {skipped}",
            f"Result: {'SUCCESS' if (failed == 0 and errors == 0) else 'FAILURE'}",
            "=" * 78,
        ])
        output_str = "\n".join(lines)

    if args.output:
        Path(args.output).write_text(output_str, encoding="utf-8")
        print(f"Results written to {args.output}")
    else:
        print(output_str)

    # Clean exit code
    sys.exit(0 if (len(collector.failures) == 0 and len(collector.errors) == 0) else 1)


if __name__ == "__main__":
    main()
