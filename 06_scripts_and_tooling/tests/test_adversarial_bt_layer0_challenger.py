#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
06_scripts_and_tooling/tests/test_adversarial_bt_layer0_challenger.py
=====================================================================
Empirical Adversarial Challenge Suite: True IP-Less Bluetooth Layer 0
Challenger: teamwork_preview_challenger_1
Governing Rules:
- Rule #0: Canonical Hardware Matrix
- Rule #1: Zero-Mock & Truth Verification Rule
- Rule #3: Host Sanctuary & Dynamic RAM Governance
- Rule #9: Bluetooth & Bleak Execution Constraint
- Rule #10: Omnipresent Bluetooth Full-Mesh Graph Layer 0

Adversarial Objectives:
1. Simulate total IP network outage: Block all IPv4/IPv6 socket creation,
   DNS lookups, and IP connections, proving bridge operates 100% IP-less.
2. Attack MAC address validation with command injection, SQL/shell syntax,
   IPv4/IPv6 addresses, hostnames, null bytes, and out-of-spec lengths.
3. Subprocess failure and corrupted output fuzzing: Test engine behavior under
   segfaults, non-zero exits, malformed JSON, timeouts, and extreme RSSI values.
4. Live baseband inquiry verification: Compare live bridge output against raw
   unmediated blueutil / IOBluetooth baseband state.
5. High-concurrency race condition attack on atomic cache file.
6. Zero-mock static and runtime forensic audit across all modified components.
"""

from __future__ import annotations

import os
import re
import sys
import time
import json
import socket
import select
import tempfile
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "06_scripts_and_tooling"
SCREEN_LENS_SRC = REPO_ROOT / "01_apps/screen_lens/src"

for p in [str(SCRIPTS_DIR), str(SCREEN_LENS_SRC), str(REPO_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import bluetooth_ip_less_telemetry_bridge as bridge_mod
from bluetooth_ip_less_telemetry_bridge import (
    BluetoothTelemetryBridge,
    is_valid_bluetooth_mac,
    normalize_mac,
    probe_bluetooth_node,
    format_terminal_ping_line,
    write_atomic_telemetry_cache,
    CANONICAL_NODES,
    BLUEUTIL_BIN,
)


class TestAdversarialIPOutageIsolation:
    """
    Simulates complete IP stack / network interface collapse.
    Blocks all IP socket creation and network system calls.
    """

    def test_complete_ip_socket_blockade_during_probe(self, monkeypatch):
        """
        Adversarial Test: Intercept socket.socket, socket.create_connection,
        and socket.getaddrinfo. Any attempt to use IPv4 or IPv6 raises PermissionError.
        The bridge probe MUST complete without triggering any IP socket operations.
        """
        original_socket = socket.socket

        def hostile_socket(family=socket.AF_INET, *args, **kwargs):
            if family in (socket.AF_INET, socket.AF_INET6):
                raise PermissionError("ADVERSARIAL ATTACK: Total IP stack collapse! IPv4/IPv6 prohibited.")
            return original_socket(family, *args, **kwargs)

        def hostile_create_connection(*args, **kwargs):
            raise PermissionError("ADVERSARIAL ATTACK: Network unreachable! IP connection attempted.")

        def hostile_getaddrinfo(*args, **kwargs):
            raise PermissionError("ADVERSARIAL ATTACK: DNS / hostname resolution prohibited.")

        monkeypatch.setattr(socket, "socket", hostile_socket)
        monkeypatch.setattr(socket, "create_connection", hostile_create_connection)
        monkeypatch.setattr(socket, "getaddrinfo", hostile_getaddrinfo)

        # Confirm IP calls are blocked
        with pytest.raises(PermissionError):
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        with pytest.raises(PermissionError):
            socket.create_connection(("127.0.0.1", 80), timeout=0.1)

        # Now execute probe_bluetooth_node for L3 Linux Head Node
        result = probe_bluetooth_node("00:41:0E:14:28:44")
        assert isinstance(result, dict)
        assert result["mac"] == "00:41:0E:14:28:44"
        assert "connected" in result

        # Test entire bridge run_once under total IP blockade
        bridge = BluetoothTelemetryBridge()
        telemetry = bridge.run_once()
        assert "nodes" in telemetry
        assert "controller" in telemetry
        assert telemetry["controller"]["powered"] is True
        assert telemetry["nodes"]["l3_linux"]["connected"] is True
        assert telemetry["nodes"]["l3_linux"]["mac"] == "00:41:0E:14:28:44"

    def test_bridge_executes_no_ip_based_subprocesses(self, monkeypatch):
        """
        Adversarial Test: Monitor all subprocess.run calls.
        Verify that neither 'ping', 'ssh', 'curl', 'nc', 'telnet', 'ifconfig',
        nor 'tailscale' are ever invoked by the bridge.
        """
        original_run = subprocess.run
        invoked_commands = []

        banned_binaries = {"ping", "ssh", "curl", "nc", "telnet", "tailscale", "wget", "traceroute"}

        def auditing_run(cmd, *args, **kwargs):
            if isinstance(cmd, list):
                bin_name = Path(cmd[0]).name
            elif isinstance(cmd, str):
                bin_name = cmd.split()[0]
            else:
                bin_name = str(cmd)
            invoked_commands.append(bin_name)
            if bin_name in banned_binaries:
                raise AssertionError(f"ADVERSARIAL TRAP: Prohibited IP utility invoked: {bin_name}")
            return original_run(cmd, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", auditing_run)

        bridge = BluetoothTelemetryBridge()
        bridge.run_once()

        assert len(invoked_commands) > 0
        # All invoked commands must be strictly Bluetooth tooling (blueutil, l2ping)
        for cmd_bin in invoked_commands:
            assert cmd_bin in ("blueutil", "l2ping"), f"Prohibited subprocess command executed: {cmd_bin}"


class TestAdversarialMACValidationAndInjection:
    """
    Stress-tests MAC parsing and input sanitization with malicious payloads.
    """

    @pytest.mark.parametrize("malicious_mac", [
        "00:41:0E:14:28:44; rm -rf /",
        "00:41:0E:14:28:44 && whoami",
        "$(whoami)",
        "`whoami`",
        "00:41:0E:14:28:44 | cat /etc/passwd",
        "192.168.8.1",
        "192.168.8.225",
        "100.119.199.76",
        "10.0.0.8",
        "127.0.0.1",
        "::1",
        "fe80::1",
        "fe80::2c-ca-16-08-c0-27",
        "mac-mini-m4",
        "localhost",
        "http://127.0.0.1",
        "00:41:0E:14:28",          # 5 octets
        "00:41:0E:14:28:44:01",     # 7 octets
        "00:41:0E:14:28:GG",        # Non-hex characters
        "00:41:0E:14:28:44\x00",    # Null byte injection
        "00:41:0E:14:28:44\nONLINE",# CRLF injection
        "",                         # Empty string
        "   ",                      # Whitespace
        "../../etc/shadow",         # Path traversal
    ])
    def test_malicious_mac_rejected_by_validator(self, malicious_mac):
        """Verify that is_valid_bluetooth_mac returns False on all attack inputs."""
        assert is_valid_bluetooth_mac(malicious_mac) is False

    @pytest.mark.parametrize("malicious_mac", [
        "00:41:0E:14:28:44; echo pwned",
        "192.168.8.225",
        "00:41:0E:14:28:GG",
        "",
    ])
    def test_normalize_mac_raises_value_error(self, malicious_mac):
        """Verify that normalize_mac raises ValueError on all attack inputs."""
        with pytest.raises(ValueError):
            normalize_mac(malicious_mac)

    def test_probe_bluetooth_node_aborts_before_subprocess(self, monkeypatch):
        """
        Verify that probe_bluetooth_node raises ValueError immediately for an invalid MAC
        and NEVER executes any subprocess.
        """
        def should_not_run(*args, **kwargs):
            raise AssertionError("Subprocess was invoked with unsanitized input!")

        monkeypatch.setattr(subprocess, "run", should_not_run)

        with pytest.raises(ValueError):
            probe_bluetooth_node("192.168.8.225; whoami")

        with pytest.raises(ValueError):
            probe_bluetooth_node("bad-mac")


class TestAdversarialSubprocessFailureAndCorruptedOutput:
    """
    Simulates hardware/OS failures, corrupted responses, segfaults, and hangs.
    """

    def test_blueutil_segfault_or_error_handled_cleanly(self, monkeypatch):
        """
        If blueutil exits with returncode != 0 (e.g. segfault / error),
        the probe must return connected=False with null metrics (Rule 1).
        """
        def failing_run(*args, **kwargs):
            return subprocess.CompletedProcess(args=args[0], returncode=139, stdout="", stderr="Segmentation fault")

        monkeypatch.setattr(subprocess, "run", failing_run)

        res = probe_bluetooth_node("00:41:0E:14:28:44")
        assert res["connected"] is False
        assert res["rssi_dbm"] is None
        assert res["ping_rtt_ms"] is None
        assert res["link_type"] is None

    def test_blueutil_corrupted_json_handled_cleanly(self, monkeypatch):
        """
        If blueutil outputs malformed / corrupted JSON,
        the probe must safely fall back without throwing an unhandled exception.
        """
        def malformed_json_run(*args, **kwargs):
            return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="{broken json: true", stderr="")

        monkeypatch.setattr(subprocess, "run", malformed_json_run)

        res = probe_bluetooth_node("00:41:0E:14:28:44")
        assert res["connected"] is False
        assert res["rssi_dbm"] is None

    def test_blueutil_unexpected_schema_handled_cleanly(self, monkeypatch):
        """
        If blueutil outputs valid JSON with unexpected types (e.g. non-numeric RSSI),
        the probe must safely degrade without throwing an unhandled exception.
        """
        def weird_schema_run(*args, **kwargs):
            weird_payload = json.dumps({"connected": True, "RSSI": "unknown_corrupted"})
            return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=weird_payload, stderr="")

        monkeypatch.setattr(subprocess, "run", weird_schema_run)

        res = probe_bluetooth_node("00:41:0E:14:28:44")
        # Must not crash, and must safely return disconnected/null metrics
        assert res["connected"] is False
        assert res["rssi_dbm"] is None

    def test_timeout_budget_strictly_enforced(self, monkeypatch):
        """
        If blueutil hangs indefinitely, subprocess timeout must abort it.
        """
        def hanging_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout", 1.5))

        monkeypatch.setattr(subprocess, "run", hanging_run)

        t0 = time.perf_counter()
        res = probe_bluetooth_node("00:41:0E:14:28:44", timeout_s=0.2)
        elapsed = time.perf_counter() - t0
        assert elapsed < 1.0
        assert res["connected"] is False
        assert res["rssi_dbm"] is None


class TestAdversarialLiveBasebandGroundTruth:
    """
    Compares live bridge execution against the unvarnished physical baseband.
    """

    def test_live_bridge_matches_raw_blueutil_state(self):
        """
        Queries raw blueutil on the L1 host for L3 Linux Head Node and Samsung S20+.
        Verifies that bridge_mod.probe_bluetooth_node matches raw hardware reality.
        """
        # 1. Query raw hardware for L3
        res_raw = subprocess.run(
            [BLUEUTIL_BIN, "--info", "00-41-0e-14-28-44", "--format", "json"],
            capture_output=True, text=True, timeout=2.0
        )
        assert res_raw.returncode == 0, f"Failed to execute blueutil: {res_raw.stderr}"
        raw_data = json.loads(res_raw.stdout)
        raw_connected = bool(raw_data.get("connected", False))
        raw_rssi = raw_data.get("rawRSSI") or raw_data.get("RSSI")

        # 2. Query via bridge function
        bridge_res = probe_bluetooth_node("00:41:0E:14:28:44")

        # 3. Assert fidelity
        assert bridge_res["connected"] == raw_connected
        if raw_connected:
            assert bridge_res["rssi_dbm"] == int(raw_rssi)
            assert bridge_res["ping_rtt_ms"] is not None
            assert bridge_res["ping_rtt_ms"] > 0
        else:
            assert bridge_res["rssi_dbm"] is None
            assert bridge_res["ping_rtt_ms"] is None

    def test_disconnected_devices_emit_zero_mock_telemetry(self):
        """
        Verifies that physically disconnected devices (L7 Samsung S20+)
        faithfully report connected=False, rssi=null, rtt=null.
        """
        res_s20 = probe_bluetooth_node("5C:CB:99:05:81:41")
        assert res_s20["connected"] is False
        assert res_s20["rssi_dbm"] is None
        assert res_s20["ping_rtt_ms"] is None
        assert res_s20["link_type"] is None
        assert res_s20["metrics"] is None


class TestAdversarialHighConcurrencyCacheHammer:
    """
    Stress-tests the atomic file replacement cache under extreme concurrent read/write loads.
    """

    def test_high_concurrency_race_condition_hammer(self, tmp_path):
        """
        Spawns 1 writer writing 100 cache updates and 10 parallel reader threads
        reading continuously. Proves 0 json.JSONDecodeError or partial file reads.
        """
        cache_path = tmp_path / "lauburu_bt_telemetry.json"
        stop_event = threading.Event()
        read_errors = []
        read_count = [0]

        # Prime cache
        init_data = {
            "timestamp": time.time(),
            "controller": {"powered": True, "address": "1C:F6:4C:81:0B:28"},
            "nodes": {"l3_linux": {"mac": "00:41:0E:14:28:44", "connected": True, "rssi_dbm": -42, "ping_rtt_ms": 50.0}}
        }
        write_atomic_telemetry_cache(str(cache_path), init_data)

        def writer_worker():
            for i in range(100):
                payload = {
                    "timestamp": time.time(),
                    "seq": i,
                    "controller": {"powered": True, "address": "1C:F6:4C:81:0B:28"},
                    "nodes": {
                        "l3_linux": {
                            "mac": "00:41:0E:14:28:44",
                            "connected": True,
                            "rssi_dbm": -40 - (i % 5),
                            "ping_rtt_ms": 40.0 + (i % 20)
                        }
                    }
                }
                write_atomic_telemetry_cache(str(cache_path), payload)
                time.sleep(0.002)

        def reader_worker():
            while not stop_event.is_set():
                try:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    assert "controller" in data
                    assert "nodes" in data
                    read_count[0] += 1
                except Exception as e:
                    read_errors.append(f"{type(e).__name__}: {e}")
                time.sleep(0.001)

        writer_thread = threading.Thread(target=writer_worker)
        reader_threads = [threading.Thread(target=reader_worker) for _ in range(10)]

        for r in reader_threads:
            r.start()
        writer_thread.start()

        writer_thread.join(timeout=5.0)
        stop_event.set()
        for r in reader_threads:
            r.join(timeout=2.0)

        assert len(read_errors) == 0, f"Concurrency race caused read errors: {read_errors[:5]}"
        assert read_count[0] > 100, f"Expected > 100 reads, got {read_count[0]}"


class TestAdversarialZeroMockMonorepoForensics:
    """
    Forensically audits the entire codebase for banned mock strings.
    """

    def test_banned_mock_strings_absent_across_all_scripts(self):
        """
        Audits all Python files in 06_scripts_and_tooling.
        Verifies zero occurrences of:
        - 'BT: CONNECTED (5c-cb-99-05-81-41)'
        - '40 Gbps, 0.43ms RTT'
        - '0.003 Gbps, 12.5ms RTT'
        """
        py_files = list(SCRIPTS_DIR.glob("*.py"))
        banned = [
            re.compile(r"BT:\s*CONNECTED\s*\(5c-cb-99-05-81-41\)", re.IGNORECASE),
            re.compile(r"40\s*Gbps,\s*0\.43ms\s*RTT", re.IGNORECASE),
            re.compile(r"0\.003\s*Gbps,\s*12\.5ms\s*RTT", re.IGNORECASE),
        ]

        violations = []
        for f in py_files:
            text = f.read_text(encoding="utf-8", errors="replace")
            for line_no, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith("*"):
                    continue
                for pattern in banned:
                    if pattern.search(line):
                        violations.append(f"{f.name}:{line_no} -> {stripped}")

        assert len(violations) == 0, f"Zero-Mock violations detected in scripts:\n" + "\n".join(violations)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
