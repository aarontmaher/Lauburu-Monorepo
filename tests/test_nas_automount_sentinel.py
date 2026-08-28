"""
Milestone 5 Test Suite: Automated Mount Self-Healing Sentinel & Service Lifecycle.
Validates:
1. Sentinel v3 Architecture & Configuration Hierarchy (Tier 1 TB4 -> Tier 2 LAN -> Tier 3 Tailscale).
2. Host Server vs Client Mode Auto-Detection.
3. Fast Non-blocking TCP & HTTP Socket Probes.
4. Asynchronous 2.0s Threaded Mount IO Probes & Kernel Hang Prevention.
5. Persistent State Telemetry JSON (/tmp/nas_automount_state.json).
6. LaunchAgent Plist Configuration & Launchd Supervisor Status.
7. Live Execution of Sentinel CLI (--once, --status).
"""

import os
import sys
import time
import json
import socket
import plistlib
import subprocess
from pathlib import Path
import pytest

SENTINEL_SCRIPT = Path("/Users/aaron/.local/bin/nas_automount_sentinel.py")
LAUNCHAGENT_PLIST = Path("/Users/aaron/Library/LaunchAgents/com.lauburu.nasautomount.plist")
STATE_FILE = Path("/tmp/nas_automount_state.json")
LOG_FILE = Path("/tmp/nas_automount.log")

# Import functions directly from sentinel script
sys.path.insert(0, str(SENTINEL_SCRIPT.parent))
import nas_automount_sentinel as sentinel


class TestSentinelArchitectureAndConfig:
    """Validates configuration, candidate tiers, and host/client role detection."""

    def test_sentinel_script_exists_and_executable(self):
        """Verify sentinel script exists, is readable, and has execute bit set."""
        assert SENTINEL_SCRIPT.exists(), f"Sentinel script not found at {SENTINEL_SCRIPT}"
        assert os.access(SENTINEL_SCRIPT, os.X_OK), f"Sentinel script {SENTINEL_SCRIPT} is not executable"

    def test_tiered_candidate_hierarchy(self):
        """Verify Tier 1 prioritizes Thunderbolt 4 bridge0 (169.254.80.69:8888)."""
        candidates = sentinel.CANDIDATES
        assert len(candidates) >= 3, f"Expected at least 3 candidates, found {len(candidates)}"
        
        # Tier 1 Verification
        tier1 = candidates[0]
        assert "TB4" in tier1["tier"] or "Tier 1" in tier1["tier"], f"Unexpected tier 1 name: {tier1['tier']}"
        assert tier1["ip"] == "169.254.80.69", f"Tier 1 IP must be 169.254.80.69, got {tier1['ip']}"
        assert tier1["filer_port"] == 8888, f"Tier 1 filer port must be 8888, got {tier1['filer_port']}"
        assert tier1["master_port"] == 9333, f"Tier 1 master port must be 9333, got {tier1['master_port']}"

        # Tier 2 Verification
        tier2 = candidates[1]
        assert "LAN" in tier2["tier"] or "Tier 2" in tier2["tier"]
        assert tier2["ip"] == "192.168.8.230"

        # Tier 3 Verification
        tier3 = candidates[2]
        assert "Tailscale" in tier3["tier"] or "Tier 3" in tier3["tier"]
        assert tier3["ip"] == "100.119.199.76"

    def test_host_server_role_detection(self):
        """Verify sentinel correctly identifies Mac Mini M4 Pro as Host Server."""
        is_host = sentinel.is_local_host_server()
        assert is_host is True, "Host server detection must return True on Mac Mini M4 Pro"


class TestSocketProbesAndNonBlockingIO:
    """Validates non-blocking socket probes and async mount IO healthchecks."""

    def test_tcp_port_probes_on_active_seaweedfs(self):
        """Verify TCP port probes succeed on running SeaweedFS sub-services."""
        ip = "169.254.80.69"
        # Test Filer (8888)
        assert sentinel.check_tcp_port(ip, 8888, timeout=1.0) is True, f"Filer port 8888 on {ip} unreachable"
        # Test Master (9333)
        assert sentinel.check_tcp_port(ip, 9333, timeout=1.0) is True, f"Master port 9333 on {ip} unreachable"
        # Test Volume (8080)
        assert sentinel.check_tcp_port(ip, 8080, timeout=1.0) is True, f"Volume port 8080 on {ip} unreachable"
        # Test S3 Gateway (8333)
        assert sentinel.check_tcp_port(ip, 8333, timeout=1.0) is True, f"S3 port 8333 on {ip} unreachable"

    def test_tcp_port_probe_timeout_safety(self):
        """Verify TCP port probe to an unreachable IP returns False quickly without blocking."""
        t0 = time.time()
        result = sentinel.check_tcp_port("192.0.2.1", 9999, timeout=0.3)
        elapsed = time.time() - t0
        assert result is False, "Unreachable IP should return False"
        assert elapsed < 0.6, f"TCP probe took too long: {elapsed:.2f}s (expected <0.6s)"

    def test_http_endpoint_probes(self):
        """Verify HTTP endpoint checks return True on active Filer and Master."""
        assert sentinel.check_http_endpoint("http://169.254.80.69:8888/", timeout=2.0) is True
        assert sentinel.check_http_endpoint("http://127.0.0.1:8888/", timeout=2.0) is True
        assert sentinel.check_http_endpoint("http://169.254.80.69:9333/dir/status", timeout=2.0) is True

    def test_non_blocking_mount_probe_healthy_directory(self):
        """Verify is_mount_healthy completes within 2.0s on valid local NVMe path."""
        local_path = "/Users/aaron/Lauburu-Monorepo-Local/Lauburu-Monorepo"
        assert os.path.exists(local_path), f"Local NVMe path missing: {local_path}"
        
        t0 = time.time()
        healthy = sentinel.is_mount_healthy(local_path, timeout=2.0)
        elapsed = time.time() - t0
        
        assert healthy is True, f"Expected {local_path} to probe as healthy"
        assert elapsed < 0.5, f"Mount probe took too long: {elapsed:.3f}s"

    def test_non_blocking_mount_probe_missing_directory(self):
        """Verify is_mount_healthy returns False immediately for non-existent path."""
        t0 = time.time()
        healthy = sentinel.is_mount_healthy("/Volumes/non_existent_mock_mount_xyz", timeout=2.0)
        elapsed = time.time() - t0
        
        assert healthy is False
        assert elapsed < 0.1, f"Missing path probe took {elapsed:.3f}s"


class TestStateTelemetryAndExecution:
    """Validates live telemetry state JSON and CLI execution."""

    def test_run_cycle_host_mode(self):
        """Verify run_cycle executes and records healthy host state."""
        success = sentinel.run_cycle()
        assert success is True, "run_cycle should return True on healthy host"
        
        assert STATE_FILE.exists(), f"State file {STATE_FILE} was not created"
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
            
        assert state["version"] == "3.0.0"
        assert state["is_host"] is True
        assert state["status"] == "HEALTHY_HOST_SERVER"
        assert "TB4" in state["active_tier"]
        assert state["active_endpoint"] == "169.254.80.69:8888"
        assert state["seaweedfs_master"] == "HEALTHY"
        assert state["seaweedfs_filer"] == "HEALTHY"
        assert state["local_nvme_healthy"] is True
        assert state["tb4_ingress_active"] is True

    def test_cli_once_mode(self):
        """Verify sentinel executes cleanly with --once argument."""
        res = subprocess.run([sys.executable, str(SENTINEL_SCRIPT), "--once"], capture_output=True, text=True, timeout=5.0)
        assert res.returncode == 0, f"--once failed: {res.stderr}\n{res.stdout}"
        assert "Host Server Healthy" in res.stdout or "Host Server Healthy" in res.stderr

    def test_cli_status_mode(self):
        """Verify sentinel --status returns valid JSON telemetry."""
        res = subprocess.run([sys.executable, str(SENTINEL_SCRIPT), "--status"], capture_output=True, text=True, timeout=5.0)
        assert res.returncode == 0, f"--status failed: {res.stderr}\n{res.stdout}"
        status_data = json.loads(res.stdout)
        assert status_data["status"] == "HEALTHY_HOST_SERVER"
        assert status_data["is_host"] is True


class TestLaunchAgentSupervisor:
    """Validates LaunchAgent plist and launchd registration."""

    def test_launchagent_plist_syntax_and_fields(self):
        """Verify LaunchAgent plist exists, passes plutil, and has required keys."""
        assert LAUNCHAGENT_PLIST.exists(), f"LaunchAgent plist missing at {LAUNCHAGENT_PLIST}"
        
        with open(LAUNCHAGENT_PLIST, "rb") as f:
            plist = plistlib.load(f)
            
        assert plist["Label"] == "com.lauburu.nasautomount"
        assert plist["RunAtLoad"] is True
        assert plist["KeepAlive"] is True
        assert "/tmp/nas_automount.log" in plist["StandardOutPath"]
        assert plist["ProgramArguments"] == ["/usr/bin/python3", str(SENTINEL_SCRIPT)]

    def test_launchagent_service_running_in_launchd(self):
        """Verify com.lauburu.nasautomount is active and running in launchd."""
        res = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
        assert res.returncode == 0
        
        found = False
        for line in res.stdout.splitlines():
            if "com.lauburu.nasautomount" in line:
                found = True
                parts = line.split()
                pid_str = parts[0]
                assert pid_str != "-", f"com.lauburu.nasautomount is not running: {line}"
                print(f"[Launchd] com.lauburu.nasautomount is running with PID {pid_str}")
                break
                
        assert found, "com.lauburu.nasautomount not found in launchctl list"

    def test_log_file_contains_clean_v3_heartbeat(self):
        """Verify /tmp/nas_automount.log contains clean v3 heartbeat entries."""
        assert LOG_FILE.exists(), f"Log file {LOG_FILE} missing"
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            
        assert "[STORAGE-SENTINEL-v3]" in content, "Log missing [STORAGE-SENTINEL-v3] prefix"
        assert "Host Server Healthy" in content, "Log missing Host Server Healthy entries"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
