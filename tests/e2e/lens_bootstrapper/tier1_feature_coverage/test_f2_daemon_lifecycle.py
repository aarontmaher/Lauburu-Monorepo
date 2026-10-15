#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 1: Feature F2 - C++ Bootstrapper Daemon Core E2E Test Suite.
Validates CLI parsing, test-run execution, POSIX signal handling (SIGTERM),
custom socket paths, and idle resident memory footprint (< 10MB RSS).
"""

import os
import sys
import time
import json
import signal
import tempfile
import subprocess
import unittest
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE_ROOT))
from test_helpers import PROJECT_ROOT, BOOTSTRAPPER_DIR

DAEMON_BIN = BOOTSTRAPPER_DIR / "build" / "lens_bootstrapper"


class TestF2DaemonLifecycle(unittest.TestCase):
    """E2E Verification for Feature F2: C++ Bootstrapper Daemon Core."""

    def setUp(self):
        self.daemon_bin = DAEMON_BIN
        self.assertTrue(self.daemon_bin.exists(), f"Daemon binary missing: {self.daemon_bin}")

    def test_f2_01_cli_help(self):
        """F2.1: Verify --help option returns 0 and displays command options."""
        proc = subprocess.run(
            [str(self.daemon_bin), "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Usage:", proc.stdout)
        self.assertIn("--foreground", proc.stdout)
        self.assertIn("--daemon", proc.stdout)
        self.assertIn("--config", proc.stdout)
        self.assertIn("--test-run", proc.stdout)

    def test_f2_02_cli_unknown_option_fails(self):
        """F2.2: Verify invalid option exits with code 1 and error message."""
        proc = subprocess.run(
            [str(self.daemon_bin), "--invalid-flag-xyz"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Unknown option", proc.stderr)

    def test_f2_03_test_run_mode(self):
        """F2.3: Verify --test-run mode executes for ~2.5-3 seconds and cleanly exits with 0."""
        start = time.time()
        proc = subprocess.run(
            [str(self.daemon_bin), "--test-run", "--no-supervisor"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        elapsed = time.time() - start
        self.assertEqual(proc.returncode, 0, f"Test-run failed: {proc.stderr}")
        self.assertGreaterEqual(elapsed, 2.0, "Test-run should run for configured ~2.5s duration")
        self.assertLess(elapsed, 8.0, "Test-run did not terminate promptly")

    def test_f2_04_signal_sigterm_handling(self):
        """F2.4: Verify process catches SIGTERM and exits cleanly with code 0."""
        proc = subprocess.Popen(
            [str(self.daemon_bin), "--foreground", "--no-supervisor"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        time.sleep(0.5)
        self.assertIsNone(proc.poll(), "Daemon exited prematurely before SIGTERM")
        
        proc.send_signal(signal.SIGTERM)
        try:
            exit_code = proc.wait(timeout=5)
            self.assertEqual(exit_code, 0, f"SIGTERM should produce clean exit code 0, got {exit_code}")
        except subprocess.TimeoutExpired:
            proc.kill()
            self.fail("Daemon did not terminate within 5 seconds after SIGTERM")
        finally:
            if proc.stdout: proc.stdout.close()
            if proc.stderr: proc.stderr.close()

    def test_f2_05_idle_resident_memory_footprint(self):
        """F2.5: Empirically verify idle RSS is strictly < 10.0 MB (Acceptance Criterion 2)."""
        proc = subprocess.Popen(
            [str(self.daemon_bin), "--foreground", "--no-supervisor"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        try:
            time.sleep(1.0)
            self.assertIsNone(proc.poll(), "Daemon died during memory measurement")

            ps_proc = subprocess.run(
                ["ps", "-o", "rss", "-p", str(proc.pid)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            lines = [line.strip() for line in ps_proc.stdout.strip().split("\n") if line.strip()]
            self.assertGreaterEqual(len(lines), 2, "Failed to read ps RSS output")
            rss_kb = int(lines[1])
            rss_mb = rss_kb / 1024.0

            # Acceptance Criterion 2: < 10MB baseline RAM
            self.assertLess(
                rss_mb, 10.0,
                f"Idle daemon RAM violation: measured {rss_mb:.2f} MB RSS, must be < 10.0 MB"
            )
        finally:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
            if proc.stdout: proc.stdout.close()
            if proc.stderr: proc.stderr.close()

    def test_f2_06_socket_path_override_via_config(self):
        """F2.6: Verify custom socket path parameter creates and binds socket file."""
        custom_sock = f"/tmp/lens_custom_{os.getpid()}.sock"
        if os.path.exists(custom_sock):
            try:
                os.unlink(custom_sock)
            except OSError:
                pass

        temp_cfg = Path(f"/tmp/lens_test_cfg_{os.getpid()}.json")
        temp_cfg.write_text(json.dumps({
            "socket_path": custom_sock,
            "enable_supervisor": False,
            "telemetry_interval_sec": 5
        }), encoding="utf-8")

        proc = subprocess.Popen(
            [str(self.daemon_bin), "--foreground", "--config", str(temp_cfg)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        try:
            time.sleep(0.5)
            self.assertTrue(
                os.path.exists(custom_sock),
                f"Daemon failed to create socket at {custom_sock}"
            )
        finally:
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=3)
            if proc.stdout: proc.stdout.close()
            if proc.stderr: proc.stderr.close()
            if temp_cfg.exists():
                temp_cfg.unlink()
            self.assertFalse(os.path.exists(custom_sock), "Socket must be removed on exit")


if __name__ == "__main__":
    unittest.main()
