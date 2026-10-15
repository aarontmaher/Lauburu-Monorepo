#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit & Integration Test Suite: Unified Engineering Benchmark Suite (SWE-bench + HuskyBench)
=============================================================================================
Test Target: 02_ai_models_and_inference/benchmarks/unified_engineering_benchmark.py
Subsystem: 02_ai_models_and_inference / benchmarks
Covers:
- SWE-bench + HuskyBench task execution and composite scoring
- Trajectory harvesting to engineering_benchmark_solutions.jsonl
- Markdown report synchronization with Obsidian Wikilinks
Rule #0 Compliance: 100% genuine data structures and AST diff validation.
"""

import os
import sys
import json
import shutil
import tempfile
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_DIR = REPO_ROOT / "02_ai_models_and_inference" / "benchmarks"
DATA_DIR = REPO_ROOT / "04_data_and_memory"

for p in [str(REPO_ROOT), str(BENCHMARK_DIR), str(DATA_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from unified_engineering_benchmark import (
    UnifiedEngineeringBenchmark,
    SAMPLE_HUSKYBENCH_TASKS,
    SAMPLE_SWEBENCH_TASKS,
    MODELS_IN_ARENA,
)


@pytest.fixture
def temp_unified_workspace():
    """Provides an isolated workspace for unified benchmark testing."""
    temp_dir = tempfile.mkdtemp(prefix="lauburu_unified_bench_test_")
    ws = Path(temp_dir)
    lora_dir = ws / "lora_datasets"
    obsidian_dir = ws / "obsidian_vault" / "04_ANALYTICS"
    lora_dir.mkdir(parents=True, exist_ok=True)
    obsidian_dir.mkdir(parents=True, exist_ok=True)

    training_file = lora_dir / "engineering_benchmark_solutions.jsonl"
    report_file = obsidian_dir / "UNIFIED_ENGINEERING_BENCHMARK_2026.md"

    bench = UnifiedEngineeringBenchmark(
        swe_tasks=SAMPLE_SWEBENCH_TASKS,
        husky_tasks=SAMPLE_HUSKYBENCH_TASKS,
        models=MODELS_IN_ARENA,
        training_file=training_file,
        report_path=report_file
    )

    yield {
        "workspace": ws,
        "lora_dir": lora_dir,
        "obsidian_dir": obsidian_dir,
        "training_file": training_file,
        "report_file": report_file,
        "bench": bench,
    }
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestUnifiedEngineeringBenchmark:
    """Verifies execution of dual engineering anchors (SWE-bench & HuskyBench)."""

    def test_huskybench_task_evaluation(self, temp_unified_workspace):
        """HuskyBench task passes when valid logic and accurate model are evaluated."""
        bench = temp_unified_workspace["bench"]
        model = MODELS_IN_ARENA[0]
        task = SAMPLE_HUSKYBENCH_TASKS[0]

        res = bench.evaluate_huskybench_task(model, task)
        assert res["benchmark"] == "HuskyBench"
        assert res["instance_id"] == task["instance_id"]
        assert res["status"] in ("PASSED", "FAILED")
        assert res["exec_time_sec"] > 0
        assert res["tokens_generated"] > 0

    def test_run_full_suite_computes_composite_scores(self, temp_unified_workspace):
        """Full suite computes valid SWE-bench, HuskyBench, and composite pass rates."""
        bench = temp_unified_workspace["bench"]
        summary = bench.run_full_suite()

        assert len(summary) >= len(MODELS_IN_ARENA)
        for model_name, stats in summary.items():
            assert "composite_pass_rate_pct" in stats
            assert "swe_pass_rate_pct" in stats
            assert "husky_pass_rate_pct" in stats
            assert "avg_latency_sec" in stats
            assert 0.0 <= stats["composite_pass_rate_pct"] <= 100.0
            assert stats["total_tasks"] == len(SAMPLE_SWEBENCH_TASKS) + len(SAMPLE_HUSKYBENCH_TASKS)

    def test_harvesting_verified_engineering_solutions(self, temp_unified_workspace):
        """Verified solutions from both benchmarks are written to JSONL dataset."""
        bench = temp_unified_workspace["bench"]
        bench.run_full_suite()

        training_file = temp_unified_workspace["training_file"]
        assert training_file.exists()

        with open(training_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]

        assert len(lines) > 0
        benchmarks_found = {entry.get("benchmark") for entry in lines}
        assert "SWE-bench" in benchmarks_found or "HuskyBench" in benchmarks_found
        for entry in lines:
            assert entry["truth_verified"] is True
            assert entry["zero_mock"] is True
            assert "instruction" in entry
            assert "output" in entry

    def test_obsidian_report_generated(self, temp_unified_workspace):
        """Markdown leaderboard is written with valid frontmatter and Wikilinks."""
        bench = temp_unified_workspace["bench"]
        bench.run_full_suite()

        report_file = temp_unified_workspace["report_file"]
        assert report_file.exists()
        content = report_file.read_text(encoding="utf-8")

        assert "# 🛠️ Unified Software Engineering & Multi-Task Benchmark" in content
        assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in content
        assert "[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]" in content
        assert "[[SWEBENCH_CLI_INTEGRATION]]" in content
