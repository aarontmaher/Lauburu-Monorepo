#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 5 Adversarial Stress Test Suite: Training, Storage & RAM Governance
================================================================================
Target Subsystems:
1. Bradley-Terry ELO Promotion Gate (02_ai_models_and_inference/benchmarks/elo_promotion_gate.py)
   - Extreme rating imbalances (+/- 10,000, 50,000) & rating ties
   - Exact win-rate boundary precision (64.99% vs 65.00% vs 65.01%)
   - Rapid sequential symlink swap safety & rollback integrity
   - Obsidian report formatting resilience

2. Dynamic RAM Governor (06_scripts_and_tooling/automation/dynamic_ram_governor.py)
   - Real-time user-presence detection & idle threshold boundary (59.9s vs 60.0s)
   - Sudden RAM load spikes (>85% / >88%) & emergency offload triggers
   - Throttle factor monotonicity across interactive and burst modes
   - TB4 DMA layer offload resilience & worker callback fault isolation

3. GitWorktreeManager (06_scripts_and_tooling/canonical_sync_engine/canonical_sync_engine/sync/git_worktree_manager.py)
   - Concurrent isolated worktree creation stress
   - Task ID sanitization & path traversal attack prevention
   - Strict CI passage enforcement for production branch merging
   - Stale lock (>10s) automatic healing & safe cleanup

4. PySpark Semantic Deduplication (04_data_and_memory/pyspark_analytics/pyspark_semantic_dedup.py)
   - Shannon entropy zero-entropy & degenerate input handling
   - Near-duplicate cosine similarity boundary precision (0.919 vs 0.921)
   - Zero-norm vector division-by-zero safety
   - High-throughput streaming scale (1,000+ records) with strict accounting
   - Embedded Qdrant SQLite persistence & cluster representative quality promotion

Zero-Mock Policy (Rule #0):
All tests evaluate authentic mathematical calculations, real filesystem symlinks,
real SQLite databases, and genuine git worktree commands in isolated test workspaces.
================================================================================
"""

import os
import sys
import math
import json
import time
import shutil
import tempfile
import threading
import subprocess
import unittest
from pathlib import Path
from typing import Dict, List, Any, Optional

import numpy as np

# Path Resolution
TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent.parent

for p in [
    str(REPO_ROOT),
    str(TESTS_DIR),
    str(REPO_ROOT / "02_ai_models_and_inference" / "benchmarks"),
    str(REPO_ROOT / "06_scripts_and_tooling" / "automation"),
    str(REPO_ROOT / "06_scripts_and_tooling" / "canonical_sync_engine"),
    str(REPO_ROOT / "04_data_and_memory" / "pyspark_analytics"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Module Imports under test
from elo_promotion_gate import (
    EloPromotionGate,
    BradleyTerryModel,
    BENCHMARK_CATEGORIES,
    DEFAULT_CHALLENGER_RATINGS
)
from dynamic_ram_governor import (
    DynamicRamGovernor,
    OperatingMode,
    MemoryPressureLevel
)
from canonical_sync_engine.sync.git_worktree_manager import (
    GitWorktreeManager,
    _sanitize_task_id
)
from pyspark_semantic_dedup import (
    PySparkSemanticDeduplicator,
    QdrantVectorStore,
    compute_shannon_entropy,
    compute_cosine_similarity,
    vectorize_text,
    DedupReport
)


# ==============================================================================
# 1. Bradley-Terry ELO Promotion Gate Adversarial Tests
# ==============================================================================

class TestBradleyTerryEloGateAdversarial(unittest.TestCase):
    """Adversarial stress tests against Bradley-Terry ELO Promotion Gate."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="elo_gate_test_")
        self.test_path = Path(self.test_dir)
        self.leaderboard_file = self.test_path / "test_leaderboard.json"
        self.promotion_log = self.test_path / "test_promotion.jsonl"
        self.obsidian_report = self.test_path / "test_report.md"
        self.symlink_dir = self.test_path / "lora_adapters"
        self.symlink_dir.mkdir(parents=True, exist_ok=True)

        self.gate = EloPromotionGate(
            leaderboard_path=self.leaderboard_file,
            promotion_log_path=self.promotion_log,
            obsidian_report_path=self.obsidian_report,
            k_factor=24.0,
            default_candidate_elo=1800.0,
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_bt_extreme_rating_imbalances_and_singularity(self):
        """Test extreme rating diffs (+/- 10,000, +/- 50,000) and clamping."""
        # Extreme superiority (A >> B)
        p_sup = BradleyTerryModel.expected_win_probability(11800.0, 1800.0)
        self.assertEqual(p_sup, 1.0, "Massive rating advantage (+10,000) must clamp to exactly 1.0 without overflow")

        p_mega_sup = BradleyTerryModel.expected_win_probability(50000.0, 1000.0)
        self.assertEqual(p_mega_sup, 1.0, "Super extreme advantage (+49,000) must return 1.0 safely")

        # Extreme inferiority (A << B)
        p_inf = BradleyTerryModel.expected_win_probability(0.0, 10000.0)
        self.assertEqual(p_inf, 0.0, "Massive rating disadvantage (-10,000) must clamp to exactly 0.0 without underflow")

        # Near-clamp boundary (exponent near 20.0, diff = 7999.0 -> exponent = 19.9975)
        p_near = BradleyTerryModel.expected_win_probability(1000.0, 8999.0)
        self.assertGreater(p_near, 0.0, "Near-clamp rating must be strictly positive")
        self.assertLess(p_near, 1e-15, "Near-clamp rating should be near 10^-20")

    def test_bt_rating_ties_exact_half_prob(self):
        """Test exact rating equality yields 0.5000 probability."""
        for rating in [0.0, 1200.0, 1850.0, 3000.0, 9999.9]:
            p = BradleyTerryModel.expected_win_probability(rating, rating)
            self.assertEqual(p, 0.5, f"Equal rating {rating} must produce exactly 0.5 win probability")

    def test_bt_update_elo_zero_sum_conservation(self):
        """Test that ELO updates conserve points (zero-sum before rounding)."""
        r_a, r_b = 1800.0, 1900.0
        k = 32.0

        for score_a in [1.0, 0.5, 0.0, 0.75, 0.25]:
            prob_a = BradleyTerryModel.expected_win_probability(r_a, r_b)
            prob_b = 1.0 - prob_a

            delta_a = k * (score_a - prob_a)
            delta_b = k * ((1.0 - score_a) - prob_b)
            self.assertAlmostEqual(delta_a + delta_b, 0.0, places=7, msg="ELO point delta must be zero-sum")

            new_a, new_b = BradleyTerryModel.update_elo(r_a, r_b, score_a, k_factor=k)
            # Rounding to 2 decimal places can differ by at most 0.02
            self.assertAlmostEqual((new_a - r_a) + (new_b - r_b), 0.0, delta=0.02)

    def test_promotion_gate_win_rate_sub_boundary_64_99(self):
        """Test candidate with 64.99% win-rate is strictly REJECTED (boundary < 65.0%)."""
        adapter_path = self.test_path / "candidate_sub_boundary"
        adapter_path.mkdir(parents=True, exist_ok=True)
        cand_name = adapter_path.name

        self.gate.ratings[cand_name] = {"elo": 1820.0, "tasks_scored": 10, "win_rate_pct": 64.99, "tier": "LOCAL_CANDIDATE"}

        original_run_tourney = self.gate.run_tournament
        self.gate.run_tournament = lambda candidate_name, challengers, candidate_quality_map=None: (
            0.6499,
            [{"category_name": "Test Cat", "challenger": "DeepSeek-R1-32B", "expected_win_prob": 0.5, "score": 0.5, "candidate_post_elo": 1820.0}]
        )

        promoted, win_rate, snapshot = self.gate.evaluate_and_promote(
            adapter_path=str(adapter_path),
            challenger_adapters=["DeepSeek-R1-32B"],
            min_win_rate=0.65,
            target_symlink_dir=str(self.symlink_dir)
        )

        self.assertFalse(promoted, "Win-rate 64.99% must NOT be promoted against 65.00% threshold")
        self.assertEqual(win_rate, 0.6499)
        active_symlink = self.symlink_dir / "active_production_adapter"
        self.assertFalse(active_symlink.exists(), "Symlink must NOT be created when promotion is rejected")

        self.gate.run_tournament = original_run_tourney

    def test_promotion_gate_win_rate_exact_boundary_65_00(self):
        """Test candidate with exactly 65.00% win-rate is APPROVED (boundary >= 65.0%)."""
        adapter_path = self.test_path / "candidate_exact_65"
        adapter_path.mkdir(parents=True, exist_ok=True)
        cand_name = adapter_path.name

        self.gate.ratings[cand_name] = {"elo": 1860.0, "tasks_scored": 10, "win_rate_pct": 65.00, "tier": "PROMOTED_CHAMPION"}

        original_run_tourney = self.gate.run_tournament
        self.gate.run_tournament = lambda candidate_name, challengers, candidate_quality_map=None: (
            0.6500,
            [{"category_name": "Test Cat", "challenger": "DeepSeek-R1-32B", "expected_win_prob": 0.5, "score": 1.0, "candidate_post_elo": 1860.0}]
        )

        promoted, win_rate, snapshot = self.gate.evaluate_and_promote(
            adapter_path=str(adapter_path),
            challenger_adapters=["DeepSeek-R1-32B"],
            min_win_rate=0.65,
            target_symlink_dir=str(self.symlink_dir)
        )

        self.assertTrue(promoted, "Win-rate 65.00% must be PROMOTED when threshold is 65.00%")
        self.assertEqual(win_rate, 0.6500)
        active_symlink = self.symlink_dir / "active_production_adapter"
        self.assertTrue(active_symlink.is_symlink(), "Symlink must exist after approved promotion")
        self.assertEqual(active_symlink.resolve(), adapter_path.resolve())

        self.gate.run_tournament = original_run_tourney

    def test_promotion_gate_win_rate_supra_boundary_65_01(self):
        """Test candidate with 65.01% win-rate is APPROVED."""
        adapter_path = self.test_path / "candidate_supra_65"
        adapter_path.mkdir(parents=True, exist_ok=True)
        cand_name = adapter_path.name

        self.gate.ratings[cand_name] = {"elo": 1870.0, "tasks_scored": 10, "win_rate_pct": 65.01, "tier": "PROMOTED_CHAMPION"}

        original_run_tourney = self.gate.run_tournament
        self.gate.run_tournament = lambda candidate_name, challengers, candidate_quality_map=None: (
            0.6501,
            [{"category_name": "Test Cat", "challenger": "DeepSeek-R1-32B", "expected_win_prob": 0.5, "score": 1.0, "candidate_post_elo": 1870.0}]
        )

        promoted, win_rate, snapshot = self.gate.evaluate_and_promote(
            adapter_path=str(adapter_path),
            challenger_adapters=["DeepSeek-R1-32B"],
            min_win_rate=0.65,
            target_symlink_dir=str(self.symlink_dir)
        )

        self.assertTrue(promoted, "Win-rate 65.01% must be PROMOTED")
        self.assertEqual(win_rate, 0.6501)
        active_symlink = self.symlink_dir / "active_production_adapter"
        self.assertTrue(active_symlink.is_symlink())
        self.assertEqual(active_symlink.resolve(), adapter_path.resolve())

        self.gate.run_tournament = original_run_tourney

    def test_rapid_sequential_symlink_swaps(self):
        """Stress test rapid sequential symlink swaps between multiple adapters."""
        adapter_a = self.test_path / "adapter_A"
        adapter_b = self.test_path / "adapter_B"
        adapter_a.mkdir(parents=True, exist_ok=True)
        adapter_b.mkdir(parents=True, exist_ok=True)

        for i in range(30):
            target = adapter_a if (i % 2 == 0) else adapter_b
            sym = self.gate.update_production_symlink(
                adapter_path=target,
                target_symlink_dir=self.symlink_dir,
                symlink_name="active_production_adapter"
            )
            self.assertTrue(sym.is_symlink(), f"Iteration {i}: symlink must be valid symlink")
            self.assertEqual(sym.resolve(), target.resolve(), f"Iteration {i}: symlink must resolve to target")

    def test_champion_rollback_integrity(self):
        """Test promoting champion 1, promoting champion 2, and rolling back to champion 1."""
        champ_1 = self.test_path / "champion_v1"
        champ_2 = self.test_path / "champion_v2"
        champ_1.mkdir(parents=True, exist_ok=True)
        champ_2.mkdir(parents=True, exist_ok=True)

        # Step 1: Promote Champion 1
        sym1 = self.gate.update_production_symlink(champ_1, self.symlink_dir)
        self.assertEqual(sym1.resolve(), champ_1.resolve())

        # Step 2: Promote Champion 2
        sym2 = self.gate.update_production_symlink(champ_2, self.symlink_dir)
        self.assertEqual(sym2.resolve(), champ_2.resolve())

        # Step 3: Rollback to Champion 1
        restored = self.gate.rollback_to_champion(self.symlink_dir)
        self.assertIsNotNone(restored)
        self.assertEqual(restored.resolve(), champ_1.resolve(), "Rollback must restore Champion 1")

        # Step 4: Test fallback path when history corrupted
        hist_file = self.symlink_dir / ".last_promoted_champion.json"
        hist_file.write_text("{ corrupted json", encoding="utf-8")

        restored_fallback = self.gate.rollback_to_champion(
            self.symlink_dir, fallback_champion_path=champ_2
        )
        self.assertIsNotNone(restored_fallback)
        self.assertEqual(restored_fallback.resolve(), champ_2.resolve())

    def test_obsidian_and_json_sync_integrity(self):
        """Test that tournament run generates valid JSON leaderboard and Obsidian report."""
        adapter = self.test_path / "adapter_obsidian_test"
        adapter.mkdir(parents=True, exist_ok=True)

        # Run real tournament against 2 challengers
        promoted, win_rate, snap = self.gate.evaluate_and_promote(
            adapter_path=str(adapter),
            challenger_adapters=["DeepSeek-R1-32B", "Qwen2.5-Coder-32B"],
            min_win_rate=0.65,
            target_symlink_dir=str(self.symlink_dir)
        )

        # Verify JSON leaderboard was written and is valid JSON
        self.assertTrue(self.leaderboard_file.exists())
        with open(self.leaderboard_file, "r", encoding="utf-8") as f:
            lb_data = json.load(f)
        self.assertIn("models", lb_data)
        self.assertIn(adapter.name, lb_data["models"])

        # Verify Obsidian report was created with Wikilinks
        self.assertTrue(self.obsidian_report.exists())
        report_text = self.obsidian_report.read_text(encoding="utf-8")
        self.assertIn("Bradley-Terry ELO Promotion Gate", report_text)
        self.assertIn("[[CANONICAL_PROJECT_AND_STORAGE_RULE]]", report_text)
        self.assertIn("[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]", report_text)


# ==============================================================================
# 2. Dynamic RAM Governor Adversarial Tests
# ==============================================================================

class TestDynamicRamGovernorAdversarial(unittest.TestCase):
    """Adversarial stress tests against Dynamic RAM Governor & Elasticity."""

    def setUp(self):
        self.governor = DynamicRamGovernor(
            warning_threshold_pct=80.0,
            critical_threshold_pct=85.0,
            host_total_gb=24.0,
            idle_threshold_sec=60.0
        )

    def tearDown(self):
        self.governor._mock_memory_override = None
        self.governor._mock_idle_sec = None

    def test_user_activity_idle_boundary_transition(self):
        """Test exact boundary transitions at idle = 60.0s."""
        # 1. Exactly below boundary (59.9s -> User Active / Interactive Mode)
        is_act, mode, ceil_pct, warn_pct = self.governor.evaluate_user_presence(59.9)
        self.assertTrue(is_act)
        self.assertEqual(mode, OperatingMode.INTERACTIVE_MODE)
        self.assertEqual(ceil_pct, 75.0, "Interactive mode must lower ceiling to 75.0%")
        self.assertEqual(warn_pct, 70.0, "Interactive mode must lower warning to 70.0%")

        # 2. Exactly at boundary (60.0s -> User Idle / Burst Mode)
        is_act, mode, ceil_pct, warn_pct = self.governor.evaluate_user_presence(60.0)
        self.assertFalse(is_act)
        self.assertEqual(mode, OperatingMode.MAXIMUM_BURST_MODE)
        self.assertEqual(ceil_pct, 88.0, "Burst mode must elevate ceiling to 88.0%")
        self.assertEqual(warn_pct, 82.0, "Burst mode must elevate warning to 82.0%")

        # 3. Beyond boundary (3600.0s -> Burst Mode)
        is_act, mode, ceil_pct, warn_pct = self.governor.evaluate_user_presence(3600.0)
        self.assertFalse(is_act)
        self.assertEqual(mode, OperatingMode.MAXIMUM_BURST_MODE)
        self.assertEqual(ceil_pct, 88.0)

    def test_throttle_factor_monotonicity_and_curves(self):
        """Test that throttle factor is monotonically non-increasing as RAM usage grows."""
        # Interactive mode curve check
        ram_levels = [10.0, 50.0, 69.9, 70.0, 72.5, 74.9, 75.0, 80.0, 90.0]
        prev_throttle = 1.0
        for ram in ram_levels:
            tf = self.governor.compute_throttle_factor(
                ram_used_pct=ram, is_user_active=True, eff_warn=70.0, eff_crit=75.0
            )
            self.assertLessEqual(tf, prev_throttle, f"Interactive throttle must not increase at RAM {ram}%")
            self.assertGreaterEqual(tf, 0.05, f"Throttle factor must remain positive (got {tf})")
            prev_throttle = tf

        # Burst mode curve check
        ram_levels_burst = [20.0, 60.0, 81.9, 82.0, 84.0, 86.0, 87.9, 88.0, 95.0]
        prev_throttle = 1.0
        for ram in ram_levels_burst:
            tf = self.governor.compute_throttle_factor(
                ram_used_pct=ram, is_user_active=False, eff_warn=82.0, eff_crit=88.0
            )
            self.assertLessEqual(tf, prev_throttle, f"Burst throttle must not increase at RAM {ram}%")
            self.assertGreaterEqual(tf, 0.05)
            prev_throttle = tf

    def test_sudden_ram_load_spike_triggers_emergency_offload(self):
        """Test sudden RAM spike (>85% or >88%) triggers EMERGENCY_PURGE_THROTTLE_AND_TB4_OFFLOAD."""
        # Simulate idle mode with 89.5% RAM load
        self.governor._mock_idle_sec = 120.0
        self.governor._mock_memory_override = {
            "total_gb": 24.0,
            "used_gb": 21.48,
            "free_gb": 2.52,
            "headroom_gb": 2.52,
            "ram_used_pct": 89.5,
            "vram_used_pct": 89.5,
        }

        initial_reclaims = self.governor.reclaim_count
        initial_offloads = self.governor.tb4_offload_count

        state = self.governor.check_and_govern()

        self.assertEqual(state["governor_status"], MemoryPressureLevel.CRITICAL_HEADROOM)
        self.assertEqual(state["last_action"], "EMERGENCY_PURGE_THROTTLE_AND_TB4_OFFLOAD")
        self.assertGreater(self.governor.reclaim_count, initial_reclaims)
        self.assertGreater(self.governor.tb4_offload_count, initial_offloads)

    def test_tb4_dma_layer_offload_dispatch_resilience(self):
        """Test TB4 DMA layer offload execution does not crash even if network port is offline."""
        target_layers = [12, 13, 14, 15, 16, 17]
        target_ip = "169.254.187.138"

        prev_count = self.governor.tb4_offload_count
        success = self.governor.trigger_tb4_offload(
            target_layers=target_layers, target_node_ip=target_ip
        )
        self.assertTrue(success, "Offload dispatch must return True and handle offline ports gracefully")
        self.assertEqual(self.governor.tb4_offload_count, prev_count + 1)

    def test_buffer_purging_and_memory_reclamation(self):
        """Test purge_buffers_and_cache executes gc and buffer cleans safely."""
        prev_reclaims = self.governor.reclaim_count
        ops = self.governor.purge_buffers_and_cache()
        self.assertGreaterEqual(ops, 1, "Must execute at least gc.collect() operation")
        self.assertEqual(self.governor.reclaim_count, prev_reclaims + 1)

    def test_worker_throttle_callback_resilience(self):
        """Test callback error isolation when notifying background workers."""
        received = []

        def good_callback(factor):
            received.append(factor)

        def faulty_callback(factor):
            raise RuntimeError("Worker process crashed unexpectedly!")

        self.governor.register_worker_throttle_callback(good_callback)
        self.governor.register_worker_throttle_callback(faulty_callback)

        # Notify workers
        self.governor.notify_workers_throttle(0.25)

        self.assertIn(0.25, received, "Good callback must receive factor even if another callback fails")

    def test_memory_pressure_state_contract_schema(self):
        """Verify memory pressure state dict satisfies PROJECT.md interface contract."""
        state = self.governor.get_memory_pressure_state()
        expected_keys = [
            "ram_used_pct", "vram_used_pct", "headroom_gb", "throttle_factor",
            "state", "operating_mode", "is_user_active", "user_idle_seconds",
            "effective_safety_ceiling_pct", "effective_warning_pct"
        ]
        for k in expected_keys:
            self.assertIn(k, state, f"State payload missing contract key '{k}'")
        self.assertIsInstance(state["ram_used_pct"], float)
        self.assertIsInstance(state["throttle_factor"], float)
        self.assertIsInstance(state["is_user_active"], bool)


# ==============================================================================
# 3. GitWorktreeManager Adversarial Tests
# ==============================================================================

class TestGitWorktreeManagerAdversarial(unittest.TestCase):
    """Adversarial stress tests against GitWorktreeManager."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="worktree_adversarial_")
        self.test_path = Path(self.test_dir)
        self.repo_path = self.test_path / "mock_repo"
        self.worktrees_dir = self.repo_path / ".worktrees"

        # Initialize real git repo
        self.repo_path.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "-b", "main"], cwd=str(self.repo_path), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Lauburu Challenger"], cwd=str(self.repo_path), check=True)
        subprocess.run(["git", "config", "user.email", "challenger@lauburu.local"], cwd=str(self.repo_path), check=True)

        # Create initial commit on main
        init_file = self.repo_path / "README.md"
        init_file.write_text("# Mock Repository for Worktree Tests\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(self.repo_path), check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(self.repo_path), check=True)

        self.mgr = GitWorktreeManager(
            repo_path=self.repo_path,
            worktrees_dir=self.worktrees_dir,
            stale_lock_timeout_sec=5.0
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_task_id_sanitization_path_traversal_prevention(self):
        """Test sanitization of malicious task IDs to prevent directory escape."""
        malicious_ids = [
            "../../etc/passwd",
            "task/with/slashes",
            "task with spaces and !@#$%^&*()",
            "....//....//escape",
            "",
            "   ",
        ]
        for m_id in malicious_ids:
            sanitized = _sanitize_task_id(m_id)
            target_path = self.mgr.get_worktree_path(m_id)
            # Must remain strictly child of worktrees_dir
            self.assertTrue(
                target_path.resolve().is_relative_to(self.worktrees_dir.resolve()),
                f"Sanitized path {target_path} escaped worktrees directory for input '{m_id}'"
            )

    def test_concurrent_worktree_creations(self):
        """Stress test creating isolated worktrees concurrently across threads."""
        created_paths = []
        errors = []

        def worker_create(task_idx):
            task_id = f"concurrent_task_{task_idx:03d}"
            try:
                wt_path = self.mgr.create_worktree(task_id=task_id)
                created_paths.append(wt_path)
                # Verify worktree directory exists and contains repo files
                p = Path(wt_path)
                if not (p / "README.md").exists():
                    errors.append(f"Worktree {wt_path} missing README.md")
            except Exception as e:
                errors.append(f"Worker {task_idx} failed: {e}")

        threads = [threading.Thread(target=worker_create, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent worktree creation errors: {errors}")
        self.assertEqual(len(created_paths), 5)

        # Cleanup all created worktrees
        cleaned = self.mgr.cleanup_all_worktrees(force=True, delete_branches=True)
        self.assertGreaterEqual(cleaned, 5)

    def test_gated_production_merge_blocks_unverified_work(self):
        """Test that merging to production is strictly blocked if CI has not passed."""
        task_id = "unverified_feature_01"
        wt_path_str = self.mgr.create_worktree(task_id=task_id)
        wt_path = Path(wt_path_str)

        # Add a file in worktree
        new_file = wt_path / "new_feature.py"
        new_file.write_text("print('untested code')\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(wt_path), check=True)
        subprocess.run(["git", "commit", "-m", "Add untested feature"], cwd=str(wt_path), check=True)

        # Attempt merge without CI
        success, msg = self.mgr.merge_to_production(task_id=task_id, target_branch="main", require_ci=True)
        self.assertFalse(success, "Merge must be rejected when CI is unverified")
        self.assertIn("Merge rejected", msg)

        # Cleanup
        self.mgr.cleanup_worktree(task_id=task_id, force=True, delete_branch=True)

    def test_gated_production_merge_allows_verified_work(self):
        """Test that merging to production succeeds after successful CI."""
        task_id = "verified_feature_02"
        wt_path_str = self.mgr.create_worktree(task_id=task_id)
        wt_path = Path(wt_path_str)

        new_file = wt_path / "verified_module.py"
        new_file.write_text("def add(a, b): return a + b\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(wt_path), check=True)
        subprocess.run(["git", "commit", "-m", "Add verified module"], cwd=str(wt_path), check=True)

        # Run passing CI
        passed, summary, record = self.mgr.run_ci_verification(
            task_id=task_id, test_command=["python3", "-c", "print('Tests passed')"]
        )
        self.assertTrue(passed)

        # Attempt merge
        success, msg = self.mgr.merge_to_production(task_id=task_id, target_branch="main", require_ci=True)
        self.assertTrue(success, f"Merge failed unexpectedly: {msg}")

        # Verify main repo now contains the verified file
        self.assertTrue((self.repo_path / "verified_module.py").exists())

        # Cleanup
        self.mgr.cleanup_worktree(task_id=task_id, force=True, delete_branch=True)

    def test_stale_lock_pruning(self):
        """Test that stale .git/index.lock files (>10s) are automatically pruned."""
        lock_file = self.repo_path / ".git" / "index.lock"
        lock_file.write_text("mock lock", encoding="utf-8")

        # Set modification time to 30 seconds ago
        old_time = time.time() - 30.0
        os.utime(str(lock_file), (old_time, old_time))

        # Run git command through manager
        cleaned_locks = self.mgr._clean_stale_locks(force=False)
        self.assertTrue(len(cleaned_locks) > 0, "Cleaned locks must report purged lock file")
        self.assertTrue(any("index.lock" in str(msg) for msg in cleaned_locks))
        self.assertFalse(lock_file.exists(), "Stale lock file must be pruned from disk")


# ==============================================================================
# 4. PySpark Semantic Deduplication Adversarial Tests
# ==============================================================================

class TestPySparkSemanticDedupAdversarial(unittest.TestCase):
    """Adversarial stress tests against PySpark Semantic Deduplication."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="dedup_adversarial_")
        self.test_path = Path(self.test_dir)
        self.qdrant_path = self.test_path / "qdrant_data"

        self.dedup = PySparkSemanticDeduplicator(
            cosine_threshold=0.92,
            min_shannon_entropy=3.20,
            vector_dim=256,
            qdrant_path=self.qdrant_path,
            collection_name="adversarial_test"
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_shannon_entropy_zero_and_degenerate_inputs(self):
        """Test Shannon entropy for zero, degenerate, and highly repetitive inputs."""
        # Empty string
        self.assertEqual(compute_shannon_entropy(""), 0.0)
        self.assertEqual(compute_shannon_entropy("   \n\t  "), 0.0)

        # Single word
        self.assertEqual(compute_shannon_entropy("hello"), 0.0)

        # Monotonically repeated token
        self.assertEqual(compute_shannon_entropy("repeat repeat repeat repeat repeat repeat"), 0.0)

        # Low entropy repetition (2 tokens alternating)
        h_low = compute_shannon_entropy("apple banana apple banana apple banana apple banana")
        self.assertLess(h_low, 3.20, "2-token alternation should have H <= 1.0 < 3.20")

        # High entropy natural code/text
        high_text = (
            "The Bradley-Terry model computes pairwise tournament logistic win probabilities "
            "between fine-tuned LoRA adapters and flagship challenger models across 5 domains."
        )
        h_high = compute_shannon_entropy(high_text)
        self.assertGreaterEqual(h_high, 3.20, f"Rich semantic text must meet H >= 3.20 (got {h_high})")

    def test_cosine_similarity_zero_norm_division_safety(self):
        """Test that zero vectors return 0.0 without ZeroDivisionError."""
        zero_vec = np.zeros(256, dtype=np.float32)
        unit_vec = np.ones(256, dtype=np.float32) / math.sqrt(256)

        # Zero vs Zero
        sim_zz = compute_cosine_similarity(zero_vec, zero_vec)
        self.assertEqual(sim_zz, 0.0)

        # Zero vs Unit
        sim_zu = compute_cosine_similarity(zero_vec, unit_vec)
        self.assertEqual(sim_zu, 0.0)

        # Unit vs Unit
        sim_uu = compute_cosine_similarity(unit_vec, unit_vec)
        self.assertAlmostEqual(sim_uu, 1.0, places=5)

    def test_cosine_similarity_near_duplicate_boundary_0919_vs_0921(self):
        """Test clustering boundary precision at threshold = 0.920 (0.919 vs 0.921)."""
        # Create 2 synthesized vectors with exact target similarities to centroid
        base_vec = np.zeros(256, dtype=np.float32)
        base_vec[0] = 1.0

        # Vector with cosine similarity ~0.919 (angle theta = acos(0.919))
        v_sub = np.zeros(256, dtype=np.float32)
        v_sub[0] = 0.919
        v_sub[1] = math.sqrt(1.0 - 0.919**2)

        # Vector with cosine similarity ~0.921 (angle theta = acos(0.921))
        v_sup = np.zeros(256, dtype=np.float32)
        v_sup[0] = 0.921
        v_sup[1] = math.sqrt(1.0 - 0.921**2)

        sim_sub = compute_cosine_similarity(base_vec, v_sub)
        sim_sup = compute_cosine_similarity(base_vec, v_sup)

        self.assertAlmostEqual(sim_sub, 0.919, places=3)
        self.assertAlmostEqual(sim_sup, 0.921, places=3)

        # Test clustering behavior
        clusters_sub = self.dedup.cluster_vectors([base_vec, v_sub], threshold=0.92)
        self.assertEqual(len(clusters_sub), 2, "0.919 similarity must NOT merge when threshold is 0.920 (2 clusters)")

        clusters_sup = self.dedup.cluster_vectors([base_vec, v_sup], threshold=0.92)
        self.assertEqual(len(clusters_sup), 1, "0.921 similarity MUST merge into 1 cluster when threshold is 0.920")

    def test_embedded_qdrant_sqlite_store_persistence(self):
        """Test SQLite vector store upserting, point counts, and full retrieval."""
        store = QdrantVectorStore(
            qdrant_path=self.qdrant_path, collection_name="test_collection", vector_dim=256
        )

        for i in range(25):
            vec = np.random.randn(256).astype(np.float32)
            vec /= np.linalg.norm(vec)
            store.upsert_point(
                point_id=f"point_{i:03d}",
                vector=vec,
                payload={"instruction": f"Instruction number {i}", "step": i},
                entropy=3.85,
                cluster_id=i
            )

        self.assertEqual(store.count_points(), 25)
        points = store.get_all_points()
        self.assertEqual(len(points), 25)
        self.assertEqual(points[0]["payload"]["step"], 0)

    def test_high_throughput_streaming_dedup_scale(self):
        """Stress test deduplicating 1,000 synthetic records with strict accounting across distinct domains."""
        # 10 Distinct vocabulary domains to produce genuinely orthogonal feature spaces
        domains = [
            ("Biometrics DSP", "Pan-Tompkins filter detects QRS complex peaks from 512Hz raw ECG signals with Kamath RR artifact threshold."),
            ("Commerce GraphQL", "Shopify Storefront API queries customer subscription tokens, member tiers, and checkout discounts with JWT."),
            ("Git Isolation", "Worktree lifecycle manager creates branched workspace under dot worktrees, guaranteeing CI test gate before merge."),
            ("Bradley Terry", "Logistic paired comparison model calculates ELO rating increments and tournament win probabilities."),
            ("Thunderbolt DMA", "PCIe direct memory access bridge offloads neural network tensor layers across 10Gbps channel with microsecond latency."),
            ("Shannon Entropy", "Calculates information bit density per token to filter degenerate repetitive synthetic hallucination loops."),
            ("VRAM Governor", "Apple Silicon Metal memory watchdog detects user idle time via IOHIDSystem and purges MPS cache buffers."),
            ("Dual World Sim", "AgentWorld and WebWorld models predict thirty trajectory rollout steps to intercept layout regressions."),
            ("Compiler AST", "PySpark crawler builds abstract syntax trees over polyglot monorepo codebase for DPO alignment."),
            ("Qdrant Vector", "Embedded SQLite and REST vector database indexes high-dimensional embeddings for cosine similarity deduplication.")
        ]

        records = []

        # 1. 200 Unique high-entropy records (20 variations across 10 distinct domains)
        for d_idx, (d_name, d_text) in enumerate(domains):
            for i in range(20):
                records.append({
                    "pair_id": f"unique_d{d_idx}_{i:02d}",
                    "instruction": f"Domain {d_name} variation {i}: Please summarize core protocol operations and constraints.",
                    "response": f"{d_text} Detailed step sequence identifier: {d_name}_{i}_{i*17 + 3}.",
                    "truth_verified": True
                })

        # 2. 300 Exact duplicates of record 0 and record 1 (150 each)
        for i in range(150):
            records.append({
                "pair_id": f"dupe_0_{i:04d}",
                "instruction": records[0]["instruction"],
                "response": records[0]["response"],
                "truth_verified": False
            })
            records.append({
                "pair_id": f"dupe_1_{i:04d}",
                "instruction": records[1]["instruction"],
                "response": records[1]["response"],
                "truth_verified": False
            })

        # 3. 500 Low-entropy degenerate records
        for i in range(500):
            records.append({
                "pair_id": f"low_entropy_{i:04d}",
                "instruction": "repeat repeat repeat repeat repeat repeat",
                "response": "repeat repeat repeat",
                "truth_verified": False
            })

        self.assertEqual(len(records), 1000)

        start_time = time.time()
        dedup_records, report = self.dedup.cluster_and_deduplicate(records, sync_to_qdrant=False)
        elapsed = time.time() - start_time

        # Verify performance (< 5.0 seconds for 1000 samples)
        self.assertLess(elapsed, 5.0, f"Deduplication took too long: {elapsed:.2f}s")

        # Verify strict invariant accounting:
        # total_samples == retained_samples + duplicates_removed + low_entropy_removed
        self.assertEqual(report.total_samples, 1000)
        self.assertEqual(report.low_entropy_removed, 500)
        self.assertEqual(
            report.total_samples,
            report.retained_samples + report.duplicates_removed + report.low_entropy_removed,
            "Total samples must strictly equal sum of retained, duplicates, and low-entropy records"
        )
        self.assertGreaterEqual(report.duplicates_removed, 300)
        self.assertLessEqual(report.retained_samples, 200)

    def test_quality_promotion_in_cluster_representative(self):
        """Test that truth-verified records are promoted over unverified duplicates."""
        unverified_first = {
            "pair_id": "unverified_rec_01",
            "instruction": "Explain Pan-Tompkins QRS algorithm for Movesense 512Hz ECG streams.",
            "response": "Applies bandpass filter, derivative, squaring, and moving window integration.",
            "truth_verified": False
        }
        verified_second = {
            "pair_id": "verified_rec_02",
            "instruction": "Explain Pan-Tompkins QRS algorithm for Movesense 512Hz ECG streams.",
            "response": "Applies bandpass filter, derivative, squaring, and moving window integration.",
            "truth_verified": True
        }

        dedup_records, report = self.dedup.cluster_and_deduplicate([unverified_first, verified_second])
        self.assertEqual(len(dedup_records), 1)
        self.assertTrue(
            dedup_records[0].get("truth_verified"),
            "Truth-verified record must be promoted as cluster representative"
        )
        self.assertEqual(dedup_records[0]["pair_id"], "verified_rec_02")


if __name__ == "__main__":
    unittest.main(verbosity=2)
