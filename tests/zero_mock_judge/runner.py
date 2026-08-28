#!/usr/bin/env python3
"""
Zero-Mock Master Verification Runner
====================================
Unified entrypoint orchestrating:
1. Phase 1: Static AST & Pattern Scanner (zero_mock_static_judge.py)
2. Phase 2: Dynamic Runtime Zero-Variance Judge (zero_mock_dynamic_judge.py)
3. Phase 3: Active Fault Injection Verification (zero_mock_fault_injector.py)
4. Phase 4: Programmatic Certification & Scorecard Generation

Usage:
  python3 -m tests.zero_mock_judge.runner --target-dir <path>
  python3 -m tests.zero_mock_judge.runner --target-dir <path> --endpoint http://localhost:5050/api/stats
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

# Relative and package import handling
try:
    from .zero_mock_static_judge import ZeroMockStaticJudge, Violation
    from .zero_mock_dynamic_judge import ZeroMockDynamicJudge
    from .zero_mock_fault_injector import ZeroMockFaultInjector
except ImportError:
    from zero_mock_static_judge import ZeroMockStaticJudge, Violation
    from zero_mock_dynamic_judge import ZeroMockDynamicJudge
    from zero_mock_fault_injector import ZeroMockFaultInjector


class ZeroMockMasterRunner:
    """Master harness executing all zero-mock verification phases."""

    def __init__(self, target_dir: str, endpoints: Optional[List[str]] = None, run_fault_injection: bool = True):
        self.target_dir = str(Path(target_dir).resolve())
        self.endpoints = endpoints or []
        self.run_fault_injection = run_fault_injection
        self.static_judge = ZeroMockStaticJudge(ignore_test_files=True, target_dir=self.target_dir)
        self.dynamic_judge = ZeroMockDynamicJudge()
        self.fault_injector = ZeroMockFaultInjector()

    def run_all(self, fail_under: float = 100.0) -> Dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()

        # 1. Phase 1: Static AST & Pattern Audit
        print("\n[Phase 1/4] Running Static AST & Pattern Audit...")
        violations = self.static_judge.audit_directory(self.target_dir)
        static_report = self.static_judge.generate_report(self.target_dir, violations)
        static_score = static_report["score"]
        print(f" > Scanned directory: {self.target_dir}")
        print(f" > Violations found: {len(violations)} (Score: {static_score:.1f}/100.0)")

        # 2. Phase 2: Dynamic Runtime Audit (if endpoints provided)
        dynamic_reports = []
        dynamic_passed = True
        if self.endpoints:
            print(f"\n[Phase 2/4] Running Dynamic Zero-Variance Audit on {len(self.endpoints)} endpoints...")
            for ep in self.endpoints:
                print(f" > Probing: {ep}")
                rep = self.dynamic_judge.audit_endpoint(ep, sample_count=5, interval_seconds=0.3)
                dynamic_reports.append(rep)
                if rep["verdict"] == "SUSPECT_SYNTHETIC_DATA":
                    dynamic_passed = False
                    print(f"   ❌ SUSPECT_SYNTHETIC_DATA detected: {rep['mock_violations_count']} zero-variance metrics.")
                else:
                    print(f"   ✅ {rep['verdict']} (Status: {rep['status']})")
        else:
            print("\n[Phase 2/4] Dynamic Runtime Audit: Skipped (no --endpoint specified)")

        # 3. Phase 3: Active Fault Injection Audit
        fault_results = []
        fault_passed = True
        if self.run_fault_injection:
            print("\n[Phase 3/4] Running Active Fault Injection Suite...")
            fault_results = self.fault_injector.run_standard_fault_suite()
            for fr in fault_results:
                if not fr.passed:
                    fault_passed = False
                    print(f"   ❌ FAILED [{fr.scenario_id}]: {fr.message}")
                else:
                    print(f"   ✅ PASSED [{fr.scenario_id}]: {fr.scenario_name}")

        # 4. Phase 4: Programmatic Scorecard & Badge Certification
        # Global Truth Score calculation
        fault_penalty = 0.0 if fault_passed else 40.0
        dynamic_penalty = 0.0 if dynamic_passed else 30.0
        global_score = max(0.0, round(static_score - fault_penalty - dynamic_penalty, 2))

        is_certified = (global_score >= fail_under) and (len(violations) == 0) and fault_passed and dynamic_passed

        final_verdict = "ZERO_MOCK_TRUTH_CERTIFIED" if is_certified else "MOCK_VERIFICATION_FAILED"

        master_report = {
            "metadata": {
                "timestamp_utc": timestamp,
                "target_directory": self.target_dir,
                "runner_version": "1.0.0",
                "rules_evaluated": [
                    "ZM-RULE-01: Hardcoded Telemetry Strings / Numbers",
                    "ZM-RULE-02: Synthetic Math Multipliers",
                    "ZM-RULE-03: Static Default Node Arrays Pre-Marked Active",
                    "ZM-RULE-04: Hardcoded Fallback Dictionaries",
                    "ZM-RULE-05: Simulation Comments & Sleep Loops",
                    "ZM-RULE-06: Unverified Randomization in Telemetry Pipelines"
                ]
            },
            "summary": {
                "verdict": final_verdict,
                "global_truth_score": global_score,
                "certification_passed": is_certified,
                "static_violations_count": len(violations),
                "dynamic_endpoints_tested": len(self.endpoints),
                "fault_injection_scenarios_passed": sum(1 for f in fault_results if f.passed),
                "fault_injection_scenarios_total": len(fault_results)
            },
            "phase_1_static": static_report,
            "phase_2_dynamic": dynamic_reports,
            "phase_3_fault_injection": [f.to_dict() for f in fault_results]
        }

        return master_report


def main():
    parser = argparse.ArgumentParser(description="Zero-Mock Master Verification Suite Runner")
    parser.add_argument("--target-dir", type=str, default=".", help="Root directory to audit")
    parser.add_argument("--endpoint", type=str, action="append", default=[], help="Live HTTP endpoint to verify (can repeat)")
    parser.add_argument("--skip-fault-injection", action="store_true", help="Skip fault injection testing")
    parser.add_argument("--json-output", type=str, default=None, help="Save structured JSON scorecard to path")
    parser.add_argument("--fail-under", type=float, default=100.0, help="Minimum passing score (default: 100.0)")

    args = parser.parse_args()

    runner = ZeroMockMasterRunner(
        target_dir=args.target_dir,
        endpoints=args.endpoint,
        run_fault_injection=not args.skip_fault_injection
    )

    report = runner.run_all(fail_under=args.fail_under)

    print("\n=======================================================")
    print(" ZERO-MOCK MASTER VERIFICATION SUMMARY SCORECARD")
    print("=======================================================")
    print(f" Target Path:         {report['metadata']['target_directory']}")
    print(f" Global Truth Score:  {report['summary']['global_truth_score']} / 100.0")
    print(f" Final Verdict:       {report['summary']['verdict']}")
    print(f" Certified (100%):    {'✅ YES' if report['summary']['certification_passed'] else '❌ NO'}")
    print("=======================================================\n")

    if args.json_output:
        out_path = Path(args.json_output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"Scorecard JSON saved to: {out_path}\n")

    sys.exit(0 if report["summary"]["certification_passed"] else 1)


if __name__ == "__main__":
    main()
