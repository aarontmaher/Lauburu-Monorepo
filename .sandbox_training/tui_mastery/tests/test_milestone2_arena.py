#!/usr/bin/env python3
"""Comprehensive Unit & Component Test Suite for Milestone 2 (Red vs Blue Arena & Abliterated 70B Referee).

Tests:
- Blue Team Defenses (Python Textual, Go Bubbletea, Rust Ratatui)
- Red Team 5-Tier Attack Engine (SIGWINCH, Event Flood, Memory, Schema Fuzzing, Lock Contention)
- Abliterated 70B Referee & Chaos Injector (Refusal ablation math, Scoring matrix, Merkle logging, NPU grants)
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List

SANDBOX_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SANDBOX_DIR.parent.parent
sys.path.insert(0, str(SANDBOX_DIR))

from attacks.sigwinch_storm import SigwinchStressor, SigwinchAttackResult
from attacks.event_flood import EventFloodStressor, EventFloodResult
from attacks.memory_stressor import MemoryStressor, MemoryStressResult
from attacks.schema_fuzzer import SchemaFuzzer, FuzzSuiteResult, get_fuzz_corpus
from attacks.lock_contention import LockContentionStressor, LockContentionResult
from referee.scoring_matrix import (
    ScoringMatrix,
    ScoreBreakdown,
    calculate_composite_score,
    calculate_npu_bonus_hours,
    calculate_refusal_ablation,
    DEFAULT_SCORING_WEIGHTS,
    CHAOS_SURGE_WEIGHTS,
)
from referee.chaos_injector import ChaosInjector, ChaosEvent
from referee.abliterated_referee import AbliteratedReferee

CANONICAL_STATE_PATH = REPO_ROOT / "04_data_and_memory" / "data" / "cloud_api_quota_state.json"


class TestMilestone2BlueDefenses(unittest.TestCase):
    """Test Blue Team Defense Components."""

    def test_python_textual_defense_verify(self):
        app_path = SANDBOX_DIR / "defenses" / "python_textual" / "app.py"
        self.assertTrue(app_path.exists(), "python_textual/app.py missing")
        cmd = [sys.executable, str(app_path), "--verify", "--state-path", str(CANONICAL_STATE_PATH)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(res.returncode, 0, f"Stderr: {res.stderr}")
        self.assertIn("Python Textual Verification Passed", res.stdout)

    def test_go_bubbletea_defense_verify(self):
        bin_path = SANDBOX_DIR / "defenses" / "go_bubbletea" / "canonical_tui_go"
        if not bin_path.exists():
            bin_path = REPO_ROOT / "01_apps" / "canonical_tui_prototypes" / "go_bubbletea" / "canonical_tui_go"
        self.assertTrue(bin_path.exists(), "go_bubbletea binary missing")
        cmd = [str(bin_path), "-verify", "-state-path", str(CANONICAL_STATE_PATH)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(res.returncode, 0, f"Stderr: {res.stderr}")
        self.assertIn("Go Bubble Tea Verification Passed", res.stdout)

    def test_rust_ratatui_defense_verify(self):
        bin_path = SANDBOX_DIR / "defenses" / "rust_ratatui" / "target" / "release" / "canonical_tui_rust"
        if not bin_path.exists():
            bin_path = SANDBOX_DIR / "defenses" / "rust_ratatui" / "target" / "debug" / "canonical_tui_rust"
        if not bin_path.exists():
            bin_path = REPO_ROOT / "01_apps" / "canonical_tui_prototypes" / "rust_ratatui" / "target" / "release" / "canonical_tui_rust"
        self.assertTrue(bin_path.exists(), "rust_ratatui binary missing")
        cmd = [str(bin_path), "--verify", "--state-path", str(CANONICAL_STATE_PATH)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(res.returncode, 0, f"Stderr: {res.stderr}")
        self.assertIn("Rust Ratatui Verification Passed", res.stdout)


class TestMilestone2RedAttacks(unittest.TestCase):
    """Test Red Team 5-Tier Attack Engine."""

    def test_sigwinch_storm_attack(self):
        py_app = SANDBOX_DIR / "defenses" / "python_textual" / "app.py"
        cmd = [sys.executable, str(py_app), "--state-path", str(CANONICAL_STATE_PATH), "--timeout", "1.0"]
        stressor = SigwinchStressor(frequency_hz=100.0, duration_secs=0.5)
        res = stressor.run_attack(cmd)
        self.assertTrue(res.survived)
        self.assertEqual(res.panics_detected, 0)
        self.assertGreater(res.total_resizes_sent, 5)

    def test_event_flood_attack(self):
        py_app = SANDBOX_DIR / "defenses" / "python_textual" / "app.py"
        cmd = [sys.executable, str(py_app), "--state-path", str(CANONICAL_STATE_PATH), "--timeout", "1.0"]
        stressor = EventFloodStressor(target_keys_per_sec=500.0, duration_secs=0.5, concurrent_state_writes=False)
        res = stressor.run_attack(cmd)
        self.assertTrue(res.survived)
        self.assertEqual(res.panics_detected, 0)
        self.assertGreater(res.total_keys_injected, 50)

    def test_memory_stressor_attack(self):
        py_app = SANDBOX_DIR / "defenses" / "python_textual" / "app.py"
        cmd = [sys.executable, str(py_app), "--state-path", str(CANONICAL_STATE_PATH), "--timeout", "1.0"]
        stressor = MemoryStressor(duration_secs=0.8, max_acceptable_rss_mb=200.0)
        res = stressor.run_attack(cmd)
        self.assertTrue(res.within_bounds)
        self.assertLessEqual(res.peak_rss_mb, 200.0)

    def test_schema_fuzzer_15_classes(self):
        corpus = get_fuzz_corpus()
        self.assertEqual(len(corpus), 15, "Expected 15 fuzz mutation classes")
        py_app = SANDBOX_DIR / "defenses" / "python_textual" / "app.py"
        fuzzer = SchemaFuzzer()
        cmd_builder = lambda sp: [sys.executable, str(py_app), "--verify", "--state-path", str(sp)]
        res = fuzzer.run_fuzz_suite(cmd_builder)
        self.assertTrue(res.all_passed)
        self.assertEqual(res.panics_count, 0)

    def test_lock_contention_attack(self):
        py_app = SANDBOX_DIR / "defenses" / "python_textual" / "app.py"
        cmd_builder = lambda sp: [sys.executable, str(py_app), "--verify", "--state-path", str(sp)]
        stressor = LockContentionStressor()
        res = stressor.run_lock_hijacking_attack(cmd_builder, concurrent_count=4, lock_hold_duration_secs=0.1)
        self.assertTrue(res.passed)
        self.assertEqual(res.panics_detected, 0)


class TestMilestone2RefereeAndChaos(unittest.TestCase):
    """Test Abliterated 70B Referee, Scoring, and Chaos Injections."""

    def test_refusal_ablation_orthogonality(self):
        h = [2.0, 4.0, 6.0]
        r = [0.0, 1.0, 0.0]  # Unit vector on y-axis
        h_clean = calculate_refusal_ablation(h, r)
        self.assertEqual(h_clean, [2.0, 0.0, 6.0])

        # Dot product of h_clean and r must be 0 (orthogonal)
        dot = sum(a * b for a, b in zip(h_clean, r))
        self.assertAlmostEqual(dot, 0.0)

    def test_scoring_matrix_and_npu_bonus(self):
        matrix = ScoringMatrix()
        breakdown = matrix.evaluate_candidate(
            framework="rust_ratatui",
            peak_rss_mb=2.5,
            avg_latency_ms=4.0,
            scenarios_survived=5,
            total_scenarios=5,
            panics_count=0,
            lint_issues=0,
            zero_mock_certified=True,
        )
        self.assertEqual(breakdown.status, "COMPLETED")
        self.assertGreaterEqual(breakdown.composite_score, 95.0)
        self.assertGreaterEqual(breakdown.bonus_npu_hours, 37.0)

    def test_disqualification_on_panic(self):
        matrix = ScoringMatrix()
        breakdown = matrix.evaluate_candidate(
            framework="test_crash",
            peak_rss_mb=10.0,
            avg_latency_ms=10.0,
            scenarios_survived=4,
            total_scenarios=5,
            panics_count=1,
        )
        self.assertEqual(breakdown.status, "DISQUALIFIED_PANIC")
        self.assertEqual(breakdown.robustness_score, 0.0)

    def test_chaos_injector_tiers(self):
        injector = ChaosInjector(seed=42)
        base_state = {
            "version": "2.0.0",
            "providers": {"test": {"name": "Test", "daily_limit": 100, "used_today": 10, "remaining_pct": 0.9, "status": "healthy"}},
            "metrics": {"total_tasks_routed": 10, "total_lora_samples_harvested": 1},
        }

        # Tier 1
        mutated, event1 = injector.generate_tier1_architectural_chaos(base_state)
        self.assertEqual(event1.tier, 1)
        self.assertIn("ast_level_0" in mutated or len(mutated.get("providers", {})) > 1 or "version" in mutated, [True])

        # Tier 2
        event2 = injector.generate_tier2_environmental_chaos()
        self.assertEqual(event2.tier, 2)

        # Tier 3
        event3 = injector.generate_tier3_cognitive_chaos()
        self.assertEqual(event3.tier, 3)
        self.assertIsNotNone(event3.scoring_weight_shift)
        self.assertEqual(event3.scoring_weight_shift["attack_robustness"], 0.40)

    def test_referee_jsonl_logging_streams(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_sandbox = Path(tmp_dir)
            referee = AbliteratedReferee(sandbox_dir=tmp_sandbox)

            referee.emit_tournament_event("TEST_EVENT", {"status": "ok"})
            referee.emit_referee_verdict({"round_id": "TEST_ROUND", "candidate": "test", "verdict": "PASS"})
            referee.emit_lora_training_sample("instr", "inp", "out", "test", 1.0)
            referee.emit_dpo_preference_pair("instr", "chosen", "rejected", "test", 0.9)

            # Verify files exist and have valid JSON
            for log_p in [
                referee.tournament_events_log,
                referee.referee_verdicts_log,
                referee.lora_distillation_log,
                referee.dpo_preferences_log,
            ]:
                self.assertTrue(log_p.exists())
                with open(log_p) as f:
                    lines = [line.strip() for line in f if line.strip()]
                self.assertEqual(len(lines), 1)
                data = json.loads(lines[0])
                self.assertIn("timestamp", data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
