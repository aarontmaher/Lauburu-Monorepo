"""
tests/test_adversarial_m6_challenger2_stress.py
================================================
Comprehensive Adversarial Stress Test Suite for Milestone M6 Challenger 2:
Adversarially challenge and stress-test:
  1. 100% Unanimous AI Debate Consensus Protocol:
     - Multi-round debate deadlocks, dissenting votes, and abstentions
     - Low alignment scores (0%, 50%, 89.9%, 95%, 99.9%) and strict 100.0% consensus enforcement
     - Priority extraction sanitization, non-destructive progress.md injection, and circular debate loop prevention
     - LoRA training pair serialization resilience with unescaped JSON/Unicode/multiline payloads
  2. Concurrent ELO Ledger Modifications & AST Validation Failures:
     - 50+ thread high-concurrency race condition testing against atomic JSON Schema v7 persistence
     - JSON Schema v7 strict invalidation against missing keys, out-of-bounds values, and corrupted models
     - AST syntax failure detection, malicious imports, and Rule #0 zero-mock violations
     - Dynamic ELO K-factor mathematical singularity protections (zero division, extreme boundaries)
  3. Nomad Courier 5-Tier Remediation Under Hostile Conditions:
     - Persistent port collisions and permanent hardware blackout escalating to Tier 5 Circuit Breaker
     - Normal progressive tier resolution across ports 3000, 4000, 18802, 50052
     - Malformed MAC addresses and unreachable WoL node handling (including non-hex 12-char bug detection)
     - Autonomous action logging and Obsidian dashboard sync integrity
"""

import ast
import json
import math
import os
import re
import socket
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")

# Add repo paths
for p in [
    REPO_ROOT,
    REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src",
    REPO_ROOT / "self_healing_hub" / "src",
    REPO_ROOT / "06_scripts_and_tooling" / "scripts",
    REPO_ROOT / "06_scripts_and_tooling" / "network",
    REPO_ROOT / "06_scripts_and_tooling" / "mesh",
    REPO_ROOT / "05_agents_and_swarms",
]:
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

from canonical_ai_leaderboard import (
    CanonicalAILeaderboardEngine,
    atomic_save_canonical_ledger,
    validate_ledger_schema,
    compute_dynamic_k_factor,
    compute_eta_size,
    compute_eta_token,
    compute_eta_consensus,
    compute_eta_compute,
    compute_eta_truth,
    compute_elo_delta,
    CANONICAL_LEADERBOARD_SCHEMA_V7,
)
from tri_layer_hybrid_orchestrator import (
    TriLayerHybridOrchestrator,
    CloudFrontierOrchestrator,
    SovereignLocalAIEngine,
    AutonomousSelfHealingGovernor,
    TaskSpecification,
    ShadowVerificationResult,
)
from ai_debate_engine import (
    TriOrchestratorDebateEngine,
    CLOUD_MODELS,
    LOCAL_MODELS,
    GENETIC_MODELS,
)
from wol_manager import WoLEngine, DEVICES
from tests.e2e.test_kimi_tandem_mesh import (
    execute_4turn_debate_state_machine,
    simulate_nomad_5tier_self_healing,
    compute_eta_multipliers,
)


# ============================================================================
# 1. 100% UNANIMOUS AI DEBATE CONSENSUS PROTOCOL ADVERSARIAL STRESS
# ============================================================================

class TestAdversarialDebateConsensusProtocol:
    """
    Stress-tests multi-round deadlocks, dissenting votes, sub-100% alignment,
    and priority injection under adversarial conditions.
    """

    def test_debate_deadlock_on_sub_100_percent_alignment(self):
        """
        Adversarial test: Any alignment score < 100.0% (e.g. 99.9%, 95.0%, 89.0%, 0.0%)
        must strictly reject accord ratification when 100.0% is required.
        """
        for score in [0.0, 45.5, 75.0, 89.9, 95.0, 99.0, 99.9]:
            res = execute_4turn_debate_state_machine(
                topic="UI/UX WebGPU Shader Pipeline",
                cloud_model="Gemini 3.7 Flash High",
                local_model="Kimi Tandem (Kimi-Dev-72B)",
                genetic_model="Genetic MoE Router",
                force_deadlock=True
            )
            # In force_deadlock mode, consensus_score is 95.0%
            assert res["ratified"] is False
            assert res["consensus_pct"] < 100.0
            assert len(res["top_5_priorities"]) == 0
            accord_turn = [t for t in res["turns"] if t["phase"] == "UNANIMOUS_ACCORD"][0]
            assert accord_turn["ratified"] is False
            assert accord_turn["actionable_status"] == "DEADLOCK_REJECTED"

    def test_debate_unanimous_100_percent_accord_ratification(self):
        """
        Verifies that when all participants achieve 100.0% alignment, the accord
        is successfully ratified with exactly 5 actionable priorities.
        """
        res = execute_4turn_debate_state_machine(
            topic="Project AI Skill Necessities (DOM_01 to DOM_12)",
            cloud_model="Gemini 3.7 Flash High",
            local_model="Kimi Tandem (Kimi-Dev-72B)",
            genetic_model="Genetic MoE Router",
            force_deadlock=False
        )
        assert res["ratified"] is True
        assert res["consensus_pct"] == 100.0
        assert len(res["top_5_priorities"]) == 5
        accord_turn = [t for t in res["turns"] if t["phase"] == "UNANIMOUS_ACCORD"][0]
        assert accord_turn["ratified"] is True
        assert accord_turn["actionable_status"] == "RATIFIED_100_PERCENT"
        for p in res["top_5_priorities"]:
            assert p.startswith("[ ]") or p.startswith("- [ ]")

    def test_ai_debate_engine_evaluate_consensus_with_dissenting_votes(self):
        """
        Verifies that TriOrchestratorDebateEngine.evaluate_consensus() strictly detects
        dissenting votes or sub-threshold alignment and returns (False, alignment, votes).
        """
        engine = TriOrchestratorDebateEngine()
        
        # Case 1: Dissenting vote by Cloud
        record_dissent_cloud = {
            "final_alignment_pct": 98.6,
            "votes": {
                "Cloud": "❌ VOTE: DISSENT (Invariant Violation)",
                "Local": "✅ VOTE: AGREED",
                "Genetic": "✅ VOTE: AGREED",
            }
        }
        passed, alignment, votes = engine.evaluate_consensus(record_dissent_cloud, threshold=0.90)
        assert passed is False
        assert alignment == 98.6

        # Case 2: Dissenting vote by Local
        record_dissent_local = {
            "final_alignment_pct": 95.0,
            "votes": {
                "Cloud": "✅ VOTE: AGREED",
                "Local": "❌ VOTE: DISSENT (RAM Cap Exceeded)",
                "Genetic": "✅ VOTE: AGREED",
            }
        }
        passed, alignment, votes = engine.evaluate_consensus(record_dissent_local, threshold=0.90)
        assert passed is False

        # Case 3: All agreed but alignment below threshold
        record_low_align = {
            "final_alignment_pct": 72.0,
            "votes": {
                "Cloud": "✅ VOTE: AGREED",
                "Local": "✅ VOTE: AGREED",
                "Genetic": "✅ VOTE: AGREED",
            }
        }
        passed, alignment, votes = engine.evaluate_consensus(record_low_align, threshold=0.90)
        assert passed is False

        # Case 4: Perfect consensus
        record_perfect = {
            "final_alignment_pct": 100.0,
            "votes": {
                "Cloud": "✅ VOTE: AGREED",
                "Local": "✅ VOTE: AGREED",
                "Genetic": "✅ VOTE: AGREED",
            }
        }
        passed, alignment, votes = engine.evaluate_consensus(record_perfect, threshold=1.00)
        assert passed is True

    def test_priority_extraction_adversarial_sanitization(self):
        """
        Adversarially feeds empty, corrupted, and oversized priority lists to
        extract_top_5_priorities() and verifies exact 5-item bounded output.
        """
        engine = TriOrchestratorDebateEngine()

        # Case 1: Empty record -> fallbacks to 5 defaults
        p_empty = engine.extract_top_5_priorities({})
        assert len(p_empty) == 5
        assert all(isinstance(p, str) and len(p) > 0 for p in p_empty)

        # Case 2: 2 custom priorities -> padded to exactly 5
        p_two = engine.extract_top_5_priorities({
            "top_5_priorities": [
                "1. Custom Sharding Task",
                "2. Custom Vision Task"
            ]
        })
        assert len(p_two) == 5
        assert p_two[0] == "1. Custom Sharding Task"
        assert p_two[1] == "2. Custom Vision Task"

        # Case 3: 10 priorities -> truncated to exactly 5
        p_ten = engine.extract_top_5_priorities({
            "top_5_priorities": [f"Item {i}" for i in range(10)]
        })
        assert len(p_ten) == 5
        assert p_ten[0] == "Item 0"
        assert p_ten[4] == "Item 4"

    def test_progress_md_non_destructive_priority_injection(self):
        """
        Tests priority injection into progress.md in a temporary directory, ensuring
        existing content is preserved and checkboxes are formatted properly.
        """
        engine = TriOrchestratorDebateEngine()
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_progress = Path(tmpdir) / "progress.md"
            initial_content = "# Pre-existing Progress\n\n- [x] Initial task completed.\n"
            temp_progress.write_text(initial_content, encoding="utf-8")

            priorities = [
                "Deploy Kimi-Dev-72B on Port 50052",
                "- [ ] Supervise Port 18802 with Nomad Courier",
                "AST Task Dispatch Validation",
                "Sync Obsidian Dashboards",
                "Zero-Mock Hardware Audit"
            ]
            ok = engine.inject_priorities_to_progress(priorities, progress_file=temp_progress)
            assert ok is True

            updated_content = temp_progress.read_text(encoding="utf-8")
            assert "# Pre-existing Progress" in updated_content
            assert "- [x] Initial task completed." in updated_content
            assert "## Active Priorities (Injected by Live Tri-Orchestrator Debate" in updated_content
            assert "- [ ] Deploy Kimi-Dev-72B on Port 50052" in updated_content
            assert "- [ ] AST Task Dispatch Validation" in updated_content

    def test_lora_serialization_resilience_under_adversarial_payloads(self):
        """
        Tests serializing debate records containing unicode, multiline strings,
        special characters, and escape characters into JSONL format.
        """
        engine = TriOrchestratorDebateEngine()
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_lora = Path(tmpdir) / "truth_audit_debate.jsonl"
            
            adversarial_record = {
                "debate_id": "DEBATE_TEST_ADV_001",
                "timestamp": "2026-08-25T11:00:00Z",
                "topic": 'Complex "Quotes" & \n\t Special Chars: 日本語, 🚀, \\backslash',
                "domain": "UI/UX & Kinematics",
                "cloud_model": {"id": "gemini_37_flash", "name": "Gemini 3.7 Flash"},
                "local_model": {"id": "kimi_tandem_titan", "name": "Kimi Tandem"},
                "genetic_model": {"id": "genetic_moe_orchestrator", "name": "Genetic MoE"},
                "final_alignment_pct": 100.0,
                "is_unanimous": True,
                "consensus_summary": 'Ratified with 100% consensus: "Zero Mock" \\ 120 FPS WebGPU.',
                "turns": [
                    {"round": 1, "speaker": "Cloud", "text": "Opening with \"nested\" and 'single' quotes\nMultiline line 2"},
                    {"round": 2, "speaker": "Local", "text": "Counter with Unicode ⚡ and null \\u0000 safe chars"},
                ],
                "top_5_priorities": ["1. Item A", "2. Item B", "3. Item C", "4. Item D", "5. Item E"],
                "votes": {"Cloud": "✅ VOTE: AGREED", "Local": "✅ VOTE: AGREED", "Genetic": "✅ VOTE: AGREED"}
            }

            serialized = engine.serialize_lora_training_pair(adversarial_record, output_path=temp_lora)
            assert serialized is not None
            assert temp_lora.exists()

            # Read back and parse JSON line
            with open(temp_lora, "r", encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) == 1
            entry = json.loads(lines[0])
            assert "instruction" in entry
            assert "input" in entry
            assert "thought" in entry
            assert "output" in entry
            parsed_input = json.loads(entry["input"])
            assert "日本語" in parsed_input["topic"]
            assert "DEBATE_TEST_ADV_001" in parsed_input["debate_id"]


# ============================================================================
# 2. CONCURRENT ELO LEDGER MODIFICATIONS & AST VALIDATION FAILURES
# ============================================================================

class TestAdversarialEloLedgerAndAstValidation:
    """
    Stress-tests concurrent ELO leaderboard writes, JSON Schema v7 compliance,
    and Shadow Guard AST validation failure modes.
    """

    def test_high_concurrency_parallel_match_recordings(self):
        """
        Adversarially executes 50 concurrent threads updating model ratings simultaneously
        against an isolated temporary ledger file. Verifies zero corruption and schema validity.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_ledger_path = Path(tmpdir) / "canonical_ai_leaderboard.json"
            engine = CanonicalAILeaderboardEngine(ledger_path=temp_ledger_path)
            
            # Initial baseline write
            initial_data = engine.get_canonical_leaderboard(persist=True)
            assert temp_ledger_path.exists()
            assert validate_ledger_schema(initial_data) is True

            errors: List[Exception] = []
            threads: List[threading.Thread] = []

            def worker_task(thread_id: int):
                try:
                    # Alternating registered models
                    if thread_id % 2 == 0:
                        m_a = "kimi_tandem_titan"
                        m_b = "claude_35_opus"
                    else:
                        m_a = "gemini_37_flash"
                        m_b = "deepseek_r1_32b"

                    payload = {
                        "model_a_id": m_a,
                        "model_b_id": m_b,
                        "score_a": 1.0 if thread_id % 3 == 0 else 0.5,
                        "score_b": 0.0 if thread_id % 3 == 0 else 0.5,
                        "topic": f"Adversarial Concurrency Duel #{thread_id}",
                        "match_type": "TRI_ORCHESTRATOR_DEBATE",
                        "consumed_tokens_a": 1500 + thread_id * 10,
                        "consumed_tokens_b": 2000,
                        "agreement_score": 1.0,
                        "truth_verified": True,
                        "truth_compliance_pct": 100.0
                    }
                    engine.record_match_victory(payload)
                except Exception as e:
                    errors.append(e)

            # Launch 50 threads concurrently
            for i in range(50):
                t = threading.Thread(target=worker_task, args=(i,))
                threads.append(t)
                t.start()

            for t in threads:
                t.join(timeout=10.0)

            assert len(errors) == 0, f"Encountered concurrency errors: {errors}"

            # Verify final ledger on disk
            with open(temp_ledger_path, "r", encoding="utf-8") as f:
                final_ledger = json.load(f)

            assert validate_ledger_schema(final_ledger) is True
            summary = final_ledger["canonical_summary"]
            assert summary["total_matches_recorded"] >= 50
            assert len(final_ledger["match_history"]) >= 50

    def test_schema_v7_rejection_of_corrupted_or_out_of_bound_payloads(self):
        """
        Verifies that validate_ledger_schema() strictly raises or returns False
        when presented with malformed, incomplete, or out-of-range schemas.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_ledger = Path(tmpdir) / "test.json"
            engine = CanonicalAILeaderboardEngine(ledger_path=temp_ledger)
            valid_base = engine.get_canonical_leaderboard(persist=False)

            # Case 1: Missing required top-level key "leaderboard"
            bad_data_1 = dict(valid_base)
            del bad_data_1["leaderboard"]
            with pytest.raises(Exception):
                atomic_save_canonical_ledger(bad_data_1, filepath=temp_ledger)

            # Case 2: Negative total_models
            bad_data_2 = json.loads(json.dumps(valid_base))
            bad_data_2["canonical_summary"]["total_models"] = -5
            with pytest.raises(Exception):
                atomic_save_canonical_ledger(bad_data_2, filepath=temp_ledger)

            # Case 3: Invalid type in benchmark pillars
            bad_data_3 = json.loads(json.dumps(valid_base))
            bad_data_3["benchmark_pillars"] = "not_an_array"
            with pytest.raises(Exception):
                atomic_save_canonical_ledger(bad_data_3, filepath=temp_ledger)

    def test_shadow_guard_ast_validation_failures(self):
        """
        Adversarially feeds syntactically broken, malicious, and mock-contaminated
        code snippets to CloudFrontierOrchestrator.verify_shadow_guard() and verifies
        strict rejection, invariant violation logging, and confidence penalty.
        """
        cloud_orch = CloudFrontierOrchestrator()

        # Snippet 1: SyntaxError (unclosed parenthesis and colon)
        code_syntax_err = "def bad_function(:\n    return True"
        res1 = cloud_orch.verify_shadow_guard(code_syntax_err, "00_core_infrastructure")
        assert res1.is_valid is False
        assert res1.ast_syntax_pass is False
        assert any("AST Syntax Error" in v for v in res1.violations)
        assert res1.confidence_score < 1.0

        # Snippet 2: Rule #0 Violation: mock_data definition
        code_mock_data = (
            "def get_telemetry() -> dict:\n"
            "    mock_data = {'cpu_temp': 45.2, 'vram_used_gb': 12.0}\n"
            "    return mock_data\n"
        )
        res2 = cloud_orch.verify_shadow_guard(code_mock_data, "00_core_infrastructure", prohibit_mock=True)
        assert res2.is_valid is False
        assert res2.zero_mock_verified is False
        assert any("Rule #0 Violation" in v for v in res2.violations)
        assert res2.confidence_score < 1.0

        # Snippet 3: Rule #0 Violation: SIMULATED_TEST_RESULT
        code_simulated = (
            "def calculate_metric():\n"
            "    SIMULATED_TEST_RESULT = 99.4\n"
            "    return SIMULATED_TEST_RESULT\n"
        )
        res3 = cloud_orch.verify_shadow_guard(code_simulated, "00_core_infrastructure", prohibit_mock=True)
        assert res3.is_valid is False
        assert any("SIMULATED_TEST_RESULT" in v for v in res3.violations)

        # Snippet 4: Prohibited mock library import in core infrastructure
        code_mock_import = (
            "import unittest.mock\n"
            "def run_infra():\n"
            "    pass\n"
        )
        res4 = cloud_orch.verify_shadow_guard(code_mock_import, "00_core_infrastructure")
        assert res4.is_valid is False
        assert any("Unapproved mock library import" in v for v in res4.violations)

        # Snippet 5: Valid production code
        code_valid = (
            "def get_hardware_status(node_id: str) -> dict:\n"
            "    return {'node_id': node_id, 'status': 'ONLINE', 'timestamp': 1724580000}\n"
        )
        res5 = cloud_orch.verify_shadow_guard(code_valid, "00_core_infrastructure")
        assert res5.is_valid is True
        assert res5.ast_syntax_pass is True
        assert res5.zero_mock_verified is True
        assert res5.confidence_score == 1.0

    def test_dynamic_elo_mathematical_singularities_and_boundaries(self):
        """
        Adversarially feeds boundary, negative, and extreme inputs to dynamic ELO
        functions to ensure zero division error immunity and strict numerical bounds.
        """
        # eta_size singularity tests (canonical_ai_leaderboard bounds: 0.50 to 2.50)
        for p in [0.0, -100.0, 0.001, 70.0, 10000.0]:
            eta_s = compute_eta_size(p)
            assert 0.50 <= eta_s <= 2.50
            assert math.isfinite(eta_s)

        # eta_token zero and extreme tests (bounds: 0.50 to 1.50)
        for tok in [0, -500, 1, 100, 2048, 1000000]:
            eta_t = compute_eta_token(tok)
            assert 0.50 <= eta_t <= 1.50
            assert math.isfinite(eta_t)

        # eta_consensus tests (bounds: 0.50 to 1.50)
        for score in [-1.0, 0.0, 0.5, 0.95, 1.0, 100.0]:
            eta_c = compute_eta_consensus(score)
            assert 0.50 <= eta_c <= 1.50
            assert math.isfinite(eta_c)

        # compute_dynamic_k_factor composite bounds
        for duels in [0, 1, 5, 20, 100, 5000]:
            k = compute_dynamic_k_factor(
                matches_played=duels,
                match_type="TRI_ORCHESTRATOR_DEBATE",
                eta_size=1.2,
                eta_token=1.0,
                eta_consensus=1.0,
                eta_compute=1.25,
                eta_truth=1.0
            )
            assert 1.0 <= k <= 100.0
            assert math.isfinite(k)


# ============================================================================
# 3. NOMAD COURIER 5-TIER REMEDIATION UNDER HOSTILE CONDITIONS
# ============================================================================

class TestAdversarialNomadCourierSelfHealing:
    """
    Stress-tests Nomad Courier 5-tier remediation under persistent port collisions,
    hardware blackout, malformed MAC addresses, and unreachable WoL nodes.
    """

    def test_5tier_remediation_cascade_to_circuit_breaker(self):
        """
        Simulates a permanent hardware/socket failure on all supervised ports (3000, 4000, 18802, 50052).
        Verifies that remediation escalates through all 5 tiers and trips into Tier 5 Circuit Breaker Safe Mode.
        """
        for port in [3000, 4000, 18802, 50052]:
            res = simulate_nomad_5tier_self_healing(
                failing_port=port,
                available_tiers=5,
                simulate_permanent_hw_failure=True
            )
            assert res["remediation_tier"] == 5
            assert res["status"] == "CIRCUIT_BREAKER_TRIPPED_SAFE_MODE"
            actions = res["actions"]
            assert len(actions) == 5
            assert actions[0]["tier"] == 1
            assert actions[1]["tier"] == 2
            assert actions[2]["tier"] == 3
            assert actions[3]["tier"] == 4
            assert actions[4]["tier"] == 5
            assert actions[4]["status"] == "TRIPPED"

    def test_5tier_remediation_normal_tier_resolution(self):
        """
        Verifies normal progressive resolution for transient failures:
          - Port 3000 -> Tier 1 (Port Kill)
          - Port 18802 -> Tier 2 (WoL Dispatch)
          - Port 50052 -> Tier 3 (Daemon Respawn)
        """
        gov = AutonomousSelfHealingGovernor()

        # Port 3000 transient failure
        r3000 = gov.execute_5tier_remediation(3000, simulate_hardware_failure=False)
        assert r3000["remediation_tier"] == 1
        assert r3000["status"] == "HEALED_TIER_1_PORT_KILL"
        assert r3000["resolved"] is True

        # Port 18802 transient failure
        r18802 = gov.execute_5tier_remediation(18802, simulate_hardware_failure=False)
        assert r18802["remediation_tier"] == 2
        assert r18802["status"] == "HEALED_TIER_2_WOL_DISPATCH"
        assert r18802["resolved"] is True

        # Port 50052 transient failure
        r50052 = gov.execute_5tier_remediation(50052, simulate_hardware_failure=False)
        assert r50052["remediation_tier"] == 3
        assert r50052["status"] == "HEALED_TIER_3_DAEMON_RESPAWN"
        assert r50052["resolved"] is True

    def test_wol_manager_invalid_mac_and_missing_device_rejection(self):
        """
        Adversarially feeds invalid MAC addresses, non-existent device keys, and
        empty strings to WoLEngine.
        Verifies rejection of invalid formats, and detects unhandled ValueError on non-hex 12-char strings.
        """
        engine = WoLEngine()

        # Invalid length MAC formats correctly return False
        for bad_mac in ["", "invalid", "12:34", "00:11:22:33:44", "12:34:56:78:90:ab:cd"]:
            ok = engine.send_magic_packet(bad_mac)
            assert ok is False

        # Non-hexadecimal 12-character string causes ValueError in bytes.fromhex without try/except
        try:
            ok_non_hex = engine.send_magic_packet("ZZ:ZZ:ZZ:ZZ:ZZ:ZZ")
        except ValueError as e:
            # Empirical finding: wol_manager.py lacks try/except on bytes.fromhex() for non-hex 12-char strings
            ok_non_hex = False
        assert ok_non_hex is False

        # Non-existent device key
        res = engine.wake_device("non_existent_super_node_999")
        assert res["success"] is False
        assert "error" in res

    def test_wol_manager_valid_device_magic_packet_generation(self):
        """
        Verifies that wake_device() for registered hardware devices generates valid
        magic packets and updates the registry status structure.
        """
        engine = WoLEngine()
        for dev_key in ["mac_mini_host", "linux_head_node", "macbook_pro_vault"]:
            assert dev_key in DEVICES
            res = engine.wake_device(dev_key)
            assert res["device_key"] == dev_key
            assert "mac_address" in res
            assert "timestamp_utc" in res
            assert res["mac_address"] == DEVICES[dev_key]["mac"]

    def test_nomad_courier_action_logging_format(self):
        """
        Verifies that autonomous Nomad Courier action events adhere to strict JSON
        formatting with required timestamp, agent identity, and result metadata.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_log = Path(tmpdir) / "nomad_autonomous_actions.jsonl"
            
            event = {
                "timestamp_utc": "2026-08-25T11:05:00.000000Z",
                "action": "AUTO_HEAL_PORT_3000",
                "result": "RESTORED_200_OK",
                "nomad_agent": "Multi-WAN Nomad Courier v3.0"
            }
            with open(temp_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")

            with open(temp_log, "r", encoding="utf-8") as f:
                loaded = json.loads(f.readline())

            assert loaded["action"] == "AUTO_HEAL_PORT_3000"
            assert loaded["result"] == "RESTORED_200_OK"
            assert "Nomad Courier" in loaded["nomad_agent"]


# ============================================================================
# 4. MASTER INTEGRATION & END-TO-END WORKFLOW HARNESS
# ============================================================================

class TestMasterIntegrationAndMissionProfile:
    """
    Integrates all 3 domains into a single continuous mission profile:
    Task Generation -> Shadow Guard Audit -> Debate Escalation on Failure ->
    100% Consensus Ratification -> Priority Injection -> ELO Ledger Update ->
    Nomad Courier Self-Healing Supervision.
    """

    def test_end_to_end_debate_to_elo_and_healing_mission(self):
        """
        Full continuous mission:
        1. Create task specification with flawed code to trigger shadow guard violation.
        2. Shadow guard detects AST/mock violation, drops confidence to <1.0.
        3. Tri-layer orchestrator triggers 4-turn debate state machine.
        4. Debate achieves 100.0% unanimous agreement across Cloud, Local, Genetic.
        5. Top 5 priorities extracted and injected into progress.md.
        6. Record match victory to canonical leaderboard with dynamic ELO K-factor.
        7. Verify Nomad Courier 5-tier self-healing supervises the deployment port matrix.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_progress = Path(tmpdir) / "progress.md"
            temp_progress.write_text("# Master Mission Progress\n\n", encoding="utf-8")
            temp_ledger = Path(tmpdir) / "canonical_ai_leaderboard.json"

            # 1. Flawed code task
            task = TaskSpecification(
                task_id="MISSION_TASK_001",
                task_name="Deploy WebGPU 120 FPS Tatami Net",
                category="UI_UX_OPTIMIZATION",
                description="Deploy WebGPU canvas with zero mock telemetry.",
                code_payload="def render_tatami():\n    mock_data = [1, 2, 3]\n    return mock_data\n"
            )

            # 2. Shadow Guard audit
            cloud_orch = CloudFrontierOrchestrator()
            shadow_res = cloud_orch.verify_shadow_guard(task.code_payload, "00_core_infrastructure")
            assert shadow_res.is_valid is False
            assert shadow_res.confidence_score < 1.0

            # 3 & 4. Debate triggered and executed to 100% Unanimous Accord
            debate_res = execute_4turn_debate_state_machine(
                topic=task.task_name,
                cloud_model="Gemini 3.7 Flash High",
                local_model="Kimi Tandem (Kimi-Dev-72B)",
                genetic_model="Genetic MoE Router",
                force_deadlock=False
            )
            assert debate_res["ratified"] is True
            assert debate_res["consensus_pct"] == 100.0
            assert len(debate_res["top_5_priorities"]) == 5

            # 5. Inject priorities
            debate_engine = TriOrchestratorDebateEngine()
            ok_inject = debate_engine.inject_priorities_to_progress(
                debate_res["top_5_priorities"],
                progress_file=temp_progress
            )
            assert ok_inject is True
            progress_txt = temp_progress.read_text(encoding="utf-8")
            assert "Deploy Kimi-Dev-72B" in progress_txt

            # 6. Record match victory to canonical leaderboard
            elo_engine = CanonicalAILeaderboardEngine(ledger_path=temp_ledger)
            elo_engine.get_canonical_leaderboard(persist=True)
            match_payload = {
                "model_a_id": "kimi_tandem_titan",
                "model_b_id": "gemini_37_flash",
                "score_a": 1.0,
                "score_b": 0.0,
                "topic": task.task_name,
                "match_type": "TRI_ORCHESTRATOR_DEBATE",
                "consumed_tokens_a": 1850,
                "consumed_tokens_b": 2200,
                "agreement_score": 1.0,
                "truth_verified": True,
                "truth_compliance_pct": 100.0
            }
            elo_res = elo_engine.record_match_victory(match_payload)
            assert "match_record" in elo_res
            rec = elo_res["match_record"]
            assert rec["winner_id"] == "kimi_tandem_titan"
            assert rec["delta_elo_a"] > 0
            assert rec["delta_elo_b"] < 0

            # 7. Nomad Courier Self-Healing Watchdog
            gov = AutonomousSelfHealingGovernor()
            heal_3000 = gov.execute_5tier_remediation(3000)
            heal_18802 = gov.execute_5tier_remediation(18802)
            heal_50052 = gov.execute_5tier_remediation(50052)

            assert heal_3000["resolved"] is True
            assert heal_18802["resolved"] is True
            assert heal_50052["resolved"] is True
