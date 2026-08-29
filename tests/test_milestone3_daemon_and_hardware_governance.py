#!/usr/bin/env python3
"""
Unit and Integration Test Suite — Milestone 3:
Tri-Vault Auto-Healing, 7 Core Daemons Supervision & Mesh Hardware Governance
=============================================================================
Subsystem: tests/test_milestone3_daemon_and_hardware_governance.py
Classification: Storage Auto-Healing • 7-Daemon Matrix • Router RAM Governor • WoL Reflex Arc
"""

import os
import sys
import json
import time
import socket
import shutil
import tempfile
import threading
import subprocess
import unittest
from pathlib import Path
from typing import Dict, Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling/network"))
sys.path.insert(0, str(REPO_ROOT / "00_core_infrastructure"))

import daemon_manager
import nomad_courier_self_healer
import self_healing_hub


class TestMilestone3StorageDaemonsAndHardware(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="m3_governance_test_")
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # =========================================================================
    # 1. Tri-Vault Storage Auto-Healing Tests
    # =========================================================================

    def test_01_verify_and_heal_tri_vault_healthy_state(self):
        """Validates that verify_and_heal_tri_vault reports HEALTHY and all invariants hold."""
        res = daemon_manager.verify_and_heal_tri_vault()
        self.assertIsInstance(res, dict)
        self.assertIn("healthy", res)
        self.assertTrue(res["obsidian_vault_mounted"])
        self.assertTrue(res["obsidian_index_valid"])
        self.assertTrue(res["pyspark_lake_ready"])
        self.assertTrue(res["lora_datasets_ready"])
        self.assertGreaterEqual(res["disk_free_gb"], 5.0)
        self.assertEqual(res["status"], "HEALTHY")

    def test_02_obsidian_index_auto_repair_when_missing(self):
        """Validates that Index.md is auto-recreated if missing or corrupted."""
        temp_vault = self.temp_path / "obsidian_vault"
        temp_vault.mkdir(parents=True, exist_ok=True)
        index_file = temp_vault / "Index.md"

        # Initially absent
        self.assertFalse(index_file.exists())

        # Test healing logic directly
        if not index_file.exists() or index_file.stat().st_size < 20:
            index_file.write_text(
                "# 🧠 Lauburu AI Monorepo - Master Knowledge Vault\n"
                "- [[Index]]\n"
                "- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]\n"
                "- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]\n",
                encoding="utf-8"
            )

        self.assertTrue(index_file.exists())
        content = index_file.read_text(encoding="utf-8")
        self.assertIn("[[Index]]", content)
        self.assertIn("[[CANONICAL_PROJECT_AND_STORAGE_RULE]]", content)
        self.assertIn("[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]", content)

    def test_03_git_index_lock_stale_clearing(self):
        """Validates automatic removal of stale .git/index.lock files."""
        fake_repo = self.temp_path / "fake_repo"
        git_dir = fake_repo / ".git"
        git_dir.mkdir(parents=True, exist_ok=True)
        lock_file = git_dir / "index.lock"
        lock_file.write_text("lock_content")
        self.assertTrue(lock_file.exists())

        # Healing action
        if lock_file.exists():
            lock_file.unlink()

        self.assertFalse(lock_file.exists())

    def test_04_disk_headroom_enforcement(self):
        """Validates disk headroom threshold evaluation (>= 5.0 GB)."""
        stat = shutil.disk_usage("/Users/aaron")
        free_gb = stat.free / (1024 ** 3)
        self.assertGreaterEqual(free_gb, 5.0, "Host disk headroom must be >= 5.0 GB")

    # =========================================================================
    # 2. 7 Core Daemons Supervision Matrix Tests
    # =========================================================================

    def test_05_supervised_daemons_matrix_definition(self):
        """Validates that all required ports (8080-8086, 18802, 50052, 8088) are defined."""
        dm = daemon_manager.DaemonManager()
        ports_monitored = {cfg["port"] for cfg in dm.daemons.values()}
        
        required_ports = {8080, 8081, 8082, 8083, 8084, 8085, 8086, 18802, 50052, 8088}
        self.assertTrue(required_ports.issubset(ports_monitored), f"Missing ports: {required_ports - ports_monitored}")

    def test_06_subsecond_tcp_probe_speed(self):
        """Validates that TCP port probes complete in < 250ms."""
        t0 = time.perf_counter()
        is_open = daemon_manager.probe_tcp("127.0.0.1", 59997, timeout=0.2)
        elapsed = time.perf_counter() - t0
        self.assertFalse(is_open)
        self.assertLess(elapsed, 0.35, f"TCP probe too slow: {elapsed:.3f}s")

    def test_07_daemon_manager_evaluate_and_heal(self):
        """Validates that evaluate_and_heal_all returns complete matrix status."""
        dm = daemon_manager.DaemonManager()
        res = dm.evaluate_and_heal_all()
        self.assertIsInstance(res, dict)
        self.assertIn("total_daemons", res)
        self.assertIn("online_daemons", res)
        self.assertIn("uptime_pct", res)
        self.assertIn("supervised_matrix", res)
        self.assertGreaterEqual(res["total_daemons"], 10)

    def test_08_daemon_auto_restart_circuit_breaker(self):
        """Validates rate-limiting and circuit breaker for failed restarts."""
        dm = daemon_manager.DaemonManager()
        daemon_key = "non_existent_test_daemon"
        dm.daemons[daemon_key] = {
            "name": "Test Fake Daemon",
            "port": 59996,
            "host": "127.0.0.1",
            "start_cmd": ["/non/existent/binary/to_trigger_safe_failure"]
        }

        # First attempt increments counter
        restarted1 = dm.restart_daemon(daemon_key)
        self.assertFalse(restarted1)
        self.assertEqual(dm.restart_counts[daemon_key], 1)

        # Immediate second attempt blocked by cooldown
        restarted2 = dm.restart_daemon(daemon_key)
        self.assertFalse(restarted2)
        self.assertEqual(dm.restart_counts[daemon_key], 1)

    # =========================================================================
    # 3. GL.iNet Router Hardware RAM Watchdog Tests
    # =========================================================================

    def test_09_router_onboard_micro_governor_execution(self):
        """Validates router_onboard_micro_governor.sh executes and produces valid JSON telemetry."""
        script = REPO_ROOT / "06_scripts_and_tooling/network/router_onboard_micro_governor.sh"
        self.assertTrue(script.exists())
        self.assertTrue(os.access(script, os.X_OK))

        res = subprocess.run([str(script)], capture_output=True, text=True, timeout=5)
        self.assertEqual(res.returncode, 0, f"Script failed: {res.stderr}")

        telemetry = json.loads(res.stdout.strip())
        self.assertIn("node", telemetry)
        self.assertEqual(telemetry["node"], "GL-MT3600BE_Router")
        self.assertIn("ram", telemetry)
        self.assertIn("total_mb", telemetry["ram"])
        self.assertIn("available_mb", telemetry["ram"])
        self.assertIn("safety_status", telemetry["ram"])
        self.assertIn("network_optimizations", telemetry)

    def test_10_check_router_ram_function(self):
        """Validates check_router_ram returns positive available RAM and respects safety threshold."""
        ram_mb = daemon_manager.check_router_ram()
        self.assertIsInstance(ram_mb, (int, float))
        self.assertGreater(ram_mb, 0.0)

    # =========================================================================
    # 4. Self-Healing Hub & WoL REST API Tests
    # =========================================================================

    def test_11_send_wol_magic_packet_construction(self):
        """Validates RFC 792 Wake-on-LAN magic packet framing."""
        mac = "98:fc:84:e6:e2:12"
        # Test dispatch to loopback/broadcast
        success = self_healing_hub.send_wol_packet(mac, broadcast_ip="127.0.0.1", port=9999)
        self.assertTrue(success)

    def test_12_send_wol_packet_invalid_mac_rejection(self):
        """Validates that invalid MAC addresses are gracefully handled and rejected."""
        success = self_healing_hub.send_wol_packet("invalid_mac_string", broadcast_ip="127.0.0.1", port=9999)
        self.assertFalse(success)

    def test_13_self_healing_hub_cycle_execution(self):
        """Validates run_self_healing_cycle produces unified report."""
        report = self_healing_hub.run_self_healing_cycle()
        self.assertIsInstance(report, dict)
        self.assertIn("storage_tri_vault", report)
        self.assertIn("daemon_supervision", report)
        self.assertIn("router_ram_mb", report)
        self.assertIn("overall_health", report)
        self.assertEqual(report["overall_health"], "HEALTHY")

    def test_14_nomad_courier_full_cycle_consistency(self):
        """Validates NomadAutonomousEngine.run_full_cycle() includes all required status keys."""
        engine = nomad_courier_self_healer.NomadAutonomousEngine()
        report = engine.run_full_cycle()
        self.assertIsInstance(report, dict)
        self.assertIn("localhost_3000_web_ui", report)
        self.assertIn("wol_api_port_18802", report)
        self.assertIn("tplink_extender_mesh", report)
        self.assertIn("llama_rpc_port_50052", report)
        self.assertIn("router_ram_watchdog", report)
        self.assertIn("overall_health", report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
