#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 1: Feature F5 - Zero-Overhead IPC Control Plane E2E Test Suite.
Validates Unix domain socket protocol, file permissions (0600), commands
(PING, STATUS, TELEMETRY, RESTART_SUPERVISOR, STOP), and companion lens_bootstrapper_ctl CLI tool.
"""

import os
import sys
import time
import json
import socket
import signal
import subprocess
import unittest
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE_ROOT))
from test_helpers import PROJECT_ROOT, BOOTSTRAPPER_DIR, send_socket_command

DAEMON_BIN = BOOTSTRAPPER_DIR / "build" / "lens_bootstrapper"
CTL_BIN = BOOTSTRAPPER_DIR / "build" / "lens_bootstrapper_ctl"
IPC_TEST_BIN = BOOTSTRAPPER_DIR / "build" / "test_bootstrapper_ipc"


class TestF5IPCControlPlane(unittest.TestCase):
    """E2E Verification for Feature F5: Zero-Overhead IPC Control Plane."""

    @classmethod
    def setUpClass(cls):
        cls.daemon_proc = None
        cls.default_sock = Path(os.path.expanduser("~/.lauburu/lens_bootstrapper.sock"))
        
        # Start daemon for live socket interaction
        cls.daemon_proc = subprocess.Popen(
            [str(DAEMON_BIN), "--foreground", "--no-supervisor"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        # Wait up to 3s for socket creation
        start = time.time()
        while time.time() - start < 3.0:
            if cls.default_sock.exists():
                break
            time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        if cls.daemon_proc:
            cls.daemon_proc.terminate()
            try:
                cls.daemon_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                cls.daemon_proc.kill()
            if cls.daemon_proc.stdout: cls.daemon_proc.stdout.close()
            if cls.daemon_proc.stderr: cls.daemon_proc.stderr.close()

    def test_f5_01_ipc_unit_binary_executes(self):
        """F5.1: Execute compiled test_bootstrapper_ipc binary, verifying Exit Code 0."""
        self.assertTrue(IPC_TEST_BIN.exists(), f"IPC test binary missing at {IPC_TEST_BIN}")
        proc = subprocess.run(
            [str(IPC_TEST_BIN)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        self.assertEqual(proc.returncode, 0, f"IPC test binary failed: {proc.stderr}\n{proc.stdout}")
        self.assertIn("[PASS] test_bootstrapper_ipc passed", proc.stdout)

    def test_f5_02_socket_file_permissions_0600(self):
        """F5.2: Verify Unix socket file mode is owner-only read/write (0600)."""
        self.assertTrue(self.default_sock.exists(), f"Socket missing at {self.default_sock}")
        mode = os.stat(str(self.default_sock)).st_mode & 0o777
        self.assertEqual(
            mode, 0o600,
            f"Socket permission vulnerability: mode is {oct(mode)}, must be 0600 (owner-only)"
        )

    def test_f5_03_ping_pong_command(self):
        """F5.3: Verify PING command returns {\"result\": \"PONG\"}."""
        ok, resp = send_socket_command(str(self.default_sock), "PING")
        self.assertTrue(ok, f"PING failed: {resp}")
        data = json.loads(resp)
        self.assertEqual(data.get("result"), "PONG")

    def test_f5_04_status_command_schema(self):
        """F5.4: Verify STATUS command returns valid JSON with PID, uptime, and status."""
        ok, resp = send_socket_command(str(self.default_sock), "STATUS")
        self.assertTrue(ok, f"STATUS failed: {resp}")
        data = json.loads(resp)
        self.assertEqual(data.get("status"), "RUNNING")
        self.assertIn("pid", data)
        self.assertIn("uptime_sec", data)
        self.assertIn("supervisor_status", data)

    def test_f5_05_telemetry_command_schema(self):
        """F5.5: Verify TELEMETRY command returns authentic Mach/system metrics."""
        ok, resp = send_socket_command(str(self.default_sock), "TELEMETRY")
        self.assertTrue(ok, f"TELEMETRY failed: {resp}")
        data = json.loads(resp)
        self.assertIn("timestamp", data)
        self.assertIn("ram_free_bytes", data)
        self.assertIn("ram_avail_bytes", data)
        self.assertIn("vm_pressure", data)
        self.assertIn("thermal_pressure", data)
        self.assertGreater(data["ram_avail_bytes"], 0)

    def test_f5_06_lens_bootstrapper_ctl_cli(self):
        """F5.6: Verify lens_bootstrapper_ctl CLI connects and formats output."""
        self.assertTrue(CTL_BIN.exists(), f"Control CLI missing at {CTL_BIN}")
        
        # Test status command
        proc = subprocess.run(
            [str(CTL_BIN), "status"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        self.assertEqual(proc.returncode, 0, f"ctl status failed: {proc.stderr}")
        self.assertIn("RUNNING", proc.stdout)

        # Test telemetry command
        proc_tel = subprocess.run(
            [str(CTL_BIN), "telemetry"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        self.assertEqual(proc_tel.returncode, 0, f"ctl telemetry failed: {proc_tel.stderr}")
        self.assertIn("ram_free_bytes", proc_tel.stdout)


if __name__ == "__main__":
    unittest.main()
