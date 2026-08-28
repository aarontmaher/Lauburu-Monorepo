"""
tests/unit/test_mesh_scanner.py
Unit tests for MeshNodeScanner in canonical_sync_engine.verification.mesh_scanner.
"""
from __future__ import annotations

import socket
import subprocess
from unittest.mock import MagicMock, patch
import pytest

from canonical_sync_engine.models.health import NodeProbeMethod, NodeStorageHealth
from canonical_sync_engine.verification.mesh_scanner import MeshNodeScanner

# Sample POSIX and Android stdout fixtures
MOCK_MAC_DF_STDOUT = """Filesystem     1024-blocks      Used Available Capacity iused ifree %iused  Mounted on
/dev/disk3s1     488245288 350245288 110000000    77% 1000000 20000000    5%   /System/Volumes/Data
"""

MOCK_LINUX_DF_STDOUT = """Filesystem     1K-blocks      Used Available Use% Mounted on
/dev/nvme0n1p2 490000000 220000000 270000000  45% /
"""

MOCK_ADB_DF_STDOUT = """Filesystem       1K-blocks   Used Available Use% Mounted on
/dev/fuse        113246208 40894464  72351744  37% /storage/emulated
"""

MOCK_WRAPPED_DF_STDOUT = """Filesystem
  1024-blocks      Used Available Capacity iused ifree %iused  Mounted on
/dev/very_long_storage_volume_identifier_name
    488245288 350245288 110000000    77% 1000000 20000000    5%   /
"""


def test_probe_local_node_healthy():
    """Test local host probe with healthy disk space."""
    with patch("shutil.disk_usage") as mock_du:
        mock_du.return_value = MagicMock(
            total=500 * (1024 ** 3), free=100 * (1024 ** 3), used=400 * (1024 ** 3)
        )
        scanner = MeshNodeScanner(min_headroom_gb=10.0)
        res = scanner.scan_node_by_spec(scanner.topology[0])
        assert res.is_reachable is True
        assert res.storage_healthy is True
        assert res.free_disk_gb == 100.0
        assert res.total_disk_gb == 500.0
        assert res.probe_method == NodeProbeMethod.LOCAL


def test_probe_local_node_low_headroom():
    """Test local host probe when free disk space is below minimum threshold."""
    with patch("shutil.disk_usage") as mock_du:
        mock_du.return_value = MagicMock(
            total=500 * (1024 ** 3), free=4.5 * (1024 ** 3), used=495.5 * (1024 ** 3)
        )
        scanner = MeshNodeScanner(min_headroom_gb=10.0)
        res = scanner.scan_node_by_spec(scanner.topology[0])
        assert res.is_reachable is True
        assert res.storage_healthy is False  # Below 10 GB
        assert res.free_disk_gb == 4.5


def test_probe_ssh_node_success():
    """Test SSH probe on remote node returning valid df output."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=MOCK_LINUX_DF_STDOUT, stderr=""
        )
        scanner = MeshNodeScanner()
        ssh_spec = scanner.topology[2]  # Linux_Head_Node
        res = scanner.scan_node_by_spec(ssh_spec)
        assert res.is_reachable is True
        assert res.storage_healthy is True
        assert res.total_disk_gb == 467.3  # 490000000 KB / 1048576 = 467.30 GB
        assert res.free_disk_gb == 257.49  # 270000000 KB / 1048576 = 257.49 GB


def test_probe_ssh_node_timeout():
    """Test SSH probe handling timeout and returning offline state."""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ssh", timeout=2.0)):
        scanner = MeshNodeScanner(timeout_sec=1.0)
        ssh_spec = scanner.topology[1]  # MacBook_Pro
        res = scanner.scan_node_by_spec(ssh_spec)
        assert res.is_reachable is False
        assert res.storage_healthy is False
        assert "timed out" in (res.error_message or "")


def test_probe_adb_node_success():
    """Test ADB probe on Android device returning valid df output."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=MOCK_ADB_DF_STDOUT, stderr=""
        )
        scanner = MeshNodeScanner()
        adb_spec = scanner.topology[6]  # Samsung_S20
        res = scanner.scan_node_by_spec(adb_spec)
        assert res.is_reachable is True
        assert res.storage_healthy is True
        assert res.free_disk_gb == 69.0  # 72351744 KB / 1048576 = 69.0 GB


def test_probe_socket_gateway_success():
    """Test TCP socket probe on Gateway router."""
    with patch("socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value = mock_sock
        scanner = MeshNodeScanner()
        gw_spec = scanner.topology[7]  # GL.iNet Router
        res = scanner.scan_node_by_spec(gw_spec)
        assert res.is_reachable is True
        assert res.storage_healthy is True
        assert res.probe_method == NodeProbeMethod.SOCKET


def test_parse_df_output_formats():
    """Validates df -k output parser across platforms and column layouts."""
    # macOS
    tot_mac, free_mac = MeshNodeScanner._parse_df_output(MOCK_MAC_DF_STDOUT)
    assert tot_mac == 465.63  # 488245288 KB
    assert free_mac == 104.9   # 110000000 KB

    # Linux
    tot_lin, free_lin = MeshNodeScanner._parse_df_output(MOCK_LINUX_DF_STDOUT)
    assert tot_lin == 467.3
    assert free_lin == 257.49

    # Android ADB
    tot_adb, free_adb = MeshNodeScanner._parse_df_output(MOCK_ADB_DF_STDOUT)
    assert tot_adb == 108.0
    assert free_adb == 69.0

    # Wrapped identifier lines
    tot_wrp, free_wrp = MeshNodeScanner._parse_df_output(MOCK_WRAPPED_DF_STDOUT)
    assert tot_wrp == 465.63
    assert free_wrp == 104.9

    # Corrupt / empty output
    tot_bad, free_bad = MeshNodeScanner._parse_df_output("")
    assert tot_bad == 0.0 and free_bad == 0.0


def test_scan_all_nodes_parallel_and_summary():
    """Test complete mesh scan and summary generation."""
    with patch("shutil.disk_usage") as mock_du, \
         patch("subprocess.run") as mock_run, \
         patch("socket.socket") as mock_sock:

        mock_du.return_value = MagicMock(
            total=500 * (1024 ** 3), free=100 * (1024 ** 3), used=400 * (1024 ** 3)
        )
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=MOCK_LINUX_DF_STDOUT, stderr=""
        )

        scanner = MeshNodeScanner()
        node_reports = scanner.scan_all_nodes(parallel=True, max_workers=8)
        assert len(node_reports) == len(scanner.topology)
        assert "L1" in node_reports

        summary = scanner.get_mesh_summary(parallel=True)
        assert summary.total_nodes == len(scanner.topology)
        assert summary.online_nodes >= 1
        assert summary.total_mesh_free_gb > 0.0


def test_probe_adb_not_found():
    """Test handling when adb binary is missing on host."""
    with patch("subprocess.run", side_effect=FileNotFoundError("No adb")):
        scanner = MeshNodeScanner()
        adb_spec = scanner.topology[6]  # Samsung_S20
        res = scanner.scan_node_by_spec(adb_spec)
        assert res.is_reachable is False
        assert "adb executable not found" in (res.error_message or "")


def test_probe_socket_refused():
    """Test handling when gateway socket connect fails."""
    with patch("socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = ConnectionRefusedError("Connection refused")
        mock_sock_cls.return_value = mock_sock
        scanner = MeshNodeScanner()
        gw_spec = scanner.topology[7]
        res = scanner.scan_node_by_spec(gw_spec)
        assert res.is_reachable is False
        assert "Socket connection refused" in (res.error_message or "")


def test_probe_ssh_nonzero_exit():
    """Test handling when remote SSH command returns non-zero exit code."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="Permission denied"
        )
        scanner = MeshNodeScanner()
        ssh_spec = scanner.topology[1]
        res = scanner.scan_node_by_spec(ssh_spec)
        assert res.is_reachable is False
        assert "SSH exit 1" in (res.error_message or "")

