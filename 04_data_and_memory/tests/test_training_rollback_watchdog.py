# -*- coding: utf-8 -*-
"""
Unit Test Suite for TrainingRollbackWatchdog & Closed-Loop Auto-Rollback
========================================================================
Subsystem: 04_data_and_memory/tests/test_training_rollback_watchdog.py
Milestone: M4 / Extension E1 — Closed-Loop Auto-Rollback Watchdog

Covers:
- Checkpoint registration, certification, and latest retrieval
- Real-time step metric tracking across loss, memory, and TUI latency
- Loss divergence detection (NaN, Inf, spikes > 3x, absolute ceiling)
- Memory leak detection (RAM > 85%, headroom < 2.50GB, RSS growth rate)
- TUI frame drop detection (>50ms render latency)
- Obsidian Vault post-mortem note snapshotting & JSONL event logging
- Rollback execution, callback triggers, and training resumption
"""

import json
import math
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent.parent
DATA_DIR = REPO_ROOT / "04_data_and_memory"

if str(DATA_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from training_rollback_watchdog import (
    TrainingRollbackWatchdog,
    CheckpointRecord,
    StepMetricSnapshot,
    DEFAULT_MAX_LOSS_SPIKE_FACTOR,
    DEFAULT_MAX_RAM_USED_PCT,
    DEFAULT_MIN_RAM_HEADROOM_GB,
    DEFAULT_MAX_TUI_LATENCY_MS
)


class TestTrainingRollbackWatchdog(unittest.TestCase):
    """Unit tests for TrainingRollbackWatchdog."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="watchdog_test_"))
        self.obsidian_dir = self.temp_dir / "obsidian_vault" / "ROLLBACK_DIAGNOSTICS"
        self.log_file = self.temp_dir / "training_rollback_events.jsonl"
        self.watchdog = TrainingRollbackWatchdog(
            obsidian_dir=self.obsidian_dir,
            rollback_log_file=self.log_file,
            sliding_window_size=30,
            auto_rollback=True,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_checkpoint_registration_and_retrieval(self):
        """Registers checkpoints and retrieves the latest certified one."""
        self.assertIsNone(self.watchdog.get_latest_certified_checkpoint())

        cp1 = self.watchdog.register_checkpoint(
            checkpoint_id="ckpt_step_100",
            checkpoint_path="/models/ckpt_100",
            step=100,
            loss=1.85,
            is_certified=True,
        )
        self.assertEqual(cp1.checkpoint_id, "ckpt_step_100")
        self.assertEqual(self.watchdog.get_latest_certified_checkpoint().checkpoint_id, "ckpt_step_100")

        # Register higher step checkpoint
        cp2 = self.watchdog.register_checkpoint(
            checkpoint_id="ckpt_step_200",
            checkpoint_path="/models/ckpt_200",
            step=200,
            loss=1.42,
            is_certified=True,
        )
        self.assertEqual(self.watchdog.get_latest_certified_checkpoint().checkpoint_id, "ckpt_step_200")

        # Register uncertified checkpoint (should not override certified)
        self.watchdog.register_checkpoint(
            checkpoint_id="ckpt_step_250_uncertified",
            checkpoint_path="/models/ckpt_250",
            step=250,
            loss=1.35,
            is_certified=False,
        )
        self.assertEqual(self.watchdog.get_latest_certified_checkpoint().checkpoint_id, "ckpt_step_200")

    def test_healthy_step_metric_recording(self):
        """Records healthy metrics across multiple steps without triggering violations."""
        for step in range(1, 15):
            healthy, status, diag = self.watchdog.record_step_metrics(
                step=step,
                loss=2.0 - (step * 0.05),
                ram_used_pct=60.0 + step * 0.5,
                rss_mb=4000.0,
                ram_headroom_gb=5.0,
                tui_latency_ms=15.0,
            )
            self.assertTrue(healthy)
            self.assertEqual(status, "HEALTHY")
            self.assertEqual(len(diag["violations"]), 0)

        status_dict = self.watchdog.get_status()
        self.assertEqual(status_dict["total_steps_monitored"], 14)
        self.assertEqual(status_dict["total_rollbacks_triggered"], 0)
        self.assertTrue(status_dict["is_training_active"])

    def test_loss_divergence_nan_detection(self):
        """Detects NaN loss and executes rollback."""
        self.watchdog.register_checkpoint("ckpt_stable", "/models/stable", step=50, loss=1.5)

        healthy, status, diag = self.watchdog.record_step_metrics(
            step=51,
            loss=float("nan"),
            ram_used_pct=65.0,
            ram_headroom_gb=4.5,
            tui_latency_ms=12.0,
        )
        self.assertFalse(healthy)
        self.assertIn("LOSS_DIVERGENCE", status)
        self.assertIn("NaN", status)
        self.assertTrue(diag.get("rollback_executed"))

        # Verify training halted
        self.assertFalse(self.watchdog.get_status()["is_training_active"])

    def test_loss_divergence_inf_detection(self):
        """Detects Inf loss and executes rollback."""
        self.watchdog.register_checkpoint("ckpt_stable", "/models/stable", step=50, loss=1.5)

        healthy, status, _ = self.watchdog.record_step_metrics(
            step=51,
            loss=float("inf"),
        )
        self.assertFalse(healthy)
        self.assertIn("Inf", status)

    def test_loss_divergence_spike_detection(self):
        """Detects loss spiking > 3.0x above rolling baseline."""
        self.watchdog.register_checkpoint("ckpt_stable", "/models/stable", step=30, loss=1.2)

        # Feed 5 stable baseline steps (~1.20)
        for s in range(1, 6):
            self.watchdog.record_step_metrics(step=s, loss=1.20)

        # Sudden spike to 5.50 (> 3.0x baseline 1.20)
        healthy, status, diag = self.watchdog.record_step_metrics(step=6, loss=5.50)
        self.assertFalse(healthy)
        self.assertIn("LOSS_DIVERGENCE", status)
        self.assertIn("spiked > 3.0x", status)

    def test_loss_divergence_absolute_ceiling_breach(self):
        """Detects loss exceeding absolute maximum ceiling (12.0)."""
        healthy, status, _ = self.watchdog.record_step_metrics(step=1, loss=18.5)
        self.assertFalse(healthy)
        self.assertIn("exceeds absolute ceiling", status)

    def test_memory_leak_ram_ceiling_breach(self):
        """Detects Host RAM exceeding 85.0% ceiling."""
        healthy, status, diag = self.watchdog.record_step_metrics(
            step=10,
            loss=1.2,
            ram_used_pct=88.5,
            ram_headroom_gb=3.0,
        )
        self.assertFalse(healthy)
        self.assertIn("MEMORY_LEAK", status)
        self.assertIn("exceeds safety ceiling (85.0%)", status)

    def test_memory_headroom_violation(self):
        """Detects RAM headroom dropping below minimum (2.50 GB)."""
        healthy, status, _ = self.watchdog.record_step_metrics(
            step=10,
            loss=1.2,
            ram_used_pct=75.0,
            ram_headroom_gb=1.80,
        )
        self.assertFalse(healthy)
        self.assertIn("below minimum (2.50 GB)", status)

    def test_tui_frame_drop_detection(self):
        """Detects TUI render latency exceeding 50.0ms budget."""
        healthy, status, diag = self.watchdog.record_step_metrics(
            step=25,
            loss=1.2,
            tui_latency_ms=78.5,
        )
        self.assertFalse(healthy)
        self.assertIn("TUI_FRAME_DROP", status)
        self.assertIn("exceeds 50ms", status)

    def test_obsidian_diagnostics_snapshot_content(self):
        """Verifies post-mortem Markdown note format, YAML frontmatter, and Wikilinks in Obsidian."""
        self.watchdog.register_checkpoint("ckpt_base_42", "/models/42", step=42, loss=1.15)
        
        # Trigger failure
        self.watchdog.record_step_metrics(
            step=43,
            loss=float("nan"),
            ram_used_pct=70.0,
            ram_headroom_gb=4.0,
        )

        notes = list(self.obsidian_dir.glob("ROLLBACK_DIAGNOSTICS_*.md"))
        self.assertGreaterEqual(len(notes), 1)

        note_content = notes[0].read_text(encoding="utf-8")
        self.assertIn("---", note_content)
        self.assertIn("status: \"ROLLBACK_EXECUTED\"", note_content)
        self.assertIn("restored_checkpoint: \"ckpt_base_42\"", note_content)
        self.assertIn("NaN", note_content)
        self.assertIn("[[Index]]", note_content)
        self.assertIn("[[CANONICAL_PROJECT_AND_STORAGE_RULE]]", note_content)
        self.assertIn("[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]", note_content)

    def test_rollback_event_jsonl_logging(self):
        """Verifies failure events are appended to JSONL telemetry log."""
        self.watchdog.register_checkpoint("ckpt_1", "/models/1", step=10, loss=1.0)
        self.watchdog.record_step_metrics(step=11, loss=25.0)

        self.assertTrue(self.log_file.exists())
        lines = self.log_file.read_text(encoding="utf-8").strip().split("\n")
        self.assertGreaterEqual(len(lines), 1)
        event = json.loads(lines[-1])
        self.assertEqual(event["event"], "TRAINING_AUTO_ROLLBACK")
        self.assertEqual(event["target_checkpoint_id"], "ckpt_1")
        self.assertIn("exceeds absolute ceiling", event["reason"])

    def test_rollback_callback_execution(self):
        """Executes registered callbacks upon rollback with event payload."""
        callback_payloads = []

        def my_rollback_handler(payload):
            callback_payloads.append(payload)
            return "HANDLER_OK"

        self.watchdog.register_rollback_callback(my_rollback_handler)
        self.watchdog.register_checkpoint("ckpt_cb", "/models/cb", step=5, loss=1.1)
        self.watchdog.trigger_rollback(reason="Manual Test Trigger")

        self.assertEqual(len(callback_payloads), 1)
        self.assertEqual(callback_payloads[0]["target_checkpoint_id"], "ckpt_cb")
        self.assertEqual(callback_payloads[0]["reason"], "Manual Test Trigger")

    def test_sliding_window_eviction(self):
        """Sliding window maintains at most window_size entries."""
        for s in range(50):
            self.watchdog.record_step_metrics(step=s, loss=1.0)

        status = self.watchdog.get_status()
        self.assertEqual(status["sliding_history_length"], 30)

    def test_training_resumption(self):
        """Allows operator to resume training after rollback."""
        self.watchdog.trigger_rollback(reason="Test")
        self.assertFalse(self.watchdog.get_status()["is_training_active"])

        self.watchdog.resume_training()
        self.assertTrue(self.watchdog.get_status()["is_training_active"])
        self.assertEqual(self.watchdog.get_status()["last_health_status"], "HEALTHY")


if __name__ == "__main__":
    unittest.main()
