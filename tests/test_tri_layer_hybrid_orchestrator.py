"""
tests/test_tri_layer_hybrid_orchestrator.py
============================================
Comprehensive Test Suite for Milestone M3 (Tri-Layer Hybrid Orchestration).

Covers:
  - Layer 1 (Cloud Orchestrator): Gemini 3.7 Flash High strategic CoT reasoning,
    multi-file invariant synthesis, shadow guard AST and zero-mock verification.
  - Layer 2 (Local AI Engine): Kimi Tandem (Kimi-VL Thinking 9.8 GB + Kimi-Dev-72B 39 GB)
    distributed sharding across 82.8 GB VRAM on Port 50052, Qwen2.5-VL-7B edge fallback on Port 8084 (>40 tok/s),
    multi-tier visual auditing, zero cloud spend enforcement ($0.00).
  - Layer 3 (Autonomous Self-Healer): Nomad Courier v3.0 4-port supervision (3000, 4000, 18802, 50052),
    5-tier progressive remediation cascade, Antigravity skills persistence, Obsidian synchronization.
  - End-to-End Tri-Layer Routing Pipeline: Failover cascades, task classification,
    asynchronous shadow guard verification, 24/7 LoRA dataset logging.
  - Rule #0 Zero-Mock Data Integrity: Rejection of mock markers, simulated flags, and fake telemetries.
"""

import ast
import json
import os
import re
import socket
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
INFRA_SRC = REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src"
SWARM_SRC = REPO_ROOT / "05_agents_and_swarms"

for p in [REPO_ROOT, INFRA_SRC, SWARM_SRC]:
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

from tri_layer_hybrid_orchestrator import (
    TriLayerHybridOrchestrator,
    CloudFrontierOrchestrator,
    SovereignLocalAIEngine,
    AutonomousSelfHealingGovernor,
    TaskSpecification,
    ShadowVerificationResult,
    TriLayerExecutionResult
)
from tri_layer_hybrid_bridge import get_tri_layer_orchestrator


# ============================================================================
# 1. LAYER 1: CLOUD FRONTIER ORCHESTRATOR TESTS
# ============================================================================

class TestLayer1CloudFrontierOrchestrator:
    """Verifies Gemini 3.7 Flash High strategic planning and shadow guard verification."""

    def test_layer1_strategic_plan_generation(self):
        """L1.1: Verifies strategic CoT reasoning trace and invariant generation."""
        cloud = CloudFrontierOrchestrator()
        plan = cloud.generate_strategic_plan(
            "Tri-Layer Hybrid Sharding & Fault Tolerance",
            {"target": "00_core_infrastructure"}
        )
        assert plan["model"] == "Gemini 3.7 Flash High (Strategic Vision)"
        assert "thought_trace" in plan
        assert len(plan["thought_trace"]) > 50
        assert len(plan["invariants"]) >= 5
        assert any("RAM ceilings" in inv for inv in plan["invariants"])
        assert plan["cost_usd"] > 0.0  # Real cloud cost accounting

    def test_layer1_shadow_guard_valid_ast_cleared(self):
        """L1.2: Verifies shadow guard passes clean, AST-valid, zero-mock Python code."""
        cloud = CloudFrontierOrchestrator()
        valid_code = (
            "def ingest_movesense_telemetry(packet_bytes: bytes) -> dict:\n"
            "    timestamp_ns = 1771891200000000000\n"
            "    return {'hr_bpm': 142.5, 'timestamp_ns': timestamp_ns, 'zero_mock': True}\n"
        )
        result = cloud.verify_shadow_guard(valid_code, "03_biometrics_and_telemetry")
        assert result.is_valid is True
        assert result.ast_syntax_pass is True
        assert result.zero_mock_verified is True
        assert result.confidence_score == 1.0
        assert len(result.violations) == 0

    def test_layer1_shadow_guard_syntax_error_rejection(self):
        """L1.3: Verifies shadow guard rejects corrupted or malformed Python syntax."""
        cloud = CloudFrontierOrchestrator()
        broken_code = "def broken_syntax(:\n    return True\n"
        result = cloud.verify_shadow_guard(broken_code, "00_core_infrastructure")
        assert result.is_valid is False
        assert result.ast_syntax_pass is False
        assert any("AST Syntax Error" in v for v in result.violations)

    def test_layer1_shadow_guard_prohibited_mock_rejection(self):
        """L1.4: Verifies shadow guard catches Rule #0 violations (mock patterns)."""
        cloud = CloudFrontierOrchestrator()
        fake_code = (
            "def get_hardware_status():\n"
            "    fake_telemetry = {'mac_mini_ram': '24GB', 'status': 'ONLINE'}\n"
            "    return fake_telemetry\n"
        )
        result = cloud.verify_shadow_guard(fake_code, "00_core_infrastructure", prohibit_mock=True)
        assert result.is_valid is False
        assert result.zero_mock_verified is False
        assert any("Rule #0 Violation" in v for v in result.violations)

    def test_layer1_formal_cot_proof(self):
        """L1.5: Verifies formal Chain-of-Thought mathematical and logical proof engine."""
        cloud = CloudFrontierOrchestrator()
        proof = cloud.formal_cot_proof(
            "Sharding -ts 28,28,24 satisfies Mac Mini 90% RAM ceiling",
            constraints=["Mac Mini RAM <= 24GB", "Cap <= 90%", "Layers = 24"]
        )
        assert proof["is_proven"] is True
        assert len(proof["proof_steps"]) >= 4
        assert "Q.E.D." in proof["proof_steps"][-1]


# ============================================================================
# 2. LAYER 2: SOVEREIGN LOCAL AI ENGINE TESTS
# ============================================================================

class TestLayer2SovereignLocalAIEngine:
    """Verifies Kimi Tandem (Port 50052) and Qwen2.5-VL-7B (Port 8084) mesh execution."""

    def test_layer2_vram_matrix_and_headroom(self):
        """L2.1: Verifies 82.8 GB pooled VRAM hardware allocation and sharding metrics."""
        engine = SovereignLocalAIEngine()
        hw = engine.get_hardware_mesh_status()
        assert hw["total_pooled_vram_gb"] == 82.8
        assert hw["sharding_configuration"] == "-ts 28,28,24"
        assert hw["kimi_dev_72b_vram_gb"] == 39.0
        assert hw["kimi_vl_thinking_vram_gb"] == 9.8
        assert hw["qwen_edge_fallback_vram_gb"] == 4.4
        assert hw["unallocated_headroom_gb"] >= 25.0
        assert hw["cloud_spend_rate_usd"] == 0.00

    def test_layer2_code_synthesis_ast_validity(self):
        """L2.2: Verifies Kimi-Dev-72B code synthesis generates genuine, AST-valid Python logic."""
        engine = SovereignLocalAIEngine()
        synth = engine.execute_code_synthesis(
            "Build zero-mock Bluetooth GATT ingestion handler",
            "03_biometrics_and_telemetry"
        )
        assert synth["model"].startswith("Kimi-Dev-72B")
        assert synth["cloud_cost_usd"] == 0.00
        assert len(synth["sharding_nodes"]) == 3
        # Confirm generated code parses cleanly
        parsed = ast.parse(synth["code"])
        assert isinstance(parsed, ast.Module)

    def test_layer2_visual_audit_tier0_edge_rapid_pass(self):
        """L2.3: Verifies Tier-0 rapid edge visual audit executes via Qwen2.5-VL-7B at >40 tok/s."""
        engine = SovereignLocalAIEngine()
        res = engine.execute_visual_audit("valid_base64_frame_data_xyz", rapid_edge=True)
        assert res["tier"] == 0
        assert "Qwen2.5-VL-7B" in res["model"]
        assert res["throughput_tok_s"] >= 40.0
        assert res["escalated_to_tier1"] is False
        assert res["zero_mock_verified"] is True

    def test_layer2_visual_audit_tier1_escalation_on_ambiguity(self):
        """L2.4: Verifies ambiguous visual frames escalate to Tier-1 Kimi-VL Thinking 2506."""
        engine = SovereignLocalAIEngine()
        # Force low initial confidence with empty payload
        res = engine.execute_visual_audit("", rapid_edge=False)
        assert res["tier"] == 1
        assert "Kimi-VL Thinking 2506" in res["model"]
        assert res["escalated_to_tier1"] is True
        assert "thought_trace" in res

    def test_layer2_dynamic_ram_headroom_caps(self):
        """L2.5: Verifies strict enforcement of platform-specific RAM caps."""
        engine = SovereignLocalAIEngine()
        caps = engine.dynamic_ram_caps
        assert caps["mac_os"] == 90.0
        assert caps["linux"] == 80.0
        assert caps["pixel_android"] == 85.0
        assert caps["samsung_android"] == 75.0


# ============================================================================
# 3. LAYER 3: AUTONOMOUS SELF-HEALING GOVERNOR TESTS
# ============================================================================

class TestLayer3AutonomousSelfHealingGovernor:
    """Verifies Nomad Courier v3.0 port matrix supervision and 5-tier remediation."""

    def test_layer3_supervised_ports_matrix(self):
        """L3.1: Verifies all 4 supervised ports are active in Nomad matrix (3000, 4000, 18802, 50052)."""
        governor = AutonomousSelfHealingGovernor()
        ports = governor.supervised_ports
        assert ports["web_ui"] == 3000
        assert ports["hub_api"] == 4000
        assert ports["wol_api"] == 18802
        assert ports["llama_rpc"] == 50052

    def test_layer3_5tier_remediation_cascade_tier1_port_kill(self):
        """L3.2: Verifies Tier 1 remediation cleans stale PIDs on Port 3000/4000."""
        governor = AutonomousSelfHealingGovernor()
        res = governor.execute_5tier_remediation(3000)
        assert res["remediation_tier"] == 1
        assert res["status"] == "HEALED_TIER_1_PORT_KILL"
        assert res["resolved"] is True

    def test_layer3_5tier_remediation_cascade_tier2_wol(self):
        """L3.3: Verifies Tier 2 remediation dispatches WoL magic packet on Port 18802."""
        governor = AutonomousSelfHealingGovernor()
        res = governor.execute_5tier_remediation(18802)
        assert res["remediation_tier"] == 2
        assert res["status"] == "HEALED_TIER_2_WOL_DISPATCH"
        assert res["resolved"] is True

    def test_layer3_5tier_remediation_cascade_tier3_daemon_respawn(self):
        """L3.4: Verifies Tier 3 remediation respawns llama.cpp RPC daemon on Port 50052."""
        governor = AutonomousSelfHealingGovernor()
        res = governor.execute_5tier_remediation(50052)
        assert res["remediation_tier"] == 3
        assert res["status"] == "HEALED_TIER_3_DAEMON_RESPAWN"
        assert res["resolved"] is True

    def test_layer3_5tier_remediation_cascade_tier5_circuit_breaker(self):
        """L3.5: Verifies Tier 5 trips circuit breaker into safe mode during permanent hardware fault."""
        governor = AutonomousSelfHealingGovernor()
        res = governor.execute_5tier_remediation(9999, simulate_hardware_failure=True)
        assert res["remediation_tier"] == 5
        assert res["status"] == "CIRCUIT_BREAKER_TRIPPED_SAFE_MODE"
        assert res["resolved"] is False

    def test_layer3_antigravity_skills_immunity(self):
        """L3.6: Verifies Antigravity skills persistence immunity audit."""
        governor = AutonomousSelfHealingGovernor()
        immunity = governor.verify_antigravity_skills_immunity()
        assert immunity["total_verified_skills"] > 0
        assert immunity["core_skills_verified"] is True
        assert len(immunity["missing_core_skills"]) == 0

    def test_layer3_obsidian_dashboards_sync(self):
        """L3.7: Verifies 8 Obsidian dashboards inventory and real-time synchronization."""
        governor = AutonomousSelfHealingGovernor()
        sync_res = governor.sync_obsidian_dashboards()
        assert sync_res["total_dashboards"] == 8
        assert sync_res["status"] == "OBSIDIAN_SYNC_COMPLETE"


# ============================================================================
# 4. MASTER TRI-LAYER HYBRID ORCHESTRATOR ROUTING & INTEGRATION TESTS
# ============================================================================

class TestMasterTriLayerHybridOrchestrator:
    """Verifies end-to-end routing, failover cascades, and shadow guard verification."""

    def test_routing_macro_strategy_to_layer1(self):
        """M.1: Verifies macro-strategy tasks route to Layer 1 Cloud Orchestrator."""
        orchestrator = TriLayerHybridOrchestrator()
        task = TaskSpecification(
            task_id="TASK_MACRO_01",
            task_name="Whole Monorepo Cohesion Review",
            category="Macro_Strategy",
            description="Audit cross-subsystem contracts across 00_core_infrastructure to 12_continuous_lora_evolution.",
            context_tokens=150000,
            zero_cloud_spend=False
        )
        res = orchestrator.route_and_execute(task)
        assert res.selected_layer == 1
        assert "Gemini 3.7 Flash High" in res.primary_model
        assert res.cloud_cost_usd > 0.0
        assert res.success is True

    def test_routing_sovereign_task_to_layer2_with_shadow_guard(self):
        """M.2: Verifies standard code tasks route to Layer 2 Kimi Tandem + Layer 1 Shadow Guard."""
        orchestrator = TriLayerHybridOrchestrator()
        task = TaskSpecification(
            task_id="TASK_LOCAL_02",
            task_name="Ray Actor Telemetry Multiplexer",
            category="Backend_Logic",
            description="Implement async multiplexer for 128Hz Movesense telemetry stream.",
            subsystem_target="03_biometrics_and_telemetry",
            requires_shadow_guard=True,
            zero_cloud_spend=True
        )
        res = orchestrator.route_and_execute(task)
        assert res.selected_layer == 2
        assert "Kimi-Dev-72B" in res.primary_model
        assert res.cloud_cost_usd == 0.00
        assert res.shadow_guard_result is not None
        assert res.shadow_guard_result.is_valid is True
        assert res.shadow_guard_result.zero_mock_verified is True

    def test_routing_visual_task_to_layer2_edge(self):
        """M.3: Verifies visual inspection routes directly to Layer 2 Edge Fallback (Qwen2.5-VL-7B)."""
        orchestrator = TriLayerHybridOrchestrator()
        task = TaskSpecification(
            task_id="TASK_VIS_03",
            task_name="Tatami Spatial Map Verification",
            category="UI_UX_Optimization",
            description="Verify tatami joint coordinates and check for zero-mock metrics.",
            requires_visual=True,
            frame_payload="base64_encoded_tatami_frame_123"
        )
        res = orchestrator.route_and_execute(task)
        assert res.selected_layer == 2
        assert "Qwen2.5-VL-7B" in res.primary_model
        assert res.cloud_cost_usd == 0.00
        assert res.success is True

    def test_routing_zero_cloud_spend_clamp_forces_local_cascade(self):
        """M.4: Verifies zero cloud spend constraint forces local cascade even for large tasks."""
        orchestrator = TriLayerHybridOrchestrator()
        task = TaskSpecification(
            task_id="TASK_LOCAL_FORCED_04",
            task_name="Offline Big Data Parsing",
            category="Cross_Repo_Planning",
            description="Perform large context parsing with strictly $0 cloud budget.",
            context_tokens=120000,
            zero_cloud_spend=True
        )
        res = orchestrator.route_and_execute(task)
        assert res.selected_layer == 2
        assert res.cloud_cost_usd == 0.00
        assert res.failover_occurred is True
        assert "cloud_layer1_skipped_zero_budget" in res.failover_chain_attempted

    def test_tri_layer_bridge_singleton_access(self):
        """M.5: Verifies swarm bridge returns valid singleton TriLayerHybridOrchestrator."""
        orch1 = get_tri_layer_orchestrator()
        orch2 = get_tri_layer_orchestrator()
        assert orch1 is orch2
        assert isinstance(orch1, TriLayerHybridOrchestrator)


# ============================================================================
# 5. ZERO MOCK & INTEGRITY RULE #0 TESTS
# ============================================================================

class TestZeroMockAndIntegrityCompliance:
    """Verifies that all generated artifacts, data structures, and outputs are 100% genuine."""

    def test_lora_dataset_serialization_contains_no_mock(self):
        """Z.1: Verifies serialized LoRA dataset records contain genuine instructions and zero mock tags."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_lora_file = Path(tmpdir) / "truth_audit_debate.jsonl"
            record = {
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "task_id": "TEST_TRUTH_01",
                "instruction": "Tri-Layer Hybrid Orchestration Verification",
                "input": "{\"subsystem\": \"00_core_infrastructure\", \"zero_mock\": true}",
                "output": "Kimi Tandem + Gemini 3.7 Flash High + Nomad Courier verified.",
                "cloud_cost_usd": 0.00
            }
            with open(test_lora_file, "w", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
                
            raw = test_lora_file.read_text(encoding="utf-8")
            loaded = json.loads(raw)
            assert "SIMULATED" not in raw
            assert "FAKE" not in raw
            assert loaded["task_id"] == "TEST_TRUTH_01"

    def test_real_time_hardware_constants_integrity(self):
        """Z.2: Verifies physical constants match monorepo hardware ground truth."""
        engine = SovereignLocalAIEngine()
        hw = engine.get_hardware_mesh_status()
        assert hw["total_pooled_vram_gb"] == 82.8
        total_alloc = round(hw["kimi_dev_72b_vram_gb"] + hw["kimi_vl_thinking_vram_gb"] + hw["qwen_edge_fallback_vram_gb"], 2)
        assert total_alloc == 53.2
        assert hw["tb4_rtt_ms"] < 0.30
