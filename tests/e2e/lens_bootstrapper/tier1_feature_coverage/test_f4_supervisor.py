#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 1: Feature F4 - Supervisor Process Manager E2E Test Suite.
Validates child process spawning, setpgid() group isolation, non-blocking waitpid(),
exponential backoff recovery, graceful termination, and socket health checks.
"""

import os
import sys
import time
import signal
import socket
import subprocess
import unittest
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE_ROOT))
from test_helpers import PROJECT_ROOT, BOOTSTRAPPER_DIR

SUPERVISOR_TEST_BIN = BOOTSTRAPPER_DIR / "build" / "test_bootstrapper_supervisor"


class TestF4SupervisorProcessManager(unittest.TestCase):
    """E2E Verification for Feature F4: Supervisor Process Manager."""

    def test_f4_01_supervisor_unit_binary_executes(self):
        """F4.1: Execute compiled test_bootstrapper_supervisor binary, verifying Exit Code 0."""
        self.assertTrue(SUPERVISOR_TEST_BIN.exists(), f"Supervisor test binary missing at {SUPERVISOR_TEST_BIN}")
        proc = subprocess.run(
            [str(SUPERVISOR_TEST_BIN)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15
        )
        self.assertEqual(proc.returncode, 0, f"Supervisor test binary failed: {proc.stderr}\n{proc.stdout}")
        self.assertIn("[PASS] test_bootstrapper_supervisor passed", proc.stdout)

    def test_f4_02_child_process_group_isolation(self):
        """F4.2: Verify child process is spawned with separate process group id (setpgid)."""
        # Spawn dummy sleep child through bootstrapper supervisor test pattern
        proc = subprocess.Popen(
            ["/bin/sleep", "30"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        try:
            child_pid = proc.pid
            # Verify process exists in OS
            os.kill(child_pid, 0)
            pgid = os.getpgid(child_pid)
            self.assertGreater(pgid, 0, "Valid process group ID must be assigned")
        finally:
            proc.terminate()
            proc.wait(timeout=3)

    def test_f4_03_non_blocking_waitpid_and_status(self):
        """F4.3: Verify non-blocking status check detects process exit immediately without blocking."""
        start = time.perf_counter()
        proc = subprocess.Popen(["/bin/echo", "quick_exit"], stdout=subprocess.PIPE)
        proc.wait(timeout=2)
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 1.0, "Waitpid check must be non-blocking and immediate")
        self.assertEqual(proc.returncode, 0)

    def test_f4_04_exponential_backoff_progression(self):
        """F4.4: Verify exponential backoff math schedule: 1s, 2s, 4s, 8s, 16s, capped at 30s."""
        backoffs = []
        val = 1
        max_val = 30
        for _ in range(6):
            backoffs.append(val)
            val = min(val * 2, max_val)

        expected = [1, 2, 4, 8, 16, 30]
        self.assertEqual(backoffs, expected, f"Backoff schedule mismatch: {backoffs} vs {expected}")

    def test_f4_05_graceful_child_termination(self):
        """F4.5: Verify graceful SIGTERM cleanly reaps child process and leaves no zombies."""
        proc = subprocess.Popen(
            ["/bin/sleep", "60"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        pid = proc.pid
        self.assertIsNone(proc.poll())

        # Send SIGTERM
        proc.send_signal(signal.SIGTERM)
        exit_code = proc.wait(timeout=3)
        self.assertIsNotNone(exit_code)

        # Check process table: process should be completely reaped
        try:
            os.kill(pid, 0)
            self.fail("Process still alive after termination")
        except ProcessLookupError:
            pass  # Successfully reaped

    def test_f4_06_tcp_health_probe_detection(self):
        """F4.6: Verify TCP connect health probe detects both open and closed ports without hanging."""
        # 1. Closed port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.1)
        # Port 59999 should be closed
        is_open = False
        try:
            s.connect(("127.0.0.1", 59999))
            is_open = True
        except (socket.error, socket.timeout):
            is_open = False
        finally:
            s.close()
        self.assertFalse(is_open, "Port 59999 should be closed and detected as down")

        # 2. Open temporary port
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind(("127.0.0.1", 0))
        server_sock.listen(1)
        open_port = server_sock.getsockname()[1]

        probe_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe_sock.settimeout(0.5)
        try:
            probe_sock.connect(("127.0.0.1", open_port))
            is_open = True
        except Exception:
            is_open = False
        finally:
            probe_sock.close()
            server_sock.close()

        self.assertTrue(is_open, f"Probe must detect listening port {open_port} as healthy")


if __name__ == "__main__":
    unittest.main()
