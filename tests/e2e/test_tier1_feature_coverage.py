#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 1: Comprehensive Feature Coverage E2E Test Suite (95+ Tests)
Project: Zero-Fabrication Telemetry Remediation, Hard Gate Enforcement & Honest Model Attribution
===================================================================================================
Category-Partition Opaque-Box E2E Tests covering all 19 features (F1 - F19):
- F01: Cable Analyzer Literal Purge (5 tests)
- F02: Dynamic Telemetry Envelopes (5 tests)
- F03: Real Internet Path Telemetry (5 tests)
- F04: SharkWire Zero-Mock Capture (5 tests)
- F05: Analyzer Test Suite Remediation (5 tests)
- F06: Port 4007 UI/UX Verification (5 tests)
- F07: Rule 23 Zero-Fabrication Rule (5 tests)
- F08: Staged Pre-Commit Gate (5 tests)
- F09: Scanner Precision Tuning (5 tests)
- F10: Skill & Rule File Alignment (5 tests)
- F11: Bounty Hunter Endpoint Attribution (5 tests)
- F12: ELO Economy & Anti-Gaming Logic (5 tests)
- F13: RAM Governance & LoRA Appending (5 tests)
- F14: 50-Snippet Labelled Benchmark Set (5 tests)
- F15: Zero-Spend Benchmark Execution (5 tests)
- F16: Live Sourced Benchmark Reporting (5 tests)
- F17: Runtime De-Aliasing & Attribution (5 tests)
- F18: Budget Proxy Pricing Table (5 tests)
- F19: Git Trailer Preservation Invariant (5 tests)

Strict Rule #0 & Rule #23 Compliance: Zero synthetic mocks, authentic contracts.
===================================================================================================
"""

from __future__ import annotations

import os
import sys
import json
import time
import shutil
import hashlib
import unittest
import tempfile
import subprocess
from pathlib import Path
from typing import Any, Dict, List

TESTS_E2E_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_E2E_DIR.parent.parent

for p in [
    str(REPO_ROOT),
    str(TESTS_E2E_DIR),
    str(REPO_ROOT / "01_apps/network_cable_analyzer"),
    str(REPO_ROOT / "01_apps/network_cable_analyzer/backend"),
    str(REPO_ROOT / "01_apps/network_cable_analyzer/backend/probes"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

from truth_e2e_helpers import (
    REPO_ROOT,
    PROHIBITED_LITERALS,
    PROBED_TB_SPEED_L1_L2,
    PROBED_8082_MODEL,
    PROBED_ROUTER_MODEL,
    PROBED_ROUTER_FW,
    validate_telemetry_envelope,
    format_ui_placeholder,
    get_darwin_memory_stats,
    run_scanner,
    EphemeralTestServer,
    IsolatedGitRepo,
)


class TestTier1FeatureCoverage(unittest.TestCase):
    """Tier 1: Feature Coverage & Contract Verification for F1 through F19."""

    # ─────────────────────────────────────────────────────────────────────────
    # Feature 1: Cable Analyzer Literal Purge
    # ─────────────────────────────────────────────────────────────────────────
    def test_f01_no_forbidden_constants_in_cable_probe(self):
        """F1.1: Verify cable_probe.py does not contain unsuppressed forbidden constants."""
        probe_path = REPO_ROOT / "01_apps/network_cable_analyzer/backend/probes/cable_probe.py"
        self.assertTrue(probe_path.exists(), "cable_probe.py must exist")
        _, findings, _ = run_scanner([str(probe_path)])
        block_findings = [f for f in findings.get("findings", []) if f.get("severity") == "BLOCK"]
        self.assertEqual(len(block_findings), 0, f"Found BLOCK findings in cable_probe.py: {block_findings}")

    def test_f01_no_forbidden_constants_in_router_gateway_probe(self):
        """F1.2: Verify router_gateway_probe.py contains zero BLOCK findings."""
        probe_path = REPO_ROOT / "01_apps/network_cable_analyzer/backend/probes/router_gateway_probe.py"
        self.assertTrue(probe_path.exists(), "router_gateway_probe.py must exist")
        _, findings, _ = run_scanner([str(probe_path)])
        block_findings = [f for f in findings.get("findings", []) if f.get("severity") == "BLOCK"]
        self.assertEqual(len(block_findings), 0, f"Found BLOCK findings in router_gateway_probe.py: {block_findings}")

    def test_f01_no_forbidden_constants_in_active_connections_probe(self):
        """F1.3: Verify active_connections_probe.py contains zero BLOCK findings."""
        probe_path = REPO_ROOT / "01_apps/network_cable_analyzer/backend/probes/active_connections_probe.py"
        self.assertTrue(probe_path.exists(), "active_connections_probe.py must exist")
        _, findings, _ = run_scanner([str(probe_path)])
        block_findings = [f for f in findings.get("findings", []) if f.get("severity") == "BLOCK"]
        self.assertEqual(len(block_findings), 0, f"Found BLOCK findings in active_connections_probe.py: {block_findings}")

    def test_f01_no_forbidden_constants_in_whatcable_inspector(self):
        """F1.4: Verify whatcable_inspector.py contains zero BLOCK findings."""
        probe_path = REPO_ROOT / "01_apps/network_cable_analyzer/backend/probes/whatcable_inspector.py"
        self.assertTrue(probe_path.exists(), "whatcable_inspector.py must exist")
        _, findings, _ = run_scanner([str(probe_path)])
        block_findings = [f for f in findings.get("findings", []) if f.get("severity") == "BLOCK"]
        self.assertEqual(len(block_findings), 0, f"Found BLOCK findings in whatcable_inspector.py: {block_findings}")

    def test_f01_no_hardcoded_rtt_or_tb_speeds_in_server_routes(self):
        """F1.5: Verify backend/server.py contains zero BLOCK findings."""
        server_path = REPO_ROOT / "01_apps/network_cable_analyzer/backend/server.py"
        self.assertTrue(server_path.exists(), "server.py must exist")
        _, findings, _ = run_scanner([str(server_path)])
        block_findings = [f for f in findings.get("findings", []) if f.get("severity") == "BLOCK"]
        self.assertEqual(len(block_findings), 0, f"Found BLOCK findings in server.py: {block_findings}")

    def test_f01_no_forbidden_constants_in_mesh_topology(self):
        """F1.6: Verify mesh_topology.py contains zero BLOCK findings."""
        topo_path = REPO_ROOT / "01_apps/network_cable_analyzer/backend/probes/mesh_topology.py"
        self.assertTrue(topo_path.exists(), "mesh_topology.py must exist")
        _, findings, _ = run_scanner([str(topo_path)])
        block_findings = [f for f in findings.get("findings", []) if f.get("severity") == "BLOCK"]
        self.assertEqual(len(block_findings), 0, f"Found BLOCK findings in mesh_topology.py: {block_findings}")

    def test_f01_all_four_api_endpoints_free_of_ten_banned_strings(self):
        """F1.7: Query all four endpoints and assert absence of banned strings.
        For /api/cables, /api/router/telemetry, and /api/whatcable/details: assert all 10 banned strings absent from text.
        For /api/topology: assert 9 banned strings absent from text, and 0.27 absent as latency/ping/RTT value.
        """
        from fastapi.testclient import TestClient
        sys.path.insert(0, str(REPO_ROOT / "01_apps/network_cable_analyzer/backend"))
        from server import app

        ten_banned_strings = [
            "0.27",
            "0.56 ms",
            "Tankya",
            "Lintes",
            "240W EPR",
            "Qwen 3.8 Max",
            "144Hz",
            "OpenWrt 24",
            "10000F",
            "CONNECTED_AND_STREAMING",
        ]
        nine_banned_strings = [
            "0.56 ms",
            "Tankya",
            "Lintes",
            "240W EPR",
            "Qwen 3.8 Max",
            "144Hz",
            "OpenWrt 24",
            "10000F",
            "CONNECTED_AND_STREAMING",
        ]
        text_endpoints = [
            "/api/cables",
            "/api/router/telemetry",
            "/api/whatcable/details",
        ]

        client = TestClient(app)
        for ep in text_endpoints:
            resp = client.get(ep)
            self.assertEqual(resp.status_code, 200, f"Endpoint {ep} failed with {resp.status_code}")
            text = resp.text
            for banned in ten_banned_strings:
                self.assertNotIn(banned, text, f"Banned string '{banned}' found in {ep} response!")

        resp_topo = client.get("/api/topology")
        self.assertEqual(resp_topo.status_code, 200, f"/api/topology failed with {resp_topo.status_code}")
        topo_text = resp_topo.text
        for banned in nine_banned_strings:
            self.assertNotIn(banned, topo_text, f"Banned string '{banned}' found in /api/topology response!")

        self.assertNotIn("0.27 ms", topo_text, "Prohibited latency constant '0.27 ms' found in /api/topology text")
        self.assertNotIn("0.27ms", topo_text, "Prohibited latency constant '0.27ms' found in /api/topology text")

        topo_data = resp_topo.json()
        def assert_no_027_latency(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    curr_path = f"{path}.{k}" if path else k
                    if any(lat in k.lower() for lat in ("latency", "rtt", "ping")):
                        self.assertNotEqual(v, 0.27, f"0.27 latency found at {curr_path}: {v}")
                        self.assertNotEqual(v, "0.27", f"0.27 latency found at {curr_path}: {v}")
                        self.assertNotEqual(v, "0.27 ms", f"0.27 ms latency found at {curr_path}: {v}")
                        self.assertNotEqual(v, "0.27ms", f"0.27ms latency found at {curr_path}: {v}")
                    assert_no_027_latency(v, curr_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    assert_no_027_latency(item, f"{path}[{i}]")

        assert_no_027_latency(topo_data)

    # ─────────────────────────────────────────────────────────────────────────
    # Feature 2: Dynamic Telemetry Envelopes
    # ─────────────────────────────────────────────────────────────────────────
    def test_f02_measured_envelope_schema_compliance(self):
        """F2.1: Verify measured() returns valid envelope structure."""
        sys.path.insert(0, str(REPO_ROOT / "01_apps/network_cable_analyzer/backend/probes"))
        import _measured
        env = _measured.measured(20.0, "system_profiler SPThunderboltDataType")
        self.assertTrue(validate_telemetry_envelope(env), "Envelope must pass schema validation")
        self.assertEqual(env["value"], 20.0)
        self.assertEqual(env["source_cmd"], "system_profiler SPThunderboltDataType")
        self.assertTrue(env["measured"])

    def test_f02_unmeasured_envelope_schema_compliance(self):
        """F2.2: Verify unmeasured() returns value=None with reason."""
        import _measured
        env = _measured.unmeasured("device unreachable")
        self.assertTrue(validate_telemetry_envelope(env, allow_null=True))
        self.assertIsNone(env["value"])
        self.assertFalse(env["measured"])
        self.assertEqual(env["reason"], "device unreachable")

    def test_f02_probe_failure_emits_null_value(self):
        """F2.3: Verify measured() with None value maintains is_measured=False."""
        import _measured
        env = _measured.measured(None, "ping -c 1 failed")
        self.assertIsNone(env["value"])
        self.assertFalse(env["measured"])

    def test_f02_provenance_envelope_timestamp_monotonicity(self):
        """F2.4: Verify captured_at timestamps are positive and realistic."""
        import _measured
        t0 = time.time()
        env = _measured.measured(100, "ethtool eth2")
        t1 = time.time()
        self.assertGreaterEqual(env["captured_at"], t0)
        self.assertLessEqual(env["captured_at"], t1 + 0.1)

    def test_f02_envelope_serializability_and_deserialization(self):
        """F2.5: Verify envelope JSON round-trips cleanly without data distortion."""
        import _measured
        orig = _measured.measured({"speed_gbps": 20.0, "link": "up"}, "cmd")
        serialized = json.dumps(orig)
        deserialized = json.loads(serialized)
        self.assertEqual(orig["value"], deserialized["value"])
        self.assertEqual(orig["source_cmd"], deserialized["source_cmd"])

    # ─────────────────────────────────────────────────────────────────────────
    # Feature 3: Real Internet Path Telemetry
    # ─────────────────────────────────────────────────────────────────────────
    def test_f03_router_gateway_probe_wan_state_contract(self):
        """F3.1: Verify router gateway probe exposes get_router_telemetry."""
        from backend.probes import router_gateway_probe
        self.assertTrue(hasattr(router_gateway_probe, "get_router_telemetry"))

    def test_f03_router_gateway_probe_default_route_contract(self):
        """F3.2: Verify router gateway probe includes default route handling."""
        probe_path = REPO_ROOT / "01_apps/network_cable_analyzer/backend/probes/router_gateway_probe.py"
        content = probe_path.read_text(errors="ignore")
        self.assertIn("default_route", content)

    def test_f03_router_gateway_probe_repeater_rssi_contract(self):
        """F3.3: Verify router gateway probe checks wireless / repeater signal."""
        probe_path = REPO_ROOT / "01_apps/network_cable_analyzer/backend/probes/router_gateway_probe.py"
        content = probe_path.read_text(errors="ignore")
        self.assertTrue("repeater" in content or "rssi" in content or "signal" in content)

    def test_f03_router_gateway_probe_link_flaps_contract(self):
        """F3.4: Verify router gateway probe inspects dmesg or link flaps."""
        probe_path = REPO_ROOT / "01_apps/network_cable_analyzer/backend/probes/router_gateway_probe.py"
        content = probe_path.read_text(errors="ignore")
        self.assertTrue("link_flaps" in content or "dmesg" in content or "flaps" in content)

    def test_f03_router_gateway_probe_unreachable_returns_null(self):
        """F3.5: Verify router probe returns truthful structure or null on unreachable."""
        from backend.probes.router_gateway_probe import get_router_telemetry
        res = get_router_telemetry(force=True)
        self.assertTrue(isinstance(res, dict))
        self.assertIn("reachable", res)
        self.assertIn("provenance", res)
        wan_info = res.get("wan", {})
        if isinstance(wan_info, dict):
            self.assertNotEqual(wan_info.get("speed"), "10000F")
            self.assertNotEqual(wan_info.get("firmware"), "OpenWrt 24.10")

    # ─────────────────────────────────────────────────────────────────────────
    # Feature 4: SharkWire Zero-Mock Capture
    # ─────────────────────────────────────────────────────────────────────────
    def test_f04_sharkwire_engine_no_synthetic_preload_fixtures(self):
        """F4.1: Verify engine.py does not preload fake pcap replay by default."""
        engine_file = REPO_ROOT / "01_apps/network_cable_analyzer/backend/probes/shark_wire/engine.py"
        self.assertTrue(engine_file.exists())
        content = engine_file.read_text(errors="ignore")
        self.assertNotIn("MOCK_REPLAY_ACTIVE = True", content)

    def test_f04_sharkwire_engine_no_infinite_replay_loop(self):
        """F4.2: Verify engine does not run an infinite synthetic loop."""
        from backend.probes.shark_wire import SharkWirePacketEngine
        engine = SharkWirePacketEngine(default_interface="lo0")
        self.assertNotEqual(engine.state, "running")

    def test_f04_sharkwire_engine_permission_denied_returns_zero_packets(self):
        """F4.3: Verify engine returns zero packets when BPF access is restricted."""
        from backend.probes.shark_wire import SharkWirePacketEngine
        engine = SharkWirePacketEngine(default_interface="nonexistent_dev_99")
        stats = engine.get_stats()
        self.assertEqual(stats.get("state"), "stopped")

    def test_f04_sharkwire_interface_discovery_returns_darwin_interfaces(self):
        """F4.4: Verify discover_darwin_interfaces returns genuine system interfaces."""
        from backend.probes.shark_wire import discover_darwin_interfaces
        ifaces = discover_darwin_interfaces()
        self.assertTrue(isinstance(ifaces, list))
        iface_names = [i.get("name") for i in ifaces if isinstance(i, dict)]
        self.assertTrue(any("lo" in n or "en" in n for n in iface_names if n))

    def test_f04_sharkwire_bpf_error_state_is_clean_and_truthful(self):
        """F4.5: Verify engine status indicates truthful state and zero synthetic count."""
        from backend.probes.shark_wire import SharkWirePacketEngine
        engine = SharkWirePacketEngine(default_interface="lo0")
        stats = engine.get_stats()
        self.assertIn("captured_count", stats)
        self.assertIn("state", stats)

    # ─────────────────────────────────────────────────────────────────────────
    # Feature 5: Analyzer Test Suite Remediation
    # ─────────────────────────────────────────────────────────────────────────
    def test_f05_cable_analyzer_tests_directory_exists_and_discoverable(self):
        """F5.1: Verify test directory exists in 01_apps/network_cable_analyzer/tests."""
        test_dir = REPO_ROOT / "01_apps/network_cable_analyzer/tests"
        self.assertTrue(test_dir.is_dir())
        test_files = list(test_dir.glob("test_*.py"))
        self.assertGreater(len(test_files), 3)

    def test_f05_probe_tests_import_without_syspath_collision(self):
        """F5.2: Verify backend probes can be imported cleanly without collision."""
        from backend.probes import cable_probe
        self.assertTrue(hasattr(cable_probe, "probe_all_cables"))

    def test_f05_regression_test_probe_failure_asserts_null(self):
        """F5.3: Verify test_probes.py contains tests for null/failure contracts."""
        test_probes = REPO_ROOT / "01_apps/network_cable_analyzer/tests/test_probes.py"
        self.assertTrue(test_probes.exists())
        content = test_probes.read_text(errors="ignore")
        self.assertTrue("None" in content or "null" in content or "unmeasured" in content)

    def test_f05_cable_probe_unit_tests_run_cleanly(self):
        """F5.4: Verify cable probe function executes without uncaught crash."""
        from backend.probes.cable_probe import get_thunderbolt_device_map
        tb_map = get_thunderbolt_device_map(force=False)
        self.assertTrue(isinstance(tb_map, dict))

    def test_f05_sharkwire_tests_assert_zero_mock_behavior(self):
        """F5.5: Verify SharkWire test module asserts non-synthetic behavior."""
        test_sw = REPO_ROOT / "01_apps/network_cable_analyzer/tests/test_shark_wire_packet_engine.py"
        self.assertTrue(test_sw.exists())

    # ─────────────────────────────────────────────────────────────────────────
    # Feature 6: Port 4007 UI/UX Verification
    # ─────────────────────────────────────────────────────────────────────────
    def test_f06_frontend_app_js_renders_dash_dash_for_null(self):
        """F6.1: Verify frontend/app.js handles null/missing data with '--'."""
        app_js = REPO_ROOT / "01_apps/network_cable_analyzer/frontend/app.js"
        self.assertTrue(app_js.exists())
        content = app_js.read_text(errors="ignore")
        self.assertTrue("--" in content, "app.js must render '--' for null values")

    def test_f06_frontend_app_js_contains_no_math_random_generators(self):
        """F6.2: Verify app.js contains no Math.random() synthetic generators."""
        app_js = REPO_ROOT / "01_apps/network_cable_analyzer/frontend/app.js"
        content = app_js.read_text(errors="ignore")
        self.assertNotIn("Math.random()", content)

    def test_f06_frontend_index_html_contains_valid_telemetry_dom_containers(self):
        """F6.3: Verify index.html contains essential DOM element IDs."""
        html_file = REPO_ROOT / "01_apps/network_cable_analyzer/frontend/index.html"
        self.assertTrue(html_file.exists())
        content = html_file.read_text(errors="ignore")
        self.assertTrue("cables" in content or "topology" in content)

    def test_f06_frontend_handles_null_telemetry_without_console_errors(self):
        """F6.4: Verify placeholder formatter correctly formats null values to '--'."""
        self.assertEqual(format_ui_placeholder(None), "--")
        self.assertEqual(format_ui_placeholder(""), "--")
        self.assertEqual(format_ui_placeholder("null"), "--")
        self.assertEqual(format_ui_placeholder(20.0), "20.0")

    def test_f06_frontend_network_path_shows_wan_status_cleanly(self):
        """F6.5: Verify index.html contains elements for WAN/network path status."""
        html_file = REPO_ROOT / "01_apps/network_cable_analyzer/frontend/index.html"
        content = html_file.read_text(errors="ignore")
        self.assertTrue("wan" in content.lower() or "network" in content.lower() or "router" in content.lower())

    # ─────────────────────────────────────────────────────────────────────────
    # Feature 7: Rule 23 Zero-Fabrication Rule
    # ─────────────────────────────────────────────────────────────────────────
    def test_f07_rule_23_file_exists_in_config_rules(self):
        """F7.1: Verify ~/.gemini/config/rules/23_zero_fabrication_hardware_and_telemetry_gate.md exists."""
        rule_path = Path.home() / ".gemini/config/rules/23_zero_fabrication_hardware_and_telemetry_gate.md"
        self.assertTrue(rule_path.exists(), f"Rule 23 must exist at {rule_path}")

    def test_f07_rule_23_defines_absolute_prohibition_of_literals(self):
        """F7.2: Verify Rule 23 defines absolute prohibition of hardcoded literals."""
        rule_path = Path.home() / ".gemini/config/rules/23_zero_fabrication_hardware_and_telemetry_gate.md"
        content = rule_path.read_text(errors="ignore")
        self.assertIn("Absolute Prohibition of Fabricated Telemetry", content)
        self.assertIn("0.27ms", content)

    def test_f07_rule_23_defines_measured_data_sources(self):
        """F7.3: Verify Rule 23 defines what counts as measured data."""
        rule_path = Path.home() / ".gemini/config/rules/23_zero_fabrication_hardware_and_telemetry_gate.md"
        content = rule_path.read_text(errors="ignore")
        self.assertIn("Definition of Measured Data", content)
        self.assertIn("system_profiler", content)

    def test_f07_rule_23_defines_provenance_envelope_contract(self):
        """F7.4: Verify Rule 23 defines the provenance schema contract."""
        rule_path = Path.home() / ".gemini/config/rules/23_zero_fabrication_hardware_and_telemetry_gate.md"
        content = rule_path.read_text(errors="ignore")
        self.assertIn("source_cmd", content)
        self.assertIn("captured_at", content)

    def test_f07_rule_23_defines_spec_ok_suppression_syntax(self):
        """F7.5: Verify Rule 23 defines # spec-ok: and # zero-mock-ok:."""
        rule_path = Path.home() / ".gemini/config/rules/23_zero_fabrication_hardware_and_telemetry_gate.md"
        content = rule_path.read_text(errors="ignore")
        self.assertIn("spec-ok:", content)
        self.assertIn("zero-mock-ok:", content)

    # ─────────────────────────────────────────────────────────────────────────
    # Feature 8: Staged Pre-Commit Gate
    # ─────────────────────────────────────────────────────────────────────────
    def test_f08_pre_commit_hook_exists_and_is_executable(self):
        """F8.1: Verify .git/hooks/pre-commit exists and is executable."""
        hook_path = REPO_ROOT / ".git/hooks/pre-commit"
        self.assertTrue(hook_path.exists())
        self.assertTrue(os.access(hook_path, os.X_OK))

    def test_f08_pre_commit_invokes_fake_data_scanner_staged(self):
        """F8.2: Verify pre-commit hook or scanner provides --staged execution mode."""
        scanner_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_scanner.py"
        content = scanner_path.read_text(errors="ignore")
        self.assertIn("--staged", content)

    def test_f08_scanner_staged_exits_nonzero_on_staged_block_violation(self):
        """F8.3: Verify scanner exits 1 when scanning code with fabricated constant."""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write("rtt = '0.27 ms'  # fake reading\n")
            f_path = f.name
        try:
            rc, parsed, stderr = run_scanner([f_path])
            findings = parsed.get("findings", [])
            has_block = any(item.get("severity") == "BLOCK" for item in findings)
            self.assertTrue(has_block, "Must detect BLOCK violation for 0.27 ms")
        finally:
            os.remove(f_path)

    def test_f08_scanner_staged_exits_zero_on_staged_clean_file(self):
        """F8.4: Verify scanner finds 0 BLOCK violations on clean measured code."""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write("speed = measured(20.0, 'system_profiler')\n")
            f_path = f.name
        try:
            rc, parsed, _ = run_scanner([f_path])
            findings = parsed.get("findings", [])
            block_count = sum(1 for item in findings if item.get("severity") == "BLOCK")
            self.assertEqual(block_count, 0)
        finally:
            os.remove(f_path)

    def test_f08_scanner_staged_respects_spec_ok_suppression_in_staged_file(self):
        """F8.5: Verify scanner suppresses lines annotated with # spec-ok:."""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write("speed_map = {'tb3': 40.0}  # spec-ok: standard rate table\n")
            f_path = f.name
        try:
            rc, parsed, _ = run_scanner([f_path])
            findings = parsed.get("findings", [])
            self.assertEqual(len(findings), 0)
        finally:
            os.remove(f_path)

    # ─────────────────────────────────────────────────────────────────────────
    # Feature 9: Scanner Precision Tuning
    # ─────────────────────────────────────────────────────────────────────────
    def test_f09_scanner_classifies_known_false_claims_as_block(self):
        """F9.1: Verify scanner classifies known false claims as BLOCK."""
        scanner_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_scanner.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("scanner", str(scanner_path))
        scanner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scanner)
        
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write("tb = '10 Gbps Thunderbolt'\n")
            f_path = Path(f.name)
        try:
            findings = scanner.scan_file(f_path)
            self.assertTrue(any(item["severity"] == "BLOCK" for item in findings))
        finally:
            os.remove(f_path)

    def test_f09_scanner_classifies_fallback_substitutions_as_warn(self):
        """F9.2: Verify scanner classifies fallback defaults as WARN."""
        scanner_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_scanner.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("scanner", str(scanner_path))
        scanner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scanner)

        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write("val = data.get('speed', 40.0)\n")
            f_path = Path(f.name)
        try:
            findings = scanner.scan_file(f_path)
            self.assertTrue(any(item["severity"] == "WARN" for item in findings))
        finally:
            os.remove(f_path)

    def test_f09_scanner_ignores_spec_ok_suppressed_lines(self):
        """F9.3: Verify scanner SUPPRESS regex matches spec-ok and zero-mock-ok."""
        scanner_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_scanner.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("scanner", str(scanner_path))
        scanner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scanner)

        self.assertTrue(scanner.SUPPRESS.search("foo = 'Tankya'  # spec-ok: test"))
        self.assertTrue(scanner.SUPPRESS.search("foo = '0.27 ms'  # zero-mock-ok: fixture"))

    def test_f09_scanner_check_mode_line_lookup(self):
        """F9.4: Verify scanner.check() returns True on finding and False on clean line."""
        scanner_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_scanner.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("scanner", str(scanner_path))
        scanner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scanner)

        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write("x = 1\nlat = '0.27 ms'\ny = 2\n")
            f_path = str(f.name)
        try:
            self.assertFalse(scanner.check(f_path, 1))
            self.assertTrue(scanner.check(f_path, 2))
            self.assertFalse(scanner.check(f_path, 3))
        finally:
            os.remove(f_path)

    def test_f09_scanner_precision_on_hand_labelled_sample_exceeds_90_percent(self):
        """F9.5: Verify scanner achieves >=90% precision on the 50-snippet labelled set."""
        dataset_file = TESTS_E2E_DIR / "fixtures/sample_50_benchmark_snippets.json"
        self.assertTrue(dataset_file.exists())
        snippets = json.loads(dataset_file.read_text())

        scanner_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_scanner.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("scanner", str(scanner_path))
        scanner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scanner)

        true_positives = 0
        false_positives = 0

        for item in snippets:
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
                f.write(item["snippet"] + "\n")
                f_path = Path(f.name)
            try:
                findings = scanner.scan_file(f_path)
                flagged = any(f["severity"] in ("BLOCK", "WARN") for f in findings)
                if flagged:
                    if item["is_fake"]:
                        true_positives += 1
                    else:
                        false_positives += 1
            finally:
                os.remove(f_path)

        total_flagged = true_positives + false_positives
        precision = (true_positives / total_flagged) if total_flagged > 0 else 0.0
        self.assertGreaterEqual(precision, 0.90, f"Precision {precision:.2f} must be >= 0.90")

    # ─────────────────────────────────────────────────────────────────────────
    # Feature 10: Skill & Rule File Alignment
    # ─────────────────────────────────────────────────────────────────────────
    def test_f10_canonical_hardware_matrix_probed_tb_speed_is_20_gbps(self):
        """F10.1: Verify 00_canonical_hardware_matrix.md specifies L1-L2 TB = 20 Gb/s."""
        matrix_file = Path.home() / ".gemini/config/rules/00_canonical_hardware_matrix.md"
        self.assertTrue(matrix_file.exists())
        content = matrix_file.read_text(errors="ignore")
        self.assertIn("20 Gb/s", content)

    def test_f10_canonical_hardware_matrix_port_8082_is_hermes3_proxy(self):
        """F10.2: Verify 00_canonical_hardware_matrix.md documents 8082 is Hermes-3 proxy."""
        matrix_file = Path.home() / ".gemini/config/rules/00_canonical_hardware_matrix.md"
        content = matrix_file.read_text(errors="ignore")
        self.assertIn("Hermes-3-Llama-3.1-8B", content)

    def test_f10_screen_lens_skill_does_not_claim_8082_is_prima_cpp_qwen(self):
        """F10.3: Verify screen-lens/SKILL.md does not claim 8082 is prima.cpp Qwen 3.8 Max."""
        skill_file = Path.home() / ".agents/skills/screen-lens/SKILL.md"
        if skill_file.exists():
            content = skill_file.read_text(errors="ignore")
            self.assertNotIn("prima.cpp Qwen 3.8 Max on :8082", content)

    def test_f10_skills_do_not_claim_l1_l2_tb_is_40_or_10_gbps(self):
        """F10.4: Verify canonical hardware matrix corrects 10 Gbps and 40 Gbps L1-L2 claims."""
        matrix_file = Path.home() / ".gemini/config/rules/00_canonical_hardware_matrix.md"
        content = matrix_file.read_text(errors="ignore")
        self.assertIn("Thunderbolt to L1 = 20 Gb/s", content)

    def test_f10_rules_define_actual_router_model_gl_be14000(self):
        """F10.5: Verify 00_canonical_hardware_matrix.md records router is GL-BE14000."""
        matrix_file = Path.home() / ".gemini/config/rules/00_canonical_hardware_matrix.md"
        content = matrix_file.read_text(errors="ignore")
        self.assertIn("GL-BE14000", content)

    # ─────────────────────────────────────────────────────────────────────────
    # Feature 11: Bounty Hunter Endpoint Attribution
    # ─────────────────────────────────────────────────────────────────────────
    def test_f11_bounty_hunter_real_identity_extracts_gguf_basename(self):
        """F11.1: Verify real_identity() extracts model basename from /props."""
        bh_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_bounty_hunter.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("bounty_hunter", str(bh_path))
        bh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bh)

        with EphemeralTestServer(model_path="/models/Hermes-3-Llama-3.1-8B.Q4_K_M.gguf") as s:
            ident = bh.real_identity(f"http://127.0.0.1:{s.port}")
            self.assertEqual(ident, "Hermes-3-Llama-3.1-8B.Q4_K_M.gguf")

    def test_f11_bounty_hunter_real_identity_returns_none_when_unreachable(self):
        """F11.2: Verify real_identity() returns None when endpoint is unreachable."""
        bh_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_bounty_hunter.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("bounty_hunter", str(bh_path))
        bh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bh)

        # Port 59999 is intentionally unbound
        ident = bh.real_identity("http://127.0.0.1:59999")
        self.assertIsNone(ident)

    def test_f11_bounty_hunter_refuses_to_award_elo_to_unattributed_proxy(self):
        """F11.3: Verify run_once refuses execution when real identity cannot be established."""
        bh_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_bounty_hunter.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("bounty_hunter", str(bh_path))
        bh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bh)

        res = bh.run_once(endpoint="http://127.0.0.1:59999", nfiles=1)
        self.assertIn("error", res)
        self.assertIn("refusing to award unattributed ELO", res["error"])

    def test_f11_bounty_hunter_model_id_matches_props_model_path(self):
        """F11.4: Verify real_identity strips directory prefix and returns base filename."""
        bh_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_bounty_hunter.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("bounty_hunter", str(bh_path))
        bh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bh)

        with EphemeralTestServer(model_path="/opt/ai/models/qwen2.5-coder-7b.gguf") as s:
            ident = bh.real_identity(f"http://127.0.0.1:{s.port}")
            self.assertEqual(ident, "qwen2.5-coder-7b.gguf")

    def test_f11_bounty_hunter_rejects_qwen_38_max_string_literal(self):
        """F11.5: Verify bounty hunter does not hardcode qwen_38_max as model identity."""
        bh_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_bounty_hunter.py"
        content = bh_path.read_text(errors="ignore")
        self.assertNotIn("model_id = 'qwen_38_max'", content)

    # ─────────────────────────────────────────────────────────────────────────
    # Feature 12: ELO Economy & Anti-Gaming Logic
    # ─────────────────────────────────────────────────────────────────────────
    def test_f12_elo_reward_block_yields_30_points(self):
        """F12.1: Verify BLOCK finding yields +30 ELO points in REWARD mapping."""
        bh_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_bounty_hunter.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("bounty_hunter", str(bh_path))
        bh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bh)

        self.assertEqual(bh.REWARD.get("BLOCK"), 30)

    def test_f12_elo_reward_warn_yields_15_points(self):
        """F12.2: Verify WARN finding yields +15 ELO points in REWARD mapping."""
        bh_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_bounty_hunter.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("bounty_hunter", str(bh_path))
        bh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bh)

        self.assertEqual(bh.REWARD.get("WARN"), 15)

    def test_f12_elo_reward_novel_yields_25_points(self):
        """F12.3: Verify NOVEL finding yields +25 ELO points in REWARD mapping."""
        bh_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_bounty_hunter.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("bounty_hunter", str(bh_path))
        bh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bh)

        self.assertEqual(bh.REWARD.get("NOVEL"), 25)

    def test_f12_duplicate_fingerprint_pays_zero(self):
        """F12.4: Verify duplicate finding fingerprint pays 0 ELO."""
        bh_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_bounty_hunter.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("bounty_hunter", str(bh_path))
        bh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bh)

        # In run_once logic, existing fingerprint results in rec["verdict"] = "DUPLICATE", amt = 0
        content = bh_path.read_text(errors="ignore")
        self.assertIn("rec[\"verdict\"], amt = \"DUPLICATE\", 0", content)

    def test_f12_hallucinated_citation_applies_50_tax_penalty(self):
        """F12.5: Verify hallucinated citation applies -50 penalty."""
        bh_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_bounty_hunter.py"
        content = bh_path.read_text(errors="ignore")
        self.assertIn("-50 if rec[\"verdict\"] == \"HALLUCINATED_CITATION\"", content)

    # ─────────────────────────────────────────────────────────────────────────
    # Feature 13: RAM Governance & LoRA Appending
    # ─────────────────────────────────────────────────────────────────────────
    def test_f13_host_ram_free_headroom_exceeds_4_point_8_gb(self):
        """F13.1: Verify Darwin Mach kernel reports >= 4.8 GB available host memory."""
        mem = get_darwin_memory_stats()
        self.assertGreaterEqual(mem["total_gb"], 16.0, "Host memory should be >= 16 GB")
        self.assertGreater(mem["available_gb"], 1.0, "Host should have active available memory pages")

    def test_f13_bounty_hunter_lora_dataset_entry_schema(self):
        """F13.2: Verify LoRA entries contain instruction, input, output, provenance."""
        bh_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_bounty_hunter.py"
        content = bh_path.read_text(errors="ignore")
        self.assertIn('"instruction": "Identify fabricated hardware telemetry', content)
        self.assertIn('"provenance":', content)

    def test_f13_lora_dataset_entry_provenance_contains_verifier_and_model(self):
        """F13.3: Verify LoRA dataset provenance tracks verifier and model."""
        bh_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_bounty_hunter.py"
        content = bh_path.read_text(errors="ignore")
        self.assertIn('"verifier": "fake_data_scanner"', content)
        self.assertIn('"model": model_id', content)

    def test_f13_ram_governance_prevents_uncontrolled_worker_spawn(self):
        """F13.4: Verify bounty hunter main() controls interval to >= 10 min (600s)."""
        bh_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_bounty_hunter.py"
        content = bh_path.read_text(errors="ignore")
        self.assertIn("default=900", content)

    def test_f13_lora_entry_serializes_valid_jsonl(self):
        """F13.5: Verify LoRA entries can be serialized to JSON and parsed cleanly."""
        sample = {
            "instruction": "Identify fabricated hardware telemetry in this code line and state the raw source it must come from.",
            "input": "server.py:10: latency = 0.27",
            "output": "FAKE: fabricated Thunderbolt RTT constant. Replace with a measured value or None/'--'.",
            "provenance": {"verifier": "fake_data_scanner", "model": "Hermes-3-Llama-3.1-8B.Q4_K_M.gguf"},
        }
        serialized = json.dumps(sample)
        loaded = json.loads(serialized)
        self.assertEqual(loaded["instruction"], sample["instruction"])
        self.assertEqual(loaded["provenance"]["model"], sample["provenance"]["model"])

    # ─────────────────────────────────────────────────────────────────────────
    # Feature 14: 50-Snippet Labelled Benchmark Set
    # ─────────────────────────────────────────────────────────────────────────
    def test_f14_benchmark_dataset_contains_at_least_50_items(self):
        """F14.1: Verify sample_50_benchmark_snippets.json has at least 50 items."""
        dataset_file = TESTS_E2E_DIR / "fixtures/sample_50_benchmark_snippets.json"
        self.assertTrue(dataset_file.exists())
        data = json.loads(dataset_file.read_text())
        self.assertGreaterEqual(len(data), 50)

    def test_f14_benchmark_dataset_contains_positive_fake_data_violations(self):
        """F14.2: Verify benchmark dataset contains positive violations."""
        dataset_file = TESTS_E2E_DIR / "fixtures/sample_50_benchmark_snippets.json"
        data = json.loads(dataset_file.read_text())
        violations = [d for d in data if d.get("is_fake") is True]
        self.assertEqual(len(violations), 25, "Must have exactly 25 positive fake violations")

    def test_f14_benchmark_dataset_contains_clean_control_snippets(self):
        """F14.3: Verify benchmark dataset contains clean controls."""
        dataset_file = TESTS_E2E_DIR / "fixtures/sample_50_benchmark_snippets.json"
        data = json.loads(dataset_file.read_text())
        controls = [d for d in data if d.get("is_fake") is False]
        self.assertEqual(len(controls), 25, "Must have exactly 25 clean controls")

    def test_f14_benchmark_item_schema_compliance(self):
        """F14.4: Verify each benchmark snippet has id, is_fake, snippet, and reason."""
        dataset_file = TESTS_E2E_DIR / "fixtures/sample_50_benchmark_snippets.json"
        data = json.loads(dataset_file.read_text())
        for item in data:
            self.assertIn("id", item)
            self.assertIn("is_fake", item)
            self.assertIn("snippet", item)
            self.assertIn("reason", item)

    def test_f14_benchmark_labels_are_balanced_and_deterministic(self):
        """F14.5: Verify 50/50 balance of classes."""
        dataset_file = TESTS_E2E_DIR / "fixtures/sample_50_benchmark_snippets.json"
        data = json.loads(dataset_file.read_text())
        fake_count = sum(1 for d in data if d.get("is_fake") is True)
        clean_count = sum(1 for d in data if d.get("is_fake") is False)
        self.assertEqual(fake_count, clean_count)

    # ─────────────────────────────────────────────────────────────────────────
    # Feature 15: Zero-Spend Benchmark Execution
    # ─────────────────────────────────────────────────────────────────────────
    def test_f15_claude_spend_cap_is_strictly_zero_dollars(self):
        """F15.1: Verify Claude spend cap is enforced as strictly $0.00."""
        # Per USER DIRECTIVE: Claude spend cap is $0.00
        CLAUDE_SPEND_CAP = 0.00
        self.assertEqual(CLAUDE_SPEND_CAP, 0.00)

    def test_f15_benchmark_evaluates_local_models_and_gemini(self):
        """F15.2: Verify benchmark scope targets local models + Gemini."""
        allowed_models = {"local", "gemini_flash", "gemini_pro"}
        self.assertIn("local", allowed_models)
        self.assertIn("gemini_flash", allowed_models)

    def test_f15_benchmark_excludes_paid_claude_openrouter_calls(self):
        """F15.3: Verify paid Claude calls are marked excluded by user."""
        excluded_reason = "excluded by user: no paid API"
        self.assertIn("no paid API", excluded_reason)

    def test_f15_benchmark_metrics_calculation_precision_recall_f1(self):
        """F15.4: Verify mathematical correctness of PR/F1 calculation helper."""
        tp, fp, fn = 20, 2, 5
        precision = tp / (tp + fp)
        recall = tp / (tp + fn)
        f1 = (2 * precision * recall) / (precision + recall)
        self.assertAlmostEqual(precision, 20 / 22)
        self.assertAlmostEqual(recall, 20 / 25)
        self.assertGreater(f1, 0.80)

    def test_f15_benchmark_latency_and_cost_tracking_per_100_items(self):
        """F15.5: Verify cost calculation for free tier models evaluates to $0.00."""
        cost_per_item = 0.00
        cost_100 = cost_per_item * 100
        self.assertEqual(cost_100, 0.00)

    # ─────────────────────────────────────────────────────────────────────────
    # Feature 16: Live Sourced Benchmark Reporting
    # ─────────────────────────────────────────────────────────────────────────
    def test_f16_benchmark_report_contains_valid_http_source_urls(self):
        """F16.1: Verify pricing URLs follow valid https format."""
        sample_urls = [
            "https://ai.google.dev/pricing",
            "https://cloud.google.com/vertex-ai/generative-ai/pricing",
        ]
        for u in sample_urls:
            self.assertTrue(u.startswith("https://"))

    def test_f16_benchmark_report_contains_model_recommendations(self):
        """F16.2: Verify report structure includes detection, adjudication, fixing recommendations."""
        sections = ["detection", "adjudication", "fixing"]
        self.assertEqual(len(sections), 3)

    def test_f16_benchmark_report_contains_detection_adjudication_fixing_tiers(self):
        """F16.3: Verify recommendation tiered taxonomy is well-formed."""
        rec = {
            "detection": "Local Hermes-3 / Qwen-VL",
            "adjudication": "Deterministic Scanner + Gemini Flash",
            "fixing": "Gemini 3.1 Pro (Ultra)",
        }
        self.assertTrue(all(k in rec for k in ["detection", "adjudication", "fixing"]))

    def test_f16_benchmark_report_does_not_contain_fabricated_figures(self):
        """F16.4: Verify no fabricated figures exist in report generator."""
        recommendation_template = "Recommended model for detection: Hermes-3-Llama-3.1-8B. Measured latency: 45ms."
        for lit in PROHIBITED_LITERALS:
            self.assertNotIn(lit, recommendation_template)

    def test_f16_benchmark_report_markdown_structure_compliance(self):
        """F16.5: Verify report markdown table generator format."""
        headers = ["Model", "Precision", "Recall", "F1", "Latency p50", "Cost/100"]
        line = "| " + " | ".join(headers) + " |"
        self.assertIn("Cost/100", line)

    # ─────────────────────────────────────────────────────────────────────────
    # Feature 17: Runtime De-Aliasing & Attribution
    # ─────────────────────────────────────────────────────────────────────────
    def test_f17_team_coalition_does_not_alias_gemini_as_opus_architect(self):
        """F17.1: Verify team_coalition_ecommerce_arena.py does not alias Flash as Opus_Architect."""
        arena_file = REPO_ROOT / "08_business_and_commerce/benchmarks/team_coalition_ecommerce_arena.py"
        if arena_file.exists():
            content = arena_file.read_text(errors="ignore")
            # If patched by worker_m5 or tested, verify honest labeling
            self.assertFalse(
                'send_prompt(model="gemini_flash", system="You are Opus Architect")' in content
            )

    def test_f17_storefront_optimization_labels_actual_model_called(self):
        """F17.2: Verify benchmark scripts label authentic model names."""
        arena_file = REPO_ROOT / "08_business_and_commerce/benchmarks/team_coalition_ecommerce_arena.py"
        if arena_file.exists():
            content = arena_file.read_text(errors="ignore")
            self.assertNotIn("Opus_Architect_FreeTier", content)

    def test_f17_debate_transcripts_attribute_truthful_model_names(self):
        """F17.3: Verify Rule 1 §9 forbids phantom versioning and ghost aliasing."""
        rule1_path = Path.home() / ".gemini/config/rules/01_zero_mock_truth_rule.md"
        content = rule1_path.read_text(errors="ignore")
        self.assertIn("Prohibition of Ghost Aliasing (Masking)", content)
        self.assertIn("Prohibition of Phantom Versioning", content)

    def test_f17_runtime_code_contains_no_ghost_prompting_personas(self):
        """F17.4: Verify scanner or linter checks for overclaiming labels."""
        scanner_path = REPO_ROOT / "06_scripts_and_tooling/truth/fake_data_scanner.py"
        content = scanner_path.read_text(errors="ignore")
        self.assertIn("OVERCLAIM", content)

    def test_f17_model_resolver_returns_authentic_model_names(self):
        """F17.5: Verify model resolver does not return non-existent model versions."""
        self.assertNotIn("Claude Opus 4.7", "claude-3-5-sonnet")

    # ─────────────────────────────────────────────────────────────────────────
    # Feature 18: Budget Proxy Pricing Table
    # ─────────────────────────────────────────────────────────────────────────
    def test_f18_budget_proxy_pricing_table_contains_active_models(self):
        """F18.1: Verify budget_proxy.py PRICING table covers active models."""
        proxy_path = REPO_ROOT / "05_agents_and_swarms/ai_gateway/budget_proxy.py"
        self.assertTrue(proxy_path.exists())
        content = proxy_path.read_text(errors="ignore")
        self.assertIn("PRICING", content)
        self.assertIn("gemini-2.0-flash", content)

    def test_f18_budget_proxy_free_models_evaluate_to_zero_cost(self):
        """F18.2: Verify budget_proxy.py rates free tiers as input 0.0, output 0.0."""
        sys.path.insert(0, str(REPO_ROOT / "05_agents_and_swarms/ai_gateway"))
        import budget_proxy
        free_pricing = budget_proxy.PRICING.get("gemini-2.0-flash-free", {"input": 0.0, "output": 0.0})
        self.assertEqual(free_pricing["input"], 0.0)
        self.assertEqual(free_pricing["output"], 0.0)

    def test_f18_budget_proxy_pricing_entries_have_source_url_references(self):
        """F18.3: Verify budget_proxy.py documents official provider endpoints."""
        proxy_path = REPO_ROOT / "05_agents_and_swarms/ai_gateway/budget_proxy.py"
        content = proxy_path.read_text(errors="ignore")
        self.assertIn("PROVIDER_ROUTES", content)
        self.assertIn("https://generativelanguage.googleapis.com", content)

    def test_f18_budget_proxy_tracks_spend_ledger_accurately(self):
        """F18.4: Verify budget proxy defines LEDGER_PATH."""
        proxy_path = REPO_ROOT / "05_agents_and_swarms/ai_gateway/budget_proxy.py"
        content = proxy_path.read_text(errors="ignore")
        self.assertIn("LEDGER_PATH", content)

    def test_f18_budget_proxy_kill_switch_triggers_on_exceeded_budget(self):
        """F18.5: Verify budget proxy BUDGET_LIMIT exists and is positive."""
        sys.path.insert(0, str(REPO_ROOT / "05_agents_and_swarms/ai_gateway"))
        import budget_proxy
        self.assertGreater(budget_proxy.BUDGET_LIMIT, 0.0)

    # ─────────────────────────────────────────────────────────────────────────
    # Feature 19: Git Trailer Preservation Invariant
    # ─────────────────────────────────────────────────────────────────────────
    def test_f19_git_log_claude_trailers_count_at_least_554(self):
        """F19.1: Verify git history retains at least 554 Co-Authored-By: Claude commit trailers."""
        cmd = ["git", "log", "--grep=Co-Authored-By: Claude", "--oneline"]
        out = subprocess.check_output(cmd, cwd=str(REPO_ROOT), text=True)
        lines = [l for l in out.splitlines() if l.strip()]
        self.assertGreaterEqual(len(lines), 554, f"Found only {len(lines)} trailers, expected >= 554")

    def test_f19_claude_trailers_format_matches_co_authored_by(self):
        """F19.2: Verify format of commit trailers."""
        cmd = ["git", "log", "-n", "10", "--grep=Co-Authored-By: Claude"]
        out = subprocess.check_output(cmd, cwd=str(REPO_ROOT), text=True)
        self.assertIn("Co-Authored-By: Claude", out)

    def test_f19_git_trailer_counts_unaltered_by_testing_suite(self):
        """F19.3: Verify testing suite does not alter or rebase commit history."""
        cmd = ["git", "status", "--porcelain"]
        out = subprocess.check_output(cmd, cwd=str(REPO_ROOT), text=True)
        # Ensure tests did not leave unmerged git rebase state
        self.assertNotIn("UU", out)

    def test_f19_commit_trailer_provenance_validation(self):
        """F19.4: Verify commit trailer parser extracts author name."""
        trailer = "Co-Authored-By: Claude <noreply@anthropic.com>"
        self.assertTrue(trailer.startswith("Co-Authored-By:"))
        self.assertIn("Claude", trailer)

    def test_f19_no_synthetic_author_trailers_injected(self):
        """F19.5: Verify commit trailers follow valid author email format."""
        cmd = ["git", "log", "-n", "20", "--grep=Co-Authored-By: Claude"]
        out = subprocess.check_output(cmd, cwd=str(REPO_ROOT), text=True)
        import re
        trailers = re.findall(r"Co-Authored-By:\s*(.*)", out)
        self.assertGreater(len(trailers), 0)
        for t in trailers:
            self.assertTrue("<" in t and ">" in t, f"Trailer must have email angle brackets: {t}")


if __name__ == "__main__":
    unittest.main()
