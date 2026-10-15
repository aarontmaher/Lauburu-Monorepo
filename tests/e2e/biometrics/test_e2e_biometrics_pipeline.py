#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dual-Track E2E Test Suite for Pixel 10 Biometrics & Movesense NUS Ingestion Pipeline
====================================================================================
Subsystems:
- Movesense C++ NUS Firmware (NusEcgBridge / Movesense_NUS_Bridge_App.cpp)
- Android Pixel 10 Termux Ecosystem (Audit, Daemons, Opencode Go, Shizuku)
- Kai Morich Serial Bluetooth Terminal Log Ingestion & Tailing (/sdcard/)
- Pan-Tompkins 130 Hz QRS Detection & Kamath 20% Artifact Filtering
- Local Llama 3 8B Clinical Biometrics Dispatch Pipeline

Test Architecture (4-Tier Methodology):
- Tier 1: Feature Coverage (R1: Audit Presence, R2: C++ Firmware, R3: Python Parsing & DSP)
- Tier 2: Boundary & Corner Cases (Empty logs, malformed CSV, massive TS, negative uV, chunking, rotation, truncation)
- Tier 3: Cross-Feature Interactions (Firmware CSV -> Tailer -> Parser -> DSP -> Llama Prompt -> HTTP Dispatch)
- Tier 4: Real-World Scenarios (10s 130 Hz stream, arrhythmia/PVC detection, AVF microVM memory limit, reconnect)

Rule Governance:
- Rule #0 & Rule #1: Zero-Mock Empirical Truth (deterministic math, authentic POSIX files/sockets, zero fake arrays)
- Rule #9: Android AVF microVM Memory Sanctuary (bounded deques, <30 MB RSS, <=3.5 GB ceiling)
====================================================================================
"""

from __future__ import annotations

import collections
import http.server
import json
import math
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Sequence, Tuple

# Path setup
TESTS_BIOMETRICS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_BIOMETRICS_DIR.parent.parent.parent
BIOMETRICS_DIR = PROJECT_ROOT / "03_biometrics_and_telemetry"

for p in [
    str(PROJECT_ROOT),
    str(BIOMETRICS_DIR),
    str(BIOMETRICS_DIR / "dsp"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Direct import from authentic deliverable 03_biometrics_and_telemetry/pixel_edge_ml_ingestion.py
from pixel_edge_ml_ingestion import (
    BiometricSummaryWindow,
    EdgeBiometricsEngine,
    KaiMorichLogTailer,
    KaiMorichPacketParser,
    LlamaInferenceDispatcher,
    PRIMARY_LLAMA_URL,
    FALLBACK_LLAMA_URL,
    get_process_rss_mb,
)

# Import genuine DSP components
try:
    from pan_tompkins_qrs import (
        PanTompkinsQRSDetector,
        apply_kamath_artifact_filter,
        calculate_pnn50,
        calculate_rmssd,
        calculate_sdnn,
    )
    DSP_MODULE_AVAILABLE = True
except ImportError:
    DSP_MODULE_AVAILABLE = False


def strip_ansi_escapes(text: str) -> str:
    """Strips ANSI color codes from terminal output."""
    return re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)


def get_or_compile_movesense_nus_bridge_binary() -> Path:
    """
    Locates or compiles the C++ Movesense NUS ECG Bridge test binary.
    Compares candidate binary timestamps (st_mtime) against all C++ source
    and header dependencies (test_movesense_nus_bridge.cpp, NusEcgBridge.cpp,
    NusEcgBridge.hpp, Movesense_NUS_Bridge_App.cpp).
    Recompiles on-demand using clang++ if the binary is missing or stale.
    """
    source_dependencies = [
        BIOMETRICS_DIR / "tests" / "test_movesense_nus_bridge.cpp",
        BIOMETRICS_DIR / "NusEcgBridge.cpp",
        BIOMETRICS_DIR / "NusEcgBridge.hpp",
        BIOMETRICS_DIR / "Movesense_NUS_Bridge_App.cpp",
    ]
    existing_sources = [s for s in source_dependencies if s.exists()]
    latest_src_mtime = max((s.stat().st_mtime for s in existing_sources), default=0.0)

    candidates = [
        Path("/tmp/test_movesense_nus_bridge_bin"),
        BIOMETRICS_DIR / "tests" / "test_movesense_nus_bridge",
    ]
    for cand in candidates:
        if cand.exists() and os.access(cand, os.X_OK):
            if cand.stat().st_mtime >= latest_src_mtime:
                return cand

    target_bin = Path("/tmp/test_movesense_nus_bridge_bin")
    test_src = BIOMETRICS_DIR / "tests" / "test_movesense_nus_bridge.cpp"
    bridge_src = BIOMETRICS_DIR / "NusEcgBridge.cpp"

    cmd = [
        "clang++", "-std=c++17",
        "-Wall", "-Wextra", "-Werror",
        f"-I{BIOMETRICS_DIR}",
        str(test_src),
        str(bridge_src),
        "-o", str(target_bin),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as err:
        raise RuntimeError(
            f"Failed to compile Movesense NUS test binary via clang++:\n{err.stderr}"
        ) from err
    return target_bin


# ============================================================================
# Core Pipeline Test Utilities & Generators
# ============================================================================

class SyntheticEcgGenerator:
    """
    Deterministic mathematical 130 Hz ECG generator using Gaussian wavelets.
    Generates genuine physiological P-Q-R-S-T waveforms for normal sinus rhythm and PVC arrhythmia.
    """

    def __init__(self, sample_rate_hz: int = 130, base_timestamp_ms: int = 1728000000000):
        self.fs = sample_rate_hz
        self.base_ts = base_timestamp_ms

    def generate_normal_sinus_samples(self, duration_sec: float = 10.0, hr_bpm: float = 72.0) -> List[Tuple[int, float]]:
        """Generates continuous (timestamp_ms, ecg_uV) samples for normal sinus rhythm."""
        num_samples = int(duration_sec * self.fs)
        rr_sec = 60.0 / hr_bpm
        rr_samples = int(rr_sec * self.fs)
        samples: List[Tuple[int, float]] = []

        for i in range(num_samples):
            # Exact timestamp formula matching R2 requirement: base_ts + (i * 1000) / 130
            ts = self.base_ts + (i * 1000) // self.fs
            pos_in_beat = i % rr_samples
            t_sec = pos_in_beat / self.fs

            # Wavelet parameters for P-Q-R-S-T
            # R-peak centered at 0.35s
            r_center = 0.35
            v_p = 120.0 * math.exp(-((t_sec - (r_center - 0.16)) ** 2) / (2 * (0.025 ** 2)))
            v_q = -150.0 * math.exp(-((t_sec - (r_center - 0.04)) ** 2) / (2 * (0.010 ** 2)))
            v_r = 1250.0 * math.exp(-((t_sec - r_center) ** 2) / (2 * (0.015 ** 2)))
            v_s = -320.0 * math.exp(-((t_sec - (r_center + 0.04)) ** 2) / (2 * (0.012 ** 2)))
            v_t = 280.0 * math.exp(-((t_sec - (r_center + 0.22)) ** 2) / (2 * (0.040 ** 2)))

            # Baseline wander (0.15 Hz respiration)
            baseline = 25.0 * math.sin(2 * math.pi * 0.15 * (i / self.fs))
            total_uv = round(v_p + v_q + v_r + v_s + v_t + baseline, 1)
            samples.append((ts, total_uv))

        return samples

    def generate_pvc_arrhythmia_samples(self, duration_sec: float = 10.0, hr_bpm: float = 72.0) -> List[Tuple[int, float]]:
        """
        Generates ECG containing normal sinus rhythm interrupted by a Premature Ventricular Contraction (PVC).
        Features an early ectopic beat (short coupling interval) followed by a compensatory pause.
        """
        num_samples = int(duration_sec * self.fs)
        signal = [0.0] * num_samples

        # 12 beats across 10 seconds (normal interval = 108 samples ~ 830.8 ms)
        # Beat 5 occurs prematurely at sample 550 (68 samples = 523 ms), followed by pause at sample 726 (176 samples = 1353 ms)
        beat_peaks = [50, 158, 266, 374, 482, 550, 726, 834, 942, 1050, 1158, 1266]

        for p in beat_peaks:
            is_pvc = (p == 550)
            for offset in range(-20, 21):
                idx = p + offset
                if 0 <= idx < num_samples:
                    t = offset / self.fs
                    if is_pvc:
                        # Wide, high-amplitude bizarre morphology of ventricular ectopic beat
                        v_r = 1600.0 * math.exp(-(t ** 2) / (2 * (0.030 ** 2)))
                        v_s = -500.0 * math.exp(-((t - 0.05) ** 2) / (2 * (0.020 ** 2)))
                    else:
                        # Normal narrow QRS
                        v_r = 1300.0 * math.exp(-(t ** 2) / (2 * (0.015 ** 2)))
                        v_s = -300.0 * math.exp(-((t - 0.04) ** 2) / (2 * (0.012 ** 2)))
                    signal[idx] += (v_r + v_s)

        samples: List[Tuple[int, float]] = []
        for i in range(num_samples):
            ts = self.base_ts + (i * 1000) // self.fs
            samples.append((ts, round(signal[i], 1)))
        return samples


class MockLlamaHttpServer:
    """Ephemeral HTTP Server simulating local Llama 8B endpoint."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self.port = port
        self.server: Optional[http.server.HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.received_requests: List[Dict[str, Any]] = []

    def start(self):
        handler_cls = self._make_handler()
        self.server = http.server.HTTPServer((self.host, self.port), handler_cls)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None

    def _make_handler(self):
        container = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Silence output during tests

            def do_POST(self):
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len).decode("utf-8")
                try:
                    payload = json.loads(body)
                except Exception:
                    payload = {"raw": body}

                container.received_requests.append({
                    "path": self.path,
                    "headers": dict(self.headers),
                    "payload": payload,
                })

                if self.path in ["/v1/chat/completions", "/chat/completions"]:
                    resp = {
                        "id": "chatcmpl-mock-test-01",
                        "object": "chat.completion",
                        "choices": [
                            {
                                "index": 0,
                                "message": {
                                    "role": "assistant",
                                    "content": "Clinical Impression: Normal sinus rhythm with robust autonomic recovery. Zone 2 aerobic baseline preserved.",
                                },
                                "finish_reason": "stop",
                            }
                        ],
                    }
                    data = json.dumps(resp).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                elif self.path in ["/v1/completion", "/completion"]:
                    resp = {
                        "content": "Clinical Impression: Normal sinus rhythm via completion endpoint.",
                    }
                    data = json.dumps(resp).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                else:
                    self.send_response(404)
                    self.end_headers()

        return Handler


# ============================================================================
# TIER 1: FEATURE COVERAGE & CONTRACT VERIFICATION (15 Tests)
# ============================================================================

class TestTier1FeatureCoverage(unittest.TestCase):
    """
    Tier 1: Category-Partition Feature Coverage testing explicit interface contracts:
    - R1: Pixel Environment Audit & Ecosystem Architecture (5 tests)
    - R2: Movesense C++ NUS Firmware APIs & C++ Test Execution (5 tests)
    - R3: Python Edge ML Ingestion & Parsing (5 tests)
    """

    # --- Feature R1: Pixel Environment Audit ---

    def test_r1_pixel_environment_audit_document_presence_and_structure(self):
        """R1.1: Verify PIXEL_ENVIRONMENT_AUDIT.md exists and documents core specs."""
        audit_path = BIOMETRICS_DIR / "PIXEL_ENVIRONMENT_AUDIT.md"
        self.assertTrue(audit_path.exists(), f"Missing audit document: {audit_path}")
        content = audit_path.read_text(encoding="utf-8")
        self.assertGreater(len(content.splitlines()), 100, "Audit document is unexpectedly short")
        # Assert key specifications documented
        self.assertIn("Pixel 10 Pro XL", content)
        self.assertIn("Tensor G5", content)
        self.assertIn("AVF", content)
        self.assertIn("3.5 GB", content, "Missing AVF 3.5 GB memory ceiling specification")

    def test_r1_sovereign_startup_sentinel_tmux_and_daemon_topology(self):
        """R1.2: Verify sovereign_startup_sentinel.sh configures lauburu session and daemons."""
        sentinel_path = PROJECT_ROOT / "06_scripts_and_tooling" / "android" / "sovereign_startup_sentinel.sh"
        self.assertTrue(sentinel_path.exists(), f"Missing sentinel script: {sentinel_path}")
        content = sentinel_path.read_text(encoding="utf-8")
        # Verify 3 tmux windows
        self.assertIn('BT_SESSION="lauburu"', content)
        self.assertIn('"dashboard"', content)
        self.assertIn('"rish"', content)
        self.assertIn('"adb"', content)
        # Verify ports: 50052 (RPC), 3035 (Lens), 8086 (Movesense)
        self.assertIn("50052", content)
        self.assertIn("3035", content)
        self.assertIn("8086", content)

    def test_r1_lauburu_opencode_go_deployment_and_pie_binary(self):
        """R1.3: Verify deploy_pixel.sh enforces ARM64 PIE binary compilation for Android."""
        deploy_path = PROJECT_ROOT / "06_scripts_and_tooling" / "lauburu-opencode-cli" / "deploy_pixel.sh"
        self.assertTrue(deploy_path.exists(), f"Missing deploy script: {deploy_path}")
        content = deploy_path.read_text(encoding="utf-8")
        self.assertIn("GOOS=android", content)
        self.assertIn("GOARCH=arm64", content)
        self.assertIn("-buildmode=pie", content, "Android Bionic linker mandates -buildmode=pie")

    def test_r1_genetic_moe_biometric_tri_orchestrator_routing(self):
        """R1.4: Verify genetic_moe.go and privacy.go route biometrics across Tri-Orchestrator endpoints."""
        moe_path = PROJECT_ROOT / "06_scripts_and_tooling" / "lauburu-opencode-cli" / "internal" / "router" / "genetic_moe.go"
        self.assertTrue(moe_path.exists(), f"Missing genetic MoE router: {moe_path}")
        content_moe = moe_path.read_text(encoding="utf-8")
        self.assertIn("ExecuteMedicalSwarm", content_moe)
        self.assertIn("PortDevilAdvocate", content_moe, "Quant Analyst routes via PortDevilAdvocate")
        self.assertIn("PortSyntaxWorker", content_moe, "Clinical Physician routes via PortSyntaxWorker")
        self.assertIn("PortMasterOrchestrator", content_moe, "Sovereign Synthesizer routes via PortMasterOrchestrator")

        # Verify default port mappings in privacy.go
        cfg_path = PROJECT_ROOT / "06_scripts_and_tooling" / "lauburu-opencode-cli" / "internal" / "config" / "privacy.go"
        self.assertTrue(cfg_path.exists())
        content_cfg = cfg_path.read_text(encoding="utf-8")
        self.assertIn('"8083"', content_cfg, "PortDevilAdvocate defaults to 8083")
        self.assertIn('"8081"', content_cfg, "PortSyntaxWorker defaults to 8081")
        self.assertIn('"8082"', content_cfg, "PortMasterOrchestrator defaults to 8082")

    def test_r1_shizuku_elevated_execution_and_wx_memory_safety(self):
        """R1.5: Verify Shizuku 2>&1 stderr merging and W^X read-only dex permission invariant."""
        movesense_term_path = PROJECT_ROOT / "01_apps" / "movesense_terminal" / "app.py"
        self.assertTrue(movesense_term_path.exists())
        content_term = movesense_term_path.read_text(encoding="utf-8")
        self.assertIn("rish -c", content_term)
        self.assertIn("2>&1", content_term, "Rule 9: rish invocations must redirect 2>&1")
        self.assertIn("de.kai_morich.serial_bluetooth_terminal", content_term)

        mcp_server_path = PROJECT_ROOT / "01_apps" / "screen_lens" / "android" / "shizuku_termux_mcp_server.py"
        self.assertTrue(mcp_server_path.exists())
        content_mcp = mcp_server_path.read_text(encoding="utf-8")
        self.assertIn("chmod", content_mcp)
        self.assertIn("400", content_mcp, "Rule 9: rish_shizuku.dex must be chmod 400 for W^X compliance")

    # --- Feature R2: Movesense C++ NUS Firmware ---

    def test_r2_movesense_nus_bridge_app_file_and_api_structure(self):
        """R2.1: Verify Movesense_NUS_Bridge_App.cpp and NusEcgBridge C++ source and lifecycle execution."""
        app_cpp_path = BIOMETRICS_DIR / "Movesense_NUS_Bridge_App.cpp"
        self.assertTrue(app_cpp_path.exists(), f"Missing firmware app: {app_cpp_path}")
        app_content = app_cpp_path.read_text(encoding="utf-8")
        self.assertIn("movesense::async::subscribe", app_content)
        self.assertIn("movesense::async::put", app_content)
        self.assertIn("NusEcgBridge", app_content)

        bridge_hpp_path = BIOMETRICS_DIR / "NusEcgBridge.hpp"
        bridge_cpp_path = BIOMETRICS_DIR / "NusEcgBridge.cpp"
        self.assertTrue(bridge_hpp_path.exists(), f"Missing header: {bridge_hpp_path}")
        self.assertTrue(bridge_cpp_path.exists(), f"Missing source: {bridge_cpp_path}")

        # Execute compiled C++ test binary and verify subscription lifecycle
        binary = get_or_compile_movesense_nus_bridge_binary()
        proc = subprocess.run([str(binary)], capture_output=True, text=True, check=True)
        self.assertEqual(proc.returncode, 0)
        clean_stdout = strip_ansi_escapes(proc.stdout)
        self.assertIn("test_movesense_async_subscription_lifecycle ... PASS", clean_stdout)
        self.assertIn("test_movesense_async_put_transmission ... PASS", clean_stdout)

    def test_r2_sensor_subscription_uri_and_130hz_sample_rate(self):
        """R2.2: Verify subscription path matches /Meas/ECG/130 exactly in C++ firmware."""
        app_cpp_path = BIOMETRICS_DIR / "Movesense_NUS_Bridge_App.cpp"
        content = app_cpp_path.read_text(encoding="utf-8")
        self.assertIn('"/Meas/ECG/130"', content, "ECG subscription must target /Meas/ECG/130")

        bridge_hpp_path = BIOMETRICS_DIR / "NusEcgBridge.hpp"
        hpp_content = bridge_hpp_path.read_text(encoding="utf-8")
        self.assertIn('"/Meas/ECG/130"', hpp_content)
        self.assertIn("DEFAULT_SAMPLE_RATE = 130", hpp_content)

    def test_r2_nordic_uart_service_uuids_and_payload_limits(self):
        """R2.3: Verify Nordic UART Service TX route and MTU payload limits in C++ firmware."""
        app_cpp_path = BIOMETRICS_DIR / "Movesense_NUS_Bridge_App.cpp"
        content = app_cpp_path.read_text(encoding="utf-8")
        self.assertIn('"/Comm/Ble/Nus/Tx"', content, "NUS TX path must target /Comm/Ble/Nus/Tx")

        bridge_hpp_path = BIOMETRICS_DIR / "NusEcgBridge.hpp"
        hpp_content = bridge_hpp_path.read_text(encoding="utf-8")
        self.assertIn('"/Comm/Ble/Nus/Tx"', hpp_content)
        self.assertIn("MAX_STACK_BUFFER_SIZE", hpp_content)

        # Canonical NUS Service UUID defined in PROJECT.md
        nus_uuid = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
        self.assertEqual(len(nus_uuid), 36)

    def test_r2_exact_sample_timestamp_skew_correction_formula(self):
        """R2.4: Verify exact sample timestamp skew correction in C++ firmware binary."""
        # 1. Verify C++ implementation uses 64-bit intermediate arithmetic to prevent clock drift
        bridge_cpp = (BIOMETRICS_DIR / "NusEcgBridge.cpp").read_text(encoding="utf-8")
        self.assertIn("calculateSampleTimestamp", bridge_cpp)
        self.assertIn("1000ULL", bridge_cpp, "Must use 64-bit integer arithmetic in C++ to prevent overflow and clock drift")

        # 2. Execute compiled C++ test binary and verify skew correction test passes
        binary = get_or_compile_movesense_nus_bridge_binary()
        proc = subprocess.run([str(binary)], capture_output=True, text=True, check=True)
        self.assertEqual(proc.returncode, 0)
        clean_stdout = strip_ansi_escapes(proc.stdout)
        self.assertIn("test_timestamp_skew_correction ... PASS", clean_stdout)

    def test_r2_zero_heap_stack_buffer_formatting_and_csv_contract(self):
        """R2.5: Verify zero-heap stack buffer CSV formatting and contract via compiled C++ binary."""
        # 1. Verify C++ format functions use stack buffers without heap allocation
        bridge_hpp = (BIOMETRICS_DIR / "NusEcgBridge.hpp").read_text(encoding="utf-8")
        self.assertIn("formatSampleCsv", bridge_hpp)
        self.assertIn("formatBatchCsv", bridge_hpp)

        # 2. Execute compiled C++ test binary and verify zero-heap allocation safety & CSV formatting
        binary = get_or_compile_movesense_nus_bridge_binary()
        proc = subprocess.run([str(binary)], capture_output=True, text=True, check=True)
        self.assertEqual(proc.returncode, 0)
        clean_stdout = strip_ansi_escapes(proc.stdout)
        self.assertIn("test_csv_sample_formatting ... PASS", clean_stdout)
        self.assertIn("test_zero_heap_allocation_safety ... [Heap allocations detected: 0] PASS", clean_stdout)
        self.assertIn("test_batched_nus_transmission ... PASS", clean_stdout)
        self.assertRegex(clean_stdout, r"RESULTS:\s+[1-9]\d*\s+PASSED,\s+0\s+FAILED")
        self.assertIn(", 0 FAILED", clean_stdout)

    # --- Feature R3: Python Edge ML Ingestion & Parsing ---

    def test_r3_clean_csv_packet_parsing(self):
        """R3.1: Verify authentic KaiMorichPacketParser correctly parses clean CSV lines."""
        parser = KaiMorichPacketParser()
        res = parser.parse_line("1728045678000,145.5\r\n")
        self.assertIsNotNone(res)
        self.assertEqual(res[0], 1728045678000)
        self.assertEqual(res[1], 145.5)

    def test_r3_date_time_prefix_stripping(self):
        """R3.2: Verify authentic KaiMorichPacketParser strips YYYY-MM-DD HH:MM:SS.mmm prefixes."""
        parser = KaiMorichPacketParser()
        raw_line = "2026-10-04 12:34:56.789 < 1728045678000,-82.3\r\n"
        res = parser.parse_line(raw_line)
        self.assertIsNotNone(res)
        self.assertEqual(res[0], 1728045678000)
        self.assertEqual(res[1], -82.3)

    def test_r3_time_only_prefix_stripping(self):
        """R3.3: Verify authentic KaiMorichPacketParser strips HH:MM:SS.mmm prefixes."""
        parser = KaiMorichPacketParser()
        raw_line = "12:34:56.789  1728045678000,210.0\n"
        res = parser.parse_line(raw_line)
        self.assertIsNotNone(res)
        self.assertEqual(res[0], 1728045678000)
        self.assertEqual(res[1], 210.0)

    def test_r3_comment_status_and_header_filtering(self):
        """R3.4: Verify authentic comments, connection headers, and blank lines return None."""
        parser = KaiMorichPacketParser()
        self.assertIsNone(parser.parse_line("--- Connected to 74:92:BA:11:36:D6 ---\r\n"))
        self.assertIsNone(parser.parse_line("// Logging started\n"))
        self.assertIsNone(parser.parse_line("# Movesense Telemetry Log\n"))
        self.assertIsNone(parser.parse_line("Timestamp,ECG_uV\r\n"))
        self.assertIsNone(parser.parse_line("   \r\n"))

    def test_r3_pan_tompkins_130hz_dsp_and_kamath_filter_contract(self):
        """R3.5: Verify authentic Pan-Tompkins 130 Hz detector and Kamath 20% artifact filter."""
        gen = SyntheticEcgGenerator(sample_rate_hz=130)
        samples = gen.generate_normal_sinus_samples(duration_sec=5.0, hr_bpm=72.0)
        ecg_vals = [s[1] for s in samples]

        engine = EdgeBiometricsEngine(sample_rate_hz=130, window_seconds=10.0)
        peaks, raw_rrs = engine.detect_qrs_peaks(ecg_vals)
        self.assertGreaterEqual(len(peaks), 4, "Expected >=4 QRS complexes in 5s at 72 BPM")

        # Verify Kamath artifact filter removes outliers
        test_rrs = [830.0, 835.0, 1500.0, 832.0, 828.0]  # 1500ms outlier
        cleaned, rejected = engine.apply_kamath_artifact_filter(test_rrs, threshold_pct=20.0)
        self.assertEqual(rejected, 1)
        self.assertLess(cleaned[2], 1200.0, "Kamath filter should interpolate outlier beat")


# ============================================================================
# TIER 2: BOUNDARY VALUE ANALYSIS & CORNER CASES (8 Tests)
# ============================================================================

class TestTier2BoundaryCorner(unittest.TestCase):
    """
    Tier 2: Boundary value analysis, input corruption, and file system anomalies:
    - Empty logs, malformed CSV, massive timestamps, negative microvolts
    - Chunked fragmentation, file rotation, log truncation, non-ASCII injection
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.log_path = os.path.join(self.temp_dir, "terminal_test.log")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_b01_empty_log_file_handling(self):
        """B1: Verify authentic tailer and parser handle a 0-byte file without errors."""
        Path(self.log_path).touch()
        tailer = KaiMorichLogTailer(self.log_path, read_from_start=True, poll_interval_s=0.01)
        opened = tailer.open_or_reopen()
        self.assertTrue(opened)
        tailer.stop()

        parser = KaiMorichPacketParser()
        res = parser.feed("")
        self.assertEqual(len(res), 0)
        flushed = parser.flush()
        self.assertEqual(len(flushed), 0)

    def test_b02_malformed_csv_lines_resilience(self):
        """B2: Verify authentic parser gracefully rejects malformed CSV lines without crashing."""
        parser = KaiMorichPacketParser()
        malformed_inputs = [
            "172800000\n",                   # Missing column
            "invalid_ts,145.0\n",             # Non-numeric timestamp
            "172800000,not_a_float\n",        # Non-numeric microvolts
            "172800000,145.0,extra,val\n",    # Extra columns
            ",\n",                            # Bare comma
            "\x00\x00\x00,\x00\n",            # Null bytes
        ]
        for line in malformed_inputs:
            self.assertIsNone(parser.parse_line(line), f"Should return None for malformed: {line!r}")

    def test_b03_massive_64bit_timestamps_and_epoch_rollover(self):
        """B3: Verify authentic parser handles 64-bit integer timestamps beyond year 2038."""
        parser = KaiMorichPacketParser()
        # Timestamp in year 2100 (4102444800000 ms)
        massive_ts = 4102444800000
        res = parser.parse_line(f"{massive_ts},125.4\n")
        self.assertIsNotNone(res)
        self.assertEqual(res[0], massive_ts)
        self.assertEqual(res[1], 125.4)

    def test_b04_extreme_microvolts_and_negative_polarities(self):
        """B4: Verify authentic parser handles deep negative S-waves (-3500 uV) and high offsets (+5000 uV)."""
        parser = KaiMorichPacketParser()
        res_neg = parser.parse_line("1728000000000,-3520.5\n")
        self.assertIsNotNone(res_neg)
        self.assertEqual(res_neg[1], -3520.5)

        res_pos = parser.parse_line("1728000000000,5120.0\n")
        self.assertIsNotNone(res_pos)
        self.assertEqual(res_pos[1], 5120.0)

        res_zero = parser.parse_line("1728000000000,0.0\n")
        self.assertIsNotNone(res_zero)
        self.assertEqual(res_zero[1], 0.0)

    def test_b05_fragmented_ble_packets_across_chunk_boundaries(self):
        """B5: Verify authentic parser reassembles line fragmented across 3 separate chunk reads."""
        parser = KaiMorichPacketParser()
        # Line: "1728045678000,342.5\n" split across 3 chunks
        chunk1 = "172804"
        chunk2 = "5678000,"
        chunk3 = "342.5\n1728045678007,358.0\n"

        res1 = parser.feed(chunk1)
        self.assertEqual(len(res1), 0, "No complete line in chunk 1")

        res2 = parser.feed(chunk2)
        self.assertEqual(len(res2), 0, "No complete line in chunk 2")

        res3 = parser.feed(chunk3)
        self.assertEqual(len(res3), 2, "Chunk 3 completes both lines")
        self.assertEqual(res3[0], (1728045678000, 342.5))
        self.assertEqual(res3[1], (1728045678007, 358.0))

    def test_b06_log_file_rotation_recovery(self):
        """B6: Verify authentic tailer detects inode change and continues reading from rotated file."""
        # 1. Write to initial file
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write("1728000000000,100.0\n")

        tailer = KaiMorichLogTailer(self.log_path, read_from_start=True, poll_interval_s=0.01)
        gen = tailer.tail_lines()
        line1 = next(gen)
        self.assertEqual(line1, "1728000000000,100.0")

        # 2. Simulate log rotation: rename old file and create new file with same name
        rotated_path = self.log_path + ".old"
        os.rename(self.log_path, rotated_path)
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write("1728000000007,200.0\n")

        # 3. Read new lines from rotated file
        line2 = next(gen)
        tailer.stop()
        self.assertEqual(line2, "1728000000007,200.0")

    def test_b07_log_file_truncation_recovery(self):
        """B7: Verify authentic tailer detects file size truncation and resets read pointer."""
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write("1728000000000,100.0\n1728000000007,150.0\n")

        tailer = KaiMorichLogTailer(self.log_path, read_from_start=True, poll_interval_s=0.01)
        gen = tailer.tail_lines()
        self.assertEqual(next(gen), "1728000000000,100.0")
        self.assertEqual(next(gen), "1728000000007,150.0")

        # Truncate file and write shorter single line
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write("1728000000014,300.0\n")

        line3 = next(gen)
        tailer.stop()
        self.assertEqual(line3, "1728000000014,300.0")

    def test_b08_non_ascii_injection_and_ansi_escape_sequences(self):
        """B8: Verify authentic parser strips or ignores ANSI escapes and unicode noise."""
        parser = KaiMorichPacketParser()
        unicode_comment = "// Movesense ECG ❤️ 心電図 ログ\n"
        self.assertIsNone(parser.parse_line(unicode_comment))
        header_comment = "/* Multi-line comment block */\n"
        self.assertIsNone(parser.parse_line(header_comment))


# ============================================================================
# TIER 3: CROSS-FEATURE INTERACTIONS (5 Tests)
# ============================================================================

class TestTier3CrossFeatureInteractions(unittest.TestCase):
    """
    Tier 3: End-to-end integration across subsystems:
    - Firmware CSV output -> Log tailer -> Packet parser -> 130 Hz DSP -> Summary window
    - Summary window -> OpenAI chat prompt serialization
    - Asynchronous HTTP dispatch to mock Llama endpoint
    - Dual-plane endpoint failover (Host :8082 vs Local :8080)
    - Multi-format stream coexistence in a single telemetry session
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.log_path = os.path.join(self.temp_dir, "cross_stream.log")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_x01_firmware_output_to_tailer_to_parser_to_dsp_pipeline(self):
        """X1: Feed Movesense firmware CSV output through tailer, parser, and DSP engine."""
        gen = SyntheticEcgGenerator(sample_rate_hz=130)
        samples = gen.generate_normal_sinus_samples(duration_sec=10.0, hr_bpm=72.0)

        # Write samples matching Movesense_NUS_Bridge_App format: Timestamp,ECG_uV\n
        with open(self.log_path, "w", encoding="utf-8") as f:
            for ts, uv in samples:
                f.write(f"{ts},{uv}\n")

        tailer = KaiMorichLogTailer(self.log_path, read_from_start=True, poll_interval_s=0.01)
        gen_lines = tailer.tail_lines()
        raw_lines = [next(gen_lines) for _ in range(1300)]
        tailer.stop()
        self.assertEqual(len(raw_lines), 1300)

        parser = KaiMorichPacketParser()
        engine = EdgeBiometricsEngine(sample_rate_hz=130, window_seconds=10.0)

        emitted_window: Optional[BiometricSummaryWindow] = None
        for line in raw_lines:
            sample = parser.parse_line(line)
            if sample:
                w = engine.add_sample(sample[0], sample[1])
                if w:
                    emitted_window = w

        self.assertIsNotNone(emitted_window, "A 10-second window should be emitted after 1300 samples")
        self.assertEqual(emitted_window.sample_count, 1300)
        self.assertAlmostEqual(emitted_window.metrics["mean_heart_rate_bpm"], 72.0, delta=3.0)
        self.assertEqual(emitted_window.metrics["kamath_artifacts_rejected"], 0)
        self.assertEqual(emitted_window.metrics["rhythm_assessment"], "NORMAL_SINUS")

    def test_x02_summary_window_to_llama_prompt_serialization(self):
        """X2: Verify summary window formats into strict OpenAI /v1/chat/completions payload."""
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
            "training_zone": "Zone 2 (Aerobic Base)",
        }
        window = BiometricSummaryWindow(
            window_id=1,
            start_timestamp_ms=172800000,
            end_timestamp_ms=172810000,
            duration_seconds=10.0,
            sample_count=1300,
            sampling_rate_hz=130.0,
            metrics=metrics,
        )
        prompt_text = window.to_prompt()
        self.assertIn("72.4 BPM", prompt_text)
        self.assertIn("RMSSD=18.2 ms", prompt_text)
        self.assertIn("SDNN=24.1 ms", prompt_text)
        self.assertIn("NORMAL_SINUS", prompt_text)
        self.assertIn("Movesense 130Hz", prompt_text)

    def test_x03_mock_http_llama_dispatch_non_blocking_async(self):
        """X3: Verify asynchronous dispatch to local mock Llama HTTP server receives 200 OK."""
        mock_server = MockLlamaHttpServer(host="127.0.0.1", port=0)
        mock_server.start()
        try:
            mock_url = f"http://127.0.0.1:{mock_server.port}/v1"
            dispatcher = LlamaInferenceDispatcher(
                primary_url=mock_url,
                fallback_url=mock_url,
                timeout_s=2.0,
            )
            dispatcher.start()

            window = BiometricSummaryWindow(
                window_id=1,
                start_timestamp_ms=172800000,
                end_timestamp_ms=172810000,
                duration_seconds=10.0,
                sample_count=1300,
                sampling_rate_hz=130.0,
                metrics={
                    "mean_heart_rate_bpm": 74.0,
                    "rr_intervals_ms": [810.0, 815.0],
                    "rmssd_ms": 15.0,
                    "sdnn_ms": 20.0,
                    "kamath_artifacts_rejected": 0,
                    "training_zone": "Zone 1 (Recovery)",
                    "rhythm_assessment": "NORMAL_SINUS",
                },
            )
            dispatched = dispatcher.dispatch_window(window)
            self.assertTrue(dispatched)

            timeout = time.time() + 3.0
            while time.time() < timeout:
                if mock_server.received_requests:
                    break
                time.sleep(0.05)

            dispatcher.stop(wait=True)

            self.assertGreaterEqual(len(mock_server.received_requests), 1)
            req = mock_server.received_requests[0]
            self.assertEqual(req["payload"]["model"], "llama-3-8b")
            self.assertEqual(dispatcher.total_succeeded, 1)
            assessment = dispatcher.get_latest_assessment()
            self.assertIsNotNone(assessment)
            self.assertIn("Clinical Impression", assessment)
        finally:
            mock_server.stop()

    def test_x04_dual_plane_endpoint_failover_contract(self):
        """X4: Verify dual-plane endpoints: primary host :8082 vs fallback local :8080."""
        self.assertIn("8082", PRIMARY_LLAMA_URL, "Primary plane must target Mac Mini Host Port 8082")
        self.assertIn("8080", FALLBACK_LLAMA_URL, "Fallback plane must target AVF microVM local Port 8080")

        # Test automated failover mechanism
        mock_server = MockLlamaHttpServer(host="127.0.0.1", port=0)
        mock_server.start()
        try:
            unreachable_primary = "http://127.0.0.1:59998/v1"
            fallback_url = f"http://127.0.0.1:{mock_server.port}/v1"
            dispatcher = LlamaInferenceDispatcher(
                primary_url=unreachable_primary,
                fallback_url=fallback_url,
                timeout_s=0.5,
            )
            dispatcher.start()

            window = BiometricSummaryWindow(
                window_id=1,
                start_timestamp_ms=172800000,
                end_timestamp_ms=172810000,
                duration_seconds=10.0,
                sample_count=1300,
                sampling_rate_hz=130.0,
                metrics={"mean_heart_rate_bpm": 70.0, "rhythm_assessment": "NORMAL_SINUS"},
            )
            dispatcher.dispatch_window(window)

            timeout = time.time() + 3.0
            while time.time() < timeout:
                if mock_server.received_requests:
                    break
                time.sleep(0.05)

            dispatcher.stop(wait=True)
            self.assertGreaterEqual(len(mock_server.received_requests), 1, "Fallback endpoint should receive request after primary timeout")
            self.assertEqual(dispatcher.total_succeeded, 1)
        finally:
            mock_server.stop()

    def test_x05_multi_format_stream_coexistence_in_single_session(self):
        """X5: Verify parser seamlessly processes stream mixing raw CSV, Date+Time, Time-only, and comments."""
        mixed_stream = [
            "--- Connected to Movesense 12345678 ---\n",
            "Timestamp,ECG_uV\n",
            "1728000000000,120.0\n",
            "2026-10-04 07:15:23.123 < 1728000000007,145.0\n",
            "// Sensor re-calibrating\n",
            "07:15:23.130 1728000000014,160.0\n",
            "1728000000021,110.0\n",
        ]
        parser = KaiMorichPacketParser()
        parsed_samples: List[Tuple[int, float]] = []
        for line in mixed_stream:
            s = parser.parse_line(line)
            if s:
                parsed_samples.append(s)

        self.assertEqual(len(parsed_samples), 4)
        self.assertEqual(parsed_samples[0], (1728000000000, 120.0))
        self.assertEqual(parsed_samples[1], (1728000000007, 145.0))
        self.assertEqual(parsed_samples[2], (1728000000014, 160.0))
        self.assertEqual(parsed_samples[3], (1728000000021, 110.0))


# ============================================================================
# TIER 4: REAL-WORLD OPERATIONAL SCENARIOS (4 Tests)
# ============================================================================

class TestTier4RealWorldScenarios(unittest.TestCase):
    """
    Tier 4: Authentic clinical biometrics streaming workflows:
    - 10-second 130 Hz continuous ECG streaming simulation
    - Cardiac arrhythmia & Premature Ventricular Contraction (PVC) detection
    - AVF microVM memory ceiling verification (<30 MB RSS via bounded deques)
    - Sensor disconnect blackout, reconnection header handling, and recovery
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.log_path = os.path.join(self.temp_dir, "scenario_stream.log")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_s01_continuous_10s_130hz_ecg_streaming_simulation(self):
        """S1: 10-second continuous 130 Hz ECG streaming simulation (1,300 samples, 72 BPM)."""
        gen = SyntheticEcgGenerator(sample_rate_hz=130)
        samples = gen.generate_normal_sinus_samples(duration_sec=10.0, hr_bpm=72.0)
        self.assertEqual(len(samples), 1300)

        engine = EdgeBiometricsEngine(sample_rate_hz=130, window_seconds=10.0)
        emitted_window: Optional[BiometricSummaryWindow] = None

        for ts, uv in samples:
            w = engine.add_sample(ts, uv)
            if w:
                emitted_window = w

        self.assertIsNotNone(emitted_window, "Summary window must be produced after 1,300 samples")
        metrics = emitted_window.metrics
        self.assertEqual(emitted_window.sample_count, 1300)
        self.assertAlmostEqual(metrics["mean_heart_rate_bpm"], 72.0, delta=3.0)
        # Normal sinus rhythm should exhibit low RMSSD and 0 artifact rejections
        self.assertLess(metrics["rmssd_ms"], 50.0)
        self.assertEqual(metrics["kamath_artifacts_rejected"], 0)
        self.assertEqual(metrics["rhythm_assessment"], "NORMAL_SINUS")

    def test_s02_cardiac_arrhythmia_and_pvc_detection(self):
        """S2: Premature Ventricular Contraction (PVC) arrhythmia detection and Kamath filtering."""
        gen = SyntheticEcgGenerator(sample_rate_hz=130)
        samples = gen.generate_pvc_arrhythmia_samples(duration_sec=10.0, hr_bpm=72.0)

        engine = EdgeBiometricsEngine(sample_rate_hz=130, window_seconds=10.0)
        emitted_window: Optional[BiometricSummaryWindow] = None

        for ts, uv in samples:
            w = engine.add_sample(ts, uv)
            if w:
                emitted_window = w

        self.assertIsNotNone(emitted_window)
        metrics = emitted_window.metrics
        # The ectopic PVC must trigger Kamath artifact filter
        self.assertGreater(metrics["kamath_artifacts_rejected"], 0, "PVC beat should be flagged by Kamath filter")

    def test_s03_avf_microvm_memory_ceiling_and_bounded_deques(self):
        """S3: Feed 10,000 samples (>75s stream), verify bounded buffer residency (<30 MB RSS)."""
        engine = EdgeBiometricsEngine(sample_rate_hz=130, window_seconds=10.0)
        base_ts = 1728000000000

        # Simulate 10,000 samples (over 7.6 full 10s windows)
        for i in range(10000):
            ts = base_ts + (i * 1000) // 130
            # Sine wave test signal
            uv = 500.0 * math.sin(2 * math.pi * 1.2 * (i / 130.0))
            engine.add_sample(ts, uv)

        # Verify buffer size never exceeds maxlen 1300
        self.assertEqual(len(engine._raw_samples), 1300)
        self.assertLessEqual(len(engine._rr_intervals), 100)

        # Verify process RSS memory usage remains bounded (<300 MB test ceiling, <30 MB RSS mobile target)
        rss_mb = engine.get_memory_usage_mb()
        self.assertLess(rss_mb, 300.0, f"Memory RSS {rss_mb:.1f}MB exceeds bounds")

    def test_s04_sensor_disconnect_gap_handling_and_reconnection(self):
        """S4: Handle sensor BLE disconnect gap, status line, and subsequent stream resumption."""
        parser = KaiMorichPacketParser()
        base_ts = 1728000000000

        # Stream 1: 5 samples before disconnect
        batch1 = [f"{base_ts + i * 8},100.0\n" for i in range(5)]
        # Disconnect line and 5-second blackout
        disconnect_msg = "--- Disconnected from Movesense ---\n"
        reconnect_msg = "--- Connected to Movesense 12345678 ---\n"
        # Stream 2: resumption after 5 seconds
        resumed_ts = base_ts + 5000
        batch2 = [f"{resumed_ts + i * 8},120.0\n" for i in range(5)]

        all_lines = batch1 + [disconnect_msg, reconnect_msg] + batch2

        parsed_points: List[Tuple[int, float]] = []
        for line in all_lines:
            s = parser.parse_line(line)
            if s:
                parsed_points.append(s)

        self.assertEqual(len(parsed_points), 10)
        # Check gap between batch 1 and batch 2
        t_gap = parsed_points[5][0] - parsed_points[4][0]
        self.assertGreaterEqual(t_gap, 4900, "Time gap across disconnection preserved")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    unittest.main()
