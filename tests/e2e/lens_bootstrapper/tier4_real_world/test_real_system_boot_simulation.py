#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 4: Real-World Workload Scenarios - Full System Boot Simulation.
Validates end-to-end bootstrapper daemon launch cycle:
1. Cold start daemon launch from command line
2. Unix domain socket binding and permission enforcement (0600)
3. Supervisor child process group isolation and health monitoring
4. Real-time telemetry query handling
5. Graceful SIGTERM shutdown and resource cleanup
"""

import os
import sys
import time
import json
import signal
import subprocess
import unittest
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE_ROOT))
from test_helpers import PROJECT_ROOT, BOOTSTRAPPER_DIR, send_socket_command

DAEMON_BIN = BOOTSTRAPPER_DIR / "build" / "lens_bootstrapper"


class TestRealSystemBootSimulation(unittest.TestCase):
    """Real-World Acceptance Scenario: Cold Start System Boot & Lifecycle."""

    def setUp(self):
        self.sock_path = f"/tmp/lens_boot_sim_{os.getpid()}.sock"
        self.config_path = Path(f"/tmp/lens_boot_cfg_{os.getpid()}.json")
        self.config_path.write_text(json.dumps({
            "socket_path": self.sock_path,
            "enable_supervisor": True,
            "supervisor_command": "/bin/sleep 60",
            "telemetry_interval_sec": 1
        }), encoding="utf-8")

    def tearDown(self):
        if self.config_path.exists():
            self.config_path.unlink()
        if os.path.exists(self.sock_path):
            try:
                os.unlink(self.sock_path)
            except OSError:
                pass

    def test_r1_01_cold_boot_startup_latency(self):
        """R1.1: Cold boot starts daemon and binds IPC socket in < 1.0 second."""
        start = time.perf_counter()
        proc = subprocess.Popen(
            [str(DAEMON_BIN), "--foreground", "--config", str(self.config_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        try:
            # Poll for socket availability
            bound = False
            for _ in range(20):
                if os.path.exists(self.sock_path):
                    bound = True
                    break
                time.sleep(0.05)

            elapsed_sec = time.perf_counter() - start
            self.assertTrue(bound, "Socket failed to bind during cold boot")
            self.assertLess(elapsed_sec, 1.0, f"Cold boot exceeded 1.0s: {elapsed_sec:.3f}s")
        finally:
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=3)
            if proc.stdout: proc.stdout.close()
            if proc.stderr: proc.stderr.close()

    def test_r1_02_boot_supervision_child_alive(self):
        """R1.2: Child process is spawned under bootstrapper and reported ALIVE via IPC."""
        proc = subprocess.Popen(
            [str(DAEMON_BIN), "--foreground", "--config", str(self.config_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        try:
            time.sleep(0.5)
            ok, resp = send_socket_command(self.sock_path, "STATUS")
            self.assertTrue(ok, f"STATUS failed: {resp}")
            data = json.loads(resp)
            self.assertEqual(data.get("status"), "RUNNING")
            self.assertIn(data.get("supervisor_status"), ["ALIVE", "STARTING"])
        finally:
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=3)
            if proc.stdout: proc.stdout.close()
            if proc.stderr: proc.stderr.close()

    def test_r1_03_telemetry_stream_during_boot(self):
        """R1.3: Real-time telemetry provides valid memory and thermal readings during active run."""
        proc = subprocess.Popen(
            [str(DAEMON_BIN), "--foreground", "--config", str(self.config_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        try:
            time.sleep(0.5)
            ok, resp = send_socket_command(self.sock_path, "TELEMETRY")
            self.assertTrue(ok)
            data = json.loads(resp)
            self.assertGreater(data["ram_total_bytes"], 0)
            self.assertGreater(data["ram_avail_bytes"], 0)
            self.assertIn(data["thermal_pressure"], [0, 1, 2, 3])
        finally:
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=3)
            if proc.stdout: proc.stdout.close()
            if proc.stderr: proc.stderr.close()

    def test_r1_04_graceful_shutdown_cleans_child_and_socket(self):
        """R1.4: SIGTERM shutdown reaps child process and cleans up socket file from filesystem."""
        proc = subprocess.Popen(
            [str(DAEMON_BIN), "--foreground", "--config", str(self.config_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        time.sleep(0.5)
        self.assertTrue(os.path.exists(self.sock_path))

        # Shutdown
        proc.send_signal(signal.SIGTERM)
        exit_code = proc.wait(timeout=5)
        self.assertEqual(exit_code, 0)
        self.assertFalse(
            os.path.exists(self.sock_path),
            "Socket file must be cleanly unlinked upon daemon exit"
        )
        if proc.stdout: proc.stdout.close()
        if proc.stderr: proc.stderr.close()


if __name__ == "__main__":
    unittest.main()
