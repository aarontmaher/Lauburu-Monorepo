# -*- coding: utf-8 -*-
"""
Distributed Mesh Consensus & Leader Election Engine
===================================================
Subsystem: 02_ai_models_and_inference/distributed_mesh_consensus.py
Lauburu Mesh Ecosystem — 2026

Implements decentralized leader election and lease lock arbitration to prevent
split-brain self-healing interventions and concurrent conflicting recovery commands.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("DistributedMeshConsensus")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


@dataclass
class LeaseLock:
    leader_node_id: str
    leader_priority: int
    lease_granted_at: float
    lease_expires_at: float
    is_valid: bool


@dataclass
class NodeHeartbeat:
    node_id: str
    priority: int
    timestamp: float
    is_online: bool


class DistributedMeshConsensus:
    """
    Priority-weighted consensus and lease-lock manager for decentralized healing.
    """

    NODE_PRIORITIES: Dict[str, int] = {
        "L1": 100,  # Mac_Node (Host M4 Pro)
        "L2": 90,   # MacBook_Pro (Metal RPC)
        "L3": 80,   # Linux_Head_Node
        "L5": 70,   # MacBook_Air
        "GW": 60,   # GL.iNet Beryl AX Router
        "L6": 50,   # Pixel_10_Pro_XL
        "L7": 50,   # Samsung_S20
    }

    LEASE_DURATION_SEC: float = 3.0

    def __init__(self, current_node_id: str = "L1"):
        self.current_node_id = current_node_id
        self.node_heartbeats: Dict[str, NodeHeartbeat] = {}
        self.active_lease: Optional[LeaseLock] = None

        # Initialize local node heartbeat
        now = time.time()
        self.record_heartbeat(current_node_id, is_online=True, timestamp=now)

    def record_heartbeat(self, node_id: str, is_online: bool, timestamp: Optional[float] = None) -> None:
        ts = timestamp if timestamp is not None else time.time()
        priority = self.NODE_PRIORITIES.get(node_id, 10)
        self.node_heartbeats[node_id] = NodeHeartbeat(
            node_id=node_id,
            priority=priority,
            timestamp=ts,
            is_online=is_online,
        )

    def elect_leader(self, current_time: Optional[float] = None) -> str:
        """
        Elects the highest priority online node that has sent a heartbeat within the last 3.0s.
        """
        now = current_time if current_time is not None else time.time()
        eligible_nodes = []

        for nid, hb in self.node_heartbeats.items():
            if hb.is_online and (now - hb.timestamp <= self.LEASE_DURATION_SEC):
                eligible_nodes.append((hb.priority, nid))

        if not eligible_nodes:
            # Fallback to current node if all else offline
            return self.current_node_id

        # Sort by priority descending
        eligible_nodes.sort(key=lambda x: x[0], reverse=True)
        return eligible_nodes[0][1]

    def acquire_or_renew_lease(self, current_time: Optional[float] = None) -> LeaseLock:
        """
        Acquires or renews the self-healing lease lock for the elected leader.
        """
        now = current_time if current_time is not None else time.time()
        leader_id = self.elect_leader(current_time=now)
        leader_prio = self.NODE_PRIORITIES.get(leader_id, 10)

        lease = LeaseLock(
            leader_node_id=leader_id,
            leader_priority=leader_prio,
            lease_granted_at=now,
            lease_expires_at=now + self.LEASE_DURATION_SEC,
            is_valid=True,
        )
        self.active_lease = lease
        return lease

    def can_execute_healing_action(self, node_id: str, current_time: Optional[float] = None) -> bool:
        """
        Determines whether the requesting node is authorized to execute a network-altering command.
        """
        now = current_time if current_time is not None else time.time()
        if not self.active_lease or now > self.active_lease.lease_expires_at:
            self.acquire_or_renew_lease(current_time=now)

        assert self.active_lease is not None
        # Either the node is the active lease holder, or local emergency fallback is permitted
        return self.active_lease.leader_node_id == node_id
