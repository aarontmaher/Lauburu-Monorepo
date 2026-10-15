#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests for Co-Working Multi-Tier AI Orchestrator (NPU + Local Mesh + Cloud AI)
==================================================================================
Subsystem: 02_ai_models_and_inference/tests/test_npu_co_working_orchestrator.py
Compliant with: Rule 0 (Zero-Mock), Rule 3 (Host RAM Sanctuary), Rule 8 (Local AI Hierarchy)
"""

import sys
import pytest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "02_ai_models_and_inference"))

from npu_co_working_orchestrator import (
    NpuCoWorkingOrchestrator,
    CoWorkingInferenceRequest,
    CoWorkingInferenceResponse
)


class TestNpuCoWorkingOrchestrator:
    def test_singleton_initialization(self):
        orch = NpuCoWorkingOrchestrator.get_instance()
        assert orch is not None
        assert orch.local_master_port == 8082
        assert orch.local_syntax_port == 8081
        assert orch.local_red_team_port == 8083

    def test_tier0_reflex_intent_classification(self):
        orch = NpuCoWorkingOrchestrator.get_instance()
        domain, tier, latency_us = orch.classify_prompt_intent_npu("check host ram headroom and sanctuary status")
        assert domain == "telemetry"
        assert tier == "TIER_0_NPU"
        assert latency_us < 200.0  # Must be sub-millisecond

    def test_tier0_reflex_biometrics_routing(self):
        orch = NpuCoWorkingOrchestrator.get_instance()
        domain, tier, latency_us = orch.classify_prompt_intent_npu("Movesense bicep ECG 512Hz R-peak status")
        assert domain == "biometrics"
        assert tier == "TIER_0_NPU"

    def test_tier1_code_generation_routing(self):
        orch = NpuCoWorkingOrchestrator.get_instance()
        domain, tier, latency_us = orch.classify_prompt_intent_npu("def compile_ast_node(node):")
        assert domain == "code_generation"
        assert tier == "TIER_1_LOCAL"

    def test_tier1_red_team_adversarial_routing(self):
        orch = NpuCoWorkingOrchestrator.get_instance()
        domain, tier, latency_us = orch.classify_prompt_intent_npu("red team adversarial challenge on buffer overflow")
        assert domain == "red_team"
        assert tier == "TIER_1_LOCAL_RED_TEAM"

    def test_tier1_kimi_multimodal_context_routing(self):
        orch = NpuCoWorkingOrchestrator.get_instance()
        domain, tier, latency_us = orch.classify_prompt_intent_npu("kimi long context pruner for document AST analysis")
        assert domain == "kimi_multimodal_context"
        assert tier == "TIER_1_LOCAL_KIMI"

        req = CoWorkingInferenceRequest(prompt="kimi long context lossless compression")
        res = orch.dispatch(req)
        assert res.selected_tier == "TIER_1_LOCAL_KIMI"
        assert "Kimi Tandem Titan" in res.primary_model
        assert res.speculative_draft_accepted is True

    def test_tier2_cloud_frontier_routing(self):
        orch = NpuCoWorkingOrchestrator.get_instance()
        domain, tier, latency_us = orch.classify_prompt_intent_npu("Explain multi-tier speculative decoding architecture")
        assert domain == "frontier_reasoning"
        assert tier == "TIER_2_CLOUD"

    def test_speculative_draft_generation_k_tokens(self):
        orch = NpuCoWorkingOrchestrator.get_instance()
        tokens, latency_us = orch.generate_npu_speculative_draft("def initialize_sram", k=4)
        assert len(tokens) == 4
        assert latency_us < 100.0

    def test_dispatch_tier0_execution(self):
        orch = NpuCoWorkingOrchestrator.get_instance()
        req = CoWorkingInferenceRequest(prompt="report current RAM headroom and Rule 3 status")
        res = orch.dispatch(req)
        assert res.selected_tier == "TIER_0_NPU"
        assert "Apple" in res.primary_model or "ANE" in res.primary_model
        assert res.speculative_draft_accepted is True
        assert res.elo_incentive_points > 0.0
        assert len(res.sha256_receipt) == 64

    def test_output_truth_verification_blocks_simulation(self):
        orch = NpuCoWorkingOrchestrator.get_instance()
        valid, msg = orch.verify_output_safety_and_truth("Here is a simulated_data array for testing")
        assert valid is False
        assert "SIMULATION_DETECTED" in msg
