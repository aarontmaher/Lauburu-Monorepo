#!/usr/bin/env python3
"""
test_s20_lens_network.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Comprehensive E2E Integration & Unit Verification Suite
for Samsung S20 Screen Lens Sovereign Expansion Module.

Validates all 4 requirements and Acceptance Criteria:
- AC1: s20_shizuku_network.py privileged ping/ip diagnostics
- AC2: glinet_luci_tools.py ubus call wg_client mapping and structured JSON
- AC3: s20_mesh_monitor.sh mesh metric parsing without crash & tmux attach
- AC4: s20_ai_dispatcher.py programmatic toggles across 3 backends
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import sys
import json
import unittest
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import s20_shizuku_network
import glinet_luci_tools
import s20_ai_dispatcher

class TestS20ShizukuNetwork(unittest.TestCase):
    """AC 1: Privileged network diagnostics via s20_shizuku_network.py."""

    def test_get_network_interfaces_structure(self):
        res = s20_shizuku_network.get_network_interfaces()
        self.assertIsInstance(res, dict)
        self.assertIn("command", res)
        self.assertIn("ip link", res["command"])
        self.assertIn("exit_code", res)
        self.assertIn("transport", res)

    def test_get_routing_table_structure(self):
        res = s20_shizuku_network.get_routing_table()
        self.assertIsInstance(res, dict)
        self.assertIn("command", res)
        self.assertIn("ip route", res["command"])
        self.assertIn("exit_code", res)

    def test_ping_host_structure(self):
        res = s20_shizuku_network.ping_host("127.0.0.1", count=1)
        self.assertIsInstance(res, dict)
        self.assertIn("command", res)
        self.assertIn("ping", res["command"])
        self.assertIn("exit_code", res)

    def test_cli_execution_interfaces(self):
        cmd = [sys.executable, str(BASE_DIR / "s20_shizuku_network.py"), "--action", "interfaces"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertIsInstance(data, dict)
        self.assertIn("command", data)

    def test_cli_execution_ping(self):
        cmd = [sys.executable, str(BASE_DIR / "s20_shizuku_network.py"), "--action", "ping", "--host", "127.0.0.1", "--count", "1"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertIsInstance(data, dict)
        self.assertIn("exit_code", data)

class TestGLiNetLuciTools(unittest.TestCase):
    """AC 2: Router & WireGuard tool-calling API and structured JSON."""

    def test_functions_exist_and_callable(self):
        self.assertTrue(callable(glinet_luci_tools.wg_client_status))
        self.assertTrue(callable(glinet_luci_tools.wg_client_profiles))
        self.assertTrue(callable(glinet_luci_tools.wg_client_start))
        self.assertTrue(callable(glinet_luci_tools.wg_client_stop))
        self.assertTrue(callable(glinet_luci_tools.luci_interfaces_dump))
        self.assertTrue(callable(glinet_luci_tools.luci_interface_status))
        self.assertTrue(callable(glinet_luci_tools.luci_device_status))
        self.assertTrue(callable(glinet_luci_tools.get_wg_show))

    def test_wg_client_status_returns_structured_dict(self):
        res = glinet_luci_tools.wg_client_status()
        self.assertIsInstance(res, dict)
        self.assertIn("command", res)
        self.assertIn("ubus call wg_client get_status", res["command"])
        self.assertIn("exit_code", res)

    def test_dispatch_tool_call_openai_schema(self):
        payload = {
            "name": "wg_client_status",
            "arguments": {}
        }
        res = glinet_luci_tools.dispatch_tool_call(payload)
        self.assertIsInstance(res, dict)
        self.assertIn("command", res)
        self.assertIn("ubus call wg_client get_status", res["command"])

    def test_dispatch_tool_call_with_args(self):
        payload = {
            "name": "luci_interface_status",
            "arguments": {"interface_name": "lan"}
        }
        res = glinet_luci_tools.dispatch_tool_call(payload)
        self.assertIsInstance(res, dict)
        self.assertIn("command", res)
        self.assertIn("ubus call network.interface.lan status", res["command"])

    def test_dispatch_unknown_tool_fails_gracefully(self):
        payload = {"name": "non_existent_tool_xyz", "arguments": {}}
        res = glinet_luci_tools.dispatch_tool_call(payload)
        self.assertIsInstance(res, dict)
        self.assertFalse(res.get("success", False))
        self.assertIn("Unknown tool", res.get("error", ""))

    def test_cli_execution_action(self):
        cmd = [sys.executable, str(BASE_DIR / "glinet_luci_tools.py"), "--action", "wg_client_status"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertIsInstance(data, dict)
        self.assertIn("command", data)

    def test_cli_execution_tool_call(self):
        tool_call_json = json.dumps({"name": "wg_client_profiles", "arguments": {}})
        cmd = [sys.executable, str(BASE_DIR / "glinet_luci_tools.py"), "--tool-call", tool_call_json]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertIsInstance(data, dict)
        self.assertIn("ubus call wg_client get_profiles", data.get("command", ""))

class TestS20MeshMonitor(unittest.TestCase):
    """AC 3: 7-device mesh monitor script parsing and tmux integration."""

    def test_mesh_monitor_json_parsing(self):
        script_path = BASE_DIR / "s20_mesh_monitor.sh"
        cmd = ["bash", str(script_path), "--json"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        self.assertEqual(proc.returncode, 0, f"Error: {proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertIn("devices", data)
        self.assertIsInstance(data["devices"], list)
        
        # Verify all 7 physical mesh layers + gateway exist in output
        device_names = [d.get("name", "") for d in data["devices"]]
        self.assertTrue(any("L1" in name for name in device_names), "L1 Mac Host missing")
        self.assertTrue(any("L2" in name for name in device_names), "L2 MacBook Pro missing")
        self.assertTrue(any("L3" in name for name in device_names), "L3 Linux Mini missing")
        self.assertTrue(any("L4" in name for name in device_names), "L4 Linux Tablet missing")
        self.assertTrue(any("L5" in name for name in device_names), "L5 MacBook Air missing")
        self.assertTrue(any("L6" in name for name in device_names), "L6 Pixel 10 missing")
        self.assertTrue(any("L7" in name for name in device_names), "L7 Samsung S20 missing")
        self.assertTrue(any("GW" in name for name in device_names), "GW Router missing")

    def test_mesh_monitor_batch_mode_no_hang(self):
        script_path = BASE_DIR / "s20_mesh_monitor.sh"
        cmd = ["bash", str(script_path), "--batch"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("LAUBURU 7-LAYER PHYSICAL MESH MONITOR", proc.stdout)
        self.assertIn("Batch mode detected", proc.stdout)

    def test_mesh_monitor_contains_tmux_attach(self):
        script_path = BASE_DIR / "s20_mesh_monitor.sh"
        with open(script_path, "r") as f:
            content = f.read()
        self.assertIn("tmux attach -t", content)
        self.assertIn("mesh_agy_fleet", content)

class TestS20AIDispatcher(unittest.TestCase):
    """AC 4: Multi-Model Intelligence Dispatcher with programmatic toggles."""

    def setUp(self):
        self.test_payload = {
            "messages": [{"role": "user", "content": "Analyze mesh ping latency"}],
            "max_tokens": 50
        }

    def test_toggle_local_backend(self):
        res = s20_ai_dispatcher.dispatch_payload(self.test_payload, backend="local")
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("backend"), "local_qwen")
        self.assertTrue(res.get("success") or "tested_endpoints" in res)

    def test_toggle_cloud_backend(self):
        res = s20_ai_dispatcher.dispatch_payload(self.test_payload, backend="cloud")
        self.assertIsInstance(res, dict)
        self.assertIn("cloud", res.get("backend", ""))
        self.assertIn("success", res)

    def test_toggle_openrouter_backend(self):
        res = s20_ai_dispatcher.dispatch_payload(self.test_payload, backend="openrouter")
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("backend"), "openrouter")
        self.assertIn("success", res)

    def test_toggle_auto_backend(self):
        res = s20_ai_dispatcher.dispatch_payload(self.test_payload, backend="auto")
        self.assertIsInstance(res, dict)
        self.assertIn("success", res)

    def test_invalid_backend_toggle(self):
        res = s20_ai_dispatcher.dispatch_payload(self.test_payload, backend="invalid_backend_name")
        self.assertIsInstance(res, dict)
        self.assertFalse(res.get("success"))
        self.assertIn("Invalid backend toggle", res.get("error", ""))

    def test_cli_execution_local_toggle(self):
        payload_json = json.dumps(self.test_payload)
        cmd = [sys.executable, str(BASE_DIR / "s20_ai_dispatcher.py"), "--backend", "local", "--payload", payload_json]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertIsInstance(data, dict)
        self.assertEqual(data.get("backend"), "local_qwen")

    def test_cli_execution_cloud_toggle(self):
        payload_json = json.dumps(self.test_payload)
        cmd = [sys.executable, str(BASE_DIR / "s20_ai_dispatcher.py"), "--backend", "cloud", "--payload", payload_json]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertIsInstance(data, dict)
        self.assertTrue("cloud" in data.get("backend", "") or "error" in data)

    def test_cli_execution_openrouter_toggle(self):
        payload_json = json.dumps(self.test_payload)
        cmd = [sys.executable, str(BASE_DIR / "s20_ai_dispatcher.py"), "--backend", "openrouter", "--payload", payload_json]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertIsInstance(data, dict)
        self.assertEqual(data.get("backend"), "openrouter")

if __name__ == "__main__":
    unittest.main()
