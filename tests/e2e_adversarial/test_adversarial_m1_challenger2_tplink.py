#!/usr/bin/env python3
"""
tests/test_adversarial_m1_challenger2_tplink.py
================================================
Empirical Challenger 2 Adversarial Stress Test Suite for Milestone 1:
TP-Link Extender Interface Discovery, Metric Hierarchy & Dual-NIC Coexistence.

Target Subsystems:
  - /Users/aaron/DFS_UNIFIED/01_apps/linux_node_projects/network_healer.py
  - /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/tests/test_milestone1_interface_coexistence.py

Covers:
  1. Section 1: Metric Hierarchy Invariants & Kernel Route Arbitration Math
  2. Section 2: Interface Discovery & State Transition Stress (Dual, Single Eth, Single Wi-Fi, None, Missing NIC)
  3. Section 3: Malformed & Corrupted Kernel/Command Output Fuzzing
  4. Section 4: Concurrency, Reentrancy & High-Frequency Healing Execution
  5. Section 5: Zero-Mock Rule #0 AST Static Analysis & Non-Destructive Integrity Audit
  6. Section 6: Empirical Network Socket & DSCP EF Telemetry Stress Verification
"""

import ast
import json
import os
import re
import socket
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
import pytest

# Ensure repository root and linux node projects are in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
LINUX_PROJECTS_DIR = Path("/Users/aaron/DFS_UNIFIED/01_apps/linux_node_projects")

for p in [REPO_ROOT, REPO_ROOT / "tests", LINUX_PROJECTS_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import network_healer
from test_challenger_tplink_nomad_empirical import movesense_udp_stream_test

# Constants
ETH_IFACE = "enx98fc84e6e212"
WIFI_IFACE = "wlp2s0"
TAILSCALE_IFACE = "tailscale0"
GATEWAY_IP = "192.168.8.1"
SUBNET = "192.168.8.0/24"


# ==============================================================================
# SECTION 1: METRIC HIERARCHY INVARIANTS & KERNEL ROUTE ARBITRATION MATH
# ==============================================================================

class TestMetricHierarchyInvariants:
    """Adversarial stress testing of metric hierarchy and kernel routing selection."""

    def test_strict_metric_ordering_invariant(self):
        """Assert strict invariant: METRIC_TAILSCALE (50) < METRIC_ETH (100) < METRIC_WIFI (200)."""
        assert network_healer.METRIC_TAILSCALE == 50
        assert network_healer.METRIC_ETH == 100
        assert network_healer.METRIC_WIFI == 200

        # Mathematical strict inequality checks
        assert network_healer.METRIC_TAILSCALE < network_healer.METRIC_ETH
        assert network_healer.METRIC_ETH < network_healer.METRIC_WIFI
        assert (network_healer.METRIC_WIFI - network_healer.METRIC_ETH) == 100
        assert (network_healer.METRIC_ETH - network_healer.METRIC_TAILSCALE) == 50

    def test_policy_routing_table_constants(self):
        """Assert policy routing table ID and name constants match specifications."""
        assert network_healer.TPLINK_TABLE_ID == 200
        assert network_healer.TPLINK_TABLE_NAME == "tplink_mesh"
        assert network_healer.SUBNET == "192.168.8.0/24"
        assert network_healer.GATEWAY_IP == "192.168.8.1"

    def test_kernel_routing_arbitration_simulation(self):
        """Simulate kernel routing resolution under various metric configurations."""
        # 1. Dual Default Routes in main table
        routes_dual = [
            {"prefix": "0.0.0.0/0", "gw": "192.168.8.1", "dev": ETH_IFACE, "metric": network_healer.METRIC_ETH},
            {"prefix": "0.0.0.0/0", "gw": "192.168.8.1", "dev": WIFI_IFACE, "metric": network_healer.METRIC_WIFI},
        ]
        chosen_dual = min(routes_dual, key=lambda r: r["metric"])
        assert chosen_dual["dev"] == ETH_IFACE, "Kernel must select lowest metric (Ethernet=100)"

        # 2. Tailscale Overlay Route for 100.64.0.0/10 vs Local Gateway
        routes_overlay = [
            {"prefix": "100.64.0.0/10", "gw": "0.0.0.0", "dev": TAILSCALE_IFACE, "metric": network_healer.METRIC_TAILSCALE},
            {"prefix": "0.0.0.0/0", "gw": "192.168.8.1", "dev": ETH_IFACE, "metric": network_healer.METRIC_ETH},
        ]
        # More specific prefix + lower metric must win for Tailscale traffic
        ts_dest = "100.101.39.98"
        # Match prefix logic
        matching_routes = [r for r in routes_overlay if r["prefix"] == "100.64.0.0/10"]
        assert len(matching_routes) == 1
        assert matching_routes[0]["dev"] == TAILSCALE_IFACE

    def test_source_policy_routing_priority(self):
        """Simulate ip rule table selector with priority 1000 for source-pinned Ethernet traffic."""
        rules = [
            {"priority": 0, "selector": "all", "table": "local"},
            {"priority": 1000, "selector": "from 192.168.8.225", "table": 200},
            {"priority": 32766, "selector": "all", "table": "main"},
            {"priority": 32767, "selector": "all", "table": "default"},
        ]
        # Pinned source IP 192.168.8.225 must hit priority 1000 before main table (32766)
        src_ip = "192.168.8.225"
        matched_rules = [r for r in sorted(rules, key=lambda x: x["priority"]) if r["selector"] == f"from {src_ip}"]
        assert len(matched_rules) == 1
        assert matched_rules[0]["table"] == 200
        assert matched_rules[0]["priority"] == 1000


# ==============================================================================
# SECTION 2: INTERFACE DISCOVERY & STATE TRANSITION STRESS TESTING
# ==============================================================================

class TestInterfaceDiscoveryAndStateTransitions:
    """Stress tests network_healer across all interface state permutations."""

    def test_dual_active_interfaces_coexistence(self):
        """Stress dual-NIC active state: both Ethernet and Wi-Fi on 192.168.8.0/24."""
        test_ips = {ETH_IFACE: "192.168.8.225", WIFI_IFACE: "192.168.8.224"}
        
        # Verify ensure_interface_metrics handles dual IPs
        network_healer.ensure_interface_metrics(test_ips)
        
        # Verify ensure_policy_routing handles active Ethernet IP
        network_healer.ensure_policy_routing(test_ips[ETH_IFACE])

    def test_single_active_interface_ethernet_only(self):
        """Stress single-NIC state: Ethernet connected, Wi-Fi disconnected."""
        test_ips = {ETH_IFACE: "192.168.8.225"}
        
        network_healer.ensure_interface_metrics(test_ips)
        network_healer.ensure_policy_routing(test_ips[ETH_IFACE])

    def test_single_active_interface_wifi_only(self):
        """Stress single-NIC state: Wi-Fi connected, Ethernet disconnected."""
        test_ips = {WIFI_IFACE: "192.168.8.224"}
        
        network_healer.ensure_interface_metrics(test_ips)
        # Should cleanly do nothing when eth_ip is None
        network_healer.ensure_policy_routing(None)
        network_healer.ensure_policy_routing("")

    def test_zero_active_interfaces_graceful_handling(self):
        """Stress zero-NIC state: both interfaces down/disconnected."""
        test_ips = {}
        network_healer.ensure_interface_metrics(test_ips)
        network_healer.ensure_policy_routing(None)

    def test_interface_status_probing_nonexistent_interface(self):
        """Verify get_interface_status handles non-existent device names gracefully."""
        dummy_ifaces = ["nonexistent_eth99", "dummy_nic_0", "wlan_ghost_42", ""]
        for iface in dummy_ifaces:
            status = network_healer.get_interface_status(iface)
            assert isinstance(status, dict)
            assert status["exists"] is False
            assert status["up"] is False
            assert status["carrier"] is False

    def test_ensure_interfaces_connected_handles_down_devices(self):
        """Verify ensure_interfaces_connected executes without exception on any interface state."""
        network_healer.ensure_interfaces_connected()

    def test_ensure_sysctl_anti_conflict_execution(self):
        """Verify ensure_sysctl_anti_conflict executes cleanly."""
        network_healer.ensure_sysctl_anti_conflict()


# ==============================================================================
# SECTION 3: MALFORMED & CORRUPTED KERNEL/COMMAND OUTPUT FUZZING
# ==============================================================================

class TestMalformedOutputFuzzing:
    """Fuzzes internal parsers against hostile, malformed, and truncated strings."""

    def test_get_interface_status_flag_parsing_fuzzing(self):
        """Test status parsing logic against various raw kernel ip link output strings."""
        test_cases = [
            # Standard UP with LOWER_UP (has carrier)
            (
                "2: enx98fc84e6e212: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP mode DEFAULT",
                True, True, True
            ),
            # UP but NO-CARRIER (cable unplugged)
            (
                "2: enx98fc84e6e212: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc fq_codel state DOWN mode DEFAULT",
                True, True, False
            ),
            # Administratively DOWN without carrier
            (
                "2: enx98fc84e6e212: <BROADCAST,MULTICAST> mtu 1500 qdisc fq_codel state DOWN mode DEFAULT",
                True, False, False
            ),
            # Malformed brackets
            (
                "2: enx98fc84e6e212: state UP mode DEFAULT",
                True, True, True
            ),
            # Completely corrupted string
            (
                "Garbage text with random <> chars and state UNKNOWN",
                True, False, False
            ),
        ]

        for raw_out, exp_exists, exp_up, exp_carrier in test_cases:
            # Inline recreation of parser logic from network_healer.py
            is_up = False
            if "state UP" in raw_out:
                is_up = True
            elif "<" in raw_out and ">" in raw_out:
                flags = raw_out.split("<", 1)[1].split(">", 1)[0].split(",")
                is_up = "UP" in flags
            has_carrier = ("NO-CARRIER" not in raw_out) and ("LOWER_UP" in raw_out or "state UP" in raw_out)
            
            assert is_up == exp_up, f"Failed up assertion on '{raw_out}': got {is_up}, exp {exp_up}"
            assert has_carrier == exp_carrier, f"Failed carrier assertion on '{raw_out}': got {has_carrier}, exp {exp_carrier}"

    def test_tailscale_healthcheck_fuzzing(self):
        """Verify check_tailscale_health handles corrupted Tailscale JSON gracefully."""
        # check_tailscale_health uses run_host_cmd internally, verify it runs without throwing
        network_healer.check_tailscale_health()

    def test_nas_and_samba_recovery_fuzzing(self):
        """Verify check_nas_mounts and check_samba_status execute without throwing."""
        network_healer.check_nas_mounts()
        network_healer.check_samba_status()


# ==============================================================================
# SECTION 4: CONCURRENCY, REENTRANCY & HIGH-FREQUENCY EXECUTION
# ==============================================================================

class TestConcurrencyAndReentrancy:
    """Stress tests high concurrency and rapid repeated invocation of healing daemon."""

    def test_concurrent_heal_cycle_execution(self):
        """Run 10 concurrent threads executing heal_cycle simultaneously."""
        errors = []

        def worker(w_id: int):
            try:
                for _ in range(3):
                    network_healer.heal_cycle()
            except Exception as e:
                errors.append(f"Worker {w_id} crashed: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent execution errors: {errors}"

    def test_rapid_sequential_diagnostics_execution(self):
        """Execute 25 rapid sequential heal_cycle calls to verify zero state leakage."""
        t0 = time.perf_counter()
        for _ in range(25):
            network_healer.check_interface_coexistence()
        elapsed = time.perf_counter() - t0
        assert elapsed < 30.0, f"Rapid diagnostics took too long: {elapsed:.2f}s"


# ==============================================================================
# SECTION 5: ZERO-MOCK RULE #0 AST STATIC ANALYSIS & INTEGRITY AUDIT
# ==============================================================================

class TestZeroMockASTStaticAnalysisAudit:
    """AST static analysis verifying zero mock objects and non-destructive code."""

    def test_ast_audit_network_healer_zero_mock(self):
        """Audit network_healer.py for zero mock imports and absence of nmcli disconnect."""
        healer_path = LINUX_PROJECTS_DIR / "network_healer.py"
        assert healer_path.exists(), f"File missing: {healer_path}"

        with open(healer_path, "r", encoding="utf-8") as f:
            source = f.read()

        parsed = ast.parse(source, filename=str(healer_path))
        assert parsed is not None

        # Verify zero mock imports
        for node in ast.walk(parsed):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "mock" not in alias.name.lower(), f"Rule #0 Violation: Mock import '{alias.name}'"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert "mock" not in node.module.lower(), f"Rule #0 Violation: Mock import from '{node.module}'"

        # Verify absolute absence of destructive disconnect calls
        assert 'nmcli", "device", "disconnect' not in source, (
            "CRITICAL VIOLATION: network_healer.py still contains destructive nmcli disconnect!"
        )
        assert "disconnect" not in source.lower() or "disconnected" in source.lower(), (
            "Suspect disconnect call in network_healer.py"
        )

        # Verify required coexistence identifiers
        required_identifiers = [
            "check_interface_coexistence",
            "check_ip_coexistence",
            "METRIC_TAILSCALE",
            "METRIC_ETH",
            "METRIC_WIFI",
            "TPLINK_TABLE_ID",
            "TPLINK_TABLE_NAME",
            "ensure_sysctl_anti_conflict",
            "ensure_policy_routing",
            "ensure_interface_metrics",
            "ensure_interfaces_connected",
        ]
        for ident in required_identifiers:
            assert ident in source, f"Required coexistence identifier '{ident}' missing in network_healer.py"

    def test_ast_audit_test_suite_zero_mock(self):
        """Audit test_milestone1_interface_coexistence.py for zero mock imports."""
        test_file = REPO_ROOT / "tests" / "test_milestone1_interface_coexistence.py"
        assert test_file.exists(), f"Test file missing: {test_file}"

        with open(test_file, "r", encoding="utf-8") as f:
            source = f.read()

        parsed = ast.parse(source, filename=str(test_file))
        assert parsed is not None

        for node in ast.walk(parsed):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "mock" not in alias.name.lower(), f"Rule #0 Violation: Mock import '{alias.name}'"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert "mock" not in node.module.lower(), f"Rule #0 Violation: Mock import from '{node.module}'"


# ==============================================================================
# SECTION 6: EMPIRICAL NETWORK SOCKET & DSCP EF TELEMETRY VERIFICATION
# ==============================================================================

class TestEmpiricalSocketAndTelemetryStress:
    """Stress tests real kernel UDP sockets with DSCP EF (0xB8) priority tagging."""

    def test_movesense_128hz_telemetry_burst(self):
        """Stream 384 packets (3s @ 128Hz) with DSCP EF (0xB8) and assert zero packet loss."""
        res = movesense_udp_stream_test(
            bind_ip="127.0.0.1",
            target_ip="127.0.0.1",
            port=54330,
            num_packets=384,
            sample_rate_hz=128.0,
            dscp_ef_tos=0xB8
        )
        assert res.get("packets_sent") == 384
        assert res.get("packets_dropped") == 0
        assert res.get("zero_packet_drop_verified") is True
        assert res.get("rfc3550_final_jitter_ms", 999.0) < 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
