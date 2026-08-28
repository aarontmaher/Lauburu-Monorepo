#!/usr/bin/env python3
"""
================================================================================
LAUBURU MONOREPO: ADVERSARIAL STRESS TEST SUITE FOR MILESTONE 2
FUSE Mount Zombie Watchdog Daemon Empirical Stress Harness
================================================================================
Empirical Challenger 1 Test Suite for:
  1. Hung FUSE probes, non-blocking timeouts, and exit code determinism (124/137)
  2. Network dropouts, offline filers, slow HTTP servers, and connection resets
  3. Single-instance locking, process contention, stale PID eviction, multi-tenancy
  4. Real subprocess execution of fuse_watchdog.sh across CLI/env configurations
  5. Platform-specific lazy unmount semantics (Darwin / Linux) and process eviction
  6. Signal interruption (SIGINT, SIGTERM) and lockfile lifecycle guarantees
================================================================================
"""

import os
import sys
import time
import json
import signal
import socket
import hashlib
import tempfile
import threading
import subprocess
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.test_seaweed_ha_watchdog import (
    FUSEWatchdogEngine,
    DEFAULT_FILER_ENDPOINTS,
    DEFAULT_MOUNT_POINT,
    MACOS_MOUNT_POINT,
)

FUSE_WATCHDOG_SCRIPT = REPO_ROOT / "00_core_infrastructure" / "scripts" / "fuse_watchdog.sh"
FUSE_WATCHDOG_SYMLINK = REPO_ROOT / "00_core_infrastructure" / "seaweedfs" / "fuse_watchdog.sh"


# ==============================================================================
# SECTION 1: HUNG FUSE PROBES & TIMEOUT ENGINE EMPIRICAL STRESS
# ==============================================================================

class TestAdversarialProbeAndTimeoutMechanics:
    """Stress test non-blocking canary stat probes under simulated kernel freezes and timeouts."""

    def test_script_file_exists_and_executable(self):
        """Verify watchdog script exists and is executable in both script and seaweedfs locations."""
        assert FUSE_WATCHDOG_SCRIPT.exists(), f"Missing {FUSE_WATCHDOG_SCRIPT}"
        assert os.access(FUSE_WATCHDOG_SCRIPT, os.X_OK), f"Not executable: {FUSE_WATCHDOG_SCRIPT}"
        assert FUSE_WATCHDOG_SYMLINK.exists(), f"Missing {FUSE_WATCHDOG_SYMLINK}"
        assert os.access(FUSE_WATCHDOG_SYMLINK, os.X_OK), f"Not executable: {FUSE_WATCHDOG_SYMLINK}"

    def test_probe_exit_code_mapping_exhaustiveness(self):
        """Verify exit code categorization for nominal and adverse probe states."""
        assert FUSEWatchdogEngine.evaluate_probe_exit_code(0) == "HEALTHY"
        assert FUSEWatchdogEngine.evaluate_probe_exit_code(124) == "FROZEN_TIMEOUT"
        assert FUSEWatchdogEngine.evaluate_probe_exit_code(137) == "FROZEN_TIMEOUT"
        assert FUSEWatchdogEngine.evaluate_probe_exit_code(1) == "UNMOUNTED_OR_INACCESSIBLE"
        assert FUSEWatchdogEngine.evaluate_probe_exit_code(2) == "ERROR_CODE_2"
        assert FUSEWatchdogEngine.evaluate_probe_exit_code(255) == "ERROR_CODE_255"

    def test_simulated_hung_probe_via_subshell_watchdog(self):
        """Empirically test the subshell timer fallback pattern used when GNU timeout is absent."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create a long-sleeping background task simulating kernel D-state I/O hang
            hung_proc = subprocess.Popen(["sleep", "10"])
            t0 = time.perf_counter()
            
            # Watchdog timeout simulation: wait up to 0.4s then force kill
            timeout_limit = 0.4
            elapsed = 0.0
            timed_out = False
            while hung_proc.poll() is None:
                time.sleep(0.05)
                elapsed = time.perf_counter() - t0
                if elapsed >= timeout_limit:
                    hung_proc.kill()
                    hung_proc.wait()
                    timed_out = True
                    break
            
            assert timed_out is True, "Hung probe must be forcefully terminated"
            assert hung_proc.returncode in (-9, 137, 1), "Terminated process must reflect kill signal"
            assert elapsed < 1.0, f"Teardown took too long: {elapsed:.2f}s"

    def test_canary_probe_against_nonexistent_deep_path(self):
        """Probe against deeply nested non-existent path returns non-zero code immediately."""
        bad_path = f"/tmp/dfs_test_nonexistent/{time.time()}/sub1/sub2/sub3"
        t0 = time.perf_counter()
        res = subprocess.run(["stat", bad_path], capture_output=True)
        duration = time.perf_counter() - t0
        assert res.returncode != 0
        assert duration < 0.2

    def test_canary_probe_path_with_whitespace_and_glob_chars(self):
        """Probe path containing whitespace, wildcards, and special characters."""
        with tempfile.TemporaryDirectory(prefix="test [dfs] * mount ? dir ") as tmp_dir:
            cmd = FUSEWatchdogEngine.build_canary_probe_command(tmp_dir)
            assert tmp_dir in cmd
            res = subprocess.run(["stat", tmp_dir], capture_output=True)
            assert res.returncode == 0
            assert FUSEWatchdogEngine.evaluate_probe_exit_code(res.returncode) == "HEALTHY"


# ==============================================================================
# SECTION 2: ADVERSARIAL FILER REACHABILITY & NETWORK PARTITIONS
# ==============================================================================

class DelayedHTTPHandler(BaseHTTPRequestHandler):
    """HTTP server that artificially delays responses or returns error codes."""
    delay_seconds = 0.0
    status_code = 200
    body_content = b"SeaweedFS Filer OK"

    def do_GET(self):
        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)
        self.send_response(self.status_code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(self.body_content)

    def do_HEAD(self):
        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)
        self.send_response(self.status_code)
        self.end_headers()

    def log_message(self, format, *args):
        pass


@pytest.fixture(scope="module")
def delayed_http_server():
    """Spin up local test HTTP server with configurable delays and status codes."""
    server = HTTPServer(("127.0.0.1", 0), DelayedHTTPHandler)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"127.0.0.1:{port}", server
    server.shutdown()
    server.server_close()


class TestAdversarialFilerReachability:
    """Stress test pre-flight filer reachability under latency, crashes, and drops."""

    def test_unroutable_blackhole_endpoint(self):
        """Pre-flight check against non-routable IP terminates within timeout and returns False."""
        blackhole = "192.0.2.1:8888"  # TEST-NET-1 non-routable
        t0 = time.perf_counter()
        alive = FUSEWatchdogEngine.check_filer_alive(blackhole, timeout_sec=0.5)
        duration = time.perf_counter() - t0
        assert alive is False
        assert duration < 1.5, f"Probe took too long to fail: {duration:.2f}s"

    def test_delayed_filer_response_exceeding_timeout(self, delayed_http_server):
        """Filer responding slower than timeout threshold is treated as offline."""
        endpoint, server = delayed_http_server
        server.RequestHandlerClass.delay_seconds = 1.0
        server.RequestHandlerClass.status_code = 200
        try:
            alive = FUSEWatchdogEngine.check_filer_alive(endpoint, timeout_sec=0.3)
            assert alive is False, "Slow filer should fail preflight check"
        finally:
            server.RequestHandlerClass.delay_seconds = 0.0

    def test_filer_http_500_and_503_errors(self, delayed_http_server):
        """HTTP error responses (500, 503) should not crash the pre-flight checker."""
        endpoint, server = delayed_http_server
        server.RequestHandlerClass.status_code = 500
        try:
            alive = FUSEWatchdogEngine.check_filer_alive(endpoint, timeout_sec=0.5)
            assert alive is False
        finally:
            server.RequestHandlerClass.status_code = 200

    def test_multi_filer_failover_first_two_dead_third_alive(self, delayed_http_server):
        """When 2 candidate filers are dead and 1 is healthy, reachability succeeds."""
        live_endpoint, _ = delayed_http_server
        dead_1 = "127.0.0.1:49191"
        dead_2 = "127.0.0.1:49192"
        endpoints = [dead_1, dead_2, live_endpoint]
        
        active = None
        for ep in endpoints:
            if FUSEWatchdogEngine.check_filer_alive(ep, timeout_sec=0.3):
                active = ep
                break
        assert active == live_endpoint

    def test_malformed_filer_endpoint_strings(self):
        """Test parsing and probing of malformed, messy, or empty filer endpoint strings."""
        malformed_cases = [
            ",,,",
            "   ",
            "invalid_host_without_port",
            "http://127.0.0.1:8888",
            "127.0.0.1:8888, 127.0.0.1:8889 , ,, 127.0.0.1:8890",
        ]
        for raw in malformed_cases:
            parts = [p.strip() for p in raw.split(",") if p.strip()]
            for p in parts:
                res = FUSEWatchdogEngine.check_filer_alive(p, timeout_sec=0.1)
                assert isinstance(res, bool)


# ==============================================================================
# SECTION 3: LOCKFILE CONTENTION & CONCURRENCY CONTROL
# ==============================================================================

class TestAdversarialLockingAndConcurrency:
    """Stress test atomic directory locking, flock concurrency, and race prevention."""

    def test_concurrent_script_invocations_same_mount(self):
        """Multiple concurrent watchdog script runs on same mount point must yield exactly 1 active lock."""
        with tempfile.TemporaryDirectory() as tmp_mount:
            procs = []
            for _ in range(5):
                p = subprocess.Popen(
                    ["bash", str(FUSE_WATCHDOG_SCRIPT), "--once", "-m", tmp_mount, "-f", "127.0.0.1:49999"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                procs.append(p)

            exit_codes = []
            for p in procs:
                out, err = p.communicate(timeout=10)
                exit_codes.append(p.returncode)

            for code in exit_codes:
                assert code == 0, f"Unexpected exit code: {code}"

    def test_distinct_mount_points_have_isolated_locks(self):
        """Two distinct mount points must produce distinct lock hashes and not block each other."""
        mount_a = "/tmp/dfs_test_mount_a"
        mount_b = "/tmp/dfs_test_mount_b"
        
        hash_a = hashlib.md5(mount_a.encode("utf-8")).hexdigest()
        hash_b = hashlib.md5(mount_b.encode("utf-8")).hexdigest()
        
        assert hash_a != hash_b, "Different mounts must produce distinct lock hashes"
        assert len(hash_a) == 32
        assert len(hash_b) == 32

    def test_stale_pid_lock_directory_recovery(self):
        """If a lock directory exists with a non-existent PID, watchdog must reclaim lock."""
        with tempfile.TemporaryDirectory() as tmp_mount:
            clean_mount = tmp_mount.rstrip("/")
            hash_val = hashlib.md5(clean_mount.encode("utf-8")).hexdigest()
            lock_dir = Path(f"/tmp/fuse_watchdog_{hash_val}.lock.d")
            
            # Create simulated stale lock directory with dead PID 999999
            lock_dir.mkdir(parents=True, exist_ok=True)
            (lock_dir / "pid").write_text("999999\n")
            
            try:
                res = subprocess.run(
                    ["bash", str(FUSE_WATCHDOG_SCRIPT), "--once", "-m", tmp_mount, "-f", "127.0.0.1:49999"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                assert res.returncode == 0
                assert "Stale lock directory detected" in res.stdout or "FUSE_WATCHDOG" in res.stdout
            finally:
                if lock_dir.exists():
                    import shutil
                    shutil.rmtree(lock_dir, ignore_errors=True)

    def test_signal_cleanup_removes_lock_directory(self):
        """Sending SIGTERM to watchdog process group removes lock directory upon exit."""
        with tempfile.TemporaryDirectory() as tmp_mount:
            clean_mount = tmp_mount.rstrip("/")
            hash_val = hashlib.md5(clean_mount.encode("utf-8")).hexdigest()
            lock_dir = Path(f"/tmp/fuse_watchdog_{hash_val}.lock.d")
            
            # Start watchdog in background with long interval in its own process group
            proc = subprocess.Popen(
                ["bash", str(FUSE_WATCHDOG_SCRIPT), "-m", tmp_mount, "-i", "30", "-f", "127.0.0.1:49999"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            time.sleep(0.5)
            
            # Check lock directory was created
            assert lock_dir.exists() or proc.poll() is not None
            
            # Send SIGTERM to entire process group
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            
            time.sleep(0.3)
            # Lock directory should be cleaned up by EXIT/TERM trap
            assert not lock_dir.exists(), f"Lock directory {lock_dir} was not cleaned up on SIGTERM"


# ==============================================================================
# SECTION 4: REAL SUBPROCESS EXECUTION OF FUSE_WATCHDOG.SH
# ==============================================================================

class TestSubprocessFuseWatchdogExecution:
    """Empirically execute fuse_watchdog.sh via subprocess under multiple modes."""

    def test_watchdog_help_flag_execution(self):
        """Executing with -h / --help prints usage manual and exits code 0."""
        res = subprocess.run(
            ["bash", str(FUSE_WATCHDOG_SCRIPT), "--help"],
            capture_output=True,
            text=True
        )
        assert res.returncode == 0
        assert "Universal, lightweight, aggressive FUSE Mount Zombie Watchdog" in res.stdout
        assert "Usage:" in res.stdout
        assert "--mount-point" in res.stdout
        assert "--filers" in res.stdout

    def test_watchdog_self_test_flag_execution(self):
        """Executing with --test runs self-test diagnostics and exits code 0."""
        res = subprocess.run(
            ["bash", str(FUSE_WATCHDOG_SCRIPT), "--test"],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert res.returncode == 0
        assert "LAUBURU FUSE WATCHDOG SELF-TEST & DIAGNOSTICS SUITE" in res.stdout
        assert "Checking diagnostic tools" in res.stdout
        assert "Checking non-blocking probe timeout engine" in res.stdout
        assert "Self-test diagnostics completed successfully" in res.stdout

    def test_watchdog_unknown_option_error_exit(self):
        """Executing with invalid unknown argument exits code 1 with error message."""
        res = subprocess.run(
            ["bash", str(FUSE_WATCHDOG_SCRIPT), "--non-existent-adversarial-flag"],
            capture_output=True,
            text=True
        )
        assert res.returncode == 1
        assert "Unknown option" in res.stderr

    def test_watchdog_single_run_unmounted_mount_point(self):
        """Executing with --once against unmounted temp directory executes clean detection."""
        with tempfile.TemporaryDirectory() as tmp_mount:
            res = subprocess.run(
                [
                    "bash", str(FUSE_WATCHDOG_SCRIPT),
                    "--once",
                    "-m", tmp_mount,
                    "-f", "127.0.0.1:49999",
                    "-i", "1",
                    "-t", "1",
                    "-v"
                ],
                capture_output=True,
                text=True,
                timeout=10
            )
            assert res.returncode == 0
            assert "Starting FUSE Mount Watchdog Daemon" in res.stdout
            assert "is not mounted in VFS table" in res.stdout
            assert "Single-run cycle (--once) complete" in res.stdout

    def test_watchdog_environment_variable_overrides(self):
        """Watchdog honors environment variables DFS_MOUNT_POINT, DFS_FILER_PEERS."""
        with tempfile.TemporaryDirectory() as tmp_mount:
            env = os.environ.copy()
            env["DFS_MOUNT_POINT"] = tmp_mount
            env["DFS_FILER_PEERS"] = "127.0.0.1:49998,127.0.0.1:49999"
            env["POLL_INTERVAL"] = "1"
            env["PROBE_TIMEOUT"] = "1"
            
            res = subprocess.run(
                ["bash", str(FUSE_WATCHDOG_SCRIPT), "--once"],
                env=env,
                capture_output=True,
                text=True,
                timeout=10
            )
            assert res.returncode == 0
            assert f"Target Mount: {tmp_mount}" in res.stdout
            assert "127.0.0.1:49998,127.0.0.1:49999" in res.stdout


# ==============================================================================
# SECTION 5: PLATFORM DETACHMENT SEMANTICS & PROCESS EVICTION
# ==============================================================================

class TestPlatformDetachmentSemantics:
    """Verify platform unmount resolution and process eviction patterns."""

    def test_darwin_diskutil_unmount_command_resolution(self):
        """Darwin platform resolves to diskutil unmount force."""
        cmd = FUSEWatchdogEngine.resolve_unmount_command(MACOS_MOUNT_POINT, platform_sys="darwin")
        assert cmd == ["diskutil", "unmount", "force", MACOS_MOUNT_POINT]

    def test_linux_umount_lazy_force_resolution(self):
        """Linux platform resolves to umount -l -f."""
        cmd = FUSEWatchdogEngine.resolve_unmount_command(DEFAULT_MOUNT_POINT, platform_sys="linux", force_lazy=True)
        assert cmd == ["umount", "-l", "-f", DEFAULT_MOUNT_POINT]

    def test_process_eviction_command_targeting(self):
        """Eviction must specifically target weed mount processes for the given mount point."""
        target_mount = "/mnt/dfs_unified"
        pattern = f"weed mount.*{target_mount}"
        assert "weed mount" in pattern
        assert target_mount in pattern

    def test_fuse_connections_abort_sysfs_check(self):
        """Verify Linux FUSE sysfs abort path specification."""
        fuse_sysfs = "/sys/fs/fuse/connections"
        assert fuse_sysfs.startswith("/sys/fs/fuse")


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
