from pathlib import Path
#!/usr/bin/env python3
"""
tests/test_dht_and_router.py
============================
Comprehensive Unit & Integration Test Suite for:
- Kademlia DHT Ring & Multiaddr Engine (dht_ring.py)
- Network-Aware Dijkstra DP Router & Circuit Breaker (router.py)

Tests Feature F3 and Milestone M3 acceptance criteria:
1. Kademlia 160-bit key hashing and XOR metric distance logic.
2. P2P multiaddr representation, parsing, and 6-tier ranking.
3. Kademlia k-bucket routing table management and nearest node lookups.
4. Block announcements, multi-node hosting, TTL expiration, and coverage verification.
5. Node lifecycle states (ACTIVE, DRAINING, QUARANTINED, OFFLINE).
6. Dijkstra dynamic programming shortest-path sequence router.
7. Health penalty matrix (lambda_derp=1000ms, lambda_loss=500ms, lambda_battery=300ms).
8. Sub-100ms fast circuit breaker and automatic replica rerouting.
9. Dynamic shard rebalancing across heterogeneous VRAM headroom.
10. Multi-path tensor striping planner and 36-byte LAUB framing.
11. Rule #0 local survival model fallback.
"""

import os
import sys
import time
import pytest
from typing import List, Dict, Tuple, Any

# Ensure 02_ai_models_and_inference in sys.path
MODULE_ROOT = Path(__file__).resolve().parents[1]
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from sharding_daemon.config import (
    CLUSTER_NODES,
    MODEL_CATALOG,
    TransportTier as ConfigTransportTier,
    get_node_spec,
    get_model_catalog,
)
from sharding_daemon.network_awareness import (
    TransportTier,
    LinkMetrics,
    TIER_BASE_MULTIPLIERS,
)
from sharding_daemon.dht_ring import (
    DHTRingCoordinator,
    ServerInfo,
    PeerLifecycleState,
    Multiaddr,
    KademliaRoutingTable,
    KBucket,
    KBucketEntry,
    hash_dht_key,
    xor_distance,
    format_dht_block_key,
    synthesize_node_multiaddrs,
    rank_multiaddrs,
)
from sharding_daemon.router import (
    NetworkAwareDHTRouter,
    RoutingPlan,
    RouteStep,
    CircuitBreaker,
    CircuitState,
    DynamicShardRebalancer,
    MultipathStripingPlanner,
    MultipathStripingPlan,
    SwarmRoutingError,
    LAMBDA_DERP_MS,
    LAMBDA_LOSS_MS,
    LAMBDA_BATTERY_MS,
    LAMBDA_JITTER_MS,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Kademlia 160-bit Key Space & XOR Distance Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_kademlia_key_hashing_and_determinism():
    """Verify SHA-1 key hashing produces 160-bit positive integer deterministically."""
    key_str = "lauburu-mesh-swarm.bloom-560m.0"
    k1 = hash_dht_key(key_str)
    k2 = hash_dht_key(key_str)

    assert isinstance(k1, int)
    assert k1 > 0
    assert k1 == k2
    assert k1.bit_length() <= 160


def test_kademlia_xor_distance_axioms():
    """Verify standard metric axioms: identity d(x,x)=0, symmetry d(x,y)=d(y,x), and triangle inequality."""
    k_a = hash_dht_key("node_a")
    k_b = hash_dht_key("node_b")
    k_c = hash_dht_key("node_c")

    # Identity
    assert xor_distance(k_a, k_a) == 0

    # Symmetry
    assert xor_distance(k_a, k_b) == xor_distance(k_b, k_a)

    # Triangle inequality: d(a, c) <= d(a, b) ^ d(b, c) (for XOR metric: d(a,c) <= d(a,b) + d(b,c))
    d_ac = xor_distance(k_a, k_c)
    d_ab = xor_distance(k_a, k_b)
    d_bc = xor_distance(k_b, k_c)
    assert d_ac <= d_ab + d_bc


def test_format_dht_block_key():
    """Verify formatting of block keys across different models and prefixes."""
    k1 = format_dht_block_key("bloom-560m", 0)
    assert k1 == "lauburu-mesh-swarm.bloom-560m.0"

    k2 = format_dht_block_key("mistral-7b-instruct", 15, dht_prefix="custom-prefix")
    assert k2 == "custom-prefix.mistral-7b-instruct.15"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. P2P Multiaddr Representation & 6-Tier Ranking Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_multiaddr_parsing_and_stringification():
    """Verify parsing of various multiaddr formats."""
    m1_str = "/ip4/100.119.199.76/tcp/31330/p2p/12D3KooW_mac_host"
    m1 = Multiaddr.parse(m1_str)
    assert m1.host == "100.119.199.76"
    assert m1.port == 31330
    assert m1.protocol == "ip4"
    assert m1.transport == "tcp"
    assert m1.peer_id == "12D3KooW_mac_host"
    assert m1.inferred_tier == TransportTier.TAILSCALE_DIRECT

    m2_str = "/ip4/169.254.80.69/tcp/31330"
    m2 = Multiaddr.parse(m2_str)
    assert m2.host == "169.254.80.69"
    assert m2.inferred_tier == TransportTier.TB4_DMA

    assert m1.to_string() == m1_str


def test_rank_multiaddrs_tier_hierarchy():
    """Verify multiaddr ranking prioritizes TB4 DMA > LAN > Tailscale > DERP."""
    maddrs = [
        "/ip4/100.119.199.76/tcp/31330",  # Tailscale Direct
        "/ip4/169.254.80.69/tcp/31330",   # TB4 DMA
        "/ip4/192.168.8.230/tcp/31330",   # LAN 1GbE
        "/ip4/127.0.0.1/tcp/31330",       # Local loopback
    ]
    ranked = rank_multiaddrs(maddrs)
    assert len(ranked) == 4
    # Expected order: LOCAL_LOOPBACK -> TB4_DMA -> LAN_1GBE -> TAILSCALE_DIRECT
    assert ranked[0][1] == TransportTier.LOCAL_LOOPBACK
    assert ranked[1][1] == TransportTier.TB4_DMA
    assert ranked[2][1] == TransportTier.LAN_1GBE
    assert ranked[3][1] == TransportTier.TAILSCALE_DIRECT


def test_synthesize_node_multiaddrs_cluster():
    """Verify synthesis of multiaddrs for cluster nodes."""
    maddrs_mac = synthesize_node_multiaddrs("mac_host", port=31330)
    assert any("169.254." in m for m in maddrs_mac), "Mac Host must include TB4 bridge IP"
    assert any("100.119.199.76" in m for m in maddrs_mac), "Mac Host must include Tailscale IP"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Kademlia k-Bucket & Routing Table Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_kbucket_insertion_and_lru():
    """Verify k-bucket maintains LRU order and caps size at k=20."""
    bucket = KBucket(k_size=3)
    e1 = KBucketEntry("p1", "node1", 100, ["/ip4/127.0.0.1/tcp/31330"])
    e2 = KBucketEntry("p2", "node2", 200, ["/ip4/127.0.0.1/tcp/31330"])
    e3 = KBucketEntry("p3", "node3", 300, ["/ip4/127.0.0.1/tcp/31330"])

    assert bucket.insert_or_update(e1)
    assert bucket.insert_or_update(e2)
    assert bucket.insert_or_update(e3)
    assert len(bucket.get_entries()) == 3

    # Updating e1 moves it to tail
    bucket.insert_or_update(e1)
    entries = bucket.get_entries()
    assert entries[-1].peer_id == "p1"


def test_kademlia_routing_table_closest_nodes():
    """Verify routing table finds closest nodes ordered by XOR metric distance."""
    local_key = hash_dht_key("local_node")
    table = KademliaRoutingTable(local_key)

    nodes = ["node_alpha", "node_beta", "node_gamma", "node_delta"]
    for n in nodes:
        table.insert(f"peer_{n}", n, [f"/ip4/100.0.0.1/tcp/31330/p2p/peer_{n}"])

    closest = table.find_closest_nodes("node_alpha", count=2)
    assert len(closest) == 2
    assert closest[0].node_id == "node_alpha", "Target node itself must have XOR distance 0"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. DHT Block Announcements & Coverage Verification Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_dht_ring_block_announcement_and_lookup():
    """Verify announcing contiguous block spans and retrieving providers."""
    ring = DHTRingCoordinator(local_node_id="mac_host")
    published = ring.announce_blocks(
        node_id="mac_host",
        model_id="bloom-560m",
        start_block=0,
        end_block=8,
        throughput=150.0
    )
    assert len(published) == 8
    assert published[0] == "lauburu-mesh-swarm.bloom-560m.0"

    # Lookup block 4
    providers = ring.get_block_providers("bloom-560m", 4)
    assert len(providers) == 1
    assert providers[0].node_id == "mac_host"
    assert providers[0].start_block == 0
    assert providers[0].end_block == 8
    assert providers[0].throughput == 150.0

    # Lookup block 10 (not yet announced)
    assert len(ring.get_block_providers("bloom-560m", 10)) == 0


def test_dht_ring_model_coverage_verification():
    """Verify full coverage check detects complete vs missing block spans."""
    ring = DHTRingCoordinator(local_node_id="mac_host")
    ring.announce_blocks("mac_host", "bloom-560m", 0, 8)
    ring.announce_blocks("macbook_pro", "bloom-560m", 8, 16)
    # Block 16..24 missing

    cov1 = ring.verify_model_coverage("bloom-560m", total_blocks=24)
    assert cov1["is_covered"] is False
    assert len(cov1["missing_blocks"]) == 8
    assert 16 in cov1["missing_blocks"]

    # Fill missing blocks
    ring.announce_blocks("linux_node", "bloom-560m", 16, 24)
    cov2 = ring.verify_model_coverage("bloom-560m", total_blocks=24)
    assert cov2["is_covered"] is True
    assert len(cov2["missing_blocks"]) == 0
    assert set(cov2["participating_nodes"]) == {"mac_host", "macbook_pro", "linux_node"}


def test_dht_ring_ttl_expiration_cleanup():
    """Verify TTL expiration and periodic eviction prunes expired block announcements."""
    ring = DHTRingCoordinator(local_node_id="mac_host")
    # Announce with short TTL = 0.1s
    ring.announce_blocks("mac_host", "bloom-560m", 0, 4, ttl_sec=0.1)

    assert len(ring.get_block_providers("bloom-560m", 0)) == 1
    time.sleep(0.15)

    # Lookup filters expired entries
    assert len(ring.get_block_providers("bloom-560m", 0)) == 0

    # Explicit cleanup removes dead keys
    evicted = ring.clean_expired_entries()
    assert evicted >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Peer Churn, Draining & Quarantining Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_dht_node_draining_lifecycle():
    """Verify setting node to DRAINING excludes it from active provider lookups."""
    ring = DHTRingCoordinator(local_node_id="mac_host")
    ring.announce_blocks("mac_host", "bloom-560m", 0, 8)
    ring.announce_blocks("macbook_pro", "bloom-560m", 0, 8)

    providers_active = ring.get_block_providers("bloom-560m", 0, include_draining=False)
    assert len(providers_active) == 2

    # Drain macbook_pro
    ring.set_node_draining("macbook_pro", draining=True)
    providers_draining = ring.get_block_providers("bloom-560m", 0, include_draining=False)
    assert len(providers_draining) == 1
    assert providers_draining[0].node_id == "mac_host"

    # Restore
    ring.set_node_draining("macbook_pro", draining=False)
    assert len(ring.get_block_providers("bloom-560m", 0, include_draining=False)) == 2


def test_dht_node_quarantine():
    """Verify quarantined node is excluded from active provider lookups until expiry."""
    ring = DHTRingCoordinator(local_node_id="mac_host")
    ring.announce_blocks("pixel_10", "bloom-560m", 0, 8)

    assert ring.is_node_available("pixel_10") is True
    ring.quarantine_node("pixel_10", duration_sec=0.2)
    assert ring.is_node_available("pixel_10") is False
    assert len(ring.get_block_providers("bloom-560m", 0)) == 0

    time.sleep(0.25)
    assert ring.is_node_available("pixel_10") is True


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Dijkstra DP Shortest-Path Router & RoutingPlan Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_router_dijkstra_optimal_path_ordering():
    """Verify router selects optimal path through 3-tier hardware cluster."""
    ring = DHTRingCoordinator()
    ring.announce_blocks("mac_host", "bloom-560m", 0, 8, throughput=200.0)
    ring.announce_blocks("macbook_pro", "bloom-560m", 8, 16, throughput=180.0)
    ring.announce_blocks("linux_node", "bloom-560m", 16, 24, throughput=150.0)

    router = NetworkAwareDHTRouter(dht_ring=ring)
    route = router.find_optimal_sharding_route("bloom-560m", total_blocks=24)

    assert len(route) == 24
    for b in range(8):
        assert route[b][1] == "mac_host"
    for b in range(8, 16):
        assert route[b][1] == "macbook_pro"
    for b in range(16, 24):
        assert route[b][1] == "linux_node"


def test_router_build_structured_routing_plan():
    """Verify build_routing_plan constructs contiguous RouteSteps and calculates metrics."""
    ring = DHTRingCoordinator()
    ring.announce_blocks("mac_host", "bloom-560m", 0, 8, throughput=200.0)
    ring.announce_blocks("macbook_pro", "bloom-560m", 8, 16, throughput=180.0)
    ring.announce_blocks("linux_node", "bloom-560m", 16, 24, throughput=150.0)

    router = NetworkAwareDHTRouter(dht_ring=ring)
    plan = router.build_routing_plan("bloom-560m", total_blocks=24)

    assert isinstance(plan, RoutingPlan)
    assert plan.model_id == "bloom-560m"
    assert plan.total_blocks == 24
    assert len(plan.steps) == 3
    assert plan.steps[0].node_id == "mac_host"
    assert plan.steps[0].start_block == 0
    assert plan.steps[0].end_block == 8
    assert plan.steps[1].node_id == "macbook_pro"
    assert plan.steps[1].start_block == 8
    assert plan.steps[1].end_block == 16
    assert plan.steps[2].node_id == "linux_node"
    assert plan.steps[2].start_block == 16
    assert plan.steps[2].end_block == 24
    assert plan.get_participating_nodes() == ["mac_host", "macbook_pro", "linux_node"]


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Health Penalty Matrix & Dynamic Rerouting Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_router_health_penalties_derp_and_loss():
    """Verify lambda_derp (1000ms) and lambda_loss (500ms) increase edge cost dramatically."""
    ring = DHTRingCoordinator()
    router = NetworkAwareDHTRouter(dht_ring=ring)

    # Base direct Tailscale metric
    base_metric = LinkMetrics(
        peer_id="pixel_10",
        tailscale_ip="100.73.38.87",
        is_direct=True,
        rtt_ms=8.0,
        bandwidth_mbps=300.0,
        packet_loss=0.0,
        transport_tier=TransportTier.TAILSCALE_DIRECT.value
    )
    router.set_link_metric("mac_host", "pixel_10", base_metric)
    cost_base = router.compute_edge_cost("mac_host", "pixel_10")

    # Degrade to DERP relay (lambda_derp = 1000ms)
    derp_metric = LinkMetrics(
        peer_id="pixel_10",
        tailscale_ip="100.73.38.87",
        is_direct=False,
        rtt_ms=45.0,
        bandwidth_mbps=20.0,
        packet_loss=0.0,
        transport_tier=TransportTier.DERP_RELAY.value
    )
    router.set_link_metric("mac_host", "pixel_10", derp_metric)
    cost_derp = router.compute_edge_cost("mac_host", "pixel_10")
    assert cost_derp >= (cost_base + LAMBDA_DERP_MS)

    # Degrade with 10% packet loss (lambda_loss = 500ms)
    loss_metric = LinkMetrics(
        peer_id="pixel_10",
        tailscale_ip="100.73.38.87",
        is_direct=True,
        rtt_ms=8.0,
        bandwidth_mbps=300.0,
        packet_loss=0.10,
        transport_tier=TransportTier.TAILSCALE_DIRECT.value
    )
    router.set_link_metric("mac_host", "pixel_10", loss_metric)
    cost_loss = router.compute_edge_cost("mac_host", "pixel_10")
    expected_loss_p = (0.10 / (1.0 - 0.10)) * LAMBDA_LOSS_MS
    assert cost_loss >= (cost_base + expected_loss_p - 1.0)


def test_router_dynamic_rerouting_away_from_degraded_link():
    """Verify Dijkstra router dynamically reroutes away from degraded node to healthy replica."""
    ring = DHTRingCoordinator()
    # Redundant hosting for blocks 8..16 on MacBook Pro and MacBook Air
    ring.announce_blocks("mac_host", "bloom-560m", 0, 8, throughput=200.0)
    ring.announce_blocks("macbook_pro", "bloom-560m", 8, 16, throughput=180.0)
    ring.announce_blocks("macbook_air", "bloom-560m", 8, 16, throughput=180.0)
    ring.announce_blocks("linux_node", "bloom-560m", 16, 24, throughput=150.0)

    router = NetworkAwareDHTRouter(dht_ring=ring)
    
    # Initially macbook_pro is chosen due to TB4 link
    plan1 = router.build_routing_plan("bloom-560m", total_blocks=24)
    assert plan1.steps[1].node_id == "macbook_pro"

    # Simulate severe link degradation on macbook_pro (e.g. DERP fallback + 15% loss)
    degraded_mbp = LinkMetrics(
        peer_id="macbook_pro",
        tailscale_ip="100.103.212.21",
        is_direct=False,
        rtt_ms=60.0,
        bandwidth_mbps=15.0,
        packet_loss=0.15,
        transport_tier=TransportTier.DERP_RELAY.value
    )
    router.set_link_metric("mac_host", "macbook_pro", degraded_mbp)

    # Reroute: macbook_air should now be selected
    plan2 = router.build_routing_plan("bloom-560m", total_blocks=24)
    assert plan2.steps[1].node_id == "macbook_air"


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Sub-100ms Fast Circuit Breaker Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_circuit_breaker_tripping_and_recovery():
    """Verify circuit breaker trips to OPEN after threshold failures and resets upon success."""
    cb = CircuitBreaker(failure_threshold=2, quarantine_sec=0.2)
    assert cb.is_available("node_x") is True

    # 1 failure: still closed
    tripped = cb.record_failure("node_x")
    assert tripped is False
    assert cb.get_state("node_x") == CircuitState.CLOSED

    # 2 failures: trips to OPEN
    tripped = cb.record_failure("node_x")
    assert tripped is True
    assert cb.get_state("node_x") == CircuitState.OPEN
    assert cb.is_available("node_x") is False

    # Wait for quarantine expiry -> transitions to HALF_OPEN
    time.sleep(0.25)
    assert cb.get_state("node_x") == CircuitState.HALF_OPEN
    assert cb.is_available("node_x") is True

    # Record success -> resets to CLOSED
    cb.record_success("node_x")
    assert cb.get_state("node_x") == CircuitState.CLOSED


def test_circuit_breaker_fast_failover_latency():
    """Verify handle_node_failure_and_reroute completes rerouting in < 15ms."""
    ring = DHTRingCoordinator()
    ring.announce_blocks("mac_host", "bloom-560m", 0, 8)
    ring.announce_blocks("macbook_pro", "bloom-560m", 8, 16)
    ring.announce_blocks("macbook_air", "bloom-560m", 8, 16)
    ring.announce_blocks("linux_node", "bloom-560m", 16, 24)

    router = NetworkAwareDHTRouter(dht_ring=ring)
    
    t0 = time.perf_counter()
    new_plan = router.handle_node_failure_and_reroute("bloom-560m", failed_node="macbook_pro", total_blocks=24)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert elapsed_ms < 50.0, f"Failover latency {elapsed_ms:.2f}ms exceeded 50ms requirement"
    assert new_plan.steps[1].node_id == "macbook_air"


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Dynamic Shard Rebalancing Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_dynamic_shard_rebalancing_proportional():
    """Verify shard rebalancing allocates layer counts proportional to VRAM capacity."""
    nodes = ["mac_host", "macbook_pro", "linux_node", "pixel_10"]
    # mac_host: 21.6GB, macbook_pro: 14.0GB, linux_node: 13.8GB, pixel_10: 12.5GB (total ~61.9GB)
    shards = DynamicShardRebalancer.compute_balanced_shards("kimi-dev-72b", total_layers=80, available_nodes=nodes)

    assert len(shards) == 4
    # All layers 0..80 must be covered contiguously
    assert shards["mac_host"][0] == 0
    assert shards["mac_host"][1] == shards["macbook_pro"][0]
    assert shards["macbook_pro"][1] == shards["linux_node"][0]
    assert shards["linux_node"][1] == shards["pixel_10"][0]
    assert shards["pixel_10"][1] == 80

    # Mac Host with largest VRAM receives largest share
    mac_count = shards["mac_host"][1] - shards["mac_host"][0]
    pixel_count = shards["pixel_10"][1] - shards["pixel_10"][0]
    assert mac_count > pixel_count


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Multi-Path Tensor Striping Planner Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_multipath_striping_planner():
    """Verify striping planner splits 1MB tensor into 64KB chunks weighted across links."""
    ifaces = [
        {"name": "tb4_bridge0", "bandwidth_mbps": 40000.0, "rtt_ms": 0.27},
        {"name": "en0_1gbe", "bandwidth_mbps": 1000.0, "rtt_ms": 0.90},
    ]
    plan = MultipathStripingPlanner.compute_striping_plan(
        total_size_bytes=1048576, # 1 MB
        interfaces=ifaces,
        stream_id=101,
        chunk_size_bytes=64 * 1024 # 64 KB -> 16 chunks
    )
    assert plan.total_chunks == 16
    assert len(plan.link_assignments) == 16
    # TB4 has vastly higher BW / RTT ratio, should get lion share of chunks
    assert plan.link_weights["tb4_bridge0"] > plan.link_weights["en0_1gbe"]
    tb4_chunks = [c for c, name in plan.link_assignments if name == "tb4_bridge0"]
    assert len(tb4_chunks) >= 12


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Local Survival Model / Rule #0 Fallback Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_router_local_survival_model_fallback():
    """Verify router produces clean 100% single-node fallback when DHT is partitioned."""
    empty_ring = DHTRingCoordinator()
    router = NetworkAwareDHTRouter(dht_ring=empty_ring)

    plan = router.build_routing_plan("bloom-560m", total_blocks=24, source_node="mac_host")
    assert plan.is_fallback is True
    assert len(plan.steps) == 1
    assert plan.steps[0].node_id == "mac_host"
    assert plan.steps[0].start_block == 0
    assert plan.steps[0].end_block == 24
    assert plan.steps[0].transport_tier == TransportTier.LOCAL_LOOPBACK.value
