#!/usr/bin/env python3
"""
Challenger 1 Adversarial Verification Harness
==============================================
Empirical challenge suite for Milestone 1:
- Evaluates ZeroMockStaticJudge on sneaky mock patterns and false-positive traps.
- Evaluates ZeroMockDynamicJudge on floating-point precision, micro-jitter spoofing, and boundary inputs.
- Evaluates ZeroMockFaultInjector on deep nested fallbacks and malformed payloads.
"""

import ast
import json
import math
import os
import random
import sys
from pathlib import Path
from typing import Dict, Any, List

# Import judges
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from tests.zero_mock_judge.zero_mock_static_judge import ZeroMockStaticJudge, Violation
from tests.zero_mock_judge.zero_mock_dynamic_judge import (
    ZeroMockDynamicJudge,
    MetricSample,
    MetricVarianceStat
)
from tests.zero_mock_judge.zero_mock_fault_injector import (
    ZeroMockFaultInjector,
    FaultSimulationServer,
    FaultInjectionResult,
    FORBIDDEN_FALLBACK_SIGNATURES
)

FIXTURES_DIR = Path(__file__).resolve().parent / "challenger_fixtures"


class ChallengerReport:
    def __init__(self):
        self.sections: Dict[str, Any] = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.vulnerabilities: List[Dict[str, Any]] = []

    def record_test(self, section: str, test_name: str, passed: bool, details: str, vuln_severity: str = None):
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            status = "PASS"
        else:
            self.failed_tests += 1
            status = "FAIL"
            if vuln_severity:
                self.vulnerabilities.append({
                    "section": section,
                    "test_name": test_name,
                    "severity": vuln_severity,
                    "details": details
                })
        
        if section not in self.sections:
            self.sections[section] = []
        
        self.sections[section].append({
            "test_name": test_name,
            "status": status,
            "passed": passed,
            "details": details
        })
        print(f"[{status}] [{section}] {test_name}: {details}")


report = ChallengerReport()


# ============================================================================
# CHALLENGE SUITE 1: False Positive Traps Evaluation
# ============================================================================
def challenge_false_positive_traps():
    print("\n" + "="*80)
    print(" CHALLENGE SUITE 1: False Positive Traps (Legitimate Code Resistance)")
    print("="*80)
    judge = ZeroMockStaticJudge(ignore_test_files=False)

    # 1. Python False Positive Traps
    py_traps_path = FIXTURES_DIR / "false_positive_traps.py"
    py_violations = judge.audit_file(str(py_traps_path))
    py_clean = len(py_violations) == 0
    py_details = f"{len(py_violations)} violations found (Expected: 0)."
    if not py_clean:
        py_details += " Offenses: " + "; ".join(f"[{v.rule_id}] L{v.line_number}: {v.offending_code}" for v in py_violations)
    report.record_test(
        "False Positive Resistance",
        "Python Physics, DSP, Unit Conversions, & Config Traps",
        py_clean,
        py_details,
        vuln_severity="HIGH" if not py_clean else None
    )

    # 2. JavaScript False Positive Traps
    js_traps_path = FIXTURES_DIR / "false_positive_traps.js"
    js_violations = judge.audit_file(str(js_traps_path))
    js_clean = len(js_violations) == 0
    js_details = f"{len(js_violations)} violations found (Expected: 0)."
    if not js_clean:
        js_details += " Offenses: " + "; ".join(f"[{v.rule_id}] L{v.line_number}: {v.offending_code}" for v in js_violations)
    report.record_test(
        "False Positive Resistance",
        "JavaScript Visual Animation (@verified-visual-animation) & Config Traps",
        js_clean,
        js_details,
        vuln_severity="HIGH" if not js_clean else None
    )

    # 3. JSON False Positive Traps
    json_traps_path = FIXTURES_DIR / "false_positive_traps.json"
    json_violations = judge.audit_file(str(json_traps_path))
    json_clean = len(json_violations) == 0
    json_details = f"{len(json_violations)} violations found (Expected: 0)."
    if not json_clean:
        json_details += " Offenses: " + "; ".join(f"[{v.rule_id}] L{v.line_number}: {v.offending_code}" for v in json_violations)
    report.record_test(
        "False Positive Resistance",
        "JSON Production Config Traps",
        json_clean,
        json_details,
        vuln_severity="HIGH" if not json_clean else None
    )


# ============================================================================
# CHALLENGE SUITE 2: Sneaky Mock Patterns (Static Evasion Vectors)
# ============================================================================
def challenge_sneaky_mock_patterns():
    print("\n" + "="*80)
    print(" CHALLENGE SUITE 2: Sneaky Mock Patterns (Static Scanner Evasion Analysis)")
    print("="*80)
    judge = ZeroMockStaticJudge(ignore_test_files=False)

    # 1. Audit Python Sneaky Mocks
    py_sneaky_path = FIXTURES_DIR / "sneaky_mocks_suite.py"
    py_violations = judge.audit_file(str(py_sneaky_path))
    
    # Analyze which evasion vectors were caught vs evaded
    caught_rules = {v.rule_id for v in py_violations}
    print(f" -> Python Sneaky Mocks: Detected {len(py_violations)} violations across rules: {caught_rules}")
    for v in py_violations:
        print(f"    * L{v.line_number} [{v.rule_id}] {v.offending_code}")

    # Specific tests for individual evasion vectors in Python
    # Check if division by 0.5 was caught (ZM-AST-PY-02)
    div_caught = any("0.5" in v.offending_code for v in py_violations if v.rule_id == "ZM-AST-PY-02")
    report.record_test(
        "Sneaky Mock Detection (Python)",
        "Synthetic Multiplier Division Obfuscation (/ 0.5)",
        div_caught,
        f"Division multiplier caught: {div_caught}",
        vuln_severity="MEDIUM" if not div_caught else None
    )

    # Check if bitwise shift was caught
    bitwise_caught = any("<<" in v.offending_code for v in py_violations)
    report.record_test(
        "Sneaky Mock Detection (Python)",
        "Bitwise Shift Multiplier Obfuscation (<< 1)",
        bitwise_caught,
        f"Bitwise shift evasion caught: {bitwise_caught}",
        vuln_severity="LOW" if not bitwise_caught else None
    )

    # Check if string concatenation in dict was caught
    concat_caught = any("stealth_node_2" in v.offending_code or "0." in v.offending_code for v in py_violations)
    report.record_test(
        "Sneaky Mock Detection (Python)",
        "String Concatenation Latency Literal ('0.' + '28ms')",
        concat_caught,
        f"String concat latency caught: {concat_caught}",
        vuln_severity="MEDIUM" if not concat_caught else None
    )

    # 2. Audit JS Sneaky Mocks
    js_sneaky_path = FIXTURES_DIR / "sneaky_mocks_suite.js"
    js_violations = judge.audit_file(str(js_sneaky_path))
    
    print(f"\n -> JS Sneaky Mocks: Detected {len(js_violations)} violations")
    for v in js_violations:
        print(f"    * L{v.line_number} [{v.rule_id}] {v.offending_code}")

    # Check if multiline whitespace in JS was caught
    multiline_caught = any("STEALTH_DEVICE_MULTILINE" in v.file_path and "0.28ms" in v.message for v in js_violations)
    report.record_test(
        "Sneaky Mock Detection (JS)",
        "Multiline Whitespace Latency Property Evasion",
        multiline_caught,
        f"Multiline whitespace evasion caught: {multiline_caught}",
        vuln_severity="HIGH" if not multiline_caught else None
    )

    # Check if template literal latency was caught
    template_caught = any("STEALTH_DEVICE_1" in v.offending_code or "0.28" in v.message for v in js_violations if v.rule_id == "ZM-JS-01")
    report.record_test(
        "Sneaky Mock Detection (JS)",
        "Template Literal Latency Evasion (`${0.28}ms`)",
        template_caught,
        f"Template literal latency caught: {template_caught}",
        vuln_severity="MEDIUM" if not template_caught else None
    )

    # Check if aliased Math.random was caught
    aliased_math_caught = any("M.random()" in v.offending_code for v in js_violations if v.rule_id == "ZM-JS-06")
    report.record_test(
        "Sneaky Mock Detection (JS)",
        "Aliased Math.random Evasion (const M = Math; M.random())",
        aliased_math_caught,
        f"Aliased Math.random caught: {aliased_math_caught}",
        vuln_severity="LOW" if not aliased_math_caught else None
    )


# ============================================================================
# CHALLENGE SUITE 3: Dynamic Judge Floating Point & Variance Precision
# ============================================================================
def challenge_dynamic_judge_precision():
    print("\n" + "="*80)
    print(" CHALLENGE SUITE 3: Dynamic Judge Precision & Evasion Stress")
    print("="*80)
    judge = ZeroMockDynamicJudge()

    # 1. Floating-Point Inaccuracy Bug on N=20, 50, 100
    for n in [2, 5, 20, 50, 100]:
        flatline_samples = [
            MetricSample(
                sample_index=i,
                timestamp=100.0 + i * 0.1,
                endpoint="http://localhost:5050/api/stats",
                status_code=200,
                raw_payload={"latency_ms": 0.28},
                extracted_metrics={"latency_ms": 0.28}
            )
            for i in range(n)
        ]
        stats = judge.analyze_variance(flatline_samples)
        stat = stats.get("latency_ms")
        is_flagged = stat and (stat.verdict == "SUSPECT_MOCK_DATA")
        
        details = f"N={n}: mean={stat.mean if stat else 'N/A'}, variance={stat.variance if stat else 'N/A'}, verdict={stat.verdict if stat else 'N/A'}"
        report.record_test(
            "Dynamic Variance Precision",
            f"Flatline Detection on Latency 0.28ms (N={n})",
            is_flagged,
            details,
            vuln_severity="CRITICAL" if not is_flagged else None
        )

    # 2. Adversarial Micro-Jitter Spoofing (Evasion via 1e-6 noise)
    # An attacker adds tiny epsilon jitter (10.000001, 10.000002) to mock data
    micro_jitter_samples = [
        MetricSample(
            sample_index=i,
            timestamp=100.0 + i * 0.1,
            endpoint="http://localhost:5050/api/stats",
            status_code=200,
            raw_payload={},
            extracted_metrics={"throughput_mbps": 10.0 + (i * 1e-6)}
        )
        for i in range(5)
    ]
    micro_stats = judge.analyze_variance(micro_jitter_samples)
    micro_tp_stat = micro_stats.get("throughput_mbps")
    # Check what dynamic judge reports
    # Notice: std_dev is 1.41e-6, variance is ~2e-12.
    micro_details = f"std_dev={micro_tp_stat.std_dev:.8f}, verdict={micro_tp_stat.verdict}"
    # This evaluates whether micro-jitter bypasses zero-variance:
    bypasses_zero_var = (micro_tp_stat.verdict == "PASS")
    report.record_test(
        "Dynamic Evasion Boundary",
        "Micro-Jitter Evasion (1e-6 noise on 10.0 Mbps)",
        not bypasses_zero_var, # If it bypasses, we record it as an adversarial finding
        f"Micro-jitter status: {micro_details}. (Judge requires std_dev > 0.0, so tiny epsilon creates non-zero variance).",
        vuln_severity="MEDIUM" if bypasses_zero_var else None
    )

    # 3. Extreme Floats / Non-Finite Value Resilience
    boundary_samples = [
        MetricSample(
            sample_index=1,
            timestamp=100.0,
            endpoint="http://localhost:5050/api/stats",
            status_code=200,
            raw_payload={},
            extracted_metrics={"latency_ms": 1e-12, "throughput_mbps": 1e9}
        ),
        MetricSample(
            sample_index=2,
            timestamp=101.0,
            endpoint="http://localhost:5050/api/stats",
            status_code=200,
            raw_payload={},
            extracted_metrics={"latency_ms": 1e-12, "throughput_mbps": 1e9}
        )
    ]
    try:
        bound_stats = judge.analyze_variance(boundary_samples)
        bound_ok = "latency_ms" in bound_stats and "throughput_mbps" in bound_stats
        bound_details = f"Extracted metrics handled cleanly: {list(bound_stats.keys())}"
    except Exception as e:
        bound_ok = False
        bound_details = f"Exception raised on boundary floats: {e}"
    
    report.record_test(
        "Dynamic Numeric Stability",
        "Extreme Float Bounds (1e-12, 1e9) Variance Computation",
        bound_ok,
        bound_details,
        vuln_severity="HIGH" if not bound_ok else None
    )


# ============================================================================
# CHALLENGE SUITE 4: Fault Injector Deep Nested & Boundary Stress
# ============================================================================
def challenge_fault_injector_boundaries():
    print("\n" + "="*80)
    print(" CHALLENGE SUITE 4: Fault Injector Deep Nested & Boundary Stress")
    print("="*80)
    injector = ZeroMockFaultInjector()

    # 1. Deeply nested fallback signature detection
    deep_nested_mock = {
        "level1": {
            "level2": {
                "level3": {
                    "status": "FLEET_DARK_ACTIVE",
                    "devices_active": 6,
                    "latency": "0.28ms (DMA)"
                }
            }
        }
    }
    res_nested = injector.verify_no_mock_fallback("deep_nested_client", "CRASH_SIMULATION", deep_nested_mock)
    # Must flag returned_mock_fallback=True, passed=False
    nested_flagged = (not res_nested.passed) and (res_nested.returned_mock_fallback)
    report.record_test(
        "Fault Injection Security",
        "Deeply Nested Prohibited Mock Detection (Level 3 Dictionary)",
        nested_flagged,
        f"Nested mock detected: passed={res_nested.passed}, fallback_detected={res_nested.returned_mock_fallback}",
        vuln_severity="HIGH" if not nested_flagged else None
    )

    # 2. Corrupt / Non-JSON Exception Recovery
    srv = FaultSimulationServer()
    srv.start("CORRUPT_JSON")
    try:
        judge = ZeroMockDynamicJudge(timeout=1.0)
        sample = judge.fetch_sample(srv.get_url(), 1)
        corrupt_ok = (sample.status_code == 200) and ("raw_text" in sample.raw_payload)
        corrupt_details = f"Corrupt JSON handled gracefully without unhandled exception: {sample.raw_payload}"
    except Exception as e:
        corrupt_ok = False
        corrupt_details = f"Unhandled crash on corrupt JSON: {e}"
    finally:
        srv.stop()

    report.record_test(
        "Fault Injection Security",
        "Corrupt JSON Stream Resilience",
        corrupt_ok,
        corrupt_details,
        vuln_severity="HIGH" if not corrupt_ok else None
    )


def print_summary():
    print("\n" + "="*80)
    print(" CHALLENGER 1 ADVERSARIAL VERIFICATION SCORECARD")
    print("="*80)
    print(f" Total Tests Executed: {report.total_tests}")
    print(f" Passed Assertions:    {report.passed_tests}")
    print(f" Failed / Evaded:      {report.failed_tests}")
    print(f" Total Vulnerabilities: {len(report.vulnerabilities)}")
    print("="*80)
    
    if report.vulnerabilities:
        print("\nIDENTIFIED VULNERABILITIES & EVASION VECTORS:")
        for idx, v in enumerate(report.vulnerabilities, 1):
            print(f" [{idx}] [{v['severity']}] ({v['section']}) {v['test_name']}")
            print(f"     Details: {v['details']}")


if __name__ == "__main__":
    challenge_false_positive_traps()
    challenge_sneaky_mock_patterns()
    challenge_dynamic_judge_precision()
    challenge_fault_injector_boundaries()
    print_summary()
