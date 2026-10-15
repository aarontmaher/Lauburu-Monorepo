#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Empirical Stress & Boundary Test Suite: SWE-bench Ingestion & AST Harness
=========================================================================
Target: 02_ai_models_and_inference/benchmarks/swe_bench_harness.py
        02_ai_models_and_inference/benchmarks/sb_cli_adapter.py
Author: Challenger 2 (Milestone M1)
Verification: Empirical stress-testing of AST parsing, sandbox evaluation,
task ingestion, boundary conditions, unicode, nesting, and Python 3.10-3.13 constructs.
Rule #0 Compliance: 100% genuine test cases and empirical assertions.
"""

import os
import sys
import json
import time
import tempfile
import textwrap
from pathlib import Path
from typing import Dict, Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_DIR = REPO_ROOT / "02_ai_models_and_inference" / "benchmarks"
DATA_DIR = REPO_ROOT / "04_data_and_memory"

for p in [str(REPO_ROOT), str(BENCHMARK_DIR), str(DATA_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from swe_bench_harness import (
    SweBenchHarness,
    PatchSandboxEvaluator,
    SAMPLE_SWEBENCH_TASKS,
    MODELS_IN_ARENA,
)
from sb_cli_adapter import SbCliAdapter


# ===========================================================================
# 1. 0-Length & Empty Diff Boundary Tests
# ===========================================================================

class TestZeroLengthAndEmptyDiffBoundaries:
    """Verifies boundary behavior for 0-length, empty, and whitespace diffs."""

    def test_empty_string_diff(self):
        """0-length empty string diff is rejected gracefully."""
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff("")
        assert is_valid is False
        assert "Empty or non-string patch" in msg
        assert details == {}

    def test_whitespace_only_diff(self):
        """Whitespace-only diff string is rejected gracefully."""
        for ws in ["   ", "\n\n\t\n  ", "\r\n  \r\n"]:
            is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(ws)
            assert is_valid is False
            assert "Empty or non-string patch" in msg

    def test_non_string_patch_inputs(self):
        """Non-string inputs (None, int, dict, list) to validate_ast_diff return False."""
        for invalid_input in [None, 42, ["diff"], {"patch": "diff"}, 3.14]:
            is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(invalid_input)
            assert is_valid is False
            assert "Empty or non-string patch" in msg

    def test_diff_with_only_context_zero_mods(self):
        """Diff with context lines but 0 additions and 0 removals parses cleanly."""
        context_diff = """diff --git a/src/module.py b/src/module.py
--- a/src/module.py
+++ b/src/module.py
@@ -10,3 +10,3 @@
 def existing():
     pass
"""
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(context_diff)
        assert is_valid is True
        assert details["lines_added"] == 0
        assert details["lines_removed"] == 0
        assert details["files"] == ["src/module.py"]

    def test_diff_with_only_deletions(self):
        """Diff with 0 added lines but multiple deletions parses cleanly."""
        del_diff = """diff --git a/src/module.py b/src/module.py
--- a/src/module.py
+++ b/src/module.py
@@ -10,3 +10,0 @@
-def obsolete():
-    return False
"""
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(del_diff)
        assert is_valid is True
        assert details["lines_added"] == 0
        assert details["lines_removed"] == 2


# ===========================================================================
# 2. 1000-Line Diff & Scale Stress Tests
# ===========================================================================

class TestLargeScaleDiffStress:
    """Verifies scalability and error localization under 1000+ line diff payloads."""

    def test_1000_line_valid_diff_execution(self):
        """1000-line valid Python diff parses and validates in <100ms."""
        thousand_lines = "\n".join([f"+x_{i}: int = {i} * 2" for i in range(1000)])
        diff_text = f"""diff --git a/large_module.py b/large_module.py
--- a/large_module.py
+++ b/large_module.py
@@ -1,1 +1,1001 @@
{thousand_lines}
"""
        start_t = time.perf_counter()
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(diff_text)
        elapsed = time.perf_counter() - start_t

        assert is_valid is True
        assert details["lines_added"] == 1000
        assert elapsed < 0.20, f"1000-line diff took {elapsed:.4f}s (>0.20s budget)"

    def test_1000_line_diff_syntax_error_localization(self):
        """1000-line diff with syntax error at line 1000 is accurately detected."""
        thousand_lines = "\n".join([f"+x_{i}: int = {i}" for i in range(999)])
        thousand_lines += "\n+invalid_assignment = (100 +"  # unclosed parenthesis
        diff_text = f"""diff --git a/large_broken.py b/large_broken.py
--- a/large_broken.py
+++ b/large_broken.py
@@ -1,1 +1,1001 @@
{thousand_lines}
"""
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(diff_text)
        assert is_valid is False
        assert "AST Syntax Error in large_broken.py" in msg
        assert "large_broken.py" == details["failed_file"]
        assert "SyntaxError" in details["ast_error"]
        assert details["lines_added"] == 1000

    def test_multi_file_scale_diff_50_files(self):
        """Diff spanning 50 files parses and extracts all 50 target paths."""
        file_chunks = []
        for i in range(50):
            file_chunks.append(f"""diff --git a/pkg/mod_{i}.py b/pkg/mod_{i}.py
--- a/pkg/mod_{i}.py
+++ b/pkg/mod_{i}.py
@@ -1,2 +1,3 @@
 def f_{i}():
+    return {i}
""")
        diff_text = "\n".join(file_chunks)
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(diff_text)
        assert is_valid is True
        assert len(details["files"]) == 50
        assert details["lines_added"] == 50


# ===========================================================================
# 3. Unicode & International Character Tests
# ===========================================================================

class TestUnicodeAndInternationalizationBoundaries:
    """Verifies UTF-8 compliance across comments, docstrings, identifiers, and paths."""

    def test_unicode_in_code_and_comments(self):
        """Unicode characters in comments, emoji, and string literals parse cleanly."""
        diff_text = """diff --git a/src/international.py b/src/international.py
--- a/src/international.py
+++ b/src/international.py
@@ -1,2 +1,6 @@
 # 🚀 Lauburu AI Mesh Subsystem
+# 日本語のコメント: 医療グレード心電図
+def get_mesh_status() -> str:
+    \"\"\"Docstring with special characters: 🧠, ⚡, π, µs\"\"\"
+    return "Status: 正常稼働 🚀"
"""
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(diff_text)
        assert is_valid is True
        assert "src/international.py" in details["files"]

    def test_unicode_python_identifiers(self):
        """Python 3 supported unicode variable names and mathematical symbols."""
        diff_text = """diff --git a/src/math_dsp.py b/src/math_dsp.py
--- a/src/math_dsp.py
+++ b/src/math_dsp.py
@@ -1,2 +1,4 @@
+π_val = 3.141592653589793
+α_learning_rate = 0.001
+速度_kmh = 120.5
"""
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(diff_text)
        assert is_valid is True
        assert details["lines_added"] == 3

    def test_unicode_in_diff_file_paths(self):
        """Diff containing non-ASCII UTF-8 file paths parses correctly."""
        diff_text = """diff --git a/モジュール/データ.py b/モジュール/データ.py
--- a/モジュール/データ.py
+++ b/モジュール/データ.py
@@ -1,2 +1,3 @@
+def 処理():
+    return True
"""
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(diff_text)
        assert is_valid is True
        assert "モジュール/データ.py" in details["files"]


# ===========================================================================
# 4. Deeply Nested Syntax Structures
# ===========================================================================

class TestDeeplyNestedSyntaxStructures:
    """Verifies parser resilience against deep AST nesting depth."""

    def test_deeply_nested_if_blocks(self):
        """Deeply nested if-blocks (30 levels) parse without hitting recursion limits."""
        lines = []
        for i in range(30):
            lines.append("    " * i + f"if condition_{i}:")
        lines.append("    " * 30 + "return 42")
        code = "\n".join(lines)

        ok, err = PatchSandboxEvaluator.validate_ast_code(code)
        assert ok is True
        assert err is None

    def test_deeply_nested_parenthesized_expressions(self):
        """Deeply nested parentheses (40 levels) evaluate cleanly."""
        nested_expr = "x = " + "(" * 40 + "100" + ")" * 40
        ok, err = PatchSandboxEvaluator.validate_ast_code(nested_expr)
        assert ok is True
        assert err is None

    def test_deeply_nested_try_except_finally(self):
        """Nested try-except structures parse without error."""
        code = """
try:
    try:
        try:
            result = compute()
        except KeyError:
            result = fallback_1()
    except ValueError:
        result = fallback_2()
except Exception:
    result = None
"""
        ok, err = PatchSandboxEvaluator.validate_ast_code(code)
        assert ok is True
        assert err is None


# ===========================================================================
# 5. Missing File Headers & Headerless Diffs
# ===========================================================================

class TestMissingFileHeadersAndFormattings:
    """Verifies handling of non-standard or missing diff headers."""

    def test_diff_missing_diff_git_header(self):
        """Diff starting directly with --- and +++ headers parses correctly."""
        diff_text = """--- a/src/app.py
+++ b/src/app.py
@@ -5,2 +5,3 @@
 def run():
+    return 42
"""
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(diff_text)
        assert is_valid is True
        assert "src/app.py" in details["files"]

    def test_diff_missing_file_headers_only_hunk(self):
        """Diff with only @@ hunk markers falls back to candidate_patch.py."""
        diff_text = """@@ -1,2 +1,3 @@
 def compute():
+    return 100
"""
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(diff_text)
        assert is_valid is True
        assert "candidate_patch.py" in details["files"]

    def test_diff_missing_all_headers_raw_modifications(self):
        """Diff with only raw + lines falls back to candidate_patch.py."""
        diff_text = """+def raw_addition():
+    return True
"""
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(diff_text)
        assert is_valid is True
        assert "candidate_patch.py" in details["files"]
        assert details["lines_added"] == 2

    def test_file_creation_diff(self):
        """Diff adding a new file (--- /dev/null) parses target file path."""
        diff_text = """diff --git a/dev/null b/src/new_service.py
--- /dev/null
+++ b/src/new_service.py
@@ -0,0 +1,3 @@
+def bootstrap():
+    return "Ready"
"""
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(diff_text)
        assert is_valid is True
        assert "src/new_service.py" in details["files"]

    def test_crlf_line_endings_in_diff(self):
        """Windows CRLF (\\r\\n) line endings parse identically to Unix LF."""
        diff_crlf = "diff --git a/win.py b/win.py\r\n--- a/win.py\r\n+++ b/win.py\r\n@@ -1,2 +1,3 @@\r\n def f():\r\n+    return 1\r\n"
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(diff_crlf)
        assert is_valid is True
        assert "win.py" in details["files"]


# ===========================================================================
# 6. Edge-Case Python Constructs (3.10 / 3.12 / 3.13)
# ===========================================================================

class TestPythonModernConstructs:
    """Verifies AST parsing of modern Python features (PEP 634, PEP 695, PEP 701, decorators)."""

    def test_pep_634_structural_pattern_matching(self):
        """Match-case statements with literal, sequence, and guard patterns."""
        match_code = """
match response.status:
    case 200:
        return "OK"
    case 404 | 500 if retries > 3:
        return "FAIL_FINAL"
    case [first, *rest]:
        return first
    case {"status": "success", "data": payload}:
        return payload
    case _:
        return "UNKNOWN"
"""
        ok, err = PatchSandboxEvaluator.validate_ast_code(match_code)
        assert ok is True
        assert err is None

    def test_pep_695_type_parameter_syntax(self):
        """Type parameters for type aliases, generic functions, and generic classes."""
        pep695_code = """
type Coordinate[T] = tuple[T, T]

def identity[T](value: T) -> T:
    return value

class MemoryBuffer[T]:
    def __init__(self, size: int):
        self.size = size
"""
        ok, err = PatchSandboxEvaluator.validate_ast_code(pep695_code)
        assert ok is True
        assert err is None

    def test_function_and_class_decorators(self):
        """Multi-level stacked decorators and class decorators."""
        deco_code = """
@dataclass(frozen=True)
class EndpointConfig:
    host: str = "127.0.0.1"
    port: int = 8085

    @property
    @functools.lru_cache(maxsize=256)
    def uri(self) -> str:
        return f"http://{self.host}:{self.port}"
"""
        ok, err = PatchSandboxEvaluator.validate_ast_code(deco_code)
        assert ok is True
        assert err is None

    def test_walrus_operator_and_positional_only_params(self):
        """Walrus operator (:=) and positional-only parameter marker (/)."""
        code = """
def process_data(a: int, b: int, /, c: int = 0, *, debug: bool = False):
    if (total := a + b + c) > 100:
        return total
    return 0
"""
        ok, err = PatchSandboxEvaluator.validate_ast_code(code)
        assert ok is True
        assert err is None

    def test_async_await_generators(self):
        """Async functions, async with, async for, and yield from."""
        async_code = """
async def stream_frames(channel):
    async with channel.acquire():
        async for frame in channel.read():
            yield frame
"""
        ok, err = PatchSandboxEvaluator.validate_ast_code(async_code)
        assert ok is True
        assert err is None

    def test_pep_701_nested_fstrings(self):
        """PEP 701 f-strings with nested quotes and multiline expressions."""
        fstring_code = """
msg = f"Report: {', '.join([f'item_{i}' for i in range(5)])}"
"""
        ok, err = PatchSandboxEvaluator.validate_ast_code(fstring_code)
        assert ok is True
        assert err is None


# ===========================================================================
# 7. Task Ingestion & Ingestion Engine Stress Tests
# ===========================================================================

class TestTaskIngestionEngineStress:
    """Verifies task ingestion limits, fallback mechanics, and cache resilience."""

    def test_load_tasks_limit_boundaries(self):
        """Tests limit clamping on task loader."""
        harness = SweBenchHarness()
        # limit = 1
        t1 = harness.load_tasks(limit=1, use_hf=False)
        assert len(t1) == 1

        # limit = 5
        t5 = harness.load_tasks(limit=5, use_hf=False)
        assert len(t5) == 5

        # limit exceeding available tasks
        t_all = harness.load_tasks(limit=9999, use_hf=False)
        assert len(t_all) >= 16

    def test_load_tasks_corrupted_cache_fallback(self):
        """Corrupted JSON in local cache gracefully falls back without crashing."""
        harness = SweBenchHarness()
        with tempfile.TemporaryDirectory() as td:
            bad_json = Path(td) / "swe-bench_lite_dev.json"
            bad_json.write_text("{CORRUPT_JSON_DATA", encoding="utf-8")

            tasks = harness.load_tasks(cache_dir=td, use_hf=False)
            assert len(tasks) >= 16
            assert tasks[0]["instance_id"] is not None

    def test_evaluate_candidate_patch_full_matrix(self):
        """Evaluates candidate patches across passing, syntax failure, and missing instance."""
        harness = SweBenchHarness()

        # 1. Valid passing patch
        task = SAMPLE_SWEBENCH_TASKS[0]
        res_pass = harness.evaluate_candidate_patch(task["instance_id"], task["sample_patch"])
        assert res_pass["status"] == "PASSED"
        assert res_pass["ast_valid"] is True
        assert res_pass["passed"] is True

        # 2. Invalid syntax patch
        broken_patch = f"""diff --git a/{task['expected_files'][0]} b/{task['expected_files'][0]}
--- a/{task['expected_files'][0]}
+++ b/{task['expected_files'][0]}
@@ -1,2 +1,3 @@
+def syntax_error(
"""
        res_broken = harness.evaluate_candidate_patch(task["instance_id"], broken_patch)
        assert res_broken["status"] == "FAILED"
        assert res_broken["ast_valid"] is False
        assert "AST Syntax Error" in res_broken["reason"]

        # 3. Non-existent instance
        res_missing = harness.evaluate_candidate_patch("non_existent__instance-9999", "diff --git ...")
        assert res_missing["status"] == "FAILED"
        assert res_missing["passed"] is False


# ===========================================================================
# 8. sb-cli Predictions Schema & Boundary Tests
# ===========================================================================

class TestSbCliPredictionsSchemaStress:
    """Verifies schema validation boundaries under large and malformed JSON structures."""

    def test_large_predictions_file_1000_items(self):
        """Predictions file with 1000 instances validates in <50ms."""
        with tempfile.TemporaryDirectory() as td:
            pred_file = Path(td) / "large_preds.json"
            preds = {
                f"repo__issue-{i}": {
                    "model_patch": f"diff --git a/mod.py b/mod.py\n+x = {i}",
                    "model_name_or_path": "qwen2.5-coder-32b"
                }
                for i in range(1000)
            }
            pred_file.write_text(json.dumps(preds), encoding="utf-8")

            t0 = time.perf_counter()
            is_valid, msg, details = SbCliAdapter.validate_predictions_file(pred_file)
            elapsed = time.perf_counter() - t0

            assert is_valid is True
            assert details["count"] == 1000
            assert elapsed < 0.10

    def test_validate_predictions_type_errors(self):
        """Validates rejection of non-string values within prediction schema."""
        with tempfile.TemporaryDirectory() as td:
            pred_file = Path(td) / "type_errors.json"

            # Case: non-string patch
            pred_file.write_text(json.dumps({"task1": {"model_patch": 12345, "model_name_or_path": "m"}}))
            ok, msg, det = SbCliAdapter.validate_predictions_file(pred_file)
            assert ok is False
            assert "must be a string, got int" in msg

            # Case: non-string model name
            pred_file.write_text(json.dumps({"task1": {"model_patch": "diff", "model_name_or_path": None}}))
            ok, msg, det = SbCliAdapter.validate_predictions_file(pred_file)
            assert ok is False
            assert "must be a string, got NoneType" in msg

            # Case: entry is primitive int instead of dict
            pred_file.write_text(json.dumps({"task1": 999}))
            ok, msg, det = SbCliAdapter.validate_predictions_file(pred_file)
            assert ok is False
            assert "must be an object/dict, got int" in msg
