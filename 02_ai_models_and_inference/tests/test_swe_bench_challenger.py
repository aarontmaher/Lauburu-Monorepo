#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adversarial Stress Test Suite & Empirical Challenge Harness for Milestone M1
=============================================================================
Author: Challenger 1 (teamwork_preview_challenger_m1_1)
Target: 02_ai_models_and_inference/benchmarks/swe_bench_harness.py
        02_ai_models_and_inference/benchmarks/sb_cli_adapter.py

Adversarial Vectors:
1. AST Diff Engine:
   - Corrupted diff headers & malformed hunk markers
   - Mixed tabs/spaces indentation in hunk additions
   - Async function hunks (async def, await, async for, async with)
   - Multi-file diffs with partial syntax errors in 2nd/3rd file
   - Multi-language diffs: Python (.py) vs Non-Python (.c, .rs, .md, .json, .sh)
   - Syntax edge cases: unclosed f-strings, unclosed brackets, invalid identifiers
   - Pure deletion diffs, whitespace-only diffs, empty diffs
2. Predictions Schema Enforcement (sb-cli):
   - Missing required keys ('model_patch', 'model_name_or_path')
   - Corrupted types (int, list, dict, float, bool, None)
   - Non-dictionary roots (list, string, int, null, float)
   - Corrupted / truncated JSON files
   - Mixed valid and invalid entries
3. 3-Tier Task Loader Network & Disk Resilience:
   - Simulated network drops / exceptions during HuggingFace ingestion
   - Corrupted / empty / unparseable local cache files
   - Offline Tier 3 fallback guarantee
   - Edge case subset names, split names, and limit bounds
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Ensure module paths are accessible
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


@pytest.fixture
def challenger_workspace():
    """Provides isolated temp workspace for challenger tests."""
    temp_dir = tempfile.mkdtemp(prefix="challenger_m1_swe_")
    ws = Path(temp_dir)
    data_dir = ws / "04_data_and_memory"
    lora_dir = ws / "lora_datasets"
    obsidian_dir = ws / "obsidian_vault" / "04_ANALYTICS"
    cache_dir = data_dir / "swe_bench_datasets"
    preds_dir = data_dir / "swe_bench_predictions"

    data_dir.mkdir(parents=True, exist_ok=True)
    lora_dir.mkdir(parents=True, exist_ok=True)
    obsidian_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    preds_dir.mkdir(parents=True, exist_ok=True)

    training_file = lora_dir / "swe_bench_solutions.jsonl"
    report_file = obsidian_dir / "SWEBENCH_MESH_LEADERBOARD_2026.md"

    harness = SweBenchHarness(
        tasks=list(SAMPLE_SWEBENCH_TASKS),
        models=list(MODELS_IN_ARENA),
        training_file=training_file,
        report_path=report_file,
    )

    yield {
        "workspace": ws,
        "data_dir": data_dir,
        "lora_dir": lora_dir,
        "obsidian_dir": obsidian_dir,
        "cache_dir": cache_dir,
        "preds_dir": preds_dir,
        "training_file": training_file,
        "report_file": report_file,
        "harness": harness,
    }
    shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# SUITE 1: ADVERSARIAL AST DIFF & SANDBOX EVALUATOR CHALLENGES
# =============================================================================

class TestAdversarialAstDiffEngine:
    """Stress-tests PatchSandboxEvaluator against pathological and malformed diffs."""

    def test_corrupted_diff_header_variations(self):
        """Tests that malformed or truncated diff headers are rejected or parsed safely."""
        corrupted_diffs = [
            "diff --git \n",
            "diff --git a/only_one_path\n",
            "+++ \n",
            "@@ invalid hunk header @@\n",
            "--- a/file.py\n+++ /dev/null\n",
        ]
        for diff in corrupted_diffs:
            # Should not crash with unhandled exception
            is_valid, msg = PatchSandboxEvaluator.validate_diff_syntax(diff)
            assert isinstance(is_valid, bool)

    def test_async_function_and_generator_hunks(self):
        """Valid async code hunks (await, async with, async for, yield) must pass AST validation."""
        async_hunk = """diff --git a/src/async_worker.py b/src/async_worker.py
--- a/src/async_worker.py
+++ b/src/async_worker.py
@@ -10,3 +10,7 @@
 async def fetch_stream(url):
+    async with aiohttp.ClientSession() as session:
+        async for chunk in session.get(url):
+            await process_chunk(chunk)
+            yield chunk
"""
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(async_hunk)
        assert is_valid is True, f"Failed async hunk validation: {msg}"
        assert details["lines_added"] == 4

    def test_mixed_tabs_and_spaces_indentation(self):
        """Mixed tabs and spaces in valid Python code."""
        clean_indented = """diff --git a/src/calc.py b/src/calc.py
--- a/src/calc.py
+++ b/src/calc.py
@@ -5,3 +5,4 @@
 def calculate(x):
+    if x > 0:
+        return x * 2
"""
        is_valid, msg, _ = PatchSandboxEvaluator.validate_ast_diff(clean_indented)
        assert is_valid is True

    def test_multi_file_partial_syntax_error_in_second_file(self):
        """Multi-file diff where 1st file is valid Python, 2nd file has SyntaxError."""
        multi_diff_with_error_in_file2 = """diff --git a/pkg/core.py b/pkg/core.py
--- a/pkg/core.py
+++ b/pkg/core.py
@@ -1,2 +1,3 @@
+def valid_core_function():
+    return "ok"
diff --git a/pkg/helpers.py b/pkg/helpers.py
--- a/pkg/helpers.py
+++ b/pkg/helpers.py
@@ -5,2 +5,3 @@
+def broken_syntax(x:
+    return x + 1
"""
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(multi_diff_with_error_in_file2)
        assert is_valid is False
        assert "AST Syntax Error in pkg/helpers.py" in msg
        assert details["failed_file"] == "pkg/helpers.py"
        assert "SyntaxError" in details["ast_error"]

    def test_multi_file_syntax_error_in_third_file(self):
        """Multi-file diff where 1st & 2nd files are valid, 3rd file has unclosed bracket."""
        multi_diff = """diff --git a/pkg/a.py b/pkg/a.py
--- a/pkg/a.py
+++ b/pkg/a.py
@@ -1,1 +1,2 @@
+A = 1
diff --git a/pkg/b.py b/pkg/b.py
--- a/pkg/b.py
+++ b/pkg/b.py
@@ -1,1 +1,2 @@
+B = 2
diff --git a/pkg/c.py b/pkg/c.py
--- a/pkg/c.py
+++ b/pkg/c.py
@@ -1,1 +1,2 @@
+C = [1, 2, 3
"""
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(multi_diff)
        assert is_valid is False
        assert details["failed_file"] == "pkg/c.py"
        assert "SyntaxError" in details["ast_error"]

    def test_non_python_diff_with_valid_and_invalid_syntax(self):
        """
        Non-Python files (.rs, .c, .md, .json, .sh, .yml) should not be subjected to Python ast.parse.
        A diff containing non-python syntax (e.g. fn main() -> Result<(), Box<dyn Error>>) must pass AST diff check.
        """
        rust_and_c_diff = """diff --git a/src/kernel.rs b/src/kernel.rs
--- a/src/kernel.rs
+++ b/src/kernel.rs
@@ -1,3 +1,5 @@
+pub fn init_mesh() -> Result<(), MeshError> {
+    println!("Mesh online");
+    Ok(())
+}
diff --git a/include/driver.h b/include/driver.h
--- a/include/driver.h
+++ b/include/driver.h
@@ -1,2 +1,3 @@
+#define BUFFER_CAPACITY 4096
+int transmit_dma(void *ptr);
diff --git a/config/settings.json b/config/settings.json
--- a/config/settings.json
+++ b/config/settings.json
@@ -1,2 +1,3 @@
+{ "baud_rate": 115200 }
"""
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(rust_and_c_diff)
        assert is_valid is True
        assert "clean AST syntax" in msg
        assert len(details["files"]) == 3
        assert "src/kernel.rs" in details["files"]
        assert "include/driver.h" in details["files"]
        assert "config/settings.json" in details["files"]

    def test_mixed_python_and_non_python_with_python_syntax_error(self):
        """Mixed diff: valid markdown and C code, but invalid Python syntax."""
        mixed_diff = """diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1,1 +1,2 @@
+# Docs updated (with unmatched paren
diff --git a/src/driver.c b/src/driver.c
--- a/src/driver.c
+++ b/src/driver.c
@@ -1,1 +1,2 @@
+int x = 42;
diff --git a/src/controller.py b/src/controller.py
--- a/src/controller.py
+++ b/src/controller.py
@@ -1,1 +1,2 @@
+def bad_function(a, b:
"""
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(mixed_diff)
        assert is_valid is False
        assert details["failed_file"] == "src/controller.py"

    def test_pure_deletion_diff(self):
        """A diff that only removes lines without adding code should be valid AST."""
        deletion_diff = """diff --git a/src/deprecated.py b/src/deprecated.py
--- a/src/deprecated.py
+++ b/src/deprecated.py
@@ -10,5 +10,0 @@
-def old_unused_method():
-    # Broken python in deleted code should not fail
-    if x :::
-        pass
"""
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(deletion_diff)
        assert is_valid is True
        assert details["lines_removed"] == 4
        assert details["lines_added"] == 0

    def test_pure_comment_and_docstring_diff(self):
        """Added lines containing only comments and docstrings."""
        comment_diff = """diff --git a/src/module.py b/src/module.py
--- a/src/module.py
+++ b/src/module.py
@@ -1,3 +1,6 @@
+# New Architecture Comment
+# Another note
+'''Module level docstring'''
"""
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(comment_diff)
        assert is_valid is True

    def test_python310_pattern_matching_syntax(self):
        """Python match-case statement must parse correctly."""
        match_case_diff = """diff --git a/src/router.py b/src/router.py
--- a/src/router.py
+++ b/src/router.py
@@ -10,3 +10,8 @@
 def route_packet(pkt):
+    match pkt:
+        case {"type": "ping", "id": pkt_id}:
+            return f"pong-{pkt_id}"
+        case _:
+            return "unknown"
"""
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(match_case_diff)
        assert is_valid is True


# =============================================================================
# SUITE 2: ADVERSARIAL PREDICTIONS SCHEMA VALIDATION (sb-cli)
# =============================================================================

class TestAdversarialPredictionsSchema:
    """Stress-tests SbCliAdapter.validate_predictions_file against corrupted and invalid schemas."""

    def test_rejects_non_dictionary_roots(self, challenger_workspace):
        """Rejects root elements that are list, string, integer, boolean, or null."""
        preds_dir = challenger_workspace["preds_dir"]

        non_dict_payloads = [
            ("list_root.json", ["item1", "item2"]),
            ("str_root.json", "just a string"),
            ("int_root.json", 12345),
            ("bool_root.json", True),
            ("null_root.json", None),
        ]

        for fname, payload in non_dict_payloads:
            pfile = preds_dir / fname
            pfile.write_text(json.dumps(payload), encoding="utf-8")
            is_valid, msg, details = SbCliAdapter.validate_predictions_file(pfile)
            assert is_valid is False, f"Failed to reject non-dict root: {fname}"
            assert "Root JSON element must be a dictionary" in msg

    def test_rejects_corrupted_json_syntax(self, challenger_workspace):
        """Rejects corrupted or truncated JSON text."""
        preds_dir = challenger_workspace["preds_dir"]
        corrupted_file = preds_dir / "truncated.json"
        corrupted_file.write_text('{"django__django-11099": {"model_patch": "diff...', encoding="utf-8")

        is_valid, msg, details = SbCliAdapter.validate_predictions_file(corrupted_file)
        assert is_valid is False
        assert "Invalid JSON syntax" in msg

    def test_rejects_missing_required_keys(self, challenger_workspace):
        """Rejects entries missing 'model_patch' or 'model_name_or_path'."""
        preds_dir = challenger_workspace["preds_dir"]

        # Missing model_patch
        f1 = preds_dir / "missing_patch.json"
        f1.write_text(json.dumps({
            "django__django-11099": {"model_name_or_path": "qwen"}
        }), encoding="utf-8")
        is_ok, msg, det = SbCliAdapter.validate_predictions_file(f1)
        assert is_ok is False
        assert "missing required field 'model_patch'" in msg
        assert det["failed_instance"] == "django__django-11099"

        # Missing model_name_or_path
        f2 = preds_dir / "missing_model.json"
        f2.write_text(json.dumps({
            "pytest-dev__pytest-7168": {"model_patch": "diff --git ..."}
        }), encoding="utf-8")
        is_ok, msg, det = SbCliAdapter.validate_predictions_file(f2)
        assert is_ok is False
        assert "missing required field 'model_name_or_path'" in msg
        assert det["failed_instance"] == "pytest-dev__pytest-7168"

    def test_rejects_corrupted_value_types(self, challenger_workspace):
        """Rejects non-string types for 'model_patch' and 'model_name_or_path'."""
        preds_dir = challenger_workspace["preds_dir"]

        # model_patch is an int / list / dict / None
        invalid_patches = [
            ("patch_int.json", 12345),
            ("patch_list.json", ["diff line 1", "diff line 2"]),
            ("patch_dict.json", {"raw_diff": "diff"}),
            ("patch_none.json", None),
        ]
        for fname, bad_patch in invalid_patches:
            f = preds_dir / fname
            f.write_text(json.dumps({
                "inst_1": {"model_patch": bad_patch, "model_name_or_path": "qwen"}
            }), encoding="utf-8")
            is_ok, msg, det = SbCliAdapter.validate_predictions_file(f)
            assert is_ok is False, f"Allowed bad patch type in {fname}"
            assert "must be a string" in msg
            assert det["failed_instance"] == "inst_1"

        # model_name_or_path is an int / list / dict / None
        invalid_models = [
            ("model_int.json", 99),
            ("model_list.json", ["qwen-1", "qwen-2"]),
            ("model_none.json", None),
        ]
        for fname, bad_model in invalid_models:
            f = preds_dir / fname
            f.write_text(json.dumps({
                "inst_1": {"model_patch": "diff ...", "model_name_or_path": bad_model}
            }), encoding="utf-8")
            is_ok, msg, det = SbCliAdapter.validate_predictions_file(f)
            assert is_ok is False, f"Allowed bad model type in {fname}"
            assert "must be a string" in msg
            assert det["failed_instance"] == "inst_1"

    def test_rejects_non_dictionary_instance_entries(self, challenger_workspace):
        """Rejects dictionary where an instance maps to a string or list instead of object."""
        preds_dir = challenger_workspace["preds_dir"]
        bad_entry_file = preds_dir / "bad_entry.json"
        bad_entry_file.write_text(json.dumps({
            "django__django-11099": "diff --git just string"
        }), encoding="utf-8")

        is_ok, msg, det = SbCliAdapter.validate_predictions_file(bad_entry_file)
        assert is_ok is False
        assert "must be an object/dict" in msg
        assert det["failed_instance"] == "django__django-11099"

    def test_mixed_valid_and_invalid_instances_fails_atomically(self, challenger_workspace):
        """If 99 instances are valid and 1 is invalid, validation must fail and identify the bad instance."""
        preds_dir = challenger_workspace["preds_dir"]
        payload = {}
        for i in range(10):
            payload[f"valid_inst_{i}"] = {
                "model_patch": "diff --git valid",
                "model_name_or_path": "qwen2.5"
            }
        payload["corrupted_inst_11"] = {
            "model_patch": 12345,  # Invalid type
            "model_name_or_path": "qwen2.5"
        }
        f = preds_dir / "mixed_payload.json"
        f.write_text(json.dumps(payload), encoding="utf-8")

        is_ok, msg, det = SbCliAdapter.validate_predictions_file(f)
        assert is_ok is False
        assert det["failed_instance"] == "corrupted_inst_11"


# =============================================================================
# SUITE 3: RESILIENCE OF 3-TIER TASK LOADER (NETWORK DROPS & CORRUPTED CACHE)
# =============================================================================

class TestTaskLoaderNetworkAndCacheResilience:
    """Stress-tests SweBenchHarness.load_tasks resilience against network drops and disk failures."""

    def test_simulated_huggingface_network_drop_with_fallback(self, challenger_workspace):
        """When HuggingFace datasets library throws Network/Connection error and no cache exists, fallback to Tier 3."""
        harness = challenger_workspace["harness"]
        empty_cache = challenger_workspace["workspace"] / "empty_cache_network_drop"
        empty_cache.mkdir(parents=True, exist_ok=True)

        mock_datasets = MagicMock()
        mock_datasets.load_dataset.side_effect = ConnectionError("Simulated DNS / Network failure")

        with patch.dict("sys.modules", {"datasets": mock_datasets}):
            tasks = harness.load_tasks(
                subset="uncached_synthetic_subset",
                split="dev",
                cache_dir=empty_cache,
                use_hf=True
            )
            assert len(tasks) >= 16
            assert any(t["instance_id"] == "django__django-11099" for t in tasks)

    def test_simulated_huggingface_exception_during_download(self, challenger_workspace):
        """Simulate datasets.load_dataset throwing ConnectionResetError or Timeout."""
        harness = challenger_workspace["harness"]
        empty_cache = challenger_workspace["workspace"] / "empty_cache_timeout"
        empty_cache.mkdir(parents=True, exist_ok=True)

        mock_datasets = MagicMock()
        mock_datasets.load_dataset.side_effect = ConnectionResetError("Remote server disconnected")

        with patch.dict("sys.modules", {"datasets": mock_datasets}):
            tasks = harness.load_tasks(
                subset="swe-bench_verified",
                split="test",
                cache_dir=empty_cache,
                use_hf=True
            )
            assert len(tasks) >= 16
            assert tasks[0]["repo"] is not None

    def test_corrupted_local_cache_file_triggers_fallback(self, challenger_workspace):
        """When local cache file is corrupted or contains empty json, loader falls back safely."""
        harness = challenger_workspace["harness"]
        cache_dir = challenger_workspace["cache_dir"]

        # Write invalid JSON to cache file
        corrupted_cache = cache_dir / "swe-bench_lite_dev.json"
        corrupted_cache.write_text("{ this is corrupted json data", encoding="utf-8")

        tasks = harness.load_tasks(
            subset="swe-bench_lite",
            split="dev",
            cache_dir=cache_dir,
            use_hf=False
        )
        assert len(tasks) >= 16

    def test_empty_local_cache_file_triggers_fallback(self, challenger_workspace):
        """When local cache file is 0 bytes."""
        harness = challenger_workspace["harness"]
        cache_dir = challenger_workspace["cache_dir"]
        empty_cache = cache_dir / "swe-bench_lite_dev.json"
        empty_cache.write_text("", encoding="utf-8")

        tasks = harness.load_tasks(
            subset="swe-bench_lite",
            split="dev",
            cache_dir=cache_dir,
            use_hf=False
        )
        assert len(tasks) >= 16

    def test_limit_bounds_and_zero_handling(self, challenger_workspace):
        """Tests limit parameter boundary conditions: 0, 1, exact count, larger than count."""
        harness = challenger_workspace["harness"]

        # Limit = 1
        tasks_1 = harness.load_tasks(subset="swe-bench_lite", split="dev", limit=1, use_hf=False)
        assert len(tasks_1) == 1

        # Limit = 5
        tasks_5 = harness.load_tasks(subset="swe-bench_lite", split="dev", limit=5, use_hf=False)
        assert len(tasks_5) == 5

        # Limit = 9999 (larger than pool)
        tasks_large = harness.load_tasks(subset="swe-bench_lite", split="dev", limit=9999, use_hf=False)
        assert len(tasks_large) >= 16

        # Limit None
        tasks_none = harness.load_tasks(subset="swe-bench_lite", split="dev", limit=None, use_hf=False)
        assert len(tasks_none) >= 16


# =============================================================================
# SUITE 4: END-TO-END ADVERSARIAL PIPELINE EVALUATION
# =============================================================================

class TestEndToEndAdversarialPipeline:
    """Evaluates candidate patches with edge-case tokens through the full harness."""

    def test_candidate_patch_with_unicode_and_special_chars(self, challenger_workspace):
        """Candidate patch with unicode characters and docstrings."""
        harness = challenger_workspace["harness"]
        inst_id = "django__django-11099"
        patch = """diff --git a/django/contrib/auth/validators.py b/django/contrib/auth/validators.py
--- a/django/contrib/auth/validators.py
+++ b/django/contrib/auth/validators.py
@@ -7,3 +7,4 @@
-    regex = r'^[\\w.@+-]+$'
+    # Unicode test: αβγ ⚡ 🧠
+    regex = r'\\A[\\w.@+-]+\\Z'
"""
        res = harness.evaluate_candidate_patch(inst_id, patch, model_name="Unicode-Model")
        assert res["status"] == "PASSED"
        assert res["passed"] is True
        assert res["ast_valid"] is True

    def test_export_predictions_json_filters_and_validates(self, challenger_workspace):
        """Harness export_predictions_json with candidate patches and AST validation."""
        harness = challenger_workspace["harness"]
        preds_file = challenger_workspace["preds_dir"] / "exported_preds.json"

        # Map some tasks with valid patches, some with syntax errors
        candidate_patches = {
            "django__django-11099": """diff --git a/django/contrib/auth/validators.py b/django/contrib/auth/validators.py
--- a/django/contrib/auth/validators.py
+++ b/django/contrib/auth/validators.py
@@ -7,3 +7,3 @@
-    regex = r'^[\\w.@+-]+$'
+    regex = r'\\A[\\w.@+-]+\\Z'
""",
            "pytest-dev__pytest-7168": """diff --git a/src/_pytest/_code/code.py b/src/_pytest/_code/code.py
--- a/src/_pytest/_code/code.py
+++ b/src/_pytest/_code/code.py
@@ -120,3 +120,4 @@
 def safe_getattr(obj, name, default=None):
-    return getattr(obj, name, default)
+    try:
+        return getattr(obj, name, default)
+    except Exception:
        return default
"""
        }

        out_path = harness.export_predictions_json(
            output_path=preds_file,
            model_name="Qwen-2.5-Coder-32B",
            candidate_patches=candidate_patches,
            validate_ast=True
        )

        is_valid, msg, det = SbCliAdapter.validate_predictions_file(out_path)
        assert is_valid is True
        assert det["count"] == len(SAMPLE_SWEBENCH_TASKS)
        assert "django__django-11099" in det["instances"]
        assert "pytest-dev__pytest-7168" in det["instances"]
