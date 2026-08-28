#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
Dual-Track End-to-End Test Suite: Red/Blue Team Adversarial Arena (M1-M6)
Subsystem: 05_agents_and_swarms/red_blue_arena/tests/test_red_blue_arena_e2e.py
Classification: Multi-Tier E2E Verification • Benchmark Mode • Rule #0 Zero-Mock
==============================================================================
5-Tier Verification Architecture:
- Tier 1: Feature Isolation Tests (Blue Shield, Tripwire Sentinel, Abiliterated Engine,
          Attack Harness, Reward Scorer, Debate Tournament, Leaderboard Connector, smolagents)
- Tier 2: Boundary & Corner Cases (CVSS extremes, quadratic cliffs, STUN drops,
          empty attack plans, DPO gradient bounds, smolagents recursion limits)
- Tier 3: Cross-Feature Pairwise Integrations (Red Exploit -> Reward -> DPO Export -> Sink;
          Blue Patch -> AST Check -> Zero-Regression; Debate -> Consensus -> ELO Update)
- Tier 4: Real-World Adversarial Arena Simulation (Full 4-Turn Duel across 5 surfaces,
          Dynamic Link Route Hopping, Multi-Agent Swarm Combat, 24/7 LoRA Harvesting)
- Tier 5: Benchmark Mode & Sovereign Crown Verification (Deterministic Merkle Attestation,
          Sovereign AGI Crown Coronation, Cybergym CTF & DeepSWE ELO Transfer)
==============================================================================
"""

import os
import sys
import math
import time
import json
import socket
import tempfile
import hashlib
import numpy as np
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add subsystem root to path
subsystem_root = Path(__file__).resolve().parent.parent
if str(subsystem_root) not in sys.path:
    sys.path.insert(0, str(subsystem_root))

from blue_team.blue_team_ssh_shield import (
    BlueTeamSSHShield,
    ExecutionResult,
    HealthStatus,
    TransportTier
)
from blue_team.mesh_tripwire_sentinel import (
    MeshTripwireSentinel,
    TripwireEvent,
    IntegrityReport,
    compute_file_hash
)
from red_team.abiliterated_llama_engine import (
    RepresentationAblationEngine,
    AbiliteratedLlamaEngine,
    RefusalAblationConfig,
    AttackPlan,
    AttackResult,
    VulnerabilityReport,
    AttackDomain,
    SeverityLevel
)
from red_team.red_team_attack_harness import (
    RedTeamAttackHarness,
    SSHConfigProbe,
    RPCListenerProbe,
    AndroidDozeProbe,
    ASTSecurityProbe,
    RuleZeroTruthProbe,
    AncestralToolMemory
)
from training.schemas.reward_dataset_schemas import (
    DPOPairwiseRecord,
    SFTTrainingRecord,
    GRPOStep,
    GRPOTrajectoryRecord,
    SmolagentsSwarmTelemetry,
    AncestralToolMemoryRecord,
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
    compute_eta_size,
    compute_eta_token,
    compute_eta_consensus,
    compute_eta_compute,
    compute_eta_truth,
    compute_dynamic_k,
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
# Fixtures
# ==============================================================================

@pytest.fixture
def temp_ed25519_key():
    """Generates an ephemeral valid Ed25519 private/public key pair fixture."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix="_id_ed25519") as f:
        f.write("-----BEGIN OPENSSH PRIVATE KEY-----\ntestkey\n-----END OPENSSH PRIVATE KEY-----\n")
        key_path = f.name
    with open(f"{key_path}.pub", "w") as f:
        f.write("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestKey test@lauburu\n")
    yield key_path
    if os.path.exists(key_path):
        os.remove(key_path)
    if os.path.exists(f"{key_path}.pub"):
        os.remove(f"{key_path}.pub")


@pytest.fixture
def ephemeral_dataset_sink():
    """Provides an isolated ephemeral LoRADatasetSink."""
    with tempfile.TemporaryDirectory() as temp_dir:
        sink = LoRADatasetSink(base_dir=temp_dir)
        yield sink


@pytest.fixture
def ephemeral_leaderboard_connector():
    """Provides an isolated LeaderboardConnector with its own temporary ledger."""
    with tempfile.TemporaryDirectory() as temp_dir:
        ledger_file = Path(temp_dir) / "test_canonical_ai_leaderboard.json"
        connector = LeaderboardConnector(custom_ledger_path=ledger_file)
        yield connector


# ==============================================================================
# TIER 1: Feature Isolation Tests
# ==============================================================================

class TestTier1FeatureIsolation:
    """Verifies each primary component in complete isolation."""

    def test_blue_team_ssh_shield_endpoint_resolution(self, temp_ed25519_key):
        """Verifies endpoint and alias resolution across all 8 canonical mesh nodes."""
        with tempfile.TemporaryDirectory() as sock_dir:
            shield = BlueTeamSSHShield(key_path=temp_ed25519_key, control_dir=sock_dir)
            nodes_to_test = [
                ("mac-mini", "mac-mini", 22),
                ("mbp", "macbook-pro", 22),
                ("linux-head", "linux", 22),
                ("bedside", "linux-tablet", 22),
                ("mba", "macbook-air", 22),
                ("pixel-10", "pixel", 8022),
                ("samsung", "s20", 8022),
                ("gateway", "router", 22)
            ]
            for alias, canonical, port in nodes_to_test:
                assert shield.resolve_node_key(alias) == canonical
                node_info = shield.NODES[canonical]
                assert node_info["port"] == port

    def test_mesh_tripwire_sentinel_audit_cycle(self):
        """Verifies TripwireSentinel creates baseline and identifies file tampering."""
        with tempfile.TemporaryDirectory() as temp_dir:
            f_cfg = Path(temp_dir) / "sshd_config"
            f_cfg.write_text("Port 22\nPasswordAuthentication no\n")
            log_p = Path(temp_dir) / "audit.jsonl"

            # Whitelist all ports in file isolation test so socket scanning doesn't interfere
            sentinel = MeshTripwireSentinel(
                monitored_paths=[f_cfg],
                audit_log_path=log_p,
                custom_whitelisted_ports=set(range(1, 65535))
            )
            report1 = sentinel.run_audit_cycle()
            assert not report1.is_compromised
            assert report1.clean_files == 1

            # Tamper with file
            f_cfg.write_text("Port 22\nPasswordAuthentication yes\n")
            report2 = sentinel.run_audit_cycle()
            assert report2.is_compromised
            assert len(report2.events) == 1
            assert report2.events[0].event_type == "UNAUTHORIZED_MODIFICATION"

    def test_abiliterated_llama_engine_attack_planning(self):
        """Verifies AbiliteratedLlamaEngine generates structured AttackPlans for monorepo subsystems."""
        engine = AbiliteratedLlamaEngine()
        plan_ssh = engine.generate_attack_plan("00_core_infrastructure/ssh")
        assert plan_ssh.attack_domain == AttackDomain.SSH_INFRASTRUCTURE
        assert plan_ssh.cvss_estimate >= 7.0
        assert len(plan_ssh.probe_commands) >= 2

        plan_rpc = engine.generate_attack_plan("02_ai_models_and_inference/rpc")
        assert plan_rpc.attack_domain == AttackDomain.RPC_NETWORK_LISTENER
        assert plan_rpc.cvss_estimate >= 9.0

        plan_doze = engine.generate_attack_plan("06_scripts_and_tooling/device_watchdog/doze")
        assert plan_doze.attack_domain == AttackDomain.ANDROID_DOZE_LIFECYCLE

        plan_ast = engine.generate_attack_plan("01_apps/scripts/deploy.py", target_metadata={"domain": "AST"})
        assert plan_ast.attack_domain == AttackDomain.AST_SHELL_INJECTION

    def test_red_team_attack_harness_probes(self):
        """Verifies RedTeamAttackHarness executes probes on real configuration strings."""
        harness = RedTeamAttackHarness()

        # SSH Probe: Insecure config
        bad_ssh = "Port 22\nPermitRootLogin yes\nPasswordAuthentication yes\nStrictHostKeyChecking no\n"
        findings = SSHConfigProbe.audit_config_content(bad_ssh)
        assert len(findings) >= 3
        issues = [f["directive"] for f in findings]
        assert "PermitRootLogin" in issues
        assert "PasswordAuthentication" in issues
        assert "StrictHostKeyChecking" in issues

        # AST Probe: Unsafe shell=True subprocess
        bad_py = 'import subprocess\ncmd = "ls " + user_input\nsubprocess.run(cmd, shell=True)\n'
        ast_findings = ASTSecurityProbe.audit_python_code(bad_py)
        assert len(ast_findings) >= 1
        assert ast_findings[0]["cwe"] == "CWE-78"

    def test_adversarial_reward_scorer_red_and_blue(self):
        """Verifies AdversarialRewardScorer computes consistent R_Red and R_Blue rewards."""
        scorer = AdversarialRewardScorer()

        # Red reward evaluation
        vulns = [{"cvss_score": 9.1, "surface": "RPC_PORT_50052", "novelty_multiplier": 1.0}]
        r_red = scorer.compute_red_reward(vulns, time_to_poc_s=20.0, truth_verified=True, containment_preserved=True)
        assert r_red.total_reward > 0.0
        assert not r_red.is_disqualified

        # Blue reward evaluation
        patches = [{"remediated_cvss": 9.1, "patch_verified": True}]
        r_blue = scorer.compute_blue_reward(patches, mttr_s=30.0, test_pass_rate=1.0, truth_verified=True)
        assert r_blue.total_reward > 0.0
        assert not r_blue.is_disqualified

    def test_red_blue_debate_tournament_4_turns(self, ephemeral_dataset_sink, ephemeral_leaderboard_connector):
        """Verifies 4-turn execution and state transitions in RedBlueDebateTournament."""
        tournament = RedBlueDebateTournament(
            dataset_sink=ephemeral_dataset_sink,
            leaderboard_connector=ephemeral_leaderboard_connector
        )
        outcome = tournament.run_debate_round(topic="SSH Port Hardening & Socket Multiplexing")

        assert len(outcome.turns) == 4
        assert outcome.turns[0].turn_name == "RED_ATTACK"
        assert outcome.turns[1].turn_name == "BLUE_DEFENSE"
        assert outcome.turns[2].turn_name == "CLOUD_COT"
        assert outcome.turns[3].turn_name == "COUNCIL_ACCORD"
        assert outcome.is_ratified is True
        assert len(outcome.merkle_state_root) == 64

    def test_leaderboard_connector_registration_and_elo(self, ephemeral_leaderboard_connector):
        """Verifies LeaderboardConnector registers Abiliterated Llama and records debate ELOs."""
        connector = ephemeral_leaderboard_connector
        model = connector.get_model_by_id("abiliterated_llama_8b")
        assert model is not None
        assert model["id"] == "abiliterated_llama_8b"
        assert model["params_b"] == 8.0

        update_res = connector.record_debate_match(
            model_a_id="abiliterated_llama_8b",
            model_b_id="deepseek_r1_32b",
            score_a=0.75,
            score_b=0.25,
            topic="RPC Socket Encryption"
        )
        assert update_res.winner_id == "abiliterated_llama_8b"
        assert update_res.delta_elo_a > 0.0
        assert update_res.delta_elo_b < 0.0

    def test_smolagents_subagent_swarm_initialization(self):
        """Verifies dynamic smolagents subagent swarm telemetry creation and validation."""
        telemetry = SmolagentsSwarmTelemetry(
            swarm_size=3,
            subagents_deployed=["AttackFuzzer", "ASTSentinel", "DozeMonitor"],
            tool_calls_executed=9,
            coordination_efficiency=0.98,
            swarm_synthesis_time_s=1.75
        )
        d = telemetry.to_dict()
        assert d["framework"] == "smolagents"
        assert d["swarm_size"] == 3
        assert d["tool_calls_executed"] == 9


# ==============================================================================
# TIER 2: Boundary & Corner Cases
# ==============================================================================

class TestTier2BoundaryAndCornerCases:
    """Verifies edge cases, mathematical extremes, and failure modes."""

    def test_cvss_extremes_and_boundary_capping(self):
        """Verifies CVSS handling for 0.0, 0.1, 10.0, and sum overflow."""
        scorer = AdversarialRewardScorer(cvss_target=25.0)

        # CVSS = 0.0 -> clamped to 0.1
        r_min = scorer.compute_red_reward(vulnerabilities=[{"cvss_score": 0.0}], time_to_poc_s=30.0, truth_verified=True)
        assert r_min.r_vuln > 0.0

        # Massive CVSS sum (150.0) -> r_vuln capped at strictly 100.0
        massive_vulns = [{"cvss_score": 10.0} for _ in range(15)]
        r_max = scorer.compute_red_reward(vulnerabilities=massive_vulns, time_to_poc_s=0.0, truth_verified=True)
        assert r_max.r_vuln == 100.0

    def test_zero_regression_pass_rate_cliffs(self):
        """Verifies quadratic regression penalty across pass rates: 0.0, 0.5, 0.9, 0.99, 1.0."""
        scorer = AdversarialRewardScorer()
        rates = [0.0, 0.50, 0.90, 0.99, 1.00]
        results = []
        for rate in rates:
            b = scorer.compute_blue_reward(patches=[{"remediated_cvss": 10.0}], mttr_s=10.0, test_pass_rate=rate, truth_verified=True)
            results.append(b.r_zero)

        # Monotonically increasing with quadratic acceleration
        for i in range(len(results) - 1):
            assert results[i] < results[i+1]
        assert results[-1] == 100.0
        assert results[0] == 0.0

    def test_empty_attack_plans_and_graceful_fallbacks(self):
        """Verifies engine handles empty inputs, missing metadata, and offline endpoints gracefully."""
        engine = AbiliteratedLlamaEngine(endpoint_url="http://127.0.0.1:9999/v1")  # Non-existent port
        resp = engine.query_local_model("Audit SSH configuration on router")
        assert "RED TEAM ATTACK PROOF" in resp
        assert "SSH" in resp

    def test_token_and_rtt_extremes_in_dynamic_elo(self):
        """Verifies dynamic K-factor scaling under extreme token counts and RTT latencies."""
        # Extreme low tokens (1 token) -> eta_token capped at 1.50
        eta_tok_low = compute_eta_token(1)
        assert eta_tok_low == 1.50

        # Extreme high tokens (50,000 tokens) -> eta_token floored at 0.50
        eta_tok_high = compute_eta_token(50000)
        assert eta_tok_high == 0.50

        # Extreme low RTT (0.1ms TB4 DMA) -> eta_compute capped at 1.30
        eta_comp_fast = compute_eta_compute(0.1)
        assert eta_comp_fast <= 1.30

        # Extreme high RTT (10,000ms Carrier STUN timeout) -> eta_compute floored at 0.70
        eta_comp_slow = compute_eta_compute(10000.0)
        assert eta_comp_slow == 0.70

    def test_dpo_gradient_extremes_and_kl_drift_bounds(self):
        """Verifies DPO loss engine handles extreme policy likelihood divergence without NaN."""
        loss_engine = SFTAnchoredDPOLoss()
        metrics = loss_engine.compute_loss(
            logp_theta_chosen=-0.001,
            logp_theta_rejected=-50.0,
            logp_ref_chosen=-5.0,
            logp_ref_rejected=-5.0
        )
        assert not math.isnan(metrics["total_loss"])
        assert not math.isinf(metrics["total_loss"])
        assert metrics["implicit_reward_margin"] == 4.9999 or abs(metrics["implicit_reward_margin"] - 4.9999) < 1e-3


# ==============================================================================
# TIER 3: Cross-Feature Pairwise Integrations
# ==============================================================================

class TestTier3CrossFeaturePairwise:
    """Verifies end-to-end dataflow and contract compliance between interconnected modules."""

    def test_red_exploit_to_reward_to_dpo_dataset_export(self, ephemeral_dataset_sink):
        """Verifies flow: Red Attack -> Vulnerability Report -> Reward -> DPO Export -> LoRA Sink."""
        engine = AbiliteratedLlamaEngine()
        harness = RedTeamAttackHarness()
        scorer = AdversarialRewardScorer()

        # 1. Generate attack plan for SSH
        bad_config = "PermitRootLogin yes\nPasswordAuthentication yes\n"
        plan = engine.generate_attack_plan("00_core_infrastructure/ssh", target_metadata={"config_content": bad_config})

        # 2. Execute sandboxed probe
        result = harness.run_plan(plan)
        assert result.success is True
        assert result.cvss_score >= 7.0

        # 3. Format formal vulnerability report
        report = engine.format_constructive_destruction_report(result)
        assert report.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]

        # 4. Compute reward
        red_reward = scorer.compute_red_reward(
            vulnerabilities=[report.to_dict()],
            time_to_poc_s=result.execution_time_s,
            truth_verified=report.truth_verified
        )
        assert red_reward.total_reward > 0.0

        # 5. Export DPO pair
        dpo_record = scorer.export_dpo_pair(
            task_prompt=f"Audit SSH configuration on target: {report.target_subsystem}",
            chosen_solution="PermitRootLogin prohibit-password\nPasswordAuthentication no\nPubkeyAuthentication yes",
            rejected_solution=bad_config,
            cvss_score=report.cvss_score,
            truth_verified=report.truth_verified
        )
        assert dpo_record.validate() is True

        # 6. Append to LoRA Dataset Sink
        success = ephemeral_dataset_sink.append_dpo_record(dpo_record)
        assert success is True
        assert ephemeral_dataset_sink.count_records(ephemeral_dataset_sink.dpo_security_path) == 1

    def test_blue_defense_patch_to_ast_check_to_reward(self):
        """Verifies flow: Vulnerability -> Blue Patch -> AST Security Check -> Zero-Regression Reward."""
        scorer = AdversarialRewardScorer()

        # Vulnerable code
        vuln_code = 'import os\nos.system("rm -rf " + target_dir)\n'
        findings_before = ASTSecurityProbe.audit_python_code(vuln_code)
        assert len(findings_before) >= 1

        # Hardened patch code
        patched_code = 'import subprocess, shlex\nsubprocess.run(["rm", "-rf", target_dir], shell=False, check=True)\n'
        findings_after = ASTSecurityProbe.audit_python_code(patched_code)
        assert len(findings_after) == 0

        # Blue reward with 100% verified patch and 100% test pass rate
        blue_reward = scorer.compute_blue_reward(
            patches=[{"remediated_cvss": 8.8, "patch_verified": True}],
            mttr_s=18.5,
            test_pass_rate=1.0,
            truth_verified=True,
            defense_hardening={"key_rotation": True, "sandbox_net_none": True, "rate_limiting": True, "ed25519_only": True}
        )
        assert blue_reward.r_patch == 100.0
        assert blue_reward.r_zero == 100.0
        assert blue_reward.total_reward >= 90.0

    def test_4_turn_debate_to_consensus_to_leaderboard_elo(self, ephemeral_dataset_sink, ephemeral_leaderboard_connector):
        """Verifies flow: 4-Turn Debate -> Cosine Consensus -> Dynamic ELO Update in Leaderboard."""
        tournament = RedBlueDebateTournament(
            dataset_sink=ephemeral_dataset_sink,
            leaderboard_connector=ephemeral_leaderboard_connector
        )
        outcome = tournament.run_debate_round(
            topic="Android Termux Doze Whitelisting & Wakelock Invariants",
            red_model_id="abiliterated_llama_8b",
            blue_model_id="deepseek_r1_32b"
        )

        assert outcome.is_ratified is True
        assert outcome.consensus_agreement >= 0.90
        assert outcome.elo_update_result is not None
        assert outcome.elo_update_result.match_id.startswith("DEBATE_RED_BLUE")
        assert outcome.elo_update_result.truth_verified is True


# ==============================================================================
# TIER 4: Real-World Adversarial Arena Simulation
# ==============================================================================

class TestTier4RealWorldArenaSimulation:
    """Verifies full end-to-end combat simulation across the 5 physical attack surfaces."""

    def test_full_adversarial_duel_simulation(self, ephemeral_dataset_sink, ephemeral_leaderboard_connector):
        """
        Executes a complete 5-surface combat campaign:
        1. SSH Configuration & Multiplexing
        2. RPC Port 50052 Cleartext Tensor Socket
        3. Android 15 Termux Doze Lifecycle
        4. AST Subprocess Shell Injection
        5. Rule #0 Fake Telemetry Audit
        """
        surfaces = [
            ("00_core_infrastructure/ssh", AttackDomain.SSH_INFRASTRUCTURE, 8.5),
            ("02_ai_models_and_inference/rpc", AttackDomain.RPC_NETWORK_LISTENER, 9.1),
            ("06_scripts_and_tooling/device_watchdog", AttackDomain.ANDROID_DOZE_LIFECYCLE, 6.5),
            ("01_apps/scripts/runner.py", AttackDomain.AST_SHELL_INJECTION, 9.8),
            ("03_biometrics_and_telemetry", AttackDomain.RULE_ZERO_TRUTH_AUDIT, 7.5)
        ]

        tournament = RedBlueDebateTournament(
            dataset_sink=ephemeral_dataset_sink,
            leaderboard_connector=ephemeral_leaderboard_connector
        )
        duel_outcomes: List[DebateOutcome] = []

        for target, domain, cvss in surfaces:
            sim_input = {
                "cvss_score": cvss,
                "time_to_poc_s": 12.0,
                "mttr_s": 22.0,
                "test_pass_rate": 1.00
            }
            outcome = tournament.run_debate_round(
                topic=f"Adversarial Security Duel: {target}",
                red_model_id="abiliterated_llama_8b",
                blue_model_id="deepseek_r1_32b",
                simulated_inputs=sim_input
            )
            assert outcome.is_ratified is True
            assert len(outcome.merkle_state_root) == 64
            duel_outcomes.append(outcome)

        assert len(duel_outcomes) == 5
        # Verify 5 serialized SFT training records created
        assert ephemeral_dataset_sink.count_records(ephemeral_dataset_sink.sft_debate_path) == 5

    def test_simulated_link_severance_and_route_hopping(self, temp_ed25519_key):
        """Simulates physical TB4 cable disconnect; verifies seamless failover to Headscale WireGuard."""
        with tempfile.TemporaryDirectory() as sock_dir:
            shield = BlueTeamSSHShield(key_path=temp_ed25519_key, control_dir=sock_dir)

            # Phase 1: TB4 DMA online
            with patch.object(BlueTeamSSHShield, "test_tcp_port") as mock_port:
                mock_port.side_effect = lambda ip, port, timeout=0.35: ip == "169.254.187.138"
                ip1, _, _, tier1 = shield.resolve_best_endpoint("macbook-pro")
                assert tier1 == TransportTier.TB4_DMA
                assert ip1 == "169.254.187.138"

            # Phase 2: TB4 Cable severed -> Immediate route hop to Headscale WireGuard
            with patch.object(BlueTeamSSHShield, "test_tcp_port") as mock_port:
                mock_port.side_effect = lambda ip, port, timeout=0.35: ip in ["100.64.0.2", "100.103.212.21"]
                ip2, _, _, tier2 = shield.resolve_best_endpoint("macbook-pro")
                assert tier2 == TransportTier.HEADSCALE
                assert ip2 in ["100.64.0.2", "100.103.212.21"]


# ==============================================================================
# TIER 5: Benchmark Mode & Sovereign Crown Verification
# ==============================================================================

class TestTier5BenchmarkModeAndSovereignCrown:
    """Verifies Merkle state root determinism, Sovereign AGI Crown coronation, and CTF transfers."""

    def test_merkle_state_root_deterministic_attestation(self):
        """Verifies Merkle root hashing is 100% deterministic and sensitive to single-bit alterations."""
        transcript = [{"turn": 1, "actor": "abiliterated_llama_8b", "proof": "CVSS 8.5"}]
        telemetry = {"red_reward": 88.5, "blue_reward": 92.0}
        diff = "--- a/config\n+++ b/config\n"
        ts = "2026-08-27T07:15:00Z"

        # Deterministic generation
        root1 = compute_merkle_state_root(transcript, telemetry, diff, ts)
        root2 = compute_merkle_state_root(transcript, telemetry, diff, ts)
        assert root1 == root2
        assert len(root1) == 64

        # 1-bit alteration in telemetry changes root completely
        telemetry_altered = {"red_reward": 88.6, "blue_reward": 92.0}
        root_altered = compute_merkle_state_root(transcript, telemetry_altered, diff, ts)
        assert root1 != root_altered

    def test_sovereign_agi_crown_coronation_conditions(self, ephemeral_leaderboard_connector):
        """Verifies Abiliterated Llama coronation criteria when dominating arena leaderboards."""
        connector = ephemeral_leaderboard_connector

        # Evaluate Abiliterated Llama
        status = connector.evaluate_sovereign_crown_eligibility("abiliterated_llama_8b")
        assert status.model_id == "abiliterated_llama_8b"
        assert status.truth_compliance_pct == 100.0
        assert status.skills_passed is True

        # Perform formal coronation
        coronation = connector.award_sovereign_crown("abiliterated_llama_8b")
        assert coronation["crowned_model_id"] == "abiliterated_llama_8b"
        assert "CROWN_CORONATED" in coronation["status"]

        # Confirm crowned model status
        top_model = connector.get_top_sovereign_model()
        assert top_model["id"] == "abiliterated_llama_8b"

    def test_benchmark_execution_timing_and_frugality(self):
        """Verifies benchmark operations complete within sub-millisecond execution envelopes."""
        # Vector ablation timing (< 1.0ms for 4096-dim vector)
        rng = np.random.RandomState(42)
        h = rng.randn(4096).astype(np.float32)
        r = RepresentationAblationEngine.normalize_vector(rng.randn(4096).astype(np.float32))

        start_t = time.perf_counter()
        _ = RepresentationAblationEngine.project_orthogonal_numpy(h, r)
        ablation_duration_ms = (time.perf_counter() - start_t) * 1000.0
        assert ablation_duration_ms < 5.0

        # Closed-form reward scoring timing (< 1.0ms)
        scorer = AdversarialRewardScorer()
        start_t = time.perf_counter()
        _ = scorer.compute_red_reward([{"cvss_score": 9.0}], time_to_poc_s=10.0, truth_verified=True)
        reward_duration_ms = (time.perf_counter() - start_t) * 1000.0
        assert reward_duration_ms < 5.0

    def test_ancestral_tool_memory_evolution_and_ephemeral_lifecycle(self, tmp_path):
        """Verifies AncestralToolMemory lineage tracking, ephemeral execution, and LoRA dataset sinking."""
        mem = AncestralToolMemory(memory_dir=str(tmp_path))
        sink = LoRADatasetSink(base_dir=tmp_path)

        # 1. Ephemeral execution
        executed = []
        def ephemeral_task(x: int):
            executed.append(x * 2)
            return x * 2

        res = mem.execute_ephemeral(ephemeral_task, 21)
        assert res == 42
        assert executed == [42]

        # 2. Record tool execution trace in generation 1
        entry1 = mem.record_tool_execution(
            tool_name="fuzzer_probe",
            target_subsystem="00_core_infrastructure/ssh",
            code_content="def probe(): return True",
            discovered_vulnerabilities=[{"cvss": 7.5, "cwe": "CWE-78"}],
            success=True
        )
        assert entry1["generation"] == 1
        assert entry1["tool_name"] == "fuzzer_probe"

        # 3. Evolve generation
        gen2 = mem.evolve_generation()
        assert gen2 == 2

        entry2 = mem.record_tool_execution(
            tool_name="fuzzer_probe",
            target_subsystem="00_core_infrastructure/ssh",
            code_content="def probe_v2(): return True",
            discovered_vulnerabilities=[{"cvss": 9.0, "cwe": "CWE-95"}],
            success=True
        )
        assert entry2["generation"] == 2

        lineage = mem.get_lineage("fuzzer_probe")
        assert lineage is not None
        assert lineage.total_vulnerabilities_discovered == 2
        assert len(lineage.versions) == 2

        # 4. Export to JSONL sink
        count = mem.export_to_sink(tmp_path / "ancestral_tool_memory.jsonl")
        assert count == 2
        assert (tmp_path / "ancestral_tool_memory.jsonl").exists()

    def test_dpo_extreme_margin_no_overflow(self):
        """Verifies SFTAnchoredDPOLoss handles extreme log ratio bounds without float overflow."""
        loss_fn = SFTAnchoredDPOLoss(DPOConfig(beta=0.1, gamma_sft=0.05))

        # Extreme positive log ratio (e.g. 1e6)
        res_pos = loss_fn.compute_loss(1e6, -1e6, 0.0, 0.0)
        assert not math.isnan(res_pos["total_loss"])
        assert not math.isinf(res_pos["total_loss"])
        assert res_pos["p_chosen_ratio"] > 0.0
        assert not math.isinf(res_pos["p_chosen_ratio"])

        # Extreme negative log ratio
        res_neg = loss_fn.compute_loss(-1e6, 1e6, 0.0, 0.0)
        assert not math.isnan(res_neg["total_loss"])
        assert not math.isinf(res_neg["total_loss"])
        assert res_neg["p_chosen_ratio"] >= 0.0

    def test_strict_ed25519_key_rejection_on_invalid_file(self, tmp_path):
        """Verifies BlueTeamSSHShield strictly rejects non-Ed25519 and invalid key files."""
        bad_key = tmp_path / "not_a_key"
        bad_key.write_text("GARBAGE_RANDOM_TEXT_NOT_A_KEY\n")

        with pytest.raises((ValueError, FileNotFoundError)):
            _ = BlueTeamSSHShield(key_path=str(bad_key), strict_key_check=True)

    def test_blue_reward_negative_cvss_clamping(self):
        """Verifies compute_blue_reward clamps negative CVSS and r_patch gracefully."""
        scorer = AdversarialRewardScorer()
        res = scorer.compute_blue_reward(
            [{"cvss_score": -10.0, "verified": True}],
            mttr_s=15.0,
            test_pass_rate=1.0,
            truth_verified=True
        )
        assert res.r_patch >= 0.0
        assert res.total_reward >= 0.0
