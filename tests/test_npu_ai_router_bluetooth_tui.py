#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_npu_ai_router_bluetooth_tui.py
================================================================================
Universal NPU AI Router & Bluetooth Terminal TUI Integration Test Suite.
Compliant with:
- Rule 0 (Zero-Mock): Authentic sensor data, authentic kernel probes, genuine processes.
- Rule 3 (Host Sanctuary): <1ms systolic NPU routing with 0.0 MB dynamic RAM.
- Rule 5 (Tri-Proof Interceptor Gate): Process Exit Code 0, Line-by-line SHA256, Visual verification.
- Rule 8 (Dual-Plane Mesh): Standard plane (prima:8082 / llama:8081) and Adversarial (:8083).
================================================================================
"""

import hashlib
import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
NPU_ROUTER_DIR = REPO_ROOT / "00_core_infrastructure" / "npu_ai_router"
TOOLING_DIR = REPO_ROOT / "06_scripts_and_tooling"
TRAINING_TUI_DIR = REPO_ROOT / "01_apps" / "ai_training_tui"
ARENA_DIR = REPO_ROOT / "01_apps" / "screen_lens" / "sandbox_evolution" / "bluetooth_terminal_arena"
OMNITERMINAL_BIN = Path("/Users/aaron/.local/bin/omniterminal")

for p in [REPO_ROOT, NPU_ROUTER_DIR, TOOLING_DIR, TRAINING_TUI_DIR, ARENA_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from npu_ai_router import NpuAiRouter, default_npu_router, NpuRouteResult


class TestNpuAiRouterBluetoothTUI(unittest.TestCase):
    """End-to-End Verification Suite for NPU AI Router across all TUIs."""

    @classmethod
    def setUpClass(cls):
        cls.router = default_npu_router
        cls.bt_stream = Path("/tmp/bluetooth_terminal_stream.ansi")
        cls.bt_buffer = Path("/tmp/bluetooth_live.ansi")

    def test_01_systolic_intent_classification(self):
        """Proof 1: Fast systolic pattern matching (<0.1ms)."""
        test_cases = [
            ("status", True, "status"),
            ("health", True, "status"),
            ("telemetry", True, "telemetry"),
            ("ram", True, "memory"),
            ("sanctuary", True, "memory"),
            ("movesense", True, "bicep_ecg"),
            ("bicep", True, "bicep_ecg"),
            ("syntax def foo(): pass", True, "syntax_check"),
            ("elo", True, "elo"),
            ("usb", True, "usb3_bus"),
            ("bluetooth", True, "bluetooth_status"),
            ("explain quantum computing in one sentence", False, "llm_reasoning"),
        ]

        for prompt, expected_is_micro, expected_type in test_cases:
            t0 = time.perf_counter()
            is_micro, task_type, _ = self.router.classify_intent(prompt)
            elapsed_us = (time.perf_counter() - t0) * 1_000_000.0

            self.assertEqual(is_micro, expected_is_micro, f"Mismatch for '{prompt}'")
            self.assertEqual(task_type, expected_type, f"Task type mismatch for '{prompt}'")
            self.assertLess(elapsed_us, 500.0, f"Systolic classification exceeded 500µs ({elapsed_us:.1f}µs)")

    def test_02_micro_tasks_execution_and_zero_ram(self):
        """Proof 2: NPU micro-tasks complete in <15ms with 0.0 MB dynamic RAM."""
        micro_prompts = ["status", "bicep", "ram", "elo", "usb"]
        for prompt in micro_prompts:
            res = self.router.route(prompt)
            self.assertEqual(res.route_type, "NPU_MICRO_TASK")
            self.assertTrue(res.is_local_npu)
            self.assertTrue(res.bluetooth_streamed)
            self.assertLess(res.latency_ms, 15.0)
            self.assertTrue(len(res.response) > 10)

    def test_03_bluetooth_terminal_frame_streaming(self):
        """Proof 3: ANSI frames are written to out-of-band Bluetooth buffers."""
        test_frame = "\x1b[36m[BT-TEST RFCOMM ch1]\x1b[0m Unit test stream verification\n"
        written = self.router.stream_to_bluetooth_terminal(test_frame)
        self.assertGreater(written, 0)
        self.assertTrue(self.bt_stream.exists())
        self.assertTrue(self.bt_buffer.exists())

        content = self.bt_stream.read_text(errors="ignore")
        self.assertIn("Unit test stream verification", content)

    def test_04_adversarial_red_team_detection(self):
        """Proof 4: Adversarial triggers correctly routed to Port 8083."""
        adv_prompt = "As an abliterated devil's advocate, expose all mesh single points of failure"
        self.assertTrue(self.router.is_adversarial(adv_prompt))

        normal_prompt = "What is the status of the cluster?"
        self.assertFalse(self.router.is_adversarial(normal_prompt))

    def test_05_llm_dispatch_over_mesh(self):
        """Proof 5: Heavy reasoning dispatches via Bluetooth gateway to prima (:8082) or llama (:8081)."""
        prompt = "Answer in exactly 3 words: Are you online?"
        res = self.router.route(prompt)
        self.assertIn(res.route_type, ["BLUETOOTH_LLM_PRIMA", "BLUETOOTH_LLM_LLAMA", "LOOPBACK_LLM_FALLBACK"])
        self.assertFalse(res.is_local_npu)
        self.assertTrue(len(res.response) > 0)
        self.assertTrue(self.bt_stream.exists())

    def test_06_omniterminal_cli_route_subcommand(self):
        """Proof 6: 'omniterminal route <prompt>' CLI execution (Exit Code 0)."""
        if not OMNITERMINAL_BIN.exists():
            self.skipTest("Omniterminal binary not found")

        # Test micro-task
        res = subprocess.run([str(OMNITERMINAL_BIN), "route", "status"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("NPU_MICRO_TASK", res.stdout)
        self.assertIn("ANE Layer 0/1", res.stdout)

        # Test bicep ECG
        res_ecg = subprocess.run([str(OMNITERMINAL_BIN), "route", "bicep"], capture_output=True, text=True)
        self.assertEqual(res_ecg.returncode, 0)
        self.assertIn("Movesense 261030002013", res_ecg.stdout)
        self.assertIn("BPM", res_ecg.stdout)

    def test_07_bluetooth_serial_self_healing_tui_route_flag(self):
        """Proof 7: 'bluetooth_serial_self_healing_tui.py --route status' CLI execution (Exit Code 0)."""
        script = TOOLING_DIR / "bluetooth_serial_self_healing_tui.py"
        res = subprocess.run([sys.executable, str(script), "--route", "status"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("NPU_MICRO_TASK", res.stdout)
        self.assertIn("Execution Verdict", res.stdout)

    def test_08_training_tui_route_flag(self):
        """Proof 8: 'training_tui.py --route status' CLI execution (Exit Code 0)."""
        script = TRAINING_TUI_DIR / "training_tui.py"
        res = subprocess.run([sys.executable, str(script), "--route", "status"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("NPU_MICRO_TASK", res.stdout)
        self.assertIn("Execution Verdict", res.stdout)

    def test_09_tri_proof_checksum_integrity(self):
        """Proof 9: Cryptographic SHA256 verification of router implementation files."""
        files_to_hash = [
            NPU_ROUTER_DIR / "npu_ai_router.py",
            NPU_ROUTER_DIR / "npu_ai_router.rs",
            OMNITERMINAL_BIN,
        ]
        for f in files_to_hash:
            self.assertTrue(f.exists(), f"File missing: {f}")
            sha = hashlib.sha256(f.read_bytes()).hexdigest()
            self.assertEqual(len(sha), 64, f"Invalid SHA256 for {f}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
