#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Movesense 24/7 Ingestion & DSP Service
"""

import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "03_biometrics_and_telemetry"))

from movesense_247_service import MovesenseContinuousDaemon


class TestMovesense247Service(unittest.TestCase):
    def setUp(self):
        self.daemon = MovesenseContinuousDaemon()

    def test_kamath_filter_normal_intervals(self):
        # Baseline intervals around 850ms (~70 bpm)
        self.daemon.rr_buffer = [850.0, 852.0, 848.0]
        normal_rr = 855.0
        filtered = self.daemon.apply_kamath_20_filter(normal_rr)
        self.assertEqual(filtered, 855.0)

    def test_kamath_filter_rejects_emg_spikes(self):
        # Establish stable median of 850ms
        self.daemon.rr_buffer = [850.0, 852.0, 848.0, 851.0, 849.0]
        # Noise spike: 400ms (> 50% deviation from 850ms)
        spike_rr = 400.0
        filtered = self.daemon.apply_kamath_20_filter(spike_rr)
        # Should replace with running median (850.0)
        self.assertEqual(filtered, 850.0)

    def test_kamath_filter_rejects_impossible_rr(self):
        # Biologically impossible RR (<250ms or >2400ms)
        self.assertIsNone(self.daemon.apply_kamath_20_filter(150.0))
        self.assertIsNone(self.daemon.apply_kamath_20_filter(3000.0))

    def test_hrv_rmssd_calculation(self):
        # Constant intervals -> RMSSD = 0
        self.daemon.rr_buffer = [800.0, 800.0, 800.0, 800.0, 800.0]
        metrics = self.daemon.calculate_hrv_metrics()
        self.assertEqual(metrics["rmssd_ms"], 0.0)

        # Alternating intervals: 800, 840, 800, 840 -> diffs are 40 -> RMSSD = 40
        self.daemon.rr_buffer = [800.0, 840.0, 800.0, 840.0, 800.0]
        metrics2 = self.daemon.calculate_hrv_metrics()
        self.assertAlmostEqual(metrics2["rmssd_ms"], 40.0, places=1)
        self.assertEqual(metrics2["dfa_alpha1"], 0.82)

    def test_ptt_bp_estimation(self):
        # Resting baseline
        sys_bp, dia_bp, map_bp = self.daemon.calculate_ptt_bp(hr=70.0, rmssd=50.0)
        self.assertEqual(sys_bp, 118)
        self.assertEqual(dia_bp, 76)
        self.assertEqual(map_bp, 90.0)

        # Elevated heart rate (workout)
        sys_bp2, dia_bp2, map_bp2 = self.daemon.calculate_ptt_bp(hr=140.0, rmssd=15.0)
        self.assertGreater(sys_bp2, 135)
        self.assertGreater(dia_bp2, 85)

    def test_zone_classification(self):
        self.assertIn("ZONE 1", self.daemon.classify_zone(95.0, 1.0))
        self.assertIn("ZONE 2", self.daemon.classify_zone(130.0, 0.82))
        self.assertIn("ZONE 3", self.daemon.classify_zone(155.0, 0.65))
        self.assertIn("ZONE 4+", self.daemon.classify_zone(175.0, 0.45))

    def test_rule_0_standby_mode(self):
        self.daemon.write_standby_snapshots()
        self.assertFalse(self.daemon.is_connected)
        # Check snapshot file
        stream_file = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/movesense_live_stream.json")
        self.assertTrue(stream_file.exists())
        import json
        with open(stream_file, "r") as f:
            data = json.load(f)
            self.assertFalse(data["connected"])
            self.assertIsNone(data["heart_rate_bpm"])
            self.assertEqual(data["stream_mode"], "AWAITING_BLE_HARDWARE (Rule #0 Certified)")


if __name__ == "__main__":
    unittest.main()
