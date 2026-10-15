"""
Unit test for Autonomous Network Storage Governor
Path: tests/test_autonomous_storage_governor.py
"""
import pytest
from pathlib import Path
import sys

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling/storage"))

from autonomous_storage_governor import (
    probe_tcp,
    verify_tri_vault_health,
    verify_dfs_mount_and_sockets,
    run_governor_cycle,
)


def test_probe_tcp_localhost():
    # Localhost should handle closed/open probes gracefully without throwing exceptions
    res = probe_tcp("127.0.0.1", 59998, timeout=0.1)
    assert res is False


def test_verify_tri_vault_health():
    tri_vault = verify_tri_vault_health()
    assert isinstance(tri_vault, dict)
    assert "healthy" in tri_vault
    assert "disk_free_gb" in tri_vault
    assert tri_vault["disk_free_gb"] > 0


def test_verify_dfs_mount_and_sockets():
    dfs = verify_dfs_mount_and_sockets()
    assert isinstance(dfs, dict)
    assert "healthy" in dfs
    assert "sockets" in dfs
    assert "mount_directory_exists" in dfs
    assert dfs["mount_directory_exists"] is True


def test_run_governor_cycle():
    report = run_governor_cycle()
    assert isinstance(report, dict)
    assert "timestamp_utc" in report
    assert "overall_status" in report
    assert "local_ai_sentinel" in report
    assert report["local_ai_sentinel"]["model"] == "qwen2.5-coder-7b-instruct"
    assert "endpoints" in report
