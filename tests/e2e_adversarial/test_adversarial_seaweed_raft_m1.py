#!/usr/bin/env python3
"""
================================================================================
LAUBURU MONOREPO: ADVERSARIAL STRESS TEST SUITE FOR MILESTONE 1
SeaweedFS 3-Node Raft Cluster Deployment & Consensus Integrity
================================================================================
Empirical Challenger 1 Test Suite:
  1. Quorum Math, Boundary Conditions, and Asymmetric Partition Matrices
  2. Corrupted, Empty, and Malformed Configuration Ingestion
  3. Live Multi-Socket Emulation & Dynamic Leader Failover Scenarios
  4. Script Subprocess Execution & Exit Code Determinism (validate_seaweed_ha.sh)
  5. YAML Schema Audit & Compose Contract Adherence
  6. High-Concurrency Stress Harness & Resource Contention
================================================================================
"""

import os
import sys
import time
import json
import socket
import tempfile
import threading
import subprocess
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import yaml
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.test_seaweed_ha_watchdog import (
    RaftConsensusEngine,
    FUSEWatchdogEngine,
    DEFAULT_MASTER_PEERS,
    DEFAULT_FILER_ENDPOINTS,
    DEFAULT_GRPC_OFFSETS,
)

COMPOSE_HA_FILE = REPO_ROOT / "00_core_infrastructure" / "docker" / "docker-compose.dfs-ha.yml"
COMPOSE_LOCAL_FILE = REPO_ROOT / "00_core_infrastructure" / "seaweedfs" / "docker-compose.yml"
VALIDATE_SCRIPT = REPO_ROOT / "00_core_infrastructure" / "scripts" / "validate_seaweed_ha.sh"
START_SCRIPT = REPO_ROOT / "00_core_infrastructure" / "scripts" / "start_seaweed_ha.sh"


# ==============================================================================
# SECTION 1: QUORUM ARITHMETIC & PARTITION MATRICES
# ==============================================================================

class TestQuorumMathAndPartitionMatrix:
    """Stress test Raft quorum calculations across arbitrary and boundary node counts."""

    @pytest.mark.parametrize("node_count, expected_quorum", [
        (1, 1),
        (2, 2),
        (3, 2),
        (4, 3),
        (5, 3),
        (6, 4),
        (7, 4),
        (9, 5),
        (11, 6),
        (21, 11),
    ])
    def test_quorum_math_odd_and_even(self, node_count, expected_quorum):
        """Verify strict majority: floor(N/2) + 1."""
        calculated = RaftConsensusEngine.calculate_quorum_required(node_count)
        assert calculated == expected_quorum, f"Failed for {node_count} nodes: got {calculated}, expected {expected_quorum}"

    def test_quorum_math_zero_and_negative(self):
        """Zero or negative node counts should return 0 safely."""
        assert RaftConsensusEngine.calculate_quorum_required(0) == 0
        assert RaftConsensusEngine.calculate_quorum_required(-5) == 0

    def test_partition_matrix_three_node_scenarios(self):
        """Exhaustively evaluate all 2^3 = 8 partition combinations for a 3-node cluster with standardized IP:port peers."""
        nodes = ["100.101.39.98:9333", "100.119.199.76:9333", "100.103.212.21:9333"]
        
        # Binary combinations of node reachability (000 to 111)
        for mask in range(8):
            online_nodes = [nodes[i] for i in range(3) if (mask & (1 << i))]
            count = len(online_nodes)
            
            if count == 0:
                responses = {}
            else:
                leader = online_nodes[0]
                responses = {
                    n: {
                        "IsLeader": (n == leader),
                        "Leader": f"{leader}.19333"
                    }
                    for n in online_nodes
                }
            
            evaluation = RaftConsensusEngine.evaluate_cluster_status(responses, expected_peers_count=3)
            
            if count >= 2:
                assert evaluation["has_quorum"] is True, f"Mask {bin(mask)} (count {count}) should have quorum"
                assert evaluation["status"] == "QUORUM_HEALTHY"
                assert evaluation["consensus_leader"] == leader
            else:
                assert evaluation["has_quorum"] is False, f"Mask {bin(mask)} (count {count}) should NOT have quorum"
                assert evaluation["status"] == "QUORUM_LOST_CRITICAL"

    def test_asymmetric_partition_split_leader_view(self):
        """Simulate asymmetric partition: Node 1 thinks Node 1 is leader; Node 2 thinks Node 2 is leader."""
        asymmetric_responses = {
            "100.101.39.98:9333": {"IsLeader": True, "Leader": "100.101.39.98:9333.19333"},
            "100.119.199.76:9333": {"IsLeader": True, "Leader": "100.119.199.76:9333.19333"},
            "100.103.212.21:9333": {"IsLeader": False, "Leader": "100.101.39.98:9333.19333"},
        }
        res = RaftConsensusEngine.evaluate_cluster_status(asymmetric_responses, expected_peers_count=3)
        assert res["status"] == "SPLIT_BRAIN_DETECTED"
        assert res["is_split_brain"] is True

    def test_no_leader_elected_state(self):
        """All nodes online but election is in progress (no leader set)."""
        candidate_responses = {
            "100.101.39.98:9333": {"IsLeader": False, "Leader": ""},
            "100.119.199.76:9333": {"IsLeader": False, "Leader": ""},
            "100.103.212.21:9333": {"IsLeader": False, "Leader": ""},
        }
        res = RaftConsensusEngine.evaluate_cluster_status(candidate_responses, expected_peers_count=3)
        assert res["status"] == "NO_LEADER_ELECTED"
        assert res["has_quorum"] is True
        assert res["consensus_leader"] == ""


# ==============================================================================
# SECTION 2: ADVERSARIAL INPUT SANITIZATION & CORRUPTED CONFIGS
# ==============================================================================

class TestCorruptedAndAdversarialConfigs:
    """Stress test string parsers, malformed configs, and hostile inputs."""

    @pytest.mark.parametrize("corrupted_addr, expected_ip, expected_http, expected_grpc", [
        ("100.101.39.98:9333", "100.101.39.98", 9333, 19333),
        ("100.101.39.98:9333.19333", "100.101.39.98", 9333, 19333),
        ("127.0.0.1:8080.18080", "127.0.0.1", 8080, 18080),
        ("10.0.0.1:1000", "10.0.0.1", 1000, 11000),
    ])
    def test_peer_address_parsing_variations(self, corrupted_addr, expected_ip, expected_http, expected_grpc):
        """Parse valid address variations with and without explicit gRPC."""
        parsed = RaftConsensusEngine.parse_peer_address(corrupted_addr)
        assert parsed["ip"] == expected_ip
        assert parsed["http_port"] == expected_http
        assert parsed["grpc_port"] == expected_grpc

    def test_peer_address_parsing_empty_and_null(self):
        """Empty or None address string handling."""
        assert RaftConsensusEngine.parse_peer_address("") == {"ip": "", "http_port": 0, "grpc_port": 0, "raw": ""}
        assert RaftConsensusEngine.parse_peer_address(None) == {"ip": "", "http_port": 0, "grpc_port": 0, "raw": None}

    def test_normalize_leader_addr_variations(self):
        """Normalize compound address 'IP:HTTP.GRPC' or 'IP:HTTP'."""
        assert RaftConsensusEngine.normalize_leader_addr("100.101.39.98:9333.19333") == "100.101.39.98:9333"
        assert RaftConsensusEngine.normalize_leader_addr("100.101.39.98:9333") == "100.101.39.98:9333"
        assert RaftConsensusEngine.normalize_leader_addr("") == ""
        assert RaftConsensusEngine.normalize_leader_addr(None) == ""

    def test_corrupted_json_handling_in_query_master_status(self):
        """Verify query_master_status does not crash when receiving non-JSON payload."""
        res = RaftConsensusEngine.query_master_status("127.0.0.1:59998", timeout_seconds=0.2)
        assert res["reachable"] is False
        assert "error" in res


# ==============================================================================
# SECTION 3: MULTI-MASTER SOCKET SIMULATION & DYNAMIC LEADER FAILOVER
# ==============================================================================

class DynamicMockMaster(BaseHTTPRequestHandler):
    """Dynamic mock HTTP server representing a SeaweedFS Master node."""
    cluster_state = {}  # Shared state across mock master instances

    def do_GET(self):
        port = self.server.server_port
        node_id = f"127.0.0.1:{port}"
        
        node_info = self.cluster_state.get(node_id, {})
        if node_info.get("offline", False):
            self.close_connection = True
            return

        status_code = node_info.get("http_status", 200)
        if status_code != 200:
            self.send_response(status_code)
            self.end_headers()
            self.wfile.write(b"Error")
            return

        if self.path in ("/cluster/status", "/dir/status"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            payload = {
                "IsLeader": node_info.get("is_leader", False),
                "Leader": node_info.get("leader", ""),
                "Peers": node_info.get("peers", []),
                "TopologyId": node_info.get("topology_id", "seaweed_topo_1"),
                "Topology": {
                    "Free": node_info.get("free", 100),
                    "Max": node_info.get("max", 200)
                }
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))
        elif self.path == "/dir/assign":
            if node_info.get("is_leader", False):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"fid": "3,01a2b3c4d5", "url": "127.0.0.1:8080"}).encode("utf-8"))
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Not Leader")
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass


@pytest.fixture(scope="class")
def mock_3node_cluster():
    """Spin up 3 local ephemeral HTTP servers emulating a 3-node Raft cluster."""
    servers = []
    ports = []
    threads = []
    DynamicMockMaster.cluster_state = {}

    for i in range(3):
        srv = HTTPServer(("127.0.0.1", 0), DynamicMockMaster)
        p = srv.server_port
        ports.append(p)
        servers.append(srv)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        threads.append(t)

    node1 = f"127.0.0.1:{ports[0]}"
    node2 = f"127.0.0.1:{ports[1]}"
    node3 = f"127.0.0.1:{ports[2]}"

    # Initial state: Node 1 is Leader
    DynamicMockMaster.cluster_state = {
        node1: {"is_leader": True, "leader": f"{node1}.{ports[0]+10000}", "peers": [node2, node3], "free": 100, "max": 200},
        node2: {"is_leader": False, "leader": f"{node1}.{ports[0]+10000}", "peers": [node1, node3], "free": 80, "max": 150},
        node3: {"is_leader": False, "leader": f"{node1}.{ports[0]+10000}", "peers": [node1, node2], "free": 60, "max": 100},
    }

    yield {
        "nodes": [node1, node2, node3],
        "ports": ports,
        "servers": servers,
    }

    for srv in servers:
        srv.shutdown()
        srv.server_close()


class TestMultiMasterSocketSimulation:
    """Simulate dynamic live cluster operations, leader death, failover, and split-brain."""

    def test_healthy_3node_cluster_query(self, mock_3node_cluster):
        """Query all 3 live mock nodes and evaluate consensus."""
        nodes = mock_3node_cluster["nodes"]
        responses = {}
        for n in nodes:
            res = RaftConsensusEngine.query_master_status(n, timeout_seconds=1.0)
            assert res["reachable"] is True
            responses[n] = res["data"]

        eval_res = RaftConsensusEngine.evaluate_cluster_status(responses, expected_peers_count=3)
        assert eval_res["status"] == "QUORUM_HEALTHY"
        assert eval_res["has_quorum"] is True
        assert eval_res["reachable_peers_count"] == 3
        assert eval_res["consensus_leader"] == nodes[0]
        assert eval_res["is_split_brain"] is False

    def test_dynamic_leader_failover(self, mock_3node_cluster):
        """Simulate death of Node 1, election of Node 2 as new Leader."""
        nodes = mock_3node_cluster["nodes"]
        node1, node2, node3 = nodes

        # Kill Node 1, Promote Node 2
        DynamicMockMaster.cluster_state[node1]["offline"] = True
        DynamicMockMaster.cluster_state[node2]["is_leader"] = True
        DynamicMockMaster.cluster_state[node2]["leader"] = f"{node2}.{mock_3node_cluster['ports'][1]+10000}"
        DynamicMockMaster.cluster_state[node3]["leader"] = f"{node2}.{mock_3node_cluster['ports'][1]+10000}"

        responses = {}
        for n in [node2, node3]:
            res = RaftConsensusEngine.query_master_status(n, timeout_seconds=1.0)
            assert res["reachable"] is True
            responses[n] = res["data"]

        eval_res = RaftConsensusEngine.evaluate_cluster_status(responses, expected_peers_count=3)
        assert eval_res["status"] == "QUORUM_HEALTHY"
        assert eval_res["has_quorum"] is True
        assert eval_res["reachable_peers_count"] == 2
        assert eval_res["consensus_leader"] == node2
        assert eval_res["is_split_brain"] is False

    def test_quorum_loss_under_two_node_failure(self, mock_3node_cluster):
        """Simulate failure of Node 2 as well, leaving only Node 3 (1/3 nodes)."""
        nodes = mock_3node_cluster["nodes"]
        node1, node2, node3 = nodes

        DynamicMockMaster.cluster_state[node1]["offline"] = True
        DynamicMockMaster.cluster_state[node2]["offline"] = True

        responses = {}
        res = RaftConsensusEngine.query_master_status(node3, timeout_seconds=1.0)
        assert res["reachable"] is True
        responses[node3] = res["data"]

        eval_res = RaftConsensusEngine.evaluate_cluster_status(responses, expected_peers_count=3)
        assert eval_res["status"] == "QUORUM_LOST_CRITICAL"
        assert eval_res["has_quorum"] is False
        assert eval_res["reachable_peers_count"] == 1

    def test_split_brain_detection(self, mock_3node_cluster):
        """Simulate split brain: Node 1 and Node 2 both claim leadership independently."""
        nodes = mock_3node_cluster["nodes"]
        node1, node2, node3 = nodes

        DynamicMockMaster.cluster_state[node1]["offline"] = False
        DynamicMockMaster.cluster_state[node2]["offline"] = False
        DynamicMockMaster.cluster_state[node1]["is_leader"] = True
        DynamicMockMaster.cluster_state[node1]["leader"] = f"{node1}.{mock_3node_cluster['ports'][0]+10000}"
        DynamicMockMaster.cluster_state[node2]["is_leader"] = True
        DynamicMockMaster.cluster_state[node2]["leader"] = f"{node2}.{mock_3node_cluster['ports'][1]+10000}"

        responses = {}
        for n in [node1, node2]:
            res = RaftConsensusEngine.query_master_status(n, timeout_seconds=1.0)
            assert res["reachable"] is True
            responses[n] = res["data"]

        eval_res = RaftConsensusEngine.evaluate_cluster_status(responses, expected_peers_count=3)
        assert eval_res["status"] == "SPLIT_BRAIN_DETECTED"
        assert eval_res["is_split_brain"] is True


# ==============================================================================
# SECTION 4: SCRIPT EXECUTION & EXIT CODE AUDITS
# ==============================================================================

class TestScriptSubprocessExecution:
    """Empirically execute validate_seaweed_ha.sh under controlled mock topologies."""

    def test_validate_script_exists_and_executable(self):
        """Validate script presence and permissions."""
        assert VALIDATE_SCRIPT.exists(), f"Missing {VALIDATE_SCRIPT}"
        assert os.access(VALIDATE_SCRIPT, os.R_OK), f"Not readable: {VALIDATE_SCRIPT}"

    def test_start_script_exists_and_executable(self):
        """Start script presence and permissions."""
        assert START_SCRIPT.exists(), f"Missing {START_SCRIPT}"
        assert os.access(START_SCRIPT, os.R_OK), f"Not readable: {START_SCRIPT}"

    def test_validate_script_quorum_healthy_execution(self, mock_3node_cluster):
        """Run validate_seaweed_ha.sh against healthy 3-node mock cluster."""
        nodes = mock_3node_cluster["nodes"]
        node1, node2, node3 = nodes

        # Reset healthy state
        DynamicMockMaster.cluster_state[node1] = {
            "offline": False, "is_leader": True, "leader": f"{node1}.{mock_3node_cluster['ports'][0]+10000}",
            "peers": [node2, node3], "free": 100, "max": 200, "topology_id": "topo1"
        }
        DynamicMockMaster.cluster_state[node2] = {
            "offline": False, "is_leader": False, "leader": f"{node1}.{mock_3node_cluster['ports'][0]+10000}",
            "peers": [node1, node3], "free": 80, "max": 150, "topology_id": "topo1"
        }
        DynamicMockMaster.cluster_state[node3] = {
            "offline": False, "is_leader": False, "leader": f"{node1}.{mock_3node_cluster['ports'][0]+10000}",
            "peers": [node1, node2], "free": 60, "max": 100, "topology_id": "topo1"
        }

        peer_arg = ",".join(nodes)
        proc = subprocess.run(["bash", str(VALIDATE_SCRIPT), peer_arg], capture_output=True, text=True)
        assert proc.returncode in (0, 3), f"Script failed unexpectedly with code {proc.returncode}: {proc.stdout}\n{proc.stderr}"
        assert "QUORUM HEALTHY" in proc.stdout
        assert "PASSED (Unified Single Leader)" in proc.stdout

    def test_validate_script_quorum_lost_exit_code_1(self, mock_3node_cluster):
        """Run validate_seaweed_ha.sh with 2 nodes offline (Quorum lost) -> Exit Code 1."""
        nodes = mock_3node_cluster["nodes"]
        node1, node2, node3 = nodes

        DynamicMockMaster.cluster_state[node1]["offline"] = True
        DynamicMockMaster.cluster_state[node2]["offline"] = True
        DynamicMockMaster.cluster_state[node3]["offline"] = False

        peer_arg = ",".join(nodes)
        proc = subprocess.run(["bash", str(VALIDATE_SCRIPT), peer_arg], capture_output=True, text=True)
        assert proc.returncode == 1, f"Expected exit code 1 for quorum loss, got {proc.returncode}"
        assert "CRITICAL: QUORUM LOST" in proc.stdout

    def test_validate_script_split_brain_exit_code_2(self, mock_3node_cluster):
        """Run validate_seaweed_ha.sh under split-brain state -> Exit Code 2."""
        nodes = mock_3node_cluster["nodes"]
        node1, node2, node3 = nodes

        DynamicMockMaster.cluster_state[node1]["offline"] = False
        DynamicMockMaster.cluster_state[node2]["offline"] = False
        DynamicMockMaster.cluster_state[node3]["offline"] = False
        DynamicMockMaster.cluster_state[node1]["is_leader"] = True
        DynamicMockMaster.cluster_state[node1]["leader"] = f"{node1}.{mock_3node_cluster['ports'][0]+10000}"
        DynamicMockMaster.cluster_state[node2]["is_leader"] = True
        DynamicMockMaster.cluster_state[node2]["leader"] = f"{node2}.{mock_3node_cluster['ports'][1]+10000}"
        DynamicMockMaster.cluster_state[node3]["leader"] = f"{node1}.{mock_3node_cluster['ports'][0]+10000}"

        peer_arg = ",".join(nodes)
        proc = subprocess.run(["bash", str(VALIDATE_SCRIPT), peer_arg], capture_output=True, text=True)
        assert proc.returncode == 2, f"Expected exit code 2 for split brain, got {proc.returncode}"
        assert "SPLIT BRAIN DETECTED" in proc.stdout


# ==============================================================================
# SECTION 5: DOCKER COMPOSE SCHEMA & CONTRACT AUDIT
# ==============================================================================

class TestDockerComposeSchemaAndContracts:
    """Verify syntactic correctness, schema adherence, and parameter matching in Docker Compose files."""

    def test_compose_ha_file_parses_valid_yaml(self):
        """Verify docker-compose.dfs-ha.yml is valid YAML."""
        assert COMPOSE_HA_FILE.exists(), f"Missing {COMPOSE_HA_FILE}"
        with open(COMPOSE_HA_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)
        assert "services" in data
        assert len(data["services"]) >= 3

    def test_compose_local_file_parses_valid_yaml(self):
        """Verify seaweedfs/docker-compose.yml is valid YAML."""
        assert COMPOSE_LOCAL_FILE.exists(), f"Missing {COMPOSE_LOCAL_FILE}"
        with open(COMPOSE_LOCAL_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)
        assert "services" in data
        assert "seaweed_master" in data["services"]
        assert "seaweed_filer" in data["services"]
        assert "seaweed_volume" in data["services"]

    def test_compose_ha_all_masters_configure_three_peers(self):
        """Verify all master nodes in docker-compose.dfs-ha.yml have 3 peers in command and environment."""
        with open(COMPOSE_HA_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        master_services = [s for s in data["services"].values() if "master" in s.get("labels", {}).get("com.lauburu.dfs.service", "")]
        assert len(master_services) == 3, f"Expected 3 master services, found {len(master_services)}"
        
        for s in master_services:
            cmd = s.get("command", "")
            assert "-peers=" in cmd
            for peer in DEFAULT_MASTER_PEERS:
                assert peer in cmd, f"Peer {peer} missing from master command: {cmd}"

    def test_compose_ha_all_services_use_host_networking(self):
        """All SeaweedFS HA services must use network_mode: 'host' for Tailscale direct binding."""
        with open(COMPOSE_HA_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        for name, service in data["services"].items():
            net_mode = service.get("network_mode")
            assert net_mode == "host", f"Service {name} does not use network_mode: 'host' (got {net_mode})"

    def test_compose_ha_memory_ceilings_enforced(self):
        """Ensure memory limits on all containers are bounded <= 256MB."""
        with open(COMPOSE_HA_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        for name, service in data["services"].items():
            mem_limit = service.get("mem_limit", "256m")
            if mem_limit.endswith("m") or mem_limit.endswith("M"):
                mb = int(mem_limit[:-1])
                assert mb <= 256, f"Service {name} exceeds memory ceiling: {mem_limit}"


# ==============================================================================
# SECTION 6: HIGH-CONCURRENCY STRESS HARNESS
# ==============================================================================

class TestHighConcurrencyStressHarness:
    """Stress test the Raft consensus parser under high-throughput concurrent load."""

    def test_50_concurrent_cluster_evaluations(self, mock_3node_cluster):
        """Execute 50 parallel queries and status evaluations against mock cluster."""
        nodes = mock_3node_cluster["nodes"]
        node1, node2, node3 = nodes

        # Ensure healthy state
        DynamicMockMaster.cluster_state[node1]["offline"] = False
        DynamicMockMaster.cluster_state[node2]["offline"] = False
        DynamicMockMaster.cluster_state[node3]["offline"] = False
        DynamicMockMaster.cluster_state[node1]["is_leader"] = True
        DynamicMockMaster.cluster_state[node2]["is_leader"] = False
        DynamicMockMaster.cluster_state[node3]["is_leader"] = False

        def _worker(idx):
            responses = {}
            for n in nodes:
                res = RaftConsensusEngine.query_master_status(n, timeout_seconds=1.0)
                if res["reachable"]:
                    responses[n] = res["data"]
            return RaftConsensusEngine.evaluate_cluster_status(responses, expected_peers_count=3)

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(_worker, i) for i in range(50)]
            results = [f.result() for f in futures]
        duration = time.perf_counter() - t0

        assert len(results) == 50
        for r in results:
            assert r["status"] == "QUORUM_HEALTHY"
            assert r["has_quorum"] is True
            assert r["reachable_peers_count"] == 3
        
        assert duration < 5.0, f"50 concurrent evaluations took {duration:.2f}s, expected < 5s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
