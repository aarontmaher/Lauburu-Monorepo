#!/usr/bin/env python3
"""
================================================================================
ADVERSARIAL STRESS HARNESS — CHALLENGER 2 FOR MILESTONE 1 (SEAWEEDFS 3-NODE HA)
================================================================================
Adversarially stress-tests:
1. gRPC Port Arithmetic (+10000 offset across all services and configurations)
2. validate_seaweed_ha.sh against live/unreachable sockets and edge cases:
   - Total cluster blackout (0/3 peers) -> Exit 1
   - Quorum loss (1/3 peers) -> Exit 1
   - Split-brain divergence (Conflicting leaders) -> Exit 2
   - No leader elected (Stalled / election pending) -> Exit 2
   - Healthy 2/3 quorum with consensus leader & /dir/assign -> Exit 0
   - Healthy 3/3 quorum with consensus leader & /dir/assign -> Exit 0
   - Write allocation failure when quorum active -> Exit 3
   - Derived gRPC companion socket open vs closed detection
   - Arbitrary and non-standard HTTP ports (e.g. 9334 -> 19334)
3. Multi-master failover & volume redirection simulation
================================================================================
"""

import os
import re
import sys
import json
import time
import socket
import tempfile
import threading
import subprocess
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR_SCRIPT = REPO_ROOT / "00_core_infrastructure" / "scripts" / "validate_seaweed_ha.sh"
START_SCRIPT = REPO_ROOT / "00_core_infrastructure" / "scripts" / "start_seaweed_ha.sh"
DFS_HA_COMPOSE = REPO_ROOT / "00_core_infrastructure" / "docker" / "docker-compose.dfs-ha.yml"
SEAWEEDFS_COMPOSE = REPO_ROOT / "00_core_infrastructure" / "seaweedfs" / "docker-compose.yml"


def strip_ansi(text: str) -> str:
    """Strip ANSI escape color sequences from terminal output."""
    return re.sub(r'\x1b\[[0-9;]*m', '', text)


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def find_free_port_pair() -> int:
    """Find a port P <= 55535 such that both P and P+10000 are valid and free."""
    for p in range(12000, 50000):
        try:
            s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s1.bind(("127.0.0.1", p))
            s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s2.bind(("127.0.0.1", p + 10000))
            s1.close()
            s2.close()
            return p
        except OSError:
            continue
    raise RuntimeError("No free port pair found")


# ==============================================================================
# 1. gRPC PORT ARITHMETIC & MANIFEST CONSISTENCY STRESS TESTS
# ==============================================================================

class TestGRPCArithmeticAndManifestIntegrity:
    """Stress tests for gRPC companion offset (+10000) across all services and manifests."""

    @pytest.mark.parametrize("http_port,expected_grpc", [
        (9333, 19333),  # Master
        (8888, 18888),  # Filer
        (8080, 18080),  # Volume
        (9334, 19334),  # Custom Master
        (8889, 18889),  # Custom Filer
        (8081, 18081),  # Custom Volume
        (1, 10001),     # Boundary Minimum
        (55535, 65535), # Boundary Maximum valid 16-bit TCP port
    ])
    def test_grpc_offset_formula_invariants(self, http_port: int, expected_grpc: int):
        """Invariant: gRPC companion port is always exactly HTTP port + 10000."""
        calc = http_port + 10000
        assert calc == expected_grpc
        assert 1 <= calc <= 65535

    def test_grpc_offset_overflow_detection(self):
        """Ports > 55535 produce gRPC offsets > 65535 which violate TCP/IP 16-bit port limits."""
        invalid_http_port = 55536
        grpc_port = invalid_http_port + 10000
        assert grpc_port > 65535, "Must identify port boundary overflow (>65535)"

    def test_all_compose_manifests_strict_grpc_alignment(self):
        """Inspect all compose files to ensure master, filer, and volume services enforce +10000 offset."""
        compose_files = [
            DFS_HA_COMPOSE,
            SEAWEEDFS_COMPOSE,
            REPO_ROOT / "00_core_infrastructure" / "docker" / "docker-compose.dfs.linux-head.yml",
            REPO_ROOT / "00_core_infrastructure" / "docker" / "docker-compose.dfs.m4-mini.yml",
            REPO_ROOT / "00_core_infrastructure" / "docker" / "docker-compose.dfs.macbook-pro.yml",
            REPO_ROOT / "00_core_infrastructure" / "docker" / "docker-compose.dfs.mac-mini.yml",
        ]

        verified_services_count = 0
        for compose_file in compose_files:
            assert compose_file.exists(), f"Compose file missing: {compose_file}"
            with open(compose_file, "r") as f:
                data = yaml.safe_load(f)
            
            services = data.get("services", {})
            for svc_name, svc_cfg in services.items():
                cmd = svc_cfg.get("command", "")
                if isinstance(cmd, list):
                    cmd = " ".join(cmd)
                env = svc_cfg.get("environment", [])
                env_dict = {}
                if isinstance(env, list):
                    for item in env:
                        if "=" in item:
                            k, v = item.split("=", 1)
                            env_dict[k] = v
                elif isinstance(env, dict):
                    env_dict = env

                # Check Master services
                if "master" in svc_name or "weed master" in cmd:
                    verified_services_count += 1
                    # Check gRPC port in command or env
                    if "-port=" in cmd and "-port.grpc=" in cmd:
                        http_p = int(cmd.split("-port=")[1].split()[0])
                        grpc_p = int(cmd.split("-port.grpc=")[1].split()[0])
                        assert grpc_p == http_p + 10000, f"gRPC offset mismatch in {compose_file}:{svc_name}"
                    if "WEED_MASTER_PORT" in env_dict and "WEED_MASTER_PORT_GRPC" in env_dict:
                        assert int(env_dict["WEED_MASTER_PORT_GRPC"]) == int(env_dict["WEED_MASTER_PORT"]) + 10000

                # Check Filer services
                if "filer" in svc_name or "weed filer" in cmd:
                    verified_services_count += 1
                    if "-port=" in cmd and "-port.grpc=" in cmd:
                        http_p = int(cmd.split("-port=")[1].split()[0])
                        grpc_p = int(cmd.split("-port.grpc=")[1].split()[0])
                        assert grpc_p == http_p + 10000, f"gRPC offset mismatch in {compose_file}:{svc_name}"
                    if "WEED_FILER_PORT" in env_dict and "WEED_FILER_PORT_GRPC" in env_dict:
                        assert int(env_dict["WEED_FILER_PORT_GRPC"]) == int(env_dict["WEED_FILER_PORT"]) + 10000

                # Check Volume services
                if "volume" in svc_name or "weed volume" in cmd:
                    verified_services_count += 1
                    if "-port=" in cmd and "-port.grpc=" in cmd:
                        http_p = int(cmd.split("-port=")[1].split()[0])
                        grpc_p = int(cmd.split("-port.grpc=")[1].split()[0])
                        assert grpc_p == http_p + 10000, f"gRPC offset mismatch in {compose_file}:{svc_name}"
                    if "WEED_VOLUME_PORT" in env_dict and "WEED_VOLUME_PORT_GRPC" in env_dict:
                        assert int(env_dict["WEED_VOLUME_PORT_GRPC"]) == int(env_dict["WEED_VOLUME_PORT"]) + 10000

        assert verified_services_count >= 10, f"Expected to verify at least 10 SeaweedFS services across compose files, found {verified_services_count}"


# ==============================================================================
# 2. ADVERSARIAL VALIDATOR HARNESS (validate_seaweed_ha.sh EMULATION)
# ==============================================================================

class MockSeaweedPeerHandler(BaseHTTPRequestHandler):
    """Configurable mock SeaweedFS peer responding to /cluster/status, /dir/status, /dir/assign."""
    
    is_leader: bool = False
    reported_leader: str = ""
    active_peers: List[str] = []
    topology_id: str = "lauburu_ha_topo_1"
    free_volumes: int = 100
    max_volumes: int = 150
    assign_fid: str = "3,01a2b3c4d5"
    assign_url: str = "127.0.0.1:8080"
    assign_fail: bool = False
    return_500: bool = False
    hang_seconds: float = 0.0

    def log_message(self, format, *args):
        pass  # Quiet logger

    def do_GET(self):
        if self.hang_seconds > 0:
            time.sleep(self.hang_seconds)

        if self.return_500:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'{"error": "Internal Raft Error"}')
            return

        parsed_path = urllib.parse.urlparse(self.path)
        
        if parsed_path.path == "/cluster/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            payload = {
                "IsLeader": self.is_leader,
                "Leader": self.reported_leader,
                "Peers": self.active_peers,
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return

        elif parsed_path.path == "/dir/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            payload = {
                "TopologyId": self.topology_id,
                "Topology": {
                    "Free": self.free_volumes,
                    "Max": self.max_volumes,
                }
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return

        elif parsed_path.path == "/dir/assign":
            if self.assign_fail:
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error": "No free volume slots"}')
            else:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                payload = {
                    "fid": self.assign_fid,
                    "url": self.assign_url,
                    "publicUrl": self.assign_url,
                    "count": 1
                }
                self.wfile.write(json.dumps(payload).encode("utf-8"))
            return

        else:
            self.send_response(404)
            self.end_headers()


class EphemeralPeerServer:
    def __init__(self, port: int, is_leader: bool, reported_leader: str, peers: List[str], assign_fail: bool = False, topology_id: str = "topo_1"):
        self.port = port
        self.handler = type(f"MockHandler_{port}", (MockSeaweedPeerHandler,), {
            "is_leader": is_leader,
            "reported_leader": reported_leader,
            "active_peers": peers,
            "assign_fail": assign_fail,
            "topology_id": topology_id,
        })
        self.server = HTTPServer(("127.0.0.1", self.port), self.handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


class EphemeralGRPCListener:
    """Listens on the derived gRPC port (HTTP port + 10000) to emulate an open gRPC companion socket."""
    def __init__(self, grpc_port: int):
        self.grpc_port = grpc_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = False
        self.thread = None

    def start(self):
        self.sock.bind(("127.0.0.1", self.grpc_port))
        self.sock.listen(5)
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()

    def _listen_loop(self):
        while self.running:
            try:
                self.sock.settimeout(0.5)
                client, _ = self.sock.accept()
                client.close()
            except socket.timeout:
                continue
            except Exception:
                break

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass


class TestValidateSeaweedHAValidatorHarness:
    """Empirically runs validate_seaweed_ha.sh against live test fixtures and hostile cluster states."""

    def test_script_syntax_and_executability(self):
        """Check validate_seaweed_ha.sh and start_seaweed_ha.sh exist and pass bash -n syntax check."""
        assert VALIDATOR_SCRIPT.exists()
        assert START_SCRIPT.exists()
        assert os.access(VALIDATOR_SCRIPT, os.X_OK), "Validator must be executable"
        assert os.access(START_SCRIPT, os.X_OK), "Start script must be executable"

        res = subprocess.run(["bash", "-n", str(VALIDATOR_SCRIPT)], capture_output=True, text=True)
        assert res.returncode == 0, f"Syntax error in validator: {res.stderr}"

        res_start = subprocess.run(["bash", "-n", str(START_SCRIPT)], capture_output=True, text=True)
        assert res_start.returncode == 0, f"Syntax error in start script: {res_start.stderr}"

    def test_validator_scenario_total_blackout_quorum_lost(self):
        """Scenario: 0 of 3 nodes online -> Exit code 1 (Quorum lost)."""
        p1, p2, p3 = find_free_port(), find_free_port(), find_free_port()
        peers_arg = f"127.0.0.1:{p1},127.0.0.1:{p2},127.0.0.1:{p3}"

        res = subprocess.run([str(VALIDATOR_SCRIPT), peers_arg], capture_output=True, text=True)
        assert res.returncode == 1, f"Expected exit 1 on total blackout, got {res.returncode}. Output:\n{res.stdout}"
        clean_out = strip_ansi(res.stdout)
        assert "CRITICAL: QUORUM LOST" in clean_out
        assert "Online Master Nodes:           0 / 3" in clean_out

    def test_validator_scenario_partial_quorum_loss_one_of_three(self):
        """Scenario: 1 of 3 nodes online -> Exit code 1 (Quorum lost, need 2/3)."""
        p1 = find_free_port()
        p2, p3 = find_free_port(), find_free_port()

        srv1 = EphemeralPeerServer(p1, is_leader=False, reported_leader="", peers=[f"127.0.0.1:{p1}"])
        srv1.start()
        try:
            peers_arg = f"127.0.0.1:{p1},127.0.0.1:{p2},127.0.0.1:{p3}"
            res = subprocess.run([str(VALIDATOR_SCRIPT), peers_arg], capture_output=True, text=True)
            assert res.returncode == 1, f"Expected exit 1 on 1/3 quorum, got {res.returncode}"
            clean_out = strip_ansi(res.stdout)
            assert "Online Master Nodes:           1 / 3" in clean_out
            assert "CRITICAL: QUORUM LOST" in clean_out
        finally:
            srv1.stop()

    def test_validator_scenario_split_brain_detected(self):
        """Scenario: 2 nodes online, but each claims itself as distinct leader -> Exit code 2 (Split-brain)."""
        p1 = find_free_port()
        p2 = find_free_port()
        p3 = find_free_port()

        srv1 = EphemeralPeerServer(p1, is_leader=True, reported_leader=f"127.0.0.1:{p1}", peers=[f"127.0.0.1:{p1}"])
        srv2 = EphemeralPeerServer(p2, is_leader=True, reported_leader=f"127.0.0.1:{p2}", peers=[f"127.0.0.1:{p2}"])

        srv1.start()
        srv2.start()
        try:
            peers_arg = f"127.0.0.1:{p1},127.0.0.1:{p2},127.0.0.1:{p3}"
            res = subprocess.run([str(VALIDATOR_SCRIPT), peers_arg], capture_output=True, text=True)
            assert res.returncode == 2, f"Expected exit 2 on split brain, got {res.returncode}. Output:\n{res.stdout}"
            clean_out = strip_ansi(res.stdout)
            assert "SPLIT BRAIN DETECTED" in clean_out
            assert "QUORUM HEALTHY" in clean_out
        finally:
            srv1.stop()
            srv2.stop()

    def test_validator_scenario_no_leader_elected(self):
        """Scenario: 3 nodes online, but all report Leader: 'NONE' -> Exit code 2 (No consensus leader)."""
        p1 = find_free_port()
        p2 = find_free_port()
        p3 = find_free_port()

        srv1 = EphemeralPeerServer(p1, is_leader=False, reported_leader="NONE", peers=[f"127.0.0.1:{p1}"])
        srv2 = EphemeralPeerServer(p2, is_leader=False, reported_leader="NONE", peers=[f"127.0.0.1:{p2}"])
        srv3 = EphemeralPeerServer(p3, is_leader=False, reported_leader="NONE", peers=[f"127.0.0.1:{p3}"])

        srv1.start()
        srv2.start()
        srv3.start()
        try:
            peers_arg = f"127.0.0.1:{p1},127.0.0.1:{p2},127.0.0.1:{p3}"
            res = subprocess.run([str(VALIDATOR_SCRIPT), peers_arg], capture_output=True, text=True)
            assert res.returncode == 2, f"Expected exit 2 when no leader elected, got {res.returncode}. Output:\n{res.stdout}"
            clean_out = strip_ansi(res.stdout)
            assert "Consensus Leader:              NONE (Leader election pending, offline, or stalled)" in clean_out
        finally:
            srv1.stop()
            srv2.stop()
            srv3.stop()

    def test_validator_scenario_healthy_quorum_two_of_three(self):
        """Scenario: 2 of 3 nodes online (Node 3 offline), both agree on Leader 1 -> Exit code 0."""
        p1 = find_free_port()
        p2 = find_free_port()
        p3 = find_free_port()

        srv1 = EphemeralPeerServer(p1, is_leader=True, reported_leader=f"127.0.0.1:{p1}", peers=[f"127.0.0.1:{p1}", f"127.0.0.1:{p2}"])
        srv2 = EphemeralPeerServer(p2, is_leader=False, reported_leader=f"127.0.0.1:{p1}", peers=[f"127.0.0.1:{p1}", f"127.0.0.1:{p2}"])

        srv1.start()
        srv2.start()
        try:
            peers_arg = f"127.0.0.1:{p1},127.0.0.1:{p2},127.0.0.1:{p3}"
            res = subprocess.run([str(VALIDATOR_SCRIPT), peers_arg], capture_output=True, text=True)
            assert res.returncode == 0, f"Expected exit 0 for healthy 2/3 quorum, got {res.returncode}. Output:\n{res.stdout}"
            clean_out = strip_ansi(res.stdout)
            assert "QUORUM HEALTHY" in clean_out
            assert "Consensus Leader:              127.0.0.1:" in clean_out
            assert "Split-Brain Guard:             PASSED (Unified Single Leader)" in clean_out
            assert "File ID Allocation (/dir/assign): SUCCESS" in clean_out
        finally:
            srv1.stop()
            srv2.stop()

    def test_validator_scenario_full_cluster_three_of_three(self):
        """Scenario: 3 of 3 nodes online, unified consensus leader, healthy /dir/assign -> Exit code 0."""
        p1 = find_free_port()
        p2 = find_free_port()
        p3 = find_free_port()

        srv1 = EphemeralPeerServer(p1, is_leader=True, reported_leader=f"127.0.0.1:{p1}", peers=[f"127.0.0.1:{p1}", f"127.0.0.1:{p2}", f"127.0.0.1:{p3}"])
        srv2 = EphemeralPeerServer(p2, is_leader=False, reported_leader=f"127.0.0.1:{p1}", peers=[f"127.0.0.1:{p1}", f"127.0.0.1:{p2}", f"127.0.0.1:{p3}"])
        srv3 = EphemeralPeerServer(p3, is_leader=False, reported_leader=f"127.0.0.1:{p1}", peers=[f"127.0.0.1:{p1}", f"127.0.0.1:{p2}", f"127.0.0.1:{p3}"])

        srv1.start()
        srv2.start()
        srv3.start()
        try:
            peers_arg = f"127.0.0.1:{p1},127.0.0.1:{p2},127.0.0.1:{p3}"
            res = subprocess.run([str(VALIDATOR_SCRIPT), peers_arg], capture_output=True, text=True)
            assert res.returncode == 0, f"Expected exit 0 for full cluster, got {res.returncode}. Output:\n{res.stdout}"
            clean_out = strip_ansi(res.stdout)
            assert "Online Master Nodes:           3 / 3" in clean_out
            assert "QUORUM HEALTHY" in clean_out
            assert "Split-Brain Guard:             PASSED (Unified Single Leader)" in clean_out
        finally:
            srv1.stop()
            srv2.stop()
            srv3.stop()

    def test_validator_scenario_write_allocation_failure_when_quorum_active(self):
        """Scenario: Quorum healthy (3/3), single leader, but /dir/assign fails -> Exit code 3."""
        p1 = find_free_port()
        p2 = find_free_port()
        p3 = find_free_port()

        srv1 = EphemeralPeerServer(p1, is_leader=True, reported_leader=f"127.0.0.1:{p1}", peers=[f"127.0.0.1:{p1}", f"127.0.0.1:{p2}", f"127.0.0.1:{p3}"], assign_fail=True)
        srv2 = EphemeralPeerServer(p2, is_leader=False, reported_leader=f"127.0.0.1:{p1}", peers=[f"127.0.0.1:{p1}", f"127.0.0.1:{p2}", f"127.0.0.1:{p3}"])
        srv3 = EphemeralPeerServer(p3, is_leader=False, reported_leader=f"127.0.0.1:{p1}", peers=[f"127.0.0.1:{p1}", f"127.0.0.1:{p2}", f"127.0.0.1:{p3}"])

        srv1.start()
        srv2.start()
        srv3.start()
        try:
            peers_arg = f"127.0.0.1:{p1},127.0.0.1:{p2},127.0.0.1:{p3}"
            res = subprocess.run([str(VALIDATOR_SCRIPT), peers_arg], capture_output=True, text=True)
            assert res.returncode == 3, f"Expected exit 3 on write allocation failure, got {res.returncode}. Output:\n{res.stdout}"
            clean_out = strip_ansi(res.stdout)
            assert "SKIPPED / NO ACTIVE VOLUMES" in clean_out
        finally:
            srv1.stop()
            srv2.stop()
            srv3.stop()

    def test_validator_grpc_socket_detection_open_vs_closed(self):
        """Verify script detects OPEN vs UNREACHABLE gRPC sockets on HTTP_PORT + 10000."""
        http_p = find_free_port_pair()
        grpc_p = http_p + 10000

        srv = EphemeralPeerServer(http_p, is_leader=True, reported_leader=f"127.0.0.1:{http_p}", peers=[f"127.0.0.1:{http_p}"])
        srv.start()

        try:
            peers_arg = f"127.0.0.1:{http_p}"
            res1 = subprocess.run([str(VALIDATOR_SCRIPT), peers_arg], capture_output=True, text=True)
            clean_out1 = strip_ansi(res1.stdout)
            assert f"• gRPC Companion Socket (:{grpc_p}): UNREACHABLE / OFF-MESH" in clean_out1

            # Start gRPC listener on grpc_p
            grpc_listener = EphemeralGRPCListener(grpc_p)
            grpc_listener.start()
            try:
                time.sleep(0.2)
                res2 = subprocess.run([str(VALIDATOR_SCRIPT), peers_arg], capture_output=True, text=True)
                clean_out2 = strip_ansi(res2.stdout)
                assert f"• gRPC Companion Socket (:{grpc_p}): OPEN / REACHABLE" in clean_out2
            finally:
                grpc_listener.stop()
        finally:
            srv.stop()

    def test_validator_topology_id_mismatch_detection(self):
        """Scenario: 3 nodes online, but report differing Topology IDs -> Stale Raft metadata warning."""
        p1 = find_free_port()
        p2 = find_free_port()
        p3 = find_free_port()

        srv1 = EphemeralPeerServer(p1, is_leader=True, reported_leader=f"127.0.0.1:{p1}", peers=[f"127.0.0.1:{p1}", f"127.0.0.1:{p2}", f"127.0.0.1:{p3}"], topology_id="cluster_topo_v1")
        srv2 = EphemeralPeerServer(p2, is_leader=False, reported_leader=f"127.0.0.1:{p1}", peers=[f"127.0.0.1:{p1}", f"127.0.0.1:{p2}", f"127.0.0.1:{p3}"], topology_id="cluster_topo_v2_STALE")
        srv3 = EphemeralPeerServer(p3, is_leader=False, reported_leader=f"127.0.0.1:{p1}", peers=[f"127.0.0.1:{p1}", f"127.0.0.1:{p2}", f"127.0.0.1:{p3}"], topology_id="cluster_topo_v1")

        srv1.start()
        srv2.start()
        srv3.start()
        try:
            peers_arg = f"127.0.0.1:{p1},127.0.0.1:{p2},127.0.0.1:{p3}"
            res = subprocess.run([str(VALIDATOR_SCRIPT), peers_arg], capture_output=True, text=True)
            clean_out = strip_ansi(res.stdout)
            assert "MISMATCH DETECTED: Stale Raft metadata present across nodes" in clean_out
        finally:
            srv1.stop()
            srv2.stop()
            srv3.stop()


# ==============================================================================
# 3. MULTI-MASTER FAILOVER & DYNAMIC LEADER TRANSITION SIMULATION
# ==============================================================================

class TestMultiMasterFailoverDynamics:
    """Stress tests dynamic failover when the active Raft leader drops offline."""

    def test_dynamic_leader_failover_recovery(self):
        """Simulate dynamic leader step-down: Master 1 dies, Master 2 elected as new leader."""
        p1 = find_free_port()
        p2 = find_free_port()
        p3 = find_free_port()

        # Step 1: Initial state: Master 1 is Leader
        srv1 = EphemeralPeerServer(p1, is_leader=True, reported_leader=f"127.0.0.1:{p1}", peers=[f"127.0.0.1:{p1}", f"127.0.0.1:{p2}", f"127.0.0.1:{p3}"])
        srv2 = EphemeralPeerServer(p2, is_leader=False, reported_leader=f"127.0.0.1:{p1}", peers=[f"127.0.0.1:{p1}", f"127.0.0.1:{p2}", f"127.0.0.1:{p3}"])
        srv3 = EphemeralPeerServer(p3, is_leader=False, reported_leader=f"127.0.0.1:{p1}", peers=[f"127.0.0.1:{p1}", f"127.0.0.1:{p2}", f"127.0.0.1:{p3}"])

        srv1.start()
        srv2.start()
        srv3.start()
        try:
            peers_arg = f"127.0.0.1:{p1},127.0.0.1:{p2},127.0.0.1:{p3}"
            res_init = subprocess.run([str(VALIDATOR_SCRIPT), peers_arg], capture_output=True, text=True)
            assert res_init.returncode == 0
            clean_init = strip_ansi(res_init.stdout)
            assert f"Consensus Leader:              127.0.0.1:{p1}" in clean_init

            # Step 2: Master 1 crashes (simulating hardware / network failure)
            srv1.stop()

            # Master 2 & 3 elect Master 2 as new Leader
            srv2.stop()
            srv3.stop()
            srv2_new = EphemeralPeerServer(p2, is_leader=True, reported_leader=f"127.0.0.1:{p2}", peers=[f"127.0.0.1:{p2}", f"127.0.0.1:{p3}"])
            srv3_new = EphemeralPeerServer(p3, is_leader=False, reported_leader=f"127.0.0.1:{p2}", peers=[f"127.0.0.1:{p2}", f"127.0.0.1:{p3}"])
            srv2_new.start()
            srv3_new.start()
            try:
                # Step 3: Run validator against remaining peers
                res_failover = subprocess.run([str(VALIDATOR_SCRIPT), peers_arg], capture_output=True, text=True)
                assert res_failover.returncode == 0, f"Expected 0 during 2/3 failover quorum, got {res_failover.returncode}"
                clean_failover = strip_ansi(res_failover.stdout)
                assert "Online Master Nodes:           2 / 3" in clean_failover
                assert "QUORUM HEALTHY (2 >= 2)" in clean_failover
                assert f"Consensus Leader:              127.0.0.1:{p2}" in clean_failover
                assert "File ID Allocation (/dir/assign): SUCCESS" in clean_failover
            finally:
                srv2_new.stop()
                srv3_new.stop()
        finally:
            try:
                srv1.stop()
                srv2.stop()
                srv3.stop()
            except Exception:
                pass


if __name__ == "__main__":
    pytest.main(["-v", __file__])
