#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit & Integration Test Suite: SWE-bench Benchmark & Continuous Training Integration
=====================================================================================
Test Target: 02_ai_models_and_inference/benchmarks/swe_bench_harness.py
Subsystem: 02_ai_models_and_inference / benchmarks
Covers:
- Feature 1: SWE-bench Task Ingestion (swe-bench_lite & swe-bench_verified, 3-tier loader)
- Feature 2: Multi-File AST Diff Parsing, Validation & Syntax Error Detection
- Feature 3: SWE-bench Benchmark Evaluation & Multi-Model Arena
- Sandboxed Patch Evaluation & Candidate Patch Evaluation
- Canonical preds.json Export & Schema Validation
- Continuous LoRA Dataset Harvesting to swe_bench_solutions.jsonl and continuous_lora_dataset.jsonl
- Obsidian Vault Markdown Leaderboard Synchronization
- End-to-End Workflow with MLX Trainer & EloPromotionGate
Rule #0 Compliance: 100% genuine test cases and real AST diff parsing.
"""

import os
import sys
import json
import time
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any

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
from elo_promotion_gate import EloPromotionGate
from mlx_qlora_trainer import MLXQLoRATrainer, DynamicRamGovernor


@pytest.fixture
def temp_swe_workspace():
    """Provides an isolated workspace for SWE-bench integration tests."""
    temp_dir = tempfile.mkdtemp(prefix="lauburu_swe_bench_test_")
    ws = Path(temp_dir)
    data_dir = ws / "04_data_and_memory"
    lora_dir = ws / "lora_datasets"
    obsidian_dir = ws / "obsidian_vault" / "04_ANALYTICS"
    cache_dir = data_dir / "swe_bench_datasets"

    data_dir.mkdir(parents=True, exist_ok=True)
    lora_dir.mkdir(parents=True, exist_ok=True)
    obsidian_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

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
        "training_file": training_file,
        "report_file": report_file,
        "harness": harness,
    }
    shutil.rmtree(temp_dir, ignore_errors=True)


# ===========================================================================
# 1. Patch Syntax & Multi-File AST Diff Parsing & Validation
# ===========================================================================

class TestPatchSandboxEvaluator:
    """Verifies multi-file patch diff parsing, AST validation, and sandbox criteria."""

    def test_valid_unified_diff_syntax_detection(self):
        """Valid diff syntax with headers and hunks passes validation."""
        valid_diff = """diff --git a/django/contrib/auth/validators.py b/django/contrib/auth/validators.py
--- a/django/contrib/auth/validators.py
+++ b/django/contrib/auth/validators.py
@@ -7,3 +7,3 @@
-    regex = r'^[\\w.@+-]+$'
+    regex = r'\\A[\\w.@+-]+\\Z'
"""
        is_valid, msg = PatchSandboxEvaluator.validate_diff_syntax(valid_diff)
        assert is_valid is True
        assert "Valid" in msg

    def test_malformed_patch_syntax_rejection(self):
        """Malformed or empty patch syntax is rejected cleanly."""
        invalid_diffs = [
            "",
            "   ",
            "This is just raw text without patch markers",
            None,
        ]
        for diff in invalid_diffs:
            is_valid, msg = PatchSandboxEvaluator.validate_diff_syntax(diff)
            assert is_valid is False
            assert "Malformed" in msg or "Empty" in msg

    def test_parse_unified_diff_single_file(self):
        """Parses single-file git diff into structured dictionary."""
        diff = """diff --git a/django/contrib/auth/validators.py b/django/contrib/auth/validators.py
--- a/django/contrib/auth/validators.py
+++ b/django/contrib/auth/validators.py
@@ -7,3 +7,3 @@
-    regex = r'^[\\w.@+-]+$'
+    regex = r'\\A[\\w.@+-]+\\Z'
"""
        parsed = PatchSandboxEvaluator.parse_unified_diff(diff)
        assert "django/contrib/auth/validators.py" in parsed
        file_info = parsed["django/contrib/auth/validators.py"]
        assert file_info["is_python"] is True
        assert len(file_info["added_lines"]) == 1
        assert "regex = r'\\A[\\w.@+-]+\\Z'" in file_info["added_lines"][0]
        assert len(file_info["removed_lines"]) == 1

    def test_parse_unified_diff_multi_file(self):
        """Parses multi-file diff with multiple Python files."""
        multi_diff = """diff --git a/src/app/main.py b/src/app/main.py
--- a/src/app/main.py
+++ b/src/app/main.py
@@ -10,3 +10,4 @@
 def run():
-    return False
+    res = compute()
+    return res
diff --git a/src/app/utils.py b/src/app/utils.py
--- a/src/app/utils.py
+++ b/src/app/utils.py
@@ -5,2 +5,4 @@
+def compute():
+    return 42
"""
        parsed = PatchSandboxEvaluator.parse_unified_diff(multi_diff)
        assert len(parsed) == 2
        assert "src/app/main.py" in parsed
        assert "src/app/utils.py" in parsed
        assert len(parsed["src/app/main.py"]["added_lines"]) == 2
        assert len(parsed["src/app/utils.py"]["added_lines"]) == 2

    def test_validate_ast_code_valid_and_scopes(self):
        """Valid top-level and indented code blocks pass AST validation."""
        # Top-level expression
        ok, err = PatchSandboxEvaluator.validate_ast_code("x = 42\ny = x + 10")
        assert ok is True
        assert err is None

        # Indented function body
        indented_code = "    if flag:\n        return calculate(value)\n    return None"
        ok, err = PatchSandboxEvaluator.validate_ast_code(indented_code)
        assert ok is True
        assert err is None

        # Async statement
        async_code = "    async with session.get(url) as response:\n        return await response.text()"
        ok, err = PatchSandboxEvaluator.validate_ast_code(async_code)
        assert ok is True
        assert err is None

    def test_validate_ast_code_syntax_error_rejection(self):
        """Invalid Python syntax is detected and rejected with SyntaxError."""
        # Unclosed parenthesis
        bad_code_1 = "def calculate(a, b:\n    return a + b"
        ok, err = PatchSandboxEvaluator.validate_ast_code(bad_code_1)
        assert ok is False
        assert "SyntaxError" in err

        # Unclosed bracket
        bad_code_2 = "x = [1, 2, 3"
        ok, err = PatchSandboxEvaluator.validate_ast_code(bad_code_2)
        assert ok is False
        assert "SyntaxError" in err

        # Invalid token / illegal syntax
        bad_code_3 = "def 123_invalid(): pass"
        ok, err = PatchSandboxEvaluator.validate_ast_code(bad_code_3)
        assert ok is False
        assert "SyntaxError" in err

    def test_validate_ast_diff_clean_multi_file(self):
        """Multi-file diff with clean syntax parses and validates cleanly."""
        multi_diff = """diff --git a/src/app/main.py b/src/app/main.py
--- a/src/app/main.py
+++ b/src/app/main.py
@@ -10,3 +10,4 @@
 def run():
-    return False
+    res = compute()
+    return res
diff --git a/src/app/utils.py b/src/app/utils.py
--- a/src/app/utils.py
+++ b/src/app/utils.py
@@ -5,2 +5,4 @@
+def compute():
+    return 42
"""
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(multi_diff)
        assert is_valid is True
        assert "clean AST syntax" in msg
        assert len(details["files"]) == 2
        assert details["lines_added"] == 4
        assert details["lines_removed"] == 1

    def test_validate_ast_diff_detects_syntax_error_in_one_file(self):
        """Detects syntax error in multi-file diff when one file has invalid syntax."""
        broken_diff = """diff --git a/src/app/main.py b/src/app/main.py
--- a/src/app/main.py
+++ b/src/app/main.py
@@ -10,3 +10,4 @@
 def run():
-    return False
+    res = compute()
+    return res
diff --git a/src/app/utils.py b/src/app/utils.py
--- a/src/app/utils.py
+++ b/src/app/utils.py
@@ -5,2 +5,4 @@
+def compute(:
+    return 42
"""
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(broken_diff)
        assert is_valid is False
        assert "AST Syntax Error in src/app/utils.py" in msg
        assert details["failed_file"] == "src/app/utils.py"
        assert "SyntaxError" in details["ast_error"]

    def test_validate_ast_diff_handles_non_python_files(self):
        """Non-Python files (e.g. .md, .json) in diff do not trigger Python AST errors."""
        mixed_diff = """diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1,2 +1,3 @@
 # Project
+This is markdown documentation. (Unmatched paren is fine here)
diff --git a/src/app/main.py b/src/app/main.py
--- a/src/app/main.py
+++ b/src/app/main.py
@@ -1,2 +1,3 @@
+def valid_func():
+    return True
"""
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(mixed_diff)
        assert is_valid is True
        assert "README.md" in details["files"]
        assert "src/app/main.py" in details["files"]

    def test_evaluate_patch_against_django_task(self):
        """Evaluates authentic regex patch against django validator task."""
        django_task = SAMPLE_SWEBENCH_TASKS[0]
        assert "django" in django_task["instance_id"]

        patch = django_task["sample_patch"]
        eval_res = PatchSandboxEvaluator.evaluate_patch_against_task(django_task, patch)
        assert eval_res["passed"] is True
        assert eval_res["golden_test"] == "test_username_validator_newline_rejection"
        assert eval_res["lines_added"] >= 1
        assert eval_res["lines_removed"] >= 1

    def test_evaluate_patch_against_movesense_task(self):
        """Evaluates 512Hz buffer lag interpolation patch against biometrics DSP task."""
        dsp_task = [t for t in SAMPLE_SWEBENCH_TASKS if "movesense" in t["instance_id"]][0]
        patch = dsp_task["sample_patch"]

        eval_res = PatchSandboxEvaluator.evaluate_patch_against_task(dsp_task, patch)
        assert eval_res["passed"] is True
        assert eval_res["golden_test"] == "test_pan_tompkins_512hz_jitter_resilience"


# ===========================================================================
# 2. SWE-bench Task Ingestion & Candidate Patch Evaluation
# ===========================================================================

class TestSweBenchTaskIngestion:
    """Verifies resilient 3-tier loading for swe-bench_lite and swe-bench_verified."""

    def test_load_tasks_swe_bench_lite(self, temp_swe_workspace):
        """Loads tasks for swe-bench_lite subset."""
        harness = temp_swe_workspace["harness"]
        tasks = harness.load_tasks(subset="swe-bench_lite", split="dev")
        assert len(tasks) >= 5
        for t in tasks:
            assert "instance_id" in t
            assert "problem_statement" in t
            assert "sample_patch" in t

    def test_load_tasks_swe_bench_verified(self, temp_swe_workspace):
        """Loads tasks for swe-bench_verified subset."""
        harness = temp_swe_workspace["harness"]
        tasks = harness.load_tasks(subset="swe-bench_verified", split="dev")
        assert len(tasks) >= 5
        for t in tasks:
            assert "instance_id" in t
            assert "repo" in t
            assert "golden_test" in t

    def test_load_tasks_with_limit(self, temp_swe_workspace):
        """Applies limit parameter correctly during task ingestion."""
        harness = temp_swe_workspace["harness"]
        tasks = harness.load_tasks(subset="swe-bench_lite", split="dev", limit=3)
        assert len(tasks) == 3

    def test_load_tasks_offline_fallback(self, temp_swe_workspace):
        """Loads offline curated fallback tasks when cache is empty and HF is disabled."""
        harness = temp_swe_workspace["harness"]
        empty_cache = temp_swe_workspace["workspace"] / "empty_cache_dir"
        empty_cache.mkdir(parents=True, exist_ok=True)

        tasks = harness.load_tasks(
            subset="non_existent_subset",
            split="dev",
            cache_dir=empty_cache,
            use_hf=False
        )
        assert len(tasks) >= 16

    def test_evaluate_candidate_patch_valid(self, temp_swe_workspace):
        """Evaluates valid candidate patch for an instance_id."""
        harness = temp_swe_workspace["harness"]
        task = SAMPLE_SWEBENCH_TASKS[0]
        inst_id = task["instance_id"]
        patch = task["sample_patch"]

        res = harness.evaluate_candidate_patch(inst_id, patch, model_name="Qwen-Coder-Test")
        assert res["status"] == "PASSED"
        assert res["passed"] is True
        assert res["ast_valid"] is True
        assert res["golden_test"] == task["golden_test"]
        assert res["lines_added"] >= 1

    def test_evaluate_candidate_patch_invalid_ast(self, temp_swe_workspace):
        """Rejects candidate patch containing invalid AST syntax."""
        harness = temp_swe_workspace["harness"]
        inst_id = "django__django-11099"
        broken_patch = """diff --git a/django/contrib/auth/validators.py b/django/contrib/auth/validators.py
--- a/django/contrib/auth/validators.py
+++ b/django/contrib/auth/validators.py
@@ -7,3 +7,3 @@
-    regex = r'^[\\w.@+-]+$'
+    regex = (r'\\A[\\w.@+-]+\\Z'
"""
        res = harness.evaluate_candidate_patch(inst_id, broken_patch, model_name="Bad-Model")
        assert res["status"] == "FAILED"
        assert res["passed"] is False
        assert res["ast_valid"] is False
        assert "AST Syntax Error" in res["reason"]

    def test_evaluate_candidate_patch_unknown_instance(self, temp_swe_workspace):
        """Handles non-existent task instance gracefully."""
        harness = temp_swe_workspace["harness"]
        res = harness.evaluate_candidate_patch("unknown__unknown-9999", "diff --git ...")
        assert res["status"] == "FAILED"
        assert res["passed"] is False
        assert "not found" in res["reason"]


# ===========================================================================
# 3. Canonical Predictions Export & Schema Validation
# ===========================================================================

class TestPredictionsExportAndValidation:
    """Verifies preds.json formatting, AST gating, and SbCliAdapter schema verification."""

    def test_export_predictions_json_canonical_schema(self, temp_swe_workspace):
        """export_predictions_json produces valid schema."""
        harness = temp_swe_workspace["harness"]
        out_file = temp_swe_workspace["data_dir"] / "test_preds.json"

        res_path = harness.export_predictions_json(
            output_path=out_file,
            model_name="Qwen-AgentWorld-35B-A3B",
            validate_ast=True
        )

        assert res_path.exists()
        with open(res_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == len(SAMPLE_SWEBENCH_TASKS)
        for task in SAMPLE_SWEBENCH_TASKS:
            inst_id = task["instance_id"]
            assert inst_id in data
            assert data[inst_id]["model_name_or_path"] == "Qwen-AgentWorld-35B-A3B"
            assert "model_patch" in data[inst_id]

    def test_validate_predictions_file_valid(self, temp_swe_workspace):
        """SbCliAdapter.validate_predictions_file certifies valid canonical schema."""
        harness = temp_swe_workspace["harness"]
        preds_file = temp_swe_workspace["data_dir"] / "valid_preds.json"
        harness.export_predictions_json(output_path=preds_file, model_name="qwen-2.5")

        is_valid, msg, details = SbCliAdapter.validate_predictions_file(preds_file)
        assert is_valid is True
        assert "Valid canonical predictions schema" in msg
        assert details["count"] >= 16

    def test_validate_predictions_file_invalid_structures(self, temp_swe_workspace):
        """SbCliAdapter.validate_predictions_file rejects invalid schemas."""
        preds_dir = temp_swe_workspace["data_dir"]

        # Missing file
        is_valid, msg, _ = SbCliAdapter.validate_predictions_file(preds_dir / "non_existent.json")
        assert is_valid is False
        assert "does not exist" in msg

        # Root not a dict
        bad_file_1 = preds_dir / "bad_root.json"
        bad_file_1.write_text("[\"item1\", \"item2\"]", encoding="utf-8")
        is_valid, msg, _ = SbCliAdapter.validate_predictions_file(bad_file_1)
        assert is_valid is False
        assert "Root JSON element must be a dictionary" in msg

        # Missing model_patch
        bad_file_2 = preds_dir / "missing_patch.json"
        bad_file_2.write_text(json.dumps({"django__django-11099": {"model_name_or_path": "qwen"}}), encoding="utf-8")
        is_valid, msg, _ = SbCliAdapter.validate_predictions_file(bad_file_2)
        assert is_valid is False
        assert "missing required field 'model_patch'" in msg

        # Missing model_name_or_path
        bad_file_3 = preds_dir / "missing_model.json"
        bad_file_3.write_text(json.dumps({"django__django-11099": {"model_patch": "diff..."}}), encoding="utf-8")
        is_valid, msg, _ = SbCliAdapter.validate_predictions_file(bad_file_3)
        assert is_valid is False
        assert "missing required field 'model_name_or_path'" in msg


# ===========================================================================
# 4. SWE-bench Benchmark Suite & Harvesting
# ===========================================================================

class TestSweBenchSuiteAndHarvesting:
    """Verifies SWE-bench execution, trajectory harvesting, and Obsidian sync."""

    def test_sample_tasks_schema_completeness(self):
        """All canonical benchmark tasks contain mandatory fields."""
        mandatory_keys = [
            "instance_id", "repo", "problem_statement",
            "difficulty", "domain", "golden_test", "sample_patch"
        ]
        for task in SAMPLE_SWEBENCH_TASKS:
            for k in mandatory_keys:
                assert k in task, f"Task {task.get('instance_id')} missing mandatory key: {k}"

    def test_run_benchmark_suite_generates_summary(self, temp_swe_workspace):
        """Benchmark suite evaluates models and returns valid pass rates and latencies."""
        harness = temp_swe_workspace["harness"]
        summary = harness.run_benchmark_suite()

        assert len(summary) >= len(MODELS_IN_ARENA)
        for model_name, stats in summary.items():
            assert "passed" in stats
            assert "total" in stats
            assert "pass_rate_pct" in stats
            assert "avg_time_sec" in stats
            assert "avg_tokens" in stats
            assert stats["total"] == len(SAMPLE_SWEBENCH_TASKS)
            assert 0.0 <= stats["pass_rate_pct"] <= 100.0
            assert stats["avg_time_sec"] > 0.0
            assert stats["avg_tokens"] > 0

    def test_harvest_verified_trajectories_zero_mock(self, temp_swe_workspace):
        """Verified trajectories are written to JSONL with 100% Rule #0 compliance."""
        harness = temp_swe_workspace["harness"]
        harness.run_benchmark_suite()

        training_file = temp_swe_workspace["training_file"]
        assert training_file.exists()

        with open(training_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]

        assert len(lines) > 0
        for entry in lines:
            assert "instruction" in entry
            assert "input" in entry
            assert "output" in entry
            assert "truth_verified" in entry
            assert entry["truth_verified"] is True
            assert entry["zero_mock"] is True
            assert entry["truth_compliance_pct"] == 100.0
            assert "Verified Solution Patch" in entry["output"]

    def test_obsidian_report_generated_with_wikilinks(self, temp_swe_workspace):
        """SWE-bench leaderboard generates valid Markdown with Wikilinks in Obsidian."""
        harness = temp_swe_workspace["harness"]
        harness.run_benchmark_suite()

        report_file = temp_swe_workspace["report_file"]
        assert report_file.exists()
        content = report_file.read_text(encoding="utf-8")

        assert "# 💻 SWE-bench Mesh Leaderboard" in content
        assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in content
        assert "[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]" in content
        assert "[[LOCAL_LMARENA_LEADERBOARD_2026]]" in content


# ===========================================================================
# 5. End-to-End Continuous Training & ELO Gate Integration
# ===========================================================================

class TestSweBenchEndToEndWorkflow:
    """Verifies end-to-end integration between SWE-bench, MLX trainer, and ELO gate."""

    def test_e2e_swe_bench_training_dataset_ingestion(self, temp_swe_workspace):
        """Harvested SWE-bench solutions are ingested by MLXQLoRATrainer.prepare_dataset."""
        harness = temp_swe_workspace["harness"]
        harness.run_benchmark_suite()

        ws = temp_swe_workspace["workspace"]
        data_dir = temp_swe_workspace["data_dir"]
        lora_dir = temp_swe_workspace["lora_dir"]

        # Copy harvested solutions into data_dir source file
        harvested = temp_swe_workspace["training_file"].read_text()
        (data_dir / "continuous_lora_dataset.jsonl").write_text(harvested)

        trainer = MLXQLoRATrainer(
            data_dir=data_dir,
            adapter_out_dir=ws / "adapters",
            governor=DynamicRamGovernor(),
        )

        prepared_ds = trainer.prepare_dataset(stage=1)
        assert prepared_ds.exists()

        with open(prepared_ds, "r", encoding="utf-8") as f:
            prepared_records = [json.loads(l) for l in f if l.strip()]

        assert len(prepared_records) > 0
        all_text = " ".join([m["content"] for r in prepared_records for m in r.get("messages", [])])
        assert "SWE-bench" in all_text

    def test_e2e_swe_bench_score_drives_elo_promotion(self, temp_swe_workspace):
        """Model achieving high SWE-bench pass rate passes EloPromotionGate."""
        ws = temp_swe_workspace["workspace"]
        adapter_path = ws / "adapters" / "swe_bench_champion"
        symlink_dir = ws / "lora_adapters"
        adapter_path.mkdir(parents=True, exist_ok=True)
        symlink_dir.mkdir(parents=True, exist_ok=True)

        gate = EloPromotionGate(
            leaderboard_path=ws / "leaderboard.json",
            promotion_log_path=ws / "promo.jsonl",
            obsidian_report_path=ws / "report.md"
        )

        # High quality score in SWE-bench domain
        quality_map = {
            "SOFTWARE_ENGINEERING": 0.96,
            "SYS_ARCH_PLANNING": 0.94,
            "MATH_AND_ALGORITHMS": 0.92,
            "BIOMETRICS_AND_DSP": 0.90,
            "CYBER_ADVERSARIAL": 0.91,
        }

        promoted, win_rate, snapshot = gate.evaluate_and_promote(
            adapter_path=str(adapter_path),
            challenger_adapters=["DeepSeek-R1-32B", "Candidate_Baseline"],
            min_win_rate=0.65,
            target_symlink_dir=str(symlink_dir),
            candidate_quality_map=quality_map
        )

        assert promoted is True
        assert win_rate >= 0.65
        assert (symlink_dir / "active_production_adapter").resolve() == adapter_path.resolve()
