#!/usr/bin/env python3
"""
Unit and Integration Test Suite — Milestone 2: Tri-Orchestrator Blind Grading & Dynamic Multi-Factor ELO Engine
=============================================================================================================
Validates:
1. ChallengerPoolCycler:
   - Dynamic rotation across Local 100B+, 70B abliterated, GGUF vault, and Cloud AI models.
   - Exclusion of current Champion model.
   - GGUF vault scanning, latency calculation, timeout boundaries, and error capture.
   - Asynchronous and synchronous execution compatibility.
2. TriOrchestratorBlindGrader / ContinuousArenaGrader:
   - Header stripping and blind alias anonymization (alpha, beta, gamma).
   - 3-Judge Judicial Council (Frontier Judge, Swarm Judge, Devil's Advocate).
   - 5-Pillar multi-dimensional scoring (Syntax, Depth, Economy, Safety, Truth).
   - Round-robin pairwise match decomposition and judicial consensus weighting.
   - Judicial rationale synthesis and proof.
3. CanonicalAILeaderboard Integration & Dynamic ELO:
   - Multi-factor Dynamic K-factor with all 6 efficiency multipliers.
   - Expected outcome logistics and ELO delta calculation.
   - Atomic POSIX ledger saving and Schema v7 validation.
   - Specialist skill progression deltas.
4. Dynamic Champion Promotion:
   - Overtake triggers dynamic Champion handover.
   - Strict rank re-indexing (1..N).
   - Subsequent prompt resolution reflection.
   - Multi-promotion stability.
5. Tri-Vault Harvesting:
   - LoRA DPO JSONL export.
   - Obsidian debate Markdown transcripts with Wikilinks and frontmatter.
6. Router Wiring & Integration:
   - Seamless wiring into ContinuousArenaEngine and ContinuousArenaInferenceRouter.
"""

import os
import sys
import time
import math
import json
import uuid
import shutil
import tempfile
import asyncio
import threading
import unittest
from pathlib import Path
from typing import Dict, Any, List, Optional

# Dynamic Path Setup
TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "01_apps" / "canonical_port" / "backend" / "agents"))
sys.path.insert(0, str(PROJECT_ROOT / "02_ai_models_and_inference"))
sys.path.insert(0, str(PROJECT_ROOT / "05_agents_and_swarms" / "tri_orchestrator"))

from challenger_pool_cycler import (
    ChallengerPoolCycler,
    DEFAULT_CHALLENGER_POOL,
)
from continuous_arena_grader import (
    TriOrchestratorBlindGrader,
    ContinuousArenaGrader,
    BLIND_ALIASES,
)
from canonical_ai_leaderboard import (
    CanonicalAILeaderboardEngine,
    compute_expected_outcome,
    compute_eta_size,
    compute_eta_token,
    compute_eta_consensus,
    compute_eta_compute,
    compute_eta_truth,
    compute_dynamic_k_factor,
    compute_elo_delta,
    compute_skill_delta,
    atomic_save_canonical_ledger,
    validate_ledger_schema,
    CANONICAL_LEADERBOARD_SCHEMA_V7,
)
from continuous_arena_router import (
    ChampionLeaderboardResolver,
    ContinuousArenaEngine,
    ContinuousArenaInferenceRouter,
    ArenaTrialRequest,
    ArenaTrialResult,
)


class TestMilestone2GraderAndELO(unittest.TestCase):
    """Comprehensive test suite for Milestone 2."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="m2_test_")
        self.temp_path = Path(self.temp_dir)
        self.leaderboard_file = self.temp_path / "data" / "canonical_ai_leaderboard.json"
        self.leaderboard_file.parent.mkdir(parents=True, exist_ok=True)
        self.lora_file = self.temp_path / "lora_datasets" / "test_lora.jsonl"
        self.lora_file.parent.mkdir(parents=True, exist_ok=True)
        self.obsidian_dir = self.temp_path / "obsidian_vault" / "01_DEBATES"
        self.obsidian_dir.mkdir(parents=True, exist_ok=True)
        self.vault_dir = self.temp_path / "model_vault_gguf"
        self.vault_dir.mkdir(parents=True, exist_ok=True)

        # Initialize test canonical leaderboard
        self.base_engine = CanonicalAILeaderboardEngine(ledger_path=self.leaderboard_file)
        self.initial_leaderboard = self.base_engine.get_canonical_leaderboard(persist=True)

    def tearDown(self):
        try:
            shutil.rmtree(self.temp_dir)
        except Exception:
            pass

    # =========================================================================
    # 1. ChallengerPoolCycler Tests
    # =========================================================================

    def test_01_challenger_pool_init_and_default_contents(self):
        """Test ChallengerPoolCycler initializes with all required models."""
        cycler = ChallengerPoolCycler()
        model_ids = [m["model_id"] for m in cycler.pool]
        
        # 100B+ titan
        self.assertIn("command_r_plus_104b", model_ids)
        # 70B abliterated
        self.assertIn("llama3_70b_abliterated", model_ids)
        self.assertIn("hermes_vision_auditor", model_ids)
        # GGUF models
        self.assertIn("mistral_nemo_12b", model_ids)
        self.assertIn("gemma_2_9b", model_ids)
        self.assertIn("qwen25_coder_7b", model_ids)
        # Cloud APIs
        self.assertIn("cloudflare_llama3_8b", model_ids)
        self.assertIn("gemini_3_1_pro", model_ids)
        self.assertIn("julien_ai_reasoner", model_ids)

    def test_02_select_challengers_excludes_champion(self):
        """Test select_challengers strictly excludes the active champion."""
        cycler = ChallengerPoolCycler()
        for champ_id in ["command_r_plus_104b", "gemini_3_1_pro", "llama3_70b_abliterated"]:
            selected = cycler.select_challengers(exclude_model_id=champ_id, count=3)
            self.assertEqual(len(selected), 3)
            for ch in selected:
                self.assertNotEqual(ch["model_id"], champ_id)

    def test_03_challenger_rotation_fairness(self):
        """Test tournament rotation cycles sequentially without repeating immediately."""
        cycler = ChallengerPoolCycler()
        s1 = cycler.select_challengers(exclude_model_id="kimi_tandem_titan", count=2)
        s2 = cycler.select_challengers(exclude_model_id="kimi_tandem_titan", count=2)
        s3 = cycler.select_challengers(exclude_model_id="kimi_tandem_titan", count=2)
        
        ids1 = [m["model_id"] for m in s1]
        ids2 = [m["model_id"] for m in s2]
        ids3 = [m["model_id"] for m in s3]
        
        self.assertNotEqual(ids1, ids2)
        self.assertNotEqual(ids2, ids3)

    def test_04_gguf_vault_scanning(self):
        """Test dynamic GGUF vault scanning and model auto-registration."""
        # Create dummy gguf files
        (self.vault_dir / "custom-llama3-70b-q4.gguf").touch()
        (self.vault_dir / "deepseek-coder-v2-16b.gguf").touch()
        
        cycler = ChallengerPoolCycler(vault_dir=self.vault_dir, auto_scan_vault=True)
        discovered = cycler.scan_gguf_vault()
        
        discovered_ids = [m["model_id"] for m in cycler.pool]
        self.assertIn("custom_llama3_70b_q4", discovered_ids)
        self.assertIn("deepseek_coder_v2_16b", discovered_ids)

    def test_05_execute_challenger_success_and_metrics(self):
        """Test synchronous challenger execution produces realistic telemetry."""
        cycler = ChallengerPoolCycler()
        spec = {"model_id": "command_r_plus_104b", "name": "Command-R+ 104B", "params_b": 104.0}
        prompt = "Write a fast matrix multiplication kernel in Metal Shading Language"
        
        res = cycler.execute_challenger(spec, prompt, timeout=10.0)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIsNone(res["error"])
        self.assertGreater(res["tokens_generated"], 0)
        self.assertGreater(res["latency_ms"], 0.0)
        self.assertIn("Command-R+ 104B", res["output"])

    def test_06_execute_challenger_timeout_boundary(self):
        """Test challenger execution times out when budget is too tight."""
        cycler = ChallengerPoolCycler()
        spec = {"model_id": "slow_titan", "name": "Slow Titan"}
        res = cycler.execute_challenger(spec, "Complex AST Task", timeout=0.01)
        self.assertEqual(res["status"], "TIMEOUT")
        self.assertIn("timeout", res["error"].lower())

    def test_07_execute_challenger_async(self):
        """Test asynchronous challenger execution via asyncio."""
        async def run_async():
            cycler = ChallengerPoolCycler()
            spec = {"model_id": "gemini_3_1_pro", "name": "Gemini 3.1 Pro"}
            res = await cycler.async_execute_challenger(spec, "Async prompt test", timeout=5.0)
            return res

        res = asyncio.run(run_async())
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["model_id"], "gemini_3_1_pro")

    def test_08_pool_status_diagnostics(self):
        """Test telemetry diagnostic reporting of candidate pool."""
        cycler = ChallengerPoolCycler()
        status = cycler.get_pool_status()
        self.assertGreater(status["total_models"], 5)
        self.assertIn("LOCAL_100B_TITAN", status["tier_distribution"])
        self.assertIn("llama_rpc", status["engine_distribution"])

    # =========================================================================
    # 2. TriOrchestratorBlindGrader / ContinuousArenaGrader Tests
    # =========================================================================

    def test_09_blind_alias_anonymization_and_header_stripping(self):
        """Test model headers are stripped and blind aliases assigned."""
        grader = ContinuousArenaGrader(
            leaderboard_path=self.leaderboard_file,
            lora_sink_path=self.lora_file,
            obsidian_sink_path=self.obsidian_dir,
            randomize_alias_order=False,
        )
        champ = {"model_id": "kimi_tandem_titan", "name": "Kimi Titan", "status": "SUCCESS", "text": "[Kimi] Solution code"}
        challengers = [
            {"model_id": "command_r_plus_104b", "name": "Command-R+", "status": "SUCCESS", "text": "[Command-R+] Solution code"},
            {"model_id": "gemini_3_1_pro", "name": "Gemini", "status": "SUCCESS", "text": "[Gemini] Solution code"},
        ]
        
        alias_map, payloads = grader._anonymize_participants(champ, challengers)
        self.assertEqual(len(alias_map), 3)
        self.assertIn("alpha", alias_map)
        self.assertIn("beta", alias_map)
        self.assertIn("gamma", alias_map)
        # Verify stripped text doesn't contain bracket prefix
        for payload in payloads.values():
            self.assertFalse(payload["text"].startswith("[Kimi]"))

    def test_10_judicial_council_5pillar_scoring(self):
        """Test 3-Judge Council computes all 5 dimensions."""
        grader = ContinuousArenaGrader(
            leaderboard_path=self.leaderboard_file,
            lora_sink_path=self.lora_file,
            obsidian_sink_path=self.obsidian_dir,
        )
        champ = {"model_id": "kimi_tandem_titan", "status": "SUCCESS", "latency_ms": 30.0, "text": "def solve(x):\n    return x * 2"}
        challengers = [
            {"model_id": "command_r_plus_104b", "status": "SUCCESS", "latency_ms": 40.0, "text": "def solve(x: int) -> int:\n    \"\"\"Docstring.\"\"\"\n    return x * 2"},
        ]
        res = grader.grade_arena_trial("Solve task", champ, challengers)
        
        for alias, score_dict in res["scores"].items():
            self.assertIn("syntax", score_dict)
            self.assertIn("depth", score_dict)
            self.assertIn("economy", score_dict)
            self.assertIn("safety", score_dict)
            self.assertIn("truth", score_dict)
            self.assertGreaterEqual(score_dict["syntax"], 0.0)
            self.assertLessEqual(score_dict["syntax"], 100.0)

    def test_11_disqualification_on_failure(self):
        """Test participant with ERROR status gets zero scores across all dimensions."""
        grader = ContinuousArenaGrader(
            leaderboard_path=self.leaderboard_file,
            lora_sink_path=self.lora_file,
            obsidian_sink_path=self.obsidian_dir,
        )
        champ = {"model_id": "good_champ", "status": "SUCCESS", "latency_ms": 20.0, "text": "valid response text here with plenty of words"}
        challengers = [{"model_id": "crashed_model", "status": "ERROR", "error": "CUDA Out of Memory", "text": ""}]
        
        res = grader.grade_arena_trial("Failure test", champ, challengers)
        crash_alias = [k for k, v in res["alias_mapping"].items() if v == "crashed_model"][0]
        self.assertEqual(res["total_scores"][crash_alias], 0.0)
        self.assertEqual(res["winner_id"], "good_champ")

    def test_12_pairwise_match_decomposition(self):
        """Test 3 participants decompose into exactly 3 pairwise duels."""
        grader = ContinuousArenaGrader(
            leaderboard_path=self.leaderboard_file,
            lora_sink_path=self.lora_file,
            obsidian_sink_path=self.obsidian_dir,
        )
        champ = {"model_id": "m1", "status": "SUCCESS", "latency_ms": 10.0, "text": "A full text answer"}
        challengers = [
            {"model_id": "m2", "status": "SUCCESS", "latency_ms": 20.0, "text": "A full text answer"},
            {"model_id": "m3", "status": "SUCCESS", "latency_ms": 30.0, "text": "A full text answer"},
        ]
        res = grader.grade_arena_trial("Pairwise test", champ, challengers)
        self.assertEqual(len(res["pairwise_matches"]), 3)
        for pm in res["pairwise_matches"]:
            self.assertIn("model_a_id", pm)
            self.assertIn("model_b_id", pm)
            self.assertIn("outcome_score", pm)

    def test_13_judicial_rationale_synthesis(self):
        """Test judicial rationale produces non-empty synthesis citing dimensions."""
        grader = ContinuousArenaGrader(
            leaderboard_path=self.leaderboard_file,
            lora_sink_path=self.lora_file,
            obsidian_sink_path=self.obsidian_dir,
        )
        champ = {"model_id": "kimi_tandem_titan", "status": "SUCCESS", "latency_ms": 25.0, "text": "Fast valid logic"}
        challengers = [{"model_id": "command_r_plus_104b", "status": "SUCCESS", "latency_ms": 35.0, "text": "Slightly slower logic"}]
        res = grader.grade_arena_trial("Rationale test", champ, challengers)
        
        self.assertTrue(len(res["judicial_rationale"]) > 20)
        self.assertIn("Tri-Orchestrator", res["judicial_rationale"])
        self.assertIn("AST syntax", res["judicial_rationale"])

    def test_14_async_grade_arena_trial(self):
        """Test asynchronous trial grading in asyncio loop."""
        async def run_async():
            grader = ContinuousArenaGrader(
                leaderboard_path=self.leaderboard_file,
                lora_sink_path=self.lora_file,
                obsidian_sink_path=self.obsidian_dir,
            )
            champ = {"model_id": "kimi_tandem_titan", "status": "SUCCESS", "latency_ms": 25.0, "text": "Async test text"}
            challengers = [{"model_id": "gemini_3_1_pro", "status": "SUCCESS", "latency_ms": 30.0, "text": "Async test text 2"}]
            return await grader.async_grade_arena_trial("Async prompt", champ, challengers)

        res = asyncio.run(run_async())
        self.assertIn("winner_id", res)
        self.assertIn("scores", res)

    # =========================================================================
    # 3. Dynamic Multi-Factor ELO Engine Tests
    # =========================================================================

    def test_15_expected_outcome_logistics(self):
        """Test logistic expected outcome formula sums to 1.0."""
        e_a, e_b = compute_expected_outcome(3000.0, 2800.0)
        self.assertAlmostEqual(e_a + e_b, 1.0, places=5)
        self.assertGreater(e_a, e_b)

    def test_16_dynamic_k_factor_multipliers(self):
        """Test dynamic K-factor scales with all 6 efficiency multipliers."""
        k = compute_dynamic_k_factor(
            base_k=32.0,
            matches_played=15,
            match_type="ARENA_DUEL",
            eta_size=1.2,
            eta_token=1.1,
            eta_consensus=0.95,
            eta_compute=1.05,
            eta_truth=1.0,
        )
        expected = 32.0 * 1.0 * 1.2 * 1.1 * 0.95 * 1.05 * 1.0
        self.assertAlmostEqual(k, round(expected, 4), places=3)

    def test_17_truth_disqualification_factor(self):
        """Test eta_truth drops to 0.0 when truth verification fails."""
        eta_clean = compute_eta_truth(truth_verified=True, truth_compliance_pct=100.0)
        eta_mock = compute_eta_truth(truth_verified=False, truth_compliance_pct=100.0)
        eta_partial = compute_eta_truth(truth_verified=True, truth_compliance_pct=95.0)
        
        self.assertEqual(eta_clean, 1.0)
        self.assertEqual(eta_mock, 0.0)
        self.assertEqual(eta_partial, 0.0)

    def test_18_atomic_save_and_schema_v7_validation(self):
        """Test atomic POSIX save preserves Schema v7 compliance."""
        engine = CanonicalAILeaderboardEngine(ledger_path=self.leaderboard_file)
        board = engine.get_canonical_leaderboard(persist=True)
        self.assertTrue(validate_ledger_schema(board))
        self.assertTrue(self.leaderboard_file.exists())

    def test_19_specialist_skill_progression(self):
        """Test specialist skill progression increases on win and decreases on loss."""
        d_win = compute_skill_delta(current_skill=85.0, score=1.0)
        d_loss = compute_skill_delta(current_skill=85.0, score=0.0)
        d_draw = compute_skill_delta(current_skill=85.0, score=0.5)
        
        self.assertGreater(d_win, 0.0)
        self.assertLess(d_loss, 0.0)
        self.assertGreater(d_draw, 0.0)

    # =========================================================================
    # 4. Dynamic Champion Promotion Tests
    # =========================================================================

    def test_20_challenger_victory_triggers_champion_promotion(self):
        """Test challenger overtaking champion ELO causes dynamic promotion."""
        engine = CanonicalAILeaderboardEngine(ledger_path=self.leaderboard_file)
        resolver = ChampionLeaderboardResolver(leaderboard_path=self.leaderboard_file, debounce_ttl_sec=0.01)
        
        # Initial champion
        initial_champ = resolver.resolve_current_champion()
        
        # Record massive win for openclaw
        match = {
            "match_id": "promo_1",
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "match_type": "ARENA_DUEL",
            "topic_or_challenge": "Promotion Trial",
            "model_a_id": "openclaw_browser_sentinel",
            "model_b_id": initial_champ["model_id"],
            "score_a": 1.0,
            "score_b": 0.0,
            "winner_id": "openclaw_browser_sentinel",
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
        }
        # Run multiple decisive matches to overtake ELO
        for _ in range(10):
            engine.record_match_victory(match)

        resolver.invalidate_cache()
        new_champ = resolver.resolve_current_champion()
        self.assertEqual(new_champ["model_id"], "openclaw_browser_sentinel")
        self.assertEqual(new_champ["rank"], 1)

    def test_21_rank_reindexing_integrity(self):
        """Test leaderboard ranks are strictly 1..N with no duplicate or missing ranks."""
        engine = CanonicalAILeaderboardEngine(ledger_path=self.leaderboard_file)
        board = engine.get_canonical_leaderboard(persist=True)
        ranks = [m["rank"] for m in board["leaderboard"]]
        self.assertEqual(ranks, list(range(1, len(ranks) + 1)))

    def test_22_champion_retains_rank_on_victory(self):
        """Test reigning champion retains rank 1 when winning matches."""
        resolver = ChampionLeaderboardResolver(leaderboard_path=self.leaderboard_file, debounce_ttl_sec=0.01)
        champ = resolver.resolve_current_champion()
        
        engine = CanonicalAILeaderboardEngine(ledger_path=self.leaderboard_file)
        engine.record_match_victory({
            "match_id": "defense_1",
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "match_type": "ARENA_DUEL",
            "topic_or_challenge": "Defense Duel",
            "model_a_id": champ["model_id"],
            "model_b_id": "hermes_vision_auditor",
            "score_a": 1.0,
            "score_b": 0.0,
            "winner_id": champ["model_id"],
            "truth_verified": True,
        })
        
        resolver.invalidate_cache()
        retained = resolver.resolve_current_champion()
        self.assertEqual(retained["model_id"], champ["model_id"])

    # =========================================================================
    # 5. Tri-Vault Harvesting Tests
    # =========================================================================

    def test_23_lora_dpo_jsonl_export(self):
        """Test trial export writes valid DPO JSONL format."""
        grader = ContinuousArenaGrader(
            leaderboard_path=self.leaderboard_file,
            lora_sink_path=self.lora_file,
            obsidian_sink_path=self.obsidian_dir,
        )
        champ = {"model_id": "kimi_tandem_titan", "status": "SUCCESS", "text": "Optimal response"}
        challengers = [{"model_id": "command_r_plus_104b", "status": "SUCCESS", "text": "Sub-optimal response"}]
        
        grader.grade_arena_trial("DPO prompt test", champ, challengers)
        
        self.assertTrue(self.lora_file.exists())
        with open(self.lora_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line.strip()) for line in f if line.strip()]
        
        self.assertGreater(len(lines), 0)
        self.assertIn("prompt", lines[0])
        self.assertIn("chosen", lines[0])
        self.assertIn("rejected", lines[0])
        self.assertIn("meta", lines[0])

    def test_24_obsidian_markdown_transcript_export(self):
        """Test trial export creates Obsidian note with Wikilinks and frontmatter."""
        grader = ContinuousArenaGrader(
            leaderboard_path=self.leaderboard_file,
            lora_sink_path=self.lora_file,
            obsidian_sink_path=self.obsidian_dir,
        )
        champ = {"model_id": "kimi_tandem_titan", "status": "SUCCESS", "text": "Obsidian test response"}
        challengers = [{"model_id": "gemini_3_1_pro", "status": "SUCCESS", "text": "Obsidian challenger response"}]
        
        trial = grader.grade_arena_trial("Obsidian prompt test", champ, challengers)
        
        note_files = list(self.obsidian_dir.glob("ARENA_TRIAL_*.md"))
        self.assertGreater(len(note_files), 0)
        
        content = note_files[0].read_text(encoding="utf-8")
        self.assertIn("---", content)
        self.assertIn("tags: [arena, debate, tri_orchestrator, lora, zero_mock]", content)
        self.assertIn("[[CANONICAL_PROJECT_AND_STORAGE_RULE]]", content)
        self.assertIn("[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]", content)

    # =========================================================================
    # 6. ContinuousArenaEngine & Router Integration Tests
    # =========================================================================

    def test_25_engine_wires_cycler_and_grader_by_default(self):
        """Test ContinuousArenaEngine auto-instantiates ChallengerPoolCycler and ContinuousArenaGrader."""
        engine = ContinuousArenaEngine()
        self.assertIsNotNone(engine.challenger_cycler)
        self.assertIsNotNone(engine.grader)
        self.assertIsInstance(engine.challenger_cycler, ChallengerPoolCycler)
        self.assertIsInstance(engine.grader, ContinuousArenaGrader)

    def test_26_full_trial_queue_and_callback_flow(self):
        """Test full asynchronous queue processing, challenger execution, and grading callback."""
        async def run_flow():
            completed_results: List[ArenaTrialResult] = []

            def on_done(res: ArenaTrialResult):
                completed_results.append(res)

            engine = ContinuousArenaEngine(
                queue_maxsize=10,
                default_timeout=5.0,
                idle_timeout=0.1,
                on_trial_complete=on_done,
            )
            engine.start()

            champ_result = {
                "model_id": "kimi_tandem_titan",
                "name": "Kimi Titan",
                "status": "SUCCESS",
                "latency_ms": 25.0,
                "text": "Champion solution response",
            }

            enqueued = engine.enqueue_trial(
                prompt="Write a test for continuous arena engine",
                champion_result=champ_result,
            )
            self.assertTrue(enqueued)

            # Wait for background queue processing
            for _ in range(50):
                if len(completed_results) > 0:
                    break
                await asyncio.sleep(0.05)

            await engine.stop(wait=True, timeout=2.0)
            return completed_results

        results = asyncio.run(run_flow())
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "COMPLETED")
        self.assertEqual(len(results[0].challenger_results), 2)
        self.assertIsNotNone(results[0].grading_result)
        self.assertIn("winner_id", results[0].grading_result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
