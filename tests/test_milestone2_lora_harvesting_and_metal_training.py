#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Milestone 2 (M2) Comprehensive Verification Suite
=================================================
Tests:
1. Multi-Stream LoRA Harvesting & Interface Contracts (tri_vault_sink.py & continuous_training_debate_daemon.py)
   - verify_zero_mock_compliance (Rule #0 Zero-Mock validation, zero dummy arrays, negative latencies)
   - append_verified_pair & get_daily_verified_count
   - Daily dataset growth >= 500 verified pairs in ai_training_game_dataset.jsonl
   - 5 Streams: Debate Transcripts, Code Diffs, Math Proofs, Recovery Actions, Training Games
2. Apple Silicon Metal QLoRA Distillation & Dynamic RAM Governance (fast_train_agentworld_mac.py)
   - Dynamic AI VRAM Cap <= 21.6GB (90% limit on M4 Pro 24GB)
   - Closed-form RAM safety headroom proof (Headroom >= 2.50GB)
   - MLX and PyTorch MPS training plan verification
3. Loss Curve Streaming to Obsidian Vault
   - Real-time updates to obsidian_vault/04_ANALYTICS/QWEN_MATH_CONTINUOUS_OPTIMIZATION_TRENDS_2026.md
   - Mathematical inverse-variance latency formulas & loss decay curves
4. Autonomous MergeKit Model Weight Merging (autonomous_consensus_merger.py)
   - High confidence (> 0.95) -> TRIGGERED, generates recipe and offspring, strictly preserves parent models
   - Low confidence (<= 0.95) -> REJECTED, generates zero offspring or recipe files
"""

import os
import sys
import json
import time
import shutil
import tempfile
import unittest
from pathlib import Path

# Path setup
TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "04_data_and_memory"))
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling" / "training"))

from tri_vault_sink import (
    TriVaultSink,
    append_verified_pair,
    get_daily_verified_count,
    stream_loss_to_obsidian,
    verify_zero_mock_compliance,
)
from continuous_training_debate_daemon import (
    ContinuousTrainingDebateDaemon,
    DEBATE_TOPICS,
    CODE_DIFF_TOPICS,
    MATH_PROOF_TOPICS,
    RECOVERY_ACTION_TOPICS,
    TRAINING_GAME_TOPICS,
)
from fast_train_agentworld_mac import (
    check_hardware_capabilities,
    check_dynamic_ram_governance,
    prepare_training_dataset,
    run_mlx_qlora_training,
    run_mps_qlora_training,
    stream_training_loss_to_obsidian,
)
from autonomous_consensus_merger import (
    AutonomousConsensusMergeEngine,
    calculate_consensus_score,
    evaluate_and_trigger_merge,
    CONSENSUS_THRESHOLD,
)


class TestMilestone2HarvestingAndTraining(unittest.TestCase):
    """Full verification suite for Milestone 2 deliverables."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="lauburu_m2_test_")
        self.temp_path = Path(self.temp_dir)
        self.test_dataset = self.temp_path / "test_ai_training_game_dataset.jsonl"
        self.test_obsidian = self.temp_path / "test_trends.md"

        self.sink = TriVaultSink(
            lora_dir=self.temp_path / "lora",
            obsidian_dir=self.temp_path / "obsidian",
            enforce_rule_zero=True
        )
        self.daemon = ContinuousTrainingDebateDaemon(
            workspace_root=REPO_ROOT,
            target_dataset=self.test_dataset,
            tri_vault_sink=self.sink
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -----------------------------------------------------------------------
    # 1. Rule #0 Zero-Mock Data Validation Tests
    # -----------------------------------------------------------------------
    def test_01_rule_zero_validates_genuine_record(self):
        """Test that genuine, verified records pass Rule #0 validation with 100% compliance."""
        record = {
            "instruction": "Explain Pan-Tompkins 512Hz QRS detection filter pipeline.",
            "input": "Raw Movesense ECG telemetry at 512Hz",
            "output": "Cascaded low-pass and high-pass bandpass filter (5-15Hz) followed by derivative and squaring.",
            "chosen_response": "Cascaded low-pass and high-pass bandpass filter (5-15Hz)",
            "rejected_response": "Unfiltered raw signal thresholding",
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
            "zero_mock": True,
            "latency_ms": 24.5,
            "tokens_generated": 150
        }
        is_valid, reason = verify_zero_mock_compliance(record)
        self.assertTrue(is_valid, f"Expected valid record, got error: {reason}")
        self.assertIn("100% Certified Empirical", reason)

    def test_02_rule_zero_rejects_unverified_flag(self):
        """Test that records marked truth_verified=False or zero_mock=False are rejected."""
        record_unverified = {
            "instruction": "Task",
            "output": "Result",
            "truth_verified": False,
            "truth_compliance_pct": 100.0
        }
        is_valid, reason = verify_zero_mock_compliance(record_unverified)
        self.assertFalse(is_valid)
        self.assertIn("Rule #0 Violation", reason)

        record_fake = {
            "instruction": "Task",
            "output": "Result",
            "zero_mock": False
        }
        is_valid, reason = verify_zero_mock_compliance(record_fake)
        self.assertFalse(is_valid)
        self.assertIn("Rule #0 Violation", reason)

    def test_03_rule_zero_rejects_sub_100_compliance(self):
        """Test that truth_compliance_pct < 100.0 is rejected."""
        record = {
            "instruction": "Task",
            "output": "Result",
            "truth_compliance_pct": 99.5
        }
        is_valid, reason = verify_zero_mock_compliance(record)
        self.assertFalse(is_valid)
        self.assertIn("Truth compliance is 99.5%", reason)

    def test_04_rule_zero_rejects_negative_metrics_and_dummy_arrays(self):
        """Test that negative latencies and dummy zero arrays are rejected."""
        neg_lat = {
            "instruction": "Task",
            "output": "Result",
            "latency_ms": -10.0
        }
        is_valid, reason = verify_zero_mock_compliance(neg_lat)
        self.assertFalse(is_valid)
        self.assertIn("Negative latency", reason)

        dummy_arr = {
            "instruction": "Task",
            "output": "Result",
            "ecg_data": [0, 0, 0, 0, 0]
        }
        is_valid, reason = verify_zero_mock_compliance(dummy_arr)
        self.assertFalse(is_valid)
        self.assertIn("Dummy zero array", reason)

    # -----------------------------------------------------------------------
    # 2. Multi-Stream Harvesting & Interface Contract Tests
    # -----------------------------------------------------------------------
    def test_05_append_verified_pair_contract(self):
        """Test append_verified_pair interface contract on tri_vault_sink."""
        pair = {
            "instruction": "Optimize AST cyclomatic complexity",
            "input": "def foo(): pass",
            "output": "def foo(): return 42",
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
            "zero_mock": True
        }
        res = self.sink.append_verified_pair(self.test_dataset, pair)
        self.assertTrue(res)
        self.assertTrue(self.test_dataset.exists())

        # Bad pair must raise ValueError
        bad_pair = dict(pair)
        bad_pair["truth_verified"] = False
        with self.assertRaises(ValueError):
            self.sink.append_verified_pair(self.test_dataset, bad_pair)

    def test_06_get_daily_verified_count_contract(self):
        """Test get_daily_verified_count calculates correct valid entries added in last 24h."""
        for i in range(15):
            pair = {
                "timestamp": time.time(),
                "instruction": f"Instruction {i}",
                "output": f"Output {i}",
                "truth_verified": True,
                "truth_compliance_pct": 100.0,
                "zero_mock": True
            }
            self.sink.append_verified_pair(self.test_dataset, pair)

        count = self.sink.get_daily_verified_count(self.test_dataset)
        self.assertEqual(count, 15)

    def test_07_harvest_all_five_streams(self):
        """Test harvesting across all 5 streams produces compliant records."""
        rec_debate = self.daemon.harvest_debate_stream(idx=0)
        self.assertEqual(rec_debate["domain"], "tri_orchestrator_debate")
        self.assertTrue(rec_debate["truth_verified"])

        rec_diff = self.daemon.harvest_code_diff_stream(idx=0)
        self.assertEqual(rec_diff["domain"], "code_refactor_ast_diff")
        self.assertTrue(rec_diff["truth_verified"])

        rec_math = self.daemon.harvest_math_proof_stream(idx=0)
        self.assertEqual(rec_math["domain"], "mathematical_proof_derivation")
        self.assertTrue(rec_math["truth_verified"])

        rec_recov = self.daemon.harvest_recovery_action_stream(idx=0)
        self.assertEqual(rec_recov["domain"], "autonomic_recovery_self_healing")
        self.assertTrue(rec_recov["truth_verified"])

        rec_game = self.daemon.harvest_training_game_stream(idx=0)
        self.assertTrue(rec_game["truth_verified"])

        stats = self.daemon.get_dataset_stats()
        self.assertEqual(stats["total_pairs"], 5)
        self.assertEqual(stats["verified_24h_pairs"], 5)

    def test_08_canonical_dataset_contains_at_least_500_pairs(self):
        """Test that canonical dataset 04_data_and_memory/ai_training_game_dataset.jsonl has >= 500 verified pairs."""
        canonical_file = REPO_ROOT / "04_data_and_memory" / "ai_training_game_dataset.jsonl"
        self.assertTrue(canonical_file.exists(), f"Canonical dataset file missing: {canonical_file}")
        
        daily_count = get_daily_verified_count(canonical_file)
        self.assertGreaterEqual(daily_count, 500, f"Expected >= 500 verified pairs, found {daily_count}")

    # -----------------------------------------------------------------------
    # 3. Dynamic RAM Governance & Apple Metal QLoRA Tests
    # -----------------------------------------------------------------------
    def test_09_hardware_capabilities_and_ram_governance(self):
        """Test dynamic RAM governance invariant: cap <= 21.6GB (90% limit), headroom >= 2.50GB."""
        hw = check_hardware_capabilities()
        self.assertEqual(hw["total_ram_gb"], 24.0)
        self.assertEqual(hw["ai_vram_cap_gb"], 21.6)
        self.assertEqual(hw["max_ram_cap_pct"], 90.0)

        gov = check_dynamic_ram_governance(cap_gb=21.6, min_headroom_gb=2.50)
        self.assertTrue(gov["is_safe"])
        self.assertEqual(gov["status"], "CERTIFIED_HEALTHY")
        self.assertGreaterEqual(gov["ram_headroom_gb"], 2.50)
        self.assertLessEqual(gov["allocated_ai_ram_gb"], 21.6)

    def test_10_fast_train_agentworld_dataset_preparation(self):
        """Test dataset preparation for AgentWorld fast training."""
        prepared_path = prepare_training_dataset(stage=1)
        self.assertTrue(prepared_path.exists())
        self.assertGreater(prepared_path.stat().st_size, 0)

        # Inspect first record
        with open(prepared_path, "r", encoding="utf-8") as f:
            first_line = json.loads(f.readline())
        self.assertIn("messages", first_line)
        self.assertEqual(len(first_line["messages"]), 3)
        self.assertTrue(first_line.get("zero_mock"))

    def test_11_fast_train_dry_run_execution(self):
        """Test MLX and MPS dry-run training workflows."""
        prepared_path = prepare_training_dataset(stage=1)
        
        mlx_res = run_mlx_qlora_training(prepared_path, iters=100, dry_run=True)
        self.assertEqual(mlx_res["status"], "DRY_RUN_PLAN_VERIFIED")
        self.assertIn("final_loss", mlx_res)
        self.assertTrue(mlx_res["ram_governor"]["is_safe"])

        mps_res = run_mps_qlora_training(prepared_path, stage=1, iters=100, dry_run=True)
        self.assertEqual(mps_res["status"], "DRY_RUN_PLAN_VERIFIED")
        self.assertIn("final_loss", mps_res)
        self.assertTrue(mps_res["ram_governor"]["is_safe"])

    # -----------------------------------------------------------------------
    # 4. Obsidian Loss Curve Streaming Tests
    # -----------------------------------------------------------------------
    def test_12_obsidian_loss_curve_streaming(self):
        """Test live loss curve streaming to Obsidian Vault note."""
        target_note = stream_training_loss_to_obsidian(
            step=500,
            loss=1.5998,
            lr=1e-4,
            headroom_gb=3.20,
            note_path=self.test_obsidian
        )
        self.assertTrue(target_note.exists())
        content = target_note.read_text(encoding="utf-8")
        
        self.assertIn("title: \"Qwen Math Continuous Optimization Trends (Live Stream)\"", content)
        self.assertIn("Training Loss (Step 500):** `1.5998`", content)
        self.assertIn("Optimal TB4 Striping Weight:** `97.5%`", content)
        self.assertIn("Optimal WireGuard Striping Weight:** `2.1%`", content)
        self.assertIn("RAM Safety Status:** `CERTIFIED_HEALTHY (Headroom: 3.20 GB)`", content)
        self.assertIn("Headroom = Cap (21.6GB)", content)
        self.assertIn("[[CANONICAL_PROJECT_AND_STORAGE_RULE]]", content)

    # -----------------------------------------------------------------------
    # 5. Autonomous Consensus Model Weight Merging Tests
    # -----------------------------------------------------------------------
    def test_13_mergekit_consensus_score_calculation(self):
        """Test calculate_consensus_score across Tri-Orchestrator votes."""
        high_conf_payload = {
            "tri_orchestrator_votes": {
                "cloud_orchestrator": {"confidence": 0.98, "vote": "APPROVE"},
                "local_ai_orchestrator": {"confidence": 0.97, "vote": "APPROVE"},
                "genetic_ai_orchestrator": {"confidence": 0.96, "vote": "APPROVE"}
            }
        }
        score = calculate_consensus_score(high_conf_payload)
        self.assertGreater(score, 0.95)

        low_conf_payload = {
            "tri_orchestrator_votes": {
                "cloud_orchestrator": {"confidence": 0.85, "vote": "APPROVE"},
                "local_ai_orchestrator": {"confidence": 0.90, "vote": "APPROVE"},
                "genetic_ai_orchestrator": {"confidence": 0.80, "vote": "APPROVE"}
            }
        }
        score_low = calculate_consensus_score(low_conf_payload)
        self.assertLessEqual(score_low, 0.95)

    def test_14_mergekit_high_consensus_triggers_merge_and_preserves_parents(self):
        """Test that high consensus (>0.95) triggers merge and strictly preserves parent models."""
        engine = AutonomousConsensusMergeEngine(workspace_root=self.temp_path)
        
        payload = {
            "tri_orchestrator_votes": {
                "cloud_orchestrator": {"confidence": 0.98, "vote": "APPROVE"},
                "local_ai_orchestrator": {"confidence": 0.97, "vote": "APPROVE"},
                "genetic_ai_orchestrator": {"confidence": 0.96, "vote": "APPROVE"}
            },
            "base_model": "deepseek_r1_32b",
            "expert_model": "qwen_38_vl_30b",
            "merge_algorithm": "SPARSE_MOE_DARE_TIES"
        }
        
        res = engine.evaluate_and_trigger_merge(payload)
        self.assertEqual(res["status"], "TRIGGERED")
        self.assertTrue(res["threshold_met"])
        self.assertTrue(res["offspring_created"])
        self.assertTrue(res["recipe_created"])
        self.assertTrue(res["parents_preserved"])
        
        # Verify recipe YAML exists under data/mergekit_recipes/
        recipe_path = Path(res["offspring"]["recipe_path"])
        self.assertTrue(recipe_path.exists())
        
        # Verify offspring artifact exists under data/models/
        model_path = Path(res["offspring"]["model_path"])
        self.assertTrue(model_path.exists())

    def test_15_mergekit_low_consensus_rejects_and_creates_zero_artifacts(self):
        """Test that low consensus (<=0.95) is rejected and creates zero recipe/offspring files."""
        engine = AutonomousConsensusMergeEngine(workspace_root=self.temp_path)
        
        payload = {
            "tri_orchestrator_votes": {
                "cloud_orchestrator": {"confidence": 0.80, "vote": "APPROVE"},
                "local_ai_orchestrator": {"confidence": 0.85, "vote": "APPROVE"},
                "genetic_ai_orchestrator": {"confidence": 0.75, "vote": "APPROVE"}
            },
            "base_model": "deepseek_r1_32b",
            "expert_model": "qwen_38_vl_30b"
        }
        
        res = engine.evaluate_and_trigger_merge(payload)
        self.assertEqual(res["status"], "REJECTED")
        self.assertFalse(res["threshold_met"])
        self.assertFalse(res["offspring_created"])
        self.assertFalse(res["recipe_created"])
        self.assertIn("did not exceed", res["reason"])


if __name__ == "__main__":
    unittest.main()
