#!/usr/bin/env python3
"""
Unit Tests for Qwen MoE Sovereign Orchestrator, Supreme Auditor & Self-Optimizer
================================================================================
Validates:
1. Bradley-Terry Logistic ELO calculations & expected score bounds
2. Supreme Victory Auditor 4-Tier Verification Gate (AST, Zero-Mock, UI, Scratch Tests)
3. Workflow Self-Optimizer bottleneck detection & auto-remediation protocols
4. Knapsack / ILP Distributed Sharding layer allocations
5. DARE-TIES Expectation-Preserving Rescale Math (E[W_hat] = W)
"""

import sys
import pytest
import math
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SWARMS_ROOT = TEST_DIR.parent

if str(SWARMS_ROOT) not in sys.path:
    sys.path.insert(0, str(SWARMS_ROOT))

from qwen_moe_orchestrator import (
    QwenMoEOrchestrator,
    BradleyTerryELORater,
    SupremeVictoryAuditor,
    WorkflowSelfOptimizer,
    DistributedShardingOptimizer,
    WeightMergeOptimizer,
    MESH_HARDWARE_TOPOLOGY
)


class TestBradleyTerryELORater:

    def test_equal_ratings_expected_score_is_half(self):
        rater = BradleyTerryELORater()
        exp = rater.compute_expected_score(1800.0, 1800.0)
        assert pytest.approx(exp, 0.001) == 0.50

    def test_higher_rating_has_higher_expected_score(self):
        rater = BradleyTerryELORater()
        exp_favored = rater.compute_expected_score(2000.0, 1600.0)
        exp_underdog = rater.compute_expected_score(1600.0, 2000.0)
        assert exp_favored > 0.90
        assert exp_underdog < 0.10
        assert pytest.approx(exp_favored + exp_underdog, 0.001) == 1.0

    def test_elo_update_delta(self):
        rater = BradleyTerryELORater(k_factor=32.0)
        new_a, new_b, exp_a = rater.evaluate_match(1900.0, 1900.0, 1.0)
        assert new_a > 1900.0
        assert new_b < 1900.0
        assert pytest.approx((new_a - 1900.0) + (new_b - 1900.0), 0.01) == 0.0

    def test_multi_factor_scoring_weights(self):
        rater = BradleyTerryELORater()
        score_perfect = rater.compute_multi_factor_score(True, True, 1.0, 0.1)
        assert score_perfect >= 0.95

        score_failed_ast = rater.compute_multi_factor_score(False, True, 1.0, 0.1)
        assert score_failed_ast <= 0.50


class TestSupremeVictoryAuditor:

    def test_clean_code_claim_is_confirmed(self):
        auditor = SupremeVictoryAuditor()
        clean_code = "def process_ecg(val: float) -> float:\n    return val * 1.5\n"
        cert = auditor.verify_completion_claim({"task_id": "TEST_CLEAN", "title": "Clean ECG"}, clean_code)
        assert cert["verdict"] == "VICTORY CONFIRMED & SIGNED OFF"
        assert cert["gates"]["gate_1_ast_syntax"]["passed"] is True
        assert cert["gates"]["gate_2_zero_mock"]["passed"] is True
        assert "QWEN-MOE-CERT" in cert["certificate_hash"]

    def test_rule_0_violation_is_rejected(self):
        auditor = SupremeVictoryAuditor()
        mock_code = "def get_heart_rate():\n    return random.randint(60, 100)\n"
        cert = auditor.verify_completion_claim({"task_id": "TEST_MOCK", "title": "Fake HR"}, mock_code)
        assert cert["verdict"] == "COMPLETION CLAIM REJECTED"
        assert cert["gates"]["gate_2_zero_mock"]["passed"] is False

    def test_unbounded_renderflex_layout_is_rejected(self):
        auditor = SupremeVictoryAuditor()
        flutter_overflow_code = "Column(children: [Text('Unbounded'), ListView(children: [])])"
        cert = auditor.verify_completion_claim({"task_id": "TEST_OVERFLOW", "title": "Bad UI"}, flutter_overflow_code)
        assert cert["verdict"] == "COMPLETION CLAIM REJECTED"
        assert cert["gates"]["gate_3_visual_ui"]["passed"] is False


class TestWorkflowSelfOptimizer:

    def test_profile_mesh_healthy_state(self):
        opt = WorkflowSelfOptimizer()
        prof = opt.profile_mesh_performance()
        assert "status" in prof
        assert isinstance(prof["bottlenecks"], list)

    def test_execute_self_optimization_protocol(self):
        opt = WorkflowSelfOptimizer()
        res = opt.execute_self_optimization_protocol({
            "component": "Local_Code_Model",
            "remediation": "Launch Metal QLoRA fine-tuning protocol."
        })
        assert res["status"] == "EXECUTED"
        assert "AUTO_REMEDIATION" in res["protocol"]


class TestDistributedShardingOptimizer:

    def test_knapsack_sharding_allocates_all_layers(self):
        total_layers = 80
        res = DistributedShardingOptimizer.calculate_optimal_tensor_split(total_layers, 42.0)
        assert res["total_layers"] == total_layers
        alloc = res["layer_allocations"]
        total_allocated = sum(node["count"] for node in alloc.values())
        assert total_allocated == total_layers

    def test_tb4_bridge_latency_is_sub_millisecond(self):
        res = DistributedShardingOptimizer.calculate_optimal_tensor_split(80, 42.0)
        assert res["tb4_bridge_latency_ms"] < 0.50


class TestWeightMergeOptimizer:

    def test_dare_expectation_preservation(self):
        res = WeightMergeOptimizer.calculate_dare_density(0.30)
        assert res["expectation_preserving"] is True
        assert pytest.approx(res["retention_rate"] * res["rescale_factor"], 0.001) == 1.0


class TestIdleExpertTrainingScheduler:

    def test_identify_idle_experts(self):
        from qwen_moe_orchestrator import IdleExpertTrainingScheduler
        sched = IdleExpertTrainingScheduler()
        idle = sched.identify_idle_experts(["Expert_0_AST_Code"])
        assert len(idle) == 5
        assert "Expert_1_Visual_UI" in idle
        assert "Expert_0_AST_Code" not in idle

    def test_schedule_idle_expert_training(self):
        from qwen_moe_orchestrator import IdleExpertTrainingScheduler
        sched = IdleExpertTrainingScheduler()
        idle = sched.identify_idle_experts(["Expert_0_AST_Code"])
        rep = sched.schedule_idle_expert_training(idle)
        assert rep["idle_experts_trained"] == 5
        assert rep["host_inference_impact_ms"] == 0.0


class TestThunderboltDMATrainingGovernor:

    def test_inspect_thunderbolt_bridge(self):
        from qwen_moe_orchestrator import ThunderboltDMATrainingGovernor
        gov = ThunderboltDMATrainingGovernor()
        info = gov.inspect_thunderbolt_bridge()
        assert info["interface"] == "bridge0"
        assert info["measured_rtt_ms"] < 0.50
        assert info["bandwidth_gbps"] >= 10.0
        assert info["status"] == "DMA_ACTIVE"

    def test_synchronize_distributed_expert_gradients(self):
        from qwen_moe_orchestrator import ThunderboltDMATrainingGovernor
        gov = ThunderboltDMATrainingGovernor()
        sync = gov.synchronize_distributed_expert_gradients("Expert_2_Biometrics_DSP", 0.35)
        assert sync["transport"] == "Thunderbolt 4 PCIe DMA (bridge0)"
        assert sync["allreduce_status"] == "CONVERGED"
        assert sync["sync_latency_ms"] < 0.50


class TestQwenMoEOrchestratorIntegration:

    def test_orchestrator_sign_off_and_self_opt(self):
        orch = QwenMoEOrchestrator()
        clean_code = "def valid_func():\n    return 42\n"
        cert = orch.sign_off_completion({"task_id": "TASK_INT", "title": "Integration Test"}, clean_code)
        assert cert["verdict"] == "VICTORY CONFIRMED & SIGNED OFF"
        assert orch.state["total_certificates_issued"] >= 1

        self_opt_res = orch.run_self_optimization_cycle()
        assert "profile" in self_opt_res
        assert "idle_expert_training" in self_opt_res
        assert orch.state["self_optimizations_run"] >= 1
        assert orch.state["idle_expert_training_cycles"] >= 1


if __name__ == "__main__":
    pytest.main(["-v", __file__])
