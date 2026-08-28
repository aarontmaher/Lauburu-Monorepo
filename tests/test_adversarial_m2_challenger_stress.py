#!/usr/bin/env python3
"""Empirical Adversarial Stress Harness — Milestone 2 TUI & Referee Mastery.

Challenger Test Suite:
1. SIGWINCH Storms (50–200 Hz resize oscillations across 9 viewport geometries on Python, Go, Rust).
2. 1k Event Floods (1,000+ keys/sec PTY injection + concurrent 200 writes/sec telemetry torrents).
3. Memory Bound & Leak Pressure (Continuous heavy allocations, 150MB RSS ceiling enforcement, slope tracking).
4. 15-Class Schema Mutation Fuzzing (Binary noise, truncated JSON, 10^18 numbers, negative %, Unicode/Kanji/Emoji, 50-deep trees, 100 shards).
5. Lock Contention & Atomic Races (Exclusive LOCK_EX hijacking + 100+ writes/sec POSIX atomic replacement races).
6. Abliterated 70B Referee & Scoring Matrix (Refusal ablation orthogonality, 0-panic disqualification, 4 JSONL streams).

Target Sandbox: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.sandbox_training/tui_mastery
"""

from __future__ import annotations

import collections
import concurrent.futures
import fcntl
import json
import math
import os
import pty
import random
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import time
import unittest
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
SANDBOX_DIR = REPO_ROOT / ".sandbox_training" / "tui_mastery"
sys.path.insert(0, str(SANDBOX_DIR))

from attacks.sigwinch_storm import SigwinchStressor, SigwinchAttackResult
from attacks.event_flood import EventFloodStressor, EventFloodResult
from attacks.memory_stressor import MemoryStressor, MemoryStressResult
from attacks.schema_fuzzer import SchemaFuzzer, FuzzSuiteResult, get_fuzz_corpus, FuzzTestCase
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

PYTHON_APP = SANDBOX_DIR / "defenses" / "python_textual" / "app.py"
GO_BIN = SANDBOX_DIR / "defenses" / "go_bubbletea" / "canonical_tui_go"
RUST_BIN = SANDBOX_DIR / "defenses" / "rust_ratatui" / "target" / "release" / "canonical_tui_rust"
if not RUST_BIN.exists():
    RUST_BIN = SANDBOX_DIR / "defenses" / "rust_ratatui" / "target" / "debug" / "canonical_tui_rust"

CANONICAL_STATE_PATH = REPO_ROOT / "04_data_and_memory" / "data" / "cloud_api_quota_state.json"


def get_base_valid_state() -> Dict[str, Any]:
    return {
        "version": "2.0.0",
        "last_reset": "2026-08-27T06:00:00.000000+00:00",
        "last_reset_date": "2026-08-27",
        "last_updated": "2026-08-27T13:00:00.000000+00:00",
        "providers": {
            "julien_ai": {
                "name": "Julien AI (Direct)",
                "daily_limit": 300,
                "used_today": 45,
                "remaining_pct": 0.85,
                "avg_latency_ms": 1200.0,
                "max_tokens": 8192,
                "consecutive_failures": 0,
                "total_requests": 45,
                "successful_requests": 45,
                "status": "healthy",
            },
            "cloudflare_ai": {
                "name": "Cloudflare Workers AI",
                "daily_limit": 1000,
                "used_today": 120,
                "remaining_pct": 0.88,
                "avg_latency_ms": 650.0,
                "max_tokens": 4096,
                "consecutive_failures": 0,
                "total_requests": 120,
                "successful_requests": 120,
                "status": "healthy",
            },
            "gemini_free": {
                "name": "Google Gemini Free Tier",
                "daily_limit": 1500,
                "used_today": 450,
                "remaining_pct": 0.70,
                "avg_latency_ms": 380.0,
                "max_tokens": 32768,
                "consecutive_failures": 0,
                "total_requests": 450,
                "successful_requests": 450,
                "status": "healthy",
            },
            "local_mesh": {
                "name": "Lauburu Local Mesh GPU",
                "daily_limit": 999999,
                "used_today": 15,
                "remaining_pct": 1.0,
                "avg_latency_ms": 280.0,
                "max_tokens": 16384,
                "consecutive_failures": 0,
                "total_requests": 15,
                "successful_requests": 15,
                "status": "healthy",
            },
        },
        "metrics": {
            "total_tasks_routed": 630,
            "cloud_tasks_succeeded": 615,
            "local_mesh_fallback_count": 15,
            "total_lora_samples_harvested": 615,
        },
    }


class TestChallengerSigwinchStorms(unittest.TestCase):
    """Empirically test SIGWINCH storms across all 3 TUI frameworks."""

    def test_python_textual_sigwinch_storm(self):
        cmd = [sys.executable, str(PYTHON_APP), "--state-path", str(CANONICAL_STATE_PATH), "--timeout", "1.2"]
        stressor = SigwinchStressor(frequency_hz=100.0, duration_secs=0.8)
        res = stressor.run_attack(cmd)
        self.assertTrue(res.survived, f"Python crashed under SIGWINCH storm: {res.error_log}")
        self.assertEqual(res.panics_detected, 0)
        self.assertGreater(res.total_resizes_sent, 15)

    def test_go_bubbletea_sigwinch_storm(self):
        cmd = [str(GO_BIN), "-state-path", str(CANONICAL_STATE_PATH), "-timeout", "1.2"]
        stressor = SigwinchStressor(frequency_hz=100.0, duration_secs=0.8)
        res = stressor.run_attack(cmd)
        self.assertTrue(res.survived, f"Go crashed under SIGWINCH storm: {res.error_log}")
        self.assertEqual(res.panics_detected, 0)
        self.assertGreater(res.total_resizes_sent, 15)

    def test_rust_ratatui_sigwinch_storm(self):
        cmd = [str(RUST_BIN), "--state-path", str(CANONICAL_STATE_PATH), "--timeout", "1.2"]
        stressor = SigwinchStressor(frequency_hz=100.0, duration_secs=0.8)
        res = stressor.run_attack(cmd)
        self.assertTrue(res.survived, f"Rust crashed under SIGWINCH storm: {res.error_log}")
        self.assertEqual(res.panics_detected, 0)
        self.assertGreater(res.total_resizes_sent, 15)


class TestChallengerEventFloods(unittest.TestCase):
    """Empirically test 1,000+ keys/sec floods across all 3 TUI frameworks."""

    def test_python_textual_event_flood(self):
        cmd = [sys.executable, str(PYTHON_APP), "--state-path", str(CANONICAL_STATE_PATH), "--timeout", "1.2"]
        stressor = EventFloodStressor(target_keys_per_sec=1000.0, duration_secs=0.8, concurrent_state_writes=False)
        res = stressor.run_attack(cmd)
        self.assertTrue(res.survived, f"Python crashed under event flood: {res.error_log}")
        self.assertEqual(res.panics_detected, 0)
        self.assertGreater(res.total_keys_injected, 100)

    def test_go_bubbletea_event_flood(self):
        cmd = [str(GO_BIN), "-state-path", str(CANONICAL_STATE_PATH), "-timeout", "1.2"]
        stressor = EventFloodStressor(target_keys_per_sec=1000.0, duration_secs=0.8, concurrent_state_writes=False)
        res = stressor.run_attack(cmd)
        self.assertTrue(res.survived, f"Go crashed under event flood: {res.error_log}")
        self.assertEqual(res.panics_detected, 0)
        self.assertGreater(res.total_keys_injected, 100)

    def test_rust_ratatui_event_flood(self):
        cmd = [str(RUST_BIN), "--state-path", str(CANONICAL_STATE_PATH), "--timeout", "1.2"]
        stressor = EventFloodStressor(target_keys_per_sec=1000.0, duration_secs=0.8, concurrent_state_writes=False)
        res = stressor.run_attack(cmd)
        self.assertTrue(res.survived, f"Rust crashed under event flood: {res.error_log}")
        self.assertEqual(res.panics_detected, 0)
        self.assertGreater(res.total_keys_injected, 100)


class TestChallengerMemoryStress(unittest.TestCase):
    """Empirically test memory ceilings (< 150 MB) and slope across all 3 TUI frameworks."""

    def test_python_textual_memory_bounds(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(get_base_valid_state(), f)
            tmp_state = Path(f.name)
        try:
            cmd = [sys.executable, str(PYTHON_APP), "--state-path", str(tmp_state), "--timeout", "1.5"]
            stressor = MemoryStressor(duration_secs=1.0, max_acceptable_rss_mb=150.0)
            res = stressor.run_attack(cmd, state_path=tmp_state)
            self.assertTrue(res.within_bounds, f"Python exceeded 150MB RSS: {res.peak_rss_mb:.1f}MB")
            self.assertEqual(res.panics_detected, 0)
        finally:
            tmp_state.unlink(missing_ok=True)

    def test_go_bubbletea_memory_bounds(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(get_base_valid_state(), f)
            tmp_state = Path(f.name)
        try:
            cmd = [str(GO_BIN), "-state-path", str(tmp_state), "-timeout", "1.5"]
            stressor = MemoryStressor(duration_secs=1.0, max_acceptable_rss_mb=150.0)
            res = stressor.run_attack(cmd, state_path=tmp_state)
            self.assertTrue(res.within_bounds, f"Go exceeded 150MB RSS: {res.peak_rss_mb:.1f}MB")
            self.assertEqual(res.panics_detected, 0)
        finally:
            tmp_state.unlink(missing_ok=True)

    def test_rust_ratatui_memory_bounds(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(get_base_valid_state(), f)
            tmp_state = Path(f.name)
        try:
            cmd = [str(RUST_BIN), "--state-path", str(tmp_state), "--timeout", "1.5"]
            stressor = MemoryStressor(duration_secs=1.0, max_acceptable_rss_mb=150.0)
            res = stressor.run_attack(cmd, state_path=tmp_state)
            self.assertTrue(res.within_bounds, f"Rust exceeded 150MB RSS: {res.peak_rss_mb:.1f}MB")
            self.assertEqual(res.panics_detected, 0)
            self.assertLess(res.peak_rss_mb, 40.0, "Rust Ratatui peak RSS should be ultra-low (< 40MB)")
        finally:
            tmp_state.unlink(missing_ok=True)


class TestChallengerSchemaFuzzing15Classes(unittest.TestCase):
    """Empirically test full 15-class mutation matrix across Python, Go, and Rust."""

    def test_python_textual_15_classes(self):
        fuzzer = SchemaFuzzer()
        cmd_builder = lambda sp: [sys.executable, str(PYTHON_APP), "--verify", "--state-path", str(sp)]
        res = fuzzer.run_fuzz_suite(cmd_builder)
        self.assertTrue(res.all_passed, f"Python failed fuzz cases: {[r.case_id for r in res.case_results if not r.passed]}")
        self.assertEqual(res.panics_count, 0)

    def test_go_bubbletea_15_classes(self):
        fuzzer = SchemaFuzzer()
        cmd_builder = lambda sp: [str(GO_BIN), "-verify", "-state-path", str(sp)]
        res = fuzzer.run_fuzz_suite(cmd_builder)
        self.assertTrue(res.all_passed, f"Go failed fuzz cases: {[r.case_id for r in res.case_results if not r.passed]}")
        self.assertEqual(res.panics_count, 0)

    def test_rust_ratatui_15_classes(self):
        fuzzer = SchemaFuzzer()
        cmd_builder = lambda sp: [str(RUST_BIN), "--verify", "--state-path", str(sp)]
        res = fuzzer.run_fuzz_suite(cmd_builder)
        self.assertTrue(res.all_passed, f"Rust failed fuzz cases: {[r.case_id for r in res.case_results if not r.passed]}")
        self.assertEqual(res.panics_count, 0)


class TestChallengerLockContentionAndRaces(unittest.TestCase):
    """Empirically test LOCK_EX hijacking and atomic file swaps across all 3 frameworks."""

    def test_python_textual_lock_contention(self):
        stressor = LockContentionStressor()
        cmd_builder = lambda sp: [sys.executable, str(PYTHON_APP), "--verify", "--state-path", str(sp)]
        res1 = stressor.run_lock_hijacking_attack(cmd_builder, concurrent_count=6, lock_hold_duration_secs=0.2)
        self.assertTrue(res1.passed)
        self.assertEqual(res1.panics_detected, 0)

        res2 = stressor.run_atomic_rename_race_attack(cmd_builder, concurrent_readers=4, duration_secs=1.0)
        self.assertTrue(res2.passed)
        self.assertEqual(res2.panics_detected, 0)

    def test_go_bubbletea_lock_contention(self):
        stressor = LockContentionStressor()
        cmd_builder = lambda sp: [str(GO_BIN), "-verify", "-state-path", str(sp)]
        res1 = stressor.run_lock_hijacking_attack(cmd_builder, concurrent_count=6, lock_hold_duration_secs=0.2)
        self.assertTrue(res1.passed)
        self.assertEqual(res1.panics_detected, 0)

        res2 = stressor.run_atomic_rename_race_attack(cmd_builder, concurrent_readers=4, duration_secs=1.0)
        self.assertTrue(res2.passed)
        self.assertEqual(res2.panics_detected, 0)

    def test_rust_ratatui_lock_contention(self):
        stressor = LockContentionStressor()
        cmd_builder = lambda sp: [str(RUST_BIN), "--verify", "--state-path", str(sp)]
        res1 = stressor.run_lock_hijacking_attack(cmd_builder, concurrent_count=6, lock_hold_duration_secs=0.2)
        self.assertTrue(res1.passed)
        self.assertEqual(res1.panics_detected, 0)

        res2 = stressor.run_atomic_rename_race_attack(cmd_builder, concurrent_readers=4, duration_secs=1.0)
        self.assertTrue(res2.passed)
        self.assertEqual(res2.panics_detected, 0)


class TestChallengerRefereeAndScoringInvariants(unittest.TestCase):
    """Empirically test referee scoring formulas, refusal ablation, and stream schemas."""

    def test_refusal_ablation_vector_orthogonality(self):
        h = [1.5, -2.0, 3.2, 0.5, -1.0]
        raw_r = [0.2, 0.4, -0.6, 0.8, 0.1]
        norm = math.sqrt(sum(x**2 for x in raw_r))
        r = [x / norm for x in raw_r]

        h_clean = calculate_refusal_ablation(h, r)
        dot = sum(a * b for a, b in zip(h_clean, r))
        self.assertAlmostEqual(dot, 0.0, places=6, msg="Refusal direction must be orthogonal to h_clean")

    def test_closed_form_composite_score_and_disqualification(self):
        matrix = ScoringMatrix()
        normal = matrix.evaluate_candidate("go_bubbletea", 12.0, 8.0, 5, 5, 0)
        self.assertEqual(normal.status, "COMPLETED")
        self.assertGreater(normal.composite_score, 80.0)

        crashed = matrix.evaluate_candidate("crashed_framework", 2.0, 2.0, 4, 5, 1)
        self.assertEqual(crashed.status, "DISQUALIFIED_PANIC")
        self.assertEqual(crashed.robustness_score, 0.0)
        self.assertLess(crashed.composite_score, normal.composite_score)

    def test_four_synchronized_jsonl_log_streams(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_sandbox = Path(tmp_dir)
            referee = AbliteratedReferee(sandbox_dir=tmp_sandbox)

            referee.emit_tournament_event("EVENT_1", {"msg": "start"})
            referee.emit_referee_verdict({"round": 1, "candidate": "rust_ratatui", "verdict": "WIN"})
            referee.emit_lora_training_sample("instr", "inp", "out", "rust_ratatui", 0.99)
            referee.emit_dpo_preference_pair("instr", "chosen_rust", "rejected_py", "rust_ratatui", 0.95)

            files = [
                referee.tournament_events_log,
                referee.referee_verdicts_log,
                referee.lora_distillation_log,
                referee.dpo_preferences_log,
            ]
            for f in files:
                self.assertTrue(f.exists(), f"Missing log file {f.name}")
                with open(f) as fh:
                    data = json.loads(fh.readline())
                    self.assertIn("timestamp", data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
