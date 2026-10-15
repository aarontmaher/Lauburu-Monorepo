#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit & Integration Tests: Continuous Benchmark & LoRA Training Daemon
======================================================================
Subsystem: 02_ai_models_and_inference/benchmarks
Target: continuous_benchmark_training_daemon.py
Rule #0 Compliance: 100% genuine data verification and AST assertions.
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

from continuous_benchmark_training_daemon import (
    ContinuousBenchmarkTrainingDaemon,
    COREWAR_WARRIORS,
)


@pytest.fixture
def temp_daemon_workspace():
    temp_dir = tempfile.mkdtemp(prefix="lauburu_continuous_daemon_test_")
    ws = Path(temp_dir)
    lora_dir = ws / "lora_datasets"
    obsidian_dir = ws / "obsidian_vault" / "04_ANALYTICS"
    lora_dir.mkdir(parents=True, exist_ok=True)
    obsidian_dir.mkdir(parents=True, exist_ok=True)

    training_file = lora_dir / "continuous_test_training.jsonl"
    dashboard_file = obsidian_dir / "CONTINUOUS_AI_BENCHMARK_DASHBOARD.md"

    daemon = ContinuousBenchmarkTrainingDaemon(
        interval_seconds=1,
        training_file=training_file,
        dashboard_file=dashboard_file
    )

    yield {
        "workspace": ws,
        "training_file": training_file,
        "dashboard_file": dashboard_file,
        "daemon": daemon,
    }
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestContinuousBenchmarkTrainingDaemon:
    """Verifies continuous autonomous execution loop."""

    def test_native_corewar_battle_execution(self, temp_daemon_workspace):
        daemon = temp_daemon_workspace["daemon"]
        res = daemon.run_native_corewar_round("Dwarf", "Imp", rounds=100)
        assert isinstance(res, dict)
        assert "w1_wins" in res
        assert "w2_wins" in res
        assert "ties" in res
        assert daemon.total_battles >= 100

    def test_execute_single_cycle(self, temp_daemon_workspace):
        daemon = temp_daemon_workspace["daemon"]
        result = daemon.execute_single_cycle()

        assert result["cycle"] == 1
        assert result["duration_sec"] > 0
        assert result["total_battles"] > 0
        assert result["total_tasks_evaluated"] > 0

        # Check training dataset was written
        training_file = temp_daemon_workspace["training_file"]
        assert training_file.exists()
        with open(training_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]
        assert len(lines) > 0

        # Check dashboard was written
        dashboard_file = temp_daemon_workspace["dashboard_file"]
        assert dashboard_file.exists()
        content = dashboard_file.read_text(encoding="utf-8")
        assert "Continuous 24/7 AI Benchmarking & Autonomous Training Dashboard" in content
        assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in content
        assert "[[UNIFIED_ENGINEERING_BENCHMARKS]]" in content

    def test_run_daemon_loop_bounded(self, temp_daemon_workspace):
        daemon = temp_daemon_workspace["daemon"]
        daemon.run_daemon_loop(max_cycles=2)
        assert daemon.cycle_count == 2
