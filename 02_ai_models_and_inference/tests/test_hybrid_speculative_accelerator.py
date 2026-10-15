#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit and Integration Tests for Hybrid Speculative Acceleration Engine (4 Mechanisms)
"""

import pytest
from pathlib import Path
import sys

ACCEL_DIR = Path(__file__).resolve().parents[1] / "acceleration"
if str(ACCEL_DIR) not in sys.path:
    sys.path.insert(0, str(ACCEL_DIR))

from hybrid_speculative_accelerator import (
    ASTContextCompressor,
    AsyncSpeculativeStreamer,
    SwarmCascadeRouter,
    SpeculativeToolDrafter,
    HybridSpeculativeAccelerator
)


def test_ast_context_compressor():
    compressor = ASTContextCompressor()
    code = """
import math

class Calculator:
    \"\"\"Docstring.\"\"\"
    def add(self, a: int, b: int) -> int:
        result = a + b
        return result
"""
    res = compressor.compress_python_source(code)
    assert res["syntax_valid"] is True
    assert "def add(self, a: int, b: int) -> int: ..." in res["compressed_code"]
    assert "result = a + b" not in res["compressed_code"]
    assert res["compression_ratio"] > 0.0


def test_async_speculative_streamer():
    streamer = AsyncSpeculativeStreamer()
    scaffold = streamer.generate_ui_scaffold("code_refactor", "Telemetry Engine")
    assert "### ⚡ Code Refactoring Plan" in scaffold["scaffold_text"]
    assert scaffold["status"] == "STREAMING_SCAFFOLD_ACTIVE"
    assert scaffold["ttft_ms"] < 20.0


def test_swarm_cascade_router_simple():
    router = SwarmCascadeRouter()
    res = router.route_query("format this json schema")
    assert res["target_tier"] == "TIER_1_LOCAL_TINY_LM"
    assert res["cloud_bypass"] is True


def test_swarm_cascade_router_complex():
    router = SwarmCascadeRouter()
    res = router.route_query("Refactor multi-file architectural SWE-bench task for Django cache")
    assert res["target_tier"] == "TIER_2_CLOUD_FRONTIER_OR_72B_MOE"
    assert res["cloud_bypass"] is False


def test_speculative_tool_drafter():
    drafter = SpeculativeToolDrafter()
    draft = drafter.pre_draft_tool_call("swe_bench_format_preds", {"task_id": "task_123", "patch": "+x=1\n"})
    assert draft["schema_valid"] is True
    assert draft["draft_arguments"]["task_id"] == "task_123"


def test_master_hybrid_accelerator_pipeline():
    accel = HybridSpeculativeAccelerator()
    res = accel.process_pipeline(
        "Refactor multi-file ECG DSP buffer",
        code_context="def process_ecg(hr: float) -> dict:\n    return {'hr': hr}\n",
        tool_name="swe_bench_format_preds"
    )
    assert res["status"] == "ACCELERATION_APPLIED"
    assert res["pipeline_overhead_ms"] < 50.0
    assert res["ast_compression"]["syntax_valid"] is True


if __name__ == "__main__":
    pytest.main(["-v", str(__file__)])
