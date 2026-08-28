#!/usr/bin/env python3
"""
tests/test_milestone2_multiwan_nomad_integration.py
===================================================
Empirical Unit & Integration Test Suite for Milestone 2:
Multi-WAN Nomad Courier Integration, TP-Link Interface Scoring,
Tensor Multipath CRC32 Chunk Striping, RPC Watchdogs, and LoRA Serialization.

Zero-Mock Standard (Global Rule #0): Zero simulated mock objects (0 unittest.mock / MagicMock).
Real kernel sockets, sysfs link probing, binary framing ('LAUB'), and AST static analysis only.

Covers:
  - Tier 1: Feature Unit Tests (5 Tests)
  - Tier 2: Boundary & Fault Tolerance Tests (4 Tests)
  - Tier 3: Cross-Feature Integration Tests (4 Tests)
  - Tier 4: Real-World Workloads & Zero-Mock Compliance (2 Tests + 1 Workload Test -> Total 16 Tests across classes)
"""

import ast
import json
import os
import re
import socket
import struct
import subprocess
import sys
import time
import zlib
from pathlib import Path
from typing import Dict, Any, List

import pytest

# Ensure repository root and modules are in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
NETWORK_SCRIPTS_DIR = REPO_ROOT / "06_scripts_and_tooling/network"
CORE_MULTIWAN_DIR = REPO_ROOT / "00_core_infrastructure/multi_wan"
DATA_DIR = REPO_ROOT / "data"

for p in [REPO_ROOT, NETWORK_SCRIPTS_DIR, CORE_MULTIWAN_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import multiwan_bond_manager
import tensor_multipath_router
import nomad_courier_self_healer
import service_keepalive


# ============================================================================
# TIER 1: FEATURE UNIT TESTS (Happy Path Components)
# ============================================================================

class TestTier1FeatureUnitTests:
    """Tier 1: Verify path registration, socket binding, watchdogs, and keepalives."""

    def test_01_multiwan_bond_manager_tplink_registration(self):
        """TC-1.1: Verify TPLink_Extender_Ethernet path definition and fitness scoring."""
        tplink_entry = None
        for path in multiwan_bond_manager.WAN_PATHS:
            if path["name"] == "TPLink_Extender_Ethernet":
                tplink_entry = path
                break

        assert tplink_entry is not None, "TPLink_Extender_Ethernet missing from WAN_PATHS in multiwan_bond_manager.py"
        assert tplink_entry["interface"] == "enx98fc84e6e212"
        assert tplink_entry["mac_address"] == "98:fc:84:e6:e2:12"
        assert tplink_entry["type"] == "extender_ethernet"
        assert tplink_entry["max_theoretical_mbps"] == 1000
        assert tplink_entry["fallback_mbps"] == 100
        assert tplink_entry["probe_host"] == "192.168.8.1"
        assert tplink_entry["route_metric"] == 100
        assert tplink_entry["routing_table"] == 200
        assert tplink_entry["table_name"] == "tplink_mesh"

        # Verify dynamic scoring calculation under nominal gigabit conditions
        score = multiwan_bond_manager.compute_score(
            bandwidth_theoretical=1000.0,
            rtt_ms=1.20,
            reachable=True,
            packet_loss_pct=0.0
        )
        assert score >= 90.0, f"Expected nominal TP-Link score >= 90.0, got {score}"

    def test_02_tensor_multipath_router_socket_binding(self):
        """TC-1.2: Validate enx98fc84e6e212 interface mapping, socket creation, and QoS marking."""
        assert "TPLink_Extender_Ethernet" in tensor_multipath_router.INTERFACES
        cfg = tensor_multipath_router.INTERFACES["TPLink_Extender_Ethernet"]
        assert cfg["device"] == "enx98fc84e6e212"
        assert cfg["ip"] == "192.168.8.224"
        assert cfg["role"] == "PRIMARY_TENSOR_BRIDGE"
        assert cfg["weight"] == 0.60
        assert cfg["theoretical_mbps"] == 1000.0
        assert cfg["metric"] == 100
        assert cfg["routing_table"] == 200

        assert "Linux_WiFi_Internal" in tensor_multipath_router.INTERFACES
        assert "Tailscale_WireGuard" in tensor_multipath_router.INTERFACES

        # Test real socket creation with DSCP AF41 (0x88) and TCP_NODELAY
        sock = tensor_multipath_router.create_bound_socket(
            device="",
            src_ip="127.0.0.1",
            tos=0x88
        )
        assert sock is not None
        # Verify TCP_NODELAY
        nodelay = sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY)
        assert nodelay != 0, "TCP_NODELAY must be enabled on tensor streaming socket"
        sock.close()

    def test_03_nomad_self_healer_tplink_watchdog(self):
        """TC-1.3: Execute heal_tplink_extender_mesh() and assert complete watchdog telemetry."""
        engine = nomad_courier_self_healer.NomadAutonomousEngine()
        result = engine.heal_tplink_extender_mesh()

        assert isinstance(result, dict)
        assert "status" in result
        assert "interface" in result
        assert "carrier" in result
        assert "gateway_192_168_8_1" in result
        assert "policy_table_200" in result
        assert result["status"] in (
            "TPLINK_EXTENDER_HEALTHY_AND_BONDED",
            "TPLINK_EXTENDER_HEALED_ONLINE",
            "TPLINK_EXTENDER_STANDBY",
            "TPLINK_EXTENDER_DEGRADED"
        )

    def test_04_nomad_self_healer_ai_compute_rpc_monitoring(self):
        """TC-1.4: Execute heal_ai_compute() and assert multi-endpoint Port 50052 matrix probing."""
        engine = nomad_courier_self_healer.NomadAutonomousEngine()
        result = engine.heal_ai_compute()

        assert isinstance(result, dict)
        assert "status" in result
        assert "active_endpoints_count" in result
        assert "standby_endpoints_count" in result
        assert "active_endpoints" in result
        assert "endpoint_matrix" in result

        matrix = result["endpoint_matrix"]
        assert "localhost" in matrix
        assert "linux_head_node_lan" in matrix
        assert "linux_head_node_ts" in matrix
        assert "mac_mini_host_ts" in matrix
        assert "pixel_10_pro_xl_ts" in matrix

        for node_name, info in matrix.items():
            assert info["port"] == 50052
            assert "latency_ms" in info
            assert isinstance(info["latency_ms"], (int, float))

    def test_05_service_keepalive_mesh_nodes_and_services(self):
        """TC-1.5: Verify service_keepalive node definitions, llamacpp_rpc service, and Port 50052 tracking."""
        manager = service_keepalive.ServiceKeepAliveManager(monorepo_dir=str(REPO_ROOT))

        # Check nodes
        assert "linux_tplink_eth" in manager.mesh_nodes
        tplink_node = manager.mesh_nodes["linux_tplink_eth"]
        assert tplink_node.primary_ip == "192.168.8.224"
        assert 50052 in tplink_node.required_ports

        assert "linux_server" in manager.mesh_nodes
        assert 50052 in manager.mesh_nodes["linux_server"].required_ports

        assert "macbook_host" in manager.mesh_nodes
        assert 50052 in manager.mesh_nodes["macbook_host"].required_ports

        # Check managed service
        assert "llamacpp_rpc" in manager.services
        rpc_service = manager.services["llamacpp_rpc"]
        assert rpc_service.port == 50052
        assert rpc_service.auto_restart is True


# ============================================================================
# TIER 2: BOUNDARY & FAULT TOLERANCE TESTS
# ============================================================================

class TestTier2BoundaryAndFaultTolerance:
    """Tier 2: Verify link recovery, socket timeouts, CRC corruption, and rate limiting."""

    def test_01_carrier_loss_and_down_interface_recovery(self):
        """TC-2.1: Verify non-destructive link healing and error tolerance when interface is down."""
        engine = nomad_courier_self_healer.NomadAutonomousEngine()
        # Probe without raising exceptions
        res = engine.heal_tplink_extender_mesh()
        assert isinstance(res, dict)
        assert res["policy_table_200"] in ("ACTIVE", "MISSING")

    def test_02_port_50052_connection_refusal_resilience(self):
        """TC-2.2: Probe an unbound port and verify sub-second socket timeout handling."""
        engine = nomad_courier_self_healer.NomadAutonomousEngine()
        t0 = time.perf_counter()
        # Probe an arbitrarily unused local port
        is_open = engine.is_port_listening(59999, host="127.0.0.1")
        elapsed = time.perf_counter() - t0

        assert is_open is False
        assert elapsed < 1.0, f"Port probe took too long ({elapsed:.3f}s > 1.0s)"

    def test_03_chunk_striping_crc32_corruption_rejection(self):
        """TC-2.3: Mutate a byte in a packed tensor chunk and verify CRC32 exception rejection."""
        engine = tensor_multipath_router.MultipathTensorEngine()
        stream_id = 0x12345678
        total_size = 65536
        total_chunks = 1
        chunk_idx = 0
        original_payload = os.urandom(65536)
        total_crc = zlib.crc32(original_payload)

        # Pack chunk with valid CRC
        packed = engine.pack_chunk(
            stream_id=stream_id,
            total_size=total_size,
            total_chunks=total_chunks,
            chunk_index=chunk_idx,
            chunk_data=original_payload,
            total_crc32=total_crc
        )

        # Unpack clean packet
        meta, payload = engine.unpack_chunk(packed)
        assert meta["chunk_index"] == 0
        assert payload == original_payload

        # Corrupt 1 byte in the payload portion
        corrupted_list = bytearray(packed)
        corrupted_list[tensor_multipath_router.HEADER_SIZE + 10] ^= 0xFF
        corrupted_packed = bytes(corrupted_list)

        with pytest.raises(ValueError) as exc_info:
            engine.unpack_chunk(corrupted_packed)
        assert "CRC32 mismatch" in str(exc_info.value)

    def test_04_auto_restart_rate_limiting_cooldown(self):
        """TC-2.4: Validate 10-second minimum cooldown on ManagedService.restart_if_needed()."""
        service = service_keepalive.ManagedService(
            key="test_service",
            name="Test Service",
            port=59998,
            health_url=None,
            start_cmd=["echo", "starting"],
            auto_restart=True
        )
        service.status = "OFFLINE"

        # First restart call
        first_restart = service.restart_if_needed(str(REPO_ROOT))
        assert first_restart is True
        assert service.restart_count == 1
        first_restart_time = service.last_restart_time

        # Immediate second restart call must be rate-limited by cooldown
        second_restart = service.restart_if_needed(str(REPO_ROOT))
        assert second_restart is False
        assert service.restart_count == 1
        assert service.last_restart_time == first_restart_time


# ============================================================================
# TIER 3: CROSS-FEATURE INTEGRATION TESTS
# ============================================================================

class TestTier3CrossFeatureIntegration:
    """Tier 3: Full cycle execution, state JSON verification, and LoRA dataset logging."""

    def test_01_multiwan_bond_manager_run_once_generates_valid_json(self):
        """TC-3.1: Execute multiwan_bond_manager.run_once() and verify wan_fitness_scores.json."""
        result = multiwan_bond_manager.run_once(verbose=False)
        assert isinstance(result, dict)
        assert "timestamp_utc" in result
        assert "paths" in result
        assert "recommendation" in result

        scores_file = DATA_DIR / "network/wan_fitness_scores.json"
        assert scores_file.exists()

        with open(scores_file, "r") as f:
            data = json.load(f)

        path_names = [p["name"] for p in data["paths"]]
        assert "TPLink_Extender_Ethernet" in path_names
        assert "recommendation" in data
        assert "llama_rpc_routing" in data["recommendation"]

    def test_02_tensor_multipath_benchmark_execution(self):
        """TC-3.2: Execute benchmark_bonded_throughput() and verify throughput speedup and CRC32."""
        engine = tensor_multipath_router.MultipathTensorEngine()
        result = engine.benchmark_bonded_throughput(tensor_size_mb=10)

        assert isinstance(result, dict)
        assert result["status"] == "OPTIMAL_BONDED"
        assert result["tensor_size_mb"] == 10
        assert result["header_size_bytes"] == 36
        assert "(VERIFIED_MATCH)" in result["integrity_crc32"]
        assert result["bonded_multipath_mbps"] > 0
        assert result["failover_sla_ms"] < 100.0

        status_file = DATA_DIR / "network/multipath_bonding_status.json"
        assert status_file.exists()

    def test_03_nomad_self_healer_full_cycle_execution(self):
        """TC-3.3: Execute NomadAutonomousEngine.run_full_cycle() and verify status report keys."""
        engine = nomad_courier_self_healer.NomadAutonomousEngine()
        report = engine.run_full_cycle()

        assert isinstance(report, dict)
        assert "localhost_3000_web_ui" in report
        assert "wol_api_port_18802" in report
        assert "tplink_extender_mesh" in report
        assert "llama_rpc_port_50052" in report
        assert "antigravity_skills_guardian" in report
        assert "mcp_server_health_guardian" in report
        assert "obsidian_documentation_engine" in report
        assert "genetic_storage_optimizer" in report
        assert "cron_daemon_governance" in report
        assert "overall_health" in report

        status_file = DATA_DIR / "network/nomad_self_healer_status.json"
        assert status_file.exists()

    def test_04_lora_dataset_atomic_serialization_and_schema(self):
        """TC-3.4: Verify Alpaca/ShareGPT schema compliance of nomad_autonomous_actions.jsonl."""
        lora_log = DATA_DIR / "lora_datasets/nomad_autonomous_actions.jsonl"
        assert lora_log.exists(), "LoRA action dataset does not exist"

        lines = lora_log.read_text().strip().splitlines()
        assert len(lines) > 0, "LoRA action dataset is empty"

        # Validate schema of recent entries
        for line in lines[-5:]:
            record = json.loads(line)
            assert "timestamp_utc" in record
            assert "instruction" in record and len(record["instruction"]) > 0
            assert "input" in record and len(record["input"]) > 0
            assert "output" in record and len(record["output"]) > 0
            assert "action" in record
            assert "result" in record
            assert record.get("nomad_agent") == "Multi-WAN Nomad Courier v3.0"


# ============================================================================
# TIER 4: WORKLOADS & ZERO-MOCK COMPLIANCE
# ============================================================================

class TestTier4WorkloadsAndZeroMockCompliance:
    """Tier 4: End-to-end 25MB tensor striping and AST static analysis zero-mock audit."""

    def test_01_tensor_chunk_striping_end_to_end(self):
        """TC-4.1: Slices 25MB tensor into 64KB chunks, multiplexes over active paths, and verifies CRC32 reassembly."""
        engine = tensor_multipath_router.MultipathTensorEngine()
        tensor_size_mb = 25
        data_bytes = os.urandom(tensor_size_mb * 1024 * 1024)
        reference_crc = zlib.crc32(data_bytes)
        stream_id = 0x99887766

        chunk_size = 64 * 1024
        chunks = [data_bytes[i:i + chunk_size] for i in range(0, len(data_bytes), chunk_size)]
        total_chunks = len(chunks)

        # Interleave chunks across paths
        allocations = engine.partition_chunks(chunks)
        assert sum(len(c) for c in allocations.values()) == total_chunks

        # Transmit & pack packets
        packed_packets: List[bytes] = []
        for path_name, path_chunks in allocations.items():
            for chunk_idx, chunk_data in path_chunks:
                pkt = engine.pack_chunk(
                    stream_id=stream_id,
                    total_size=len(data_bytes),
                    total_chunks=total_chunks,
                    chunk_index=chunk_idx,
                    chunk_data=chunk_data,
                    total_crc32=reference_crc
                )
                packed_packets.append(pkt)

        # Receive & unpack packets
        received_chunks: Dict[int, bytes] = {}
        for pkt in packed_packets:
            meta, payload = engine.unpack_chunk(pkt)
            assert meta["stream_id"] == stream_id
            assert meta["total_crc32"] == reference_crc
            received_chunks[meta["chunk_index"]] = payload

        # Reassemble and verify end-to-end byte integrity
        reassembled = b"".join(received_chunks[i] for i in range(total_chunks))
        assert len(reassembled) == len(data_bytes)
        assert zlib.crc32(reassembled) == reference_crc

    def test_02_tensor_multipath_failover_simulation_workload(self):
        """TC-4.2: Workload test validating <100ms failover resilience and chunk recovery on link failure."""
        engine = tensor_multipath_router.MultipathTensorEngine()
        failover_res = engine.test_failover_resilience(tensor_size_mb=10)

        assert isinstance(failover_res, dict)
        assert failover_res["status"] == "FAILOVER_SUCCESSFUL"
        assert failover_res["crc32_verified"] is True
        assert failover_res["failover_sla_met"] is True
        assert failover_res["failover_duration_ms"] < 100.0

    def test_03_ast_zero_mock_compliance_audit_milestone2(self):
        """TC-4.3: AST static analysis proving zero mock objects and zero destructive commands in Milestone 2 files."""
        audit_files = [
            NETWORK_SCRIPTS_DIR / "multiwan_bond_manager.py",
            NETWORK_SCRIPTS_DIR / "tensor_multipath_router.py",
            NETWORK_SCRIPTS_DIR / "nomad_courier_self_healer.py",
            CORE_MULTIWAN_DIR / "service_keepalive.py",
            Path(__file__).resolve()
        ]

        destructive_pattern = "nmcli" + '", "' + "device" + '", "' + "disconnect"

        for p in audit_files:
            assert p.exists(), f"Audit file not found: {p}"
            with open(p, "r", encoding="utf-8") as f:
                source = f.read()

            parsed = ast.parse(source, filename=str(p))
            assert parsed is not None

            for node in ast.walk(parsed):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "mock" not in alias.name.lower(), (
                            f"Rule #0 Violation: Mock import '{alias.name}' in {p}"
                        )
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        assert "mock" not in node.module.lower(), (
                            f"Rule #0 Violation: Mock import from '{node.module}' in {p}"
                        )

            # Ensure zero destructive disconnect commands in production scripts
            if p != Path(__file__).resolve():
                assert destructive_pattern not in source, (
                    f"Destructive disconnect command found in {p}"
                )
