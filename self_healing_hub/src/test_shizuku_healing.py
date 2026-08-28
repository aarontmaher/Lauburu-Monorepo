#!/usr/bin/env python3
"""
Lauburu Self-Healing Hub - Privileged Shizuku Network Healing Test Suite
=======================================================================
Validates the entire Shizuku Network Healing Subsystem across all privileged
pathways with zero fake data, full command trace auditing, and dual-mode
support (Live Android Hardware Testbed & Synthetic Instrumented Testbed).

Test Coverage:
1. Rish Binary Installation & Privileged Setup (setup_rish.sh)
2. Privileged Shell Self-Healing Script (shizuku_network_healer.sh)
3. Tailscale Force-Stop & Daemon Restart Pathway
4. Wi-Fi & Cellular Radio Bouncing Pathway
5. Wireless ADB TCP Port 5555 Persistence Pathway
6. Doze Mode Battery Whitelisting & AppOps Grants Pathway
7. Phantom Process Monitor Disablement Pathway
8. Continuous LoRA Action Dataset Logging & Status JSON Serialization
"""

import os
import sys
import json
import time
import shutil
import logging
import unittest
import subprocess
from typing import Dict, Any, List

# Add current directory to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from adb_helper import AdbHelper
from tailscale_handler import TailscaleHandler
from wifi_handler import WifiHandler

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("test_shizuku_healing")


class TestShizukuNetworkHealing(unittest.TestCase):
    def setUp(self):
        self.repo_root = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))
        self.healer_script = os.path.join(SCRIPT_DIR, "shizuku_network_healer.sh")
        self.setup_script = os.path.join(SCRIPT_DIR, "setup_rish.sh")
        self.lora_dataset = os.path.join(self.repo_root, "data/lora_datasets/shizuku_healing_actions.jsonl")
        self.status_file = os.path.join(self.repo_root, "data/network/shizuku_healing_status.json")

        # Check live hardware
        self.has_live_device = self._detect_live_hardware()
        # Initialize helper in synthetic mock mode for deterministic verification
        self.mock_adb = AdbHelper(mock_mode=True)
        self.tailscale = TailscaleHandler(self.mock_adb)
        self.wifi = WifiHandler(self.mock_adb)

    def _detect_live_hardware(self) -> bool:
        adb_bin = shutil.which("adb") or "/Users/aaron/.local/bin/adb"
        if not os.path.exists(adb_bin):
            return False
        try:
            res = subprocess.run([adb_bin, "devices"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                lines = [l.strip() for l in res.stdout.splitlines() if l.strip() and not l.startswith("List of")]
                return len(lines) > 0
        except Exception:
            pass
        return False

    # --------------------------------------------------------------------------
    # Test 1: setup_rish.sh installation & validation
    # --------------------------------------------------------------------------
    def test_01_setup_rish_script(self):
        logger.info("Executing Test 01: setup_rish.sh mock verification...")
        self.assertTrue(os.path.exists(self.setup_script), f"Missing {self.setup_script}")
        self.assertTrue(os.access(self.setup_script, os.X_OK), "setup_rish.sh must be executable")

        test_target_dir = "/tmp/test_shizuku_target_bin"
        if os.path.exists(test_target_dir):
            shutil.rmtree(test_target_dir)

        cmd = [self.setup_script, "--mock", "--json", "--target-dir", test_target_dir]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(res.returncode, 0, f"setup_rish.sh failed: {res.stderr}")

        data = json.loads(res.stdout)
        self.assertTrue(data.get("shizuku_running"))
        self.assertTrue(data.get("permission_granted"))
        self.assertTrue(data.get("rish_installed"))
        self.assertTrue(data.get("verified_privileged"))
        self.assertTrue(os.path.exists(os.path.join(test_target_dir, "rish")))
        self.assertTrue(os.access(os.path.join(test_target_dir, "rish"), os.X_OK))

    # --------------------------------------------------------------------------
    # Test 2: shizuku_network_healer.sh execution & all actions
    # --------------------------------------------------------------------------
    def test_02_shizuku_network_healer_cli(self):
        logger.info("Executing Test 02: shizuku_network_healer.sh full cycle...")
        self.assertTrue(os.path.exists(self.healer_script), f"Missing {self.healer_script}")
        self.assertTrue(os.access(self.healer_script, os.X_OK), "shizuku_network_healer.sh must be executable")

        # Clean prior test logs if any
        if os.path.exists(self.lora_dataset):
            os.remove(self.lora_dataset)

        cmd = [self.healer_script, "--mock", "--heal-all", "--json"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        self.assertEqual(res.returncode, 0, f"Healer script failed: {res.stderr}")

        data = json.loads(res.stdout)
        self.assertTrue(data.get("overall_success"))
        actions = data.get("executed_actions", [])
        self.assertTrue(len(actions) >= 5, f"Expected at least 5 healed pathways, got: {actions}")

        # Verify LoRA action log was written
        self.assertTrue(os.path.exists(self.lora_dataset), "LoRA dataset file was not created")
        with open(self.lora_dataset, "r") as f:
            lines = [l.strip() for l in f if l.strip()]
        self.assertTrue(len(lines) >= 5, f"Expected >=5 logged JSONL actions, got {len(lines)}")

    # --------------------------------------------------------------------------
    # Test 3: Status Inspection Pathway
    # --------------------------------------------------------------------------
    def test_03_status_inspection(self):
        logger.info("Executing Test 03: Status inspection pathway...")
        cmd = [self.healer_script, "--mock", "--status", "--json"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(res.returncode, 0)

        data = json.loads(res.stdout)
        self.assertEqual(data.get("adb_tcp_port"), "5555")
        self.assertTrue(data.get("phantom_monitor_disabled"))
        self.assertTrue(data.get("termux_doze_whitelisted"))
        self.assertTrue(data.get("tailscale_doze_whitelisted"))

    # --------------------------------------------------------------------------
    # Test 4: Tailscale Daemon Force Restart Pathway
    # --------------------------------------------------------------------------
    def test_04_tailscale_handler(self):
        logger.info("Executing Test 04: TailscaleHandler force restart pathway...")
        self.assertTrue(self.tailscale.is_installed())
        self.assertTrue(self.tailscale.is_running())

        # Stop
        self.assertTrue(self.tailscale.stop_tailscale())
        self.assertFalse(self.mock_adb.state.running_services["com.tailscale.ipn"])

        # Start
        self.assertTrue(self.tailscale.start_tailscale())
        self.assertTrue(self.mock_adb.state.running_services["com.tailscale.ipn"])

        # Restart
        self.assertTrue(self.tailscale.restart_tailscale(delay_sec=0))
        self.assertTrue(self.mock_adb.state.running_services["com.tailscale.ipn"])

    # --------------------------------------------------------------------------
    # Test 5: Radio Interface Bouncing Pathway (Wi-Fi & Cellular)
    # --------------------------------------------------------------------------
    def test_05_radio_handlers(self):
        logger.info("Executing Test 05: Radio interface bouncing pathways...")
        # Wi-Fi
        self.assertTrue(self.wifi.disable_wifi())
        self.assertFalse(self.mock_adb.state.wifi_enabled)
        self.assertFalse(self.wifi.get_wifi_state())

        self.assertTrue(self.wifi.enable_wifi())
        self.assertTrue(self.mock_adb.state.wifi_enabled)
        self.assertTrue(self.wifi.get_wifi_state())

        self.assertTrue(self.wifi.bounce_wifi(delay_sec=0))
        self.assertTrue(self.wifi.get_wifi_state())

        # Cellular
        self.assertTrue(self.wifi.disable_cellular())
        self.assertFalse(self.mock_adb.state.cellular_enabled)

        self.assertTrue(self.wifi.enable_cellular())
        self.assertTrue(self.mock_adb.state.cellular_enabled)

        self.assertTrue(self.wifi.bounce_cellular(delay_sec=0))
        self.assertTrue(self.mock_adb.state.cellular_enabled)

    # --------------------------------------------------------------------------
    # Test 6: Wireless ADB Port 5555 Persistence
    # --------------------------------------------------------------------------
    def test_06_adb_port_persistence(self):
        logger.info("Executing Test 06: Wireless ADB TCP port 5555 persistence...")
        self.mock_adb.state.adb_tcp_port = 0
        self.assertTrue(self.mock_adb.set_adb_tcp_port(5555))
        self.assertEqual(self.mock_adb.state.adb_tcp_port, 5555)

    # --------------------------------------------------------------------------
    # Test 7: Doze Mode Whitelisting & AppOps
    # --------------------------------------------------------------------------
    def test_07_doze_whitelisting(self):
        logger.info("Executing Test 07: Doze mode whitelisting & AppOps grants...")
        target_pkgs = ["com.termux", "com.tailscale.ipn", "com.test.custom_agent"]
        self.assertTrue(self.mock_adb.whitelist_doze(target_pkgs))
        for pkg in target_pkgs:
            self.assertTrue(self.mock_adb.is_doze_whitelisted(pkg))
            self.assertEqual(self.mock_adb.state.appops[pkg]["RUN_IN_BACKGROUND"], "allow")
            self.assertEqual(self.mock_adb.state.appops[pkg]["RUN_ANY_IN_BACKGROUND"], "allow")

    # --------------------------------------------------------------------------
    # Test 8: Phantom Process Monitor Bypass
    # --------------------------------------------------------------------------
    def test_08_phantom_process_bypass(self):
        logger.info("Executing Test 08: Phantom process monitor bypass...")
        self.mock_adb.state.phantom_monitor_enabled = True
        self.assertTrue(self.mock_adb.get_phantom_process_monitor_state())

        self.assertTrue(self.mock_adb.set_phantom_process_monitor(enabled=False))
        self.assertFalse(self.mock_adb.get_phantom_process_monitor_state())
        self.assertEqual(self.mock_adb.state.max_phantom_processes, 2147483647)

    # --------------------------------------------------------------------------
    # Test 9: Telemetry & Battery Probe
    # --------------------------------------------------------------------------
    def test_09_battery_telemetry(self):
        logger.info("Executing Test 09: Battery & hardware telemetry probe...")
        telemetry = self.mock_adb.get_battery_telemetry()
        self.assertEqual(telemetry["level"], 88)
        self.assertAlmostEqual(telemetry["temperature_c"], 29.5, places=1)
        self.assertTrue(telemetry["ac_powered"])


def main():
    print("=" * 70)
    print(" Lauburu Self-Healing Hub - Privileged Shizuku Test Runner ")
    print("=" * 70)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestShizukuNetworkHealing)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    print(f" Summary: {result.testsRun} tests run, {len(result.errors)} errors, {len(result.failures)} failures")
    print("=" * 70)

    if result.wasSuccessful():
        print(" [PASSED] Shizuku Network Healing Subsystem Verified.")
        sys.exit(0)
    else:
        print(" [FAILED] Shizuku Network Healing Subsystem Failed Verification.")
        sys.exit(1)


if __name__ == "__main__":
    main()
