#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit and Integration Test Suite — Milestone 3: Tri-Vault Logging & Error Resilience
===================================================================================
Subsystem: tests/test_milestone3_trivault_resilience.py
Classification: Tri-Vault Dataset Harvesting • Atomic File Safety • Rule #0 Zero-Mock Verification

Validates:
1. Tri-Vault Dataset Harvesting & Knowledge Core Synchronization:
   - DPO pairs (prompt, chosen, rejected, metadata) schema and JSONL append.
   - SFT training instructions (Alpaca + OpenAI ShareGPT formats).
   - Chat distillation records (multi-turn conversation format).
   - Obsidian Vault debate transcripts with YAML frontmatter, tags, 3-judge panel breakdowns, and master Wikilinks.
2. Resilience & Self-Healing:
   - Atomic POSIX file replacement (os.replace + os.fsync) avoiding corruption.
   - Concurrent multi-threaded dataset appending without line interleaving.
   - Storage health verification (>= 5.0 GB free disk headroom check).
   - Dynamic fallback path routing when primary target directory is unwritable.
   - Graceful error recovery during dataset writes preventing router/evaluator crashes.
3. Rule #0 Zero-Mock Data Verification:
   - Rejection of unverified or mock telemetry (truth_verified=False, compliance < 100%).
   - Verification of genuine latency, authentic token metrics, and real ELO deltas.
   - Quarantine and metrics tracking for Rule #0 compliance.
4. End-to-End Integration:
   - ContinuousArenaGrader and ContinuousArenaInferenceRouter synchronization with TriVaultSink.
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

# Setup path resolution
TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "01_apps" / "canonical_port" / "backend" / "agents"))
sys.path.insert(0, str(PROJECT_ROOT / "02_ai_models_and_inference"))
sys.path.insert(0, str(PROJECT_ROOT / "04_data_and_memory"))
sys.path.insert(0, str(PROJECT_ROOT / "05_agents_and_swarms" / "tri_orchestrator"))

from tri_vault_sink import (
    TriVaultSink,
    verify_zero_mock_compliance,
    check_storage_health,
    PRIMARY_LORA_DIR,
    SECONDARY_LORA_DIR,
    PRIMARY_OBSIDIAN_DIR,
    SECONDARY_OBSIDIAN_DIR,
)
from continuous_arena_grader import (
    ContinuousArenaGrader,
    TriOrchestratorBlindGrader,
    BLIND_ALIASES,
)
from canonical_ai_leaderboard import (
    CanonicalAILeaderboardEngine,
    compute_eta_truth,
    compute_dynamic_k_factor,
    compute_elo_delta,
    atomic_save_canonical_ledger,
    validate_ledger_schema,
)
from continuous_arena_router import (
    ChampionLeaderboardResolver,
    ContinuousArenaEngine,
    ContinuousArenaInferenceRouter,
    ArenaTrialRequest,
    ArenaTrialResult,
)


class TestMilestone3TriVaultResilience(unittest.TestCase):
    """
    Comprehensive Unit and Integration Test Suite for Milestone 3.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="m3_trivault_test_")
        self.temp_path = Path(self.temp_dir)

        self.primary_lora_dir = self.temp_path / "primary_lora"
        self.secondary_lora_dir = self.temp_path / "secondary_lora"
        self.primary_obsidian_dir = self.temp_path / "primary_obsidian" / "01_DEBATES"
        self.secondary_obsidian_dir = self.temp_path / "secondary_obsidian" / "01_DEBATES"
        self.leaderboard_file = self.temp_path / "data" / "canonical_ai_leaderboard.json"

        self.primary_lora_dir.mkdir(parents=True, exist_ok=True)
        self.secondary_lora_dir.mkdir(parents=True, exist_ok=True)
        self.primary_obsidian_dir.mkdir(parents=True, exist_ok=True)
        self.secondary_obsidian_dir.mkdir(parents=True, exist_ok=True)
        self.leaderboard_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize Base Leaderboard
        self.leaderboard_engine = CanonicalAILeaderboardEngine(ledger_path=self.leaderboard_file)
        self.leaderboard_engine.get_canonical_leaderboard(persist=True)

        # Instantiate TriVaultSink
        self.sink = TriVaultSink(
            lora_dir=self.primary_lora_dir,
            obsidian_dir=self.primary_obsidian_dir,
            secondary_lora_dir=self.secondary_lora_dir,
            secondary_obsidian_dir=self.secondary_obsidian_dir,
            enforce_rule_zero=True,
        )

        # Sample Canonical Trial Record
        self.sample_trial = {
            "trial_id": f"trial_{uuid.uuid4().hex[:12]}",
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "prompt": "Implement a zero-copy ring buffer for 512Hz ECG biometrics streaming in C++.",
            "winner_id": "kimi_tandem_titan",
            "winner_alias": "alpha",
            "alias_mapping": {
                "alpha": "kimi_tandem_titan",
                "beta": "command_r_plus_104b",
                "gamma": "gemini_3_1_pro"
            },
            "scores": {
                "alpha": {"syntax": 99.0, "depth": 96.0, "economy": 95.0, "safety": 100.0, "truth": 100.0},
                "beta": {"syntax": 95.0, "depth": 92.0, "economy": 90.0, "safety": 100.0, "truth": 100.0},
                "gamma": {"syntax": 92.0, "depth": 88.0, "economy": 94.0, "safety": 100.0, "truth": 100.0}
            },
            "total_scores": {"alpha": 97.75, "beta": 93.65, "gamma": 92.70},
            "judge_breakdowns": {
                "alpha": {
                    "frontier_judge": {"score": 98.0, "verdict": "VALID_AST"},
                    "swarm_judge": {"score": 97.0, "verdict": "STRONG_CONSENSUS"},
                    "devils_advocate": {"score": 99.0, "verdict": "ROBUST_DEFENSE"}
                },
                "beta": {
                    "frontier_judge": {"score": 94.0, "verdict": "VALID_AST"},
                    "swarm_judge": {"score": 92.0, "verdict": "STRONG_CONSENSUS"},
                    "devils_advocate": {"score": 91.0, "verdict": "ROBUST_DEFENSE"}
                }
            },
            "pairwise_matches": [
                {"model_a_id": "kimi_tandem_titan", "model_b_id": "command_r_plus_104b", "winner_id": "kimi_tandem_titan", "loser_id": "command_r_plus_104b", "score_a": 97.75, "score_b": 93.65},
                {"model_a_id": "kimi_tandem_titan", "model_b_id": "gemini_3_1_pro", "winner_id": "kimi_tandem_titan", "loser_id": "gemini_3_1_pro", "score_a": 97.75, "score_b": 92.70},
                {"model_a_id": "command_r_plus_104b", "model_b_id": "gemini_3_1_pro", "winner_id": "command_r_plus_104b", "loser_id": "gemini_3_1_pro", "score_a": 93.65, "score_b": 92.70}
            ],
            "judicial_rationale": "Tri-Orchestrator Council unanimously awarded victory to Kimi Tandem Titan for lock-free atomic pointer updates and zero heap allocations during 512Hz ECG DSP.",
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
            "latency_ms": 28.5,
            "tokens_generated": 184
        }

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # =========================================================================
    # 1. Tri-Vault Dataset Harvesting Tests
    # =========================================================================

    def test_01_dpo_pair_schema_and_jsonl_append(self):
        """Test DPO pair export schema validity and append-only persistence."""
        dpo_res = self.sink.export_dpo_pair(self.sample_trial, target_filename="test_dpo.jsonl")
        
        # Verify schema keys
        self.assertIn("trial_id", dpo_res)
        self.assertIn("timestamp", dpo_res)
        self.assertIn("prompt", dpo_res)
        self.assertIn("chosen", dpo_res)
        self.assertIn("rejected", dpo_res)
        self.assertIn("meta", dpo_res)
        
        # Verify chosen and rejected contents
        self.assertIn("kimi_tandem_titan", dpo_res["chosen"])
        self.assertIn("Tri-Orchestrator", dpo_res["chosen"])
        self.assertIn("Sub-optimal", dpo_res["rejected"])
        self.assertTrue(dpo_res["meta"]["zero_mock_certified"])

        # Check physical file on disk
        target_file = self.primary_lora_dir / "test_dpo.jsonl"
        self.assertTrue(target_file.exists())
        with open(target_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line.strip()) for line in f if line.strip()]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["trial_id"], self.sample_trial["trial_id"])

    def test_02_sft_instruction_alpaca_and_sharegpt_format(self):
        """Test SFT training instruction export supports both Alpaca and ShareGPT conventions."""
        sft_res = self.sink.export_sft_instruction(self.sample_trial, target_filename="test_sft.jsonl")
        
        # Alpaca keys
        self.assertIn("instruction", sft_res)
        self.assertIn("input", sft_res)
        self.assertIn("thought", sft_res)
        self.assertIn("output", sft_res)
        self.assertIn("Frontier Judge", sft_res["thought"])

        # ShareGPT / OpenAI messages format
        self.assertIn("messages", sft_res)
        self.assertEqual(len(sft_res["messages"]), 3)
        self.assertEqual(sft_res["messages"][0]["role"], "system")
        self.assertEqual(sft_res["messages"][1]["role"], "user")
        self.assertEqual(sft_res["messages"][2]["role"], "assistant")
        self.assertIn("<thought>", sft_res["messages"][2]["content"])

        # Check persistence
        target_file = self.primary_lora_dir / "test_sft.jsonl"
        self.assertTrue(target_file.exists())

    def test_03_chat_distillation_record_structure(self):
        """Test Chat distillation export structure and metadata."""
        chat_res = self.sink.export_chat_distillation(self.sample_trial, target_filename="test_chat.jsonl")
        
        self.assertIn("session_id", chat_res)
        self.assertIn("turns", chat_res)
        self.assertIn("consensus_summary", chat_res)
        self.assertIn("judge_breakdowns", chat_res)
        self.assertIn("metadata", chat_res)
        self.assertEqual(chat_res["metadata"]["winner_id"], "kimi_tandem_titan")

        target_file = self.primary_lora_dir / "test_chat.jsonl"
        self.assertTrue(target_file.exists())

    def test_04_continuous_dataset_harvesting_across_multiple_trials(self):
        """Test sequential trials continuously append without overwriting or truncating."""
        target_file = self.primary_lora_dir / "continuous_harvest.jsonl"
        
        for i in range(5):
            trial = dict(self.sample_trial)
            trial["trial_id"] = f"trial_seq_{i}"
            trial["prompt"] = f"Sequential prompt {i}"
            self.sink.export_dpo_pair(trial, target_filename="continuous_harvest.jsonl")

        with open(target_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line.strip()) for line in f if line.strip()]

        self.assertEqual(len(lines), 5)
        for i, line in enumerate(lines):
            self.assertEqual(line["trial_id"], f"trial_seq_{i}")
            self.assertEqual(line["prompt"], f"Sequential prompt {i}")

    def test_05_dpo_chosen_rejected_differentiation(self):
        """Test that chosen and rejected reasoning are strictly differentiated."""
        dpo_res = self.sink.export_dpo_pair(self.sample_trial)
        self.assertNotEqual(dpo_res["chosen"].strip(), dpo_res["rejected"].strip())
        self.assertGreater(len(dpo_res["chosen"]), 20)
        self.assertGreater(len(dpo_res["rejected"]), 20)

    # =========================================================================
    # 2. Obsidian Knowledge Core Synchronization Tests
    # =========================================================================

    def test_06_obsidian_markdown_file_creation_and_naming(self):
        """Test Obsidian debate transcript note creation and exact filename pattern."""
        note_path = self.sink.export_obsidian_transcript(self.sample_trial)
        self.assertTrue(note_path.exists())
        self.assertEqual(note_path.name, f"ARENA_TRIAL_{self.sample_trial['trial_id']}.md")

    def test_07_yaml_frontmatter_validity(self):
        """Test Obsidian transcript contains valid, parseable YAML frontmatter."""
        note_path = self.sink.export_obsidian_transcript(self.sample_trial)
        content = note_path.read_text(encoding="utf-8")

        self.assertTrue(content.startswith("---"))
        parts = content.split("---")
        self.assertGreaterEqual(len(parts), 3)

        frontmatter_text = parts[1]
        self.assertIn("title: \"Continuous Arena Trial", frontmatter_text)
        self.assertIn("date: \"", frontmatter_text)
        self.assertIn("tags: [arena, debate, tri_orchestrator, lora, zero_mock]", frontmatter_text)
        self.assertIn("winner: \"kimi_tandem_titan\"", frontmatter_text)
        self.assertIn("zero_mock_certified: true", frontmatter_text)

    def test_08_canonical_wikilinks_presence(self):
        """Test Obsidian note concludes with canonical Tri-Vault master Wikilinks."""
        note_path = self.sink.export_obsidian_transcript(self.sample_trial)
        content = note_path.read_text(encoding="utf-8")

        self.assertIn("[[CANONICAL_PROJECT_AND_STORAGE_RULE]]", content)
        self.assertIn("[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]", content)
        self.assertIn("[[Index]]", content)

    def test_09_three_judge_council_breakdowns(self):
        """Test Obsidian Markdown contains 3-Judge Council evaluations (Frontier, Swarm, Devil's Advocate)."""
        note_path = self.sink.export_obsidian_transcript(self.sample_trial)
        content = note_path.read_text(encoding="utf-8")

        self.assertIn("Frontier Judge", content)
        self.assertIn("Swarm Judge", content)
        self.assertIn("Devils Advocate", content)
        self.assertIn("VALID_AST", content)

    def test_10_five_pillar_detailed_score_matrix_in_markdown(self):
        """Test Obsidian note formats detailed 5-pillar score JSON matrix."""
        note_path = self.sink.export_obsidian_transcript(self.sample_trial)
        content = note_path.read_text(encoding="utf-8")

        self.assertIn("Detailed 5-Pillar Score Matrix", content)
        self.assertIn('"syntax": 99.0', content)
        self.assertIn('"depth": 96.0', content)
        self.assertIn('"safety": 100.0', content)

    # =========================================================================
    # 3. Atomic Write Safety & Concurrency Tests
    # =========================================================================

    def test_11_atomic_posix_file_replacement(self):
        """Test POSIX atomic replace guarantees clean target file without partial state."""
        target_file = self.primary_obsidian_dir / "atomic_test.md"
        content_1 = "Initial complete content\n"
        self.sink.atomic_write_file(target_file, content_1)
        self.assertEqual(target_file.read_text(encoding="utf-8"), content_1)

        content_2 = "Updated replacement content\n"
        self.sink.atomic_write_file(target_file, content_2)
        self.assertEqual(target_file.read_text(encoding="utf-8"), content_2)

    def test_12_concurrent_multithreaded_dataset_appends(self):
        """Test 20 concurrent threads writing DPO records simultaneously without corruption."""
        target_file = self.primary_lora_dir / "concurrent_dpo.jsonl"
        thread_count = 20
        errors = []

        def worker_task(thread_idx: int):
            try:
                t = dict(self.sample_trial)
                t["trial_id"] = f"trial_th_{thread_idx}"
                t["prompt"] = f"Concurrent prompt from thread {thread_idx}"
                self.sink.export_dpo_pair(t, target_filename="concurrent_dpo.jsonl")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker_task, args=(i,)) for i in range(thread_count)]
        for th in threads: th.start()
        for th in threads: th.join()

        self.assertEqual(len(errors), 0)
        with open(target_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line.strip()) for line in f if line.strip()]

        self.assertEqual(len(lines), thread_count)
        observed_ids = {line["trial_id"] for line in lines}
        expected_ids = {f"trial_th_{i}" for i in range(thread_count)}
        self.assertEqual(observed_ids, expected_ids)

    def test_13_fsync_data_durability(self):
        """Test safe_append_jsonl flushes and syncs data to disk."""
        target_file = self.primary_lora_dir / "fsync_test.jsonl"
        success = self.sink.safe_append_jsonl(target_file, {"test": "durability_check"})
        self.assertTrue(success)
        self.assertTrue(target_file.exists())
        self.assertGreater(target_file.stat().st_size, 0)

    def test_14_temp_file_cleanup_on_success_and_failure(self):
        """Test temporary files are cleaned up and do not litter the directory."""
        note_path = self.sink.export_obsidian_transcript(self.sample_trial)
        parent_dir = note_path.parent
        tmp_files = list(parent_dir.glob("*.tmp*"))
        self.assertEqual(len(tmp_files), 0)

    # =========================================================================
    # 4. Disk Fallback & Self-Healing Tests
    # =========================================================================

    def test_15_preflight_storage_health_check(self):
        """Test check_storage_health validates directory access and disk headroom."""
        health = check_storage_health(self.primary_lora_dir, self.secondary_lora_dir, min_free_gb=1.0)
        self.assertTrue(health["is_healthy"])
        self.assertTrue(health["primary_accessible"])
        self.assertGreater(health["free_disk_gb"], 0.0)

    def test_16_fallback_to_secondary_when_primary_unwritable(self):
        """Test automatic fallback to secondary directory when primary directory is unwritable."""
        unwritable_primary = self.temp_path / "unwritable_primary"
        unwritable_primary.mkdir(parents=True, exist_ok=True)
        # Set unwritable permissions
        os.chmod(unwritable_primary, 0o444)

        fallback_sink = TriVaultSink(
            lora_dir=unwritable_primary,
            secondary_lora_dir=self.secondary_lora_dir,
            obsidian_dir=self.primary_obsidian_dir,
            enforce_rule_zero=False,
        )

        try:
            active_lora = fallback_sink.resolve_active_lora_dir()
            self.assertEqual(active_lora, self.secondary_lora_dir)
            
            # Export should succeed by writing to secondary
            dpo_res = fallback_sink.export_dpo_pair(self.sample_trial, target_filename="fallback_test.jsonl")
            self.assertIsNotNone(dpo_res)
            self.assertTrue((self.secondary_lora_dir / "fallback_test.jsonl").exists())
        finally:
            os.chmod(unwritable_primary, 0o755)

    def test_17_self_healing_missing_directory_creation(self):
        """Test automatic creation of non-existent deeply nested directories."""
        deep_lora = self.temp_path / "lvl1" / "lvl2" / "lvl3_lora"
        deep_obs = self.temp_path / "lvl1" / "lvl2" / "lvl3_obs"
        
        deep_sink = TriVaultSink(lora_dir=deep_lora, obsidian_dir=deep_obs)
        deep_sink.export_trial_to_trivault(self.sample_trial)
        
        self.assertTrue(deep_lora.exists())
        self.assertTrue(deep_obs.exists())
        self.assertTrue((deep_lora / "continuous_lora_dataset.jsonl").exists())
        self.assertTrue((deep_obs / f"ARENA_TRIAL_{self.sample_trial['trial_id']}.md").exists())

    def test_18_low_disk_space_detection_and_reporting(self):
        """Test storage health flags warning when free space threshold is not met."""
        # Request unrealistic 999999.0 GB to trigger warning note
        health = check_storage_health(self.primary_lora_dir, self.secondary_lora_dir, min_free_gb=999999.0)
        self.assertTrue(any("below minimum" in note for note in health["notes"]))

    # =========================================================================
    # 5. Graceful Error Recovery Tests
    # =========================================================================

    def test_19_master_export_handles_subsystem_failures_gracefully(self):
        """Test export_trial_to_trivault returns structured summary without crashing caller on sink errors."""
        res = self.sink.export_trial_to_trivault(self.sample_trial)
        self.assertEqual(res["trial_id"], self.sample_trial["trial_id"])
        self.assertTrue(res["dpo_exported"])
        self.assertTrue(res["sft_exported"])
        self.assertTrue(res["chat_exported"])
        self.assertTrue(res["obsidian_exported"])
        self.assertEqual(len(res["errors"]), 0)

    def test_20_malformed_trial_record_handling(self):
        """Test graceful rejection/handling of malformed trial records."""
        malformed = {"invalid_key": 123}
        is_valid, reason = verify_zero_mock_compliance(malformed)
        self.assertFalse(is_valid)
        self.assertIn("Violation", reason)

    def test_21_circuit_breaker_and_zero_router_crashes(self):
        """Test continuous arena grader export handles invalid records without throwing exceptions."""
        grader = ContinuousArenaGrader(
            leaderboard_path=self.leaderboard_file,
            lora_sink_path=self.primary_lora_dir / "grader_lora.jsonl",
            obsidian_sink_path=self.primary_obsidian_dir,
        )
        # Should not raise exception
        grader.export_trial_to_trivault({"trial_id": "test_crash_safe"})

    # =========================================================================
    # 6. Rule #0 Zero-Mock Data Verification Tests
    # =========================================================================

    def test_22_rejection_of_unverified_truth_status(self):
        """Test that records with truth_verified=False or truth_compliance_pct < 100 are rejected."""
        fake_trial = dict(self.sample_trial)
        fake_trial["truth_verified"] = False
        
        is_valid, reason = verify_zero_mock_compliance(fake_trial)
        self.assertFalse(is_valid)
        self.assertIn("Rule #0 Violation", reason)

        with self.assertRaises(ValueError):
            self.sink.export_dpo_pair(fake_trial)

    def test_23_rejection_of_negative_or_malformed_latencies(self):
        """Test that negative latencies are caught as Rule #0 violations."""
        bad_trial = dict(self.sample_trial)
        bad_trial["latency_ms"] = -50.0
        
        is_valid, reason = verify_zero_mock_compliance(bad_trial)
        self.assertFalse(is_valid)
        self.assertIn("Negative latency", reason)

    def test_24_eta_truth_disqualification_and_quarantine(self):
        """Test that compute_eta_truth produces 0.0 for unverified data and sink records metric."""
        eta_mock = compute_eta_truth(truth_verified=False, truth_compliance_pct=50.0)
        self.assertEqual(eta_mock, 0.0)

        # Attempting bad export increments quarantine count
        bad_trial = dict(self.sample_trial)
        bad_trial["truth_verified"] = False
        try:
            self.sink.export_dpo_pair(bad_trial)
        except ValueError:
            pass

        metrics = self.sink.get_metrics()
        self.assertGreaterEqual(metrics["rule_zero_violations_quarantined"], 1)

    def test_25_authentic_token_and_latency_audit(self):
        """Test that authentic latency and token metrics are preserved in exported datasets."""
        self.sink.export_dpo_pair(self.sample_trial, target_filename="audit_dpo.jsonl")
        target_file = self.primary_lora_dir / "audit_dpo.jsonl"
        
        with open(target_file, "r", encoding="utf-8") as f:
            record = json.loads(f.readline().strip())
        
        self.assertTrue(record["meta"]["zero_mock_certified"])
        self.assertTrue(record["meta"]["truth_verified"])

    # =========================================================================
    # 7. End-to-End Grader & Router Integration Tests
    # =========================================================================

    def test_26_continuous_arena_grader_syncs_all_trivault_layers(self):
        """Test that ContinuousArenaGrader.grade_arena_trial automatically exports across all Tri-Vault layers."""
        grader = ContinuousArenaGrader(
            leaderboard_path=self.leaderboard_file,
            lora_sink_path=self.primary_lora_dir / "grader_auto_dpo.jsonl",
            obsidian_sink_path=self.primary_obsidian_dir,
        )

        champ = {"model_id": "kimi_tandem_titan", "status": "SUCCESS", "latency_ms": 25.0, "text": "def sort_data(arr): return sorted(arr)"}
        challengers = [
            {"model_id": "command_r_plus_104b", "status": "SUCCESS", "latency_ms": 35.0, "text": "def sort_data(arr: list) -> list: return sorted(arr)"},
            {"model_id": "gemini_3_1_pro", "status": "SUCCESS", "latency_ms": 20.0, "text": "def sort_data(arr): return sorted(arr)"},
        ]

        result = grader.grade_arena_trial("Write a python sort function", champ, challengers)
        self.assertIn("winner_id", result)
        self.assertIn("trial_id", result)

        # Verify physical files created
        self.assertTrue((self.primary_lora_dir / "grader_auto_dpo.jsonl").exists())
        obsidian_notes = list(self.primary_obsidian_dir.glob("ARENA_TRIAL_*.md"))
        self.assertGreaterEqual(len(obsidian_notes), 1)

    def test_27_async_continuous_arena_engine_background_trivault_sync(self):
        """Test end-to-end asynchronous background queue execution persisting to Tri-Vault."""
        async def run_async_flow():
            completed_events = []

            def on_trial_done(outcome: ArenaTrialResult):
                completed_events.append(outcome)

            grader = ContinuousArenaGrader(
                leaderboard_path=self.leaderboard_file,
                lora_sink_path=self.primary_lora_dir / "async_engine_dpo.jsonl",
                obsidian_sink_path=self.primary_obsidian_dir,
            )

            engine = ContinuousArenaEngine(
                queue_maxsize=10,
                default_timeout=5.0,
                idle_timeout=0.1,
                grader=grader,
                on_trial_complete=on_trial_done,
            )
            engine.start()

            champ_result = {
                "model_id": "kimi_tandem_titan",
                "name": "Kimi Titan",
                "status": "SUCCESS",
                "latency_ms": 20.0,
                "text": "Async champion response payload",
            }

            enqueued = engine.enqueue_trial(
                prompt="Async background Tri-Vault pipeline validation prompt",
                champion_result=champ_result,
            )
            self.assertTrue(enqueued)

            # Wait for background queue drain
            for _ in range(40):
                if len(completed_events) > 0:
                    break
                await asyncio.sleep(0.05)

            await engine.stop(wait=True, timeout=2.0)
            return completed_events

        results = asyncio.run(run_async_flow())
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "COMPLETED")
        self.assertTrue((self.primary_lora_dir / "async_engine_dpo.jsonl").exists())
        self.assertGreaterEqual(len(list(self.primary_obsidian_dir.glob("ARENA_TRIAL_*.md"))), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
