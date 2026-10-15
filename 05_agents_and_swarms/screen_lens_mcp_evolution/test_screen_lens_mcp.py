#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Comprehensive Zero-Mock Test Suite for Screen Lens MCP Evolution (Hardened v2)
================================================================================
Subsystem: 05_agents_and_swarms/screen_lens_mcp_evolution/test_screen_lens_mcp.py
Version: 2.0.0-HARDENED-ZERO-MOCK
Lauburu Mesh Ecosystem — 2026

Tests:
1. MCP Protocol Handshake & Tool Discovery (`initialize`, `tools/list`)
2. Tool Execution: `capture_ui_graph` (XML/compact node parsing & bounding boxes)
3. Tool Execution: `inject_touch_event` (Zero-mock physical vs unattached hardware states)
4. Tool Execution: `screen_lens_infer` (Edge local execution vs Host prima.cpp offload)
5. Tool Execution: `get_mesh_telemetry` (Live host RAM syscalls via sysctl/vm_stat)
6. MCP Stdio Pipe Loop (JSON-RPC 2.0 framing over subprocess stdio)
7. Genetic MoE Router Bridge (SSoT ELO loading, payload complexity routing)
8. Neo Vision Model Training Script (Genuine silicon execution, adapter weights on disk)
9. Architecture Debate & Tri-Vault Compliance (`DEBATE_SCREEN_LENS_MCP.md`)
================================================================================
"""

import sys
import os
import json
import time
import subprocess
from pathlib import Path
import unittest

PROJECT_DIR = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_DIR.parents[1]

# Import the modules under test
sys.path.insert(0, str(PROJECT_DIR))
from screen_lens_mcp import ScreenLensMCPServer
from mcp_genetic_router_bridge import MCPGeneticRouterBridge


class TestScreenLensMCPEvolution(unittest.TestCase):

    def setUp(self):
        self.server = ScreenLensMCPServer()
        self.bridge = MCPGeneticRouterBridge()

    # -------------------------------------------------------------------------
    # Test Group 1: MCP Server Protocol & Tool Discovery
    # -------------------------------------------------------------------------

    def test_01_mcp_initialize(self):
        """Verify standard MCP initialize request."""
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"}
            }
        }
        res = self.server.handle_request(req)
        self.assertIsNotNone(res)
        self.assertEqual(res.get("jsonrpc"), "2.0")
        self.assertEqual(res.get("id"), 1)
        result = res.get("result", {})
        self.assertEqual(result.get("serverInfo", {}).get("name"), "screen-lens-mcp")
        self.assertTrue(self.server.initialized)

    def test_02_mcp_tools_list(self):
        """Verify tools/list returns all required tools with schemas."""
        req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        res = self.server.handle_request(req)
        self.assertIsNotNone(res)
        tools = res.get("result", {}).get("tools", [])
        tool_names = [t["name"] for t in tools]
        self.assertIn("capture_ui_graph", tool_names)
        self.assertIn("inject_touch_event", tool_names)
        self.assertIn("screen_lens_infer", tool_names)
        self.assertIn("get_mesh_telemetry", tool_names)

    # -------------------------------------------------------------------------
    # Test Group 2: Tool Execution
    # -------------------------------------------------------------------------

    def test_03_tool_capture_ui_graph(self):
        """Verify capture_ui_graph returns structured nodes and bounding boxes."""
        req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "capture_ui_graph",
                "arguments": {"format": "compact"}
            }
        }
        res = self.server.handle_request(req)
        self.assertFalse(res.get("result", {}).get("isError", True))
        content = json.loads(res["result"]["content"][0]["text"])
        self.assertEqual(content.get("status"), "success")
        self.assertGreater(content.get("node_count", 0), 0)
        self.assertIn("nodes", content)
        first_node = content["nodes"][0]
        self.assertIn("bbox", first_node)
        self.assertIn("clickable", first_node)

    def test_04_tool_inject_touch_event_honest_truth(self):
        """Verify inject_touch_event truthfully reports actuation state per Rule 0."""
        req = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "inject_touch_event",
                "arguments": {"action": "tap", "x": 540, "y": 960}
            }
        }
        res = self.server.handle_request(req)
        self.assertFalse(res.get("result", {}).get("isError", True))
        content = json.loads(res["result"]["content"][0]["text"])
        self.assertEqual(content.get("action"), "tap")
        self.assertEqual(content.get("parameters", {}).get("x"), 540)
        # Per Rule 0, actuation must be either adb_physical_actuated (if connected) or device_unreachable_noop
        self.assertIn(content.get("actuation"), ["adb_physical_actuated", "device_unreachable_noop"])
        if content.get("actuation") == "adb_physical_actuated":
            self.assertTrue(content.get("rule_0_verified"))
        else:
            self.assertFalse(content.get("rule_0_verified"))

    def test_05_tool_screen_lens_infer_edge_execution(self):
        """Verify screen_lens_infer executes locally on Edge TPU when confidence is high."""
        req = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "screen_lens_infer",
                "arguments": {
                    "goal": "Click the Settings Gear",
                    "confidence_threshold": 0.85,
                    "force_host_offload": False
                }
            }
        }
        res = self.server.handle_request(req)
        self.assertFalse(res.get("result", {}).get("isError", True))
        content = json.loads(res["result"]["content"][0]["text"])
        self.assertEqual(content.get("status"), "success")
        self.assertFalse(content.get("offload_triggered", True))
        self.assertEqual(content.get("backend_used"), "edge_local_tpu")
        self.assertGreaterEqual(content.get("confidence", 0.0), 0.85)

    def test_06_tool_screen_lens_infer_host_offload(self):
        """Verify screen_lens_infer offload logic truthfully attributes backend and coordinates."""
        req = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "screen_lens_infer",
                "arguments": {
                    "goal": "Locate ambiguous custom widget with low initial visual salience",
                    "confidence_threshold": 0.95,
                    "force_host_offload": True
                }
            }
        }
        res = self.server.handle_request(req)
        self.assertFalse(res.get("result", {}).get("isError", True))
        content = json.loads(res["result"]["content"][0]["text"])
        self.assertEqual(content.get("status"), "success")
        self.assertTrue(content.get("offload_triggered", False))
        # Rule 0 & Zero-Mock: When Host Sovereign Engine on Port 8082 is online, host offload must succeed on prima_cpp_8082
        self.assertEqual(content.get("backend_used"), "prima_cpp_8082")
        self.assertTrue(content.get("rule_0_verified"))
        self.assertIn("coordinates", content)
        self.assertIn("x", content["coordinates"])
        self.assertIn("y", content["coordinates"])

    def test_07_tool_get_mesh_telemetry_live_metrics(self):
        """Verify get_mesh_telemetry queries genuine host RAM and reports sanctuary headroom."""
        req = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "get_mesh_telemetry", "arguments": {}}
        }
        res = self.server.handle_request(req)
        self.assertFalse(res.get("result", {}).get("isError", True))
        content = json.loads(res["result"]["content"][0]["text"])
        self.assertIn("nodes", content)
        l1 = content["nodes"]["L1"]
        self.assertGreater(l1["total_physical_ram_gb"], 0)
        self.assertTrue(l1["sanctuary_headroom_preserved"])

    # -------------------------------------------------------------------------
    # Test Group 3: Stdio Subprocess Pipe
    # -------------------------------------------------------------------------

    def test_08_stdio_process_communication(self):
        """Verify screen_lens_mcp.py runs as a real subprocess communicating over stdin/stdout."""
        script_path = PROJECT_DIR / "screen_lens_mcp.py"
        proc = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Send initialize
        init_req = json.dumps({"jsonrpc": "2.0", "id": 101, "method": "initialize", "params": {}}) + "\n"
        proc.stdin.write(init_req)
        proc.stdin.flush()

        stdout_line = proc.stdout.readline()
        res = json.loads(stdout_line.strip())
        self.assertEqual(res.get("id"), 101)
        self.assertEqual(res.get("result", {}).get("serverInfo", {}).get("name"), "screen-lens-mcp")

        # Graceful cleanup
        proc.stdin.close()
        proc.stdout.close()
        proc.stderr.close()
        proc.terminate()
        proc.wait(timeout=2.0)

    # -------------------------------------------------------------------------
    # Test Group 4: Genetic MoE Router Bridge
    # -------------------------------------------------------------------------

    def test_09_genetic_router_elo_and_routing(self):
        """Verify Genetic MoE router routes by payload complexity and ELO."""
        # 1. Vision payload -> Pixel 10 Edge TPU
        v_res = self.bridge.route_payload({
            "task_type": "vision",
            "complexity_score": 0.25,
            "description": "Extract bounding box coordinates of top bar icon"
        })
        self.assertEqual(v_res["routing_decision"]["mcp_id"], "pixel10_edge_mcp")

        # 2. Mobile logic -> Samsung S20 Hermes
        l_res = self.bridge.route_payload({
            "task_type": "logic",
            "complexity_score": 0.45,
            "description": "Dispatch UI scroll action"
        })
        self.assertEqual(l_res["routing_decision"]["mcp_id"], "s20_mobile_mcp")

        # 3. High-complexity -> Mac Mini Host Qwen 3.8 Max (:8082)
        c_res = self.bridge.route_payload({
            "task_type": "hybrid",
            "complexity_score": 0.92,
            "description": "Multi-hop cross-application planning"
        })
        self.assertEqual(c_res["routing_decision"]["mcp_id"], "host_sovereign_mcp")

    # -------------------------------------------------------------------------
    # Test Group 5: Neo Vision Model Training Script (Genuine Silicon Run)
    # -------------------------------------------------------------------------

    def test_10_neo_train_vision_script_genuine_weights(self):
        """Verify neo_train_vision.sh executes genuine training and produces real weights on disk."""
        script_path = PROJECT_DIR / "neo_train_vision.sh"
        self.assertTrue(script_path.exists())
        self.assertTrue(os.access(script_path, os.X_OK))

        # 1. Test validation mode
        val_res = subprocess.run([str(script_path), "--validate-only"], capture_output=True, text=True, timeout=5.0)
        self.assertEqual(val_res.returncode, 0)
        self.assertIn("Validation check passed successfully", val_res.stdout)

        # 2. Test genuine training execution
        train_res = subprocess.run([str(script_path), "--epochs", "2"], capture_output=True, text=True, timeout=15.0)
        self.assertEqual(train_res.returncode, 0)

        # 3. Verify real adapter files exist on disk with non-zero size
        adapter_dir = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/adapters/screen_lens_edge_vla")
        bin_file = adapter_dir / "adapter_model.bin"
        config_file = adapter_dir / "adapter_config.json"

        self.assertTrue(bin_file.exists(), "adapter_model.bin must be written to disk")
        self.assertGreater(os.path.getsize(bin_file), 0, "adapter_model.bin must not be empty")
        self.assertTrue(config_file.exists(), "adapter_config.json must exist")

        with open(config_file) as f:
            cfg = json.load(f)
        self.assertIn("weights_sha256", cfg)
        self.assertGreater(cfg.get("weights_bytes", 0), 1000)
        self.assertIn("final_loss", cfg)
        self.assertGreater(cfg.get("dataset_records_trained", 0), 0)

    # -------------------------------------------------------------------------
    # Test Group 6: Architecture Debate & Documentation
    # -------------------------------------------------------------------------

    def test_11_architecture_debate_artifacts(self):
        """Verify DEBATE_SCREEN_LENS_MCP.md exists and contains required sections."""
        debate_md = PROJECT_DIR / "DEBATE_SCREEN_LENS_MCP.md"
        self.assertTrue(debate_md.exists())
        with open(debate_md, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Tri-Orchestrator AI Debate: Screen Lens Distributed MCP Architecture", content)
        self.assertIn("Pixel 10 Pro XL", content)
        self.assertIn("Samsung Galaxy S20+", content)
        self.assertIn("Qwen 3.8 Max", content)
        self.assertIn("40Gbps TB4 DMA Bridge", content)
        self.assertIn("0.992", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
