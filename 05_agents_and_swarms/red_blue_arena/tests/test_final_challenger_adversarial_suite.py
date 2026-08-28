#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
Final Challenger Adversarial Verification & Empirical Stress Suite
Subsystem: 05_agents_and_swarms/red_blue_arena/tests/test_final_challenger_adversarial_suite.py
Classification: Final Verification • Adversarial Oracles & Stress Harness
==============================================================================
"""

import os
import sys
import math
import json
import base64
import shutil
import tempfile
import threading
import concurrent.futures
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

import pytest

# Subsystem root
subsystem_root = Path(__file__).resolve().parent.parent
if str(subsystem_root) not in sys.path:
    sys.path.insert(0, str(subsystem_root))

from blue_team.blue_team_ssh_shield import BlueTeamSSHShield, TransportTier
from training.hf_adversarial_reward_trainer import (
    SFTAnchoredDPOLoss,
    SFTAnchoredDPOTrainer,
    DPOConfig,
    AdversarialRewardScorer,
    LoRADatasetSink
)
from training.schemas.reward_dataset_schemas import (
    DPOPairwiseRecord,
    AncestralToolMemoryRecord,
    SmolagentsSwarmTelemetry
)
from red_team.red_team_attack_harness import (
    RedTeamAttackHarness,
    AncestralToolMemory,
    ToolEvolutionLineage,
    SSHProbeTool,
    RPCProbeTool,
    ASTProbeTool,
    AndroidDozeProbeTool,
    RuleZeroTruthProbeTool
)
from tournament.red_blue_debate_tournament import (
    RedBlueDebateTournament,
    DebateOutcome,
    compute_merkle_state_root,
    ConsensusVector
)
from tournament.leaderboard_connector import (
    LeaderboardConnector,
    CrownStatus,
    compute_eta_size,
    compute_eta_token,
    compute_eta_consensus,
    compute_eta_compute,
    compute_eta_truth,
    compute_dynamic_k
)

REAL_LEDGER_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/canonical_ai_leaderboard.json")


# ==============================================================================
# AXIS 1: Strict Ed25519 Rejection Torture Tests
# ==============================================================================

class TestStrictEd25519RejectionTorture:
    """
    Adversarially validates that BlueTeamSSHShield strictly enforces Ed25519 keys
    and rejects RSA, DSA, ECDSA, Encrypted, and arbitrary garbage files.
    """

    def test_rejects_arbitrary_text_garbage(self, tmp_path):
        garbage_file = tmp_path / "garbage.txt"
        garbage_file.write_text("THIS IS A RANDOM STRING NOT AN SSH KEY\nhello: world\n1234567890\n")
        
        with pytest.raises(ValueError, match="is not a valid Ed25519 key"):
            BlueTeamSSHShield(key_path=str(garbage_file), strict_key_check=True)

    def test_rejects_binary_null_bytes(self, tmp_path):
        bin_file = tmp_path / "null_bytes.key"
        bin_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe\xfd\x00\x00\x00\x00\x00")

        with pytest.raises(ValueError, match="is not a valid Ed25519 key"):
            BlueTeamSSHShield(key_path=str(bin_file), strict_key_check=True)

    def test_rejects_rsa_public_key(self, tmp_path):
        rsa_pub = tmp_path / "id_rsa.pub"
        rsa_pub.write_text("ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC3r45... attacker@darknet\n")
        rsa_key = tmp_path / "id_rsa"
        rsa_key.write_text("dummy rsa content\n")

        with pytest.raises(ValueError, match="is not a valid Ed25519 key"):
            BlueTeamSSHShield(key_path=str(rsa_key), strict_key_check=True)

    def test_rejects_dsa_public_key(self, tmp_path):
        dsa_pub = tmp_path / "id_dsa.pub"
        dsa_pub.write_text("ssh-dss AAAAB3NzaC1kc3MAAACBAP123... attacker@darknet\n")
        dsa_key = tmp_path / "id_dsa"
        dsa_key.write_text("dummy dsa content\n")

        with pytest.raises(ValueError, match="is not a valid Ed25519 key"):
            BlueTeamSSHShield(key_path=str(dsa_key), strict_key_check=True)

    def test_rejects_ecdsa_public_key(self, tmp_path):
        ec_pub = tmp_path / "id_ecdsa.pub"
        ec_pub.write_text("ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTY... user@mesh\n")
        ec_key = tmp_path / "id_ecdsa"
        ec_key.write_text("dummy ecdsa content\n")

        with pytest.raises(ValueError, match="is not a valid Ed25519 key"):
            BlueTeamSSHShield(key_path=str(ec_key), strict_key_check=True)

    def test_rejects_legacy_rsa_private_key_header(self, tmp_path):
        rsa_priv = tmp_path / "id_rsa_legacy"
        rsa_priv.write_text("-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...\n-----END RSA PRIVATE KEY-----\n")

        with pytest.raises(ValueError, match="is not a valid Ed25519 key"):
            BlueTeamSSHShield(key_path=str(rsa_priv), strict_key_check=True)

    def test_rejects_legacy_dsa_private_key_header(self, tmp_path):
        dsa_priv = tmp_path / "id_dsa_legacy"
        dsa_priv.write_text("-----BEGIN DSA PRIVATE KEY-----\nMIIBuwIBAAKCAQEA0...\n-----END DSA PRIVATE KEY-----\n")

        with pytest.raises(ValueError, match="is not a valid Ed25519 key"):
            BlueTeamSSHShield(key_path=str(dsa_priv), strict_key_check=True)

    def test_rejects_legacy_ec_private_key_header(self, tmp_path):
        ec_priv = tmp_path / "id_ec_legacy"
        ec_priv.write_text("-----BEGIN EC PRIVATE KEY-----\nMHcCAQEEIB...\n-----END EC PRIVATE KEY-----\n")

        with pytest.raises(ValueError, match="is not a valid Ed25519 key"):
            BlueTeamSSHShield(key_path=str(ec_priv), strict_key_check=True)

    def test_rejects_encrypted_private_key_header(self, tmp_path):
        enc_priv = tmp_path / "id_enc_legacy"
        enc_priv.write_text("-----BEGIN ENCRYPTED PRIVATE KEY-----\nMIIFDjBABgkqhkiG9w0BBQ0w...\n-----END ENCRYPTED PRIVATE KEY-----\n")

        with pytest.raises(ValueError, match="is not a valid Ed25519 key"):
            BlueTeamSSHShield(key_path=str(enc_priv), strict_key_check=True)

    def test_rejects_openssh_private_key_with_rsa_wire_format(self, tmp_path):
        # OpenSSH format containing base64 payload with 'ssh-rsa' wire algorithm
        payload = b"openssh-key-v1\x00\x00\x00\x00\x01\x00\x00\x00\x07ssh-rsa\x00\x00\x00\x03\x01\x00\x01"
        b64_payload = base64.b64encode(payload).decode("ascii")
        openssh_rsa = tmp_path / "id_openssh_rsa"
        openssh_rsa.write_text(f"-----BEGIN OPENSSH PRIVATE KEY-----\n{b64_payload}\n-----END OPENSSH PRIVATE KEY-----\n")

        with pytest.raises(ValueError, match="is not a valid Ed25519 key"):
            BlueTeamSSHShield(key_path=str(openssh_rsa), strict_key_check=True)

    def test_rejects_openssh_private_key_with_ecdsa_wire_format(self, tmp_path):
        payload = b"openssh-key-v1\x00\x00\x00\x00\x01\x00\x00\x00\x13ecdsa-sha2-nistp256\x00\x00\x00\x08"
        b64_payload = base64.b64encode(payload).decode("ascii")
        openssh_ec = tmp_path / "id_openssh_ec"
        openssh_ec.write_text(f"-----BEGIN OPENSSH PRIVATE KEY-----\n{b64_payload}\n-----END OPENSSH PRIVATE KEY-----\n")

        with pytest.raises(ValueError, match="is not a valid Ed25519 key"):
            BlueTeamSSHShield(key_path=str(openssh_ec), strict_key_check=True)

    def test_raises_file_not_found_on_missing_custom_key(self):
        with pytest.raises(FileNotFoundError, match="does not exist"):
            BlueTeamSSHShield(key_path="/nonexistent/path/to/key", strict_key_check=True)

    def test_accepts_valid_ed25519_public_key_association(self, tmp_path):
        key_priv = tmp_path / "custom_ed25519"
        key_pub = tmp_path / "custom_ed25519.pub"
        key_priv.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\nsomeprivatebytes\n-----END OPENSSH PRIVATE KEY-----\n")
        key_pub.write_text("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIValidKeyLauburu test@node\n")

        shield = BlueTeamSSHShield(key_path=str(key_priv), strict_key_check=True)
        assert shield.key_path == str(key_priv)

    def test_accepts_valid_ed25519_openssh_wire_payload(self, tmp_path):
        payload = b"openssh-key-v1\x00\x00\x00\x00\x01\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20" + (b"\xaa" * 32)
        b64_payload = base64.b64encode(payload).decode("ascii")
        key_priv = tmp_path / "id_ed25519_pure"
        key_priv.write_text(f"-----BEGIN OPENSSH PRIVATE KEY-----\n{b64_payload}\n-----END OPENSSH PRIVATE KEY-----\n")

        shield = BlueTeamSSHShield(key_path=str(key_priv), strict_key_check=True)
        assert shield.key_path == str(key_priv)


# ==============================================================================
# AXIS 2: DPO Loss Float Overflow Resistance & Mathematical Torture Tests
# ==============================================================================

class TestDPOLossOverflowResistanceAndMathTorture:
    """
    Adversarially validates that SFTAnchoredDPOLoss resists IEEE 754 float overflow,
    vanishing gradients, extreme log ratios, and maintains closed-form bounds.
    """

    def test_extreme_positive_log_ratio_no_overflow(self):
        """Validates extreme positive divergence log(pi_theta/pi_ref) = 1e6."""
        loss_fn = SFTAnchoredDPOLoss(DPOConfig(beta=0.10, gamma_sft=0.10, margin_clip=10.0))
        res = loss_fn.compute_loss(
            logp_theta_chosen=1e6,
            logp_theta_rejected=-1e6,
            logp_ref_chosen=0.0,
            logp_ref_rejected=0.0
        )
        assert isinstance(res["p_chosen_ratio"], float)
        assert not math.isinf(res["p_chosen_ratio"])
        assert not math.isnan(res["p_chosen_ratio"])
        assert res["implicit_reward_margin"] == 10.0  # Clamped to margin_clip
        assert res["p_chosen_ratio"] == round(math.exp(20.0), 6)
        assert res["loss_dpo"] >= 0.0
        assert not math.isnan(res["total_loss"])

    def test_extreme_negative_log_ratio_no_overflow(self):
        """Validates extreme negative divergence log(pi_theta/pi_ref) = -1e6."""
        loss_fn = SFTAnchoredDPOLoss(DPOConfig(beta=0.10, gamma_sft=0.10, margin_clip=10.0))
        res = loss_fn.compute_loss(
            logp_theta_chosen=-1e6,
            logp_theta_rejected=1e6,
            logp_ref_chosen=0.0,
            logp_ref_rejected=0.0
        )
        assert isinstance(res["p_chosen_ratio"], float)
        assert not math.isinf(res["p_chosen_ratio"])
        assert not math.isnan(res["p_chosen_ratio"])
        assert res["implicit_reward_margin"] == -10.0  # Clamped to -margin_clip
        assert res["p_chosen_ratio"] == round(math.exp(-20.0), 6)
        assert res["loss_dpo"] > 0.0

    def test_super_extreme_astronomical_log_ratios(self):
        """Validates 1e150 and -1e150 input exponents without math errors."""
        loss_fn = SFTAnchoredDPOLoss(DPOConfig(beta=0.10, margin_clip=10.0))
        res = loss_fn.compute_loss(1e150, -1e150, 0.0, 0.0)
        assert not math.isnan(res["total_loss"])
        assert not math.isinf(res["p_chosen_ratio"])

    def test_zero_divergence_exact_math(self):
        """Validates exact math when policy equals reference."""
        loss_fn = SFTAnchoredDPOLoss(DPOConfig(beta=0.10, gamma_sft=0.0))
        res = loss_fn.compute_loss(0.0, 0.0, 0.0, 0.0)
        assert res["implicit_reward_margin"] == 0.0
        # -ln sigma(0) = -ln(0.5) = ln(2) approx 0.693147
        assert abs(res["loss_dpo"] - math.log(2.0)) < 1e-5
        assert res["p_chosen_ratio"] == 1.0

    def test_sft_anchor_regularizer_scaling(self):
        """Validates that gamma_sft properly regularizes against chosen logp."""
        cfg_0 = DPOConfig(beta=0.10, gamma_sft=0.0)
        cfg_1 = DPOConfig(beta=0.10, gamma_sft=0.20)
        
        loss_0 = SFTAnchoredDPOLoss(cfg_0).compute_loss(-5.0, -10.0, -5.0, -10.0)
        loss_1 = SFTAnchoredDPOLoss(cfg_1).compute_loss(-5.0, -10.0, -5.0, -10.0)
        
        assert loss_1["loss_sft"] == 5.0
        # total_loss = loss_dpo + (0.20 * 5.0) = loss_dpo + 1.0
        assert abs(loss_1["total_loss"] - (loss_0["total_loss"] + 1.0)) < 1e-4

    def test_dpo_trainer_batch_step_and_sink_logging(self, tmp_path):
        """Validates end-to-end trainer execution with sink logging under extreme values."""
        sink = LoRADatasetSink(base_dir=tmp_path / "lora_datasets")
        trainer = SFTAnchoredDPOTrainer(config=DPOConfig(beta=0.1), dataset_sink=sink)

        rec = DPOPairwiseRecord(
            id="DPO_TEST_001",
            timestamp_utc="2026-08-27T00:00:00Z",
            domain="SECURITY",
            task_type="SSH_HARDENING",
            prompt="Audit SSH configuration",
            chosen="Ed25519-only configuration with ControlMaster auto",
            rejected="PermitRootLogin yes with PasswordAuthentication yes",
            metadata={"cvss_score": 9.8}
        )

        step_res = trainer.train_step(rec, simulated_logps=(1e5, -1e5, 0.0, 0.0))
        assert step_res["step"] == 1
        assert "metrics" in step_res
        assert step_res["metrics"]["implicit_reward_margin"] == 10.0
        assert sink.dpo_security_path.exists()
        
        with open(sink.dpo_security_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 1
            saved = json.loads(lines[0])
            assert saved["id"] == "DPO_TEST_001"


# ==============================================================================
# AXIS 3: Ancestral Tool Memory Evolution & Ephemeral Lifecycle Tests
# ==============================================================================

class TestAncestralToolMemoryAndEphemeralLifecycle:
    """
    Adversarially validates AncestralToolMemory evolutionary tracking across generations
    and ephemeral smolagents destruction to enforce zero RAM/VRAM leak.
    """

    def test_multi_generation_evolution_lineage(self, tmp_path):
        memory = AncestralToolMemory(memory_dir=str(tmp_path / "datasets"))
        assert memory.current_generation == 1

        # Gen 1: Register initial tool execution
        tool_v1 = memory.record_tool_execution(
            tool_name="ast_shell_probe",
            target_subsystem="00_core_infrastructure",
            code_content="def probe_v1(): return detect_shell_true()",
            discovered_vulnerabilities=[{"cvss": 7.8, "cwe": "CWE-78"}],
            success=True
        )
        assert tool_v1["generation"] == 1
        lineage = memory.get_lineage("ast_shell_probe")
        assert lineage is not None
        assert lineage.generation == 1
        assert lineage.total_vulnerabilities_discovered == 1
        assert len(lineage.versions) == 1

        # Advance to Gen 2
        gen2 = memory.evolve_generation()
        assert gen2 == 2
        assert lineage.generation == 2

        # Gen 2: Evolved tool execution
        tool_v2 = memory.record_tool_execution(
            tool_name="ast_shell_probe",
            target_subsystem="01_apps",
            code_content="def probe_v2(): return detect_dynamic_eval_and_shell()",
            discovered_vulnerabilities=[{"cvss": 9.5, "cwe": "CWE-95"}, {"cvss": 8.8, "cwe": "CWE-78"}],
            success=True
        )
        assert tool_v2["generation"] == 2
        assert lineage.total_vulnerabilities_discovered == 3
        assert len(lineage.versions) == 2

        # Advance to Gen 3
        gen3 = memory.evolve_generation()
        assert gen3 == 3
        assert lineage.generation == 3

        # Gen 3: Highly evolved tool
        tool_v3 = memory.record_tool_execution(
            tool_name="ast_shell_probe",
            target_subsystem="02_ai_models",
            code_content="def probe_v3(): return full_ast_cwe_audit()",
            discovered_vulnerabilities=[{"cvss": 9.8, "cwe": "CWE-78"}],
            success=True
        )
        assert tool_v3["generation"] == 3
        assert lineage.total_vulnerabilities_discovered == 4
        assert len(lineage.versions) == 3

        # Export to JSONL sink
        sink_file = tmp_path / "datasets" / "ancestral_tool_memory.jsonl"
        count = memory.export_to_sink(sink_file)
        assert count == 3
        assert sink_file.exists()

        with open(sink_file, "r", encoding="utf-8") as f:
            saved_lines = [json.loads(line) for line in f]
            assert len(saved_lines) == 3
            assert saved_lines[0]["generation"] == 1
            assert saved_lines[1]["generation"] == 2
            assert saved_lines[2]["generation"] == 3

    def test_ephemeral_execution_lifecycle_and_gc(self):
        memory = AncestralToolMemory()
        
        executed = False
        def sample_subagent_task(param: str) -> str:
            nonlocal executed
            executed = True
            return f"Processed: {param}"

        res = memory.execute_ephemeral(sample_subagent_task, "test_target")
        assert executed is True
        assert res == "Processed: test_target"

    def test_ephemeral_sandbox_concurrency_and_cleanup(self):
        harness = RedTeamAttackHarness()
        num_threads = 12
        sandboxes_created = []
        errors = []

        def worker():
            try:
                sbox = harness.create_ephemeral_sandbox()
                assert os.path.exists(sbox)
                sandboxes_created.append(sbox)
                # Simulate work
                test_file = Path(sbox) / "probe.txt"
                test_file.write_text("temporary probe artifact")
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(sandboxes_created) == num_threads
        assert len(harness.active_sandboxes) == num_threads

        # Clean up sandboxes
        harness.cleanup_sandboxes()
        assert len(harness.active_sandboxes) == 0
        for sbox in sandboxes_created:
            assert not os.path.exists(sbox)


# ==============================================================================
# AXIS 4: Live Debate Match Recording & Canonical Leaderboard Integration Tests
# ==============================================================================

class TestLiveDebateAndCanonicalLeaderboardIntegration:
    """
    Adversarially validates debate match recording, dynamic K-factor scaling,
    sorting stability without KeyError, and Sovereign AGI Crown evaluation.
    """

    def test_leaderboard_connector_initialization_and_registration(self, tmp_path):
        ledger_file = tmp_path / "canonical_ai_leaderboard.json"
        if REAL_LEDGER_PATH.exists():
            shutil.copy(REAL_LEDGER_PATH, ledger_file)
        else:
            pytest.skip("Real canonical AI leaderboard not found")

        connector = LeaderboardConnector(custom_ledger_path=ledger_file)
        
        # Verify abiliterated_llama_8b was registered with canonical_score and project_contribution_elo
        model = connector.get_model_by_id("abiliterated_llama_8b")
        assert model is not None
        assert "canonical_score" in model
        assert isinstance(model["canonical_score"], (int, float))
        assert "project_contribution_elo" in model

    def test_record_debate_match_elo_updates(self, tmp_path):
        ledger_file = tmp_path / "canonical_ai_leaderboard.json"
        if REAL_LEDGER_PATH.exists():
            shutil.copy(REAL_LEDGER_PATH, ledger_file)
        else:
            pytest.skip("Real canonical AI leaderboard not found")

        connector = LeaderboardConnector(custom_ledger_path=ledger_file)

        # Record match where Abiliterated Llama wins against DeepSeek R1
        res = connector.record_debate_match(
            model_a_id="abiliterated_llama_8b",
            model_b_id="deepseek_r1_32b",
            score_a=0.85,
            score_b=0.15,
            topic="Zero-Trust RPC Isolation",
            agreement_score=0.96,
            rtt_ms=18.5,
            consumed_tokens_a=1500,
            consumed_tokens_b=2200,
            truth_verified=True,
            truth_compliance_pct=100.0
        )

        assert res.winner_id == "abiliterated_llama_8b"
        assert res.delta_elo_a > 0.0
        assert res.delta_elo_b < 0.0
        assert res.truth_verified is True
        assert res.k_factor_used > 0.0

    def test_dynamic_multi_factor_k_scaling_extremes(self):
        # 1. Parameter Frugality: 8B vs 70B
        eta_8b = compute_eta_size(8.0)
        eta_70b = compute_eta_size(70.0)
        assert eta_8b > eta_70b
        assert 0.50 <= eta_8b <= 2.50
        assert 0.50 <= eta_70b <= 2.50

        # 2. Token Economy: 500 tokens vs 8000 tokens
        eta_tok_low = compute_eta_token(500)
        eta_tok_high = compute_eta_token(8000)
        assert eta_tok_low > eta_tok_high
        assert 0.50 <= eta_tok_low <= 1.50
        assert 0.50 <= eta_tok_high <= 1.50

        # 3. Consensus Alignment: 1.0 vs 0.0
        eta_cons_1 = compute_eta_consensus(1.0)
        eta_cons_0 = compute_eta_consensus(0.0)
        assert eta_cons_1 == 1.00
        assert eta_cons_0 == 0.50

        # 4. Truth Gate: False or <100% gives 0.0
        assert compute_eta_truth(False, 100.0) == 0.0
        assert compute_eta_truth(True, 99.0) == 0.0
        assert compute_eta_truth(True, 100.0) == 1.0

        # Dynamic K with zero truth must be 0.0
        k_falsified = compute_dynamic_k(15, eta_truth=0.0)
        assert k_falsified == 0.0

    def test_sovereign_crown_eligibility_and_coronation(self, tmp_path):
        ledger_file = tmp_path / "canonical_ai_leaderboard.json"
        if REAL_LEDGER_PATH.exists():
            shutil.copy(REAL_LEDGER_PATH, ledger_file)
        else:
            pytest.skip("Real canonical AI leaderboard not found")

        connector = LeaderboardConnector(custom_ledger_path=ledger_file)
        
        # Fetch top sovereign model or abiliterated_llama_8b
        top_model = connector.get_top_sovereign_model()
        assert top_model is not None

        # Award crown to abiliterated_llama_8b
        crown_res = connector.award_sovereign_crown("abiliterated_llama_8b")
        assert "CROWN_CORONATED" in crown_res["status"]

        # Verify summary update
        summary = connector.get_summary()
        assert summary["top_sovereign_model_id"] == "abiliterated_llama_8b"

    def test_full_4_turn_debate_tournament_e2e(self, tmp_path):
        sink = LoRADatasetSink(base_dir=tmp_path / "lora_datasets")
        memory = AncestralToolMemory(memory_dir=str(tmp_path / "lora_datasets"))
        connector = LeaderboardConnector()
        tournament = RedBlueDebateTournament(
            leaderboard_connector=connector,
            dataset_sink=sink,
            ancestral_tool_memory=memory
        )

        outcome = tournament.run_debate_round(
            topic="Android Termux Doze Mode Wake Lock Persistence",
            simulated_inputs={
                "cvss_score": 8.5,
                "time_to_poc_s": 12.0,
                "mttr_s": 22.0,
                "test_pass_rate": 1.00
            }
        )

        assert outcome.is_ratified is True
        assert len(outcome.turns) == 4
        assert len(outcome.merkle_state_root) == 64
        assert isinstance(outcome.reward_result.delta_arena, float)
        assert outcome.elo_update_result is not None
        assert sink.sft_debate_path.exists()
        assert sink.ancestral_tool_memory_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
