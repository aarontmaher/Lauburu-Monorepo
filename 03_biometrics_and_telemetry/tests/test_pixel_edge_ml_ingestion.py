#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Unit & Integration Test Suite for Pixel Edge ML Ingestion
Requirement R3: Testing KaiMorichLogTailer, KaiMorichPacketParser,
EdgeBiometricsEngine (130 Hz Pan-Tompkins QRS, Kamath 20% filter, HRV),
and LlamaInferenceDispatcher.

Subsystem: 03_biometrics_and_telemetry/tests/test_pixel_edge_ml_ingestion.py
"""

from __future__ import annotations

import http.server
import json
import math
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List

# Add parent directory to sys.path so we can import pixel_edge_ml_ingestion
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


class TestKaiMorichPacketParser(unittest.TestCase):
    """Test suite for KaiMorichPacketParser multi-format parsing grammar."""

    def setUp(self) -> None:
        self.parser = KaiMorichPacketParser()

    def test_raw_csv_parsing(self) -> None:
        """Verifies parsing of standard raw CSV lines."""
        # CRLF
        res1 = self.parser.parse_line("172800000,342.0\r\n")
        self.assertIsNotNone(res1)
        self.assertEqual(res1, (172800000, 342.0))

        # LF
        res2 = self.parser.parse_line("172800007,-150.5\n")
        self.assertIsNotNone(res2)
        self.assertEqual(res2, (172800007, -150.5))

        # Integer ECG
        res3 = self.parser.parse_line("172800014,200\n")
        self.assertIsNotNone(res3)
        self.assertEqual(res3, (172800014, 200.0))

    def test_datetime_prefix_parsing(self) -> None:
        """Verifies stripping of Date+Time prefixes with and without RX markers."""
        # Date+Time with '<' marker
        res1 = self.parser.parse_line("2026-10-04 07:15:23.123 < 172800000,342.0\r\n")
        self.assertIsNotNone(res1)
        self.assertEqual(res1, (172800000, 342.0))

        # Date+Time without RX marker
        res2 = self.parser.parse_line("2026-10-04 07:15:23.123 172800000,-45.2\n")
        self.assertIsNotNone(res2)
        self.assertEqual(res2, (172800000, -45.2))

        # Date+Time without fractional seconds
        res3 = self.parser.parse_line("2026-10-04 07:15:23 > 172800000,512.0\n")
        self.assertIsNotNone(res3)
        self.assertEqual(res3, (172800000, 512.0))

    def test_time_only_prefix_parsing(self) -> None:
        """Verifies stripping of Time-only prefixes."""
        # Time-only with '<' marker
        res1 = self.parser.parse_line("07:15:23.123 < 172800000,342.0\r\n")
        self.assertIsNotNone(res1)
        self.assertEqual(res1, (172800000, 342.0))

        # Time-only without RX marker
        res2 = self.parser.parse_line("07:15:23.123 172800000,-88.4\n")
        self.assertIsNotNone(res2)
        self.assertEqual(res2, (172800000, -88.4))

        # Time-only without milliseconds
        res3 = self.parser.parse_line("07:15:23 172800000,120.0\n")
        self.assertIsNotNone(res3)
        self.assertEqual(res3, (172800000, 120.0))

    def test_rx_marker_stripping(self) -> None:
        """Verifies stripping of leading RX/TX markers (< or >)."""
        res1 = self.parser.parse_line("< 172800000,342.0\n")
        self.assertIsNotNone(res1)
        self.assertEqual(res1, (172800000, 342.0))

        res2 = self.parser.parse_line("> 172800000,-120.0\n")
        self.assertIsNotNone(res2)
        self.assertEqual(res2, (172800000, -120.0))

    def test_connection_status_and_comment_lines_ignored(self) -> None:
        """Verifies that decorative connection, comment, header, and blank lines return None."""
        ignored_lines = [
            "--- Connected to Movesense 12345678 ---",
            "--- Connected ---",
            "--- Disconnected ---",
            "// Logging started: 2026-10-04",
            "# Bluetooth Terminal log",
            "/* Block comment */",
            "Timestamp,ECG_uV\r\n",
            "timestamp,ecg\n",
            "",
            "   \r\n",
            "Random non-numeric garbage line",
        ]
        for line in ignored_lines:
            self.assertIsNone(self.parser.parse_line(line), f"Expected None for line: {line!r}")

    def test_line_fragment_reassembly(self) -> None:
        """Verifies chunk-level buffering and reassembly of partial BLE lines."""
        # Chunk 1: Incomplete line
        s1 = self.parser.feed("172800000,")
        self.assertEqual(s1, [])

        # Chunk 2: Completes line 1 and includes line 2
        s2 = self.parser.feed("342.0\r\n172800007,-150.0\n")
        self.assertEqual(s2, [(172800000, 342.0), (172800007, -150.0)])

        # Chunk 3: Prefix fragment
        s3 = self.parser.feed("2026-10-04 07:15:23.123 < ")
        self.assertEqual(s3, [])

        # Chunk 4: Completes line 3
        s4 = self.parser.feed("172800014,210.5\n")
        self.assertEqual(s4, [(172800014, 210.5)])

        # Chunk 5: Final fragment flushed
        self.parser.feed("172800021,99.0")
        flushed = self.parser.flush()
        self.assertEqual(flushed, [(172800021, 99.0)])

    def test_nan_and_inf_microvolts_rejected(self) -> None:
        """Verifies that NaN and Inf microvolts are safely rejected and return None."""
        invalid_ecg_lines = [
            "172800000,nan\n",
            "172800000,-nan\n",
            "172800000,NaN\n",
            "172800000,inf\n",
            "172800000,-inf\n",
            "172800000,INF\n",
            "2026-10-04 07:15:23.123 < 172800000,nan\n",
            "07:15:23.123 < 172800000,inf\n",
        ]
        for line in invalid_ecg_lines:
            res = self.parser.parse_line(line)
            self.assertIsNone(res, f"Expected None for non-finite microvolts in: {line!r}")

    def test_extreme_overflow_timestamps_do_not_crash(self) -> None:
        """Verifies extreme or overflow timestamps do not crash the parser."""
        extreme_lines = [
            "inf,100.0\n",
            "-inf,100.0\n",
            "1e309,100.0\n",
            "-1e309,100.0\n",
            "1" * 350 + ",100.0\n",
            "nan,100.0\n",
            "-nan,100.0\n",
        ]
        for line in extreme_lines:
            res = self.parser.parse_line(line)
            self.assertIsNone(res, f"Expected None for extreme timestamp in: {line!r}")

    def test_64bit_timestamps_preserve_exact_integer_values(self) -> None:
        """Verifies 64-bit integer timestamps > 2^53 preserve exact values without float precision loss."""
        # 2^63 - 1 (INT64_MAX)
        res1 = self.parser.parse_line("9223372036854775807,150.0\n")
        self.assertIsNotNone(res1)
        self.assertEqual(res1, (9223372036854775807, 150.0))

        # 2^53 + 1 (9007199254740993) - classic IEEE 754 float precision loss boundary
        res2 = self.parser.parse_line("9007199254740993,250.0\n")
        self.assertIsNotNone(res2)
        self.assertEqual(res2, (9007199254740993, 250.0))

        # Microsecond timestamp (16 digits)
        res3 = self.parser.parse_line("1728000000000000,-50.0\n")
        self.assertIsNotNone(res3)
        self.assertEqual(res3, (1728000000000000, -50.0))

        # Negative 64-bit timestamp
        res4 = self.parser.parse_line("-9007199254740993,10.0\n")
        self.assertIsNotNone(res4)
        self.assertEqual(res4, (-9007199254740993, 10.0))

    def test_parser_buffer_bounded_on_unbroken_lines(self) -> None:
        """Verifies feed buffer does not grow unbounded when receiving chunks without newlines."""
        huge_chunk = "X" * 100000
        samples = self.parser.feed(huge_chunk)
        self.assertEqual(samples, [])
        self.assertLessEqual(len(self.parser._buffer), self.parser.max_buffer_size)


class TestKaiMorichLogTailer(unittest.TestCase):
    """Test suite for KaiMorichLogTailer file tailing, truncation, and rotation."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_tailer_reads_from_beginning(self) -> None:
        """Verifies that tailer with read_from_start=True reads existing file contents."""
        log_file = Path(self.test_dir) / "test.log"
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("172800000,100\n")
            f.write("172800007,150\n")
            f.write("172800014,200\n")

        tailer = KaiMorichLogTailer(
            log_path=log_file,
            read_from_start=True,
            poll_interval_s=0.01,
        )

        lines: List[str] = []
        gen = tailer.tail_lines()
        for _ in range(3):
            lines.append(next(gen))
        tailer.stop()

        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], "172800000,100")
        self.assertEqual(lines[1], "172800007,150")
        self.assertEqual(lines[2], "172800014,200")

    def test_tailer_truncation_recovery(self) -> None:
        """Verifies tailer recovers when file is truncated (size < offset)."""
        log_file = Path(self.test_dir) / "trunc_test.log"
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("long_initial_line_1\nlong_initial_line_2\nlong_initial_line_3\n")

        tailer = KaiMorichLogTailer(
            log_path=log_file,
            read_from_start=True,
            poll_interval_s=0.01,
        )

        gen = tailer.tail_lines()
        self.assertEqual(next(gen), "long_initial_line_1")
        self.assertEqual(next(gen), "long_initial_line_2")
        self.assertEqual(next(gen), "long_initial_line_3")

        # Truncate file and write new shorter content (st_size < current_offset)
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("new_1\nnew_2\n")

        # Tailer should detect truncation and read the new lines from byte 0
        self.assertEqual(next(gen), "new_1")
        self.assertEqual(next(gen), "new_2")
        tailer.stop()

    def test_tailer_rotation_recovery(self) -> None:
        """Verifies tailer recovers when file is rotated (inode changed)."""
        log_file = Path(self.test_dir) / "rotate_test.log"
        old_file = Path(self.test_dir) / "rotate_test.log.1"

        with open(log_file, "w", encoding="utf-8") as f:
            f.write("first_file_line\n")

        tailer = KaiMorichLogTailer(
            log_path=log_file,
            read_from_start=True,
            poll_interval_s=0.01,
        )

        gen = tailer.tail_lines()
        self.assertEqual(next(gen), "first_file_line")

        # Simulate log rotation: rename and create new file with new inode
        os.rename(log_file, old_file)
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("second_file_line\n")

        self.assertEqual(next(gen), "second_file_line")
        tailer.stop()

    def test_auto_discovery(self) -> None:
        """Verifies auto-discovery picks the most recently modified log file."""
        sub_dir = Path(self.test_dir) / "Download"
        sub_dir.mkdir(parents=True)

        f1 = sub_dir / "older.log"
        f2 = sub_dir / "newer.log"

        f1.write_text("old", encoding="utf-8")
        time.sleep(0.05)
        f2.write_text("new", encoding="utf-8")

        tailer = KaiMorichLogTailer(search_dirs=[sub_dir])
        discovered = tailer.auto_discover()
        self.assertIsNotNone(discovered)
        self.assertEqual(discovered.name, "newer.log")

    def test_inplace_truncation_followed_by_write_burst(self) -> None:
        """Verifies tailer recovers when file is truncated in-place and written with burst > old offset."""
        log_file = Path(self.test_dir) / "burst_trunc.log"
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("short_1\nshort_2\n")

        tailer = KaiMorichLogTailer(
            log_path=log_file,
            read_from_start=True,
            poll_interval_s=0.01,
        )
        gen = tailer.tail_lines()
        self.assertEqual(next(gen), "short_1")
        self.assertEqual(next(gen), "short_2")
        old_offset = tailer._current_offset

        # In-place truncate and immediately write 80+ bytes (exceeding old offset 16 bytes)
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("brand_new_long_line_number_one_12345\nbrand_new_long_line_number_two_12345\n")

        self.assertGreater(log_file.stat().st_size, old_offset)

        # Tailer must detect the in-place overwrite and yield line 1 completely
        l3 = next(gen)
        l4 = next(gen)
        tailer.stop()

        self.assertEqual(l3, "brand_new_long_line_number_one_12345")
        self.assertEqual(l4, "brand_new_long_line_number_two_12345")

    def test_long_line_without_newline_bounded_buffer(self) -> None:
        """Verifies tailer caps line buffer and does not explode memory on unbroken long lines."""
        log_file = Path(self.test_dir) / "long_unbroken.log"
        with open(log_file, "w", encoding="utf-8") as f:
            # 20,000 characters with no newline
            f.write("A" * 20000)

        tailer = KaiMorichLogTailer(
            log_path=log_file,
            read_from_start=True,
            poll_interval_s=0.01,
            max_line_buffer_bytes=1024,
        )

        gen = tailer.tail_lines()

        # Append a newline and a valid line
        with open(log_file, "a", encoding="utf-8") as f:
            f.write("\n172800000,342.0\n")

        # Tailer should discard the overgrown buffer and cleanly yield the valid line
        line = next(gen)
        tailer.stop()

        self.assertEqual(line, "172800000,342.0")
        self.assertLessEqual(len(tailer._line_buffer), 1024)


class TestEdgeBiometricsEngine(unittest.TestCase):
    """Test suite for 130 Hz Pan-Tompkins QRS, Kamath filter, and HRV metrics."""

    def setUp(self) -> None:
        self.fs = 130.0
        self.engine = EdgeBiometricsEngine(sample_rate_hz=self.fs, window_seconds=10.0)

    def _generate_synthetic_ecg(self, duration_sec: float = 10.0, bpm: float = 60.0) -> List[float]:
        """Generates synthetic 130 Hz ECG with realistic QRS complexes at given BPM."""
        n_samples = int(duration_sec * self.fs)
        signal = [0.0] * n_samples
        interval_samples = (60.0 / bpm) * self.fs

        beat_idx = 1
        while True:
            center = int(round(beat_idx * interval_samples))
            if center + 4 >= n_samples:
                break
            # QRS waveform morphology
            signal[center - 2] = 50.0    # Q wave dip/rise
            signal[center - 1] = 250.0   # Steep R upstroke
            signal[center] = 500.0       # R-peak apex
            signal[center + 1] = -150.0  # S wave downstroke
            signal[center + 2] = -50.0   # S recovery
            beat_idx += 1

        return signal

    def test_synthetic_qrs_detection_60bpm(self) -> None:
        """Verifies accurate detection of 60 BPM signal (~1000ms RR intervals)."""
        ecg = self._generate_synthetic_ecg(duration_sec=10.0, bpm=60.0)
        peaks, rrs = self.engine.detect_qrs_peaks(ecg)

        self.assertGreaterEqual(len(peaks), 8)
        self.assertGreaterEqual(len(rrs), 7)

        for rr in rrs:
            self.assertAlmostEqual(rr, 1000.0, delta=25.0)

        cleaned, artifacts = self.engine.apply_kamath_artifact_filter(rrs)
        self.assertEqual(artifacts, 0)

        hrv = self.engine.calculate_hrv_metrics(cleaned)
        self.assertAlmostEqual(hrv["mean_heart_rate_bpm"], 60.0, delta=2.0)
        self.assertLess(hrv["rmssd_ms"], 15.0)

    def test_synthetic_qrs_detection_72bpm(self) -> None:
        """Verifies accurate detection of 72 BPM signal (~833ms RR intervals)."""
        ecg = self._generate_synthetic_ecg(duration_sec=10.0, bpm=72.0)
        peaks, rrs = self.engine.detect_qrs_peaks(ecg)

        self.assertGreaterEqual(len(peaks), 10)
        self.assertGreaterEqual(len(rrs), 9)

        for rr in rrs:
            self.assertAlmostEqual(rr, 833.3, delta=25.0)

        hrv = self.engine.calculate_hrv_metrics(rrs)
        self.assertAlmostEqual(hrv["mean_heart_rate_bpm"], 72.0, delta=2.0)

    def test_kamath_artifact_rejection(self) -> None:
        """Verifies Kamath 20% filter flags and interpolates ectopic outliers."""
        # Regular 1000ms beats with a 450ms premature ventricular contraction (PVC)
        raw_rrs = [1000.0, 1000.0, 450.0, 1000.0, 1000.0]
        cleaned, artifact_count = self.engine.apply_kamath_artifact_filter(raw_rrs, threshold_pct=20.0)

        self.assertEqual(artifact_count, 1)
        self.assertEqual(len(cleaned), len(raw_rrs))
        # The 450ms beat was corrected to physiological interpolation
        self.assertGreater(cleaned[2], 700.0)

    def test_hrv_metrics_calculation(self) -> None:
        """Verifies mathematical correctness of RMSSD, SDNN, and pNN50."""
        rrs = [800.0, 820.0, 810.0, 830.0, 800.0]
        hrv = self.engine.calculate_hrv_metrics(rrs)

        self.assertAlmostEqual(hrv["mean_heart_rate_bpm"], 60000.0 / 812.0, delta=0.5)
        self.assertGreater(hrv["rmssd_ms"], 0.0)
        self.assertGreater(hrv["sdnn_ms"], 0.0)
        self.assertEqual(hrv["pnn50_pct"], 0.0)

    def test_sliding_window_emission_and_memory_bounds(self) -> None:
        """Verifies that windows are emitted every 1,300 samples and buffers stay bounded."""
        emitted_windows: List[BiometricSummaryWindow] = []
        base_ts = 172800000

        # Feed 2,600 samples (2 full 10s windows)
        for i in range(2600):
            ts = base_ts + int(i * (1000.0 / self.fs))
            val = 500.0 if (i % 130 == 0) else 0.0
            win = self.engine.add_sample(ts, val)
            if win is not None:
                emitted_windows.append(win)

        self.assertEqual(len(emitted_windows), 2)
        self.assertEqual(emitted_windows[0].window_id, 1)
        self.assertEqual(emitted_windows[1].window_id, 2)
        self.assertEqual(emitted_windows[0].sample_count, 1300)

        # Verify bounded circular buffers (Rule 9 AVF memory governance)
        self.assertEqual(len(self.engine._raw_samples), 1300)
        self.assertEqual(len(self.engine._raw_timestamps), 1300)
        self.assertLessEqual(len(self.engine._rr_intervals), 100)
        self.assertLess(self.engine.get_memory_usage_mb(), 50.0)

    def test_nan_and_inf_samples_rejected_without_filter_poisoning(self) -> None:
        """Verifies non-finite samples are rejected by add_sample and do not poison future windows."""
        # Attempt to inject NaN and Inf samples
        self.assertIsNone(self.engine.add_sample(172800000, float("nan")))
        self.assertIsNone(self.engine.add_sample(172800007, float("inf")))
        self.assertIsNone(self.engine.add_sample(172800014, float("-inf")))
        self.assertEqual(len(self.engine._raw_samples), 0)

        # Now feed 1,300 clean samples (10s @ 60 BPM)
        ecg = self._generate_synthetic_ecg(duration_sec=10.0, bpm=60.0)
        window = None
        base_ts = 172800000
        for i, val in enumerate(ecg):
            w = self.engine.add_sample(base_ts + i * 7, val)
            if w is not None:
                window = w

        self.assertIsNotNone(window)
        self.assertEqual(window.sample_count, 1300)
        hr = window.metrics.get("mean_heart_rate_bpm", 0.0)
        self.assertAlmostEqual(hr, 60.0, delta=2.0)
        self.assertEqual(window.metrics.get("rhythm_assessment"), "NORMAL_SINUS")
        self.assertGreaterEqual(window.metrics.get("qrs_peak_count", 0), 8)


class MockLlamaHandler(http.server.BaseHTTPRequestHandler):
    """Mock HTTP handler simulating OpenAI /v1/chat/completions."""

    requests_received: List[Dict[str, Any]] = []
    delay_s: float = 0.0

    def do_POST(self) -> None:
        if MockLlamaHandler.delay_s > 0:
            time.sleep(MockLlamaHandler.delay_s)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        parsed_body = json.loads(body) if body else {}

        MockLlamaHandler.requests_received.append({
            "path": self.path,
            "headers": dict(self.headers),
            "body": parsed_body,
        })

        if self.path == "/v1/chat/completions" or self.path == "/chat/completions":
            response = {
                "id": "chatcmpl-mock-123",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "llama-3-8b",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "Rhythm is normal sinus with stable 72 BPM. Autonomic recovery is optimal.",
                        },
                        "finish_reason": "stop",
                    }
                ],
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))
        elif self.path == "/completion":
            response = {
                "content": "Rhythm is normal sinus via completion endpoint.",
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        pass  # Silence HTTP server logs during tests


class TestLlamaInferenceDispatcher(unittest.TestCase):
    """Test suite for LlamaInferenceDispatcher HTTP client, retry, and offline fallback."""

    @classmethod
    def setUpClass(cls) -> None:
        MockLlamaHandler.requests_received = []
        cls.server = http.server.HTTPServer(("127.0.0.1", 0), MockLlamaHandler)
        cls.server_port = cls.server.server_address[1]
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self) -> None:
        MockLlamaHandler.requests_received.clear()
        self.test_dir = tempfile.mkdtemp()
        self.offline_log = Path(self.test_dir) / "offline.jsonl"

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_mock_window(self) -> BiometricSummaryWindow:
        metrics = {
            "mean_heart_rate_bpm": 72.4,
            "min_heart_rate_bpm": 68.0,
            "max_heart_rate_bpm": 76.5,
            "rr_intervals_ms": [820.0, 835.0, 815.0, 840.0, 825.0],
            "rmssd_ms": 18.2,
            "sdnn_ms": 24.1,
            "pnn50_pct": 0.0,
            "kamath_artifacts_rejected": 0,
            "artifact_rate_pct": 0.0,
            "signal_quality_sqi_pct": 100.0,
            "rhythm_assessment": "NORMAL_SINUS",
            "training_zone": "Zone 1 (Recovery / Aerobic Base)",
        }
        return BiometricSummaryWindow(
            window_id=1,
            start_timestamp_ms=172800000,
            end_timestamp_ms=172810000,
            duration_seconds=10.0,
            sample_count=1300,
            sampling_rate_hz=130.0,
            metrics=metrics,
        )

    def test_mock_http_llama_dispatch(self) -> None:
        """Verifies asynchronous HTTP dispatch with OpenAI payload schema verification."""
        mock_url = f"http://127.0.0.1:{self.server_port}/v1"
        dispatcher = LlamaInferenceDispatcher(
            primary_url=mock_url,
            fallback_url=mock_url,
            timeout_s=2.0,
            offline_log_path=self.offline_log,
        )
        dispatcher.start()

        window = self._create_mock_window()
        self.assertTrue(dispatcher.dispatch_window(window))

        # Wait for background worker to complete dispatch
        timeout = time.time() + 3.0
        while time.time() < timeout:
            if MockLlamaHandler.requests_received:
                break
            time.sleep(0.05)

        dispatcher.stop(wait=True)

        self.assertGreaterEqual(len(MockLlamaHandler.requests_received), 1)
        req = MockLlamaHandler.requests_received[0]
        self.assertEqual(req["path"], "/v1/chat/completions")
        self.assertEqual(req["body"]["model"], "llama-3-8b")
        self.assertIn("NORMAL_SINUS", req["body"]["messages"][1]["content"])

        assessment = dispatcher.get_latest_assessment()
        self.assertIsNotNone(assessment)
        self.assertIn("Rhythm is normal sinus", assessment)
        self.assertEqual(dispatcher.total_succeeded, 1)

    def test_offline_fallback_when_unreachable(self) -> None:
        """Verifies graceful offline fallback when inference endpoints are offline."""
        unreachable_url = "http://127.0.0.1:59998/v1"
        dispatcher = LlamaInferenceDispatcher(
            primary_url=unreachable_url,
            fallback_url=unreachable_url,
            timeout_s=0.5,
            offline_log_path=self.offline_log,
        )
        dispatcher.start()

        window = self._create_mock_window()
        dispatcher.dispatch_window(window)

        # Wait for dispatch to timeout and fall back
        timeout = time.time() + 3.0
        while time.time() < timeout:
            if dispatcher.total_dispatched > 0 and dispatcher.total_offline_fallbacks > 0:
                break
            time.sleep(0.05)

        dispatcher.stop(wait=True)

        self.assertEqual(dispatcher.total_offline_fallbacks, 1)
        self.assertTrue(self.offline_log.exists())

        # Verify offline summary entry
        with open(self.offline_log, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)
        data = json.loads(lines[0])
        self.assertIn("OFFLINE_FALLBACK", data["assessment"])
        self.assertEqual(data["window"]["metrics"]["rhythm_assessment"], "NORMAL_SINUS")

    def test_dispatcher_restart_lifecycle_robust_under_inflight_timeout(self) -> None:
        """
        Verifies that LlamaInferenceDispatcher handles stop() during an in-flight request
        and subsequent start() reliably revives the worker without entering a dead state.
        """
        MockLlamaHandler.delay_s = 1.0  # Server delays response by 1.0s
        mock_url = f"http://127.0.0.1:{self.server_port}/v1"
        dispatcher = LlamaInferenceDispatcher(
            primary_url=mock_url,
            fallback_url=mock_url,
            timeout_s=1.0,
            offline_log_path=self.offline_log,
        )
        dispatcher.start()

        # Enqueue window 1 which enters the 1.0s in-flight delay
        w1 = self._create_mock_window()
        self.assertTrue(dispatcher.dispatch_window(w1))
        time.sleep(0.05)  # Ensure worker picks up w1

        # Stop with short join timeout (0.1s), leaving request in-flight
        dispatcher.stop(wait=True, timeout=0.1)

        # Revive dispatcher with start()
        dispatcher.start()
        self.assertTrue(dispatcher._running, "Dispatcher _running must be True after start()")

        # Reset server delay and enqueue window 2 in dry-run mode
        MockLlamaHandler.delay_s = 0.0
        w2 = self._create_mock_window()
        w2.window_id = 2
        dispatcher.dry_run = True
        self.assertTrue(dispatcher.dispatch_window(w2))

        # Wait for dispatch of window 2 to complete
        timeout = time.time() + 3.0
        while time.time() < timeout:
            if dispatcher.total_dispatched >= 2:
                break
            time.sleep(0.05)

        dispatcher.stop(wait=True)
        self.assertGreaterEqual(
            dispatcher.total_dispatched, 2,
            "Worker must process window 2 successfully after restart during in-flight timeout"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
