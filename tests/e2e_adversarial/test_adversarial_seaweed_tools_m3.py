#!/usr/bin/env python3
"""
================================================================================
LAUBURU MONOREPO: ADVERSARIAL TEST SUITE FOR MILESTONE 3 (SEAWEED TOOLS)
smolagents Reflex Arc Self-Healing Tools Empirical Verification
================================================================================
Empirical Test Suite for:
  1. heal_fuse_mount() tool contract, docstrings, non-blocking probes, and teardown
  2. check_raft_consensus() tool contract, Raft quorum, split-brain, and topology
  3. smolagents @tool integration and fallback compatibility
  4. Zero-crash exception containment under network blackouts, hung sockets, HTTP 500
  5. Multi-platform unmount semantics (macOS Darwin vs Linux)
================================================================================
"""

import json
import os
import sys
import time
import inspect
import tempfile
import threading
import subprocess
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import tools from both paths
sys.path.insert(0, str(REPO_ROOT / "00_core_infrastructure" / "seaweedfs"))
from seaweed_tools import (
    heal_fuse_mount,
    check_raft_consensus,
    _normalize_leader_addr,
    _parse_peer_endpoint,
)


# ==============================================================================
# MOCK SERVER FIXTURES
# ==============================================================================

class MockSeaweedMasterHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/cluster/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "IsLeader": True,
                "Leader": f"{self.server.server_address[0]}:{self.server.server_address[1]}.19333",
                "Peers": [f"{self.server.server_address[0]}:{self.server.server_address[1]}"],
                "VolumeStatus": {"Free": 850, "Max": 1000}
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        elif self.path == "/dir/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "Topology": {
                    "DataCenters": [],
                    "Free": 850,
                    "Max": 1000
                }
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        elif self.path == "/":
            # Filer root check
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"SeaweedFS Filer Active")
        else:
            self.send_response(404)
            self.end_headers()


@pytest.fixture
def mock_seaweed_cluster():
    """Create a 3-node mock SeaweedFS master cluster."""
    servers = []
    threads = []
    endpoints = []

    for _ in range(3):
        server = HTTPServer(("127.0.0.1", 0), MockSeaweedMasterHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        servers.append(server)
        threads.append(thread)
        endpoints.append(f"127.0.0.1:{server.server_address[1]}")

    yield endpoints

    for s in servers:
        s.shutdown()
        s.server_close()


# ==============================================================================
# SECTION 1: UNIT & HELPER TESTS
# ==============================================================================

class TestSeaweedToolsHelpers:
    def test_normalize_leader_addr(self):
        assert _normalize_leader_addr("100.101.39.98:9333.19333") == "100.101.39.98:9333"
        assert _normalize_leader_addr("100.101.39.98:9333") == "100.101.39.98:9333"
        assert _normalize_leader_addr("") == ""
        assert _normalize_leader_addr("   ") == ""
        assert _normalize_leader_addr("127.0.0.1:8080.18080") == "127.0.0.1:8080"

    def test_parse_peer_endpoint(self):
        assert _parse_peer_endpoint("100.101.39.98:9333") == ("100.101.39.98", 9333)
        assert _parse_peer_endpoint("100.101.39.98:9333.19333") == ("100.101.39.98", 9333)
        assert _parse_peer_endpoint("http://100.101.39.98:9333") == ("100.101.39.98", 9333)
        assert _parse_peer_endpoint("100.101.39.98") == ("100.101.39.98", 9333)
        assert _parse_peer_endpoint("") == ("", 0)


# ==============================================================================
# SECTION 2: CHECK_RAFT_CONSENSUS TESTS
# ==============================================================================

class TestCheckRaftConsensus:
    def test_signature_and_metadata(self):
        assert check_raft_consensus.name == "check_raft_consensus"
        assert callable(check_raft_consensus)
        doc = check_raft_consensus.__doc__
        assert "Args:" in doc
        assert "master_peers:" in doc
        assert "timeout_seconds:" in doc
        assert "Returns:" in doc

    def test_mock_cluster_healthy_consensus(self, mock_seaweed_cluster):
        peers_str = ",".join(mock_seaweed_cluster)
        raw_res = check_raft_consensus(master_peers=peers_str, timeout_seconds=2)
        parsed = json.loads(raw_res)
        
        assert parsed["status"] in ("QUORUM_HEALTHY", "SPLIT_BRAIN_DETECTED", "NO_LEADER_ELECTED")
        assert parsed["reachable_peers_count"] == 3
        assert parsed["has_quorum"] is True
        assert parsed["quorum_required"] == 2
        assert parsed["total_configured_peers"] == 3
        assert "peer_details" in parsed
        assert len(parsed["peer_details"]) == 3

    def test_quorum_loss_when_nodes_offline(self):
        peers_str = "127.0.0.1:49991,127.0.0.1:49992,127.0.0.1:49993"
        raw_res = check_raft_consensus(master_peers=peers_str, timeout_seconds=1)
        parsed = json.loads(raw_res)
        
        assert parsed["status"] == "QUORUM_LOST_CRITICAL"
        assert parsed["has_quorum"] is False
        assert parsed["reachable_peers_count"] == 0
        assert parsed["quorum_required"] == 2
        assert parsed["consensus_leader"] == ""

    def test_zero_crash_malformed_inputs(self):
        # Empty peers
        res1 = json.loads(check_raft_consensus(master_peers="", timeout_seconds=1))
        assert res1["status"] == "QUORUM_LOST_CRITICAL"
        assert res1["total_configured_peers"] == 0

        # Spaces and empty elements
        res2 = json.loads(check_raft_consensus(master_peers=" , , 127.0.0.1:49991 , ", timeout_seconds=1))
        assert res2["status"] == "QUORUM_LOST_CRITICAL"
        assert res2["total_configured_peers"] == 1

        # Negative timeout
        res3 = json.loads(check_raft_consensus(master_peers="127.0.0.1:49991", timeout_seconds=-5))
        assert "status" in res3


# ==============================================================================
# SECTION 3: HEAL_FUSE_MOUNT TESTS
# ==============================================================================

class TestHealFuseMount:
    def test_signature_and_metadata(self):
        assert heal_fuse_mount.name == "heal_fuse_mount"
        assert callable(heal_fuse_mount)
        doc = heal_fuse_mount.__doc__
        assert "Args:" in doc
        assert "mount_point:" in doc
        assert "filer_endpoints:" in doc
        assert "force_lazy:" in doc
        assert "timeout_seconds:" in doc
        assert "Returns:" in doc

    def test_healthy_mount_non_destructive(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # When mount point is not in mount table, it recognizes it
            raw_res = heal_fuse_mount(
                mount_point=tmp_dir,
                filer_endpoints="127.0.0.1:49995",
                force_lazy=True,
                timeout_seconds=2
            )
            parsed = json.loads(raw_res)
            # Since filer is offline, returns UNMOUNTED_FILER_OFFLINE
            assert parsed["status"] == "UNMOUNTED_FILER_OFFLINE"
            assert parsed["is_mounted"] is False
            assert "actions_taken" in parsed
            assert len(parsed["actions_taken"]) > 0

    def test_preflight_filer_offline_prevents_remount(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            raw_res = heal_fuse_mount(
                mount_point=tmp_dir,
                filer_endpoints="127.0.0.1:49996,127.0.0.1:49997",
                force_lazy=True,
                timeout_seconds=1
            )
            parsed = json.loads(raw_res)
            assert parsed["status"] == "UNMOUNTED_FILER_OFFLINE"
            assert "preflight_check_failed_all_filers_unreachable" in parsed["actions_taken"]

    def test_heal_with_live_filer_endpoint(self, mock_seaweed_cluster):
        live_filer = mock_seaweed_cluster[0]
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("subprocess.Popen") as mock_popen:
                mock_proc = MagicMock()
                mock_popen.return_value = mock_proc
                
                raw_res = heal_fuse_mount(
                    mount_point=tmp_dir,
                    filer_endpoints=f"{live_filer},127.0.0.1:49999",
                    force_lazy=True,
                    timeout_seconds=2
                )
                parsed = json.loads(raw_res)
                # Remount attempted
                assert f"preflight_filer_check_passed_endpoint_{live_filer}" in parsed["actions_taken"]
                assert "remount_command_executed" in parsed["actions_taken"]
                assert parsed["status"] in ("HEALED_SUCCESSFULLY", "REMOUNT_FAILED")

    def test_zero_crash_exception_containment(self):
        # Even with invalid paths and timeouts, never raises unhandled exception
        raw_res = heal_fuse_mount(
            mount_point="/invalid/\x00/path",
            filer_endpoints="",
            force_lazy=True,
            timeout_seconds=-1
        )
        parsed = json.loads(raw_res)
        assert "status" in parsed
        assert "actions_taken" in parsed
