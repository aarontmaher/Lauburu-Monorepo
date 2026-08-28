#!/usr/bin/env python3
"""Red Team 15-Class Schema Mutation Fuzzing Engine.

Exhaustively stress-tests TUI state parsers and validators against 15 distinct
payload mutation classes:
 1. empty_file: 0-byte empty file
 2. whitespace_only: Whitespace and newlines only
 3. binary_noise_raw: Non-UTF8 binary bytes (\\xDE\\xAD\\xBE\\xEF\\x00\\xFF\\xFE\\xFD)
 4. truncated_json: Truncated JSON cut mid-key/mid-value
 5. malformed_json_syntax: Mismatched brackets and invalid syntax
 6. root_array: JSON array at root instead of object
 7. root_primitive: Primitive string/null/number/boolean at root
 8. missing_root_keys: Missing 'version', 'providers', or 'metrics'
 9. missing_provider_keys: Provider missing required fields ('status', 'daily_limit')
10. extreme_numbers_10_pow_18: 10^18 token numbers & int64 boundaries
11. negative_and_overflow_pct: Negative percentages (-0.95) and >100% (999.99%)
12. zero_division_all_zeros: 0 daily limit, 0 used, 0 tokens (0/0 triggers)
13. unicode_special_ids: UTF-8 / Kanji / Arabic / Emoji provider names
14. deeply_nested_json: 50-level deeply nested JSON trees
15. scale_100_providers: 100 dynamic edge provider shards

Measures:
- Zero unhandled panics, segfaults, or Python tracebacks
- Clean, deterministic error rejection on malformed inputs
- Graceful rendering / parsing on extreme valid boundaries
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class FuzzTestCase:
    id: str
    description: str
    payload: Any
    is_valid_schema: bool


@dataclass
class FuzzExecutionResult:
    case_id: str
    description: str
    is_valid_schema: bool
    returncode: int
    passed: bool
    is_panic: bool
    duration_ms: float
    output_snippet: str


@dataclass
class FuzzSuiteResult:
    target_command_template: List[str]
    total_cases: int
    passed_cases: int
    failed_cases: int
    panics_count: int
    all_passed: bool
    case_results: List[FuzzExecutionResult]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attack_id": "SCHEMA_FUZZER_15_CLASSES",
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": self.failed_cases,
            "panics_count": self.panics_count,
            "all_passed": self.all_passed,
            "cases": [
                {
                    "case_id": r.case_id,
                    "description": r.description,
                    "is_valid_schema": r.is_valid_schema,
                    "returncode": r.returncode,
                    "passed": r.passed,
                    "is_panic": r.is_panic,
                    "duration_ms": r.duration_ms,
                }
                for r in self.case_results
            ],
        }


def get_base_valid_state() -> Dict[str, Any]:
    """Helper returning canonical valid state dict."""
    return {
        "version": "2.0.0",
        "last_reset": "2026-08-27T06:00:00.000000+00:00",
        "last_reset_date": "2026-08-27",
        "last_updated": "2026-08-27T13:00:00.000000+00:00",
        "providers": {
            "julien_ai": {
                "name": "Julien AI (Direct)",
                "daily_limit": 300,
                "used_today": 45,
                "remaining_pct": 0.85,
                "avg_latency_ms": 1200.0,
                "max_tokens": 8192,
                "consecutive_failures": 0,
                "total_requests": 45,
                "successful_requests": 45,
                "status": "healthy",
            },
            "cloudflare_ai": {
                "name": "Cloudflare Workers AI",
                "daily_limit": 1000,
                "used_today": 120,
                "remaining_pct": 0.88,
                "avg_latency_ms": 650.0,
                "max_tokens": 4096,
                "consecutive_failures": 0,
                "total_requests": 120,
                "successful_requests": 120,
                "status": "healthy",
            },
        },
        "metrics": {
            "total_tasks_routed": 165,
            "cloud_tasks_succeeded": 165,
            "local_mesh_fallback_count": 0,
            "total_lora_samples_harvested": 12,
        },
    }


def get_fuzz_corpus() -> List[FuzzTestCase]:
    """Construct the canonical 15-class mutation fuzz corpus."""
    corpus: List[FuzzTestCase] = []

    # 1. Empty 0-byte file
    corpus.append(FuzzTestCase("01_empty_file", "0-byte empty file", "", False))

    # 2. Whitespace only
    corpus.append(FuzzTestCase("02_whitespace_only", "Whitespace and newlines only", "   \n\t\r\n   ", False))

    # 3. Random binary noise (invalid UTF-8 bytes)
    corpus.append(FuzzTestCase(
        "03_binary_noise_raw",
        "Non-UTF8 binary bytes (0xDEADBEEF)",
        bytes([0xDE, 0xAD, 0xBE, 0xEF, 0x00, 0xFF, 0xFE, 0xFD]),
        False,
    ))

    # 4. Truncated JSON
    corpus.append(FuzzTestCase(
        "04_truncated_json",
        "Truncated JSON cut mid-token",
        '{"version": "2.0.0", "providers": {"gemini_free": {"daily_limit": 1500, "used_to',
        False,
    ))

    # 5. Broken JSON syntax
    corpus.append(FuzzTestCase(
        "05_malformed_json_syntax",
        "Mismatched braces and syntax error",
        '{"version": 2.0.0, "providers": [invalid_array}, {metrics: {}}',
        False,
    ))

    # 6. Root array mismatch
    corpus.append(FuzzTestCase(
        "06_root_array",
        "JSON array at root instead of object",
        [{"version": "2.0.0"}],
        False,
    ))

    # 7. Root primitive types
    corpus.append(FuzzTestCase("07_root_primitive_string", "Primitive string at root", "just a string", False))

    # 8. Missing required root keys
    no_version = get_base_valid_state()
    del no_version["version"]
    corpus.append(FuzzTestCase("08_missing_root_version", "Missing 'version' root key", no_version, False))

    # 9. Missing required provider keys
    missing_prov_status = get_base_valid_state()
    del missing_prov_status["providers"]["julien_ai"]["status"]
    corpus.append(FuzzTestCase(
        "09_missing_provider_status",
        "Provider missing 'status' field",
        missing_prov_status,
        False,
    ))

    # 10. Extreme Numbers (10^18 Token Values)
    extreme_nums = get_base_valid_state()
    extreme_nums["providers"]["julien_ai"]["daily_limit"] = 10**18
    extreme_nums["providers"]["julien_ai"]["used_today"] = (10**18) - 1
    extreme_nums["metrics"]["total_tasks_routed"] = 10**18
    corpus.append(FuzzTestCase(
        "10_extreme_numbers_10_pow_18",
        "10^18 token values & int64 boundaries",
        extreme_nums,
        True,
    ))

    # 11. Negative percentages & overflow values
    neg_pct = get_base_valid_state()
    neg_pct["providers"]["cloudflare_ai"]["remaining_pct"] = -0.95
    neg_pct["providers"]["julien_ai"]["remaining_pct"] = 999.99
    corpus.append(FuzzTestCase(
        "11_negative_and_overflow_pct",
        "Negative and >100% remaining_pct",
        neg_pct,
        True,
    ))

    # 12. Zero division boundary cases (0/0)
    zero_div = get_base_valid_state()
    for p in zero_div["providers"].values():
        p["daily_limit"] = 0
        p["used_today"] = 0
        p["remaining_pct"] = 0.0
        p["max_tokens"] = 0
        p["avg_latency_ms"] = 0.0
    corpus.append(FuzzTestCase(
        "12_zero_division_all_zeros",
        "All limits, used, tokens, latencies = 0",
        zero_div,
        True,
    ))

    # 13. Unicode, Emojis, and Custom Provider Keys
    unicode_state = get_base_valid_state()
    unicode_state["providers"]["tokyo_edge_東京"] = {
        "name": "東京 Edge Node ⚡",
        "daily_limit": 5000,
        "used_today": 120,
        "remaining_pct": 0.976,
        "avg_latency_ms": 42.5,
        "status": "healthy",
    }
    corpus.append(FuzzTestCase(
        "13_unicode_special_ids",
        "Unicode, Japanese, and Emoji provider identifiers",
        unicode_state,
        True,
    ))

    # 14. Deeply nested extra structures (50 levels)
    deep_state = get_base_valid_state()
    curr = deep_state["providers"]["julien_ai"]
    for i in range(50):
        curr["nested_level"] = {}
        curr = curr["nested_level"]
    corpus.append(FuzzTestCase(
        "14_deeply_nested_json",
        "50 levels of nested JSON AST objects",
        deep_state,
        True,
    ))

    # 15. Scaling to 100 dynamic providers
    scale_state = get_base_valid_state()
    for i in range(1, 101):
        scale_state["providers"][f"shard_{i:03d}"] = {
            "name": f"Shard {i}",
            "daily_limit": 1000 * i,
            "used_today": 5 * i,
            "remaining_pct": 0.995,
            "avg_latency_ms": 10.0 + i,
            "status": "healthy" if i % 5 != 0 else "degraded",
        }
    corpus.append(FuzzTestCase(
        "15_scale_100_providers",
        "100 dynamic edge provider shards",
        scale_state,
        True,
    ))

    return corpus


class SchemaFuzzer:
    """Adversarial stressor executing 15-class mutation fuzzing."""

    def __init__(self, corpus: Optional[List[FuzzTestCase]] = None):
        self.corpus = corpus or get_fuzz_corpus()

    def run_fuzz_suite(
        self,
        cmd_builder: Any,  # Callable[[Path], List[str]]
        cwd: Optional[Path] = None,
    ) -> FuzzSuiteResult:
        """Run all 15 fuzz test cases against the given command builder."""
        results: List[FuzzExecutionResult] = []
        panics = 0

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            for case in self.corpus:
                state_file = tmp_path / f"{case.id}.json"

                # Write payload
                if isinstance(case.payload, bytes):
                    state_file.write_bytes(case.payload)
                elif isinstance(case.payload, str):
                    state_file.write_text(case.payload, encoding="utf-8")
                else:
                    state_file.write_text(json.dumps(case.payload, indent=2), encoding="utf-8")

                cmd = cmd_builder(state_file)
                t0 = time.perf_counter()

                try:
                    proc = subprocess.run(
                        cmd,
                        cwd=str(cwd) if cwd else None,
                        capture_output=True,
                        text=True,
                        timeout=5.0,
                    )
                    dur_ms = (time.perf_counter() - t0) * 1000.0
                    combined = (proc.stderr or "") + (proc.stdout or "")

                    is_panic = (
                        "panic:" in combined
                        or "fatal error:" in combined
                        or "SIGSEGV" in combined
                        or "Traceback (most recent call last)" in combined
                        or proc.returncode in (-11, -6, -4, 134, 139)
                    )

                    if is_panic:
                        panics += 1
                        passed = False
                    elif case.is_valid_schema:
                        # Valid schema must exit 0
                        passed = (proc.returncode == 0)
                    else:
                        # Invalid schema must exit non-zero without panic
                        passed = (proc.returncode != 0)

                    snippet = (proc.stdout or proc.stderr or "")[:100].strip()

                    results.append(FuzzExecutionResult(
                        case_id=case.id,
                        description=case.description,
                        is_valid_schema=case.is_valid_schema,
                        returncode=proc.returncode,
                        passed=passed,
                        is_panic=is_panic,
                        duration_ms=round(dur_ms, 2),
                        output_snippet=snippet,
                    ))

                except subprocess.TimeoutExpired:
                    dur_ms = (time.perf_counter() - t0) * 1000.0
                    results.append(FuzzExecutionResult(
                        case_id=case.id,
                        description=case.description,
                        is_valid_schema=case.is_valid_schema,
                        returncode=-9,
                        passed=False,
                        is_panic=False,
                        duration_ms=round(dur_ms, 2),
                        output_snippet="TIMEOUT",
                    ))
                except Exception as ex:
                    dur_ms = (time.perf_counter() - t0) * 1000.0
                    panics += 1
                    results.append(FuzzExecutionResult(
                        case_id=case.id,
                        description=case.description,
                        is_valid_schema=case.is_valid_schema,
                        returncode=-1,
                        passed=False,
                        is_panic=True,
                        duration_ms=round(dur_ms, 2),
                        output_snippet=str(ex)[:100],
                    ))

        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count
        all_passed = (passed_count == len(results)) and (panics == 0)

        sample_cmd = cmd_builder(Path("sample.json")) if results else []

        return FuzzSuiteResult(
            target_command_template=sample_cmd,
            total_cases=len(results),
            passed_cases=passed_count,
            failed_cases=failed_count,
            panics_count=panics,
            all_passed=all_passed,
            case_results=results,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Red Team 15-Class Schema Mutation Fuzzer")
    parser.add_argument("cmd_prefix", nargs="+", help="Command prefix before state path argument (e.g. python3 app.py --verify --state-path)")
    args = parser.parse_args()

    def cmd_builder(state_p: Path) -> List[str]:
        return args.cmd_prefix + [str(state_p)]

    fuzzer = SchemaFuzzer()
    res = fuzzer.run_fuzz_suite(cmd_builder)

    print(f"[*] 15-Class Schema Fuzzing Results:")
    print(f"    Total Cases : {res.total_cases}")
    print(f"    Passed      : {res.passed_cases}")
    print(f"    Failed      : {res.failed_cases}")
    print(f"    Panics      : {res.panics_count}")
    print(f"    All Passed  : {res.all_passed}")

    for r in res.case_results:
        status = "✓ PASS" if r.passed else "❌ FAIL"
        print(f"    [{status}] {r.case_id:28s} (ret={r.returncode}, {r.duration_ms:.1f}ms): {r.description}")

    sys.exit(0 if res.all_passed else 1)


if __name__ == "__main__":
    main()
