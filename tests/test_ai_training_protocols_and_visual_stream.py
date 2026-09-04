#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Lauburu Sovereign Mesh: AI Training Protocols & Visual Stream Test Suite
================================================================================
Test Target:
- 05_agents_and_swarms/training_protocols/high_roi_protocol_registry.py
- 05_agents_and_swarms/training_protocols/grpo_rule_based_trainer.py
- 05_agents_and_swarms/training_protocols/dpo_debate_distiller.py
- 05_agents_and_swarms/training_protocols/frontier_benchmarking_arena.py
- 01_apps/ai_training_visual_stream/training_stream_server.py (Port 4004)
- 06_scripts_and_tooling/autonomous_training_supervisor.py
================================================================================
"""

import json
import os
import shutil
import sys
import tempfile
import time
import urllib.request
import socket
import threading
from pathlib import Path
import pytest

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "05_agents_and_swarms"))

from training_protocols import (
    TrainingProtocolID,
    ProtocolStatus,
    HighROIProtocolRegistry,
    GRPORuleBasedRewardEngine,
    DPODebateDistiller,
    FrontierBenchmarkingArena
)


def test_high_roi_protocol_registry_initialization():
    registry = HighROIProtocolRegistry()
    protocols = registry.list_protocols()
    assert len(protocols) == 5, f"Expected 5 protocols, got {len(protocols)}"

    expected_ids = {
        TrainingProtocolID.GRPO_COMPILER_REWARD,
        TrainingProtocolID.DPO_DEBATE_CONSENSUS,
        TrainingProtocolID.GBNF_SERIAL_CONSTRAINED,
        TrainingProtocolID.ELO_SELF_PLAY_TOURNAMENT,
        TrainingProtocolID.BIOMETRIC_ECG_DSP_DISTILLATION
    }
    actual_ids = {p.protocol_id for p in protocols}
    assert actual_ids == expected_ids, f"Mismatch in protocol IDs: {actual_ids}"

    # Verify GRPO protocol details
    grpo = registry.get_protocol(TrainingProtocolID.GRPO_COMPILER_REWARD)
    assert grpo is not None
    assert grpo.estimated_roi_multiplier == 4.8
    assert "ast" in grpo.mathematical_formulation.lower()
    assert len(grpo.proof_requirements) >= 4


def test_protocol_registry_record_verification():
    registry = HighROIProtocolRegistry()
    p_id = TrainingProtocolID.GRPO_COMPILER_REWARD

    registry.record_verification(p_id, passed=True, reward=8.5, samples_count=2)
    registry.record_verification(p_id, passed=True, reward=9.5, samples_count=1)
    registry.record_verification(p_id, passed=False, reward=2.0, samples_count=1)

    p = registry.get_protocol(p_id)
    assert p.samples_harvested == 4
    assert p.verifications_passed == 2
    assert p.verifications_failed == 1
    assert p.to_dict()["pass_rate"] == 66.67


def test_grpo_rule_based_reward_engine():
    engine = GRPORuleBasedRewardEngine()

    candidates = [
        {
            "id": "cand_good",
            "code": "def multiply(x, y):\n    return x * y\nassert multiply(3, 4) == 12\nprint('PASS')"
        },
        {
            "id": "cand_syntax_err",
            "code": "def multiply(x, y\n    return x * y"
        },
        {
            "id": "cand_mock_fail",
            "code": "import unittest.mock\ndef multiply(x, y):\n    return 12"
        },
        {
            "id": "cand_assertion_fail",
            "code": "def multiply(x, y):\n    return x + y\nassert multiply(3, 4) == 12"
        }
    ]

    samples = engine.evaluate_group("Multiply two integers", candidates)
    assert len(samples) == 4

    cand_map = {s.candidate_id: s for s in samples}

    # Cand good should have exit 0, ast_valid=True, zero_mock_clean=True, positive advantage
    assert cand_map["cand_good"].exit_code == 0
    assert cand_map["cand_good"].ast_valid is True
    assert cand_map["cand_good"].zero_mock_clean is True
    assert cand_map["cand_good"].normalized_advantage > 0

    # Cand syntax err
    assert cand_map["cand_syntax_err"].ast_valid is False
    assert cand_map["cand_syntax_err"].exit_code != 0

    # Cand mock fail
    assert cand_map["cand_mock_fail"].zero_mock_clean is False
    assert cand_map["cand_mock_fail"].raw_reward < 0

    # Cand assertion fail
    assert cand_map["cand_assertion_fail"].exit_code != 0
    assert cand_map["cand_assertion_fail"].assertions_passed == 0


def test_dpo_debate_distiller():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_file = Path(tmpdir) / "test_dpo_pairs.jsonl"
        distiller = DPODebateDistiller(output_file=tmp_file)

        pair = distiller.distill_from_text(
            prompt="Optimal multi-transport failover ladder?",
            chosen_response="1. Wi-Fi 7 / 2.5GbE -> 2. USB Serial CDC -> 3. Bluetooth RFCOMM /dev/rfcomm0.",
            rejected_response="Rely exclusively on cloud WebSocket relays without offline fallback.",
            consensus_score=0.99,
            source="test_debate.md"
        )

        assert pair.pair_id.startswith("dpo_")
        assert tmp_file.exists()

        stats = distiller.get_dataset_stats()
        assert stats["total_pairs"] == 1
        assert stats["avg_consensus"] == 0.99


def test_frontier_benchmarking_arena():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_status = Path(tmpdir) / "test_bench_status.json"
        arena = FrontierBenchmarkingArena(status_file=tmp_status)

        res = arena.evaluate_local_model(
            model_id="qwen_coder32",
            model_name="Qwen 2.5 Coder 32B (Local Metal TB4)",
            empirical_scores={
                "monorepo_ast_compliance": 94.0,
                "zero_mock_truth_adherence": 99.0,
                "serial_grammar_execution": 90.0,
                "biometric_dsp_precision": 88.0
            },
            zero_mock_pass=True
        )

        assert res.overall_score > 90.0
        assert res.cloud_teacher_delta > 0  # Outperformed cloud baseline
        assert res.win_rate_vs_cloud == 100.0
        assert tmp_status.exists()


def test_training_stream_server_http_endpoints():
    url_base = "http://localhost:4004"
    # Ensure server is up
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    is_open = s.connect_ex(("localhost", 4004)) == 0
    s.close()
    if not is_open:
        stream_dir = str(REPO_ROOT / "01_apps" / "ai_training_visual_stream")
        if stream_dir not in sys.path:
            sys.path.insert(0, stream_dir)
        from training_stream_server import ReusableTCPServer, TrainingStreamHandler
        srv = ReusableTCPServer(("0.0.0.0", 4004), TrainingStreamHandler)
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        time.sleep(0.3)

    # 1. Test GET / (Dashboard HTML)
    req = urllib.request.Request(f"{url_base}/")
    with urllib.request.urlopen(req, timeout=3.0) as resp:
        assert resp.status == 200
        content = resp.read().decode("utf-8")
        assert "Lauburu Sovereign Mesh — AI Training Visual Stream" in content
        assert "PORT 4004 • LIVE SSE" in content

    # 2. Test GET /api/status
    req_status = urllib.request.Request(f"{url_base}/api/status")
    with urllib.request.urlopen(req_status, timeout=3.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["server_port"] == 4004
        assert data["system_status"] == "ONLINE_STREAMING"
        assert data["ram_headroom_gb"] >= 9.6

    # 3. Test GET /api/protocols
    req_proto = urllib.request.Request(f"{url_base}/api/protocols")
    with urllib.request.urlopen(req_proto, timeout=3.0) as resp:
        assert resp.status == 200
        pdata = json.loads(resp.read().decode("utf-8"))
        assert pdata["total_protocols"] == 5

    # 4. Test POST /api/trigger_benchmark
    post_req = urllib.request.Request(
        f"{url_base}/api/trigger_benchmark",
        data=b"",
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(post_req, timeout=5.0) as resp:
        assert resp.status == 200
        bdata = json.loads(resp.read().decode("utf-8"))
        assert bdata["status"] == "SUCCESS"
        assert bdata["result"]["overall_score"] > 85.0


def test_zero_mock_compliance_in_new_codebase():
    """Rule #0 & Rule 1: Zero mock imports across all new production modules."""
    files_to_check = [
        REPO_ROOT / "05_agents_and_swarms/training_protocols/high_roi_protocol_registry.py",
        REPO_ROOT / "05_agents_and_swarms/training_protocols/grpo_rule_based_trainer.py",
        REPO_ROOT / "05_agents_and_swarms/training_protocols/dpo_debate_distiller.py",
        REPO_ROOT / "05_agents_and_swarms/training_protocols/frontier_benchmarking_arena.py",
        REPO_ROOT / "01_apps/ai_training_visual_stream/training_stream_server.py",
        REPO_ROOT / "06_scripts_and_tooling/autonomous_training_supervisor.py",
    ]

    for fpath in files_to_check:
        assert fpath.exists(), f"File {fpath} does not exist"
        content = fpath.read_text(encoding="utf-8")
        # Check that unittest.mock or MagicMock are not imported or used for testing
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if s.startswith("import mock") or s.startswith("from unittest import mock") or s.startswith("from unittest.mock"):
                pytest.fail(f"Mock import violation in {fpath.name}:{i} -> {line}")
            if "MagicMock" in line and not ("forbidden_tokens" in content or "mock_tokens" in line or "check_zero_mock" in line):
                pytest.fail(f"MagicMock usage violation in {fpath.name}:{i} -> {line}")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
