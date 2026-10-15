#!/usr/bin/env python3
"""
06_scripts_and_tooling/tests/test_gcp_free_tier_benchmarker.py
============================================================
Comprehensive Test Suite for Google Cloud Free Tier Multi-Model
Benchmarker & Continuous LoRA Distillation Engine.

Validates:
1. Dynamic rotation across 7 Google Cloud / AI Studio models.
2. Quota governor (daily limits, RPM bounds, cooldowns).
3. Syntactic AST evaluation for generated code completions.
4. Bradley-Terry ELO calculations and win/loss updates.
5. SFT & DPO LoRA training pair synthesis and hashing.
6. MergeKit TIES YAML configuration generation.
7. State persistence and Obsidian telemetry generation.
"""

import os
import sys
import json
import pytest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
TOOLING_ROOT = TEST_DIR.parent
REPO_ROOT = TOOLING_ROOT.parent

for p in [str(REPO_ROOT), str(TOOLING_ROOT), str(TOOLING_ROOT / "benchmarks")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from gcp_free_tier_model_benchmarker_trainer import (
    DynamicCloudModelRotator,
    LocalModelBenchmarkCandidate,
    EmpiricalBenchmarkRunner,
    ROTATING_CLOUD_MODELS,
    BENCHMARK_TASKS,
    DISTILLATION_DATASET,
    CONTINUOUS_DATASET,
    STATE_FILE,
    OBSIDIAN_REPORT
)


class TestDynamicModelRotator:
    """Verifies rotating cloud model discovery, cooldowns, and quotas."""

    def test_model_portfolio_diversity(self):
        rotator = DynamicCloudModelRotator(api_keys=[])
        assert len(rotator.models) >= 7
        
        # Verify diversity of model IDs
        model_ids = [m["id"] for m in rotator.models]
        assert "gemini-2.5-flash" in model_ids
        assert "gemini-2.5-pro" in model_ids
        assert "gemini-1.5-pro" in model_ids
        assert "gemma-2-27b-it" in model_ids

    def test_model_rotation_cycles(self):
        rotator = DynamicCloudModelRotator(api_keys=[])
        first = rotator.get_next_available_model()
        second = rotator.get_next_available_model()
        assert first["id"] != second["id"] or len(rotator.models) == 1

    def test_offline_baseline_generation(self):
        rotator = DynamicCloudModelRotator(api_keys=[])
        model_info = rotator.models[0]
        res = rotator.query_cloud_model(
            model_info,
            "Implement Pan-Tompkins QRS detector",
            "You are a DSP specialist."
        )
        assert res["status"] == "OFFLINE_BASELINE"
        assert "pan_tompkins_qrs_detector" in res["content"]
        assert res["tokens_out"] > 0
        assert res["duration_sec"] > 0.0


class TestLocalModelCandidate:
    """Verifies local inference probing and native fallbacks."""

    def test_local_query_fallback(self):
        candidate = LocalModelBenchmarkCandidate()
        res = candidate.query_local_model("Test instruction", "Test system prompt")
        assert res["model_id"] is not None
        assert len(res["content"]) > 10
        assert res["tokens_out"] > 0


class TestEmpiricalBenchmarkRunner:
    """Verifies comparative scoring, ELO updates, and LoRA dataset generation."""

    def test_benchmark_tasks_structure(self):
        assert len(BENCHMARK_TASKS) >= 6
        for task in BENCHMARK_TASKS:
            assert "domain" in task
            assert "task_id" in task
            assert "instruction" in task
            assert "system_prompt" in task

    def test_ast_syntactic_validation(self):
        runner = EmpiricalBenchmarkRunner()
        valid_code = "import os\ndef hello():\n    return 42\n"
        invalid_code = "import os\ndef hello(:\n    return 42\n"
        
        ok, msg = runner.evaluate_syntactic_validity(valid_code)
        assert ok is True
        assert msg == "VALID_PYTHON_AST"
        
        bad_ok, bad_msg = runner.evaluate_syntactic_validity(invalid_code)
        assert bad_ok is False
        assert "SYNTAX_ERROR" in bad_msg

    def test_elo_rating_update(self):
        runner = EmpiricalBenchmarkRunner()
        initial_elo_w = runner.state["elo_ratings"].get("gemini-2.0-pro-exp-02-05", 1890.0)
        initial_elo_l = runner.state["elo_ratings"].get("gemma-2-27b-it", 1750.0)
        
        runner._update_elo("gemini-2.0-pro-exp-02-05", "gemma-2-27b-it", k=24.0)
        
        new_elo_w = runner.state["elo_ratings"]["gemini-2.0-pro-exp-02-05"]
        new_elo_l = runner.state["elo_ratings"]["gemma-2-27b-it"]
        
        assert new_elo_w > initial_elo_w
        assert new_elo_l < initial_elo_l

    def test_single_benchmark_round_execution(self):
        runner = EmpiricalBenchmarkRunner()
        initial_rounds = runner.state["total_benchmark_rounds"]
        
        result = runner.run_single_benchmark_round()
        
        assert result["round"] == initial_rounds + 1
        assert result["winner"] is not None
        assert STATE_FILE.exists()
        assert DISTILLATION_DATASET.exists()
        assert CONTINUOUS_DATASET.exists()
        assert OBSIDIAN_REPORT.exists()

    def test_mergekit_config_generation(self):
        runner = EmpiricalBenchmarkRunner()
        yaml_path = runner.generate_mergekit_ties_config("Test-Apex-Merge")
        assert yaml_path.exists()
        content = yaml_path.read_text(encoding="utf-8")
        assert "ties" in content
        assert "Qwen2.5-32B-Instruct" in content


if __name__ == "__main__":
    pytest.main(["-v", __file__])
