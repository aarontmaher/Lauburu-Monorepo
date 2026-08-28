#!/usr/bin/env python3
"""
================================================================================
LAUBURU MONOREPO: SEAWEEDFS PIXEL VOLUME DAEMON & R2 CLOUD TIERING TEST SUITE
================================================================================
Comprehensive test suite verifying:
  1. Termux-compatible Pixel 10 Pro XL SeaweedFS Volume Daemon (pixel_volume_daemon.sh)
  2. Cloudflare R2 Remote Storage & Volume Tiering Configuration (r2_tiering_config.json)
  3. Pre-flight diagnostics, CLI flags, process lifecycle, signal trapping, and schema fidelity

Usage:
  pytest tests/test_pixel_volume_and_r2_tiering.py -v
================================================================================
"""

import json
import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DAEMON_SCRIPT = REPO_ROOT / "00_core_infrastructure" / "seaweedfs" / "pixel_volume_daemon.sh"
R2_CONFIG = REPO_ROOT / "00_core_infrastructure" / "seaweedfs" / "r2_tiering_config.json"


# ==============================================================================
# 1. PIXEL VOLUME DAEMON (pixel_volume_daemon.sh) TESTS
# ==============================================================================

class TestPixelVolumeDaemon:
    """Validates pixel_volume_daemon.sh script syntax, metadata, and CLI behavior."""

    def test_daemon_script_exists_and_executable(self):
        """Verifies the daemon script exists and has executable permissions."""
        assert DAEMON_SCRIPT.is_file(), f"Expected {DAEMON_SCRIPT} to exist."
        file_stat = os.stat(DAEMON_SCRIPT)
        assert bool(file_stat.st_mode & stat.S_IXUSR), "Script must have user executable permission."

    def test_daemon_script_shebang_and_fallback(self):
        """Verifies Termux shebang and POSIX fallback logic."""
        content = DAEMON_SCRIPT.read_text(encoding="utf-8")
        lines = content.splitlines()
        assert len(lines) > 0
        assert lines[0].strip() == "#!/data/data/com.termux/files/usr/bin/bash", (
            "Shebang must point to Termux bash path."
        )
        assert "BASH_VERSION" in content, "Must include bash version verification."
        assert "/data/data/com.termux/files/usr/bin/bash" in content
        assert "/bin/bash" in content

    def test_daemon_script_bash_syntax_check(self):
        """Runs `bash -n` to ensure 0 syntax errors."""
        res = subprocess.run(["bash", "-n", str(DAEMON_SCRIPT)], capture_output=True, text=True)
        assert res.returncode == 0, f"bash -n failed with stderr:\n{res.stderr}"

    def test_daemon_script_default_constants(self):
        """Verifies canonical defaults matching network topology and hardware matrix."""
        content = DAEMON_SCRIPT.read_text(encoding="utf-8")
        assert "/data/data/com.termux/files/home/storage/shared/seaweedfs" in content, (
            "Default storage partition must be 500GB Termux shared storage path."
        )
        assert "100.119.199.76:9333" in content, "Default Master must be Mac Mini Master."
        assert "100.73.38.87" in content, "Default Node IP must be Pixel 10 Pro XL Tailscale IP."
        assert "termux-wake-lock" in content, "Must handle Android wake-lock acquisition."
        assert "termux-wake-unlock" in content, "Must handle Android wake-lock release."
        assert "termux-setup-storage" in content, "Must mention termux-setup-storage for permission validation."

    def test_daemon_script_help_flag(self):
        """Verifies `--help`, `-h`, and `help` actions return usage and exit 0."""
        for flag in ["--help", "-h", "help"]:
            res = subprocess.run(["bash", str(DAEMON_SCRIPT), flag], capture_output=True, text=True)
            assert res.returncode == 0, f"Expected {flag} to exit 0. Got {res.returncode}"
            assert "Usage:" in res.stdout
            assert "Pixel 10 Pro XL" in res.stdout
            assert "100.119.199.76:9333" in res.stdout

    def test_daemon_script_preflight_test_flag(self):
        """Verifies `--test` / `test` action runs non-destructive preflight diagnostics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            res = subprocess.run(
                [
                    "bash", str(DAEMON_SCRIPT), "--test",
                    "-dir", tmpdir,
                    "--pid-file", f"{tmpdir}/test.pid",
                    "--log-file", f"{tmpdir}/test.log",
                ],
                capture_output=True,
                text=True
            )
            # The test will complete and report status
            assert "PRE-FLIGHT TEST" in res.stdout
            assert "Storage Directory:" in res.stdout
            assert "Target Master:" in res.stdout

    def test_daemon_script_status_when_stopped(self):
        """Verifies status command correctly reports stopped state when no PID file is present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            res = subprocess.run(
                [
                    "bash", str(DAEMON_SCRIPT), "status",
                    "--pid-file", f"{tmpdir}/nonexistent.pid"
                ],
                capture_output=True,
                text=True
            )
            assert "STOPPED" in res.stdout

    def test_daemon_script_stop_idempotence(self):
        """Verifies stopping when already stopped exits cleanly without error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            res = subprocess.run(
                [
                    "bash", str(DAEMON_SCRIPT), "stop",
                    "--pid-file", f"{tmpdir}/nonexistent.pid"
                ],
                capture_output=True,
                text=True
            )
            assert res.returncode == 0
            assert "No active" in res.stdout or "stopped" in res.stdout.lower()


# ==============================================================================
# 2. CLOUDFLARE R2 TIERING CONFIG (r2_tiering_config.json) TESTS
# ==============================================================================

class TestR2TieringConfig:
    """Validates r2_tiering_config.json schema, S3 compatibility, and tiering parameters."""

    def test_r2_config_file_exists(self):
        """Verifies r2_tiering_config.json exists."""
        assert R2_CONFIG.is_file(), f"Expected {R2_CONFIG} to exist."

    def test_r2_config_valid_json(self):
        """Verifies r2_tiering_config.json is strictly valid RFC 8259 JSON."""
        content = R2_CONFIG.read_text(encoding="utf-8")
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            pytest.fail(f"Invalid JSON in {R2_CONFIG}: {exc}")
        assert isinstance(data, dict)

    def test_r2_config_remote_storage_structure(self):
        """Validates the remote_storage block structure and S3 parameters."""
        data = json.loads(R2_CONFIG.read_text(encoding="utf-8"))
        assert "remote_storage" in data, "Missing 'remote_storage' top-level key."
        rs = data["remote_storage"]
        assert rs.get("type") == "s3", "Remote storage type must be 's3'."
        assert "s3" in rs, "Missing 's3' configuration object."
        
        s3 = rs["s3"]
        assert s3.get("force_path_style") is True, "Cloudflare R2 requires force_path_style: true."
        assert "${R2_ACCESS_KEY}" in s3.get("access_key", ""), "Must use ${R2_ACCESS_KEY} placeholder."
        assert "${R2_SECRET_KEY}" in s3.get("secret_key", ""), "Must use ${R2_SECRET_KEY} placeholder."
        assert "${R2_ENDPOINT}" in s3.get("endpoint", ""), "Must use ${R2_ENDPOINT} placeholder."
        assert "${R2_BUCKET}" in s3.get("bucket", ""), "Must use ${R2_BUCKET} placeholder."

    def test_r2_config_tiering_policy(self):
        """Validates automated tiering policy rules."""
        data = json.loads(R2_CONFIG.read_text(encoding="utf-8"))
        assert "tiering_policy" in data, "Missing 'tiering_policy' key."
        policy = data["tiering_policy"]
        assert policy.get("enabled") is True
        assert policy.get("destination") == "cloudflare_r2"
        assert "criteria" in policy
        
        criteria = policy["criteria"]
        assert criteria.get("full_percent") == 95
        assert criteria.get("quiet_for") == "24h"
        assert "schedule" in policy
        assert policy.get("auto_vacuum") is True

    def test_r2_config_s3_identities(self):
        """Validates S3 gateway identity definitions."""
        data = json.loads(R2_CONFIG.read_text(encoding="utf-8"))
        assert "s3_identities" in data, "Missing 's3_identities' key."
        identities = data["s3_identities"]
        assert isinstance(identities, list)
        assert len(identities) >= 1
        
        admin_id = identities[0]
        assert "credentials" in admin_id
        assert "actions" in admin_id
        assert set(["Read", "Write", "List", "Admin"]).issubset(set(admin_id["actions"]))
        assert "resources" in admin_id
        assert any("buckets/${R2_BUCKET}" in r for r in admin_id["resources"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
