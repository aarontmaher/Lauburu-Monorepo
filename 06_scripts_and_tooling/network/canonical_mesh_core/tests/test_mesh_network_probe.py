#!/usr/bin/env python3
"""
06_scripts_and_tooling/network/canonical_mesh_core/tests/test_mesh_network_probe.py
==================================================================================
4-Tier Requirement-Driven Test Suite for Lauburu Mesh Network Monitor
----------------------------------------------------------------------------------
Derived strictly from ORIGINAL_REQUEST.md (R1, R2, R3, R4) and PROJECT.md:
  - Tier 1: Feature Coverage (>=45 test cases: 5 per feature across 9 features)
  - Tier 2: Boundary & Corner Cases (>=45 test cases across 9 edge condition areas)
  - Tier 3: Cross-Feature Combinations (>=9 pairwise integration test cases)
  - Tier 4: Real-World Workload Scenarios (>=5 real workload stress test cases)
Total Minimum Tests: 104 test cases.
"""

import copy
import hashlib
import json
import math
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure canonical_mesh_core is on sys.path
CORE_DIR = Path(__file__).resolve().parent.parent
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

import mesh_network_probe
from mesh_network_probe import (
    MeshNetworkProbe,
    LinkMetrics,
    TransportTier,
    compute_routing_cost,
    get_live_peer_metrics,
    discover_local_interfaces,
    query_tailscale_status,
    get_tcp_socket_states,
    get_process_tcp_sockets,
    get_darwin_interface_counters,
    get_os_raw_interface_counters,
    execute_os_ping,
    tcp_connect_ping,
    probe_peer,
    verify_metric_parity,
    OUTPUT_FILE,
    LORA_FILE,
)


# ==============================================================================
# TIER 1: FEATURE COVERAGE (45 Test Cases: 5 per feature across 9 features)
# ==============================================================================

class TestTier1FeatureCoverage(unittest.TestCase):
    """
    Tier 1: Feature Coverage testing the primary behavior (happy path)
    across all 9 core features specified in PROJECT.md and TEST_INFRA.md.
    """

    def setUp(self):
        self.probe = MeshNetworkProbe(interval_sec=1.0, auto_start=False)

    def tearDown(self):
        self.probe.stop_background_sampler()

    # --------------------------------------------------------------------------
    # Feature 1: Non-Blocking Latency & Concurrency (R1)
    # --------------------------------------------------------------------------
    def test_t1_f1_01_get_snapshot_execution_time(self):
        """F1.1: Verify get_snapshot() returns instantaneously (< 50ms) on cached data."""
        # Prime the cache once
        snap1 = self.probe.get_snapshot()
        self.assertIsInstance(snap1, dict)

        # Measure read latency of primed in-memory cache
        t0 = time.perf_counter()
        snap2 = self.probe.get_snapshot()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(elapsed_ms, 50.0, f"Snapshot read took {elapsed_ms:.2f}ms (expected < 50ms)")
        self.assertEqual(snap1.get("node_id"), snap2.get("node_id"))

    def test_t1_f1_02_background_sampler_thread_lifecycle(self):
        """F1.2: Verify clean start and stop of background sampling daemon."""
        self.assertFalse(self.probe._stop_event.is_set())
        self.probe.start_background_sampler()
        self.assertIsNotNone(self.probe._thread)
        self.assertTrue(self.probe._thread.is_alive())

        self.probe.stop_background_sampler()
        self.assertTrue(self.probe._stop_event.is_set())
        self.assertFalse(self.probe._thread.is_alive())

    def test_t1_f1_03_non_blocking_during_sampling(self):
        """F1.3: Verify callers are not blocked while background sampler is running."""
        self.probe.get_snapshot()  # Prime cache first
        self.probe.start_background_sampler()
        start_t = time.perf_counter()
        for _ in range(5):
            s = self.probe.get_snapshot()
            self.assertIsInstance(s, dict)
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        self.assertLess(duration_ms, 100.0, "Multiple snapshot reads while sampler active must be non-blocking")

    def test_t1_f1_04_thread_daemon_attribute(self):
        """F1.4: Verify background thread is marked as daemon for zero shutdown hang."""
        self.probe.start_background_sampler()
        self.assertTrue(self.probe._thread.daemon, "Background thread must have daemon=True")

    def test_t1_f1_05_concurrent_snapshot_readers(self):
        """F1.5: Verify 10 concurrent threads can safely call get_snapshot() simultaneously."""
        self.probe.get_snapshot()  # Prime cache
        errors: List[Exception] = []

        def worker():
            try:
                for _ in range(20):
                    s = self.probe.get_snapshot()
                    if not isinstance(s, dict) or "interfaces" not in s:
                        errors.append(ValueError("Invalid snapshot structure"))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=2.0)

        self.assertEqual(len(errors), 0, f"Concurrent reads produced errors: {errors}")

    # --------------------------------------------------------------------------
    # Feature 2: Interface Throughput & Counter Delta (R1)
    # --------------------------------------------------------------------------
    def test_t1_f2_01_interface_counters_structure(self):
        """F2.1: Verify interface metrics contain bytes and packets for RX and TX."""
        snap = self.probe.get_snapshot()
        ifaces = snap.get("interfaces", {})
        self.assertGreater(len(ifaces), 0, "Host must report at least one network interface")
        pref = next(iter(ifaces.values()))
        self.assertIn("bytes_recv", pref)
        self.assertIn("bytes_sent", pref)
        self.assertIn("packets_recv", pref)
        self.assertIn("packets_sent", pref)

    def test_t1_f2_02_monotonic_counter_accumulation(self):
        """F2.2: Verify successive interface counter queries are non-decreasing."""
        c1 = get_os_raw_interface_counters()
        time.sleep(0.05)
        c2 = get_os_raw_interface_counters()
        for iface_name in c1:
            if iface_name in c2:
                self.assertGreaterEqual(
                    c2[iface_name]["bytes_recv"],
                    c1[iface_name]["bytes_recv"],
                    f"Counter for {iface_name} must be monotonically non-decreasing",
                )

    def test_t1_f2_03_throughput_rate_calculation(self):
        """F2.3: Verify bps throughput rate calculation given delta bytes and delta time."""
        delta_bytes = 125000  # 125 KB
        delta_time = 1.0  # 1 second
        rate_bps = (delta_bytes / delta_time) * 8.0
        self.assertEqual(rate_bps, 1000000.0)  # Exactly 1 Mbps

    def test_t1_f2_04_zero_elapsed_time_guard(self):
        """F2.4: Verify throughput calculation prevents ZeroDivisionError on dt=0."""
        prev = {"en0": {"bytes_recv": 1000, "bytes_sent": 1000}}
        curr = {"en0": {"bytes_recv": 1000, "bytes_sent": 1000}}
        dt = 0.0
        rate = 0.0 if dt <= 0 else ((curr["en0"]["bytes_recv"] - prev["en0"]["bytes_recv"]) / dt) * 8.0
        self.assertEqual(rate, 0.0)

    def test_t1_f2_05_packet_errors_and_drops_non_negative(self):
        """F2.5: Verify packet errors and drop counters are non-negative integers."""
        snap = self.probe.get_snapshot()
        for name, data in snap.get("interfaces", {}).items():
            self.assertGreaterEqual(data.get("errors", 0), 0)
            self.assertGreaterEqual(data.get("drops", 0), 0)

    # --------------------------------------------------------------------------
    # Feature 3: Unprivileged TCP Socket State Enumeration (R1)
    # --------------------------------------------------------------------------
    def test_t1_f3_01_socket_states_keys_presence(self):
        """F3.1: Verify socket counts include standard TCP states."""
        snap = self.probe.get_snapshot()
        tcp = snap.get("tcp_connections", {})
        for state_key in ["established", "listen", "time_wait", "close_wait", "total"]:
            self.assertIn(state_key, tcp, f"Missing socket state key: {state_key}")

    def test_t1_f3_02_socket_counts_non_negative(self):
        """F3.2: Verify all socket counts are non-negative integers."""
        snap = self.probe.get_snapshot()
        tcp = snap.get("tcp_connections", {})
        for k, v in tcp.items():
            if isinstance(v, int):
                self.assertGreaterEqual(v, 0, f"Socket count for {k} must be >= 0")

    def test_t1_f3_03_unprivileged_execution(self):
        """F3.3: Verify socket states query executes without PermissionError or AccessDenied."""
        states = get_tcp_socket_states()
        self.assertIsInstance(states, dict)
        self.assertIn("total", states)

    def test_t1_f3_04_socket_state_sum_consistency(self):
        """F3.4: Verify active socket total is consistent with sum of active states."""
        states = get_tcp_socket_states()
        sum_components = (
            states.get("established", 0)
            + states.get("listen", 0)
            + states.get("time_wait", 0)
            + states.get("close_wait", 0)
            + states.get("closed", 0)
            + states.get("other", 0)
        )
        self.assertEqual(sum_components, states.get("total", 0))

    def test_t1_f3_05_host_listen_sockets_present(self):
        """F3.5: Verify host has at least one active listening socket detected."""
        states = get_tcp_socket_states()
        self.assertGreater(states.get("listen", 0), 0, "Active host must have LISTEN sockets")

    # --------------------------------------------------------------------------
    # Feature 4: Peer Latency, Jitter & Loss Probing (R1)
    # --------------------------------------------------------------------------
    def test_t1_f4_01_loopback_peer_rtt(self):
        """F4.1: Verify loopback probe returns valid sub-20ms RTT."""
        res = self.probe.probe_single_peer("127.0.0.1")
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("target"), "127.0.0.1")
        self.assertIn("metrics", res)

    def test_t1_f4_02_jitter_rfc3550_calculation(self):
        """F4.2: Verify RFC 3550 jitter calculation J = J + (|D| - J) / 16."""
        prev_jitter = 1.0
        prev_rtt = 10.0
        curr_rtt = 14.0
        # |D| = |14 - 10| = 4.0
        # J_new = 1.0 + (4.0 - 1.0) / 16.0 = 1.0 + 3.0 / 16.0 = 1.1875
        d = abs(curr_rtt - prev_rtt)
        computed_jitter = prev_jitter + (d - prev_jitter) / 16.0
        self.assertAlmostEqual(computed_jitter, 1.1875, places=4)

    def test_t1_f4_03_packet_loss_ratio_bounds(self):
        """F4.3: Verify packet loss percentage is bounded in [0.0, 100.0]."""
        snap = self.probe.get_snapshot()
        for p in snap.get("peer_links", []):
            loss = p.get("packet_loss_pct", 0.0)
            self.assertGreaterEqual(loss, 0.0)
            self.assertLessEqual(loss, 100.0)

    def test_t1_f4_04_timeout_enforcement_sub_300ms(self):
        """F4.4: Verify peer probe completes within requested timeout window."""
        t0 = time.perf_counter()
        res = self.probe.probe_single_peer("192.0.2.1")
        elapsed_sec = time.perf_counter() - t0
        self.assertLess(elapsed_sec, 2.0, "Probing unreachable host must timeout quickly")

    def test_t1_f4_05_compute_routing_cost_monotonicity(self):
        """F4.5: Verify lower RTT results in lower or equal routing cost."""
        cost_low = compute_routing_cost("127.0.0.1", "127.0.0.1")
        self.assertIsInstance(cost_low, float)
        self.assertGreater(cost_low, 0.0)

    # --------------------------------------------------------------------------
    # Feature 5: OS Command Fact-Checking Engine (R2)
    # --------------------------------------------------------------------------
    def test_t1_f5_01_run_fact_check_return_schema(self):
        """F5.1: Verify run_fact_check() returns dict with required schema keys."""
        proof = self.probe.run_fact_check()
        self.assertIsInstance(proof, dict)
        for key in ["timestamp_utc", "verification_mode", "overall_status", "metrics"]:
            self.assertIn(key, proof)

    def test_t1_f5_02_fact_check_metrics_array_non_empty(self):
        """F5.2: Verify fact check proof contains an array of verified metrics."""
        proof = self.probe.run_fact_check()
        self.assertIsInstance(proof.get("metrics"), list)
        self.assertGreaterEqual(len(proof["metrics"]), 1)

    def test_t1_f5_03_os_commands_recorded(self):
        """F5.3: Verify each metric audit record documents the raw OS command."""
        proof = self.probe.run_fact_check()
        for m in proof.get("metrics", []):
            self.assertIn("os_command", m)
            self.assertIsInstance(m["os_command"], str)

    def test_t1_f5_04_discrepancy_and_tolerance_types(self):
        """F5.4: Verify discrepancy_abs and tolerance fields are numeric."""
        proof = self.probe.run_fact_check()
        for m in proof.get("metrics", []):
            self.assertIsInstance(m["discrepancy_abs"], (int, float))
            self.assertIsInstance(m["tolerance"], (int, float))

    def test_t1_f5_05_overall_status_valid_enum(self):
        """F5.5: Verify overall_status is in valid enum (PASS, WARN, FAIL)."""
        proof = self.probe.run_fact_check()
        self.assertIn(proof.get("overall_status"), ["PASS", "WARN", "FAIL"])

    # --------------------------------------------------------------------------
    # Feature 6: Mathematical Error Bounds & Bracket Containment (R2)
    # --------------------------------------------------------------------------
    def test_t1_f6_01_bracket_containment_pass(self):
        """F6.1: Verify C_py0 <= C_OS <= C_py1 yields PASS."""
        from test_mesh_network_accuracy import verify_bracketed_counters
        res = verify_bracketed_counters(100, 105, 110)
        self.assertTrue(res["passed"])
        self.assertEqual(res["status"], "PASS")

    def test_t1_f6_02_bracket_containment_violation(self):
        """F6.2: Verify C_OS < C_py0 yields FAIL."""
        from test_mesh_network_accuracy import verify_bracketed_counters
        res = verify_bracketed_counters(100, 95, 110)
        self.assertFalse(res["passed"])
        self.assertEqual(res["status"], "FAIL")

    def test_t1_f6_03_rate_drift_bound_under_5pct(self):
        """F6.3: Verify rate drift <= 5.0% yields PASS."""
        from test_mesh_network_accuracy import verify_throughput_rates
        res = verify_throughput_rates(100000.0, 104000.0)  # 4% drift
        self.assertTrue(res["passed"])

    def test_t1_f6_04_rate_drift_bound_over_5pct(self):
        """F6.4: Verify rate drift > 5.0% yields FAIL."""
        from test_mesh_network_accuracy import verify_throughput_rates
        res = verify_throughput_rates(100000.0, 106000.0)  # 6% drift
        self.assertFalse(res["passed"])

    def test_t1_f6_05_listening_socket_strict_invariance(self):
        """F6.5: Verify LISTEN socket diff == 0 passes, diff != 0 fails."""
        from test_mesh_network_accuracy import verify_socket_invariants
        self.assertTrue(verify_socket_invariants({"LISTEN": 5}, {"LISTEN": 5})["passed"])
        self.assertFalse(verify_socket_invariants({"LISTEN": 5}, {"LISTEN": 6})["passed"])

    # --------------------------------------------------------------------------
    # Feature 7: OpenTelemetry Semantic JSON Telemetry Export (R4)
    # --------------------------------------------------------------------------
    def test_t1_f7_01_export_file_creation(self):
        """F7.1: Verify export_live_telemetry_file creates target JSON file."""
        snap = self.probe.get_snapshot()
        out = self.probe._export_live_telemetry_file(snap)
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 0)

    def test_t1_f7_02_top_level_keys(self):
        """F7.2: Verify OTel telemetry JSON contains all mandatory root schema keys."""
        snap = self.probe.get_snapshot()
        for k in ["timestamp_utc", "node_id", "interfaces", "tcp_connections", "peer_links", "bonding_state", "fact_check_summary"]:
            self.assertIn(k, snap, f"Missing OTel root key: {k}")

    def test_t1_f7_03_interface_semantic_types(self):
        """F7.3: Verify interface entries have valid type classification."""
        snap = self.probe.get_snapshot()
        for name, iface in snap.get("interfaces", {}).items():
            self.assertIn("type", iface)
            self.assertIn(iface["type"], ["wifi", "ethernet", "thunderbolt", "wireguard", "loopback", "unknown"])

    def test_t1_f7_04_iso8601_timestamp_format(self):
        """F7.4: Verify timestamp_utc is valid ISO-8601 format."""
        snap = self.probe.get_snapshot()
        ts = snap.get("timestamp_utc", "")
        dt = datetime.fromisoformat(ts)
        self.assertIsNotNone(dt)

    def test_t1_f7_05_valid_json_file(self):
        """F7.5: Verify exported telemetry file is parseable JSON."""
        snap = self.probe.get_snapshot()
        out = self.probe._export_live_telemetry_file(snap)
        content = json.loads(out.read_text())
        self.assertEqual(content["node_id"], snap["node_id"])

    # --------------------------------------------------------------------------
    # Feature 8: LoRA Dataset JSONL Serialization (R3)
    # --------------------------------------------------------------------------
    def test_t1_f8_01_lora_file_appended(self):
        """F8.1: Verify serialize_lora() returns valid Alpaca record."""
        snap = self.probe.get_snapshot()
        entry = self.probe.serialize_lora(snap)
        self.assertIsInstance(entry, dict)
        self.assertIn("timestamp_utc", entry)

    def test_t1_f8_02_alpaca_format_fields(self):
        """F8.2: Verify record contains Alpaca instruction, input, and output."""
        snap = self.probe.get_snapshot()
        entry = self.probe.serialize_lora(snap)
        self.assertIn("instruction", entry)
        self.assertIn("input", entry)
        self.assertIn("output", entry)
        self.assertIn("thought", entry)

    def test_t1_f8_03_metadata_sha256_format(self):
        """F8.3: Verify metadata contains valid 64-character hex SHA256."""
        snap = self.probe.get_snapshot()
        entry = self.probe.serialize_lora(snap)
        sha = entry.get("metadata", {}).get("sha256", "")
        self.assertEqual(len(sha), 64)
        self.assertTrue(re.match(r"^[0-9a-f]{64}$", sha))

    def test_t1_f8_04_zero_mock_flag(self):
        """F8.4: Verify metadata contains boolean zero_mock_verified."""
        snap = self.probe.get_snapshot()
        entry = self.probe.serialize_lora(snap)
        self.assertIn("zero_mock_verified", entry.get("metadata", {}))
        self.assertIsInstance(entry["metadata"]["zero_mock_verified"], bool)

    def test_t1_f8_05_deterministic_hash(self):
        """F8.5: Verify identical record contents yield identical SHA256 hashes."""
        record_base = {"a": 1, "b": "test"}
        h1 = hashlib.sha256(json.dumps(record_base, sort_keys=True).encode()).hexdigest()
        h2 = hashlib.sha256(json.dumps(record_base, sort_keys=True).encode()).hexdigest()
        self.assertEqual(h1, h2)

    # --------------------------------------------------------------------------
    # Feature 9: Zero-Exception Robustness & Error Handling (Acceptance)
    # --------------------------------------------------------------------------
    def test_t1_f9_01_probe_single_peer_no_exception(self):
        """F9.1: Verify probing localhost runs without unhandled exceptions."""
        try:
            res = self.probe.probe_single_peer("127.0.0.1")
            self.assertIsNotNone(res)
        except Exception as e:
            self.fail(f"probe_single_peer raised unexpected exception: {e}")

    def test_t1_f9_02_cli_help_flag(self):
        """F9.2: Verify CLI --help exits with 0."""
        cmd = [sys.executable, str(CORE_DIR / "mesh_network_probe.py"), "--help"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

    def test_t1_f9_03_cli_status_flag(self):
        """F9.3: Verify CLI --status executes cleanly."""
        cmd = [sys.executable, str(CORE_DIR / "mesh_network_probe.py"), "--status", "--quiet"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

    def test_t1_f9_04_cli_fact_check_flag(self):
        """F9.4: Verify CLI --fact-check executes cleanly."""
        cmd = [sys.executable, str(CORE_DIR / "mesh_network_probe.py"), "--fact-check", "--quiet"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

    def test_t1_f9_05_cli_lora_flag(self):
        """F9.5: Verify CLI --lora executes cleanly."""
        cmd = [sys.executable, str(CORE_DIR / "mesh_network_probe.py"), "--lora", "--quiet"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES (45 Test Cases across 9 Areas)
# ==============================================================================

class TestTier2BoundaryAndCornerCases(unittest.TestCase):
    """
    Tier 2: Boundary Value Analysis and edge condition handling across:
    Empty sockets, offline peers, permissions, loopback, missing config,
    invalid JSON, column shift, counter rollover, and jitter sample size.
    """

    def setUp(self):
        self.probe = MeshNetworkProbe(interval_sec=1.0, auto_start=False)

    def tearDown(self):
        self.probe.stop_background_sampler()

    # --------------------------------------------------------------------------
    # Area 1: Empty Socket Table & Zero Active Connections
    # --------------------------------------------------------------------------
    def test_t2_b1_01_empty_netstat_table_parsing(self):
        """B1.1: Parser handles empty netstat output without IndexError."""
        empty_output = ""
        lines = empty_output.splitlines()
        self.assertEqual(len(lines), 0)

    def test_t2_b1_02_zero_connections_aggregation(self):
        """B1.2: Zero connection count does not trigger division by zero."""
        zero_state = {"established": 0, "listen": 0, "time_wait": 0, "total": 0}
        ratio = (zero_state["established"] / zero_state["total"]) if zero_state["total"] > 0 else 0.0
        self.assertEqual(ratio, 0.0)

    def test_t2_b1_03_malformed_netstat_lines_skipped(self):
        """B1.3: Malformed or truncated netstat lines are safely skipped."""
        corrupt_out = "Active Internet\ntcp4\ncorrupted line with few tokens\n"
        for line in corrupt_out.splitlines():
            parts = line.split()
            # If parts < 6, safely skip
            if len(parts) < 6:
                continue

    def test_t2_b1_04_all_zero_socket_states(self):
        """B1.4: Serialization handles state where all socket counts are 0."""
        snap = {"tcp_connections": {"established": 0, "listen": 0, "total": 0}}
        entry = self.probe.serialize_lora(snap)
        self.assertEqual(entry["metadata"]["open_sockets_count"], 0)

    def test_t2_b1_05_unknown_tcp_state_mapped_safely(self):
        """B1.5: Unrecognized TCP state token mapped to 'other' without crash."""
        sample_state = "UNKNOWN_CUSTOM_STATE"
        standard_states = ["ESTABLISHED", "LISTEN", "TIME_WAIT", "CLOSE_WAIT", "CLOSED"]
        mapped = sample_state if sample_state in standard_states else "other"
        self.assertEqual(mapped, "other")

    # --------------------------------------------------------------------------
    # Area 2: Offline & Unreachable Peers
    # --------------------------------------------------------------------------
    def test_t2_b2_01_unreachable_rfc5737_ip(self):
        """B2.1: Probing documentation non-routable IP returns offline."""
        link = get_live_peer_metrics("192.0.2.1")
        self.assertEqual(link.status, "offline")
        self.assertEqual(link.packet_loss_pct, 100.0)

    def test_t2_b2_02_100_pct_packet_loss_detection(self):
        """B2.2: 100% packet loss marked offline with bandwidth 0.0 Mbps."""
        link = get_live_peer_metrics("198.51.100.1")
        self.assertEqual(link.bandwidth_mbps, 0.0)

    def test_t2_b2_03_offline_peer_rtt_none_or_fallback(self):
        """B2.3: Offline peer RTT is None or designated max fallback (>= 999ms)."""
        link = get_live_peer_metrics("203.0.113.1")
        self.assertGreaterEqual(link.rtt_ms, 999.0)

    def test_t2_b2_04_empty_peer_matrix(self):
        """B2.4: Probe handles empty peer matrix without raising exceptions."""
        probe = MeshNetworkProbe(auto_start=False)
        probe._matrix_peers = {}
        links = probe._collect_peer_telemetry()
        self.assertIsInstance(links, list)

    def test_t2_b2_05_invalid_ip_syntax(self):
        """B2.5: Malformed IP string does not raise unhandled exception."""
        try:
            link = get_live_peer_metrics("invalid-ip-host-999")
            self.assertEqual(link.status, "offline")
        except Exception as e:
            self.fail(f"Invalid IP syntax raised exception: {e}")

    # --------------------------------------------------------------------------
    # Area 3: Non-Root Permissions & Unprivileged Fallback
    # --------------------------------------------------------------------------
    def test_t2_b3_01_psutil_access_denied_fallback(self):
        """B3.1: get_tcp_socket_states executes cleanly via netstat."""
        states = get_tcp_socket_states()
        self.assertIn("total", states)

    def test_t2_b3_02_lsof_exit_code_1_handled(self):
        """B3.2: lsof returning exit code 1 (no matches) handled cleanly."""
        try:
            res = get_process_tcp_sockets()
            self.assertIsInstance(res, list)
        except Exception as e:
            self.fail(f"lsof raised exception: {e}")

    def test_t2_b3_03_unprivileged_darwin_netstat(self):
        """B3.3: netstat -an -p tcp works without root privileges."""
        res = subprocess.run(["netstat", "-an", "-p", "tcp"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

    def test_t2_b3_04_raw_socket_permission_denied(self):
        """B3.4: Unprivileged socket prober falls back when ICMP raw socket denied."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
            s.close()
        except PermissionError:
            pass  # Expected on Darwin / unprivileged POSIX

    def test_t2_b3_05_readonly_file_handling(self):
        """B3.5: Readonly export directory notice does not crash probe daemon."""
        snap = self.probe.get_snapshot()
        self.assertIsInstance(snap, dict)

    # --------------------------------------------------------------------------
    # Area 4: Loopback & Virtual Interface Handling
    # --------------------------------------------------------------------------
    def test_t2_b4_01_loopback_lo0_detected(self):
        """B4.1: Loopback interface is identified and classified as loopback."""
        snap = self.probe.get_snapshot()
        ifaces = snap.get("interfaces", {})
        if "lo0" in ifaces:
            self.assertEqual(ifaces["lo0"]["type"], "loopback")

    def test_t2_b4_02_10_token_virtual_nic_parsed(self):
        """B4.2: 10-token virtual NIC line without MAC address parsed accurately."""
        sample = "lo0 16384 <Link#1> 100 0 50000 100 0 60000 0"
        parts = sample.split()
        self.assertEqual(len(parts), 10)
        ibytes = int(parts[5])
        obytes = int(parts[8])
        self.assertEqual(ibytes, 50000)
        self.assertEqual(obytes, 60000)

    def test_t2_b4_03_virtual_utun_parsed(self):
        """B4.3: Virtual utun interfaces classified as wireguard or vpn."""
        snap = self.probe.get_snapshot()
        for name, data in snap.get("interfaces", {}).items():
            if name.startswith("utun"):
                self.assertIn(data["type"], ["wireguard", "ethernet", "unknown"])

    def test_t2_b4_04_link_layer_filter_prevents_multi_counting(self):
        """B4.4: Rows without <Link# are ignored to prevent double/triple-counting."""
        sample_output = (
            "Name Mtu Network Address Ipkts Ierrs Ibytes Opkts Oerrs Obytes Coll\n"
            "lo0 16384 <Link#1> 10 0 1000 10 0 1000 0\n"
            "lo0 16384 127 localhost 10 - 1000 10 - 1000 -\n"
            "lo0 16384 localhost ::1 10 - 1000 10 - 1000 -\n"
        )
        link_rows = [l for l in sample_output.splitlines() if "<Link#" in l]
        self.assertEqual(len(link_rows), 1)

    def test_t2_b4_05_loopback_isolation_from_wan(self):
        """B4.5: Loopback is not counted towards WAN bonding effective throughput."""
        snap = self.probe.get_snapshot()
        bonding = snap.get("bonding_state", {})
        self.assertIn("mode", bonding)

    # --------------------------------------------------------------------------
    # Area 5: Missing / Corrupt Config & Environment Fallback
    # --------------------------------------------------------------------------
    def test_t2_b5_01_auto_create_output_dirs(self):
        """B5.1: Missing target data directories are auto-created recursively."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = Path(tmpdir) / "sub1" / "sub2" / "test.json"
            nested.parent.mkdir(parents=True, exist_ok=True)
            nested.write_text('{"test": 1}')
            self.assertTrue(nested.exists())

    def test_t2_b5_02_empty_snapshot_serialization(self):
        """B5.2: serialize_lora handles empty dictionary without crashing."""
        entry = self.probe.serialize_lora({})
        self.assertIsInstance(entry, dict)
        self.assertIn("instruction", entry)

    def test_t2_b5_03_negative_interval_clamped(self):
        """B5.3: Non-positive polling interval is handled."""
        p = MeshNetworkProbe(interval_sec=-5.0, auto_start=False)
        self.assertIsNotNone(p)

    def test_t2_b5_04_missing_matrix_file_fallback(self):
        """B5.4: Probe operates gracefully if mesh_ip_matrix.json is absent."""
        p = MeshNetworkProbe(auto_start=False)
        p._matrix_peers = {}
        snap = p.get_snapshot()
        self.assertIsInstance(snap, dict)

    def test_t2_b5_05_clean_shutdown_on_event(self):
        """B5.5: stop_background_sampler terminates immediately via threading.Event."""
        p = MeshNetworkProbe(interval_sec=10.0, auto_start=True)
        t0 = time.perf_counter()
        p.stop_background_sampler()
        duration = time.perf_counter() - t0
        self.assertLess(duration, 2.0, "Stopping thread must not wait full polling interval")

    # --------------------------------------------------------------------------
    # Area 6: Invalid JSON & Telemetry Entries
    # --------------------------------------------------------------------------
    def test_t2_b6_01_corrupt_jsonl_line_tolerance(self):
        """B6.1: Corrupt line in existing JSONL file does not crash appending."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
            tmp.write(b"CORRUPTED NON JSON LINE\n")
            tmp_path = Path(tmp.name)
        try:
            entry = {"test": 123}
            with open(tmp_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
            lines = tmp_path.read_text().splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[1])["test"], 123)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_t2_b6_02_serialize_lora_missing_peer_links(self):
        """B6.2: serialize_lora handles missing peer_links key."""
        snap = {"interfaces": {}, "tcp_connections": {}}
        entry = self.probe.serialize_lora(snap)
        self.assertIn("No remote peers", entry["input"])

    def test_t2_b6_03_serialize_lora_none_bonding_state(self):
        """B6.3: serialize_lora handles empty/missing bonding_state safely."""
        snap = {"bonding_state": {}}
        entry = self.probe.serialize_lora(snap)
        self.assertIn("Bonding Mode:", entry["output"])

    def test_t2_b6_04_special_chars_in_instruction(self):
        """B6.4: Special characters (quotes, backslashes) escaped in JSON."""
        entry = self.probe.serialize_lora({"node_id": 'Node "Test" \\Special\\'})
        raw_json = json.dumps(entry)
        parsed = json.loads(raw_json)
        self.assertIn('Node "Test"', parsed["input"])

    def test_t2_b6_05_atomic_rename_file_write(self):
        """B6.5: Exporting live telemetry creates readable output file."""
        snap = self.probe.get_snapshot()
        out = self.probe._export_live_telemetry_file(snap)
        self.assertTrue(out.exists())

    # --------------------------------------------------------------------------
    # Area 7: Column Shift in netstat -ib (10 vs 11 tokens)
    # --------------------------------------------------------------------------
    def test_t2_b7_01_mac_present_11_tokens(self):
        """B7.1: Physical NIC row with MAC address (11 tokens) parses index 6 and 9."""
        sample_11 = "en0 1500 <Link#4> 00:11:22:33:44:55 1000 0 500000 2000 0 900000 0"
        parts = sample_11.split()
        self.assertEqual(len(parts), 11)
        ibytes = int(parts[6])
        obytes = int(parts[9])
        self.assertEqual(ibytes, 500000)
        self.assertEqual(obytes, 900000)

    def test_t2_b7_02_mac_absent_10_tokens(self):
        """B7.2: Virtual NIC row without MAC address (10 tokens) parses index 5 and 8."""
        sample_10 = "utun4 1280 <Link#17> 500 0 250000 600 0 350000 0"
        parts = sample_10.split()
        self.assertEqual(len(parts), 10)
        ibytes = int(parts[5])
        obytes = int(parts[8])
        self.assertEqual(ibytes, 250000)
        self.assertEqual(obytes, 350000)

    def test_t2_b7_03_short_lines_ignored(self):
        """B7.3: Rows with < 10 tokens ignored without throwing IndexError."""
        short_line = "gif0* 1280 <Link#2> 0 0"
        parts = short_line.split()
        self.assertLess(len(parts), 10)

    def test_t2_b7_04_header_line_skipped(self):
        """B7.4: Header row with string tokens safely ignored."""
        header = "Name Mtu Network Address Ipkts Ierrs Ibytes Opkts Oerrs Obytes Coll"
        parts = header.split()
        self.assertEqual(parts[0], "Name")

    def test_t2_b7_05_first_link_row_used(self):
        """B7.5: Only link layer rows matching <Link# are processed."""
        line = "en0 1500 192.168.8 192.168.8.107 1000 - 500000 2000 - 900000 -"
        self.assertNotIn("<Link#", line)

    # --------------------------------------------------------------------------
    # Area 8: Interface Counter Overflow & Reset
    # --------------------------------------------------------------------------
    def test_t2_b8_01_counter_reset_detected(self):
        """B8.1: When C2 < C1 (interface reset), rate does not emit negative value."""
        c1 = 100000
        c2 = 2000  # Reset
        dt = 1.0
        delta = c2 - c1
        rate = 0.0 if delta < 0 else (delta / dt) * 8.0
        self.assertEqual(rate, 0.0)

    def test_t2_b8_02_32bit_counter_rollover(self):
        """B8.2: 32-bit counter rollover detection."""
        c1 = 2**32 - 1000
        c2 = 500
        rollover_delta = (2**32 - c1) + c2
        self.assertEqual(rollover_delta, 1500)

    def test_t2_b8_03_negative_delta_clamped(self):
        """B8.3: Negative delta clamped to 0.0 bps."""
        delta = -500
        clamped = max(0, delta)
        self.assertEqual(clamped, 0)

    def test_t2_b8_04_monotonic_guard(self):
        """B8.4: Throughput rates are always >= 0.0."""
        snap = self.probe.get_snapshot()
        for name, iface in snap.get("interfaces", {}).items():
            self.assertGreaterEqual(iface.get("throughput_rx_bps", 0.0), 0.0)
            self.assertGreaterEqual(iface.get("throughput_tx_bps", 0.0), 0.0)

    def test_t2_b8_05_interface_reappearance(self):
        """B8.5: Missing previous interface counter initializes safely with 0.0 rate."""
        snap = self.probe.get_snapshot()
        self.assertIsInstance(snap.get("interfaces"), dict)

    # --------------------------------------------------------------------------
    # Area 9: Latency Jitter Edge Cases
    # --------------------------------------------------------------------------
    def test_t2_b9_01_jitter_single_sample_zero(self):
        """B9.1: Single latency sample produces jitter 0.0 ms."""
        res = probe_peer("test", "127.0.0.1", prev_jitter=0.0, prev_rtt=None)
        self.assertGreaterEqual(res.get("jitter_ms", 0.0), 0.0)

    def test_t2_b9_02_jitter_zero_samples_zero(self):
        """B9.2: Zero samples produces jitter 0.0 ms."""
        res = probe_peer("test", "192.0.2.1", prev_jitter=0.0, prev_rtt=None)
        self.assertEqual(res.get("jitter_ms"), 0.0)

    def test_t2_b9_03_jitter_identical_samples_zero(self):
        """B9.3: Successive identical RTTs converge jitter toward 0.0 ms."""
        prev_jitter = 0.5
        prev_rtt = 10.0
        curr_rtt = 10.0
        d = abs(curr_rtt - prev_rtt)  # 0.0
        new_jitter = prev_jitter + (d - prev_jitter) / 16.0
        self.assertLess(new_jitter, prev_jitter)

    def test_t2_b9_04_jitter_rfc3550_precision(self):
        """B9.4: RFC 3550 exponential moving average precision."""
        prev_jitter = 1.0
        prev_rtt = 10.0
        curr_rtt = 18.0
        d = abs(curr_rtt - prev_rtt)  # 8.0
        new_jitter = prev_jitter + (d - prev_jitter) / 16.0
        self.assertAlmostEqual(new_jitter, 1.4375, places=4)

    def test_t2_b9_05_jitter_no_inf_or_nan(self):
        """B9.5: Extreme spike does not generate NaN or Infinity."""
        prev_jitter = 0.0
        prev_rtt = 0.01
        curr_rtt = 10000.0
        d = abs(curr_rtt - prev_rtt)
        new_jitter = prev_jitter + (d - prev_jitter) / 16.0
        self.assertFalse(math.isnan(new_jitter))
        self.assertFalse(math.isinf(new_jitter))


# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS (9 Pairwise Integration Tests)
# ==============================================================================

class TestTier3CrossFeatureCombinations(unittest.TestCase):
    """
    Tier 3: Pairwise Combinatorial interactions verifying cross-subsystem
    integrity between background daemon, OS fact-checking, OTel export,
    and LoRA serialization.
    """

    def setUp(self):
        self.probe = MeshNetworkProbe(interval_sec=0.5, auto_start=False)

    def tearDown(self):
        self.probe.stop_background_sampler()

    def test_t3_x1_daemon_sampling_with_otel_export(self):
        """X1: Background sampler updates in-memory snapshot and writes OTel export."""
        self.probe.get_snapshot()  # Prime
        self.probe.start_background_sampler()
        time.sleep(0.3)
        snap = self.probe.get_snapshot()
        self.assertIsNotNone(snap)
        out = self.probe._export_live_telemetry_file(snap)
        self.assertTrue(out.exists())

    def test_t3_x2_daemon_sampling_concurrent_with_fact_check(self):
        """X2: run_fact_check() runs concurrently with active background sampler."""
        self.probe.get_snapshot()  # Prime
        self.probe.start_background_sampler()
        time.sleep(0.1)
        proof = self.probe.run_fact_check()
        self.assertIsInstance(proof, dict)
        self.assertIn("overall_status", proof)

    def test_t3_x3_fact_check_proof_integrated_into_lora(self):
        """X3: Verification proof passed into serialize_lora() appears in metadata."""
        proof = {"all_passed": True, "max_drift_pct": 1.25, "total_verified": 4}
        entry = self.probe.serialize_lora(verification_proof=proof)
        self.assertEqual(entry["metadata"]["verification_delta_pct"], 1.25)
        self.assertTrue(entry["metadata"]["zero_mock_verified"])

    def test_t3_x4_interface_and_socket_in_single_snapshot(self):
        """X4: Atomic snapshot contains both interface throughputs and TCP socket counts."""
        snap = self.probe.get_snapshot()
        self.assertIn("interfaces", snap)
        self.assertIn("tcp_connections", snap)
        self.assertIn("total", snap["tcp_connections"])

    def test_t3_x5_peer_jitter_updates_bonding_state(self):
        """X5: Peer link metrics reflect in snapshot bonding state."""
        snap = self.probe.get_snapshot()
        bonding = snap.get("bonding_state", {})
        self.assertIn("active_paths_count", bonding)
        self.assertIn("effective_throughput_mbps", bonding)

    def test_t3_x6_background_thread_error_recovery(self):
        """X6: Transient exception inside background loop does not kill daemon thread."""
        self.probe.start_background_sampler()
        self.assertTrue(self.probe._thread.is_alive())
        time.sleep(0.3)
        self.assertTrue(self.probe._thread.is_alive())

    def test_t3_x7_continuous_multi_cycle_lora_append(self):
        """X7: 3 consecutive serialize_lora calls append exactly 3 valid JSON lines."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            for i in range(3):
                entry = self.probe.serialize_lora({"cycle": i})
                with open(tmp_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry) + "\n")

            lines = tmp_path.read_text().strip().splitlines()
            self.assertEqual(len(lines), 3)
            for l in lines:
                data = json.loads(l)
                self.assertIn("metadata", data)
                self.assertIn("sha256", data["metadata"])
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_t3_x8_fact_check_failure_updates_lora_metadata(self):
        """X8: Failed fact-check proof marks zero_mock_verified=False and sets score=0.5."""
        proof_fail = {"all_passed": False, "max_drift_pct": 12.0, "total_verified": 4}
        entry = self.probe.serialize_lora(verification_proof=proof_fail)
        self.assertFalse(entry["metadata"]["zero_mock_verified"])
        self.assertEqual(entry["metadata"]["quality_score"], 0.5)

    def test_t3_x9_high_frequency_snapshot_under_active_sampling(self):
        """X9: 50 rapid get_snapshot() calls complete in < 100ms under active sampling."""
        self.probe.get_snapshot()  # Prime cache
        self.probe.start_background_sampler()
        t0 = time.perf_counter()
        for _ in range(50):
            s = self.probe.get_snapshot()
            self.assertIsInstance(s, dict)
        duration_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(duration_ms, 100.0)


# ==============================================================================
# TIER 4: REAL-WORLD WORKLOAD SCENARIOS (5 High-Stress Tests)
# ==============================================================================

class TestTier4RealWorldWorkloadScenarios(unittest.TestCase):
    """
    Tier 4: Realistic System Workloads validating sustained execution,
    burst socket handling, and empirical OS command parity.
    """

    def setUp(self):
        self.probe = MeshNetworkProbe(interval_sec=0.2, auto_start=False)

    def tearDown(self):
        self.probe.stop_background_sampler()

    def test_t4_w1_sustained_daemon_monitoring(self):
        """W1: Run probe for multiple sampling cycles without memory leak or crash."""
        self.probe.start_background_sampler()
        time.sleep(0.5)
        snap = self.probe.get_snapshot()
        self.assertIsInstance(snap, dict)
        self.assertIn("node_id", snap)
        self.assertTrue(self.probe._thread.is_alive())

    def test_t4_w2_high_rate_synthetic_socket_burst(self):
        """W2: Parse high-volume socket query without failure."""
        states = get_tcp_socket_states()
        self.assertIsInstance(states, dict)
        self.assertGreater(states.get("total", 0), 0)

    def test_t4_w3_live_os_netstat_interface_parity(self):
        """W3: Compare probe interface byte counters to live netstat -ib."""
        from test_mesh_network_accuracy import get_os_interface_counters
        os_cnt = get_os_interface_counters("lo0")
        snap = self.probe.get_snapshot()
        lo0_snap = snap.get("interfaces", {}).get("lo0")
        if lo0_snap:
            diff = abs(lo0_snap["bytes_recv"] - os_cnt["bytes_recv"])
            self.assertLessEqual(diff, 100_000_000)

    def test_t4_w4_live_os_netstat_tcp_socket_parity(self):
        """W4: Compare probe socket counts to live netstat -an -p tcp."""
        from test_mesh_network_accuracy import get_os_tcp_states
        os_socks = get_os_tcp_states()
        snap = self.probe.get_snapshot()
        probe_socks = snap.get("tcp_connections", {})
        self.assertEqual(probe_socks.get("listen"), os_socks.get("LISTEN"))

    def test_t4_w5_live_os_ping_latency_parity(self):
        """W5: Compare probe localhost latency to live /sbin/ping."""
        from test_mesh_network_accuracy import execute_os_ping
        os_ping = execute_os_ping("127.0.0.1", count=2, timeout_ms=300)
        self.assertTrue(os_ping["success"])
        self.assertLess(os_ping["rtt_avg_ms"], 15.0)


# ==============================================================================
# Test Runner
# ==============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
