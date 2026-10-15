#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 2: Boundary Value Analysis - Dead & Corrupted Sockets.
Stresses IPC server against Unix domain socket anomalies:
1. Connecting to nonexistent socket path
2. Stale leftover socket cleanup on daemon restart
3. Sudden client disconnect mid-transaction
4. Rapid successive connection bursts
5. Oversized payload / giant input line
"""

import os
import sys
import time
import socket
import signal
import subprocess
import unittest
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE_ROOT))
from test_helpers import PROJECT_ROOT, BOOTSTRAPPER_DIR, send_socket_command

DAEMON_BIN = BOOTSTRAPPER_DIR / "build" / "lens_bootstrapper"


class TestBoundaryDeadSockets(unittest.TestCase):
    """Boundary testing for Unix domain socket error handling."""

    def test_b2_01_connect_nonexistent_socket_fails_safely(self):
        """B2.1: Connecting to a nonexistent socket path returns clean False and error string."""
        bogus_sock = "/tmp/lens_nonexistent_socket_9999.sock"
        ok, msg = send_socket_command(bogus_sock, "PING")
        self.assertFalse(ok)
        self.assertIn("does not exist", msg)

    def test_b2_02_stale_socket_cleanup_on_start(self):
        """B2.2: Daemon unlinks existing stale socket file from prior crashed run and successfully binds."""
        stale_sock = f"/tmp/lens_stale_{os.getpid()}.sock"
        # Create dummy file at socket path
        with open(stale_sock, "w") as f:
            f.write("stale_garbage_content")

        proc = subprocess.Popen(
            [str(DAEMON_BIN), "--foreground", "--no-supervisor", "--socket", stale_sock],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        try:
            time.sleep(0.5)
            # Socket should now be a real socket file, not our garbage file
            self.assertTrue(os.path.exists(stale_sock))
            ok, resp = send_socket_command(stale_sock, "PING")
            self.assertTrue(ok, f"Failed to connect to resurrected socket: {resp}")
        finally:
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=3)
            if proc.stdout: proc.stdout.close()
            if proc.stderr: proc.stderr.close()

    def test_b2_03_sudden_client_disconnect_mid_transaction(self):
        """B2.3: Client socket closes immediately after connecting without crashing the daemon."""
        sock_path = f"/tmp/lens_abrupt_{os.getpid()}.sock"
        proc = subprocess.Popen(
            [str(DAEMON_BIN), "--foreground", "--no-supervisor", "--socket", sock_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        try:
            time.sleep(0.5)
            # Connect and immediately close without sending data
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(sock_path)
            s.close()
            time.sleep(0.1)

            # Connect and send partial bytes without newline, then close
            s2 = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s2.connect(sock_path)
            s2.sendall(b"PIN")
            s2.close()
            time.sleep(0.1)

            # Verify daemon is still alive and responds to normal commands
            ok, resp = send_socket_command(sock_path, "PING")
            self.assertTrue(ok, f"Daemon died after abrupt disconnects: {resp}")
        finally:
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=3)
            if proc.stdout: proc.stdout.close()
            if proc.stderr: proc.stderr.close()

    def test_b2_04_rapid_successive_connection_burst(self):
        """B2.4: Daemon cleanly handles 25 rapid sequential connections in a burst."""
        sock_path = f"/tmp/lens_burst_{os.getpid()}.sock"
        proc = subprocess.Popen(
            [str(DAEMON_BIN), "--foreground", "--no-supervisor", "--socket", sock_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        try:
            time.sleep(0.5)
            for i in range(25):
                ok, resp = send_socket_command(sock_path, "PING", timeout_sec=1.0)
                self.assertTrue(ok, f"Connection #{i} failed: {resp}")
        finally:
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=3)
            if proc.stdout: proc.stdout.close()
            if proc.stderr: proc.stderr.close()

    def test_b2_05_oversized_payload_handling(self):
        """B2.5: Oversized input line (>64KB) is safely handled without buffer overflow."""
        sock_path = f"/tmp/lens_giant_{os.getpid()}.sock"
        proc = subprocess.Popen(
            [str(DAEMON_BIN), "--foreground", "--no-supervisor", "--socket", sock_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        try:
            time.sleep(0.5)
            giant_cmd = "BOGUS_CMD_" + ("X" * 65536) + "\n"
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(2.0)
            s.connect(sock_path)
            s.sendall(giant_cmd.encode("utf-8"))
            s.close()
            time.sleep(0.2)

            # Verify daemon is still healthy and operational
            ok, resp = send_socket_command(sock_path, "PING")
            self.assertTrue(ok, "Daemon crashed after oversized input")
        finally:
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=3)
            if proc.stdout: proc.stdout.close()
            if proc.stderr: proc.stderr.close()


if __name__ == "__main__":
    unittest.main()
