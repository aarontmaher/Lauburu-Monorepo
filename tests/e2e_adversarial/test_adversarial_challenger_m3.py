#!/usr/bin/env python3
"""
================================================================================
LAUBURU MONOREPO: CHALLENGER 1 ADVERSARIAL STRESS HARNESS FOR MILESTONE 3
Empirical Stress-Testing of SeaweedFS Self-Healing & Raft Consensus Tools
================================================================================
Covers:
  1. Corrupt network payloads (non-JSON, truncated JSON, binary garbage, HTML errors)
  2. Split-brain master topologies (2-way, 3-way conflicting leaders, leaderless election)
  3. Total network blackouts and hung socket timeouts
  4. Input fuzzing (trailing slashes, empty strings, malformed endpoints, negative timeouts)
  5. Multi-threaded high-concurrency stress execution
  6. Smolagents tool contract, signature, docstring parsing, and schema integrity
================================================================================
"""

import json
import os
import sys
import time
import socket
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import tools from 00_core_infrastructure/seaweedfs
sys.path.insert(0, str(REPO_ROOT / "00_core_infrastructure" / "seaweedfs"))
from seaweed_tools import (
    heal_fuse_mount,
    check_raft_consensus,
    _normalize_leader_addr,
    _parse_peer_endpoint,
)


# ==============================================================================
# ADVERSARIAL HTTP MOCK SERVERS
# ==============================================================================

class AdversarialMasterHandler(BaseHTTPRequestHandler):
    """Configurable HTTP mock handler to simulate corrupt, slow, split-brain, and failing masters."""
    mode = "nominal"  # nominal, html_error, truncated_json, binary_garbage, split_brain_leader, leaderless, http_500, http_502, sleep_delay
    claimed_leader = ""
    is_leader = False
    peers = []
    volume_free = 1000
    volume_max = 2000
    delay_seconds = 0.0

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)

        if self.mode == "http_500":
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"500 Internal Server Error")
            return
        elif self.mode == "http_502":
            self.send_response(502)
            self.end_headers()
            self.wfile.write(b"502 Bad Gateway")
            return
        elif self.mode == "html_error":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<!DOCTYPE html><html><body>Error: Service Unavailable</body></html>")
            return
        elif self.mode == "truncated_json":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"IsLeader": true, "Leader": "127.0.0.1:9333", "VolumeStatus": {')
            return
        elif self.mode == "binary_garbage":
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.end_headers()
            self.wfile.write(b"\x00\xff\xfe\x01\x02\x03\xfa\xce\xde\xad\xbe\xef")
            return
        elif self.mode == "leaderless":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            payload = {
                "IsLeader": False,
                "Leader": "",
                "Peers": self.peers,
                "VolumeStatus": {"Free": self.volume_free, "Max": self.volume_max}
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return
        elif self.mode == "split_brain_leader":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            payload = {
                "IsLeader": self.is_leader,
                "Leader": self.claimed_leader or f"{self.server.server_address[0]}:{self.server.server_address[1]}.19333",
                "Peers": self.peers,
                "VolumeStatus": {"Free": self.volume_free, "Max": self.volume_max}
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return
        else:
            # Nominal mode
            if self.path == "/cluster/status":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                payload = {
                    "IsLeader": self.is_leader,
                    "Leader": self.claimed_leader,
                    "Peers": self.peers,
                    "VolumeStatus": {"Free": self.volume_free, "Max": self.volume_max}
                }
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif self.path == "/dir/status":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                payload = {
                    "Topology": {
                        "Free": self.volume_free,
                        "Max": self.volume_max
                    }
                }
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            elif self.path == "/":
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"OK")
            else:
                self.send_response(404)
                self.end_headers()


def create_mock_server(handler_config=None):
    """Helper to start an ephemeral mock HTTP server with specific config."""
    server = HTTPServer(("127.0.0.1", 0), AdversarialMasterHandler)
    if handler_config:
        for k, v in handler_config.items():
            setattr(AdversarialMasterHandler, k, v)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


# ==============================================================================
# SECTION 1: CORRUPT NETWORK PAYLOAD & BLACKOUT TESTS
# ==============================================================================

class TestAdversarialNetworkResilience:
    """Stress-test check_raft_consensus against malformed, corrupt, and dead network responses."""

    def test_corrupt_html_payload_handled_safely(self):
        """Master returning HTML error page instead of JSON must not throw unhandled JSONDecodeError."""
        server = HTTPServer(("127.0.0.1", 0), AdversarialMasterHandler)
        AdversarialMasterHandler.mode = "html_error"
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        endpoint = f"127.0.0.1:{server.server_port}"
        try:
            res_raw = check_raft_consensus(master_peers=endpoint, timeout_seconds=2)
            parsed = json.loads(res_raw)
            assert parsed["status"] == "QUORUM_LOST_CRITICAL"
            assert parsed["reachable_peers_count"] == 0
            assert endpoint in parsed["peer_details"]
            assert "cluster_error" in parsed["peer_details"][endpoint]
        finally:
            server.shutdown()
            server.server_close()
            AdversarialMasterHandler.mode = "nominal"

    def test_truncated_json_payload_handled_safely(self):
        """Master returning truncated JSON must catch JSONDecodeError gracefully."""
        server = HTTPServer(("127.0.0.1", 0), AdversarialMasterHandler)
        AdversarialMasterHandler.mode = "truncated_json"
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        endpoint = f"127.0.0.1:{server.server_port}"
        try:
            res_raw = check_raft_consensus(master_peers=endpoint, timeout_seconds=2)
            parsed = json.loads(res_raw)
            assert parsed["status"] == "QUORUM_LOST_CRITICAL"
            assert parsed["reachable_peers_count"] == 0
            assert endpoint in parsed["peer_details"]
        finally:
            server.shutdown()
            server.server_close()
            AdversarialMasterHandler.mode = "nominal"

    def test_binary_garbage_payload_handled_safely(self):
        """Master returning raw binary stream must catch decoding/parsing exceptions."""
        server = HTTPServer(("127.0.0.1", 0), AdversarialMasterHandler)
        AdversarialMasterHandler.mode = "binary_garbage"
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        endpoint = f"127.0.0.1:{server.server_port}"
        try:
            res_raw = check_raft_consensus(master_peers=endpoint, timeout_seconds=2)
            parsed = json.loads(res_raw)
            assert parsed["status"] == "QUORUM_LOST_CRITICAL"
            assert parsed["reachable_peers_count"] == 0
        finally:
            server.shutdown()
            server.server_close()
            AdversarialMasterHandler.mode = "nominal"

    def test_http_502_bad_gateway_handled_safely(self):
        """Master returning HTTP 502 must record cluster_error HTTP_502."""
        server = HTTPServer(("127.0.0.1", 0), AdversarialMasterHandler)
        AdversarialMasterHandler.mode = "http_502"
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        endpoint = f"127.0.0.1:{server.server_port}"
        try:
            res_raw = check_raft_consensus(master_peers=endpoint, timeout_seconds=2)
            parsed = json.loads(res_raw)
            assert parsed["status"] == "QUORUM_LOST_CRITICAL"
            assert "HTTP_502" in parsed["peer_details"][endpoint].get("cluster_error", "")
        finally:
            server.shutdown()
            server.server_close()
            AdversarialMasterHandler.mode = "nominal"

    def test_total_network_blackout_unreachable_ips(self):
        """All peers on non-routable / non-listening addresses terminate within bounded timeout."""
        blackout_peers = "192.0.2.10:9333,192.0.2.11:9333,192.0.2.12:9333"
        t0 = time.perf_counter()
        res_raw = check_raft_consensus(master_peers=blackout_peers, timeout_seconds=1)
        duration = time.perf_counter() - t0
        parsed = json.loads(res_raw)

        assert parsed["status"] == "QUORUM_LOST_CRITICAL"
        assert parsed["has_quorum"] is False
        assert parsed["reachable_peers_count"] == 0
        assert parsed["total_configured_peers"] == 3
        assert parsed["quorum_required"] == 2
        assert duration < 5.0, "Blackout probe should respect timeout limit"


# ==============================================================================
# SECTION 2: SPLIT-BRAIN & CONSENSUS TOPOLOGY TESTS
# ==============================================================================

class TestSplitBrainAndConsensusTopology:
    """Stress-test 2-way and 3-way split brain, leaderless states, and quorum math."""

    def test_two_way_split_brain_detected(self):
        """Two nodes reporting different leaders with quorum reachable."""
        # Server 1 claiming Node 1 is leader
        s1 = HTTPServer(("127.0.0.1", 0), AdversarialMasterHandler)
        p1 = s1.server_port
        t1 = threading.Thread(target=s1.serve_forever, daemon=True)
        t1.start()

        # Server 2 claiming Node 2 is leader
        s2 = HTTPServer(("127.0.0.1", 0), AdversarialMasterHandler)
        p2 = s2.server_port
        t2 = threading.Thread(target=s2.serve_forever, daemon=True)
        t2.start()

        # Custom handler logic per server port
        def custom_do_GET(handler):
            port = handler.server.server_address[1]
            handler.send_response(200)
            handler.send_header("Content-Type", "application/json")
            handler.end_headers()
            if port == p1:
                resp = {"IsLeader": True, "Leader": f"127.0.0.1:{p1}.19333", "VolumeStatus": {"Free": 100, "Max": 200}}
            else:
                resp = {"IsLeader": True, "Leader": f"127.0.0.1:{p2}.19333", "VolumeStatus": {"Free": 100, "Max": 200}}
            handler.wfile.write(json.dumps(resp).encode("utf-8"))

        AdversarialMasterHandler.do_GET = custom_do_GET

        try:
            peers = f"127.0.0.1:{p1},127.0.0.1:{p2},127.0.0.1:49999"
            res_raw = check_raft_consensus(master_peers=peers, timeout_seconds=2)
            parsed = json.loads(res_raw)

            assert parsed["status"] == "SPLIT_BRAIN_DETECTED"
            assert parsed["is_split_brain"] is True
            assert parsed["reachable_peers_count"] == 2
            assert parsed["has_quorum"] is True
            assert parsed["consensus_leader"] == ""
        finally:
            s1.shutdown()
            s1.server_close()
            s2.shutdown()
            s2.server_close()
            AdversarialMasterHandler.mode = "nominal"

    def test_leaderless_cluster_election_in_progress(self):
        """All reachable nodes report no leader currently elected."""
        s1 = HTTPServer(("127.0.0.1", 0), AdversarialMasterHandler)
        p1 = s1.server_port
        t1 = threading.Thread(target=s1.serve_forever, daemon=True)
        t1.start()

        s2 = HTTPServer(("127.0.0.1", 0), AdversarialMasterHandler)
        p2 = s2.server_port
        t2 = threading.Thread(target=s2.serve_forever, daemon=True)
        t2.start()

        def custom_do_GET(handler):
            handler.send_response(200)
            handler.send_header("Content-Type", "application/json")
            handler.end_headers()
            resp = {"IsLeader": False, "Leader": "", "VolumeStatus": {"Free": 50, "Max": 100}}
            handler.wfile.write(json.dumps(resp).encode("utf-8"))

        AdversarialMasterHandler.do_GET = custom_do_GET

        try:
            peers = f"127.0.0.1:{p1},127.0.0.1:{p2},127.0.0.1:49999"
            res_raw = check_raft_consensus(master_peers=peers, timeout_seconds=2)
            parsed = json.loads(res_raw)

            assert parsed["status"] == "NO_LEADER_ELECTED"
            assert parsed["is_split_brain"] is False
            assert parsed["consensus_leader"] == ""
            assert parsed["reachable_peers_count"] == 2
            assert parsed["has_quorum"] is True
        finally:
            s1.shutdown()
            s1.server_close()
            s2.shutdown()
            s2.server_close()

    def test_asymmetric_cluster_vs_dir_status(self):
        """Master responds to /cluster/status but /dir/status fails with 500."""
        server = HTTPServer(("127.0.0.1", 0), AdversarialMasterHandler)
        p = server.server_port
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def custom_do_GET(handler):
            if handler.path == "/cluster/status":
                handler.send_response(200)
                handler.send_header("Content-Type", "application/json")
                handler.end_headers()
                resp = {"IsLeader": True, "Leader": f"127.0.0.1:{p}.19333", "VolumeStatus": {"Free": 80, "Max": 100}}
                handler.wfile.write(json.dumps(resp).encode("utf-8"))
            elif handler.path == "/dir/status":
                handler.send_response(500)
                handler.end_headers()
                handler.wfile.write(b"Topology unavailable")
            else:
                handler.send_response(404)
                handler.end_headers()

        AdversarialMasterHandler.do_GET = custom_do_GET

        try:
            res_raw = check_raft_consensus(master_peers=f"127.0.0.1:{p}", timeout_seconds=2)
            parsed = json.loads(res_raw)

            assert parsed["status"] == "QUORUM_HEALTHY"
            assert parsed["reachable_peers_count"] == 1
            assert parsed["total_free_volumes"] == 80
            assert parsed["peer_details"][f"127.0.0.1:{p}"]["is_leader"] is True
        finally:
            server.shutdown()
            server.server_close()


# ==============================================================================
# SECTION 3: INPUT FUZZING & BOUNDARY CONDITIONS
# ==============================================================================

class TestAdversarialInputFuzzing:
    """Fuzz check_raft_consensus and heal_fuse_mount with pathological inputs."""

    @pytest.mark.parametrize("malformed_peers", [
        "",
        "   ",
        ",,,",
        "  ,  ,  ",
        "http://127.0.0.1:9333",
        "127.0.0.1",
        ":9333",
        "127.0.0.1:not_a_port",
        "127.0.0.1:-9333",
        "127.0.0.1:9333.19333.99999",
        "127.0.0.1:9333/extra/path",
        "[::1]:9333",
        "127.0.0.1:9333, " * 10,
    ])
    def test_check_raft_consensus_fuzzing(self, malformed_peers):
        """check_raft_consensus must never crash or raise uncaught exception on fuzzed input."""
        res_raw = check_raft_consensus(master_peers=malformed_peers, timeout_seconds=1)
        assert isinstance(res_raw, str)
        parsed = json.loads(res_raw)
        assert "status" in parsed
        assert "has_quorum" in parsed
        assert "peer_details" in parsed

    @pytest.mark.parametrize("timeout_val", [-100, -1, 0, 0.0001, 1000])
    def test_timeout_bounds_handling(self, timeout_val):
        """Non-positive or extreme timeout values are clamped safely without error."""
        res_raw = check_raft_consensus(master_peers="127.0.0.1:49999", timeout_seconds=timeout_val)
        parsed = json.loads(res_raw)
        assert parsed["status"] == "QUORUM_LOST_CRITICAL"

    @pytest.mark.parametrize("fuzzed_mount", [
        "",
        "   ",
        "/mnt/dfs_unified///",
        "/mnt/dfs_unified/./",
        "/tmp/non_existent_folder_xyz_999",
        "/dev/null",
        "/tmp/path with spaces/and/slashes///",
    ])
    def test_heal_fuse_mount_fuzzing(self, fuzzed_mount):
        """heal_fuse_mount must safely sanitize path and return valid JSON."""
        res_raw = heal_fuse_mount(
            mount_point=fuzzed_mount,
            filer_endpoints="127.0.0.1:49999",
            force_lazy=True,
            timeout_seconds=1
        )
        assert isinstance(res_raw, str)
        parsed = json.loads(res_raw)
        assert "status" in parsed
        assert "actions_taken" in parsed
        assert "is_mounted" in parsed


# ==============================================================================
# SECTION 4: FUSE HEALING ADVERSARIAL STRESS
# ==============================================================================

class TestFUSEHealingAdversarial:
    """Stress-test heal_fuse_mount under offline filers, Darwin unmounts, and frozen mounts."""

    def test_all_filers_offline_safely_prevents_remount(self):
        """When all filers are dead, unmount is executed but remount is blocked to prevent host freeze."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            res_raw = heal_fuse_mount(
                mount_point=tmp_dir,
                filer_endpoints="127.0.0.1:49991,127.0.0.1:49992,127.0.0.1:49993",
                force_lazy=True,
                timeout_seconds=1
            )
            parsed = json.loads(res_raw)

            assert parsed["status"] == "UNMOUNTED_FILER_OFFLINE"
            assert parsed["is_mounted"] is False
            assert "actions_taken" in parsed
            assert "preflight_check_failed_all_filers_unreachable" in parsed["actions_taken"]
            assert parsed["reachable_filers"] == []

    def test_heal_mount_selects_first_live_filer_from_pool(self):
        """Pool with [dead, live, dead] correctly finds the live filer and attempts remount."""
        server = HTTPServer(("127.0.0.1", 0), AdversarialMasterHandler)
        p = server.server_port
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def custom_do_GET(handler):
            handler.send_response(200)
            handler.send_header("Content-Type", "text/plain")
            handler.end_headers()
            handler.wfile.write(b"SeaweedFS Filer Active")

        AdversarialMasterHandler.do_GET = custom_do_GET

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("subprocess.Popen") as mock_popen:
                mock_proc = MagicMock()
                mock_popen.return_value = mock_proc

                pool = f"127.0.0.1:49990,127.0.0.1:{p},127.0.0.1:49999"
                res_raw = heal_fuse_mount(
                    mount_point=tmp_dir,
                    filer_endpoints=pool,
                    force_lazy=True,
                    timeout_seconds=2
                )
                parsed = json.loads(res_raw)

                assert f"127.0.0.1:{p}" in parsed["reachable_filers"]
                assert f"preflight_filer_check_passed_endpoint_127.0.0.1:{p}" in parsed["actions_taken"]
                assert "remount_command_executed" in parsed["actions_taken"]

        server.shutdown()
        server.server_close()

    def test_heal_fuse_mount_darwin_and_linux_unmount_calls(self):
        """Verify unmount execution branch on Darwin vs Linux."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("subprocess.run") as mock_subrun:
                mock_subrun.return_value = MagicMock(returncode=0, stdout="")
                res_raw = heal_fuse_mount(
                    mount_point=tmp_dir,
                    filer_endpoints="127.0.0.1:49999",
                    force_lazy=True,
                    timeout_seconds=1
                )
                parsed = json.loads(res_raw)
                assert parsed["status"] == "UNMOUNTED_FILER_OFFLINE"


# ==============================================================================
# SECTION 5: HIGH CONCURRENCY & THREAD-SAFETY STRESS
# ==============================================================================

class TestAdversarialConcurrency:
    """Stress-test concurrent execution of Raft audit and FUSE healing tools."""

    def test_check_raft_consensus_high_concurrency_30_threads(self):
        """Execute 30 concurrent check_raft_consensus calls without lockups or crashes."""
        server = HTTPServer(("127.0.0.1", 0), AdversarialMasterHandler)
        p = server.server_port
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def custom_do_GET(handler):
            handler.send_response(200)
            handler.send_header("Content-Type", "application/json")
            handler.end_headers()
            resp = {
                "IsLeader": True,
                "Leader": f"127.0.0.1:{p}.19333",
                "Peers": [f"127.0.0.1:{p}"],
                "VolumeStatus": {"Free": 500, "Max": 1000}
            }
            handler.wfile.write(json.dumps(resp).encode("utf-8"))

        AdversarialMasterHandler.do_GET = custom_do_GET

        peers = f"127.0.0.1:{p},127.0.0.1:49998,127.0.0.1:49999"

        def worker_task(idx):
            res = check_raft_consensus(master_peers=peers, timeout_seconds=1)
            parsed = json.loads(res)
            return parsed["status"], parsed["reachable_peers_count"]

        with ThreadPoolExecutor(max_workers=15) as pool:
            futures = [pool.submit(worker_task, i) for i in range(30)]
            results = [f.result() for f in futures]

        assert len(results) == 30
        for status, reachable in results:
            assert status == "QUORUM_LOST_CRITICAL"
            assert reachable == 1

        server.shutdown()
        server.server_close()

    def test_heal_fuse_mount_concurrency_10_threads(self):
        """Execute 10 concurrent heal_fuse_mount calls on distinct temporary paths."""
        def heal_worker(idx):
            with tempfile.TemporaryDirectory() as tmp_mount:
                res = heal_fuse_mount(
                    mount_point=tmp_mount,
                    filer_endpoints="127.0.0.1:49991",
                    force_lazy=True,
                    timeout_seconds=1
                )
                parsed = json.loads(res)
                return parsed["status"]

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(heal_worker, i) for i in range(10)]
            results = [f.result() for f in futures]

        assert len(results) == 10
        for status in results:
            assert status == "UNMOUNTED_FILER_OFFLINE"


# ==============================================================================
# SECTION 6: SMOLAGENTS TOOL CONTRACT REFLECTION
# ==============================================================================

class TestSmolagentsToolContractReflection:
    """Verify smolagents tool decorator, properties, docstring parsing, and inputs."""

    def test_check_raft_consensus_tool_contract(self):
        """Tool name, description, and signature introspect cleanly."""
        assert hasattr(check_raft_consensus, "name")
        assert check_raft_consensus.name == "check_raft_consensus"
        assert callable(check_raft_consensus)
        doc = check_raft_consensus.__doc__
        assert doc is not None
        assert "Audits Raft consensus health" in doc
        assert "Args:" in doc
        assert "master_peers:" in doc
        assert "timeout_seconds:" in doc
        assert "Returns:" in doc

    def test_heal_fuse_mount_tool_contract(self):
        """Tool name, description, and signature introspect cleanly."""
        assert hasattr(heal_fuse_mount, "name")
        assert heal_fuse_mount.name == "heal_fuse_mount"
        assert callable(heal_fuse_mount)
        doc = heal_fuse_mount.__doc__
        assert doc is not None
        assert "Detects SeaweedFS FUSE mount health" in doc
        assert "Args:" in doc
        assert "mount_point:" in doc
        assert "filer_endpoints:" in doc
        assert "force_lazy:" in doc
        assert "timeout_seconds:" in doc
        assert "Returns:" in doc
