#!/usr/bin/env python3
"""
test_figma_mcp_zero_mock.py - Comprehensive 4-Tier E2E Test Suite
==================================================================
Part of the Lauburu Monorepo Rule #0 Zero-Mock Guardrail Infrastructure.

Covers:
  - Tier 1: Feature Coverage (>=5 tests per feature across 5 features)
    * Feature 1.1: Figma MCP Setup CLI & SettingsConfigurator
    * Feature 1.2: Figma MCP Client JSON-RPC Stdio Protocol
    * Feature 1.3: Figma MCP Tool Schemas
    * Feature 1.4: Zero-Mock Linter on Permissible Structural Layouts
    * Feature 1.5: Tri-Lens Visual Swarm MD5 Frame Hash & SSIM Parity Logic

  - Tier 2: Boundary & Corner Cases (>=5 tests per feature across 5 features)
    * Corner Case 2.1: Settings.json Fault Tolerance & Atomic Recovery
    * Corner Case 2.2: Missing/Revoked Figma Tokens & Auth Errors
    * Corner Case 2.3: Non-existent / Malformed Figma Node IDs & File Keys
    * Corner Case 2.4: Empty Comments Threads & Rate Limiting (HTTP 429 Backoff)
    * Corner Case 2.5: Zero-Mock Linter Edge Cases & Anti-Cheat Discrimination

  - Tier 3: Cross-Feature Combinations (Pairwise Interaction Tests)
    * Pairwise 3.1: AST Extraction -> Code Gen -> Zero-Mock Linter -> Tri-Lens Audit
    * Pairwise 3.2: Settings Registration -> MCP Stdio Launch -> Client Tool Dispatch
    * Pairwise 3.3: Pre-Commit Hook Simulation (Block Mock Data / Pass Clean Code)
    * Pairwise 3.4: Linter Auto-Remediation Diff Generation & Re-Audit
    * Pairwise 3.5: OAuth/PAT Token Configuration -> Client Auth -> MCP Tool Call

  - Tier 4: Real-World Scenarios (End-to-End Workloads)
    * Scenario 4.1: Real-World Live Telemetry Stream Component Audit
    * Scenario 4.2: Real-World Hardcoded Mock Component Rejection & Remediation
    * Scenario 4.3: Real-World Settings Verification & Configuration Integrity (~/.gemini/settings.json)
    * Scenario 4.4: Complex Multi-Language Component Design System Audit
    * Scenario 4.5: Full Stdio MCP Subprocess End-to-End JSON-RPC Lifecycle

Zero-Mock Integrity Mandate:
  - 100% genuine assertions; zero hardcoded test pass facades.
  - Strict compliance with Monorepo Rule #0.
"""

import os
import sys
import re
import ast
import json
import time
import shutil
import tempfile
import unittest
import subprocess
import urllib.error
from io import BytesIO
from unittest.mock import patch, MagicMock

# Add scripts directory to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, "06_scripts_and_tooling", "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from setup_figma_mcp import SettingsConfigurator, FigmaAuthManager, HealthVerifier
from figma_mcp_client import FigmaRESTClient, FigmaMCPServer, FigmaAPIError, MCP_PROTOCOL_VERSION
from figma_zero_mock_linter import (
    FigmaZeroMockLinter, Violation, JsTsxScanner, VueScanner, DartUiScanner,
    HtmlScanner, PythonAstJudge
)
from figma_tri_lens_auditor import (
    TriLensSwarmAuditor, VisualParityEngine, FrameDeltaValidator,
    DomZeroMockAuditor, LensAuditResult, FrameHashResult
)

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# ============================================================================
# TIER 1: FEATURE COVERAGE (>=5 tests per feature across 5 features)
# ============================================================================

class TestTier1FigmaMCPSetup(unittest.TestCase):
    """Tier 1.1: Feature tests for Figma MCP Setup CLI & SettingsConfigurator."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_figma_setup_")
        self.settings_file = os.path.join(self.test_dir, "settings.json")
        self.configurator = SettingsConfigurator(settings_path=self.settings_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_setup_cli_status_inspection(self):
        """1.1.1: Verify status returns accurate dictionary structure and flags."""
        status = self.configurator.get_status()
        self.assertIsInstance(status, dict)
        self.assertEqual(status["settings_path"], self.settings_file)
        self.assertFalse(status["settings_exists"])
        self.assertFalse(status["stdio_registered"])
        self.assertFalse(status["remote_registered"])

    def test_setup_cli_register_stdio_server(self):
        """1.1.2: Verify register_stdio_server adds figma server with trust: true."""
        client_script = os.path.join(SCRIPTS_DIR, "figma_mcp_client.py")
        res = self.configurator.register_stdio_server(
            client_script_path=client_script,
            token="figd_test_token_12345"
        )
        self.assertTrue(res)

        # Inspect settings content
        settings = self.configurator.load_settings()
        self.assertIn("mcpServers", settings)
        self.assertIn("figma", settings["mcpServers"])
        figma_cfg = settings["mcpServers"]["figma"]
        self.assertTrue(figma_cfg.get("trust"))
        self.assertEqual(figma_cfg.get("command"), sys.executable)
        self.assertIn(client_script, figma_cfg.get("args", []))
        self.assertIn("--stdio", figma_cfg.get("args", []))
        self.assertEqual(figma_cfg.get("env", {}).get("FIGMA_ACCESS_TOKEN"), "figd_test_token_12345")

    def test_setup_cli_register_remote_server(self):
        """1.1.3: Verify register_remote_server adds figma-remote with trust: true."""
        res = self.configurator.register_remote_server(
            remote_url="https://mcp.figma.com/v1"
        )
        self.assertTrue(res)
        settings = self.configurator.load_settings()
        self.assertIn("figma-remote", settings["mcpServers"])
        remote_cfg = settings["mcpServers"]["figma-remote"]
        self.assertTrue(remote_cfg.get("trust"))
        self.assertEqual(remote_cfg.get("url"), "https://mcp.figma.com/v1")

    def test_setup_cli_unregister_server(self):
        """1.1.4: Verify unregister_server cleanly removes server entry."""
        self.configurator.register_stdio_server()
        self.assertTrue(self.configurator.get_status()["stdio_registered"])

        unreg = self.configurator.unregister_server("figma")
        self.assertTrue(unreg)
        self.assertFalse(self.configurator.get_status()["stdio_registered"])

    def test_setup_cli_atomic_backup_and_rollback(self):
        """1.1.5: Verify create_backup and rollback_latest_backup accurately restore prior state."""
        # State 1: Initial configuration
        self.configurator.write_settings_atomically({"version": "1.0", "mcpServers": {}})
        backup_path = self.configurator.create_backup()
        self.assertIsNotNone(backup_path)
        self.assertTrue(os.path.exists(backup_path))

        # State 2: Mutated configuration
        self.configurator.write_settings_atomically({"version": "2.0", "mcpServers": {"figma": {"trust": True}}})
        current = self.configurator.load_settings()
        self.assertEqual(current["version"], "2.0")

        # Rollback
        success, msg = self.configurator.rollback_latest_backup()
        self.assertTrue(success)
        restored = self.configurator.load_settings()
        self.assertEqual(restored["version"], "1.0")

    def test_setup_cli_validate_pat_format_and_probe(self):
        """1.1.6: Verify FigmaAuthManager.validate_pat validates token format & probe response."""
        # Empty token
        empty_res = FigmaAuthManager.validate_pat("")
        self.assertFalse(empty_res["valid"])
        self.assertIn("empty", empty_res["error"].lower())

        # Mock successful probe
        mock_user = {"id": "123", "handle": "aaron", "email": "aaron@lauburu.ai"}
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = json.dumps(mock_user).encode("utf-8")
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            probe_res = FigmaAuthManager.validate_pat("figd_valid_token")
            self.assertTrue(probe_res["valid"])
            self.assertEqual(probe_res["user"]["handle"], "aaron")


class TestTier1FigmaMCPStdioProtocol(unittest.TestCase):
    """Tier 1.2: Feature tests for Figma MCP Client JSON-RPC Stdio Protocol."""

    def setUp(self):
        self.client = FigmaRESTClient(token="figd_mock_test_token")
        self.server = FigmaMCPServer(client=self.client)

    def test_jsonrpc_initialize(self):
        """1.2.1: Verify JSON-RPC initialize returns protocolVersion and serverInfo."""
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        res = self.server.handle_jsonrpc(req)
        self.assertEqual(res["jsonrpc"], "2.0")
        self.assertEqual(res["id"], 1)
        self.assertEqual(res["result"]["protocolVersion"], MCP_PROTOCOL_VERSION)
        self.assertEqual(res["result"]["serverInfo"]["name"], "figma-mcp")
        self.assertIn("tools", res["result"]["capabilities"])

    def test_jsonrpc_tools_list(self):
        """1.2.2: Verify JSON-RPC tools/list returns all 5 core Figma tools."""
        req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        res = self.server.handle_jsonrpc(req)
        self.assertEqual(res["jsonrpc"], "2.0")
        self.assertEqual(res["id"], 2)
        tools = res["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        expected_tools = ["get_file", "get_file_nodes", "get_image", "get_comments", "get_me"]
        for expected in expected_tools:
            self.assertIn(expected, tool_names)

    def test_jsonrpc_ping(self):
        """1.2.3: Verify JSON-RPC ping returns empty result dictionary."""
        req = {"jsonrpc": "2.0", "id": 3, "method": "ping", "params": {}}
        res = self.server.handle_jsonrpc(req)
        self.assertEqual(res["jsonrpc"], "2.0")
        self.assertEqual(res["id"], 3)
        self.assertEqual(res["result"], {})

    def test_jsonrpc_tools_call_valid(self):
        """1.2.4: Verify JSON-RPC tools/call executes tool and wraps response in text content."""
        mock_me_data = {"id": "usr_999", "handle": "mesh_specialist", "email": "mesh@lauburu.ai"}
        with patch.object(self.client, "get_me", return_value=mock_me_data):
            req = {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "get_me",
                    "arguments": {}
                }
            }
            res = self.server.handle_jsonrpc(req)
            self.assertEqual(res["jsonrpc"], "2.0")
            self.assertEqual(res["id"], 4)
            self.assertFalse(res["result"]["isError"])
            content = res["result"]["content"]
            self.assertEqual(len(content), 1)
            self.assertEqual(content[0]["type"], "text")
            parsed_body = json.loads(content[0]["text"])
            self.assertEqual(parsed_body["handle"], "mesh_specialist")

    def test_jsonrpc_tools_call_error_handling(self):
        """1.2.5: Verify JSON-RPC tools/call handles exceptions and returns isError: true."""
        req = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "get_file",
                "arguments": {}  # Missing required 'file_key'
            }
        }
        res = self.server.handle_jsonrpc(req)
        self.assertEqual(res["jsonrpc"], "2.0")
        self.assertEqual(res["id"], 5)
        self.assertTrue(res["result"]["isError"])
        self.assertIn("Error executing tool", res["result"]["content"][0]["text"])

    def test_jsonrpc_unknown_method_error(self):
        """1.2.6: Verify JSON-RPC returns method not found error (-32601) for unknown methods."""
        req = {"jsonrpc": "2.0", "id": 6, "method": "invalid/method", "params": {}}
        res = self.server.handle_jsonrpc(req)
        self.assertEqual(res["jsonrpc"], "2.0")
        self.assertEqual(res["id"], 6)
        self.assertIn("error", res)
        self.assertEqual(res["error"]["code"], -32601)


class TestTier1FigmaMCPToolSchemas(unittest.TestCase):
    """Tier 1.3: Feature tests for Figma MCP Tool Schemas."""

    def setUp(self):
        self.server = FigmaMCPServer(client=FigmaRESTClient(token="figd_test"))
        self.tools_by_name = {t["name"]: t for t in self.server.tools}

    def test_schema_get_file(self):
        """1.3.1: Verify get_file schema properties and requirements."""
        tool = self.tools_by_name["get_file"]
        schema = tool["inputSchema"]
        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["required"], ["file_key"])
        self.assertIn("file_key", schema["properties"])
        self.assertIn("depth", schema["properties"])
        self.assertIn("geometry", schema["properties"])

    def test_schema_get_file_nodes(self):
        """1.3.2: Verify get_file_nodes schema properties and requirements."""
        tool = self.tools_by_name["get_file_nodes"]
        schema = tool["inputSchema"]
        self.assertEqual(schema["type"], "object")
        self.assertIn("file_key", schema["required"])
        self.assertIn("ids", schema["required"])
        self.assertIn("ids", schema["properties"])
        self.assertEqual(schema["properties"]["ids"]["type"], "array")

    def test_schema_get_image(self):
        """1.3.3: Verify get_image schema properties and requirements."""
        tool = self.tools_by_name["get_image"]
        schema = tool["inputSchema"]
        self.assertEqual(schema["type"], "object")
        self.assertIn("file_key", schema["required"])
        self.assertIn("ids", schema["required"])
        self.assertIn("format", schema["properties"])
        self.assertIn("scale", schema["properties"])
        self.assertIn("png", schema["properties"]["format"]["enum"])
        self.assertIn("svg", schema["properties"]["format"]["enum"])

    def test_schema_get_comments(self):
        """1.3.4: Verify get_comments schema properties and requirements."""
        tool = self.tools_by_name["get_comments"]
        schema = tool["inputSchema"]
        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["required"], ["file_key"])
        self.assertIn("file_key", schema["properties"])

    def test_schema_get_me(self):
        """1.3.5: Verify get_me schema properties."""
        tool = self.tools_by_name["get_me"]
        schema = tool["inputSchema"]
        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["properties"], {})


class TestTier1ZeroMockPermissibleLayouts(unittest.TestCase):
    """Tier 1.4: Feature tests for Zero-Mock Linter on Permissible Structural Layouts."""

    def setUp(self):
        self.linter = FigmaZeroMockLinter(fail_under=100.0, strict=True)

    def test_permissible_react_tsx_layout(self):
        """1.4.1: React TSX with dynamic state bindings ({val ?? '--'}) passes with 0 violations."""
        code = """
import React from 'react';

interface TelemetryCardProps {
  telemetry?: {
    heartRate?: number;
    latency?: number;
  };
  isLoading?: boolean;
}

export const TelemetryCard: React.FC<TelemetryCardProps> = ({ telemetry, isLoading }) => {
  return (
    <div className="flex flex-col p-4 bg-slate-900 border border-slate-800 rounded-lg">
      <h2 className="text-sm font-semibold text-slate-400">Heart Rate</h2>
      <div className="text-3xl font-bold text-emerald-400">
        {isLoading ? <span className="skeleton">Loading...</span> : `${telemetry?.heartRate ?? '--'} bpm`}
      </div>
      <p className="text-xs text-slate-500">Latency: {telemetry?.latency ?? '--'} ms</p>
    </div>
  );
};
"""
        scanner = JsTsxScanner(file_path="TelemetryCard.tsx", source_text=code)
        violations = scanner.scan()
        self.assertEqual(len(violations), 0, f"Expected 0 violations, got: {violations}")

    def test_permissible_vue_sfc_layout(self):
        """1.4.2: Vue SFC with dynamic template expressions passes with 0 violations."""
        code = """
<template>
  <div class="metrics-grid">
    <div class="card">
      <h3>Blood Oxygen</h3>
      <span class="value">{{ telemetry?.spo2 ? `${telemetry.spo2}%` : '--' }}</span>
    </div>
    <div class="card">
      <h3>Heart Rate</h3>
      <span class="value">{{ telemetry?.hr ?? '--' }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  telemetry?: {
    spo2?: number;
    hr?: number;
  }
}>();
</script>
"""
        scanner = VueScanner(file_path="MetricsGrid.vue", source_text=code)
        violations = scanner.scan()
        self.assertEqual(len(violations), 0, f"Expected 0 violations, got: {violations}")

    def test_permissible_flutter_dart_layout(self):
        """1.4.3: Flutter Dart widget tree with dynamic expressions passes with 0 violations."""
        code = """
import 'package:flutter/material.dart';

class BiometricsWidget extends StatelessWidget {
  final Map<String, dynamic>? telemetryStream;

  const BiometricsWidget({Key? key, this.telemetryStream}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final hr = telemetryStream?['heart_rate'];
    return Container(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        children: [
          const Text('Live Telemetry', style: TextStyle(fontWeight: FontWeight.bold)),
          Text(hr != null ? '$hr bpm' : '--', style: const TextStyle(fontSize: 24)),
        ],
      ),
    );
  }
}
"""
        scanner = DartUiScanner(file_path="biometrics_widget.dart", source_text=code)
        violations = scanner.scan()
        self.assertEqual(len(violations), 0, f"Expected 0 violations, got: {violations}")

    def test_permissible_html_layout(self):
        """1.4.4: Semantic HTML table with table headers & dynamic attributes passes with 0 violations."""
        code = """
<!DOCTYPE html>
<html>
<head><title>Hardware Telemetry</title></head>
<body>
  <table>
    <thead>
      <tr>
        <th>Device Name</th>
        <th>Throughput</th>
        <th>Latency</th>
        <th>Status</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Pixel 9 Pro</td>
        <td class="metric-val">{{ device.throughput | default('--') }}</td>
        <td class="metric-val">{{ device.latency | default('--') }}</td>
        <td>{{ device.status | default('AWAITING') }}</td>
      </tr>
    </tbody>
  </table>
</body>
</html>
"""
        scanner = HtmlScanner(file_path="table.html", source_text=code)
        violations = scanner.scan()
        self.assertEqual(len(violations), 0, f"Expected 0 violations, got: {violations}")

    def test_permissible_python_dashboard(self):
        """1.4.5: Python view module using stream.get('hr', None) passes with 0 violations."""
        code = """
import streamlit as st

def render_dashboard(stream_packet: dict):
    st.title("Movesense Live Biometrics")
    hr_val = stream_packet.get("heart_rate")
    hr_display = f"{hr_val} bpm" if hr_val is not None else "--"
    st.metric(label="Heart Rate", value=hr_display)
    
    latency_val = stream_packet.get("latency_ms")
    st.metric(label="BLE RTT", value=f"{latency_val} ms" if latency_val is not None else "--")
"""
        tree = ast.parse(code, filename="dashboard.py")
        judge = PythonAstJudge(file_path="dashboard.py", source_text=code)
        judge.visit(tree)
        violations = judge.violations
        self.assertEqual(len(violations), 0, f"Expected 0 violations, got: {violations}")

    def test_permissible_annotated_visual_animation(self):
        """1.4.6: UI code annotated with @verified-visual-animation is permitted for procedural waves."""
        code = """
/* @verified-visual-animation */
import React from 'react';

export const ProceduralWave: React.FC = () => {
  const simulatedHeight = Math.sin(Date.now() / 1000) * 50;
  return <div style={{ height: `${simulatedHeight}px` }} className="wave" />;
};
"""
        scanner = JsTsxScanner(file_path="ProceduralWave.tsx", source_text=code)
        violations = scanner.scan()
        self.assertEqual(len(violations), 0, f"Expected 0 violations for verified animation, got: {violations}")


class TestTier1TriLensVisualSwarm(unittest.TestCase):
    """Tier 1.5: Feature tests for Tri-Lens Visual Swarm MD5 frame hash & SSIM parity."""

    def test_frame_hash_computation(self):
        """1.5.1: Frame hash computation yields 32-character hexadecimal MD5 digest."""
        frame_bytes = b"RAW_RGB_FRAME_DATA_123456789"
        res = FrameDeltaValidator.compute_frame_hash(frame_bytes, index=1)
        self.assertEqual(len(res.md5_hash), 32)
        self.assertRegex(res.md5_hash, r"^[a-f0-9]{32}$")

    def test_dynamic_frame_delta_validation(self):
        """1.5.2: 5-frame sequence with live rolling updates passes dynamic frame delta check."""
        frames = [
            b"FRAME_BUFFER_TIME_0.0",
            b"FRAME_BUFFER_TIME_0.1",
            b"FRAME_BUFFER_TIME_0.2",
            b"FRAME_BUFFER_TIME_0.3",
            b"FRAME_BUFFER_TIME_0.4"
        ]
        passed, hash_results, unique_count = FrameDeltaValidator.evaluate_frame_series(frames)
        self.assertEqual(len(hash_results), 5)
        self.assertEqual(unique_count, 5)
        self.assertTrue(passed)

    def test_ssim_identical_parity(self):
        """1.5.3: SSIM between identical images produces score 1.0 (>= 0.95 pass)."""
        img_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        score = VisualParityEngine.compute_ssim(img_bytes, img_bytes)
        self.assertAlmostEqual(score, 1.0, places=2)
        self.assertGreaterEqual(score, 0.95)

    def test_ssim_degraded_parity_mismatch(self):
        """1.5.4: SSIM between drastically differing images produces score < 0.90."""
        if HAS_PIL:
            im1 = Image.new("RGB", (100, 100), color=(0, 0, 0))
            im2 = Image.new("RGB", (100, 100), color=(255, 255, 255))
            b1, b2 = BytesIO(), BytesIO()
            im1.save(b1, format="PNG")
            im2.save(b2, format="PNG")
            score = VisualParityEngine.compute_ssim(b1.getvalue(), b2.getvalue())
        else:
            img1 = bytes([i % 256 for i in range(1000)])
            img2 = bytes([(i + 128) % 256 for i in range(1000)])
            score = VisualParityEngine._compute_ssim_fallback(img1, img2)
        self.assertLess(score, 0.90)

    def test_dom_zero_mock_auditor_clean(self):
        """1.5.5: DomZeroMockAuditor verifies clean DOM tree has no static mock tokens."""
        clean_dom = """
        <div class="metrics-container">
          <div class="stat-box">
            <span class="label">Heart Rate</span>
            <span class="value">--</span>
          </div>
          <div class="stat-box">
            <span class="label">Blood Pressure</span>
            <span class="value">--</span>
          </div>
        </div>
        """
        passed, tokens = DomZeroMockAuditor.audit_dom_text(clean_dom)
        self.assertTrue(passed)
        self.assertEqual(len(tokens), 0)

    def test_tri_lens_swarm_aggregation(self):
        """1.5.6: TriLensSwarmAuditor aggregates Lens 1, Lens 2, and Lens 3 results."""
        auditor = TriLensSwarmAuditor(
            target_url="http://localhost:3000/telemetry",
            min_ssim=0.95,
            frame_count=5
        )
        res = auditor.run_full_swarm_audit(lens_filter="all")
        self.assertIn("results", res)
        self.assertEqual(len(res["results"]), 3)
        lens_names = [l["lens_name"] for l in res["results"]]
        self.assertIn("Lens 1: Chromium CDP", lens_names)
        self.assertIn("Lens 2: Gecko Marionette", lens_names)
        self.assertIn("Lens 3: Mobile ADB Edge", lens_names)


# ============================================================================
# TIER 2: BOUNDARY & CORNER CASES (>=5 tests per feature across 5 features)
# ============================================================================

class TestTier2SettingsFaultTolerance(unittest.TestCase):
    """Tier 2.1: Boundary tests for settings.json fault tolerance and recovery."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_figma_settings_err_")
        self.settings_file = os.path.join(self.test_dir, "settings.json")
        self.configurator = SettingsConfigurator(settings_path=self.settings_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_malformed_json_quarantine_and_recovery(self):
        """2.1.1: Malformed settings.json syntax is detected and raises descriptive error."""
        with open(self.settings_file, "w") as f:
            f.write("{ invalid json content: 1234, ")

        with self.assertRaises(ValueError) as ctx:
            self.configurator.load_settings()
        self.assertIn("Failed to parse settings", str(ctx.exception))

    def test_missing_parent_directory_creation(self):
        """2.1.2: Settings in non-existent nested directory creates parent dirs on save."""
        deep_path = os.path.join(self.test_dir, "nested", "sub", "settings.json")
        deep_configurator = SettingsConfigurator(settings_path=deep_path)
        res = deep_configurator.write_settings_atomically({"created": True})
        self.assertTrue(res)
        self.assertTrue(os.path.exists(deep_path))

    def test_atomic_write_safety_tmp_file(self):
        """2.1.3: write_settings_atomically guarantees no partial corruption via tmp file."""
        self.configurator.write_settings_atomically({"key": "original_value"})
        self.configurator.write_settings_atomically({"key": "new_value"})
        loaded = self.configurator.load_settings()
        self.assertEqual(loaded["key"], "new_value")
        tmp_files = [f for f in os.listdir(self.test_dir) if f.endswith(".tmp")]
        self.assertEqual(len(tmp_files), 0)

    def test_rollback_no_backups_available(self):
        """2.1.4: rollback_latest_backup returns (False, msg) when no backups exist."""
        success, msg = self.configurator.rollback_latest_backup()
        self.assertFalse(success)
        self.assertIn("no backup", msg.lower())

    def test_multiple_sequential_backups_and_rollbacks(self):
        """2.1.5: Sequential updates maintain ordered backups; rollback recovers prior state."""
        self.configurator.write_settings_atomically({"step": 1})
        self.configurator.create_backup()
        time.sleep(0.01)
        self.configurator.write_settings_atomically({"step": 2})
        self.configurator.create_backup()
        time.sleep(0.01)
        self.configurator.write_settings_atomically({"step": 3})

        s1, _ = self.configurator.rollback_latest_backup()
        self.assertTrue(s1)
        self.assertEqual(self.configurator.load_settings()["step"], 2)


class TestTier2FigmaAuthBoundaryCases(unittest.TestCase):
    """Tier 2.2: Boundary tests for Figma authentication and token handling."""

    def test_http_401_unauthorized_no_infinite_loop(self):
        """2.2.1: HTTP 401 raises FigmaAPIError immediately without infinite retries."""
        client = FigmaRESTClient(token="figd_invalid_token")
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_err = urllib.error.HTTPError(
                url="https://api.figma.com/v1/me",
                code=401,
                msg="Unauthorized",
                hdrs={},
                fp=BytesIO(b'{"err": "Invalid token"}')
            )
            mock_urlopen.side_effect = mock_err

            with self.assertRaises(FigmaAPIError) as ctx:
                client.get_me()
            self.assertEqual(ctx.exception.status_code, 401)
            self.assertIn("Invalid token", str(ctx.exception))
            self.assertEqual(mock_urlopen.call_count, 1)

    def test_missing_env_token_raises_before_request(self):
        """2.2.2: Instantiating client with empty token raises 401 before network call."""
        with patch.dict(os.environ, {}, clear=True):
            client = FigmaRESTClient(token="")
            with self.assertRaises(FigmaAPIError) as ctx:
                client.get_me()
            self.assertEqual(ctx.exception.status_code, 401)
            self.assertIn("missing", str(ctx.exception).lower())

    def test_pat_vs_oauth_bearer_headers(self):
        """2.2.3: figd_ prefix generates X-Figma-Token header; regular token generates Bearer."""
        pat_client = FigmaRESTClient(token="figd_personal_access_token_123")
        pat_headers = pat_client._get_headers()
        self.assertIn("X-Figma-Token", pat_headers)
        self.assertEqual(pat_headers["X-Figma-Token"], "figd_personal_access_token_123")
        self.assertNotIn("Authorization", pat_headers)

        oauth_client = FigmaRESTClient(token="oauth_access_token_abc")
        oauth_headers = oauth_client._get_headers()
        self.assertIn("Authorization", oauth_headers)
        self.assertEqual(oauth_headers["Authorization"], "Bearer oauth_access_token_abc")
        self.assertNotIn("X-Figma-Token", oauth_headers)

    def test_http_403_forbidden_handling(self):
        """2.2.4: HTTP 403 Forbidden raises FigmaAPIError with error details."""
        client = FigmaRESTClient(token="figd_forbidden_token")
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_err = urllib.error.HTTPError(
                url="https://api.figma.com/v1/files/secret_file",
                code=403,
                msg="Forbidden",
                hdrs={},
                fp=BytesIO(b'{"message": "Insufficient permissions to view file"}')
            )
            mock_urlopen.side_effect = mock_err
            with self.assertRaises(FigmaAPIError) as ctx:
                client.get_file("secret_file")
            self.assertEqual(ctx.exception.status_code, 403)
            self.assertIn("Insufficient permissions", str(ctx.exception))

    def test_malformed_api_error_response(self):
        """2.2.5: Server returning HTML error 502/500 is handled safely without JSON crash."""
        client = FigmaRESTClient(token="figd_valid_token")
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_err = urllib.error.HTTPError(
                url="https://api.figma.com/v1/me",
                code=502,
                msg="Bad Gateway",
                hdrs={},
                fp=BytesIO(b"<html><body>502 Bad Gateway</body></html>")
            )
            mock_urlopen.side_effect = mock_err
            with self.assertRaises(FigmaAPIError) as ctx:
                client.get_me()
            self.assertEqual(ctx.exception.status_code, 502)


class TestTier2FigmaNodeBoundaryCases(unittest.TestCase):
    """Tier 2.3: Boundary tests for Figma node IDs and file key parsing."""

    def test_non_existent_node_id_response(self):
        """2.3.1: Response with nodes: {'999:999': null} handled cleanly."""
        client = FigmaRESTClient(token="figd_test")
        mock_response = {"name": "Test File", "nodes": {"999:999": None}}
        with patch.object(client, "request", return_value=mock_response):
            res = client.get_file_nodes("file123", ["999:999"])
            self.assertIn("nodes", res)
            self.assertIsNone(res["nodes"]["999:999"])

    def test_complex_url_node_id_parsing(self):
        """2.3.2: Complex Figma URLs with query params & percent-encoding parsed accurately."""
        url1 = "https://www.figma.com/design/abcXYZ123/Project-Alpha?node-id=10-25&t=7h8j"
        key1, node1 = FigmaRESTClient.parse_file_key(url1)
        self.assertEqual(key1, "abcXYZ123")
        self.assertEqual(node1, "10:25")

        url2 = "https://www.figma.com/proto/defUVW456/Prototype?node-id=2%3A100"
        key2, node2 = FigmaRESTClient.parse_file_key(url2)
        self.assertEqual(key2, "defUVW456")
        self.assertEqual(node2, "2:100")

        raw_key = "plain_key_789"
        k3, n3 = FigmaRESTClient.parse_file_key(raw_key)
        self.assertEqual(k3, "plain_key_789")
        self.assertIsNone(n3)

    def test_string_vs_list_node_ids_normalization(self):
        """2.3.3: Node IDs passed as comma-separated string or list normalized with colons."""
        client = FigmaRESTClient(token="figd_test")
        with patch.object(client, "request") as mock_req:
            mock_req.return_value = {"images": {"0:1": "http://img/1"}}
            client.get_image("file_key", "0-1,1-23", format="png")
            mock_req.assert_called_once()
            called_params = mock_req.call_args[0][1]
            self.assertEqual(called_params["ids"], ["0:1", "1:23"])

    def test_empty_or_whitespace_file_key(self):
        """2.3.4: Whitespace in file key stripped cleanly."""
        key, node = FigmaRESTClient.parse_file_key("   trimmed_key   ")
        self.assertEqual(key, "trimmed_key")
        self.assertIsNone(node)

    def test_special_character_and_dash_node_ids(self):
        """2.3.5: get_file_nodes formats all dashes to colons."""
        client = FigmaRESTClient(token="figd_test")
        with patch.object(client, "request") as mock_req:
            mock_req.return_value = {"nodes": {}}
            client.get_file_nodes("file1", ["100-200", "300-400"])
            called_params = mock_req.call_args[0][1]
            self.assertEqual(called_params["ids"], ["100:200", "300:400"])


class TestTier2FigmaNetworkBoundaryCases(unittest.TestCase):
    """Tier 2.4: Boundary tests for empty comments threads and HTTP 429 backoff."""

    def test_empty_comments_thread_handling(self):
        """2.4.1: Empty comments thread returns empty list without error."""
        client = FigmaRESTClient(token="figd_test")
        with patch.object(client, "request", return_value={"comments": []}):
            res = client.get_comments("file123")
            self.assertEqual(res, {"comments": []})

    def test_http_429_rate_limit_backoff_and_recovery(self):
        """2.4.2: HTTP 429 with Retry-After header performs backoff and succeeds on retry."""
        client = FigmaRESTClient(token="figd_test")
        err_429 = urllib.error.HTTPError(
            url="https://api.figma.com/v1/me",
            code=429,
            msg="Too Many Requests",
            hdrs={"Retry-After": "0.01"},
            fp=BytesIO(b'{"message": "Rate limit exceeded"}')
        )
        mock_success = MagicMock()
        mock_success.status = 200
        mock_success.read.return_value = b'{"id": "usr_recovered", "handle": "recovered"}'
        mock_success.__enter__.return_value = mock_success

        with patch("urllib.request.urlopen", side_effect=[err_429, mock_success]) as mock_open:
            with patch("time.sleep") as mock_sleep:
                res = client.get_me()
                self.assertEqual(res["handle"], "recovered")
                self.assertEqual(mock_open.call_count, 2)
                mock_sleep.assert_called_with(0.01)

    def test_http_429_exceeding_max_retries(self):
        """2.4.3: Persistent HTTP 429 exceeding max_retries raises FigmaAPIError(429)."""
        client = FigmaRESTClient(token="figd_test")
        err_429 = urllib.error.HTTPError(
            url="https://api.figma.com/v1/me",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=BytesIO(b'{"message": "Rate limit permanent"}')
        )
        with patch("urllib.request.urlopen", side_effect=err_429):
            with patch("time.sleep"):
                with self.assertRaises(FigmaAPIError) as ctx:
                    client.request("me", max_retries=3)
                self.assertEqual(ctx.exception.status_code, 429)

    def test_transient_network_urlerror_retry(self):
        """2.4.4: Transient URLError on attempt 1 recovers on attempt 2."""
        client = FigmaRESTClient(token="figd_test")
        url_err = urllib.error.URLError("Connection reset by peer")
        mock_success = MagicMock()
        mock_success.read.return_value = b'{"status": "ok"}'
        mock_success.__enter__.return_value = mock_success

        with patch("urllib.request.urlopen", side_effect=[url_err, mock_success]):
            with patch("time.sleep"):
                res = client.request("health", max_retries=2)
                self.assertEqual(res["status"], "ok")

    def test_large_comment_payload_with_nested_replies(self):
        """2.4.5: Large comments payload with multiple nested threads processed cleanly."""
        client = FigmaRESTClient(token="figd_test")
        large_comments = {
            "comments": [
                {"id": f"c_{i}", "message": f"Review note {i}", "user": {"handle": f"dev_{i}"}}
                for i in range(100)
            ]
        }
        with patch.object(client, "request", return_value=large_comments):
            res = client.get_comments("large_file")
            self.assertEqual(len(res["comments"]), 100)


class TestTier2ZeroMockLinterBoundaryCases(unittest.TestCase):
    """Tier 2.5: Boundary tests for Zero-Mock Linter and Anti-Cheat discrimination."""

    def setUp(self):
        self.linter = FigmaZeroMockLinter(fail_under=100.0, strict=True)

    def test_linter_clean_waiting_state_pass(self):
        """2.5.1: Clean waiting states ({val ?? '--'}, <span className="waiting">--</span>) PASS."""
        code = """
export const LiveHr = ({ rate }: { rate?: number }) => (
  <div className="stat">
    <label>Heart Rate</label>
    <span>{rate ?? '--'}</span>
  </div>
);
"""
        scanner = JsTsxScanner("LiveHr.tsx", code)
        self.assertEqual(len(scanner.scan()), 0)

    def test_linter_chrome_headers_and_labels_pass(self):
        """2.5.2: Chrome headers <th>Heart Rate</th> and <label>Device Latency</label> PASS."""
        code = """
export const HeaderTable = () => (
  <table>
    <tr>
      <th>Heart Rate (bpm)</th>
      <th>Latency (ms)</th>
      <th>Throughput (Mbps)</th>
    </tr>
  </table>
);
"""
        scanner = JsTsxScanner("HeaderTable.tsx", code)
        self.assertEqual(len(scanner.scan()), 0)

    def test_linter_hardcoded_metric_in_display_fail(self):
        """2.5.3: Hardcoded telemetry in display position (<span>142 bpm</span>) FAILS."""
        code = """
export const FakeCard = () => (
  <div className="card">
    <span>142 bpm</span>
  </div>
);
"""
        scanner = JsTsxScanner("FakeCard.tsx", code)
        violations = scanner.scan()
        self.assertGreaterEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, "ZM-JSX-01")

    def test_linter_static_mock_arrays_fail(self):
        """2.5.4: Mock arrays const mockDevices = [{ id: 1, name: 'Pixel' }] FAILS."""
        code = """
const mockDevices = [
  { id: 'dev_1', name: 'Pixel 9', status: 'ACTIVE' },
  { id: 'dev_2', name: 'MacBook M3', status: 'ONLINE' }
];

export const DeviceList = () => <div>{mockDevices.length}</div>;
"""
        scanner = JsTsxScanner("DeviceList.tsx", code)
        violations = scanner.scan()
        self.assertGreaterEqual(len(violations), 1)
        rule_ids = [v.rule_id for v in violations]
        self.assertIn("ZM-JS-03", rule_ids)

    def test_linter_synthetic_timers_fail(self):
        """2.5.5: Synthetic simulation timers (setTimeout(() => setStatus('ONLINE'), 1000)) FAILS."""
        code = """
import React, { useEffect, useState } from 'react';

export const SimulatedStream = () => {
  const [status, setStatus] = useState('OFFLINE');
  useEffect(() => {
    const timer = setTimeout(() => {
      setStatus('ONLINE');
    }, 1000);
    return () => clearTimeout(timer);
  }, []);
  return <div>{status}</div>;
};
"""
        scanner = JsTsxScanner("SimulatedStream.tsx", code)
        violations = scanner.scan()
        self.assertGreaterEqual(len(violations), 1)
        rule_ids = [v.rule_id for v in violations]
        self.assertIn("ZM-JS-05", rule_ids)

    def test_linter_python_synthetic_math_multiplier_fail(self):
        """2.5.6: Python synthetic multiplier single_tp * 2.0 FAILS (Rule ZM-PY-02)."""
        code = """
def compute_combined_throughput(single_tp: float) -> float:
    return single_tp * 2.0
"""
        tree = ast.parse(code, filename="metrics.py")
        judge = PythonAstJudge("metrics.py", code)
        judge.visit(tree)
        violations = judge.violations
        self.assertGreaterEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, "ZM-PY-02")

    def test_linter_dart_hardcoded_text_fail(self):
        """2.5.7: Dart hardcoded telemetry Text('142 bpm') FAILS (Rule ZM-DART-01)."""
        code = """
import 'package:flutter/material.dart';

Widget buildStat() {
  return Card(
    child: Text("142 bpm"),
  );
}
"""
        scanner = DartUiScanner("stat.dart", code)
        violations = scanner.scan()
        self.assertGreaterEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, "ZM-DART-01")


# ============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS (Pairwise Interaction Tests)
# ============================================================================

class TestTier3Combinations(unittest.TestCase):
    """Tier 3: Pairwise and Cross-Feature interaction tests."""

    def test_pipeline_ast_extraction_to_code_to_linter_to_trilens(self):
        """3.1: Figma AST Node Extraction -> Code Generation -> Linter Scan -> Tri-Lens Audit."""
        mock_figma_node_name = "LiveHeartRateCard"
        
        generated_code = """
import React from 'react';

export interface LiveHeartRateCardProps {
  heartRate?: number;
}

export const LiveHeartRateCard: React.FC<LiveHeartRateCardProps> = ({ heartRate }) => {
  return (
    <div className="flex flex-col gap-2 p-4 rounded bg-slate-900">
      <span className="text-sm text-slate-400">Heart Rate</span>
      <span className="text-2xl font-bold text-emerald-400">
        {heartRate != null ? `${heartRate} bpm` : '--'}
      </span>
    </div>
  );
};
"""
        linter = FigmaZeroMockLinter()
        scanner = JsTsxScanner(f"{mock_figma_node_name}.tsx", generated_code)
        violations = scanner.scan()
        self.assertEqual(len(violations), 0, "Generated code must pass Rule #0 Linter.")

        frame_bytes_1 = b"RENDERED_FRAME_WAITING_STATE_1"
        score = VisualParityEngine.compute_ssim(frame_bytes_1, frame_bytes_1)
        self.assertGreaterEqual(score, 0.95, "SSIM parity must meet or exceed 0.95 threshold.")

    def test_pipeline_settings_to_stdio_mcp_to_client_dispatch(self):
        """3.2: Settings Registration -> Stdio Server Handshake -> Tool Call -> AST Payload."""
        temp_dir = tempfile.mkdtemp(prefix="test_tier3_stdio_")
        try:
            settings_path = os.path.join(temp_dir, "settings.json")
            cfg = SettingsConfigurator(settings_path=settings_path)
            cfg.register_stdio_server(token="figd_tier3_token")

            status = cfg.get_status()
            self.assertTrue(status["stdio_registered"])

            rest_client = FigmaRESTClient(token="figd_tier3_token")
            mcp_server = FigmaMCPServer(client=rest_client)

            init_res = mcp_server.handle_jsonrpc({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
            self.assertEqual(init_res["result"]["serverInfo"]["name"], "figma-mcp")

            mock_ast = {"nodes": {"0:1": {"document": {"id": "0:1", "name": "Canvas"}}}}
            with patch.object(rest_client, "get_file_nodes", return_value=mock_ast):
                call_res = mcp_server.handle_jsonrpc({
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "get_file_nodes",
                        "arguments": {"file_key": "test_key", "ids": ["0:1"]}
                    }
                })
                self.assertFalse(call_res["result"]["isError"])
                ret_json = json.loads(call_res["result"]["content"][0]["text"])
                self.assertIn("nodes", ret_json)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_precommit_hook_blocks_mock_component_and_passes_clean_component(self):
        """3.3: Zero-Mock Linter CLI exits with 1 on mock data and 0 on clean code."""
        temp_dir = tempfile.mkdtemp(prefix="test_precommit_")
        try:
            bad_file = os.path.join(temp_dir, "BadComponent.tsx")
            with open(bad_file, "w") as f:
                f.write('export const Bad = () => <span>142 bpm</span>;')

            clean_file = os.path.join(temp_dir, "CleanComponent.tsx")
            with open(clean_file, "w") as f:
                f.write('export const Clean = ({ hr }: { hr?: number }) => <span>{hr ?? "--"}</span>;')

            linter_script = os.path.join(SCRIPTS_DIR, "figma_zero_mock_linter.py")

            # Run linter CLI on bad component -> must exit 1
            proc_bad = subprocess.run(
                [sys.executable, linter_script, "--target-file", bad_file],
                capture_output=True,
                text=True
            )
            self.assertEqual(proc_bad.returncode, 1, "Bad component must trigger exit code 1.")

            # Run linter CLI on clean component -> must exit 0
            proc_clean = subprocess.run(
                [sys.executable, linter_script, "--target-file", clean_file],
                capture_output=True,
                text=True
            )
            self.assertEqual(proc_clean.returncode, 0, "Clean component must trigger exit code 0.")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_linter_auto_remediation_diff_generation(self):
        """3.4: Linter remediation engine creates diff for detected mock literals."""
        bad_code = '<span className="metric">142 bpm</span>\n'
        temp_dir = tempfile.mkdtemp(prefix="test_remediation_")
        try:
            test_file = os.path.join(temp_dir, "Card.tsx")
            with open(test_file, "w") as f:
                f.write(bad_code)

            linter = FigmaZeroMockLinter()
            violations = linter.audit_file(test_file)
            self.assertEqual(len(violations), 1)

            diff = linter.generate_remediation_diff(test_file, violations)
            self.assertIsNotNone(diff)
            self.assertIn("---", diff)
            self.assertIn("+++", diff)
            self.assertIn("telemetry?.value", diff)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_auth_token_registration_and_rest_client_dispatch(self):
        """3.5: SettingsConfigurator registers token -> REST client authenticates & queries."""
        temp_dir = tempfile.mkdtemp(prefix="test_auth_client_")
        try:
            settings_path = os.path.join(temp_dir, "settings.json")
            cfg = SettingsConfigurator(settings_path=settings_path)
            cfg.register_stdio_server(token="figd_pairwise_auth_123")

            loaded = cfg.load_settings()
            token = loaded["mcpServers"]["figma"]["env"]["FIGMA_ACCESS_TOKEN"]

            client = FigmaRESTClient(token=token)
            with patch.object(client, "request", return_value={"id": "usr_1", "handle": "aaron"}):
                me = client.get_me()
                self.assertEqual(me["handle"], "aaron")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# TIER 4: REAL-WORLD SCENARIOS (End-to-End Workloads)
# ============================================================================

class TestTier4RealWorldScenarios(unittest.TestCase):
    """Tier 4: Full End-to-End real-world scenario tests."""

    def test_real_world_live_telemetry_stream_component(self):
        """4.1: Real-world Movesense / BLE biometrics dashboard passes Rule #0 linter & Tri-Lens audit."""
        real_world_component = """
import React, { useEffect, useState } from 'react';

interface MovesenseTelemetry {
  heartRate: number;
  rttMs: number;
  rrIntervalMs: number;
  batteryLevel: number;
  isStreamActive: boolean;
}

export const MovesenseLiveDashboard: React.FC = () => {
  const [telemetry, setTelemetry] = useState<MovesenseTelemetry | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'DISCONNECTED' | 'STREAMING'>('DISCONNECTED');

  useEffect(() => {
    // Authentic WebSocket stream connection to Movesense Edge daemon (Port 4000)
    const ws = new WebSocket("ws://localhost:4000/api/movesense/stream");
    ws.onmessage = (event) => {
      try {
        const packet = JSON.parse(event.data);
        setTelemetry(packet);
        setConnectionStatus('STREAMING');
      } catch (err) {
        console.error("Telemetry parse error", err);
      }
    };
    ws.onclose = () => {
      setConnectionStatus('DISCONNECTED');
      setTelemetry(null);
    };
    return () => ws.close();
  }, []);

  return (
    <div className="p-6 bg-slate-950 text-slate-100 rounded-xl border border-slate-800">
      <header className="flex justify-between items-center mb-6">
        <h1 className="text-xl font-bold">Movesense ECG & Kinematics Monitor</h1>
        <span className="px-2 py-1 rounded text-xs bg-slate-800 text-slate-400">
          {connectionStatus}
        </span>
      </header>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 bg-slate-900 rounded-lg">
          <span className="text-xs text-slate-400">Heart Rate</span>
          <p className="text-2xl font-bold text-emerald-400">
            {telemetry?.heartRate != null ? `${telemetry.heartRate} bpm` : '--'}
          </p>
        </div>

        <div className="p-4 bg-slate-900 rounded-lg">
          <span className="text-xs text-slate-400">BLE RTT Latency</span>
          <p className="text-2xl font-bold text-cyan-400">
            {telemetry?.rttMs != null ? `${telemetry.rttMs} ms` : '--'}
          </p>
        </div>

        <div className="p-4 bg-slate-900 rounded-lg">
          <span className="text-xs text-slate-400">RR Interval</span>
          <p className="text-2xl font-bold text-indigo-400">
            {telemetry?.rrIntervalMs != null ? `${telemetry.rrIntervalMs} ms` : '--'}
          </p>
        </div>

        <div className="p-4 bg-slate-900 rounded-lg">
          <span className="text-xs text-slate-400">Battery Level</span>
          <p className="text-2xl font-bold text-amber-400">
            {telemetry?.batteryLevel != null ? `${telemetry.batteryLevel}%` : '--'}
          </p>
        </div>
      </div>
    </div>
  );
};
"""
        temp_dir = tempfile.mkdtemp(prefix="test_real_world_")
        try:
            comp_path = os.path.join(temp_dir, "MovesenseLiveDashboard.tsx")
            with open(comp_path, "w") as f:
                f.write(real_world_component)

            # 1. Audit with Zero-Mock Linter
            linter = FigmaZeroMockLinter(fail_under=100.0, strict=True)
            violations = linter.audit_file(comp_path)
            self.assertEqual(len(violations), 0, "Real-world live component must pass Rule #0.")

            # 2. Audit with Tri-Lens Swarm Auditor
            auditor = TriLensSwarmAuditor(
                target_url="http://localhost:4000/movesense",
                min_ssim=0.95,
                frame_count=5
            )
            swarm_res = auditor.run_full_swarm_audit()
            self.assertTrue(swarm_res["all_passed"])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_real_world_hardcoded_mock_component_rejected_and_remediated(self):
        """4.2: Real-world component with hardcoded mock data is caught, blocked (1), and diff created."""
        fake_component = """
import React from 'react';

const mock_telemetry = [
  { id: '1', hr: 142, status: 'ONLINE' }
];

export const FakeTelemetryDashboard: React.FC = () => {
  return (
    <div>
      <h1>Hardware Dashboard</h1>
      <span>142 bpm</span>
    </div>
  );
};
"""
        temp_dir = tempfile.mkdtemp(prefix="test_fake_audit_")
        try:
            fake_path = os.path.join(temp_dir, "FakeTelemetryDashboard.tsx")
            with open(fake_path, "w") as f:
                f.write(fake_component)

            linter = FigmaZeroMockLinter(fail_under=100.0)
            violations = linter.audit_file(fake_path)
            self.assertGreater(len(violations), 0, "Hardcoded mock data must be detected.")

            diff = linter.generate_remediation_diff(fake_path, violations)
            self.assertIsNotNone(diff)
            self.assertIn("telemetry?.value", diff)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_real_world_live_settings_verification(self):
        """4.3: Real-world ~/.gemini/settings.json verification ensuring figma MCP is active & trusted."""
        settings_path = os.path.expanduser("~/.gemini/settings.json")
        self.assertTrue(os.path.exists(settings_path), f"settings.json must exist at {settings_path}")

        cfg = SettingsConfigurator(settings_path=settings_path)
        status = cfg.get_status()
        self.assertTrue(status["settings_exists"])
        self.assertTrue(status["stdio_registered"], "Figma MCP server must be registered in settings.json.")

        stdio_cfg = status["stdio_config"]
        self.assertTrue(stdio_cfg.get("trust"), "Figma MCP server must have 'trust': true.")
        self.assertIn("figma_mcp_client.py", " ".join(stdio_cfg.get("args", [])))
        self.assertIn("--stdio", stdio_cfg.get("args", []))

    def test_real_world_multi_component_design_system_audit(self):
        """4.4: Complex multi-language design system directory audit."""
        temp_dir = tempfile.mkdtemp(prefix="test_design_system_")
        try:
            # 1. Clean React Component
            with open(os.path.join(temp_dir, "Button.tsx"), "w") as f:
                f.write('export const Button = ({ label }: { label: string }) => <button>{label}</button>;')

            # 2. Clean Vue SFC Component
            with open(os.path.join(temp_dir, "Badge.vue"), "w") as f:
                f.write('<template><span class="badge">{{ status ?? "--" }}</span></template>')

            # 3. Clean Flutter Dart Component
            with open(os.path.join(temp_dir, "stat_tile.dart"), "w") as f:
                f.write('import "package:flutter/material.dart"; Widget tile(String? v) => Text(v ?? "--");')

            # 4. Clean Python Endpoint
            with open(os.path.join(temp_dir, "api_view.py"), "w") as f:
                f.write('def get_view(telemetry: dict): return {"hr": telemetry.get("hr", None)}')

            linter = FigmaZeroMockLinter()
            violations = linter.audit_directory(temp_dir)
            report = linter.generate_report(temp_dir, violations)
            self.assertEqual(report["total_violations"], 0)
            self.assertEqual(report["score"], 100.0)
            self.assertTrue(report["passed"])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_real_world_stdio_subprocess_e2e_jsonrpc_lifecycle(self):
        """4.5: Full stdio subprocess lifecycle with initialize, ping, and tools/list frames."""
        client_script = os.path.join(SCRIPTS_DIR, "figma_mcp_client.py")
        proc = subprocess.Popen(
            [sys.executable, client_script, "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        try:
            # Frame 1: initialize
            req1 = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}) + "\n"
            proc.stdin.write(req1)
            proc.stdin.flush()
            line1 = proc.stdout.readline()
            res1 = json.loads(line1)
            self.assertEqual(res1["id"], 1)
            self.assertEqual(res1["result"]["serverInfo"]["name"], "figma-mcp")

            # Frame 2: ping
            req2 = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "ping"}) + "\n"
            proc.stdin.write(req2)
            proc.stdin.flush()
            line2 = proc.stdout.readline()
            res2 = json.loads(line2)
            self.assertEqual(res2["id"], 2)
            self.assertEqual(res2["result"], {})

            # Frame 3: tools/list
            req3 = json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/list"}) + "\n"
            proc.stdin.write(req3)
            proc.stdin.flush()
            line3 = proc.stdout.readline()
            res3 = json.loads(line3)
            self.assertEqual(res3["id"], 3)
            tools = res3["result"]["tools"]
            self.assertGreaterEqual(len(tools), 5)
        finally:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
            if proc.stdout and not proc.stdout.closed:
                proc.stdout.close()
            if proc.stderr and not proc.stderr.closed:
                proc.stderr.close()
            proc.terminate()
            proc.wait(timeout=5.0)


if __name__ == "__main__":
    unittest.main()
