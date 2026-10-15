#!/usr/bin/env python3
"""
Unit tests for continuous_npu_agent_tester.py
Verifies zero-mock empirical testing of NPU agents across the Triumvirate Models.
"""

import sys
import json
import pytest
from pathlib import Path

# Add repo root and inference dir to path
REPO_ROOT = Path(__file__).resolve().parents[2]
INFERENCE_DIR = REPO_ROOT / "02_ai_models_and_inference"
INFRA_DIR = REPO_ROOT / "00_core_infrastructure"

for d in [str(REPO_ROOT), str(INFERENCE_DIR), str(INFRA_DIR)]:
    if d not in sys.path:
        sys.path.insert(0, d)

from continuous_npu_agent_tester import ContinuousNpuAgentTester, STATE_FILE, TRIUMVIRATE


def test_tester_initialization():
    tester = ContinuousNpuAgentTester()
    assert tester.syntax_validator is not None
    assert tester.numerical_sentinel is not None
    assert tester.total_cycles == 0


def test_tb4_link_probe():
    tester = ContinuousNpuAgentTester()
    link = tester.probe_tb4_link()
    assert link["bridge_ip"] == "169.254.187.138"
    assert link["bandwidth_gbps"] == 10.0
    assert link["measured_rtt_ms"] >= 0.0
    assert "PRP" in link["protocol"]


def test_triumvirate_capacity_structure():
    tester = ContinuousNpuAgentTester()
    cap = tester.check_triumvirate_capacity()
    assert "qwen_38_max" in cap
    assert "qwen_38_max_abliterated" in cap
    assert "kimi_tandem_titan" in cap
    assert "fallback_coder" in cap
    assert cap["qwen_38_max"]["port"] == 8082
    assert cap["qwen_38_max_abliterated"]["port"] == 8083
    assert cap["kimi_tandem_titan"]["port"] == 8085
    assert cap["fallback_coder"]["port"] == 8081


def test_npu_syntax_validator_execution():
    tester = ContinuousNpuAgentTester()
    res = tester.test_npu_syntax_validator()
    assert res["status"] == "PASSED"
    assert res["subtests_count"] == 5
    assert res["passed_count"] == 5
    assert res["avg_latency_us"] < 2000.0  # Fast sub-2ms gate
    assert res["host_ram_mb"] == 0.0
    assert res["paired_model"] == "qwen_38_max"


def test_npu_numerical_sentinel_execution():
    tester = ContinuousNpuAgentTester()
    res = tester.test_npu_numerical_sentinel()
    assert res["status"] == "PASSED"
    assert res["detection_accuracy_passed"] is True
    assert res["elo_math_passed"] is True
    assert res["avg_latency_us"] < 50.0  # Sub-50µs systolic math
    assert res["host_ram_mb"] == 0.0
    assert res["paired_model"] == "qwen_38_max_abliterated"
    assert res["master_elo_delta"] > 0.0


def test_candidate_discovery():
    tester = ContinuousNpuAgentTester()
    candidates = tester.discover_candidate_npu_agents()
    assert isinstance(candidates, list)
    assert len(candidates) > 0
    candidate_names = [c["name"] for c in candidates]
    assert any("npu_" in name for name in candidate_names)


def test_full_run_cycle_and_state_persistence():
    tester = ContinuousNpuAgentTester()
    state = tester.run_cycle()
    assert state["overall_status"] == "HEALTHY"
    assert state["default_sharding_engine"] == "prima.cpp"
    assert state["cycle_index"] == 1
    assert state["summary"]["pass_rate_pct"] == 100.0
    assert state["summary"]["host_ram_overhead_mb"] == 0.0
    assert state["summary"]["zero_mock_verified"] is True

    # Check persistence
    assert STATE_FILE.exists()
    saved = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    assert saved["default_sharding_engine"] == "prima.cpp"
    assert saved["overall_status"] == "HEALTHY"
