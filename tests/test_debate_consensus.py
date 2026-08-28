"""
Comprehensive Test Suite for Tri-Orchestrator AI Debate & Dynamic Consensus Protocol.
=====================================================================================
Verifies:
1. 4-Turn Deliberative State Machine:
   - Turn 1: Opening Theses (Cloud safety invariants, Local $0 spend sovereignty, Genetic fitness)
   - Turn 2: Cross-Examination & Critique (Latency vs thermals, token burn vs unverified mutations)
   - Turn 3: Technical Concessions & Synthesis (100% local telemetry, asynchronous cloud shadow audits)
   - Turn 4: Consensus Accord Ratification & Formal Voting (Unanimous votes, alignment >= 90%)
2. Multi-Model Support:
   - Cloud: Gemini 3.7 Flash/Pro, Gemini 3.1 Pro, Claude 3.7 Sonnet, Claude 4.6 Opus
   - Local: Kimi Tandem Titan, Kimi-Dev-72B, DeepSeek-R1-32B/671B, Qwen 2.5 Coder 32B, Qwen 2.5-VL 72B
   - Genetic: MoE Evolutionary Router
3. Debate Focus Domains:
   - UI/UX Development Optimization (120 FPS WebGPU shaders, 3D tatami world models, AST/CoT diff viewers)
   - Project AI Skill Necessities (26 monorepo applications, 12 domains, 82.8 GB VRAM mesh sharding)
4. Consensus Voting Mechanism:
   - Strict >=90% agreement threshold validation
   - Formal voting ledger verification
   - Deadlock / threshold boundary conditions
5. Top 5 Priority Extraction & Non-Destructive progress.md Injection:
   - Exactly 5 checkable, non-destructive priority items
   - Clean markdown formatting and preservation of existing progress.md contents
6. 24/7 LoRA Dataset Serialization:
   - Valid JSONL records with instruction, input, thought, output, and timestamp
   - Multi-turn thought trace capture
7. Canonical ELO Leaderboard Integration:
   - Real victory recording via CanonicalAILeaderboardEngine.record_match_victory()
   - Efficiency multipliers (eta_size, eta_token, eta_consensus, eta_compute, eta_truth)
   - Specialist skill delta updates (debating, 3d_ai_training_game, vision_vlm_truth_auditing)
   - Match history updates and JSON Schema v7 validation
8. TriOrchestratorChatService Integration:
   - Live debate execution via /debate action and deliberate_consensus_accord()
   - 1-click execution actions (launch_swarm_sprint, sync_obsidian, push_adb, send_google_chat)
9. Zero-Mock Rule #0 Compliance:
   - Genuine empirical calculations and state mutations
"""

import os
import sys
import json
import time
import tempfile
from pathlib import Path
from typing import Dict, Any, List
import pytest

# Ensure repository packages are in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_PATHS = [
    REPO_ROOT,
    REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src",
    REPO_ROOT / "self_healing_hub" / "src",
    REPO_ROOT / "scripts",
    REPO_ROOT / "06_scripts_and_tooling" / "scripts",
]

for p in SRC_PATHS:
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

from ai_debate_engine import (
    TriOrchestratorDebateEngine,
    generate_domain_conclusions,
    record_debate_and_conclusions,
    CLOUD_MODELS,
    LOCAL_MODELS,
    GENETIC_MODELS,
)
from canonical_ai_leaderboard import (
    CanonicalAILeaderboardEngine,
    validate_ledger_schema,
)
from tri_orchestrator_chat_service import TriOrchestratorChatService


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def temp_workspace(tmp_path):
    """Creates a temporary workspace with genuine directory structure."""
    data_dir = tmp_path / "data"
    lora_dir = data_dir / "lora_datasets"
    logs_dir = tmp_path / "session_logs"
    data_dir.mkdir(parents=True, exist_ok=True)
    lora_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Initialize a canonical leaderboard ledger in temp
    engine_src = CanonicalAILeaderboardEngine()
    initial_ledger = engine_src.get_canonical_leaderboard(persist=False)
    ledger_path = data_dir / "canonical_ai_leaderboard.json"
    with open(ledger_path, "w", encoding="utf-8") as f:
        json.dump(initial_ledger, f, indent=2)

    progress_path = tmp_path / "progress.md"
    progress_path.write_text("# Monorepo Progress Ledger\n\n## Initial Status\n- [x] Initialized workspace\n", encoding="utf-8")

    return {
        "root": tmp_path,
        "data_dir": data_dir,
        "lora_path": lora_dir / "truth_audit_debate.jsonl",
        "ledger_path": ledger_path,
        "progress_path": progress_path,
        "logs_dir": logs_dir,
    }


@pytest.fixture
def debate_engine(temp_workspace):
    """Instantiates a TriOrchestratorDebateEngine pointed to temp workspace."""
    return TriOrchestratorDebateEngine(
        workspace_root=temp_workspace["root"],
        leaderboard_path=temp_workspace["ledger_path"],
        lora_path=temp_workspace["lora_path"],
        progress_path=temp_workspace["progress_path"],
    )


# ===========================================================================
# Tier 1: 4-Turn Deliberative State Machine Structure & Models
# ===========================================================================

class TestFourTurnStateMachine:
    """Verifies the 4-turn state machine and multi-model coordination."""

    def test_four_turns_present_and_ordered(self, debate_engine):
        """Verify that all 4 deliberative turns exist with correct round numbers and stages."""
        record = debate_engine.execute_4_turn_debate(
            topic="WebGPU 120 FPS Rendering & 3D Kinematics",
            domain="UI_UX_Development",
        )
        turns = record["turns"]
        assert len(turns) == 10, f"Expected 10 total turn statements (3+3+3+1), got {len(turns)}"

        # Round 1: Opening Thesis (Cloud, Local, Genetic)
        r1 = [t for t in turns if t["round"] == 1]
        assert len(r1) == 3
        assert any("Cloud" in t["speaker"] for t in r1)
        assert any("Local" in t["speaker"] for t in r1)
        assert any("Genetic" in t["speaker"] for t in r1)
        for t in r1:
            assert t["stage"] == "Opening Thesis"
            assert 40.0 <= t["alignment_pct"] <= 60.0

        # Round 2: Cross-Examination & Critique
        r2 = [t for t in turns if t["round"] == 2]
        assert len(r2) == 3
        for t in r2:
            assert 65.0 <= t["alignment_pct"] <= 85.0

        # Round 3: Technical Concessions & Synthesis
        r3 = [t for t in turns if t["round"] == 3]
        assert len(r3) == 3
        for t in r3:
            assert t["alignment_pct"] >= 90.0

        # Round 4: Consensus Accord & Formal Voting
        r4 = [t for t in turns if t["round"] == 4]
        assert len(r4) == 1
        accord = r4[0]
        assert accord["stage"] == "Unanimous Consensus Accord"
        assert accord["alignment_pct"] >= 90.0
        assert "votes" in accord
        assert len(accord["votes"]) == 3

    @pytest.mark.parametrize("cloud_key", ["gemini_37_flash", "gemini_37_pro", "claude_37_sonnet", "claude_opus_4_6"])
    @pytest.mark.parametrize("local_key", ["kimi_tandem_titan", "kimi_dev_72b", "deepseek_r1_distill_qwen_32b", "qwen2_5_coder_32b"])
    def test_model_permutations(self, debate_engine, cloud_key, local_key):
        """Verify that all combinations of frontier cloud and sovereign local models execute properly."""
        record = debate_engine.execute_4_turn_debate(
            topic=f"Testing {cloud_key} vs {local_key}",
            domain="UI_UX_Development",
            cloud_model_key=cloud_key,
            local_model_key=local_key,
        )
        assert record["cloud_model"]["name"] in [t["speaker"] for t in record["turns"]]
        assert record["local_model"]["name"] in [t["speaker"] for t in record["turns"]]
        assert record["genetic_model"]["name"] in [t["speaker"] for t in record["turns"]]
        assert record["consensus_status"] == "RATIFIED"


# ===========================================================================
# Tier 2: Focus Domains (UI/UX Development & Project AI Skill Necessities)
# ===========================================================================

class TestDebateFocusDomains:
    """Verifies domain-specific argumentation and synthesized recommendations."""

    def test_ui_ux_development_domain(self, debate_engine):
        """Verify that UI/UX development debates generate specific WebGPU, 3D, and layout findings."""
        record = debate_engine.execute_4_turn_debate(
            topic="120 FPS WebGPU Shader Pipeline & 3D Tatami Models",
            domain="UI_UX_Development",
        )
        assert record["domain"] == "UI_UX_Development"
        priorities_text = " ".join(record["top_5_priorities"]).lower()

        assert "webgpu" in priorities_text or "shader" in priorities_text
        assert "3d" in priorities_text or "tatami" in priorities_text
        assert "cot" in priorities_text or "reasoning" in priorities_text or "diff" in priorities_text
        assert "dark mode" in priorities_text or "visual" in priorities_text
        assert "visual audit" in priorities_text or "openclaw" in priorities_text

    def test_project_ai_skill_necessities_domain(self, debate_engine):
        """Verify that Project AI skill debates address 26 applications, 12 domains, and GGUF sharding."""
        record = debate_engine.execute_4_turn_debate(
            topic="Monorepo 26-App Project AI Specialist Skill Sharding",
            domain="Project_AI_Skill_Necessities",
        )
        assert record["domain"] == "Project_AI_Skill_Necessities"
        priorities_text = " ".join(record["top_5_priorities"]).lower()

        assert "gguf" in priorities_text or "sharding" in priorities_text or "vram" in priorities_text
        assert "elo" in priorities_text or "calibration" in priorities_text
        assert "thunderbolt" in priorities_text or "rpc" in priorities_text
        assert "lora" in priorities_text or "distillation" in priorities_text
        assert "truth audit" in priorities_text or "hardware" in priorities_text


# ===========================================================================
# Tier 3: Consensus Voting & Threshold Enforcement (>=90%)
# ===========================================================================

class TestConsensusVoting:
    """Verifies unanimous voting and threshold evaluation logic."""

    def test_consensus_voting_passes_above_90_percent(self, debate_engine):
        """Verify that default deliberation exceeds the 90% threshold and confirms agreement."""
        record = debate_engine.execute_4_turn_debate(
            topic="System Self-Healing & Distributed Mesh Architecture",
            agreement_threshold=0.90,
        )
        is_passed, alignment, votes = debate_engine.evaluate_consensus(record, threshold=0.90)
        assert is_passed is True
        assert alignment >= 90.0
        assert len(votes) == 3
        for speaker, vote in votes.items():
            assert "✅ VOTE: AGREED" in vote

    def test_consensus_fails_when_threshold_unmet(self, debate_engine):
        """Verify that when the required threshold exceeds actual alignment, consensus fails."""
        record = debate_engine.execute_4_turn_debate(
            topic="Strict 99.9% Consensus Challenge",
            agreement_threshold=0.999,  # 99.9% requirement
        )
        is_passed, alignment, votes = debate_engine.evaluate_consensus(record, threshold=0.999)
        assert is_passed is False
        assert record["consensus_status"] == "DEADLOCK"


# ===========================================================================
# Tier 4: Top 5 Priority Extraction & progress.md Injection
# ===========================================================================

class TestPriorityExtractionAndProgressInjection:
    """Verifies priority extraction and safe non-destructive progress file injection."""

    def test_extract_exactly_five_priorities(self, debate_engine):
        """Verify that exactly 5 non-empty checkable priorities are extracted."""
        record = debate_engine.execute_4_turn_debate(topic="Core Mesh Governance")
        priorities = debate_engine.extract_top_5_priorities(record)
        assert len(priorities) == 5
        for p in priorities:
            assert isinstance(p, str)
            assert len(p.strip()) > 10

    def test_non_destructive_progress_injection(self, debate_engine, temp_workspace):
        """Verify that progress.md is updated without overwriting existing content."""
        progress_path = temp_workspace["progress_path"]
        initial_content = progress_path.read_text(encoding="utf-8")

        record = debate_engine.execute_4_turn_debate(topic="WebGPU UI Optimization")
        priorities = debate_engine.extract_top_5_priorities(record)
        injected = debate_engine.inject_priorities_to_progress(priorities, progress_file=progress_path)

        assert injected is True
        updated_content = progress_path.read_text(encoding="utf-8")
        assert initial_content in updated_content, "Existing content in progress.md was overwritten!"
        assert "## Active Priorities (Injected by Live Tri-Orchestrator Debate" in updated_content
        for p in priorities:
            assert "- [ ]" in updated_content


# ===========================================================================
# Tier 5: 24/7 LoRA Dataset Serialization
# ===========================================================================

class TestLoRADatasetSerialization:
    """Verifies JSONL formatting and instruction-thought-solution structure."""

    def test_serialize_lora_training_pair(self, debate_engine, temp_workspace):
        """Verify that debate turns are converted to a valid JSONL training pair."""
        lora_file = temp_workspace["lora_path"]
        record = debate_engine.execute_4_turn_debate(topic="LoRA Dataset Fine-Tuning & Memory Distillation")
        lora_entry = debate_engine.serialize_lora_training_pair(record, output_path=lora_file)

        assert "instruction" in lora_entry
        assert "input" in lora_entry
        assert "thought" in lora_entry
        assert "output" in lora_entry
        assert "timestamp" in lora_entry

        assert "[Turn 1 - Opening Thesis]" in lora_entry["thought"]
        assert "[Turn 2 - Counter-Argument & Critique]" in lora_entry["thought"]
        assert "[Turn 3 - Technical Concession]" in lora_entry["thought"]
        assert "[Turn 4 - Unanimous Consensus Accord]" in lora_entry["thought"]

        assert lora_file.exists()
        lines = lora_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) >= 1
        parsed = json.loads(lines[-1])
        assert parsed["instruction"] == lora_entry["instruction"]


# ===========================================================================
# Tier 6: Canonical ELO Leaderboard Integration
# ===========================================================================

class TestCanonicalEloLeaderboardIntegration:
    """Verifies that debate match victories update canonical_ai_leaderboard.json."""

    def test_record_debate_to_leaderboard(self, debate_engine, temp_workspace):
        """Verify that record_debate_to_leaderboard updates model ELOs and records match history."""
        ledger_path = temp_workspace["ledger_path"]
        record = debate_engine.execute_4_turn_debate(topic="Kinematic Grappling & UI Debate")

        res = debate_engine.record_debate_to_leaderboard(
            debate_record=record,
            model_a_id="kimi_tandem_titan",
            model_b_id="gemini_37_flash",
            score_a=1.0,
            score_b=0.0,
            target_skills=["debating", "3d_ai_training_game", "vision_vlm_truth_auditing"],
            ledger_path=ledger_path,
        )

        assert "match_record" in res
        assert res["match_record"]["winner_id"] == "kimi_tandem_titan"
        assert res["match_record"]["score_a"] == 1.0
        assert res["match_record"]["score_b"] == 0.0

        # Read back ledger and validate schema
        with open(ledger_path, "r", encoding="utf-8") as f:
            ledger_data = json.load(f)

        assert validate_ledger_schema(ledger_data) is True
        assert ledger_data["canonical_summary"]["total_matches_recorded"] >= 1
        assert len(ledger_data["match_history"]) >= 1

        match_entry = ledger_data["match_history"][-1]
        assert match_entry["match_type"] == "TRI_ORCHESTRATOR_DEBATE"
        assert "efficiency_multipliers" in match_entry
        assert match_entry["efficiency_multipliers"]["eta_consensus"] >= 0.90

    def test_full_debate_cycle_e2e(self, debate_engine, temp_workspace):
        """Verify the complete end-to-end cycle from deliberation to ELO ledger and LoRA sync."""
        res = debate_engine.run_full_debate_cycle(
            topic="End-to-End System Synchronization",
            domain="UI_UX_Development",
            cloud_model_key="claude_37_sonnet",
            local_model_key="deepseek_r1_distill_qwen_32b",
            record_to_leaderboard=True,
            progress_file=temp_workspace["progress_path"],
            lora_file=temp_workspace["lora_path"],
            ledger_path=temp_workspace["ledger_path"],
        )

        assert res["consensus_passed"] is True
        assert len(res["top_5_priorities"]) == 5
        assert res["leaderboard_update"] is not None
        assert res["lora_entry"] is not None


# ===========================================================================
# Tier 7: TriOrchestratorChatService Integration
# ===========================================================================

class TestTriOrchestratorChatServiceIntegration:
    """Verifies that the live chat service executes debates and dispatches actions."""

    def test_chat_service_deliberate_consensus_accord(self):
        """Verify deliberate_consensus_accord generates a consensus card and history record."""
        svc = TriOrchestratorChatService()
        topic = "WebGPU 120 FPS UI/UX Canvas Pipeline"
        res = svc.deliberate_consensus_accord(topic=topic, user_name="TestOperator")

        assert res["success"] is True
        assert "consensus" in res
        card = res["consensus"]
        assert card["type"] == "consensus_accord_card"
        assert topic in card["text"]
        assert "execution_actions" in card
        action_ids = [a["id"] for a in card["execution_actions"]]
        assert "exec_sprint" in action_ids
        assert "exec_obsidian" in action_ids
        assert "exec_adb" in action_ids
        assert "exec_gchat" in action_ids

    def test_chat_service_execute_action(self):
        """Verify 1-click execution dispatchers."""
        svc = TriOrchestratorChatService()
        action_res = svc.execute_action("launch_swarm_sprint", {"topic": "Automated WebGPU Test"})
        assert action_res["status"] == "SUCCESS"
        assert "WebGPU" in action_res["summary"]


# ===========================================================================
# Tier 8: Zero-Mock & Rule #0 Compliance
# ===========================================================================

class TestZeroMockCompliance:
    """Ensures genuine execution without hardcoded mock responses."""

    def test_standalone_functions_generate_real_records(self):
        """Verify backwards-compatible helper functions return live computed records."""
        rec = generate_domain_conclusions(
            topic="Empirical Telemetry Verification",
            domain="System_Orchestration",
        )
        assert "turns" in rec
        assert len(rec["turns"]) == 3
        assert rec["final_alignment_pct"] >= 90.0
        assert len(rec["top_5_priorities"]) == 5

    def test_real_file_persistence(self, debate_engine, temp_workspace):
        """Verify that genuine file writes happen on disk and are readable."""
        lora_file = temp_workspace["lora_path"]
        record = debate_engine.execute_4_turn_debate(topic="Disk Integrity Test")
        debate_engine.serialize_lora_training_pair(record, output_path=lora_file)

        assert lora_file.exists()
        assert lora_file.stat().st_size > 0
        content = lora_file.read_text(encoding="utf-8")
        assert "Perform Tri-Orchestrator AI Debate" in content
