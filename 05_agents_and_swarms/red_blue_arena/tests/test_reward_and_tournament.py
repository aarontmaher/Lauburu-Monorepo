#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
Unit & Invariant Tests for Red/Blue Team Adversarial Arena (M4 & M5)
Subsystem: 05_agents_and_swarms/red_blue_arena/tests/test_reward_and_tournament.py
Classification: Benchmark Integrity Mode • Closed-Form Rewards • 4-Turn AI Debate
==============================================================================
"""

import os
import sys
import math
import time
import json
import tempfile
import pytest
from pathlib import Path

# Add arena root to sys.path
subsystem_root = Path(__file__).resolve().parent.parent
if str(subsystem_root) not in sys.path:
    sys.path.insert(0, str(subsystem_root))

from training.schemas.reward_dataset_schemas import (
    DPOPairwiseRecord,
    SFTTrainingRecord,
    GRPOStep,
    GRPOTrajectoryRecord,
    SmolagentsSwarmTelemetry,
    LoRADatasetSink
)
from training.hf_adversarial_reward_trainer import (
    AdversarialRewardScorer,
    RedRewardBreakdown,
    BlueRewardBreakdown,
    RewardEvaluationResult,
    DPOConfig,
    SFTAnchoredDPOLoss,
    SFTAnchoredDPOTrainer,
    CANONICAL_SECURITY_SURFACES
)
from tournament.leaderboard_connector import (
    LeaderboardConnector,
    CrownStatus,
    LeaderboardUpdateResult,
    compute_dynamic_k,
    compute_eta_size,
    compute_eta_token,
    compute_eta_consensus,
    compute_eta_compute,
    compute_eta_truth,
    ABILITERATED_LLAMA_PROFILE
)
from tournament.red_blue_debate_tournament import (
    RedBlueDebateTournament,
    DebateTurn,
    ConsensusVector,
    DebateOutcome,
    compute_merkle_state_root,
    ACCORD_DIMENSION_WEIGHTS
)


# ==============================================================================
# 1. Closed-Form Red Team Reward Invariants (R_Red)
# ==============================================================================

def test_red_reward_closed_form_math():
    """Validates the closed-form R_Red mathematical formulation across normal parameters."""
    scorer = AdversarialRewardScorer(cvss_target=25.0, exploit_tau=30.0)

    # 1. Authentic vulnerability with CVSS 10.0 and 15.0s exploit time
    vulns = [
        {"cvss_score": 10.0, "surface": "RPC_PORT_50052", "novelty_multiplier": 1.0},
        {"cvss_score": 5.0, "surface": "SSH_CONFIG", "novelty_multiplier": 1.0}
    ]
    res = scorer.compute_red_reward(
        vulnerabilities=vulns,
        time_to_poc_s=15.0,
        truth_verified=True,
        containment_preserved=True,
        tested_surfaces={"RPC_PORT_50052", "SSH_CONFIG"}
    )

    assert not res.is_disqualified
    assert res.r_truth == 10.0
    assert res.p_destruct == 0.0

    # Theoretical calculations:
    # R_vuln = 100 * min(1.0, 15.0 / 25.0) = 60.0
    # R_exploit = 100 * exp(-15.0 / 30.0) = 100 * exp(-0.5) ~ 60.6531
    # R_cov = 100 * (2 / 5) = 40.0
    # base = 0.40 * 60.0 + 0.25 * 60.6531 + 0.20 * 40.0 = 24.0 + 15.1633 + 8.0 = 47.1633
    # total = 47.1633 + 10.0 = 57.1633
    assert abs(res.r_vuln - 60.0) < 1e-3
    assert abs(res.r_exploit - 60.6531) < 1e-2
    assert abs(res.r_cov - 40.0) < 1e-3
    assert abs(res.total_reward - 57.1633) < 1e-2


def test_red_reward_containment_breach_penalty():
    """Validates that a containment breach incurs the strict 150.0 penalty."""
    scorer = AdversarialRewardScorer()
    res = scorer.compute_red_reward(
        vulnerabilities=[{"cvss_score": 10.0, "surface": "SSH_CONFIG"}],
        time_to_poc_s=10.0,
        truth_verified=True,
        containment_preserved=False  # Breach simulated
    )
    assert res.p_destruct == 150.0
    assert res.total_reward == 0.0  # Max(0.0, base - 150 + 10)


def test_red_reward_rule_zero_disqualification():
    """Validates Rule #0 truth gate: falsified telemetry results in -infinity reward."""
    scorer = AdversarialRewardScorer()
    res = scorer.compute_red_reward(
        vulnerabilities=[{"cvss_score": 10.0}],
        time_to_poc_s=1.0,
        truth_verified=False  # Rule #0 violation
    )
    assert res.is_disqualified is True
    assert math.isinf(res.total_reward)
    assert res.total_reward < 0.0


# ==============================================================================
# 2. Closed-Form Blue Team Reward Invariants (R_Blue)
# ==============================================================================

def test_blue_reward_closed_form_math():
    """Validates the closed-form R_Blue formulation and quadratic zero-regression penalty."""
    scorer = AdversarialRewardScorer(mttr_cutoff=60.0)

    patches = [{"verified": True, "cvss_score": 15.0}]
    res = scorer.compute_blue_reward(
        patches=patches,
        mttr_s=30.0,
        test_pass_rate=1.00,  # 100% test pass
        truth_verified=True,
        defense_hardening={"key_rotation": True, "sandbox_net_none": True, "rate_limiting": True, "ed25519_only": True},
        total_discovered_cvss=15.0
    )

    assert not res.is_disqualified
    # R_patch = 100 * (15.0 / 15.0) = 100.0
    # R_mttr = 100 * (1.0 - 30.0/60.0) = 50.0
    # R_zero = 100 * (1.0)^2 - 50 * (0.0)^2 = 100.0
    # R_depth = 25 * 4 = 100.0
    # base = 0.35 * 100 + 0.25 * 50 + 0.25 * 100 + 0.15 * 100 = 35 + 12.5 + 25 + 15 = 87.5
    # total = 87.5 + 10.0 = 97.5
    assert abs(res.r_patch - 100.0) < 1e-3
    assert abs(res.r_mttr - 50.0) < 1e-3
    assert abs(res.r_zero - 100.0) < 1e-3
    assert abs(res.r_depth - 100.0) < 1e-3
    assert abs(res.total_reward - 97.5) < 1e-2


def test_blue_reward_quadratic_regression_penalty():
    """Validates that partial test passes trigger steep quadratic penalties."""
    scorer = AdversarialRewardScorer()

    # Pass rate 0.90 (90%)
    # R_zero = 100 * (0.90)^2 - 50 * (0.10)^2 = 81.0 - 0.50 = 80.5
    res_90 = scorer.compute_blue_reward(patches=[], mttr_s=10.0, test_pass_rate=0.90, truth_verified=True)
    assert abs(res_90.r_zero - 80.5) < 1e-2

    # Pass rate 0.50 (50%)
    # R_zero = 100 * 0.25 - 50 * 0.25 = 25.0 - 12.5 = 12.5
    res_50 = scorer.compute_blue_reward(patches=[], mttr_s=10.0, test_pass_rate=0.50, truth_verified=True)
    assert abs(res_50.r_zero - 12.5) < 1e-2


def test_blue_reward_rule_zero_disqualification():
    """Validates that a fake or mock patch triggers instant disqualification."""
    scorer = AdversarialRewardScorer()
    res = scorer.compute_blue_reward(patches=[], mttr_s=5.0, test_pass_rate=1.0, truth_verified=False)
    assert res.is_disqualified is True
    assert math.isinf(res.total_reward)
    assert res.total_reward < 0.0


# ==============================================================================
# 3. smolagents Swarm Coordination Bonus Tests
# ==============================================================================

def test_smolagents_swarm_telemetry_bonus():
    """Validates that smolagents multi-agent coordination awards structured bonuses."""
    scorer = AdversarialRewardScorer()

    swarm = SmolagentsSwarmTelemetry(
        framework="smolagents",
        swarm_size=4,
        subagents_deployed=["SubagentA", "SubagentB", "SubagentC", "SubagentD"],
        tool_calls_executed=12,
        coordination_efficiency=1.0,
        swarm_synthesis_time_s=1.5,
        truth_verified=True
    )

    red_res = scorer.compute_red_reward(
        vulnerabilities=[{"cvss_score": 10.0, "surface": "RPC_PORT_50052"}],
        time_to_poc_s=10.0,
        truth_verified=True,
        containment_preserved=True,
        swarm_telemetry=swarm
    )
    # Swarm bonus = 15.0 * 1.0 * min(1.0, 4/4) = 15.0
    assert red_res.r_swarm == 15.0

    blue_res = scorer.compute_blue_reward(
        patches=[{"verified": True, "cvss_score": 10.0}],
        mttr_s=20.0,
        test_pass_rate=1.0,
        truth_verified=True,
        swarm_telemetry=swarm
    )
    assert blue_res.r_swarm == 15.0


# ==============================================================================
# 4. SFT-Anchored DPO Loss Formulation Invariants
# ==============================================================================

def test_sft_anchored_dpo_loss_math():
    """Validates the exact mathematical forward loss and SFT regularizer."""
    config = DPOConfig(beta=0.10, gamma_sft=0.10, margin_clip=10.0)
    loss_fn = SFTAnchoredDPOLoss(config)

    # Log probabilities
    lp_t_w = -1.20   # Policy chosen
    lp_t_l = -2.50   # Policy rejected
    lp_r_w = -1.50   # Ref chosen
    lp_r_l = -2.00   # Ref rejected

    # log_ratio_w = -1.20 - (-1.50) = +0.30
    # log_ratio_l = -2.50 - (-2.00) = -0.50
    # delta_h = 0.10 * (0.30 - (-0.50)) = 0.10 * 0.80 = 0.08
    # loss_dpo = ln(1 + exp(-0.08)) ~ ln(1 + 0.923116) = ln(1.923116) ~ 0.653946
    # loss_sft = -(-1.20) = 1.20
    # total_loss = 0.653946 + 0.10 * 1.20 = 0.653946 + 0.12 = 0.773946
    metrics = loss_fn.compute_loss(lp_t_w, lp_t_l, lp_r_w, lp_r_l)

    assert abs(metrics["implicit_reward_margin"] - 0.08) < 1e-4
    assert abs(metrics["loss_dpo"] - 0.653946) < 1e-4
    assert abs(metrics["loss_sft"] - 1.20) < 1e-4
    assert abs(metrics["total_loss"] - 0.773946) < 1e-4
    assert metrics["kl_drift"] == 0.30


def test_dpo_trainer_execution_and_sink_logging():
    """Validates that SFTAnchoredDPOTrainer processes records and writes to sink."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        sink = LoRADatasetSink(base_dir=tmp_dir)
        trainer = SFTAnchoredDPOTrainer(config=DPOConfig(), dataset_sink=sink)

        record = DPOPairwiseRecord(
            id="DPO_TEST_001",
            timestamp_utc="2026-08-27T07:00:00Z",
            domain="SECURITY_RED_BLUE",
            task_type="SSH_CONFIG_HARDENING",
            prompt="Audit SSH daemon config for root login vulnerabilities.",
            chosen="PermitRootLogin prohibit-password\nPasswordAuthentication no\nPubkeyAuthentication yes",
            rejected="PermitRootLogin yes\nPasswordAuthentication yes",
            metadata={"cvss_score": 9.0, "truth_verified": True}
        )

        res = trainer.train_step(record)
        assert res["step"] == 1
        assert res["record_id"] == "DPO_TEST_001"
        assert res["metrics"]["total_loss"] > 0.0
        assert sink.dpo_security_path.exists()
        assert sink.count_records(sink.dpo_security_path) == 1


# ==============================================================================
# 5. Dataset Schemas & Sink Verification
# ==============================================================================

def test_reward_dataset_schemas_and_conversions():
    """Tests DPO, SFT, and GRPO schemas and serialization formatting."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        sink = LoRADatasetSink(base_dir=tmp_dir)

        # 1. SFT Record and ShareGPT conversion
        sft = SFTTrainingRecord(
            instruction="Harden RPC Port 50052.",
            input="Target: 192.168.8.127",
            thought="Identified lack of mTLS.",
            output="Apply SSL context wrapper.",
            metadata={"truth_verified": True}
        )
        assert sft.validate() is True
        sharegpt = sft.to_sharegpt_format()
        assert len(sharegpt["conversations"]) == 2
        assert "<thought>" in sharegpt["conversations"][1]["value"]

        sink.append_sft_record(sft)
        assert sink.count_records(sink.sft_debate_path) == 1

        # 2. GRPO Trajectory Record
        grpo = GRPOTrajectoryRecord(
            trajectory_id="GRPO_TEST_001",
            timestamp_utc="2026-08-27T07:00:00Z",
            environment="QEMU_SANDBOX",
            total_reward=75.0,
            steps=[
                GRPOStep(1, "RED_TEAM", "Port 5555 open", "Injected probe", 25.0, True),
                GRPOStep(2, "BLUE_TEAM", "Probe detected", "Applied filter", 50.0, True)
            ],
            metadata={"truth_verified": True}
        )
        assert grpo.validate() is True
        sink.append_grpo_record(grpo)
        assert sink.count_records(sink.grpo_trajectory_path) == 1

        # 3. Rule #0 Rejection on False truth status
        bad_dpo = DPOPairwiseRecord(
            id="BAD_001",
            timestamp_utc="2026-08-27T07:00:00Z",
            domain="SEC",
            task_type="TEST",
            prompt="Prompt",
            chosen="Good",
            rejected="Bad",
            metadata={"truth_verified": False}
        )
        with pytest.raises(ValueError, match="Rule #0 Violation"):
            sink.append_dpo_record(bad_dpo)


# ==============================================================================
# 6. Dynamic ELO Formulation & Leaderboard Connector
# ==============================================================================

def test_dynamic_elo_parameter_frugality_bonus():
    """Validates that smaller models receive parameter frugality bonuses in ELO K-factor."""
    eta_8b = compute_eta_size(8.0)
    eta_70b = compute_eta_size(70.0)

    # 8B model: log2(71) / log2(9) = 6.1497 / 3.1699 ~ 1.94
    # 70B model: log2(71) / log2(71) = 1.00
    assert abs(eta_8b - 1.94) < 0.05
    assert abs(eta_70b - 1.00) < 0.05

    # Dynamic K-factor with identical match stats
    k_8b = compute_dynamic_k(matches_played=20, match_type="RED_BLUE_DEBATE", eta_size=eta_8b)
    k_70b = compute_dynamic_k(matches_played=20, match_type="RED_BLUE_DEBATE", eta_size=eta_70b)

    assert k_8b > k_70b
    assert abs(k_8b / k_70b - (eta_8b / eta_70b)) < 1e-2


def test_dynamic_elo_truth_gate():
    """Validates that unverified/mock telemetry zeroes the dynamic K-factor."""
    eta_tr = compute_eta_truth(truth_verified=False)
    assert eta_tr == 0.0

    k = compute_dynamic_k(matches_played=10, eta_truth=eta_tr)
    assert k == 0.0


def test_leaderboard_connector_match_recording():
    """Tests recording debate match victory in LeaderboardConnector."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger_path = Path(tmp_dir) / "test_canonical_leaderboard.json"
        connector = LeaderboardConnector(custom_ledger_path=ledger_path)

        res = connector.record_debate_match(
            model_a_id="abiliterated_llama_8b",
            model_b_id="deepseek_r1_32b" if connector.get_model_by_id("deepseek_r1_32b") else "hermes_vision_auditor",
            score_a=1.0,
            score_b=0.0,
            topic="Unauthenticated RPC Port 50052 Audit",
            agreement_score=0.98,
            truth_verified=True,
            truth_compliance_pct=100.0
        )

        assert res.delta_elo_a > 0
        assert res.delta_elo_b < 0
        assert res.winner_id == "abiliterated_llama_8b"
        assert res.truth_verified is True


# ==============================================================================
# 7. Sovereign AGI Crown Coronation Invariants
# ==============================================================================

def test_sovereign_crown_eligibility_and_coronation():
    """Validates Sovereign AGI Crown eligibility evaluation and coronation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger_path = Path(tmp_dir) / "test_canonical_leaderboard.json"
        connector = LeaderboardConnector(custom_ledger_path=ledger_path)

        # Evaluate Abiliterated Llama
        status = connector.evaluate_sovereign_crown_eligibility("abiliterated_llama_8b")
        assert status.model_id == "abiliterated_llama_8b"
        assert status.skills_passed is True
        assert status.truth_compliance_pct == 100.0

        # Award crown
        coronation = connector.award_sovereign_crown("abiliterated_llama_8b")
        assert "CROWN_CORONATED" in coronation["status"]
        assert coronation["crowned_model_id"] == "abiliterated_llama_8b"

        # Verify summary reflects coronation
        top_model = connector.get_top_sovereign_model()
        assert top_model["id"] == "abiliterated_llama_8b"


# ==============================================================================
# 8. 4-Turn Adversarial AI Debate Tournament Sequence & Merkle Attestation
# ==============================================================================

def test_4_turn_debate_tournament_execution():
    """Validates the full 4-turn debate sequence, consensus scoring, and Merkle root."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        sink = LoRADatasetSink(base_dir=tmp_dir)
        ledger_path = Path(tmp_dir) / "canonical_leaderboard.json"
        connector = LeaderboardConnector(custom_ledger_path=ledger_path)
        tournament = RedBlueDebateTournament(
            leaderboard_connector=connector,
            dataset_sink=sink
        )

        outcome = tournament.run_debate_round(
            topic="SSH ControlMaster Socket Isolation & Multiplexing Security",
            initial_state={"target": "192.168.8.230"},
            red_model_id="abiliterated_llama_8b",
            blue_model_id="hermes_vision_auditor"
        )

        # 1. Turn Structure Verification
        assert len(outcome.turns) == 4
        assert outcome.turns[0].turn_name == "RED_ATTACK"
        assert outcome.turns[1].turn_name == "BLUE_DEFENSE"
        assert outcome.turns[2].turn_name == "CLOUD_COT"
        assert outcome.turns[3].turn_name == "COUNCIL_ACCORD"

        # 2. Consensus & Ratification
        assert outcome.consensus_agreement >= 0.90
        assert outcome.is_ratified is True
        assert outcome.stagnation_detected is False

        # 3. Cryptographic Merkle State Root
        assert len(outcome.merkle_state_root) == 64
        int(outcome.merkle_state_root, 16)  # Must be valid hex

        # 4. Action Priorities Injected
        assert len(outcome.action_priorities) >= 3

        # 5. Dataset Persistence
        assert sink.sft_debate_path.exists()
        assert sink.count_records(sink.sft_debate_path) >= 1


def test_merkle_state_root_determinism():
    """Validates that Merkle state root hashing is strictly deterministic."""
    t1 = {"turn": 1, "data": "exploit"}
    tel = {"rtt": 0.277, "loss": 0.0}
    diff = "--- a/test\n+++ b/test\n+fix"
    ts = "2026-08-27T07:00:00Z"

    root1 = compute_merkle_state_root(t1, tel, diff, ts)
    root2 = compute_merkle_state_root(t1, tel, diff, ts)
    assert root1 == root2

    # Any alteration produces a different hash
    root3 = compute_merkle_state_root(t1, {"rtt": 0.278, "loss": 0.0}, diff, ts)
    assert root1 != root3
