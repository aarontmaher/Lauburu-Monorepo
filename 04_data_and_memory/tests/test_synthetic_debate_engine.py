#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E & Unit Test Suite: Tri-Orchestrator Synthetic Debate & Stagnation Defense Engine
====================================================================================
Test Target: 04_data_and_memory/synthetic_debate_engine.py
Covers:
- Feature 7: Multi-Port Fleet Interlock (Ports 8082, 8083, 8087, 8096) (Tier 1 & Tier 2)
- Feature 8: 4-Turn DPO Debate & 5-Pillar Scoring (Tier 1 & Tier 2)
- Feature 9: Debate Stagnation Defense (ΔC < 0.02) (Tier 1 & Tier 2)
Test Framework: pytest
Zero-Mock Compliance: 100% genuine inputs, deterministic verification, zero facade mocks.
"""

import os
import sys
import json
import time
import socket
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Dict, Any

import pytest

# Ensure module path is accessible
MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from synthetic_debate_engine import (
    SyntheticDebateEngine,
    DebateTurn,
    DebateConsensusAccord,
    FLEET_PORTS,
    SYNTHETIC_DEBATE_TOPICS,
)
from tri_vault_sink import TriVaultSink, verify_zero_mock_compliance


@pytest.fixture
def temp_debate_workspace():
    """Provides an isolated workspace for synthetic debate tests."""
    temp_dir = tempfile.mkdtemp(prefix="lauburu_debate_test_")
    ws = Path(temp_dir)
    sink = TriVaultSink(
        lora_dir=ws / "lora_datasets",
        obsidian_dir=ws / "obsidian_vault" / "01_DEBATES",
        enforce_rule_zero=True,
    )
    engine = SyntheticDebateEngine(
        tri_vault_sink=sink,
        stagnation_threshold=0.02,
        stagnation_turn_limit=3,
    )
    yield {
        "workspace": ws,
        "sink": sink,
        "engine": engine,
    }
    shutil.rmtree(temp_dir, ignore_errors=True)


# ===========================================================================
# FEATURE 7: Multi-Port Fleet Interlock (Tiers 1 & 2)
# ===========================================================================

class TestFeature7MultiPortFleetInterlock:
    """Tests fleet port registry, non-blocking socket probes, and health mapping."""

    def test_fleet_ports_registry_mapping(self):
        """Tier 1.1: Verify FLEET_PORTS maps all 8 sovereign inference roles."""
        assert FLEET_PORTS["gateway"] == 8080
        assert FLEET_PORTS["coder_architect"] == 8082
        assert FLEET_PORTS["devils_advocate"] == 8083
        assert FLEET_PORTS["vision_auditor"] == 8084
        assert FLEET_PORTS["heavy_abliterated"] == 8085
        assert FLEET_PORTS["math_7b"] == 8086
        assert FLEET_PORTS["edge_agentworld"] == 8087
        assert FLEET_PORTS["math_72b"] == 8096

    def test_probe_port_health_open_and_closed_ports(self, temp_debate_workspace):
        """Tier 1.2: probe_port_health correctly detects open vs closed ports."""
        engine = temp_debate_workspace["engine"]

        # Create a temporary local listening socket
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        assigned_port = srv.getsockname()[1]

        try:
            assert engine.probe_port_health(assigned_port, timeout_s=0.5) is True
        finally:
            srv.close()

        # After closing, port should return False
        time.sleep(0.05)
        assert engine.probe_port_health(assigned_port, timeout_s=0.2) is False

    def test_get_fleet_status_schema(self, temp_debate_workspace):
        """Tier 1.3: get_fleet_status returns complete health map across all fleet roles."""
        engine = temp_debate_workspace["engine"]
        status = engine.get_fleet_status()

        assert len(status) == len(FLEET_PORTS)
        for role, info in status.items():
            assert "port" in info
            assert "is_live" in info
            assert isinstance(info["port"], int)
            assert isinstance(info["is_live"], bool)

    def test_fleet_interlock_non_blocking_timeout(self, temp_debate_workspace):
        """Tier 1.4: Probe respects strict sub-second timeout without stalling."""
        engine = temp_debate_workspace["engine"]
        t0 = time.perf_counter()
        # Probe an arbitrary unused high port
        engine.probe_port_health(58999, timeout_s=0.1)
        dt = time.perf_counter() - t0
        assert dt < 0.5  # Sub-second guarantee

    def test_fleet_port_health_closed_port_resilience(self, temp_debate_workspace):
        """Tier 2.1: Closed port probe handles connection refused cleanly without crashing."""
        engine = temp_debate_workspace["engine"]
        # Non-listening port
        assert engine.probe_port_health(59999, timeout_s=0.1) is False


# ===========================================================================
# FEATURE 8: 4-Turn DPO Debate & 5-Pillar Scoring (Tiers 1 & 2)
# ===========================================================================

class TestFeature8DPO4TurnDebateAnd5PillarScoring:
    """Tests 4-turn state machine, 3-judge council 5-pillar scoring, and TRL DPO export."""

    def test_run_deliberation_4_turns_sequence(self, temp_debate_workspace):
        """Tier 1.1: run_deliberation executes 4-turn protocol in strict sequence."""
        engine = temp_debate_workspace["engine"]
        accord = engine.run_deliberation(topic_idx=0)

        assert isinstance(accord, DebateConsensusAccord)
        assert len(accord.rounds) == 4
        assert accord.rounds[0].turn_type == "OPENING_THESIS"
        assert accord.rounds[1].turn_type == "CROSS_EXAMINATION"
        assert accord.rounds[2].turn_type == "TECHNICAL_SYNTHESIS"
        assert accord.rounds[3].turn_type == "CONSENSUS_RATIFICATION"

    def test_3judge_council_5pillar_scoring_weights(self, temp_debate_workspace):
        """Tier 1.2: 5-pillar scoring calculates exact weighted composite score."""
        engine = temp_debate_workspace["engine"]
        scores, total_scores, winner_role = engine.evaluate_3judge_council(
            architect_text="def compute_headroom(cap=21.6):\n    return cap - 18.4",
            challenger_text="What happens if activation spikes above 2.0GB?",
            synthesis_text="def safe_train():\n    torch.mps.empty_cache()\n    return True",
        )

        assert "alpha" in scores
        assert "beta" in scores
        assert "gamma" in scores

        for alias, s_dict in scores.items():
            expected = round(
                (s_dict["syntax"] * 0.25)
                + (s_dict["depth"] * 0.25)
                + (s_dict["economy"] * 0.20)
                + (s_dict["safety"] * 0.15)
                + (s_dict["truth"] * 0.15),
                2
            )
            assert total_scores[alias] == expected

    def test_consensus_accord_ratification_threshold(self, temp_debate_workspace):
        """Tier 1.3: Consensus passes at >= 90.0% alignment and fails below."""
        engine = temp_debate_workspace["engine"]
        accord_pass = engine.run_deliberation(topic_idx=0, force_stagnation=False)
        assert accord_pass.consensus_alignment_pct >= 90.0
        assert accord_pass.consensus_passed is True

        accord_fail = engine.run_deliberation(topic_idx=0, force_stagnation=True)
        assert accord_fail.consensus_alignment_pct < 90.0
        assert accord_fail.consensus_passed is False

    def test_export_dpo_pair_huggingface_trl_schema(self, temp_debate_workspace):
        """Tier 1.4: export_dpo_pair outputs HuggingFace TRL DPOTrainer schema."""
        engine = temp_debate_workspace["engine"]
        accord = engine.run_deliberation(topic_idx=0)
        dpo_record = engine.export_dpo_pair(accord, topic_idx=0)

        assert "trial_id" in dpo_record
        assert "prompt" in dpo_record
        assert "chosen" in dpo_record
        assert "rejected" in dpo_record
        assert "meta" in dpo_record
        assert dpo_record["meta"]["zero_mock_certified"] is True
        assert dpo_record["meta"]["truth_compliance_pct"] == 100.0
        assert "10Gbps Thunderbolt 4" in dpo_record["chosen"]

    def test_export_sft_pair_chatml_messages_format(self, temp_debate_workspace):
        """Tier 1.5: export_sft_pair outputs standard ShareGPT/ChatML format with <thought>."""
        engine = temp_debate_workspace["engine"]
        accord = engine.run_deliberation(topic_idx=0)
        sft_record = engine.export_sft_pair(accord, topic_idx=0)

        assert "instruction" in sft_record
        assert "thought" in sft_record
        assert sft_record["thought"].startswith("<thought>")
        assert sft_record["thought"].endswith("</thought>")
        assert "messages" in sft_record
        assert len(sft_record["messages"]) == 3
        assert sft_record["messages"][0]["role"] == "system"
        assert sft_record["messages"][1]["role"] == "user"
        assert sft_record["messages"][2]["role"] == "assistant"

    def test_top_5_priorities_extraction(self, temp_debate_workspace):
        """Tier 2.1: Consensus accord contains exactly 5 actionable priorities."""
        engine = temp_debate_workspace["engine"]
        accord = engine.run_deliberation(topic_idx=0)
        assert len(accord.top_5_priorities) == 5
        assert any("zero-mock" in p.lower() for p in accord.top_5_priorities)

    def test_multiple_deliberation_topics_coverage(self, temp_debate_workspace):
        """Tier 2.2: Deliberation engine supports all canonical topics in repository."""
        engine = temp_debate_workspace["engine"]
        for idx in range(len(SYNTHETIC_DEBATE_TOPICS)):
            accord = engine.run_deliberation(topic_idx=idx)
            assert accord.topic == SYNTHETIC_DEBATE_TOPICS[idx]["topic"]
            assert accord.consensus_passed is True


# ===========================================================================
# FEATURE 9: Debate Stagnation Defense (Tiers 1 & 2)
# ===========================================================================

class TestFeature9DebateStagnationDefense:
    """Tests score plateau detection (ΔC < 0.02 over 3 rounds) and specialist substitution."""

    def test_stagnation_detection_on_score_plateau(self, temp_debate_workspace):
        """Tier 1.1: ΔC < 0.02 over 3 consecutive turns triggers automated substitution."""
        engine = temp_debate_workspace["engine"]

        # Initial baseline
        engine.detect_stagnation_and_substitute(95.00)
        # Turn 1 plateau (delta 0.01)
        stagnated, _ = engine.detect_stagnation_and_substitute(95.01)
        assert stagnated is False
        # Turn 2 plateau (delta 0.005)
        stagnated, _ = engine.detect_stagnation_and_substitute(95.015)
        assert stagnated is False
        # Turn 3 plateau (delta 0.005) -> Triggers substitution
        stagnated, sub_msg = engine.detect_stagnation_and_substitute(95.020)
        assert stagnated is True
        assert "STAGNATION DEFENSE TRIGGERED" in sub_msg

    def test_nominal_progression_resets_stagnation_counter(self, temp_debate_workspace):
        """Tier 1.2: Meaningful consensus delta (ΔC >= 0.02) resets stagnant turn counter."""
        engine = temp_debate_workspace["engine"]

        engine.detect_stagnation_and_substitute(90.0)
        engine.detect_stagnation_and_substitute(90.01)  # stagnant turn 1
        engine.detect_stagnation_and_substitute(90.015)  # stagnant turn 2
        assert engine.consecutive_stagnant_turns == 2

        # Turn with large delta (0.05 >= 0.02)
        stagnated, msg = engine.detect_stagnation_and_substitute(90.07)
        assert stagnated is False
        assert engine.consecutive_stagnant_turns == 0
        assert "Nominal debate progression" in msg

    def test_stagnation_specialist_substitution_toggle(self, temp_debate_workspace):
        """Tier 1.3: Stagnation auto-substitutes coder_architect -> math_72b and resets turns."""
        engine = temp_debate_workspace["engine"]
        assert engine.active_primary_model == "coder_architect"

        # Force 3 stagnant rounds
        engine.detect_stagnation_and_substitute(95.0)
        engine.detect_stagnation_and_substitute(95.005)
        engine.detect_stagnation_and_substitute(95.010)
        stagnated, msg = engine.detect_stagnation_and_substitute(95.015)

        assert stagnated is True
        assert engine.active_primary_model == "math_72b"
        assert "Qwen-Math-72B Specialist" in msg
        assert engine.consecutive_stagnant_turns == 0

    def test_deliberation_with_forced_stagnation_replaces_model(self, temp_debate_workspace):
        """Tier 1.4: run_deliberation with force_stagnation flags stagnation in accord."""
        engine = temp_debate_workspace["engine"]
        accord = engine.run_deliberation(topic_idx=0, force_stagnation=True)

        assert accord.stagnation_occurred is True
        assert accord.substituted_specialist is not None

    def test_run_full_debate_cycle_exports_both_dpo_and_sft(self, temp_debate_workspace):
        """Tier 1.5: run_full_debate_cycle executes full deliberation and exports datasets."""
        engine = temp_debate_workspace["engine"]
        summary = engine.run_full_debate_cycle(topic_idx=1)

        assert "debate_id" in summary
        assert "topic" in summary
        assert summary["consensus_passed"] is True
        assert summary["dpo_exported"] is True
        assert summary["sft_exported"] is True

    def test_stagnation_threshold_parameterization(self, temp_debate_workspace):
        """Tier 2.1: Engine respects custom stagnation thresholds and turn limits."""
        engine = SyntheticDebateEngine(stagnation_threshold=0.05, stagnation_turn_limit=2)

        engine.detect_stagnation_and_substitute(90.0)
        # Turn 1 delta 0.03 (< 0.05)
        engine.detect_stagnation_and_substitute(90.03)
        # Turn 2 delta 0.02 (< 0.05) -> Triggers at limit=2
        stagnated, _ = engine.detect_stagnation_and_substitute(90.05)
        assert stagnated is True
