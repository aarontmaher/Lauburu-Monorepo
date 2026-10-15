#!/usr/bin/env python3
"""
================================================================================
LAUBURU MONOREPO: CHALLENGER 2 EMPIRICAL TEST SUITE (MILESTONE 3)
smolagents Dynamic Ingestion, Tool Schema Compilation & Reflex Arc Recovery
================================================================================
Empirically verifies:
  1. smolagents Tool / ToolCallingAgent ingestion & schema compilation
  2. JSON return values parse cleanly with json.loads() across 100% of branches
  3. Dynamic agent loop reflex arc execution (diagnosis -> recovery -> observation)
  4. Adversarial resilience (split-brain, hung sockets, 502/500 errors, corrupted JSON)
  5. Execution timings, timeout enforcement, and 50-run stress benchmark
================================================================================
"""

import json
import os
import sys
import time
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

# Import tools from 00_core_infrastructure/seaweedfs
sys.path.insert(0, str(REPO_ROOT / "00_core_infrastructure" / "seaweedfs"))
from seaweed_tools import (
    heal_fuse_mount,
    check_raft_consensus,
    _normalize_leader_addr,
    _parse_peer_endpoint,
)

# Detect if smolagents is available in environment
try:
    import smolagents
    from smolagents import Tool, ToolCallingAgent
    HAS_SMOLAGENTS = True
except ImportError:
    HAS_SMOLAGENTS = False


# ==============================================================================
# ADVERSARIAL HTTP MOCK SERVERS
# ==============================================================================

class MockSeaweedMasterRaftHandler(BaseHTTPRequestHandler):
    """Configurable mock SeaweedFS master server supporting split-brain, errors, and custom topologies."""
    leader_addr = "127.0.0.1:9333"
    is_leader = True
    corrupt_response = False
    http_error_code = 0
    response_delay_sec = 0.0

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.response_delay_sec > 0:
            time.sleep(self.response_delay_sec)

        if self.http_error_code > 0:
            self.send_response(self.http_error_code)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Internal Server Error / Bad Gateway")
            return

        if self.corrupt_response:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"<html><body>502 Bad Gateway: Corrupted Non-JSON Payload</body></html>")
            return

        port = self.server.server_address[1]
        host = self.server.server_address[0]
        
        if self.path == "/cluster/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "IsLeader": getattr(self, "is_leader", True),
                "Leader": getattr(self, "leader_addr", f"{host}:{port}.19333"),
                "Peers": [f"{host}:{port}"],
                "VolumeStatus": {"Free": 1200, "Max": 2000}
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        elif self.path == "/dir/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "Topology": {
                    "DataCenters": [],
                    "Free": 1200,
                    "Max": 2000
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
def mock_3node_raft_cluster():
    """Create a 3-node mock SeaweedFS master cluster in healthy consensus."""
    servers = []
    threads = []
    endpoints = []

    # Choose leader endpoint as first node
    leader_server = HTTPServer(("127.0.0.1", 0), MockSeaweedMasterRaftHandler)
    leader_port = leader_server.server_address[1]
    leader_addr = f"127.0.0.1:{leader_port}.19333"

    for i in range(3):
        server = leader_server if i == 0 else HTTPServer(("127.0.0.1", 0), MockSeaweedMasterRaftHandler)
        server.RequestHandlerClass.leader_addr = leader_addr
        server.RequestHandlerClass.is_leader = (i == 0)
        server.RequestHandlerClass.corrupt_response = False
        server.RequestHandlerClass.http_error_code = 0
        server.RequestHandlerClass.response_delay_sec = 0.0

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        servers.append(server)
        threads.append(thread)
        endpoints.append(f"127.0.0.1:{server.server_address[1]}")

    yield endpoints, leader_addr

    for s in servers:
        try:
            s.shutdown()
            s.server_close()
        except Exception:
            pass


# ==============================================================================
# SECTION 1: SMOLAGENTS SCHEMA & TOOL COMPILATION
# ==============================================================================

class TestSmolagentsToolSchemaCompilation:
    def test_tool_attributes_and_typing(self):
        """Verify tool naming, outputs, and inputs comply with smolagents contract."""
        assert heal_fuse_mount.name == "heal_fuse_mount"
        assert check_raft_consensus.name == "check_raft_consensus"

        # Check description exists and is non-empty
        heal_desc = getattr(heal_fuse_mount, "description", None) or getattr(heal_fuse_mount, "__doc__", "")
        raft_desc = getattr(check_raft_consensus, "description", None) or getattr(check_raft_consensus, "__doc__", "")
        assert heal_desc and len(heal_desc) > 10
        assert raft_desc and len(raft_desc) > 10

        # Check inputs schema
        if hasattr(heal_fuse_mount, "inputs"):
            inputs = heal_fuse_mount.inputs
            assert "mount_point" in inputs
            assert inputs["mount_point"]["type"] == "string"
            assert "filer_endpoints" in inputs
            assert inputs["filer_endpoints"]["type"] == "string"
            assert "force_lazy" in inputs
            assert inputs["force_lazy"]["type"] == "boolean"
            assert "timeout_seconds" in inputs
            assert inputs["timeout_seconds"]["type"] == "integer"

        if hasattr(check_raft_consensus, "inputs"):
            inputs = check_raft_consensus.inputs
            assert "master_peers" in inputs
            assert inputs["master_peers"]["type"] == "string"
            assert "timeout_seconds" in inputs
            assert inputs["timeout_seconds"]["type"] == "integer"

    def test_smolagents_agent_registration(self):
        """Verify registration into ToolCallingAgent when smolagents is available."""
        if not HAS_SMOLAGENTS:
            pytest.skip("smolagents not installed in current environment")

        class MockLLMModel:
            def __call__(self, messages, stop_sequences=None, grammar=None):
                return "Mock LLM step"

        agent = ToolCallingAgent(tools=[heal_fuse_mount, check_raft_consensus], model=MockLLMModel())
        assert "heal_fuse_mount" in agent.tools
        assert "check_raft_consensus" in agent.tools
        assert agent.tools["heal_fuse_mount"].output_type == "string"
        assert agent.tools["check_raft_consensus"].output_type == "string"


# ==============================================================================
# SECTION 2: DYNAMIC AGENT LOOP & REFLEX ARC EXECUTION
# ==============================================================================

class TestDynamicAgentLoopReflexArc:
    def test_agent_execute_tool_call_raft_audit(self, mock_3node_raft_cluster):
        """Test ToolCallingAgent dynamic tool call execution for check_raft_consensus."""
        endpoints, leader = mock_3node_raft_cluster
        peers_str = ",".join(endpoints)

        if HAS_SMOLAGENTS:
            class MockLLM:
                def __call__(self, messages, stop_sequences=None, grammar=None):
                    return "Raft check step"

            agent = ToolCallingAgent(tools=[heal_fuse_mount, check_raft_consensus], model=MockLLM())
            raw_result = agent.execute_tool_call(
                "check_raft_consensus",
                {"master_peers": peers_str, "timeout_seconds": 2}
            )
        else:
            raw_result = check_raft_consensus(master_peers=peers_str, timeout_seconds=2)

        data = json.loads(raw_result)
        assert data["status"] == "QUORUM_HEALTHY"
        assert data["has_quorum"] is True
        assert data["reachable_peers_count"] == 3
        assert data["consensus_leader"] == _normalize_leader_addr(leader)

    def test_agent_execute_tool_call_heal_fuse(self, mock_3node_raft_cluster):
        """Test ToolCallingAgent dynamic tool call execution for heal_fuse_mount."""
        endpoints, _ = mock_3node_raft_cluster
        live_filer = endpoints[0]

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("subprocess.Popen") as mock_popen:
                mock_proc = MagicMock()
                mock_popen.return_value = mock_proc

                if HAS_SMOLAGENTS:
                    class MockLLM:
                        def __call__(self, messages, stop_sequences=None, grammar=None):
                            return "Heal mount step"

                    agent = ToolCallingAgent(tools=[heal_fuse_mount, check_raft_consensus], model=MockLLM())
                    raw_result = agent.execute_tool_call(
                        "heal_fuse_mount",
                        {
                            "mount_point": tmp_dir,
                            "filer_endpoints": f"{live_filer},127.0.0.1:49999",
                            "force_lazy": True,
                            "timeout_seconds": 2
                        }
                    )
                else:
                    raw_result = heal_fuse_mount(
                        mount_point=tmp_dir,
                        filer_endpoints=f"{live_filer},127.0.0.1:49999",
                        force_lazy=True,
                        timeout_seconds=2
                    )

                data = json.loads(raw_result)
                assert "actions_taken" in data
                assert any("preflight_filer_check_passed" in a for a in data["actions_taken"])
                assert "remount_command_executed" in data["actions_taken"]

    def test_agent_multi_turn_reflex_loop(self, mock_3node_raft_cluster):
        """Simulate autonomous dynamic reflex loop: Raft Audit -> FUSE Health Check -> Action."""
        endpoints, _ = mock_3node_raft_cluster
        peers_str = ",".join(endpoints)

        # Step 1: Reflex Arc audits Raft consensus
        audit_raw = check_raft_consensus(master_peers=peers_str, timeout_seconds=1)
        audit_data = json.loads(audit_raw)
        assert audit_data["has_quorum"] is True

        # Step 2: Reflex Arc audits FUSE mount health
        with tempfile.TemporaryDirectory() as tmp_dir:
            heal_raw = heal_fuse_mount(
                mount_point=tmp_dir,
                filer_endpoints=endpoints[0],
                force_lazy=True,
                timeout_seconds=1
            )
            heal_data = json.loads(heal_raw)
            assert isinstance(heal_data, dict)
            assert "status" in heal_data
            assert "actions_taken" in heal_data


# ==============================================================================
# SECTION 3: STRICT JSON SERIALIZATION & DESERIALIZATION VERIFICATION
# ==============================================================================

class TestJsonDeserializationCleanliness:
    """Verify that 100% of return values from both tools parse strictly with json.loads()."""

    def test_heal_fuse_mount_all_branches_json_clean(self, mock_3node_raft_cluster):
        endpoints, _ = mock_3node_raft_cluster

        # Branch 1: Non-existent mount + Offline filers
        res1 = heal_fuse_mount(mount_point="/tmp/unlikely_mount_path_123", filer_endpoints="127.0.0.1:54321", timeout_seconds=1)
        parsed1 = json.loads(res1)
        assert isinstance(parsed1, dict)
        assert parsed1["status"] == "UNMOUNTED_FILER_OFFLINE"
        assert parsed1["is_mounted"] is False
        assert isinstance(parsed1["actions_taken"], list)
        assert isinstance(parsed1["elapsed_seconds"], (int, float))

        # Branch 2: Healthy mount canary stat probe passed
        # Mocking stat probe and mount command
        with patch("subprocess.run") as mock_subrun:
            mock_mount = MagicMock(return_value=subprocess.CompletedProcess(args=["mount"], returncode=0, stdout="weed on /mnt/dfs (fuse)"))
            mock_stat = MagicMock(return_value=subprocess.CompletedProcess(args=["stat"], returncode=0, stdout="File: /mnt/dfs"))
            
            def side_effect(*args, **kwargs):
                cmd = args[0]
                if cmd[0] == "mount":
                    return mock_mount()
                elif cmd[0] == "stat":
                    return mock_stat()
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="")
            
            mock_subrun.side_effect = side_effect
            res2 = heal_fuse_mount(mount_point="/mnt/dfs", filer_endpoints=endpoints[0], timeout_seconds=1)
            parsed2 = json.loads(res2)
            assert isinstance(parsed2, dict)
            assert parsed2["status"] == "HEALTHY"
            assert parsed2["is_mounted"] is True
            assert parsed2["is_frozen"] is False
            assert "canary_stat_probe_passed" in parsed2["actions_taken"]

        # Branch 3: Frozen mount -> Dismantle & Remount
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("subprocess.Popen") as mock_popen:
                mock_popen.return_value = MagicMock()
                res3 = heal_fuse_mount(mount_point=tmp_dir, filer_endpoints=endpoints[0], timeout_seconds=1)
                parsed3 = json.loads(res3)
                assert isinstance(parsed3, dict)
                assert parsed3["status"] in ("HEALED_SUCCESSFULLY", "REMOUNT_FAILED")
                assert "actions_taken" in parsed3

    def test_check_raft_consensus_all_branches_json_clean(self, mock_3node_raft_cluster):
        endpoints, leader = mock_3node_raft_cluster

        # Branch 1: Quorum Healthy
        res1 = check_raft_consensus(master_peers=",".join(endpoints), timeout_seconds=1)
        parsed1 = json.loads(res1)
        assert isinstance(parsed1, dict)
        assert parsed1["status"] == "QUORUM_HEALTHY"
        assert parsed1["has_quorum"] is True
        assert parsed1["quorum_required"] == 2
        assert parsed1["reachable_peers_count"] == 3
        assert isinstance(parsed1["peer_details"], dict)

        # Branch 2: Quorum Lost (all peers down)
        res2 = check_raft_consensus(master_peers="127.0.0.1:51111,127.0.0.1:51112,127.0.0.1:51113", timeout_seconds=1)
        parsed2 = json.loads(res2)
        assert isinstance(parsed2, dict)
        assert parsed2["status"] == "QUORUM_LOST_CRITICAL"
        assert parsed2["has_quorum"] is False
        assert parsed2["reachable_peers_count"] == 0

        # Branch 3: Split-Brain Simulation
        # Peer 1 claims Peer 1 is leader, Peer 2 claims Peer 2 is leader
        s1 = HTTPServer(("127.0.0.1", 0), MockSeaweedMasterRaftHandler)
        s1_port = s1.server_address[1]
        s1.RequestHandlerClass.leader_addr = f"127.0.0.1:{s1_port}.19333"
        s1.RequestHandlerClass.is_leader = True
        t1 = threading.Thread(target=s1.serve_forever, daemon=True)
        t1.start()

        s2 = HTTPServer(("127.0.0.1", 0), MockSeaweedMasterRaftHandler)
        s2_port = s2.server_address[1]
        class SplitBrainHandler(BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                resp = {"IsLeader": True, "Leader": f"127.0.0.1:{s2_port}.19333", "Peers": []}
                self.wfile.write(json.dumps(resp).encode("utf-8"))

        s2.RequestHandlerClass = SplitBrainHandler
        t2 = threading.Thread(target=s2.serve_forever, daemon=True)
        t2.start()

        try:
            res3 = check_raft_consensus(master_peers=f"127.0.0.1:{s1_port},127.0.0.1:{s2_port}", timeout_seconds=1)
            parsed3 = json.loads(res3)
            assert isinstance(parsed3, dict)
            assert parsed3["is_split_brain"] is True
            assert parsed3["status"] == "SPLIT_BRAIN_DETECTED"
        finally:
            s1.shutdown()
            s1.server_close()
            s2.shutdown()
            s2.server_close()


# ==============================================================================
# SECTION 4: ADVERSARIAL RESILIENCE & ERROR CONTAINMENT
# ==============================================================================

class TestAdversarialResilience:
    def test_corrupted_non_json_http_response_containment(self):
        """Verify zero unhandled exceptions when master returns corrupted HTML 502."""
        server = HTTPServer(("127.0.0.1", 0), MockSeaweedMasterRaftHandler)
        port = server.server_address[1]
        server.RequestHandlerClass.corrupt_response = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            raw_res = check_raft_consensus(master_peers=f"127.0.0.1:{port}", timeout_seconds=1)
            parsed = json.loads(raw_res)
            assert isinstance(parsed, dict)
            assert parsed["status"] == "QUORUM_LOST_CRITICAL"
            assert f"127.0.0.1:{port}" in parsed["peer_details"]
            assert "cluster_error" in parsed["peer_details"][f"127.0.0.1:{port}"]
        finally:
            server.shutdown()
            server.server_close()

    def test_http_500_internal_error_containment(self):
        """Verify zero unhandled exceptions when master returns HTTP 500."""
        server = HTTPServer(("127.0.0.1", 0), MockSeaweedMasterRaftHandler)
        port = server.server_address[1]
        server.RequestHandlerClass.http_error_code = 500
        server.RequestHandlerClass.corrupt_response = False
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            raw_res = check_raft_consensus(master_peers=f"127.0.0.1:{port}", timeout_seconds=1)
            parsed = json.loads(raw_res)
            assert isinstance(parsed, dict)
            assert parsed["status"] == "QUORUM_LOST_CRITICAL"
            assert "HTTP_500" in parsed["peer_details"][f"127.0.0.1:{port}"]["cluster_error"]
        finally:
            server.shutdown()
            server.server_close()

    def test_pathological_inputs_containment(self):
        """Test resilience against malformed strings, null bytes, negative values."""
        # Null bytes in path
        res1 = heal_fuse_mount(mount_point="\x00\x00/mnt/bad", filer_endpoints="", timeout_seconds=-10)
        parsed1 = json.loads(res1)
        assert isinstance(parsed1, dict)

        # Empty and garbage peers
        res2 = check_raft_consensus(master_peers=":::invalid:::, , 999.999.999.999:9999", timeout_seconds=0)
        parsed2 = json.loads(res2)
        assert isinstance(parsed2, dict)
        assert parsed2["status"] == "QUORUM_LOST_CRITICAL"


# ==============================================================================
# SECTION 5: PERFORMANCE BENCHMARK & TIMING ENFORCEMENT
# ==============================================================================

class TestPerformanceAndTimings:
    def test_fast_path_stat_probe_latency(self):
        """Fast-path health probe on healthy mount must execute in < 50ms."""
        with patch("subprocess.run") as mock_subrun:
            def side_effect(*args, **kwargs):
                cmd = args[0]
                if cmd[0] == "mount":
                    return subprocess.CompletedProcess(
                        args=cmd,
                        returncode=0,
                        stdout="fuse@osxfuse0 on /mnt/dfs_unified (osxfuse, nodev, nosuid)"
                    )
                elif cmd[0] == "stat":
                    return subprocess.CompletedProcess(
                        args=cmd,
                        returncode=0,
                        stdout="stat ok"
                    )
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="")

            mock_subrun.side_effect = side_effect
            start = time.perf_counter()
            raw_res = heal_fuse_mount(mount_point="/mnt/dfs_unified", filer_endpoints="127.0.0.1:8888", timeout_seconds=2)
            elapsed_ms = (time.perf_counter() - start) * 1000

            parsed = json.loads(raw_res)
            assert parsed["status"] == "HEALTHY"
            assert elapsed_ms < 50.0  # Fast path must be under 50ms

    def test_timeout_bounds_enforcement_on_dead_endpoints(self):
        """Check that timeout_seconds=1 strictly bounds network probe latency."""
        # Unroutable IP on non-routable range (RFC 5737 TEST-NET 192.0.2.1)
        start = time.perf_counter()
        raw_res = check_raft_consensus(
            master_peers="192.0.2.1:9333",
            timeout_seconds=1
        )
        elapsed_sec = time.perf_counter() - start
        parsed = json.loads(raw_res)
        assert parsed["has_quorum"] is False
        assert elapsed_sec <= 3.5

    def test_stress_harness_50_iterations_percentiles(self, mock_3node_raft_cluster):
        """Run 50 consecutive Raft audit calls and compute P50, P95, P99 latency percentiles."""
        endpoints, _ = mock_3node_raft_cluster
        peers_str = ",".join(endpoints)
        latencies_ms: List[float] = []

        for _ in range(50):
            t0 = time.perf_counter()
            res = check_raft_consensus(master_peers=peers_str, timeout_seconds=1)
            t1 = time.perf_counter()
            parsed = json.loads(res)
            assert parsed["status"] == "QUORUM_HEALTHY"
            latencies_ms.append((t1 - t0) * 1000)

        latencies_ms.sort()
        p50 = latencies_ms[int(len(latencies_ms) * 0.50)]
        p95 = latencies_ms[int(len(latencies_ms) * 0.95)]
        p99 = latencies_ms[int(len(latencies_ms) * 0.99)]

        print(f"\n[BENCHMARK] 50-Run Stress Harness: P50={p50:.2f}ms, P95={p95:.2f}ms, P99={p99:.2f}ms")
        assert p50 < 25.0
        assert p99 < 50.0
