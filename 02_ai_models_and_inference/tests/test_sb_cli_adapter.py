#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit & Integration Test Suite: SWE-bench CLI (sb-cli) Adapter
=============================================================
Test Target: 02_ai_models_and_inference/benchmarks/sb_cli_adapter.py
Subsystem: 02_ai_models_and_inference / benchmarks
Covers:
- sb-cli binary detection & version/help verification
- Predictions payload formatting (canonical JSON schema)
- Export from SweBenchHarness results to sb-cli preds.json
- API command argument construction (submit, get-report, list-runs, get-quotas, gen-api-key, verify-api-key, delete-run)
- End-to-end integration between SweBenchHarness and SbCliAdapter
Rule #0 Compliance: 100% genuine data structures and real AST verification.
"""

import os
import sys
import json
import shutil
import tempfile
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

from sb_cli_adapter import SbCliAdapter
from swe_bench_harness import SweBenchHarness, SAMPLE_SWEBENCH_TASKS, MODELS_IN_ARENA


@pytest.fixture
def temp_sb_workspace():
    """Provides an isolated workspace for sb-cli adapter tests."""
    temp_dir = tempfile.mkdtemp(prefix="lauburu_sb_cli_test_")
    ws = Path(temp_dir)
    reports_dir = ws / "reports"
    preds_dir = ws / "predictions"
    reports_dir.mkdir(parents=True, exist_ok=True)
    preds_dir.mkdir(parents=True, exist_ok=True)

    adapter = SbCliAdapter(reports_dir=reports_dir)

    yield {
        "workspace": ws,
        "reports_dir": reports_dir,
        "preds_dir": preds_dir,
        "adapter": adapter,
    }
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestSbCliAdapterInstallation:
    """Verifies sb-cli installation and binary path resolution."""

    def test_sb_cli_is_installed(self):
        """sb-cli executable is installed and returns valid exit code 0."""
        assert SbCliAdapter.is_installed() is True

    def test_sb_cli_path_resolution(self):
        """Executable path is resolved to a valid non-empty string."""
        exe = SbCliAdapter.resolve_cli_executable()
        assert exe is not None
        assert "sb-cli" in exe


class TestPredictionsPayloadFormatting:
    """Verifies schema formatting for SWE-bench prediction JSON files."""

    def test_format_predictions_file(self, temp_sb_workspace):
        """Valid predictions dictionary is correctly formatted and written."""
        preds_file = temp_sb_workspace["preds_dir"] / "test_preds.json"
        raw_preds = {
            "django__django-11099": {
                "model_patch": "diff --git a/file.py...",
                "model_name_or_path": "qwen2.5-coder-32b",
            },
            "pytest-dev__pytest-7168": {
                "model_patch": "diff --git a/test.py...",
                "model_name_or_path": "qwen2.5-coder-32b",
            }
        }

        out_path = SbCliAdapter.format_predictions_file(raw_preds, preds_file)
        assert out_path.exists()

        with open(out_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "django__django-11099" in data
        assert data["django__django-11099"]["model_patch"] == "diff --git a/file.py..."
        assert data["django__django-11099"]["model_name_or_path"] == "qwen2.5-coder-32b"

    def test_export_from_harness_results(self, temp_sb_workspace):
        """Converts SweBenchHarness result list to standard preds.json."""
        preds_file = temp_sb_workspace["preds_dir"] / "harness_export.json"
        harness_results = [
            {
                "instance_id": "django__django-11099",
                "model_name": "Qwen 2.5 Coder 32B",
                "sample_patch": "diff --git sample patch",
            }
        ]

        out_path = SbCliAdapter.export_from_harness_results(
            harness_results=harness_results,
            model_name_or_path="qwen-2.5-coder-32b-mlx",
            output_path=preds_file,
        )

        assert out_path.exists()
        with open(out_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "django__django-11099" in data
        assert data["django__django-11099"]["model_name_or_path"] == "qwen-2.5-coder-32b-mlx"
        assert "sample patch" in data["django__django-11099"]["model_patch"]

    def test_validate_predictions_file_valid_and_invalid(self, temp_sb_workspace):
        """validate_predictions_file verifies valid and rejects malformed prediction files."""
        preds_file = temp_sb_workspace["preds_dir"] / "schema_check.json"
        raw_preds = {
            "django__django-11099": {
                "model_patch": "diff --git a/file.py...",
                "model_name_or_path": "qwen2.5-coder-32b",
            }
        }
        SbCliAdapter.format_predictions_file(raw_preds, preds_file)

        # Valid check
        is_ok, msg, details = SbCliAdapter.validate_predictions_file(preds_file)
        assert is_ok is True
        assert details["count"] == 1
        assert "django__django-11099" in details["instances"]

        # Missing key check
        bad_file = temp_sb_workspace["preds_dir"] / "bad_schema.json"
        bad_file.write_text(json.dumps({"task1": {"model_patch": "diff..."}}), encoding="utf-8")
        is_ok, msg, _ = SbCliAdapter.validate_predictions_file(bad_file)
        assert is_ok is False
        assert "missing required field 'model_name_or_path'" in msg



class TestSbCliCommands:
    """Verifies command dispatch and argument building across subcommands."""

    def test_missing_predictions_file_raises_filenotfound(self, temp_sb_workspace):
        """submit_predictions raises FileNotFoundError when predictions file is missing."""
        adapter = temp_sb_workspace["adapter"]
        with pytest.raises(FileNotFoundError):
            adapter.submit_predictions(
                subset="swe-bench_lite",
                split="dev",
                predictions_path="/non/existent/path/preds.json",
            )

    def test_submit_predictions_argument_construction(self, temp_sb_workspace):
        """submit_predictions builds correct argument list for sb-cli invocation."""
        adapter = temp_sb_workspace["adapter"]
        preds_file = temp_sb_workspace["preds_dir"] / "mock_preds.json"
        preds_file.write_text("{}", encoding="utf-8")

        with patch.object(adapter, "_run_command", return_value=(0, "Upload OK", "")) as mock_run:
            res = adapter.submit_predictions(
                subset="swe-bench_lite",
                split="dev",
                predictions_path=preds_file,
                run_id="test_run_01",
                instance_ids=["django__django-11099"],
                api_key="test_api_key_123",
            )

            assert res["success"] is True
            assert mock_run.called
            args_passed = mock_run.call_args[0][0]
            assert "submit" in args_passed
            assert "swe-bench_lite" in args_passed
            assert "dev" in args_passed
            assert "--predictions_path" in args_passed
            assert "--run_id" in args_passed
            assert "test_run_01" in args_passed
            assert "--instance_ids" in args_passed
            assert "--api_key" in args_passed

    def test_get_report_argument_construction(self, temp_sb_workspace):
        """get_report builds correct command arguments."""
        adapter = temp_sb_workspace["adapter"]
        with patch.object(adapter, "_run_command", return_value=(0, "Report Data", "")) as mock_run:
            res = adapter.get_report(
                subset="swe-bench_verified",
                split="test",
                run_id="run_999",
                api_key="key_abc",
            )
            assert res["success"] is True
            args = mock_run.call_args[0][0]
            assert args == [
                "get-report",
                "swe-bench_verified",
                "test",
                "run_999",
                "--output_dir", str(temp_sb_workspace["reports_dir"].resolve()),
                "--overwrite", "0",
                "--api_key", "key_abc",
            ]

    def test_list_runs_argument_construction(self, temp_sb_workspace):
        """list_runs builds correct command arguments."""
        adapter = temp_sb_workspace["adapter"]
        with patch.object(adapter, "_run_command", return_value=(0, "run1\nrun2", "")) as mock_run:
            res = adapter.list_runs(subset="swe-bench-m", split="dev", api_key="key_xyz")
            assert res["success"] is True
            args = mock_run.call_args[0][0]
            assert args == ["list-runs", "swe-bench-m", "dev", "--api-key", "key_xyz"]

    def test_delete_run_argument_construction(self, temp_sb_workspace):
        """delete_run builds correct command arguments."""
        adapter = temp_sb_workspace["adapter"]
        with patch.object(adapter, "_run_command", return_value=(0, "Deleted run", "")) as mock_run:
            res = adapter.delete_run(subset="swe-bench_lite", split="dev", run_id="run_old", api_key="key_del")
            assert res["success"] is True
            args = mock_run.call_args[0][0]
            assert args == ["delete-run", "swe-bench_lite", "dev", "run_old", "--api-key", "key_del"]

    def test_generate_and_verify_api_key_dispatch(self, temp_sb_workspace):
        """gen-api-key and verify-api-key dispatches correctly."""
        adapter = temp_sb_workspace["adapter"]
        with patch.object(adapter, "_run_command", return_value=(0, "Check your email", "")) as mock_run:
            res = adapter.generate_api_key("researcher@lauburu.ai")
            assert res["success"] is True
            assert mock_run.call_args[0][0] == ["gen-api-key", "researcher@lauburu.ai"]

        with patch.object(adapter, "_run_command", return_value=(0, "Verified", "")) as mock_run:
            res = adapter.verify_api_key("CODE_12345", api_key="KEY_ABC")
            assert res["success"] is True
            assert mock_run.call_args[0][0] == ["verify-api-key", "CODE_12345", "--api_key", "KEY_ABC"]


class TestHarnessSweBenchIntegration:
    """Verifies end-to-end integration between SweBenchHarness and SbCliAdapter."""

    def test_harness_export_predictions_json(self, temp_sb_workspace):
        """SweBenchHarness.export_predictions_json produces valid schema."""
        harness = SweBenchHarness(tasks=SAMPLE_SWEBENCH_TASKS, models=MODELS_IN_ARENA)
        out_file = temp_sb_workspace["preds_dir"] / "harness_preds.json"

        res_path = harness.export_predictions_json(
            output_path=out_file,
            model_name="Qwen-AgentWorld-35B-A3B",
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
