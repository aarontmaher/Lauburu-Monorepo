#!/usr/bin/env python3
"""
Unit & Integration Tests for Live RAM Governor Sentinel
======================================================
Subsystem: 02_ai_models_and_inference/
Validates:
- Live physical memory capture (Total, Used, Available, Inactive, Wired)
- Top process RSS parsing
- Dynamic Governor Tier calculation
- Generation of the Obsidian Report and JSONL streaming
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
AI_DIR = REPO_ROOT / "02_ai_models_and_inference"
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from live_ram_governor_sentinel import (
    LiveHostRAMSnapshot,
    LiveRAMGovernorSentinel
)


class TestLiveRAMGovernorSentinel(unittest.TestCase):

    def setUp(self):
        self.sentinel = LiveRAMGovernorSentinel()

    def test_01_capture_live_snapshot(self):
        snap = self.sentinel.capture_live_snapshot()
        self.assertIsInstance(snap, LiveHostRAMSnapshot)
        self.assertGreater(snap.total_ram_gb, 8.0)
        self.assertGreater(snap.used_percent, 10.0)
        self.assertLessEqual(snap.used_percent, 100.0)
        self.assertGreater(len(snap.top_processes), 0)

    def test_02_governor_tier_logic(self):
        snap = self.sentinel.capture_live_snapshot()
        self.assertIn("TIER_", snap.governor_tier)
        self.assertGreater(len(snap.governor_action), 10)

    def test_03_report_and_telemetry(self):
        self.sentinel.capture_live_snapshot()
        report_path = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "LIVE_MESH_RAM_GOVERNOR_STATUS_2026.md"
        telemetry_path = REPO_ROOT / "04_data_and_memory" / "lora_datasets" / "ram_governor_live_telemetry.jsonl"
        self.assertTrue(report_path.exists())
        self.assertTrue(telemetry_path.exists())


if __name__ == "__main__":
    unittest.main()
