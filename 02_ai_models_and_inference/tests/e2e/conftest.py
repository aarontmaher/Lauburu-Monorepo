#!/usr/bin/env python3
"""
E2E Test Configuration & Shared Fixtures
=========================================
Provides reusable test fixtures, mock/live dual test harnesses, synthetic network
topology generators, and protocol validation helpers for the Lauburu AI Mesh E2E test suite.
"""

import os
import sys
import time
import zlib
import struct
import pytest
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field

# Ensure 02_ai_models_and_inference and 06_scripts_and_tooling are in sys.path
TEST_DIR = Path(__file__).resolve().parent
MODULE_ROOT = TEST_DIR.parents[1]
MONOREPO_ROOT = MODULE_ROOT.parent

if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))
if str(MONOREPO_ROOT) not in sys.path:
    sys.path.insert(0, str(MONOREPO_ROOT))

from sharding_daemon.config import (
    CLUSTER_NODES,
    MODEL_CATALOG,
    TransportTier as ConfigTransportTier,
    TRANSPORT_TIER_PROFILES,
    NodeSpec,
    ModelCatalogEntry,
    get_cluster_total_usable_vram,
    get_cluster_total_physical_ram,
    get_node_spec,
    get_model_catalog,
    validate_cluster_vram_headroom,
)
from sharding_daemon.network_awareness import (
    LinkMetrics,
    TransportTier,
    NetworkInterface,
    PeerStatus,
    MeshTelemetrySnapshot,
    TIER_BASE_MULTIPLIERS,
    compute_routing_cost,
    get_live_peer_metrics,
    discover_local_interfaces,
    query_tailscale_status,
    probe_socket_tcp,
    probe_ping_empirical,
    probe_peer_empirical,
)


# ─── Multipath Framing Constants (Matches tensor_multipath_router.py) ─────────
HEADER_FORMAT = "!4sIQIIIII"
HEADER_MAGIC = b"LAUB"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 36 bytes


@dataclass
class MultipathChunk:
    magic: bytes
    stream_id: int
    total_size: int
    total_chunks: int
    chunk_index: int
    payload_len: int
    chunk_crc32: int
    total_crc32: int
    payload: bytes

    def pack(self) -> bytes:
        header = struct.pack(
            HEADER_FORMAT,
            self.magic,
            self.stream_id,
            self.total_size,
            self.total_chunks,
            self.chunk_index,
            self.payload_len,
            self.chunk_crc32,
            self.total_crc32,
        )
        return header + self.payload

    @classmethod
    def unpack(cls, data: bytes) -> "MultipathChunk":
        if len(data) < HEADER_SIZE:
            raise ValueError(f"Data length {len(data)} is less than header size {HEADER_SIZE}")
        magic, stream_id, total_size, total_chunks, chunk_index, payload_len, chunk_crc32, total_crc32 = struct.unpack(
            HEADER_FORMAT, data[:HEADER_SIZE]
        )
        payload = data[HEADER_SIZE:HEADER_SIZE + payload_len]
        return cls(
            magic=magic,
            stream_id=stream_id,
            total_size=total_size,
            total_chunks=total_chunks,
            chunk_index=chunk_index,
            payload_len=payload_len,
            chunk_crc32=chunk_crc32,
            total_crc32=total_crc32,
            payload=payload,
        )


# ─── Mock/Live DHT Ring Routing Harness ───────────────────────────────────────
class MockDHTRing:
    """
    Self-contained Kademlia DHT Ring simulator with UNAL hooks and Dijkstra DP routing.
    Used for opaque-box test verification of sharding and failover logic.
    """
    def __init__(self, cluster_nodes: Optional[Dict[str, NodeSpec]] = None):
        self.nodes: Dict[str, NodeSpec] = cluster_nodes or dict(CLUSTER_NODES)
        self.routing_table: Dict[str, Dict[int, Dict[str, Any]]] = {}  # model_id -> block_idx -> ServerInfo
        self.link_metrics: Dict[Tuple[str, str], LinkMetrics] = {}
        self.draining_nodes: set = set()
        self._init_default_link_metrics()

    def _init_default_link_metrics(self):
        for s_id, s_node in self.nodes.items():
            for d_id, d_node in self.nodes.items():
                if s_id == d_id:
                    self.link_metrics[(s_id, d_id)] = LinkMetrics(
                        peer_id=d_id,
                        tailscale_ip=d_node.tailscale_ip,
                        is_direct=True,
                        rtt_ms=0.01,
                        bandwidth_mbps=40000.0,
                        packet_loss=0.0,
                        transport_tier=TransportTier.LOCAL_LOOPBACK.value,
                    )
                elif s_id in ("mac_host", "macbook_pro") and d_id in ("mac_host", "macbook_pro"):
                    self.link_metrics[(s_id, d_id)] = LinkMetrics(
                        peer_id=d_id,
                        tailscale_ip=d_node.tailscale_ip,
                        is_direct=True,
                        rtt_ms=0.27,
                        bandwidth_mbps=10000.0,
                        packet_loss=0.0,
                        transport_tier=TransportTier.TB4_DMA.value,
                    )
                elif "linux" in s_id or "linux" in d_id:
                    self.link_metrics[(s_id, d_id)] = LinkMetrics(
                        peer_id=d_id,
                        tailscale_ip=d_node.tailscale_ip,
                        is_direct=True,
                        rtt_ms=0.90,
                        bandwidth_mbps=1000.0,
                        packet_loss=0.0,
                        transport_tier=TransportTier.LAN_1GBE.value,
                    )
                elif s_node.is_mobile or d_node.is_mobile:
                    self.link_metrics[(s_id, d_id)] = LinkMetrics(
                        peer_id=d_id,
                        tailscale_ip=d_node.tailscale_ip,
                        is_direct=True,
                        rtt_ms=8.0,
                        bandwidth_mbps=300.0,
                        packet_loss=0.0,
                        transport_tier=TransportTier.TAILSCALE_DIRECT.value,
                    )
                else:
                    self.link_metrics[(s_id, d_id)] = LinkMetrics(
                        peer_id=d_id,
                        tailscale_ip=d_node.tailscale_ip,
                        is_direct=True,
                        rtt_ms=15.0,
                        bandwidth_mbps=500.0,
                        packet_loss=0.0,
                        transport_tier=TransportTier.TAILSCALE_DIRECT.value,
                    )

    def announce_blocks(self, node_id: str, model_id: str, start_block: int, end_block: int, throughput: float = 100.0):
        if model_id not in self.routing_table:
            self.routing_table[model_id] = {}
        for b_idx in range(start_block, end_block):
            if b_idx not in self.routing_table[model_id]:
                self.routing_table[model_id][b_idx] = {}
            self.routing_table[model_id][b_idx][node_id] = {
                "node_id": node_id,
                "throughput": throughput,
                "announced_at": time.time(),
                "ttl": 30.0,
            }

    def set_node_draining(self, node_id: str, draining: bool = True):
        if draining:
            self.draining_nodes.add(node_id)
        else:
            self.draining_nodes.discard(node_id)

    def set_link_degraded(self, src_id: str, dst_id: str, tier: str, rtt_ms: float, loss: float = 0.0, bandwidth_mbps: Optional[float] = None):
        if (src_id, dst_id) in self.link_metrics:
            old = self.link_metrics[(src_id, dst_id)]
            if bandwidth_mbps is not None:
                bw = bandwidth_mbps
            elif tier == TransportTier.TB4_DMA.value:
                bw = 10000.0
            elif tier == TransportTier.LAN_1GBE.value:
                bw = 1000.0
            elif tier == TransportTier.WIFI7_MLO.value:
                bw = 2400.0
            elif tier == TransportTier.MULTIPATH_BOND.value:
                bw = 3400.0
            elif tier == TransportTier.DERP_RELAY.value:
                bw = 20.0
            else:
                bw = 500.0
            self.link_metrics[(src_id, dst_id)] = LinkMetrics(
                peer_id=old.peer_id,
                tailscale_ip=old.tailscale_ip,
                is_direct=(tier != TransportTier.DERP_RELAY.value),
                rtt_ms=rtt_ms,
                bandwidth_mbps=bw,
                packet_loss=loss,
                transport_tier=tier,
            )

    def compute_edge_cost(self, src: str, dst: str, tensor_size_bytes: int = 1048576) -> float:
        if dst in self.draining_nodes:
            return float("inf")
        metric = self.link_metrics.get((src, dst))
        if not metric:
            return float("inf")
        if metric.transport_tier == TransportTier.UNREACHABLE.value:
            return float("inf")
        
        # Base latency + transmission time
        comm_time_ms = metric.rtt_ms + (tensor_size_bytes * 8.0) / (metric.bandwidth_mbps * 1e6) * 1000.0
        multiplier = TIER_BASE_MULTIPLIERS.get(metric.transport_tier, 1.0)
        
        # Health penalty
        loss_penalty = (metric.packet_loss / max(0.001, (1.0 - metric.packet_loss))) * 200.0 if metric.packet_loss < 1.0 else 10000.0
        derp_penalty = 1000.0 if metric.transport_tier == TransportTier.DERP_RELAY.value else 0.0
        
        return (comm_time_ms * multiplier) + loss_penalty + derp_penalty

    def find_optimal_sharding_route(self, model_id: str, total_blocks: int, tensor_size_bytes: int = 1048576) -> List[Tuple[int, str, float]]:
        """
        Computes dynamic programming shortest path over available block providers.
        Returns: List of (block_index, assigned_node_id, cumulative_cost)
        """
        if model_id not in self.routing_table:
            raise KeyError(f"Model {model_id} not announced in DHT")

        # Check coverage
        for b in range(total_blocks):
            active_providers = [nid for nid in self.routing_table[model_id].get(b, {}) if nid not in self.draining_nodes]
            if not active_providers:
                raise RuntimeError(f"No active provider for block {b} of {model_id}")

        # Dynamic programming over blocks
        # dp[b][node] = min cost to reach block b hosted at node
        dp: Dict[int, Dict[str, float]] = {}
        prev: Dict[int, Dict[str, Optional[str]]] = {}

        # Base case: block 0
        dp[0] = {}
        prev[0] = {}
        for nid in self.routing_table[model_id][0]:
            if nid not in self.draining_nodes:
                dp[0][nid] = self.compute_edge_cost("mac_host", nid, tensor_size_bytes)
                prev[0][nid] = None

        # Inductive step
        for b in range(1, total_blocks):
            dp[b] = {}
            prev[b] = {}
            for curr_node in self.routing_table[model_id].get(b, {}):
                if curr_node in self.draining_nodes:
                    continue
                min_cost = float("inf")
                best_prev = None
                for prev_node, prev_cost in dp[b - 1].items():
                    step_cost = self.compute_edge_cost(prev_node, curr_node, tensor_size_bytes)
                    total_c = prev_cost + step_cost
                    if total_c < min_cost:
                        min_cost = total_c
                        best_prev = prev_node
                if best_prev is not None:
                    dp[b][curr_node] = min_cost
                    prev[b][curr_node] = best_prev

        # Find best end node
        if not dp[total_blocks - 1]:
            raise RuntimeError("No viable path through block sequence")

        best_last_node = min(dp[total_blocks - 1].keys(), key=lambda n: dp[total_blocks - 1][n])
        
        # Backtrack
        route: List[Tuple[int, str, float]] = []
        curr = best_last_node
        for b in range(total_blocks - 1, -1, -1):
            route.append((b, curr, dp[b][curr]))
            curr = prev[b][curr]
        
        route.reverse()
        return route


# ─── Pytest Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def cluster_matrix() -> Dict[str, NodeSpec]:
    """Returns the canonical 8-node cluster matrix."""
    return dict(CLUSTER_NODES)


@pytest.fixture
def model_matrix() -> Dict[str, ModelCatalogEntry]:
    """Returns the canonical model catalog."""
    return dict(MODEL_CATALOG)


@pytest.fixture
def dht_ring(cluster_matrix) -> MockDHTRing:
    """Returns an initialized mock DHT ring coordinator."""
    return MockDHTRing(cluster_matrix)


@pytest.fixture
def multipath_helper():
    """Returns helper function to create framed multipath chunks."""
    def _create_chunks(payload: bytes, stream_id: int = 1, chunk_size: int = 64 * 1024) -> List[MultipathChunk]:
        total_size = len(payload)
        total_crc32 = zlib.crc32(payload) & 0xFFFFFFFF
        total_chunks = (total_size + chunk_size - 1) // chunk_size if total_size > 0 else 1
        chunks = []
        for i in range(total_chunks):
            start = i * chunk_size
            end = min(start + chunk_size, total_size)
            chunk_data = payload[start:end]
            chunk_crc32 = zlib.crc32(chunk_data) & 0xFFFFFFFF
            chunks.append(
                MultipathChunk(
                    magic=HEADER_MAGIC,
                    stream_id=stream_id,
                    total_size=total_size,
                    total_chunks=total_chunks,
                    chunk_index=i,
                    payload_len=len(chunk_data),
                    chunk_crc32=chunk_crc32,
                    total_crc32=total_crc32,
                    payload=chunk_data,
                )
            )
        return chunks
    return _create_chunks
