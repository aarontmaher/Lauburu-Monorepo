#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit and Integration Tests for SWE-bench Tool & Qwen MoE Integration
"""

import os
import sys
import json
import pytest
from pathlib import Path

# Add parent path to sys.path
TEST_DIR = Path(__file__).resolve().parent
SWARMS_DIR = TEST_DIR.parent
if str(SWARMS_DIR) not in sys.path:
    sys.path.insert(0, str(SWARMS_DIR))

from tools.swe_bench_tool import (
    SweBenchTool,
    SWE_BENCH_TOOL_SCHEMAS,
    swe_bench_get_quotas,
    swe_bench_format_preds,
    swe_bench_eval_ast_patch
)
from tools.mesh_algorithm_tools import get_tool_schemas
from qwen_moe_orchestrator import QwenMoEOrchestrator


def test_swe_bench_tool_initialization():
    tool = SweBenchTool()
    assert tool is not None
    assert tool.cli_path is not None
    assert "swe-bench_lite" in tool.SUPPORTED_SUBSETS


def test_swe_bench_tool_schemas():
    schemas = SWE_BENCH_TOOL_SCHEMAS
    assert len(schemas) == 6
    schema_names = [s["function"]["name"] for s in schemas]
    assert "swe_bench_oracle_retrieval" in schema_names
    assert "swe_bench_get_quotas" in schema_names
    assert "swe_bench_format_preds" in schema_names
    assert "swe_bench_eval_ast_patch" in schema_names
    assert "swe_bench_submit_predictions" in schema_names
    assert "swe_bench_get_report" in schema_names


def test_mesh_algorithm_tool_registry():
    all_schemas = get_tool_schemas()
    assert len(all_schemas) >= 11
    names = [s["function"]["name"] for s in all_schemas]
    assert "swe_bench_eval_ast_patch" in names
    assert "mesh_aco_routing_optimizer" in names


def test_eval_ast_patch_valid():
    tool = SweBenchTool()
    valid_patch = (
        "diff --git a/src/core.py b/src/core.py\n"
        "--- a/src/core.py\n"
        "+++ b/src/core.py\n"
        "@@ -1,3 +1,4 @@\n"
        "+def sanitize_input(text: str) -> str:\n"
        "+    return text.strip()\n"
    )
    res = tool.eval_ast_patch("test_task_01", valid_patch)
    assert res["valid"] is True
    assert res["has_diff_header"] is True
    assert res["ast_syntax_valid"] is True
    assert res["zero_mock_verified"] is True


def test_eval_ast_patch_empty():
    tool = SweBenchTool()
    res = tool.eval_ast_patch("test_task_empty", "")
    assert res["valid"] is False
    assert "Empty patch" in res["error"]


def test_format_predictions_file(tmp_path):
    out_file = tmp_path / "preds.json"
    tool = SweBenchTool()
    patch = "diff --git a/a.py b/a.py\n+x = 1\n"
    res = tool.format_predictions("pytest__pytest-123", patch, model_name_or_path="qwen-72b", output_file=out_file)
    assert res["status"] == "FORMATTED"
    assert out_file.exists()
    
    with open(out_file, "r") as f:
        data = json.load(f)
    assert "pytest__pytest-123" in data
    assert data["pytest__pytest-123"]["model_name_or_path"] == "qwen-72b"


def test_qwen_moe_orchestrator_integration():
    orch = QwenMoEOrchestrator()
    assert orch.swe_tool is not None
    
    patch = (
        "diff --git a/django/db/models/query.py b/django/db/models/query.py\n"
        "+def get_queryset_cache():\n"
        "+    return {}\n"
    )
    res = orch.evaluate_swe_patch("django__django-9999", patch)
    assert res["task_id"] == "django__django-9999"
    assert res["ast_validation"]["valid"] is True
    assert res["lora_logged"] is True


if __name__ == "__main__":
    pytest.main(["-v", str(__file__)])
