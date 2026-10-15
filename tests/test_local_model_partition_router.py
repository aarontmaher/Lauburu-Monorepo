#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_local_model_partition_router.py
===========================================
Unit test suite validating:
1. Qwen 3.8 Standard GGUF orchestrator pinning.
2. Dual segregated planes (Normal vs Abliterated).
3. Strict cross-plane isolation enforcement (PlaneViolationError).
4. 100% GGUF format and llama.cpp / prima.cpp engine standardization.
"""

import sys
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SWARMS_DIR = REPO_ROOT / "05_agents_and_swarms"
if str(SWARMS_DIR) not in sys.path:
    sys.path.insert(0, str(SWARMS_DIR))

from local_model_partition_router import (
    LocalModelPartitionRouter,
    PlaneViolationError,
    NORMAL_MODELS,
    ABLITERATED_MODELS,
    partition_router
)


class TestLocalModelPartitionRouter:

    def setup_method(self):
        self.router = LocalModelPartitionRouter()

    def test_normal_orchestrator_is_qwen38_standard_gguf(self):
        orch = self.router.get_orchestrator("normal")
        assert orch.model_id == "qwen_38_standard"
        assert orch.format == "GGUF"
        assert orch.is_abliterated is False
        assert orch.is_orchestrator is True
        assert "llama.cpp" in orch.engines
        assert "prima.cpp" in orch.engines

    def test_abliterated_orchestrator_is_qwen38_abliterated_gguf(self):
        orch = self.router.get_orchestrator("abliterated")
        assert orch.model_id == "qwen_38_max_abliterated"
        assert orch.format == "GGUF"
        assert orch.is_abliterated is True
        assert orch.is_orchestrator is True
        assert "llama.cpp" in orch.engines
        assert "prima.cpp" in orch.engines

    def test_normal_plane_delegation_to_normal_models_succeeds(self):
        test_models = [
            "qwen_38_flash_next",
            "qwen_moe_80b",
            "qwen2.5_coder_7b",
            "qwen2.5_coder_32b",
            "qwen2.5_math_7b",
            "smollm2_1.7b",
            "smollm2_360m",
            "phi_3.5_mini",
            "ministral_3b",
            "qwen2.5_vl_7b",
            "deepseek_coder_v2_lite"
        ]
        for m_id in test_models:
            trace = self.router.route_call("normal", m_id, f"Test task for {m_id}")
            assert trace["caller_plane"] == "normal"
            assert trace["target_model_id"] == m_id
            assert trace["is_abliterated"] is False
            assert trace["format"] == "GGUF"

    def test_abliterated_plane_delegation_to_abliterated_models_succeeds(self):
        test_models = [
            "qwen_38_max_abliterated",
            "mistral_nemo_12b_abliterated",
            "qwen2.5_7b_abliterated",
            "gemma_2_9b_abliterated",
            "llama_3.2_1b_abliterated"
        ]
        for m_id in test_models:
            trace = self.router.route_call("abliterated", m_id, f"Adversarial audit {m_id}")
            assert trace["caller_plane"] == "abliterated"
            assert trace["target_model_id"] == m_id
            assert trace["is_abliterated"] is True
            assert trace["format"] == "GGUF"

    def test_normal_plane_calling_abliterated_model_is_strictly_blocked(self):
        for ablit_id in ABLITERATED_MODELS.keys():
            with pytest.raises(PlaneViolationError) as excinfo:
                self.router.route_call("normal", ablit_id, "Illegal call attempt")
            assert "CRITICAL GOVERNANCE VIOLATION" in str(excinfo.value)
            assert "Normal plane is restricted to normal models only" in str(excinfo.value)

    def test_abliterated_plane_calling_normal_model_is_strictly_blocked(self):
        for norm_id in NORMAL_MODELS.keys():
            with pytest.raises(PlaneViolationError) as excinfo:
                self.router.route_call("abliterated", norm_id, "Illegal call attempt")
            assert "CRITICAL GOVERNANCE VIOLATION" in str(excinfo.value)
            assert "Abliterated plane is restricted to abliterated models only" in str(excinfo.value)

    def test_invalid_plane_raises_value_error(self):
        with pytest.raises(ValueError):
            self.router.route_call("invalid_plane", "qwen2.5_coder_7b", "Task")

    def test_unknown_model_raises_key_error(self):
        with pytest.raises(KeyError):
            self.router.route_call("normal", "non_existent_model_xyz", "Task")

    def test_all_registered_models_are_gguf_format(self):
        for m in list(NORMAL_MODELS.values()) + list(ABLITERATED_MODELS.values()):
            assert m.format == "GGUF"
            assert "llama.cpp" in m.engines
            assert "prima.cpp" in m.engines

    def test_router_summary_structure(self):
        summary = self.router.get_summary()
        assert "orchestrator_normal" in summary
        assert "orchestrator_abliterated" in summary
        assert summary["format_standard"] == "100% GGUF (llama.cpp & prima.cpp PRP)"
        assert summary["normal_models_count"] >= 10
        assert summary["abliterated_models_count"] >= 5

    def test_orchestrator_delegate_helper(self):
        res = self.router.orchestrator_delegate("qwen_moe_80b", "Analyze cluster stability")
        assert res["caller_plane"] == "normal"
        assert res["target_model_id"] == "qwen_moe_80b"

        with pytest.raises(PlaneViolationError):
            self.router.orchestrator_delegate("qwen_38_max_abliterated", "Attempt breach")

    def test_adversary_delegate_helper(self):
        res = self.router.adversary_delegate("mistral_nemo_12b_abliterated", "Conduct red team sweep")
        assert res["caller_plane"] == "abliterated"
        assert res["target_model_id"] == "mistral_nemo_12b_abliterated"

        with pytest.raises(PlaneViolationError):
            self.router.adversary_delegate("qwen_38_standard", "Attempt breach")

    def test_live_execution_on_port_8081(self):
        # Port 8081 is active with llama-server
        res = self.router.route_call("normal", "qwen2.5_coder_7b", "respond with ping", execute=True, max_tokens=10)
        assert res["executed"] is True
        assert res["execution_status"] == "SUCCESS"
        assert res["response_text"] is not None
        assert res["tokens_per_second"] > 0.0

