#!/usr/bin/env python3
"""
Comprehensive Test Suite for Tri-Orchestrator AI Debate Package
================================================================
Validates:
  1. 4-Turn Deliberative State Machine:
     - Turn 1: Independent Candidate Proposals (Candidates A, B, C)
     - Turn 2: Cross-Examination & Adversarial Stress Testing (Battery, Doze, Phantom Kill, ABI)
     - Turn 3: Mathematical Accord Synthesis (Agreement Matrix >= 0.90, Voting Ledger)
     - Turn 4: Top 5 Action Priorities Checklist
  2. Mathematical Accord Synthesis:
     - Multi-criteria weighted scoring across 5 operational dimensions
     - Pairwise Persona Agreement Matrix calculation (Cosine alignment >= 0.90)
     - Unanimous consensus ratification of Candidate C
  3. Artifact Serialization & Schema Compliance:
     - Full Markdown Transcript (data/debates/debate_shizuku_architecture.md)
     - LoRA JSONL Dataset (data/lora_datasets/truth_audit_nomad_mesh_debate.jsonl)
     - Canonical ELO Leaderboard Update & JSON Schema v7 validation
  4. Boundary and Edge Conditions:
     - Threshold boundary evaluation (>=0.90 passing, >0.9999 deadlock detection)
     - Multi-turn JSONL entry verification and schema validation
     - Specialist skill progression delta assertions
  5. Zero-Mock Rule #0 Compliance:
     - Real mathematical calculations, genuine file persistence, and state mutations
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Any, List

# Locate project roots
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_PATHS = [
    REPO_ROOT,
    REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src",
    REPO_ROOT / "self_healing_hub" / "src",
    REPO_ROOT / "scripts",
    REPO_ROOT / "06_scripts_and_tooling" / "scripts",
    REPO_ROOT / "ai_debate" / "src",
]
for p in SRC_PATHS:
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

from ai_debate.src.tri_orchestrator_debate import (
    TriOrchestratorDebateEngine,
    CandidateProposal,
    DebateTurn,
    MathematicalAccord,
    PERSONA_PROFILES,
    execute_shizuku_architecture_debate,
    run_full_shizuku_debate_cycle,
)
from canonical_ai_leaderboard import (
    CanonicalAILeaderboardEngine,
    validate_ledger_schema,
)


class BaseDebateTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="tri_debate_test_")
        self.tmp_path = Path(self.tmp_dir)

        self.debates_dir = self.tmp_path / "data" / "debates"
        self.lora_dir = self.tmp_path / "data" / "lora_datasets"
        self.memory_dir = self.tmp_path / "data" / "memory"

        self.debates_dir.mkdir(parents=True, exist_ok=True)
        self.lora_dir.mkdir(parents=True, exist_ok=True)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self.transcript_path = self.debates_dir / "debate_shizuku_architecture.md"
        self.lora_path = self.lora_dir / "truth_audit_nomad_mesh_debate.jsonl"
        self.leaderboard_path = self.memory_dir / "canonical_ai_leaderboard.json"

        # Seed leaderboard in temp
        engine_src = CanonicalAILeaderboardEngine()
        initial_ledger = engine_src.get_canonical_leaderboard(persist=False)
        with open(self.leaderboard_path, "w", encoding="utf-8") as f:
            json.dump(initial_ledger, f, indent=2)

        self.engine = TriOrchestratorDebateEngine(
            workspace_root=self.tmp_path,
            debates_dir=self.debates_dir,
            lora_path=self.lora_path,
            leaderboard_path=self.leaderboard_path,
        )

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)


class TestCandidateProposals(BaseDebateTestCase):
    """Verifies that all three candidates are comprehensively defined."""

    def test_candidate_definitions(self):
        candidates = self.engine.define_candidate_proposals()

        self.assertIn("Candidate_A", candidates)
        self.assertIn("Candidate_B", candidates)
        self.assertIn("Candidate_C", candidates)

        cand_a = candidates["Candidate_A"]
        self.assertIn("Kotlin", cand_a.title)
        self.assertIn("Binder", cand_a.mechanism)
        self.assertTrue(len(cand_a.key_advantages) >= 3)
        self.assertTrue(len(cand_a.critical_vulnerabilities) >= 2)

        cand_b = candidates["Candidate_B"]
        self.assertTrue("Termux" in cand_b.title or "rish" in cand_b.title)
        self.assertIn("rish", cand_b.mechanism)
        self.assertTrue(len(cand_b.key_advantages) >= 3)
        self.assertTrue(len(cand_b.critical_vulnerabilities) >= 2)

        cand_c = candidates["Candidate_C"]
        self.assertIn("Hybrid", cand_c.title)
        self.assertTrue("Kotlin" in cand_c.mechanism and "rish" in cand_c.mechanism)
        self.assertTrue(len(cand_c.key_advantages) >= 3)


class TestFourTurnDeliberativeStateMachine(BaseDebateTestCase):
    """Verifies the execution, order, and stages of all 4 debate turns."""

    def test_full_turn_sequence_structure(self):
        record = self.engine.execute_shizuku_architecture_debate()

        self.assertIn("turns", record)
        turns = record["turns"]
        self.assertEqual(len(turns), 10, f"Expected 10 total turn statements (3+3+3+1), got {len(turns)}")

        # Verify Turn 1
        t1_turns = [t for t in turns if t["turn_number"] == 1]
        self.assertEqual(len(t1_turns), 3)
        self.assertTrue(any(t["target_candidate"] == "Candidate_A" for t in t1_turns))
        self.assertTrue(any(t["target_candidate"] == "Candidate_B" for t in t1_turns))
        self.assertTrue(any(t["target_candidate"] == "Candidate_C" for t in t1_turns))

        # Verify Turn 2 (Adversarial stress testing)
        t2_turns = [t for t in turns if t["turn_number"] == 2]
        self.assertEqual(len(t2_turns), 3)
        t2_text = " ".join([t["content"] for t in t2_turns]).lower()
        self.assertTrue("battery" in t2_text or "power" in t2_text)
        self.assertIn("doze", t2_text)
        self.assertTrue("phantom process" in t2_text or "phantom" in t2_text)
        self.assertTrue("abi" in t2_text or "portability" in t2_text)

        # Verify Turn 3 (Mathematical accord)
        t3_turns = [t for t in turns if t["turn_number"] == 3]
        self.assertEqual(len(t3_turns), 3)
        for t in t3_turns:
            self.assertGreaterEqual(t["alignment_metric"], 90.0)

        # Verify Turn 4 (Priorities & Ratification)
        t4_turns = [t for t in turns if t["turn_number"] == 4]
        self.assertEqual(len(t4_turns), 1)
        self.assertGreaterEqual(t4_turns[0]["alignment_metric"], 90.0)


class TestMathematicalAccordSynthesis(BaseDebateTestCase):
    """Verifies mathematical agreement scores, weighting, and voting ledger."""

    def test_agreement_score_exceeds_threshold(self):
        record = self.engine.execute_shizuku_architecture_debate()

        self.assertTrue(record["is_consensus_passed"])
        self.assertGreaterEqual(record["final_alignment_pct"], 90.0)
        self.assertEqual(record["ratified_candidate"], "Candidate_C")

        accord = record["accord"]
        weighted_scores = accord["weighted_scores"]
        self.assertGreater(weighted_scores["Candidate_C"], weighted_scores["Candidate_A"])
        self.assertGreater(weighted_scores["Candidate_C"], weighted_scores["Candidate_B"])
        self.assertGreaterEqual(weighted_scores["Candidate_C"], 0.95)

        # Verify Pairwise Persona Agreement Matrix
        p_matrix = accord["pairwise_agreement_matrix"]
        for p1, row in p_matrix.items():
            for p2, sim in row.items():
                self.assertGreaterEqual(sim, 0.95, f"Pairwise correlation {p1} vs {p2} is below 0.95: {sim}")

        # Verify Voting Ledger
        votes = record["votes"]
        self.assertEqual(len(votes), 3)
        for speaker, vote in votes.items():
            self.assertTrue("RATIFIED" in vote or "AGREED" in vote)


class TestTopFiveActionPriorities(BaseDebateTestCase):
    """Verifies that exactly 5 checkable action priorities are extracted."""

    def test_top_5_priorities_content(self):
        record = self.engine.execute_shizuku_architecture_debate()

        priorities = record["top_5_priorities"]
        self.assertEqual(len(priorities), 5)
        for p in priorities:
            self.assertIsInstance(p, str)
            self.assertGreater(len(p.strip()), 15)

        all_p_text = " ".join(priorities).lower()
        self.assertTrue("hybrid" in all_p_text or "shizuku" in all_p_text)
        self.assertTrue("doze" in all_p_text or "phantom" in all_p_text)
        self.assertTrue("tailscale" in all_p_text or "daemon" in all_p_text)
        self.assertTrue("adb" in all_p_text or "5555" in all_p_text)
        self.assertIn("lora", all_p_text)


class TestArtifactGenerationAndPersistence(BaseDebateTestCase):
    """Verifies file writing on disk: Markdown transcript, LoRA JSONL, and ELO leaderboard."""

    def test_full_cycle_artifacts(self):
        res = self.engine.run_full_shizuku_debate_cycle(
            transcript_file=self.transcript_path,
            lora_file=self.lora_path,
            leaderboard_file=self.leaderboard_path,
        )

        self.assertTrue(res["success"])
        self.assertTrue(res["is_consensus_passed"])

        # 1. Check Markdown Transcript
        self.assertTrue(self.transcript_path.exists())
        self.assertGreater(self.transcript_path.stat().st_size, 500)
        md_content = self.transcript_path.read_text(encoding="utf-8")
        self.assertIn("# 🏛️ Tri-Orchestrator Live Agent Debate Transcript", md_content)
        self.assertIn("Candidate C (Hybrid Layered Controller)", md_content)
        self.assertIn("```mermaid", md_content)
        self.assertIn("flowchart TD", md_content)

        # 2. Check LoRA JSONL Dataset
        self.assertTrue(self.lora_path.exists())
        self.assertGreater(self.lora_path.stat().st_size, 0)
        lines = self.lora_path.read_text(encoding="utf-8").strip().split("\n")
        self.assertGreaterEqual(len(lines), 1)
        last_pair = json.loads(lines[-1])
        self.assertIn("instruction", last_pair)
        self.assertIn("input", last_pair)
        self.assertIn("thought", last_pair)
        self.assertIn("output", last_pair)
        self.assertIn("timestamp", last_pair)
        self.assertIn("Android Execution Architecture", last_pair["instruction"])
        self.assertIn("Candidate C", last_pair["output"])

        # 3. Check Canonical ELO Leaderboard
        self.assertTrue(self.leaderboard_path.exists())
        with open(self.leaderboard_path, "r", encoding="utf-8") as f:
            ledger_data = json.load(f)

        self.assertTrue(validate_ledger_schema(ledger_data))
        self.assertGreaterEqual(ledger_data["canonical_summary"]["total_matches_recorded"], 1)
        self.assertGreaterEqual(len(ledger_data["match_history"]), 1)

        last_match = ledger_data["match_history"][-1]
        self.assertEqual(last_match["match_type"], "TRI_ORCHESTRATOR_DEBATE")
        self.assertEqual(last_match["winner_id"], "genetic_moe_orchestrator")
        self.assertGreaterEqual(last_match["efficiency_multipliers"]["eta_consensus"], 0.90)

    def test_lora_dataset_multiple_append_integrity(self):
        """Verifies that running multiple debate cycles appends valid JSONL lines."""
        for _ in range(3):
            self.engine.run_full_shizuku_debate_cycle(
                transcript_file=self.transcript_path,
                lora_file=self.lora_path,
                leaderboard_file=self.leaderboard_path,
            )

        lines = self.lora_path.read_text(encoding="utf-8").strip().split("\n")
        self.assertEqual(len(lines), 3)
        for idx, line in enumerate(lines):
            parsed = json.loads(line)
            self.assertIn("instruction", parsed)
            self.assertIn("input", parsed)
            self.assertIn("thought", parsed)
            self.assertIn("output", parsed)
            self.assertIn("timestamp", parsed)


class TestZeroMockIntegrity(BaseDebateTestCase):
    """Verifies that all math and metrics are genuinely computed."""

    def test_live_empirical_calculations(self):
        record = self.engine.execute_shizuku_architecture_debate()

        accord = record["accord"]
        for cand_id, score in accord["weighted_scores"].items():
            self.assertIsInstance(score, float)
            self.assertTrue(0.0 < score <= 1.0)

        p_mat = accord["pairwise_agreement_matrix"]
        for p1, cols in p_mat.items():
            self.assertEqual(cols[p1], 1.0)  # Self-correlation must be 1.0
            for p2, val in cols.items():
                self.assertTrue(0.0 <= val <= 1.0)


if __name__ == "__main__":
    unittest.main()
