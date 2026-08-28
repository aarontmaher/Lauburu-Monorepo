#!/usr/bin/env python3
"""
02_ai_models_and_inference/sharding_daemon/dht_ring.py
======================================================
Network-Aware Dynamic Petals / Hivemind Kademlia DHT Ring & Multiaddr Engine.
-----------------------------------------------------------------------------
Implements decentralized Kademlia key-space management (<dht_prefix>.<model_id>.<block_idx>),
160-bit XOR metric distance topology, peer registration, block location announcements,
heartbeat lifecycle, TTL expiration cleanup, multi-homed P2P multiaddr representation,
transport tier multiaddr ranking, and graceful peer churn/drain handling.

Part of Milestone M3: Network-Aware Dynamic Petals DHT Ring & Routing Engine.
"""

from __future__ import annotations

import os
import sys
import time
import math
import hashlib
import logging
import threading
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set, Union

from pydantic import BaseModel, Field

# Add module root to sys.path if not present
MODULE_ROOT = Path(__file__).resolve().parents[1]
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from .config import (
    CLUSTER_NODES,
    DEFAULT_PORTS,
    TransportTier as ConfigTransportTier,
    TRANSPORT_TIER_PROFILES,
    NodeSpec,
    get_node_spec,
    get_model_catalog,
)
from .network_awareness import (
    TransportTier,
    LinkMetrics,
    TIER_BASE_MULTIPLIERS,
    get_live_peer_metrics,
    discover_local_interfaces,
)

logger = logging.getLogger("DHTRing")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Kademlia 160-bit Distance Metric & Key Management
# ═══════════════════════════════════════════════════════════════════════════════

KADEMLIA_KEY_BITS = 160
KADEMLIA_K_BUCKET_SIZE = 20
KADEMLIA_ALPHA = 3
DEFAULT_BLOCK_TTL_SEC = 30.0
DEFAULT_DHT_PREFIX = "lauburu-mesh-swarm"


def hash_dht_key(key_str: str) -> int:
    """
    Compute 160-bit SHA-1 hash integer for Kademlia DHT key-space.
    """
    digest = hashlib.sha1(key_str.encode("utf-8")).digest()
    return int.from_bytes(digest, byteorder="big")


def xor_distance(key1: Union[int, str], key2: Union[int, str]) -> int:
    """
    Compute Kademlia XOR metric distance: d(x, y) = x ^ y
    Accepts integer keys or raw key strings (which are automatically hashed).
    """
    k1 = hash_dht_key(key1) if isinstance(key1, str) else key1
    k2 = hash_dht_key(key2) if isinstance(key2, str) else key2
    return k1 ^ k2


def format_dht_block_key(model_id: str, block_idx: int, dht_prefix: str = DEFAULT_DHT_PREFIX) -> str:
    """
    Generate canonical Petals Kademlia key for a specific transformer block.
    Format: `<dht_prefix>.<model_id>.<block_idx>`
    Example: `lauburu-mesh-swarm.bloom-560m.0`
    """
    return f"{dht_prefix}.{model_id}.{block_idx}"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. P2P Multiaddr Representation & Ranking
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Multiaddr:
    """
    Structured representation of a libp2p multiaddr endpoint.
    Format: /<protocol>/<host>/<transport>/<port>[/p2p/<peer_id>]
    Examples:
      - /ip4/169.254.80.69/tcp/31330
      - /ip4/100.119.199.76/tcp/31330/p2p/12D3KooWJzV9...
    """
    host: str
    port: int
    protocol: str = "ip4"
    transport: str = "tcp"
    peer_id: Optional[str] = None
    inferred_tier: TransportTier = TransportTier.TAILSCALE_DIRECT

    def __post_init__(self):
        self.inferred_tier = self._infer_transport_tier(self.host)

    @classmethod
    def parse(cls, multiaddr_str: str) -> Multiaddr:
        """Parse a libp2p multiaddr string into a Multiaddr object."""
        m = multiaddr_str.strip()
        parts = [p for p in m.split("/") if p]
        
        protocol = "ip4"
        host = "127.0.0.1"
        transport = "tcp"
        port = 31330
        peer_id = None

        i = 0
        while i < len(parts):
            tag = parts[i]
            if tag in ("ip4", "ip6", "dns4", "dns6"):
                protocol = tag
                if i + 1 < len(parts):
                    host = parts[i + 1]
                    i += 2
                    continue
            elif tag in ("tcp", "udp"):
                transport = tag
                if i + 1 < len(parts):
                    try:
                        port = int(parts[i + 1])
                    except ValueError:
                        port = 31330
                    i += 2
                    continue
            elif tag == "p2p" or tag == "ipfs":
                if i + 1 < len(parts):
                    peer_id = parts[i + 1]
                    i += 2
                    continue
            i += 1

        return cls(host=host, port=port, protocol=protocol, transport=transport, peer_id=peer_id)

    @staticmethod
    def _infer_transport_tier(ip_or_host: str) -> TransportTier:
        """Infer physical/virtual interconnect tier from IP address."""
        if ip_or_host in ("127.0.0.1", "::1", "localhost"):
            return TransportTier.LOCAL_LOOPBACK
        if ip_or_host.startswith("169.254."):
            return TransportTier.TB4_DMA
        if ip_or_host.startswith("192.168.8.") or ip_or_host.startswith("10.0.0."):
            return TransportTier.LAN_1GBE
        if ip_or_host.startswith("100."):
            return TransportTier.TAILSCALE_DIRECT
        return TransportTier.TAILSCALE_DIRECT

    def to_string(self, include_peer_id: bool = True) -> str:
        base = f"/{self.protocol}/{self.host}/{self.transport}/{self.port}"
        if include_peer_id and self.peer_id:
            base += f"/p2p/{self.peer_id}"
        return base

    def __str__(self) -> str:
        return self.to_string()


def synthesize_node_multiaddrs(
    node_id: str,
    port: int = DEFAULT_PORTS["petals_dht_port"],
    peer_id: Optional[str] = None
) -> List[str]:
    """
    Generate prioritized multiaddrs for a known node based on CLUSTER_NODES and local interfaces.
    """
    multiaddrs: List[str] = []
    pid = peer_id or f"12D3KooW_{node_id}"

    # 1. Check if node is in CLUSTER_NODES
    node_spec = get_node_spec(node_id)
    if node_spec:
        # Check TB4 link
        if node_id in ("mac_host", "macbook_pro"):
            tb4_ip = "169.254.80.69" if node_id == "mac_host" else "169.254.187.138"
            multiaddrs.append(f"/ip4/{tb4_ip}/tcp/{port}/p2p/{pid}")

        # LAN / Local IP
        if node_spec.local_ip:
            multiaddrs.append(f"/ip4/{node_spec.local_ip}/tcp/{port}/p2p/{pid}")

        # Tailscale IP
        if node_spec.tailscale_ip:
            multiaddrs.append(f"/ip4/{node_spec.tailscale_ip}/tcp/{port}/p2p/{pid}")

    if not multiaddrs:
        multiaddrs.append(f"/ip4/127.0.0.1/tcp/{port}/p2p/{pid}")

    return multiaddrs


def rank_multiaddrs(multiaddr_list: List[str]) -> List[Tuple[str, TransportTier, float]]:
    """
    Rank advertised multiaddrs by Transport Tier priority and nominal latency.
    Returns sorted list of (multiaddr_str, transport_tier, priority_weight).
    """
    ranked = []
    tier_priorities = {
        TransportTier.LOCAL_LOOPBACK: (10.0, 0.01),
        TransportTier.TB4_DMA: (9.0, 0.27),
        TransportTier.LAN_1GBE: (7.0, 0.90),
        TransportTier.WIFI7_MLO: (6.0, 2.10),
        TransportTier.MULTIPATH_BOND: (5.0, 1.50),
        TransportTier.TAILSCALE_DIRECT: (4.0, 3.50),
        TransportTier.DERP_RELAY: (1.0, 35.0),
        TransportTier.UNREACHABLE: (0.0, 999.0),
    }

    for m_str in multiaddr_list:
        parsed = Multiaddr.parse(m_str)
        tier = parsed.inferred_tier
        weight, rtt = tier_priorities.get(tier, (3.0, 10.0))
        ranked.append((m_str, tier, weight))

    # Sort descending by priority weight, then ascending by nominal RTT
    ranked.sort(key=lambda x: (-x[2], x[1].value))
    return ranked


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Peer States & ServerInfo Data Schema
# ═══════════════════════════════════════════════════════════════════════════════

class PeerLifecycleState(str, Enum):
    ACTIVE = "ACTIVE"
    JOINING = "JOINING"
    DEGRADED = "DEGRADED"
    DRAINING = "DRAINING"
    OFFLINE = "OFFLINE"
    QUARANTINED = "QUARANTINED"


class ServerInfo(BaseModel):
    """
    Full metadata schema for a Petals DHT block provider entry.
    Published to key `<dht_prefix>.<model_id>.<block_idx>` for each served transformer layer.
    """
    peer_id: str
    node_id: str
    model_id: str
    start_block: int
    end_block: int
    throughput: float = 100.0                  # Estimated forward tokens/sec
    inference_rps: float = 15.0                # Requests/sec for step decoding
    torch_dtype: str = "float32"
    adapters: List[str] = Field(default_factory=list)
    version: str = "1.1.0"
    state: PeerLifecycleState = PeerLifecycleState.ACTIVE
    announced_at: float = Field(default_factory=time.time)
    expiration_time: float = Field(default_factory=lambda: time.time() + DEFAULT_BLOCK_TTL_SEC)
    ttl_sec: float = DEFAULT_BLOCK_TTL_SEC
    advertised_multiaddrs: List[str] = Field(default_factory=list)
    hardware_specs: Dict[str, Any] = Field(default_factory=dict)
    network_telemetry: Dict[str, Any] = Field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expiration_time

    @property
    def is_active(self) -> bool:
        return (self.state == PeerLifecycleState.ACTIVE) and (not self.is_expired)

    def refresh_ttl(self, ttl_sec: Optional[float] = None):
        ttl = ttl_sec or self.ttl_sec
        self.announced_at = time.time()
        self.expiration_time = self.announced_at + ttl


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Kademlia k-Bucket & Routing Table
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class KBucketEntry:
    peer_id: str
    node_id: str
    key_int: int
    multiaddrs: List[str]
    last_seen: float = field(default_factory=time.time)
    state: PeerLifecycleState = PeerLifecycleState.ACTIVE
    consecutive_failures: int = 0
    quarantine_until: float = 0.0


class KBucket:
    """
    Single Kademlia k-bucket containing up to k=20 nodes, sorted by last_seen (LRU).
    """
    def __init__(self, k_size: int = KADEMLIA_K_BUCKET_SIZE):
        self.k_size = k_size
        self.entries: List[KBucketEntry] = []
        self._lock = threading.RLock()

    def insert_or_update(self, entry: KBucketEntry) -> bool:
        with self._lock:
            # Check if peer already exists
            for idx, existing in enumerate(self.entries):
                if existing.peer_id == entry.peer_id or existing.node_id == entry.node_id:
                    # Move to tail (most recently seen)
                    existing.last_seen = time.time()
                    existing.state = entry.state
                    existing.multiaddrs = entry.multiaddrs
                    existing.consecutive_failures = entry.consecutive_failures
                    existing.quarantine_until = entry.quarantine_until
                    self.entries.append(self.entries.pop(idx))
                    return True

            if len(self.entries) < self.k_size:
                self.entries.append(entry)
                return True

            # Bucket is full; check if oldest entry is stale/unreachable
            oldest = self.entries[0]
            if oldest.state in (PeerLifecycleState.OFFLINE, PeerLifecycleState.QUARANTINED) or (time.time() - oldest.last_seen > 120.0):
                self.entries.pop(0)
                self.entries.append(entry)
                return True

            return False

    def remove(self, peer_id: str) -> bool:
        with self._lock:
            for idx, e in enumerate(self.entries):
                if e.peer_id == peer_id or e.node_id == peer_id:
                    self.entries.pop(idx)
                    return True
            return False

    def get_entries(self) -> List[KBucketEntry]:
        with self._lock:
            return list(self.entries)


class KademliaRoutingTable:
    """
    Standard 160-bit Kademlia binary routing table partitioned into k-buckets.
    """
    def __init__(self, local_key_int: int, k_size: int = KADEMLIA_K_BUCKET_SIZE):
        self.local_key_int = local_key_int
        self.k_size = k_size
        self.buckets: List[KBucket] = [KBucket(k_size=k_size) for _ in range(KADEMLIA_KEY_BITS)]
        self._lock = threading.RLock()

    def _get_bucket_index(self, key_int: int) -> int:
        dist = self.local_key_int ^ key_int
        if dist == 0:
            return 0
        # Index based on highest bit difference
        return min(KADEMLIA_KEY_BITS - 1, dist.bit_length() - 1)

    def insert(self, peer_id: str, node_id: str, multiaddrs: List[str]) -> bool:
        key_int = hash_dht_key(peer_id)
        entry = KBucketEntry(
            peer_id=peer_id,
            node_id=node_id,
            key_int=key_int,
            multiaddrs=multiaddrs,
            last_seen=time.time(),
            state=PeerLifecycleState.ACTIVE
        )
        b_idx = self._get_bucket_index(key_int)
        with self._lock:
            return self.buckets[b_idx].insert_or_update(entry)

    def find_closest_nodes(self, target_key: Union[int, str], count: int = KADEMLIA_K_BUCKET_SIZE) -> List[KBucketEntry]:
        target_int = hash_dht_key(target_key) if isinstance(target_key, str) else target_key
        all_entries: List[KBucketEntry] = []
        with self._lock:
            for b in self.buckets:
                all_entries.extend(b.get_entries())

        # Sort by XOR distance to target
        all_entries.sort(key=lambda e: e.key_int ^ target_int)
        return all_entries[:count]

    def remove(self, peer_id: str):
        with self._lock:
            for b in self.buckets:
                if b.remove(peer_id):
                    break


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Thread-Safe DHT Storage Engine & Ring Coordinator
# ═══════════════════════════════════════════════════════════════════════════════

class DHTRingCoordinator:
    """
    Master Petals / Hivemind Kademlia DHT Ring Coordinator.
    Governs distributed model block discovery, multiaddr endpoints, TTL management,
    peer churn, node draining, and UNAL integration.
    """
    def __init__(
        self,
        local_node_id: str = "mac_host",
        dht_prefix: str = DEFAULT_DHT_PREFIX,
        dht_port: int = DEFAULT_PORTS["petals_dht_port"],
        bootstrap_peers: Optional[List[str]] = None,
    ):
        self.local_node_id = local_node_id
        self.dht_prefix = dht_prefix
        self.dht_port = dht_port
        self.local_peer_id = f"12D3KooW_{local_node_id}_{int(time.time())}"
        self.local_key_int = hash_dht_key(self.local_peer_id)

        self.routing_table = KademliaRoutingTable(self.local_key_int)
        
        # In-memory DHT Key-Value Store:
        # key_str -> Dict[node_id, ServerInfo]
        self._store: Dict[str, Dict[str, ServerInfo]] = {}
        
        # Peer metadata registry: node_id -> ServerInfo (local/remote)
        self._peer_registry: Dict[str, ServerInfo] = {}
        
        # Draining / Quarantined nodes
        self._draining_nodes: Set[str] = set()
        self._quarantined_nodes: Dict[str, float] = {} # node_id -> quarantine_expiry
        
        self.bootstrap_peers = bootstrap_peers or [
            "100.119.199.76:31330",
            "100.101.39.98:31330",
        ]
        
        self._lock = threading.RLock()
        self._governor_running = False
        self._governor_thread: Optional[threading.Thread] = None

        # Pre-seed routing table with known cluster nodes
        self._init_cluster_topology()

    def _init_cluster_topology(self):
        """Register known hardware cluster nodes into routing table and peer registry."""
        for n_id, spec in CLUSTER_NODES.items():
            maddrs = synthesize_node_multiaddrs(n_id, self.dht_port)
            pid = f"12D3KooW_{n_id}"
            self.routing_table.insert(pid, n_id, maddrs)

    # ─── Block Announcement & Storage ─────────────────────────────────────────

    def announce_blocks(
        self,
        node_id: str,
        model_id: str,
        start_block: int,
        end_block: int,
        throughput: float = 100.0,
        inference_rps: float = 15.0,
        torch_dtype: str = "float32",
        adapters: Optional[List[str]] = None,
        advertised_multiaddrs: Optional[List[str]] = None,
        ttl_sec: float = DEFAULT_BLOCK_TTL_SEC,
        hardware_specs: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Announce that node_id serves transformer blocks [start_block..end_block) of model_id.
        Stores ServerInfo at all block keys in the DHT key-space.
        Returns list of published DHT key strings.
        """
        with self._lock:
            pid = f"12D3KooW_{node_id}"
            maddrs = advertised_multiaddrs or synthesize_node_multiaddrs(node_id, self.dht_port)

            info = ServerInfo(
                peer_id=pid,
                node_id=node_id,
                model_id=model_id,
                start_block=start_block,
                end_block=end_block,
                throughput=throughput,
                inference_rps=inference_rps,
                torch_dtype=torch_dtype,
                adapters=adapters or [],
                state=PeerLifecycleState.ACTIVE if node_id not in self._draining_nodes else PeerLifecycleState.DRAINING,
                announced_at=time.time(),
                expiration_time=time.time() + ttl_sec,
                ttl_sec=ttl_sec,
                advertised_multiaddrs=maddrs,
                hardware_specs=hardware_specs or {},
            )

            self._peer_registry[node_id] = info
            self.routing_table.insert(pid, node_id, maddrs)

            published_keys: List[str] = []
            for b_idx in range(start_block, end_block):
                key = format_dht_block_key(model_id, b_idx, self.dht_prefix)
                if key not in self._store:
                    self._store[key] = {}
                self._store[key][node_id] = info
                published_keys.append(key)

            logger.debug(f"[DHT] Node {node_id} announced blocks [{start_block}:{end_block}) for {model_id} ({len(published_keys)} keys)")
            return published_keys

    def withdraw_blocks(self, node_id: str, model_id: str, start_block: int, end_block: int):
        """Withdraw block announcements for a specific node and range."""
        with self._lock:
            for b_idx in range(start_block, end_block):
                key = format_dht_block_key(model_id, b_idx, self.dht_prefix)
                if key in self._store and node_id in self._store[key]:
                    del self._store[key][node_id]
                    if not self._store[key]:
                        del self._store[key]

    def store_value(self, key: str, value: Any, ttl_sec: float = DEFAULT_BLOCK_TTL_SEC):
        """Generic key-value store in DHT space."""
        with self._lock:
            if key not in self._store:
                self._store[key] = {}
            if isinstance(value, ServerInfo):
                self._store[key][value.node_id] = value
            else:
                info = ServerInfo(
                    peer_id=self.local_peer_id,
                    node_id=self.local_node_id,
                    model_id="custom",
                    start_block=0,
                    end_block=1,
                    ttl_sec=ttl_sec,
                    expiration_time=time.time() + ttl_sec,
                    hardware_specs={"payload": value}
                )
                self._store[key][self.local_node_id] = info

    def get_block_providers(
        self,
        model_id: str,
        block_idx: int,
        include_draining: bool = False
    ) -> List[ServerInfo]:
        """
        Look up all active, non-expired servers hosting a specific transformer block.
        """
        key = format_dht_block_key(model_id, block_idx, self.dht_prefix)
        now = time.time()
        with self._lock:
            if key not in self._store:
                return []

            providers: List[ServerInfo] = []
            for n_id, info in self._store[key].items():
                if info.expiration_time < now:
                    continue  # Expired
                if not include_draining and n_id in self._draining_nodes:
                    continue  # Draining
                if n_id in self._quarantined_nodes and self._quarantined_nodes[n_id] > now:
                    continue  # Quarantined
                providers.append(info)

            return providers

    def get_all_block_providers_for_model(
        self,
        model_id: str,
        total_blocks: int,
        include_draining: bool = False
    ) -> Dict[int, List[ServerInfo]]:
        """
        Fetch all active block providers across all model blocks [0..total_blocks-1].
        """
        table: Dict[int, List[ServerInfo]] = {}
        for b_idx in range(total_blocks):
            table[b_idx] = self.get_block_providers(model_id, b_idx, include_draining=include_draining)
        return table

    # ─── Node State, Drain & Quarantining ─────────────────────────────────────

    def set_node_draining(self, node_id: str, draining: bool = True):
        """Mark a node as draining to gracefully migrate traffic away."""
        with self._lock:
            if draining:
                self._draining_nodes.add(node_id)
                if node_id in self._peer_registry:
                    self._peer_registry[node_id].state = PeerLifecycleState.DRAINING
                logger.info(f"[DHT] Node {node_id} is now set to DRAINING.")
            else:
                self._draining_nodes.discard(node_id)
                if node_id in self._peer_registry:
                    self._peer_registry[node_id].state = PeerLifecycleState.ACTIVE
                logger.info(f"[DHT] Node {node_id} restored to ACTIVE state.")

    def quarantine_node(self, node_id: str, duration_sec: float = 5.0):
        """Quarantine an unresponsive or failing node temporarily for fast circuit breaking."""
        with self._lock:
            self._quarantined_nodes[node_id] = time.time() + duration_sec
            logger.warning(f"[DHT] Node {node_id} QUARANTINED for {duration_sec:.1f}s.")

    def unquarantine_node(self, node_id: str):
        with self._lock:
            self._quarantined_nodes.pop(node_id, None)

    def is_node_available(self, node_id: str) -> bool:
        """Check if node is active and not currently draining or quarantined."""
        now = time.time()
        with self._lock:
            if node_id in self._draining_nodes:
                return False
            if node_id in self._quarantined_nodes and self._quarantined_nodes[node_id] > now:
                return False
            return True

    # ─── Verification & Maintenance ──────────────────────────────────────────

    def verify_model_coverage(self, model_id: str, total_blocks: int) -> Dict[str, Any]:
        """
        Verify if full block range [0..total_blocks-1] is actively hosted by reachable peers.
        Returns coverage diagnostics and redundancy counts.
        """
        missing_blocks: List[int] = []
        redundancy_map: Dict[int, int] = {}
        participating_nodes: Set[str] = set()

        for b_idx in range(total_blocks):
            providers = self.get_block_providers(model_id, b_idx, include_draining=False)
            count = len(providers)
            redundancy_map[b_idx] = count
            if count == 0:
                missing_blocks.append(b_idx)
            for p in providers:
                participating_nodes.add(p.node_id)

        is_complete = (len(missing_blocks) == 0)
        return {
            "model_id": model_id,
            "total_blocks": total_blocks,
            "is_covered": is_complete,
            "missing_blocks": missing_blocks,
            "covered_blocks_count": total_blocks - len(missing_blocks),
            "redundancy_map": redundancy_map,
            "participating_nodes": list(participating_nodes),
        }

    def clean_expired_entries(self) -> int:
        """Evict expired block announcements and prune old routing entries."""
        now = time.time()
        evicted_count = 0
        with self._lock:
            keys_to_delete = []
            for key, node_map in self._store.items():
                expired_nodes = [n_id for n_id, info in node_map.items() if info.expiration_time < now]
                for n_id in expired_nodes:
                    del node_map[n_id]
                    evicted_count += 1
                if not node_map:
                    keys_to_delete.append(key)

            for k in keys_to_delete:
                del self._store[k]

            # Prune expired quarantines
            quarantines_to_clear = [n_id for n_id, exp in self._quarantined_nodes.items() if exp < now]
            for n_id in quarantines_to_clear:
                del self._quarantined_nodes[n_id]

        return evicted_count

    # ─── Background Heartbeat Governor ───────────────────────────────────────

    def start_heartbeat_governor(self, interval_sec: float = 10.0):
        """Start background governor thread for TTL maintenance and link refreshing."""
        if self._governor_running:
            return
        self._governor_running = True

        def _governor_loop():
            logger.info(f"[DHT] Heartbeat governor started (interval={interval_sec}s)")
            while self._governor_running:
                try:
                    self.clean_expired_entries()
                except Exception as e:
                    logger.debug(f"[DHT] Governor error: {e}")
                time.sleep(interval_sec)

        self._governor_thread = threading.Thread(target=_governor_loop, daemon=True, name="DHT_HeartbeatGovernor")
        self._governor_thread.start()

    def stop_heartbeat_governor(self):
        """Stop background heartbeat governor."""
        self._governor_running = False
        if self._governor_thread and self._governor_thread.is_alive():
            self._governor_thread.join(timeout=2.0)
            logger.info("[DHT] Heartbeat governor stopped.")
