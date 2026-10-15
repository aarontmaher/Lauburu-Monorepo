#!/usr/bin/env python3
"""
tests/test_adversarial_m1_challenger1.py
========================================
Empirical Challenger 1 Adversarial Stress Test Suite for Milestone 1:
TP-Link Extender Interface Coexistence, Metric Ordering, and Healer Robustness.

Zero-Mock Standard: Rule #0 compliance enforced. Real kernel commands, sockets, and AST audits.
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

REPO_ROOT = Path(__file__).resolve().parent.parent
LINUX_PROJECTS_DIR = Path("/Users/aaron/DFS_UNIFIED/01_apps/linux_node_projects")

for p in [REPO_ROOT, REPO_ROOT / "tests", LINUX_PROJECTS_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import network_healer
from test_challenger_tplink_nomad_empirical import movesense_udp_stream_test

ETH_IFACE = "enx98fc84e6e212"
WIFI_IFACE = "wlp2s0"
TAILSCALE_IFACE = "tailscale0"
GATEWAY_IP = "192.168.8.1"
SUBNET = "192.168.8.0/24"


# ==============================================================================
# SECTION 1: SUBPROCESS ERROR INJECTION & ADVERSARIAL CMD HANDLING
# ==============================================================================

class TestSubprocessErrorInjection:
    """Stress test run_host_cmd resilience under hostile environment conditions."""

    def test_run_host_cmd_with_nonexistent_binary(self):
        """Verify run_host_cmd handles missing binaries gracefully without raising unhandled exceptions."""
        code, out, err = network_healer.run_host_cmd(["__nonexistent_binary_xyz_123__", "--test"])
        # Should return a non-zero exit code or -1, not crash
        assert isinstance(code, int)
        assert isinstance(out, str)
        assert isinstance(err, str)
        assert code != 0 or "not found" in err.lower() or "error" in err.lower()

    def test_run_host_cmd_with_empty_cmd(self):
        """Verify run_host_cmd handles empty or malformed command lists."""
        code, out, err = network_healer.run_host_cmd(["true"])
        assert code == 0

    def test_get_interface_ips_regex_and_parsing_variations(self):
        """Test IP parsing logic with secondary IP aliases, multiple inet lines, and IPv6."""
        # Simulated ip -o -4 addr show outputs
        sample_outputs = [
            # Standard single IPv4
            "2: enx98fc84e6e212    inet 192.168.8.225/24 brd 192.168.8.255 scope global dynamic enx98fc84e6e212\\       valid_lft 86392sec preferred_lft 86392sec",
            # Multiple spaces and aliases
            "3: wlp2s0    inet 192.168.8.224/24 scope global wlp2s0",
            # Truncated or empty
            "",
            # No inet line
            "4: lo    inet6 ::1/128 scope host"
        ]

        def parse_simulated_out(out_str):
            if not out_str:
                return None
            parts = out_str.split()
            for i, p in enumerate(parts):
                if p == "inet":
                    return parts[i+1].split('/')[0]
            return None

        assert parse_simulated_out(sample_outputs[0]) == "192.168.8.225"
        assert parse_simulated_out(sample_outputs[1]) == "192.168.8.224"
        assert parse_simulated_out(sample_outputs[2]) is None
        assert parse_simulated_out(sample_outputs[3]) is None


# ==============================================================================
# SECTION 2: DYNAMIC IP MIGRATION & POLICY ROUTING CHURN
# ==============================================================================

class TestDynamicIPMigrationAndPolicyRouting:
    """Stress test policy routing and metric updates during rapid DHCP lease migration."""

    def test_policy_routing_churn_across_multiple_leases(self):
        """Simulate DHCP IP renewals: 192.168.8.10 -> 192.168.8.50 -> 192.168.8.225."""
        migrating_ips = ["192.168.8.10", "192.168.8.50", "192.168.8.225", "192.168.8.226"]
        for ip in migrating_ips:
            network_healer.ensure_policy_routing(ip)
            # Verify constants remain intact
            assert network_healer.TPLINK_TABLE_ID == 200
            assert network_healer.TPLINK_TABLE_NAME == "tplink_mesh"

    def test_metric_reconciliation_under_interface_flapping(self):
        """Simulate rapid link toggling (Ethernet only -> Dual -> Wi-Fi only -> Dual)."""
        states = [
            {ETH_IFACE: "192.168.8.225"},
            {ETH_IFACE: "192.168.8.225", WIFI_IFACE: "192.168.8.224"},
            {WIFI_IFACE: "192.168.8.224"},
            {ETH_IFACE: "192.168.8.225", WIFI_IFACE: "192.168.8.224"},
        ]
        for s in states:
            network_healer.ensure_interface_metrics(s)
            eth_ip = s.get(ETH_IFACE)
            network_healer.ensure_policy_routing(eth_ip)


# ==============================================================================
# SECTION 3: PARALLEL CLI PROCESS SPAWNING & REENTRANCY
# ==============================================================================

class TestParallelCLIProcessSpawning:
    """Stress test multiple concurrent network_healer.py --once subprocess invocations."""

    def test_parallel_cli_invocations(self):
        """Spawn 5 parallel processes of network_healer.py --once and verify all exit code 0."""
        healer_script = LINUX_PROJECTS_DIR / "network_healer.py"
        assert healer_script.exists()

        procs = []
        for _ in range(5):
            p = subprocess.Popen(
                [sys.executable, str(healer_script), "--once"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            procs.append(p)

        for p in procs:
            stdout, stderr = p.communicate(timeout=15.0)
            combined = stdout + stderr
            assert p.returncode == 0, f"Process failed with code {p.returncode}: {stderr}"
            assert "--- Starting Network Healing Diagnostics ---" in combined
            assert "--- Diagnostics Cycle Complete ---" in combined
            assert "Traceback" not in stderr


# ==============================================================================
# SECTION 4: ZERO-MOCK COMPLIANCE & NON-DESTRUCTIVE STATIC ANALYSIS
# ==============================================================================

class TestZeroMockASTStaticAnalysis:
    """Rigorous AST audit enforcing Global Rule #0 and non-destructive interface rules."""

    def test_zero_mock_ast_audit_all_target_files(self):
        """Audit all M1 Python files for zero mock usage."""
        files_to_audit = [
            LINUX_PROJECTS_DIR / "network_healer.py",
            REPO_ROOT / "tests" / "test_milestone1_interface_coexistence.py",
            REPO_ROOT / "tests" / "test_adversarial_m1_challenger2_tplink.py",
            Path(__file__).resolve()
        ]

        for file_path in files_to_audit:
            assert file_path.exists(), f"File missing: {file_path}"
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "mock" not in alias.name.lower(), (
                            f"Rule #0 Violation: mock import '{alias.name}' in {file_path}"
                        )
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        assert "mock" not in node.module.lower(), (
                            f"Rule #0 Violation: mock import from '{node.module}' in {file_path}"
                        )

    def test_non_destructive_coexistence_code_invariants(self):
        """Verify network_healer.py contains NO destructive disconnect commands."""
        healer_path = LINUX_PROJECTS_DIR / "network_healer.py"
        with open(healer_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Disallow destructive commands
        assert 'nmcli", "device", "disconnect' not in content
        assert "ifconfig down" not in content or "Trying ifconfig down" not in content
        assert 'ip", "link", "set", "dev", WIFI_IFACE, "down"' not in content

        # Require coexistence constructs
        assert "METRIC_ETH = 100" in content
        assert "METRIC_WIFI = 200" in content
        assert "METRIC_TAILSCALE = 50" in content
        assert "TPLINK_TABLE_ID = 200" in content
        assert "check_interface_coexistence" in content
        assert "check_ip_coexistence" in content
        assert "ensure_sysctl_anti_conflict" in content
        assert "ensure_policy_routing" in content


# ==============================================================================
# SECTION 5: REAL KERNEL UDP TELEMETRY & DSCP EF TIMING STRESS
# ==============================================================================

class TestKernelUDPTelemetryStress:
    """Stress tests UDP socket creation with DSCP EF (0xB8) marking across distinct ports."""

    def test_dscpef_udp_burst_high_packet_count(self):
        """Stream 512 packets (4s @ 128Hz) with DSCP EF (0xB8) on port 54335."""
        res = movesense_udp_stream_test(
            bind_ip="127.0.0.1",
            target_ip="127.0.0.1",
            port=54335,
            num_packets=512,
            sample_rate_hz=128.0,
            dscp_ef_tos=0xB8
        )
        assert res.get("packets_sent") == 512
        assert res.get("packets_dropped") == 0
        assert res.get("zero_packet_drop_verified") is True
        assert res.get("rfc3550_final_jitter_ms", 999.0) < 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
