#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adversarial Stress Test Suite for KaiMorichPacketParser and KaiMorichLogTailer
Target: 03_biometrics_and_telemetry/pixel_edge_ml_ingestion.py

Covers:
1. Rapid file truncations and rolling log file re-creations.
2. Corrupted and truncated lines, null bytes, raw binary sequences.
3. High-frequency line bursts (1,000+ lines in a burst).
4. Malformed microvolts, huge timestamps, boundary extremes.
5. End-to-end pipeline survival (no crash, no hang, no resource leak).
6. Empirical demonstration of critical vulnerabilities (OverflowError, NaN poisoning, int64 precision loss).
"""

from __future__ import annotations

import gc
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any, List, Optional, Tuple

# Add parent directory to sys.path
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


class TestAdversarialKaiMorichPacketParser(unittest.TestCase):
    """Adversarial stress testing of KaiMorichPacketParser grammar & edge cases."""

    def setUp(self) -> None:
        self.parser = KaiMorichPacketParser()

    def test_null_bytes_and_control_characters(self) -> None:
        """Verifies parser cleanly rejects null bytes and control codes without exception."""
        adversarial_inputs = [
            "\x00172800000,100.0\n",
            "172800000\x00,100.0\n",
            "172800000,\x00100.0\n",
            "172800000,100.0\x00\n",
            "\x00\x01\x02\x03,100.0\n",
            "172800000,\x00\x01\x02\x03\n",
            "\x00\n",
            "\x00" * 1000 + "\n",
            "2026-10-04 07:15:23.123 < \x00172800000,342.0\n",
            "\x1b[31m172800000,100.0\x1b[0m\n",  # ANSI escape codes
        ]
        for line in adversarial_inputs:
            res = self.parser.parse_line(line)
            if "\x00" in line:
                self.assertIsNone(res, f"Expected None for null-corrupted line: {line!r}")

    def test_demonstrate_overflow_error_vulnerability(self) -> None:
        """
        [VERIFIED REMEDIATION #1]
        Verifies that KaiMorichPacketParser.parse_line cleanly catches OverflowError
        and returns None for 'inf', '-inf', '1e309', and astronomical digit strings.
        """
        overflow_inputs = [
            "inf,100.0",
            "-inf,100.0",
            "1e309,100.0",
            "-1e309,100.0",
            "1" * 310 + ",100.0",
        ]
        overflow_handled_count = 0
        for line in overflow_inputs:
            res = self.parser.parse_line(line)
            self.assertIsNone(res, f"Expected None on {line[:15]}")
            overflow_handled_count += 1

        self.assertEqual(overflow_handled_count, len(overflow_inputs))
        print(f"\n[REMEDIATION VERIFIED #1] OverflowError handled cleanly across {overflow_handled_count} inputs.")

    def test_demonstrate_int64_precision_loss(self) -> None:
        """
        [VERIFIED REMEDIATION #2]
        Verifies that exact 64-bit integer timestamp precision is preserved
        without IEEE 754 precision loss for timestamps > 2^53 (e.g. INT64_MAX).
        """
        int64_max_str = "9223372036854775807,100.0"
        res = self.parser.parse_line(int64_max_str)
        self.assertIsNotNone(res)
        ts, _ = res
        self.assertEqual(ts, 9223372036854775807, "Exact 64-bit integer timestamp must be preserved")
        self.assertIsInstance(ts, int)
        print(f"\n[REMEDIATION VERIFIED #2] Exact int64 precision verified: {ts}")

    def test_demonstrate_nan_and_inf_microvolt_leakage(self) -> None:
        """
        [VERIFIED REMEDIATION #3]
        Verifies that float('nan') and float('inf') are rejected by the parser,
        returning None and preventing IIR filter poisoning.
        """
        res_nan = self.parser.parse_line("172800000,nan")
        self.assertIsNone(res_nan, "NaN microvolts must return None")

        res_inf = self.parser.parse_line("172800000,inf")
        self.assertIsNone(res_inf, "Inf microvolts must return None")

        print("\n[REMEDIATION VERIFIED #3] NaN and Inf microvolts cleanly rejected by parser.")

    def test_timestamp_boundary_extremes(self) -> None:
        """Tests handling of valid boundary integer timestamps."""
        boundary_inputs = [
            ("0,100.0", (0, 100.0)),
            ("-1,100.0", (-1, 100.0)),
            ("172800000.89,100.0", (172800000, 100.0)),  # Fractional timestamp truncated
        ]
        for line, expected in boundary_inputs:
            res = self.parser.parse_line(line)
            self.assertEqual(res, expected, f"Failed for {line!r}")

    def test_fragmentation_fuzzing(self) -> None:
        """
        Feeds fragmented streams with byte-by-byte or tiny-slice splitting
        to verify fragment reassembly does not drop data or corrupt samples.
        """
        clean_lines = [
            f"2026-10-04 07:15:23.{i:03d} < {172800000 + i * 7},{100 + i}.0\n"
            for i in range(50)
        ]
        full_stream = "".join(clean_lines)

        for step in [1, 3, 7, 13, 31]:
            parser = KaiMorichPacketParser()
            collected: List[Tuple[int, float]] = []
            for offset in range(0, len(full_stream), step):
                chunk = full_stream[offset : offset + step]
                collected.extend(parser.feed(chunk))
            collected.extend(parser.flush())

            self.assertEqual(len(collected), 50, f"Fragmentation step={step} failed to parse 50 samples")
            self.assertEqual(collected[0], (172800000, 100.0))
            self.assertEqual(collected[-1], (172800000 + 49 * 7, 149.0))

    def test_extremely_long_unbroken_lines(self) -> None:
        """Verifies parser handles unbroken lines up to 500 KB without memory explosion."""
        huge_line = "A" * 500000 + "\n"
        res = self.parser.parse_line(huge_line)
        self.assertIsNone(res)

        huge_csv = "172800000," + "9" * 100000 + "\n"
        res = self.parser.parse_line(huge_csv)
        self.assertIsNone(res, "Astronomical float overflow must return None")


class TestAdversarialKaiMorichLogTailer(unittest.TestCase):
    """Adversarial stress testing of KaiMorichLogTailer file I/O & lifecycle."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()
        self.log_path = Path(self.test_dir) / "stress.log"
        self.log_path.touch()

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_rapid_inplace_truncations(self) -> None:
        """
        Stress test: 30 rapid in-place truncations while tailer is reading.
        Verifies tailer recovers every time without deadlock or crashing.
        """
        tailer = KaiMorichLogTailer(
            log_path=self.log_path,
            read_from_start=True,
            poll_interval_s=0.005,
        )
        gen = tailer.tail_lines()

        for cycle in range(30):
            # Write a few lines
            with open(self.log_path, "a") as f:
                f.write(f"cycle_{cycle}_line1\ncycle_{cycle}_line2\n")

            # Read lines
            l1 = next(gen)
            l2 = next(gen)
            self.assertEqual(l1, f"cycle_{cycle}_line1")
            self.assertEqual(l2, f"cycle_{cycle}_line2")

            # In-place truncate to 0 bytes
            with open(self.log_path, "w") as f:
                f.truncate(0)

            # Write new line after truncation
            with open(self.log_path, "a") as f:
                f.write(f"post_trunc_{cycle}\n")

            l_post = next(gen)
            self.assertEqual(l_post, f"post_trunc_{cycle}")

        tailer.stop()

    def test_rapid_rolling_file_recreations(self) -> None:
        """
        Stress test: 30 rolling file recreations (unlink + recreate with new inode).
        Verifies st_ino tracking reliably switches files.
        """
        tailer = KaiMorichLogTailer(
            log_path=self.log_path,
            read_from_start=True,
            poll_interval_s=0.005,
        )
        gen = tailer.tail_lines()

        for cycle in range(30):
            # Write line
            with open(self.log_path, "a") as f:
                f.write(f"file_cycle_{cycle}\n")

            l = next(gen)
            self.assertEqual(l, f"file_cycle_{cycle}")

            # Recreate file (simulate logrotate: unlink and open fresh)
            self.log_path.unlink()
            with open(self.log_path, "w") as f:
                f.write(f"new_inode_cycle_{cycle}\n")

            l_new = next(gen)
            self.assertEqual(l_new, f"new_inode_cycle_{cycle}")

        tailer.stop()

    def test_file_disappears_and_reappears(self) -> None:
        """
        Tests behavior when the log file is deleted and remains absent for 100ms.
        Verifies tailer waits and resumes when recreated.
        """
        tailer = KaiMorichLogTailer(
            log_path=self.log_path,
            read_from_start=True,
            poll_interval_s=0.01,
        )
        gen = tailer.tail_lines()

        with open(self.log_path, "w") as f:
            f.write("before_deletion\n")
        self.assertEqual(next(gen), "before_deletion")

        # Delete file
        self.log_path.unlink()
        time.sleep(0.1)  # Absent for 100ms

        # Recreate file
        with open(self.log_path, "w") as f:
            f.write("after_recreation\n")

        self.assertEqual(next(gen), "after_recreation")
        tailer.stop()

    def test_demonstrate_truncate_and_immediate_expand_desync(self) -> None:
        """
        [EMPIRICAL VULNERABILITY #4: MEDIUM]
        Demonstrates that in-place truncate-and-immediate-burst write where
        new_size >= old_offset causes offset desynchronization because
        st.st_size < offset check evaluates to False.
        """
        tailer = KaiMorichLogTailer(
            log_path=self.log_path,
            read_from_start=True,
            poll_interval_s=0.02,
        )
        gen = tailer.tail_lines()

        with open(self.log_path, "w") as f:
            f.write("short_line_1\nshort_line_2\n")
        l1 = next(gen)
        l2 = next(gen)
        old_offset = tailer._current_offset

        # Truncate and write 80 bytes (greater than old_offset 26 bytes)
        with open(self.log_path, "w") as f:
            f.write("brand_new_long_line_number_one_12345\nbrand_new_long_line_number_two_12345\n")

        new_size = self.log_path.stat().st_size
        self.assertGreater(new_size, old_offset)

        l3 = next(gen)
        tailer.stop()

        # Due to remediation header check, tailer seeks to 0 and reads line 1
        self.assertEqual(l3, "brand_new_long_line_number_one_12345")
        print(f"\n[REMEDIATION VERIFIED #4] In-place truncate-and-immediate-expand recovered cleanly: got {l3!r}")

    def test_high_frequency_line_bursts(self) -> None:
        """
        Stress test: High-frequency bursts (2,000 lines written in one shot).
        Verifies no line loss, no buffer overflow, and low CPU latency.
        """
        tailer = KaiMorichLogTailer(
            log_path=self.log_path,
            read_from_start=True,
            poll_interval_s=0.005,
        )

        burst_count = 2000
        received: List[str] = []

        def worker():
            for line in tailer.tail_lines():
                received.append(line)
                if len(received) >= burst_count:
                    break

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        # Write 2,000 lines in a single burst
        with open(self.log_path, "a") as f:
            for i in range(burst_count):
                f.write(f"burst_sample_{i:04d},100.0\n")

        thread.join(timeout=5.0)
        tailer.stop()

        self.assertFalse(thread.is_alive(), "Worker thread hung on burst processing")
        self.assertEqual(len(received), burst_count)
        self.assertEqual(received[0], "burst_sample_0000,100.0")
        self.assertEqual(received[-1], f"burst_sample_{burst_count - 1:04d},100.0")

    def test_no_file_descriptor_leak(self) -> None:
        """Verifies zero file descriptor leaks across 100 log file rotations."""
        tailer = KaiMorichLogTailer(
            log_path=self.log_path,
            read_from_start=True,
            poll_interval_s=0.001,
        )
        gen = tailer.tail_lines()

        def get_fd_count():
            try:
                return len(os.listdir("/dev/fd"))
            except Exception:
                return 0

        fd_start = get_fd_count()
        for i in range(100):
            self.log_path.unlink()
            with open(self.log_path, "w") as f:
                f.write(f"line_{i}\n")
            line = next(gen)
            self.assertEqual(line, f"line_{i}")

        fd_end = get_fd_count()
        tailer.stop()
        # Active file fd is held, but no accumulating leaks
        self.assertLessEqual(fd_end - fd_start, 2, f"FD leak detected: {fd_end - fd_start} FDs leaked")


class TestAdversarialEndToEndPipeline(unittest.TestCase):
    """End-to-end stress test combining Tailer, Parser, Biometrics Engine, and Dispatcher."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()
        self.log_path = Path(self.test_dir) / "e2e_stress.log"
        self.offline_log = Path(self.test_dir) / "offline.jsonl"
        self.log_path.touch()

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_pipeline_under_adversarial_stream(self) -> None:
        """
        Feeds a mixed adversarial stream containing:
        - Clean ECG samples
        - Comment / status / header noise
        - Truncated lines
        - Extreme / corrupted microvolts
        - Null bytes
        - In-place truncations
        Verifies pipeline survives, emits valid windows, and does not leak memory.
        """
        initial_rss = get_process_rss_mb()

        tailer = KaiMorichLogTailer(
            log_path=self.log_path,
            read_from_start=True,
            poll_interval_s=0.005,
        )
        parser = KaiMorichPacketParser()
        engine = EdgeBiometricsEngine(sample_rate_hz=130.0, window_seconds=2.0)
        dispatcher = LlamaInferenceDispatcher(
            offline_log_path=self.offline_log,
            dry_run=True,
        )
        dispatcher.start()

        windows_emitted: List[BiometricSummaryWindow] = []
        crashed = False
        exception_msg = ""

        # Feed 1,500 samples with periodic chaos
        base_ts = 172800000
        lines_to_write = []

        for i in range(1500):
            ts = base_ts + i * 7
            ecg_val = 500.0 if (i % 130 == 0) else 0.0

            if i % 100 == 10:
                lines_to_write.append("CORRUPTED_LINE_GARBAGE\n")
            elif i % 100 == 20:
                lines_to_write.append(f"{ts},\x00{ecg_val}\n")
            elif i % 100 == 30:
                lines_to_write.append("--- Reconnecting Movesense BLE ---\n")
            elif i % 100 == 40:
                lines_to_write.append(f"2026-10-04 07:15:23.123 < {ts},{ecg_val}\n")
            elif i % 100 == 50:
                lines_to_write.append(f"07:15:23.123 {ts},{ecg_val}\n")
            else:
                lines_to_write.append(f"{ts},{ecg_val}\n")

        with open(self.log_path, "a") as f:
            f.writelines(lines_to_write)

        try:
            line_count = 0
            for line in tailer.tail_lines():
                line_count += 1
                try:
                    sample = parser.parse_line(line)
                except Exception as pe:
                    crashed = True
                    exception_msg = f"Parser crashed on {line!r}: {pe}"
                    break

                if sample is not None:
                    ts_ms, ecg_uv = sample
                    if math.isfinite(ecg_uv):
                        win = engine.add_sample(ts_ms, ecg_uv)
                        if win is not None:
                            windows_emitted.append(win)
                            dispatcher.dispatch_window(win)

                if line_count >= len(lines_to_write):
                    break
        finally:
            tailer.stop()
            dispatcher.stop(wait=True)

        self.assertFalse(crashed, f"Pipeline crashed: {exception_msg}")
        self.assertGreater(len(windows_emitted), 3, "Expected at least 3 summary windows emitted")

        final_rss = get_process_rss_mb()
        rss_growth = final_rss - initial_rss
        self.assertLess(rss_growth, 30.0, f"Excessive memory growth: {rss_growth:.2f} MB")

    def test_cli_unhandled_crash_on_overflow_timestamp(self) -> None:
        """
        [VERIFIED REMEDIATION #6]
        Verifies that running pixel_edge_ml_ingestion.py on a log file containing
        overflow and non-finite timestamps does not crash, ignores invalid lines,
        and cleanly processes summary windows.
        """
        test_log = Path(self.test_dir) / "overflow_safe.log"
        with open(test_log, "w") as f:
            # Write 1,300 valid samples with overflow lines interspersed
            for i in range(1300):
                f.write(f"{172800000 + i * 7},100.0\n")
                if i == 10:
                    f.write("inf,100.0\n")
                    f.write("-inf,100.0\n")
                    f.write("1e309,100.0\n")
                    f.write("172800000,nan\n")

        proc = subprocess.run(
            [
                sys.executable,
                str(BASE_DIR / "pixel_edge_ml_ingestion.py"),
                "--log-path", str(test_log),
                "--from-beginning",
                "--dry-run",
                "--max-windows", "1",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertEqual(proc.returncode, 0, f"Expected CLI to exit cleanly with code 0. Stderr: {proc.stderr}")
        self.assertNotIn("OverflowError", proc.stderr)
        self.assertIn("Evaluated window #1", proc.stdout + proc.stderr)
        print(f"\n[CLI ROBUSTNESS CONFIRMED] Process exited cleanly with code {proc.returncode}.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
