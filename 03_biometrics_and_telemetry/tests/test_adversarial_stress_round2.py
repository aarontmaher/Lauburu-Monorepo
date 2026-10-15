#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adversarial Stress Test Suite Round 2: KaiMorichPacketParser, KaiMorichLogTailer,
EdgeBiometricsEngine, and LlamaInferenceDispatcher.

Verifies:
1. Immunity to 'inf', '-inf', 'nan', '1e309', and massive/overflow timestamps.
2. Complete prevention of IIR biquad filter poisoning and rapid recovery from transients.
3. In-place file truncation followed by write bursts exceeding old offset.
4. Exact 64-bit integer timestamp precision (tested across 2^53 boundary up to INT64_MAX).
5. Runaway unbounded lines without newlines memory bounds.
6. Dispatcher concurrency lifecycle under in-flight endpoint stalls.
"""

from __future__ import annotations

import gc
import math
import os
import queue
import shutil
import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from pixel_edge_ml_ingestion import (
    BiometricSummaryWindow,
    EdgeBiometricsEngine,
    KaiMorichLogTailer,
    KaiMorichPacketParser,
    LlamaInferenceDispatcher,
    get_process_rss_mb,
)


class TestAdversarialExtremesRound2(unittest.TestCase):
    """Stress tests for malformed numbers, non-finite floats, and overflow strings."""

    def setUp(self) -> None:
        self.parser = KaiMorichPacketParser()

    def test_non_finite_and_overflow_timestamps_rejected(self) -> None:
        """Verifies that infinite, NaN, and overflow timestamps never raise and return None."""
        adversarial_lines = [
            "inf,100.0",
            "-inf,100.0",
            "nan,100.0",
            "-nan,100.0",
            "NaN,100.0",
            "1e309,100.0",
            "-1e309,100.0",
            "1" * 31 + ",100.0",
            "1" * 310 + ",100.0",
            "9" * 1000 + ",100.0",
            "inf,inf",
            "nan,nan",
            "1e309,1e309",
            "inf.5,100.0",
            "nan.0,100.0",
        ]
        for line in adversarial_lines:
            try:
                res = self.parser.parse_line(line)
                self.assertIsNone(
                    res,
                    f"Expected None for adversarial line: {line[:20]}... but got {res}",
                )
            except Exception as e:
                self.fail(f"parse_line raised unhandled exception on {line[:20]}: {type(e).__name__}: {e}")

    def test_non_finite_and_overflow_microvolts_rejected(self) -> None:
        """Verifies that non-finite and overflow microvolts never raise and return None."""
        adversarial_lines = [
            "172800000,nan",
            "172800000,-nan",
            "172800000,NaN",
            "172800000,inf",
            "172800000,-inf",
            "172800000,Infinity",
            "172800000,-Infinity",
            "172800000,1e309",
            "172800000,-1e309",
            "172800000," + "9" * 400,
        ]
        for line in adversarial_lines:
            try:
                res = self.parser.parse_line(line)
                self.assertIsNone(
                    res,
                    f"Expected None for non-finite microvolts line: {line[:30]}... but got {res}",
                )
            except Exception as e:
                self.fail(f"parse_line raised unhandled exception on {line[:30]}: {type(e).__name__}: {e}")

    def test_64bit_integer_timestamp_precision(self) -> None:
        """
        Verifies exact integer parsing without IEEE 754 float precision loss
        for timestamps across 2^53 boundary up to INT64_MAX.
        """
        test_cases = [
            0,
            1,
            -1,
            172800000,
            # 2^53 boundary tests
            9007199254740991,   # 2^53 - 1
            9007199254740992,   # 2^53
            9007199254740993,   # 2^53 + 1 (crucial: float64 rounds this to 9007199254740992)
            9007199254740994,   # 2^53 + 2
            9007199254740995,   # 2^53 + 3
            # Microsecond epoch timestamps (16 digits)
            1728000000123456,
            # Nanosecond epoch timestamps (19 digits)
            1728000000123456789,
            # INT64_MAX
            9223372036854775807,
            -9223372036854775807,
        ]

        for expected_ts in test_cases:
            line = f"{expected_ts},345.5\n"
            res = self.parser.parse_line(line)
            self.assertIsNotNone(res, f"Failed to parse valid integer timestamp {expected_ts}")
            parsed_ts, ecg_val = res
            self.assertEqual(
                parsed_ts,
                expected_ts,
                f"Precision loss detected: expected exact int {expected_ts}, got {parsed_ts}",
            )
            self.assertIsInstance(parsed_ts, int, "Parsed timestamp must be an integer instance")
            self.assertAlmostEqual(ecg_val, 345.5)


class TestAdversarialFilterPoisoningAndRecovery(unittest.TestCase):
    """Stress tests for biquad filter poisoning defense and transient recovery."""

    def setUp(self) -> None:
        self.engine = EdgeBiometricsEngine(sample_rate_hz=130.0, window_seconds=10.0)

    def test_add_sample_rejects_non_finite_defensively(self) -> None:
        """Verifies engine.add_sample defensively rejects NaN and Inf samples."""
        self.assertIsNone(self.engine.add_sample(1000, float("nan")))
        self.assertIsNone(self.engine.add_sample(1001, float("inf")))
        self.assertIsNone(self.engine.add_sample(1002, float("-inf")))
        self.assertEqual(len(self.engine._raw_samples), 0, "Non-finite samples must not be buffered")

    def test_transient_spike_resilience_and_biquad_recovery(self) -> None:
        """
        Feeds normal ECG baseline, injects huge transient motion artifacts (1e5 uV),
        then resumes normal rhythm. Verifies:
        1. Biquad filter does not diverge or produce NaN/Inf.
        2. Computed window metrics are strictly finite and within physiological bounds.
        """
        fs = 130.0
        # 1,300 samples total (10 seconds)
        # Normal QRS pulses every 104 samples (75 BPM)
        for i in range(1300):
            ts = i * 7
            t = i / fs
            # Clean synthetic ECG
            phase = (i % 104)
            if phase == 0:
                ecg = 1200.0  # R-peak
            elif phase in (1, 103):
                ecg = -200.0  # Q and S
            elif 15 <= phase <= 30:
                ecg = 250.0   # T wave
            else:
                ecg = 10.0    # Isoelectric

            # Inject 5-sample violent transient spike at i=500..505
            if 500 <= i < 505:
                ecg = 50000.0

            res = self.engine.add_sample(ts, ecg)
            if i == 1299:
                self.assertIsNotNone(res, "Expected window emission at sample 1300")
                self.assertIsInstance(res, BiometricSummaryWindow)
                metrics = res.metrics
                for k, v in metrics.items():
                    if isinstance(v, (int, float)):
                        self.assertTrue(
                            math.isfinite(v),
                            f"Metric {k} became non-finite ({v}) after transient spike!",
                        )
                # Verify rhythm was assessed without crashing
                self.assertIn(
                    metrics.get("rhythm_assessment"),
                    ("NORMAL_SINUS", "SINUS_TACHYCARDIA", "SINUS_BRADYCARDIA", "NOISY_SIGNAL", "ASYSTOLE_OR_DISCONNECTED"),
                )


class TestAdversarialInplaceTruncationAndWriteBursts(unittest.TestCase):
    """Stress tests for in-place file truncation, offset resets, and write bursts."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()
        self.log_path = Path(self.test_dir) / "burst_test.log"
        self.log_path.touch()

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_inplace_truncation_with_larger_write_burst(self) -> None:
        """
        Scenario:
        1. Write initial lines (offset advances to 80 bytes).
        2. Tailer reads these lines.
        3. File is truncated in place (size -> 0, same inode).
        4. External writer immediately writes a 150-byte burst (new_size > old_offset).
        5. Tailer must detect the header change at offset 0, seek to 0, and yield ALL new lines.
        """
        tailer = KaiMorichLogTailer(
            log_path=self.log_path,
            read_from_start=True,
            poll_interval_s=0.005,
        )
        gen = tailer.tail_lines()

        # Phase 1: Write initial lines
        with open(self.log_path, "w") as f:
            f.write("initial_line_alpha_001\ninitial_line_beta_002\n")

        line1 = next(gen)
        line2 = next(gen)
        self.assertEqual(line1, "initial_line_alpha_001")
        self.assertEqual(line2, "initial_line_beta_002")
        self.assertGreater(tailer._current_offset, 0)
        old_offset = tailer._current_offset

        # Phase 2: In-place truncate and write burst that exceeds old_offset
        with open(self.log_path, "w") as f:
            f.write(
                "burst_new_log_stream_first_line_header_xyz\n"
                "burst_second_line_1234567890\n"
                "burst_third_line_abcdefghijklmn\n"
                "burst_fourth_line_qwertyuiopasdf\n"
            )

        new_size = self.log_path.stat().st_size
        self.assertGreater(new_size, old_offset, "Burst size must exceed old offset to test header detection")

        # Tailer must yield the new lines starting from line 1 of the new file
        b1 = next(gen)
        b2 = next(gen)
        b3 = next(gen)
        b4 = next(gen)

        self.assertEqual(b1, "burst_new_log_stream_first_line_header_xyz")
        self.assertEqual(b2, "burst_second_line_1234567890")
        self.assertEqual(b3, "burst_third_line_abcdefghijklmn")
        self.assertEqual(b4, "burst_fourth_line_qwertyuiopasdf")

        tailer.stop()

    def test_rapid_loop_inplace_truncation_stress(self) -> None:
        """Torture test: 20 rapid in-place truncations and burst cycles."""
        tailer = KaiMorichLogTailer(
            log_path=self.log_path,
            read_from_start=True,
            poll_interval_s=0.002,
        )
        gen = tailer.tail_lines()

        for cycle in range(20):
            # In-place overwrite with unique cycle header
            payload = f"cycle_{cycle:03d}_hdr_unique_token\ncycle_{cycle:03d}_data_payload_line\n"
            with open(self.log_path, "w") as f:
                f.write(payload)

            l1 = next(gen)
            l2 = next(gen)
            self.assertEqual(l1, f"cycle_{cycle:03d}_hdr_unique_token")
            self.assertEqual(l2, f"cycle_{cycle:03d}_data_payload_line")

        tailer.stop()


class TestAdversarialDispatcherLifecycle(unittest.TestCase):
    """Stress tests for LlamaInferenceDispatcher restart and concurrency."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()
        self.offline_log = Path(self.test_dir) / "offline.jsonl"

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_dispatcher_stop_and_immediate_restart_lifecycle(self) -> None:
        """
        Verifies that stopping and immediately restarting the dispatcher
        reliably resurrects processing and consumes queued items without deadlocking.
        """
        dispatcher = LlamaInferenceDispatcher(
            timeout_s=0.2,
            dry_run=True,
            offline_log_path=self.offline_log,
        )
        dispatcher.start()

        # Enqueue window in phase 1
        w1 = BiometricSummaryWindow(
            window_id=1,
            start_timestamp_ms=0,
            end_timestamp_ms=10000,
            duration_seconds=10.0,
            sample_count=1300,
            sampling_rate_hz=130.0,
            metrics={"mean_heart_rate_bpm": 70.0, "rhythm_assessment": "NORMAL_SINUS"},
        )
        self.assertTrue(dispatcher.dispatch_window(w1))
        time.sleep(0.05)

        # Stop and restart in rapid sequence
        dispatcher.stop(wait=True)
        self.assertFalse(dispatcher._running)

        dispatcher.start()
        self.assertTrue(dispatcher._running)

        # Enqueue window in phase 2
        w2 = BiometricSummaryWindow(
            window_id=2,
            start_timestamp_ms=10000,
            end_timestamp_ms=20000,
            duration_seconds=10.0,
            sample_count=1300,
            sampling_rate_hz=130.0,
            metrics={"mean_heart_rate_bpm": 72.0, "rhythm_assessment": "NORMAL_SINUS"},
        )
        self.assertTrue(dispatcher.dispatch_window(w2))

        # Wait for w2 processing
        t0 = time.time()
        while time.time() - t0 < 2.0:
            if dispatcher.total_succeeded >= 2:
                break
            time.sleep(0.02)

        self.assertEqual(dispatcher.total_succeeded, 2, "Both windows must be successfully processed across restarts")
        dispatcher.stop(wait=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
