"""
capacity_governor.py — Dynamic RAM/VRAM Capacity Governor for Router AI Daemon (smolagi).

Enforces strict <= 300MB RAM budget on GL.iNet router (N_local <= 3) and computes
distributed mesh offload scaling across the 7-Layer physical topology up to 64 workers.
Authoritative Specifications: ORIGINAL_REQUEST.md §R3 & PROJECT.md §F6.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.config import RouterConfig, get_config


@dataclass(frozen=True)
class MeshNodeSpec:
    """Specification of a physical mesh network node."""

    layer: str
    name: str
    ip: str
    ram_mb: float
    ai_cap_mb: float
    type: str
    alpha: float
    eta: float
    online: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer": self.layer,
            "name": self.name,
            "ip": self.ip,
            "ram_mb": self.ram_mb,
            "ai_cap_mb": self.ai_cap_mb,
            "type": self.type,
            "alpha": self.alpha,
            "eta": self.eta,
            "online": self.online,
        }


# Canonical 7-Layer Hardware Topology Matrix
CANONICAL_MESH_MATRIX: Dict[str, MeshNodeSpec] = {
    "GW": MeshNodeSpec(
        layer="GW",
        name="GL_iNet_Router",
        ip="192.168.8.1",
        ram_mb=1024.0,
        ai_cap_mb=300.0,
        type="arm64",
        alpha=1.0,
        eta=1.0,
    ),
    "L1": MeshNodeSpec(
        layer="L1",
        name="Mac_Node",
        ip="192.168.8.230",
        ram_mb=24576.0,
        ai_cap_mb=22118.4,
        type="arm64",
        alpha=0.90,
        eta=1.00,
    ),
    "L2": MeshNodeSpec(
        layer="L2",
        name="MacBook_Pro",
        ip="192.168.8.127",
        ram_mb=16384.0,
        ai_cap_mb=14336.0,
        type="arm64",
        alpha=0.90,
        eta=1.00,
    ),
    "L3": MeshNodeSpec(
        layer="L3",
        name="Linux_Head_Node",
        ip="192.168.8.224",
        ram_mb=16384.0,
        ai_cap_mb=13107.2,
        type="x86_64",
        alpha=0.80,
        eta=0.85,
    ),
    "L4": MeshNodeSpec(
        layer="L4",
        name="Linux_Tablet",
        ip="100.81.92.125",
        ram_mb=8192.0,
        ai_cap_mb=6144.0,
        type="x86_64",
        alpha=0.75,
        eta=0.70,
    ),
    "L5": MeshNodeSpec(
        layer="L5",
        name="MacBook_Air",
        ip="192.168.8.222",
        ram_mb=16384.0,
        ai_cap_mb=14336.0,
        type="arm64",
        alpha=0.90,
        eta=0.85,
    ),
    "L6": MeshNodeSpec(
        layer="L6",
        name="Pixel_10_Pro_XL",
        ip="100.73.38.87",
        ram_mb=16384.0,
        ai_cap_mb=12800.0,
        type="arm64",
        alpha=0.75,
        eta=0.70,
    ),
    "L7": MeshNodeSpec(
        layer="L7",
        name="Samsung_S20",
        ip="100.84.40.95",
        ram_mb=12288.0,
        ai_cap_mb=9216.0,
        type="arm64",
        alpha=0.75,
        eta=0.70,
    ),
}


@dataclass
class CapacityReport:
    """Detailed capacity status for local container and mesh network."""

    total_cap_mb: float
    core_daemon_mb: float
    safety_headroom_mb: float
    current_used_mb: float
    allocatable_mb: float
    max_local_workers: int
    active_local_workers: int
    active_mesh_workers: int
    mesh_nodes_online: int
    is_healthy: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_cap_mb": self.total_cap_mb,
            "core_daemon_mb": self.core_daemon_mb,
            "safety_headroom_mb": self.safety_headroom_mb,
            "current_used_mb": self.current_used_mb,
            "allocatable_mb": self.allocatable_mb,
            "max_local_workers": self.max_local_workers,
            "active_local_workers": self.active_local_workers,
            "active_mesh_workers": self.active_mesh_workers,
            "mesh_nodes_online": self.mesh_nodes_online,
            "is_healthy": self.is_healthy,
        }


@dataclass
class ScalePlan:
    """Computed allocation plan for swarm scaling."""

    target_count: int
    local_allocated: int
    mesh_allocated: int
    offload_by_layer: Dict[str, int]
    headroom_mb: float
    total_ram_allocated_mb: float
    is_feasible: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_count": self.target_count,
            "local_allocated": self.local_allocated,
            "mesh_allocated": self.mesh_allocated,
            "offload_by_layer": dict(self.offload_by_layer),
            "headroom_mb": self.headroom_mb,
            "total_ram_allocated_mb": self.total_ram_allocated_mb,
            "is_feasible": self.is_feasible,
        }


class CapacityGovernor:
    """Dynamic capacity governor enforcing router RAM limits and orchestrating mesh scaling."""

    def __init__(
        self,
        config: Optional[RouterConfig] = None,
        mesh_matrix: Optional[Dict[str, Any]] = None,
        core_daemon_mb: float = 110.0,
        safety_headroom_mb: float = 40.0,
        max_local_workers: int = 3,
        avg_specialist_mb: float = 45.0,
    ) -> None:
        self.config = config or get_config()
        self.total_cap_mb = float(self.config.ram_budget_mb)
        self.core_daemon_mb = float(core_daemon_mb)
        self.safety_headroom_mb = float(safety_headroom_mb)
        self.max_local_workers = int(max_local_workers)
        self.avg_specialist_mb = float(avg_specialist_mb)

        # Initialize mesh nodes
        self._mesh_nodes: Dict[str, MeshNodeSpec] = {}
        if mesh_matrix is None:
            self._mesh_nodes = dict(CANONICAL_MESH_MATRIX)
        else:
            for layer, node in mesh_matrix.items():
                if isinstance(node, MeshNodeSpec):
                    self._mesh_nodes[layer] = node
                elif isinstance(node, dict):
                    alpha = node.get("alpha", 0.90 if "Mac" in node.get("name", "") else 0.80)
                    eta = node.get("eta", 1.0 if "TB4" in node.get("name", "") or layer in ("L1", "L2") else 0.85)
                    self._mesh_nodes[layer] = MeshNodeSpec(
                        layer=layer,
                        name=node.get("name", f"Node_{layer}"),
                        ip=node.get("ip", "127.0.0.1"),
                        ram_mb=float(node.get("ram_mb", 1024.0)),
                        ai_cap_mb=float(node.get("ai_cap_mb", 300.0)),
                        type=node.get("type", "arm64"),
                        alpha=float(alpha),
                        eta=float(eta),
                        online=node.get("online", True),
                    )

    def compute_local_capacity(
        self,
        used_mb: Optional[float] = None,
        avg_spec_mb: Optional[float] = None,
    ) -> int:
        """
        Compute maximum allowed concurrent local specialists on the router.
        Formula: N_local = min(N_max_local, max(0, floor((Cap - Core - Headroom) / avg_spec_mb)))
        """
        spec_size = avg_spec_mb or self.avg_specialist_mb
        base_used = used_mb if used_mb is not None else self.core_daemon_mb
        available_mb = self.total_cap_mb - base_used - self.safety_headroom_mb
        if available_mb <= 0:
            return 0
        n_local = int(math.floor(available_mb / spec_size))
        return min(self.max_local_workers, max(0, n_local))

    def compute_allocatable_headroom(self, current_used_mb: float) -> float:
        """
        Compute dynamic allocatable RAM headroom under safety margin.
        Formula: allocatable_mb = max(0.0, total_cap_mb - current_used_mb - safety_headroom_mb)
        """
        return max(0.0, self.total_cap_mb - current_used_mb - self.safety_headroom_mb)

    def can_allocate_local(
        self,
        current_used_mb: float,
        requested_mb: float,
        enforce_safety_headroom: bool = True,
    ) -> bool:
        """
        Check if a requested RAM allocation is valid under strict <= 300MB budget.
        """
        total_projected = current_used_mb + requested_mb
        if total_projected > self.total_cap_mb:
            return False
        if enforce_safety_headroom:
            # Must preserve at least safety headroom
            if (self.total_cap_mb - total_projected) < 0:
                return False
        return True

    def compute_mesh_capacity(
        self,
        avg_worker_vram_mb: float = 100.0,
    ) -> Dict[str, Any]:
        """
        Calculate distributed mesh worker capacity across physical layers (L1-L7).
        Formula: workers_k = floor((VRAM_free_k * alpha_k) / avg_worker_vram_mb)
        """
        mesh_breakdown: Dict[str, int] = {}
        total_mesh_workers = 0

        for layer, node in self._mesh_nodes.items():
            if layer == "GW" or not node.online:
                continue
            vram_free_mb = node.ai_cap_mb
            allocatable_mb = vram_free_mb * node.alpha
            workers_on_node = int(allocatable_mb // avg_worker_vram_mb)
            mesh_breakdown[layer] = workers_on_node
            total_mesh_workers += workers_on_node

        return {
            "total_mesh_workers": total_mesh_workers,
            "layer_breakdown": mesh_breakdown,
            "nodes_online": sum(1 for l, n in self._mesh_nodes.items() if l != "GW" and n.online),
        }

    def calculate_scale_plan(
        self,
        target_workers: int,
        current_local_workers: int = 0,
        current_mesh_workers: int = 0,
        max_total_mesh_workers: int = 64,
    ) -> ScalePlan:
        """
        Compute optimal swarm scale plan distributing workers between local router and mesh layers.
        Enforces N_local <= 3 and distributes overflow across L1..L7.
        """
        if target_workers <= 0:
            return ScalePlan(
                target_count=0,
                local_allocated=0,
                mesh_allocated=0,
                offload_by_layer={},
                headroom_mb=self.compute_allocatable_headroom(self.core_daemon_mb),
                total_ram_allocated_mb=self.core_daemon_mb,
                is_feasible=True,
            )

        # 1. Determine local worker quota
        max_local_possible = self.compute_local_capacity()
        local_allocated = min(target_workers, max_local_possible)
        overflow_needed = target_workers - local_allocated

        # 2. Distribute overflow across mesh layers in priority order
        offload_by_layer: Dict[str, int] = {}
        remaining_needed = min(overflow_needed, max_total_mesh_workers)
        mesh_allocated = 0

        # Preferred mesh allocation order: L1 (Mac Mini), L2 (MBP), L3 (Linux Head Node),
        # L5 (MacBook Air), L4 (Tablet), L6 (Pixel), L7 (Samsung)
        layer_priority = ["L1", "L2", "L3", "L5", "L4", "L6", "L7"]

        for layer in layer_priority:
            if remaining_needed <= 0:
                break
            node = self._mesh_nodes.get(layer)
            if not node or not node.online:
                continue

            node_cap_workers = int((node.ai_cap_mb * node.alpha) // 100.0)
            assigned = min(remaining_needed, node_cap_workers)
            if assigned > 0:
                offload_by_layer[layer] = assigned
                mesh_allocated += assigned
                remaining_needed -= assigned

        total_local_ram = self.core_daemon_mb + (local_allocated * self.avg_specialist_mb)
        headroom = max(0.0, self.total_cap_mb - total_local_ram)
        is_feasible = (local_allocated + mesh_allocated) >= target_workers

        return ScalePlan(
            target_count=target_workers,
            local_allocated=local_allocated,
            mesh_allocated=mesh_allocated,
            offload_by_layer=offload_by_layer,
            headroom_mb=headroom,
            total_ram_allocated_mb=total_local_ram,
            is_feasible=is_feasible,
        )

    def get_capacity_report(
        self,
        current_used_mb: float,
        active_local_workers: int,
        active_mesh_workers: int,
    ) -> CapacityReport:
        """Generate comprehensive capacity and health report."""
        allocatable = self.compute_allocatable_headroom(current_used_mb)
        online_count = sum(1 for n in self._mesh_nodes.values() if n.online)
        is_healthy = (
            current_used_mb <= self.total_cap_mb
            and (self.total_cap_mb - current_used_mb) >= self.safety_headroom_mb
        )

        return CapacityReport(
            total_cap_mb=self.total_cap_mb,
            core_daemon_mb=self.core_daemon_mb,
            safety_headroom_mb=self.safety_headroom_mb,
            current_used_mb=current_used_mb,
            allocatable_mb=allocatable,
            max_local_workers=self.max_local_workers,
            active_local_workers=active_local_workers,
            active_mesh_workers=active_mesh_workers,
            mesh_nodes_online=online_count,
            is_healthy=is_healthy,
        )

    def get_mesh_node(self, layer: str) -> Optional[MeshNodeSpec]:
        """Retrieve node specification for a given layer."""
        return self._mesh_nodes.get(layer.upper())

    def update_node_status(self, layer: str, online: bool) -> bool:
        """Update online status of a mesh node."""
        layer_upper = layer.upper()
        if layer_upper in self._mesh_nodes:
            old = self._mesh_nodes[layer_upper]
            self._mesh_nodes[layer_upper] = MeshNodeSpec(
                layer=old.layer,
                name=old.name,
                ip=old.ip,
                ram_mb=old.ram_mb,
                ai_cap_mb=old.ai_cap_mb,
                type=old.type,
                alpha=old.alpha,
                eta=old.eta,
                online=online,
            )
            return True
        return False


# Global singleton instance
DEFAULT_GOVERNOR = CapacityGovernor()


def get_capacity_governor() -> CapacityGovernor:
    """Return the global default CapacityGovernor instance."""
    return DEFAULT_GOVERNOR
