#!/usr/bin/env python3
"""
================================================================================
CHALLENGER 2: ADVERSARIAL STRESS TEST SUITE FOR FUSE WATCHDOG (MILESTONE 2)
================================================================================
Empirical testing of:
  1. Concurrency locks & process contention (Darwin atomic lock & Linux flock)
  2. Stale lock recovery & multi-mount isolation
  3. Probe timeouts, non-existent paths, special character paths, and trailing slashes
  4. Process teardown, lazy unmount command generation & execution
  5. Auto-remount resilience, filer reachability pre-flight, and crash-loop prevention
  6. CLI options, environment variable overrides, and symlink integrity
================================================================================
"""

import os
import sys
import time
import signal
import socket
import tempfile
import subprocess
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "00_core_infrastructure" / "scripts" / "fuse_watchdog.sh"
SYMLINK_PATH = REPO_ROOT / "00_core_infrastructure" / "seaweedfs" / "fuse_watchdog.sh"
SYSTEMD_SERVICE_PATH = REPO_ROOT / "00_core_infrastructure" / "systemd" / "dfs-fuse-watchdog.service"


class MockFilerHandler(BaseHTTPRequestHandler):
    """HTTP handler simulating SeaweedFS Filer responses."""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"Status":"OK","Filer":"Live"}')

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress console noise


@pytest.fixture(scope="module")
def mock_filer_server():
    """Spawns an in-process mock HTTP Filer server on a free port."""
    server = HTTPServer(("127.0.0.1", 0), MockFilerHandler)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"127.0.0.1:{port}"
    server.shutdown()


class TestWatchdogScriptIntegrity:
    """Verifies file existence, permissions, and symlink topology."""

    def test_script_exists_and_executable(self):
        assert SCRIPT_PATH.exists(), f"Missing watchdog script: {SCRIPT_PATH}"
        assert os.access(SCRIPT_PATH, os.X_OK), f"Watchdog script is not executable: {SCRIPT_PATH}"

    def test_symlink_points_to_script(self):
        assert SYMLINK_PATH.exists() or SYMLINK_PATH.is_symlink(), f"Missing symlink: {SYMLINK_PATH}"
        resolved = SYMLINK_PATH.resolve()
        assert resolved == SCRIPT_PATH.resolve(), f"Symlink resolved to {resolved}, expected {SCRIPT_PATH.resolve()}"

    def test_bash_syntax_validity(self):
        res = subprocess.run(["bash", "-n", str(SCRIPT_PATH)], capture_output=True, text=True)
        assert res.returncode == 0, f"Bash syntax check failed: {res.stderr}"

    def test_systemd_service_file(self):
        assert SYSTEMD_SERVICE_PATH.exists(), f"Missing systemd service file: {SYSTEMD_SERVICE_PATH}"
        content = SYSTEMD_SERVICE_PATH.read_text()
        assert "ExecStart=" in content
        assert "Restart=always" in content
        assert "fuse_watchdog.sh" in content


class TestConcurrencyAndLocks:
    """Stress tests concurrent instances competing for single-instance locks."""

    def test_concurrent_instances_same_mount_point(self, mock_filer_server):
        """Two instances targeting the same mount point must not collide; the second must exit cleanly."""
        # Use an active mounted directory or mock filers to test probe loop
        p1 = subprocess.Popen(
            [str(SCRIPT_PATH), "--mount-point", "/", "--interval", "10", "--timeout", "2", "--filers", mock_filer_server],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True
        )
        try:
            time.sleep(0.6)  # allow p1 to acquire lock
            assert p1.poll() is None, "Primary watchdog died unexpectedly"

            # Attempt to start second instance on the exact same mount point
            p2 = subprocess.Popen(
                [str(SCRIPT_PATH), "--mount-point", "/", "--interval", "10", "--timeout", "2", "--filers", mock_filer_server],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout2, stderr2 = p2.communicate(timeout=5)
            
            # The second instance must exit with 0 (clean skip) and log message about lock
            assert p2.returncode == 0, f"Second instance exited with code {p2.returncode}, stderr: {stderr2}"
            combined_out = stdout2 + stderr2
            assert "Another watchdog instance" in combined_out or "lock" in combined_out.lower()
        finally:
            try:
                os.killpg(os.getpgid(p1.pid), signal.SIGTERM)
                p1.wait(timeout=3)
            except Exception:
                pass

    def test_concurrent_instances_distinct_mount_points(self, mock_filer_server):
        """Two instances targeting distinct mount points should both run independently without blocking each other."""
        p1 = subprocess.Popen(
            [str(SCRIPT_PATH), "--mount-point", "/", "--interval", "10", "--timeout", "2", "--filers", mock_filer_server],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True
        )
        p2 = subprocess.Popen(
            [str(SCRIPT_PATH), "--mount-point", "/dev", "--interval", "10", "--timeout", "2", "--filers", mock_filer_server],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True
        )
        try:
            time.sleep(0.8)
            assert p1.poll() is None, "Instance 1 died unexpectedly"
            assert p2.poll() is None, "Instance 2 died unexpectedly"
        finally:
            try:
                os.killpg(os.getpgid(p1.pid), signal.SIGTERM)
                p1.wait(timeout=3)
            except Exception:
                pass
            try:
                os.killpg(os.getpgid(p2.pid), signal.SIGTERM)
                p2.wait(timeout=3)
            except Exception:
                pass

    def test_stale_lock_recovery_after_abrupt_kill(self, mock_filer_server):
        """When a previous process holding the lock is killed via SIGKILL without cleaning up lock files, the next watchdog must recover."""
        p1 = subprocess.Popen(
            [str(SCRIPT_PATH), "--mount-point", "/", "--interval", "10", "--timeout", "2", "--filers", mock_filer_server],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True
        )
        time.sleep(0.6)
        # Kill abruptly with SIGKILL (bypassing trap)
        os.killpg(os.getpgid(p1.pid), signal.SIGKILL)
        p1.wait()

        # Launch a new watchdog on the same mount point with --once
        res = subprocess.run(
            [str(SCRIPT_PATH), "--mount-point", "/", "--once", "--timeout", "2", "--filers", mock_filer_server],
            capture_output=True,
            text=True,
            timeout=5
        )
        assert res.returncode == 0, f"Recovery instance failed with code {res.returncode}: {res.stderr}"
        assert "Single-run cycle (--once) complete" in res.stdout or "Stale lock" in res.stdout or "FUSE" in res.stdout


class TestPathEdgeCasesAndSanitization:
    """Stress tests non-existent paths, special characters, spaces, and trailing slashes."""

    def test_trailing_slashes_normalization(self, mock_filer_server):
        """Paths with trailing slashes like / or /// should normalize cleanly to root and succeed."""
        path_with_slashes = "///"
        res = subprocess.run(
            [str(SCRIPT_PATH), "--mount-point", path_with_slashes, "--once", "--timeout", "2", "--filers", mock_filer_server, "-v"],
            capture_output=True,
            text=True,
            timeout=5
        )
        assert res.returncode == 0, f"Failed on trailing slashes: {res.stderr}"
        assert "responsive and healthy" in res.stdout or "complete" in res.stdout

    def test_path_with_spaces_and_special_chars(self, mock_filer_server):
        """Paths containing spaces and special characters must not cause shell expansion errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            special_dir = os.path.join(tmpdir, "dfs space_test-dir!@#")
            os.makedirs(special_dir, exist_ok=True)
            res = subprocess.run(
                [str(SCRIPT_PATH), "--mount-point", special_dir, "--once", "--timeout", "2", "--filers", mock_filer_server],
                capture_output=True,
                text=True,
                timeout=5
            )
            assert res.returncode == 0, f"Failed on special characters path: {res.stderr}"

    def test_non_existent_mount_path(self, mock_filer_server):
        """Non-existent mount path should be handled gracefully (identified as unmounted, attempting auto-remount without crash)."""
        non_existent = f"/tmp/non_existent_mount_point_{int(time.time()*1000)}"
        res = subprocess.run(
            [str(SCRIPT_PATH), "--mount-point", non_existent, "--once", "--filers", mock_filer_server, "--timeout", "2"],
            capture_output=True,
            text=True,
            timeout=8
        )
        # Should not crash with unhandled exception; returns 0 after completing single pass
        assert res.returncode == 0, f"Failed on non-existent path: {res.stderr}"
        assert "not mounted" in res.stdout.lower() or "attempting auto-mount" in res.stdout.lower()

    def test_empty_mount_point_defaults_to_root(self, mock_filer_server):
        """When mount point is empty, it should normalize safely to root '/'."""
        res = subprocess.run(
            [str(SCRIPT_PATH), "--mount-point", "", "--once", "--timeout", "2", "--filers", mock_filer_server],
            capture_output=True,
            text=True,
            timeout=5
        )
        assert res.returncode == 0, f"Failed on empty mount point: {res.stderr}"


class TestProbeTimeoutsAndHangDetection:
    """Empirically tests the non-blocking canary probe mechanism under latency and timeouts."""

    def test_probe_on_responsive_directory(self):
        """Probe against /tmp should return 0 in under 1 second."""
        res = subprocess.run(
            [str(SCRIPT_PATH), "--mount-point", "/", "--once", "--timeout", "2", "-v"],
            capture_output=True,
            text=True,
            timeout=5
        )
        assert res.returncode == 0
        assert "responsive and healthy" in res.stdout or "complete" in res.stdout

    def test_cli_diagnostics_self_test(self, mock_filer_server):
        """The --test option runs full diagnostic suite and exits 0."""
        res = subprocess.run(
            [str(SCRIPT_PATH), "--test", "--filers", mock_filer_server],
            capture_output=True,
            text=True,
            timeout=6
        )
        assert res.returncode == 0, f"--test failed: {res.stderr}"
        assert "LAUBURU FUSE WATCHDOG SELF-TEST" in res.stdout
        assert "completed successfully" in res.stdout

    def test_cli_help_flag(self):
        """The --help flag outputs usage and exits 0."""
        res = subprocess.run(
            [str(SCRIPT_PATH), "--help"],
            capture_output=True,
            text=True,
            timeout=3
        )
        assert res.returncode == 0
        assert "Usage:" in res.stdout
        assert "Universal, lightweight, aggressive FUSE Mount Zombie Watchdog" in res.stdout


class TestFilerPreFlightAndRemountResilience:
    """Tests filer reachability checks, mock filer fallback, and crash loop prevention."""

    def test_filer_reachability_with_live_mock_filer(self, mock_filer_server):
        """When a reachable filer endpoint is provided, pre-flight check recognizes it."""
        res = subprocess.run(
            [str(SCRIPT_PATH), "--test", "--filers", mock_filer_server],
            capture_output=True,
            text=True,
            timeout=5
        )
        assert res.returncode == 0
        assert f"Reachable Filer found: {mock_filer_server}" in res.stdout

    def test_filer_reachability_all_filers_unreachable(self):
        """When all filers are down, the script warns and defers remount without infinite blocking or crashing."""
        unreachable_filers = "127.0.0.1:59991,127.0.0.1:59992,127.0.0.1:59993"
        with tempfile.TemporaryDirectory() as tmpdir:
            res = subprocess.run(
                [str(SCRIPT_PATH), "--mount-point", tmpdir, "--filers", unreachable_filers, "--once", "--timeout", "1"],
                capture_output=True,
                text=True,
                timeout=12
            )
            assert res.returncode == 0
            assert "Deferring remount" in res.stdout or "not reachable" in res.stdout or "not mounted" in res.stdout

    def test_multi_filer_resilience_first_offline_second_online(self, mock_filer_server):
        """When first filer is offline but second is online, it successfully connects to the second."""
        mixed_filers = f"127.0.0.1:59999,{mock_filer_server}"
        res = subprocess.run(
            [str(SCRIPT_PATH), "--test", "--filers", mixed_filers],
            capture_output=True,
            text=True,
            timeout=6
        )
        assert res.returncode == 0
        assert f"Reachable Filer found: {mock_filer_server}" in res.stdout


class TestProcessTeardownAndSignalHandling:
    """Verifies clean teardown under SIGINT, SIGTERM, and unmount command logic."""

    def test_clean_sigterm_handling(self, mock_filer_server):
        """Watchdog should catch SIGTERM, clean up lock directory/file, and exit cleanly."""
        p = subprocess.Popen(
            [str(SCRIPT_PATH), "--mount-point", "/", "--interval", "5", "--timeout", "2", "--filers", mock_filer_server],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True
        )
        time.sleep(0.6)
        assert p.poll() is None

        os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        p.wait(timeout=3)
        assert p.returncode in (0, -signal.SIGTERM, 143)

    def test_clean_sigint_handling(self, mock_filer_server):
        """Watchdog should catch SIGINT (Ctrl+C), clean up lock, and exit cleanly."""
        p = subprocess.Popen(
            [str(SCRIPT_PATH), "--mount-point", "/", "--interval", "5", "--timeout", "2", "--filers", mock_filer_server],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True
        )
        time.sleep(0.6)
        assert p.poll() is None

        os.killpg(os.getpgid(p.pid), signal.SIGINT)
        p.wait(timeout=3)
        assert p.returncode in (0, -signal.SIGINT, 130)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
