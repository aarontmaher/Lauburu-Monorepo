"""
compute_broker.py — Idle Mesh NPU/RAM/Bandwidth Detection & Reserve Pricing Engine.

Governs Feature F12/F13 Surplus Compute Brokering:
1. Dynamic 7-Layer Mesh Capacity Detection:
   - Scans L1 (Mac Mini M4 Pro), L2 (MacBook Pro TB4), L3 (Linux Head Node),
     L4 (Linux Tablet), L5 (MacBook Air M4), L6 (Pixel 10 Pro XL Tensor G5 NPU),
     L7 (Samsung S20 Exynos NPU), and GW (GL.iNet Router).
2. Dynamic Reserve & Floor Pricing Math:
   - Calculates base compute unit value in Lauburu Compute Tokens (LCT) and AUD fiat equivalent.
   - Adjusts for NPU TOPS, VRAM headroom, connection latency (TB4 DMA vs Wi-Fi),
     battery state, thermal throttling, and mesh congestion index.
3. Compute Slice Packaging:
   - Standardizes surplus compute capacity into `surplus_compute` asset payloads
     conforming to the canonical schema.

Authoritative Reference: ORIGINAL_REQUEST.md § R7 & PROJECT.md Feature F12.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .asset_packager import (
    AssetPackager,
    MonetizationSpec,
    ProvenanceSpec,
    TechnicalSpec,
)


# ---------------------------------------------------------------------------
# 7-Layer Physical Mesh Topology Specifications
# ---------------------------------------------------------------------------

@dataclass
class MeshNodeSpec:
    layer: str
    name: str
    ip: str
    total_ram_mb: float
    ai_cap_mb: float
    npu_tops: float
    vram_headroom_gb: float
    bandwidth_gbps: float
    arch: str
    is_battery: bool = False
    is_online: bool = True
    active_load_pct: float = 0.0
    temperature_c: float = 45.0

    @property
    def free_vram_gb(self) -> float:
        allocated = (self.active_load_pct / 100.0) * self.vram_headroom_gb
        return max(0.0, self.vram_headroom_gb - allocated)

    @property
    def available_npu_tops(self) -> float:
        if self.npu_tops <= 0.0:
            return 0.0
        allocated = (self.active_load_pct / 100.0) * self.npu_tops
        return max(0.0, self.npu_tops - allocated)


CANONICAL_MESH_NODES: Dict[str, MeshNodeSpec] = {
    "GW": MeshNodeSpec(
        layer="GW",
        name="GL_iNet_Router",
        ip="192.168.8.1",
        total_ram_mb=1024.0,
        ai_cap_mb=300.0,
        npu_tops=0.0,
        vram_headroom_gb=0.3,
        bandwidth_gbps=1.0,
        arch="arm64",
        is_battery=False,
    ),
    "L1": MeshNodeSpec(
        layer="L1",
        name="Mac_Node",
        ip="192.168.8.230",
        total_ram_mb=24576.0,
        ai_cap_mb=22118.4,
        npu_tops=38.0,
        vram_headroom_gb=21.6,
        bandwidth_gbps=1.0,
        arch="arm64",
        is_battery=False,
    ),
    "L2": MeshNodeSpec(
        layer="L2",
        name="MacBook_Pro",
        ip="192.168.8.127",
        total_ram_mb=16384.0,
        ai_cap_mb=14336.0,
        npu_tops=18.0,
        vram_headroom_gb=14.0,
        bandwidth_gbps=10.0,  # 10Gbps Thunderbolt 4 DMA
        arch="arm64",
        is_battery=True,
    ),
    "L3": MeshNodeSpec(
        layer="L3",
        name="Linux_Head_Node",
        ip="192.168.8.224",
        total_ram_mb=16384.0,
        ai_cap_mb=13107.2,
        npu_tops=0.0,
        vram_headroom_gb=13.8,
        bandwidth_gbps=1.0,
        arch="x86_64",
        is_battery=False,
    ),
    "L4": MeshNodeSpec(
        layer="L4",
        name="Linux_Tablet",
        ip="100.81.92.125",
        total_ram_mb=8192.0,
        ai_cap_mb=6144.0,
        npu_tops=0.0,
        vram_headroom_gb=6.5,
        bandwidth_gbps=0.5,
        arch="x86_64",
        is_battery=True,
    ),
    "L5": MeshNodeSpec(
        layer="L5",
        name="MacBook_Air",
        ip="192.168.8.222",
        total_ram_mb=16384.0,
        ai_cap_mb=14336.0,
        npu_tops=38.0,
        vram_headroom_gb=14.0,
        bandwidth_gbps=1.0,
        arch="arm64",
        is_battery=True,
    ),
    "L6": MeshNodeSpec(
        layer="L6",
        name="Pixel_10_Pro_XL",
        ip="100.73.38.87",
        total_ram_mb=16384.0,
        ai_cap_mb=12800.0,
        npu_tops=45.0,  # Google Tensor G5 Edge TPU
        vram_headroom_gb=12.5,
        bandwidth_gbps=0.8,
        arch="arm64",
        is_battery=True,
    ),
    "L7": MeshNodeSpec(
        layer="L7",
        name="Samsung_S20",
        ip="100.84.40.95",
        total_ram_mb=12288.0,
        ai_cap_mb=9216.0,
        npu_tops=15.0,  # Exynos 990 NPU
        vram_headroom_gb=9.0,
        bandwidth_gbps=0.5,
        arch="arm64",
        is_battery=True,
    ),
}


# ---------------------------------------------------------------------------
# Compute Slice Data Model
# ---------------------------------------------------------------------------

@dataclass
class ComputeSlice:
    slice_id: str
    node_layer: str
    node_name: str
    npu_tops: float
    vram_headroom_gb: float
    max_lease_duration_sec: int
    bandwidth_gbps: float
    arch: str
    pricing: MonetizationSpec
    created_at_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    def to_claim_payload(self) -> bytes:
        """Serializes compute lease claim token for cryptographic signing."""
        claim_data = {
            "slice_id": self.slice_id,
            "node_layer": self.node_layer,
            "node_name": self.node_name,
            "npu_tops": self.npu_tops,
            "vram_headroom_gb": self.vram_headroom_gb,
            "max_lease_duration_sec": self.max_lease_duration_sec,
            "bandwidth_gbps": self.bandwidth_gbps,
            "floor_price_lct": self.pricing.floor_price_lct,
            "suggested_price_lct": self.pricing.suggested_price_lct,
            "created_at_utc": self.created_at_utc,
        }
        return json.dumps(claim_data, sort_keys=True).encode("utf-8")


# ---------------------------------------------------------------------------
# Compute Broker Implementation
# ---------------------------------------------------------------------------

class ComputeBroker:
    """
    Scans the 7-layer mesh for surplus NPU/VRAM/bandwidth cycles,
    computes reserve pricing, and packages monetizable compute slices.
    """

    # 1 LCT (Lauburu Compute Token) ≈ 1.50 AUD fiat equivalent
    LCT_TO_AUD_RATE = 1.50

    def __init__(
        self,
        nodes: Optional[Dict[str, MeshNodeSpec]] = None,
        packager: Optional[AssetPackager] = None,
    ):
        self.nodes = dict(nodes) if nodes else {k: MeshNodeSpec(**asdict(v)) for k, v in CANONICAL_MESH_NODES.items()}
        self.packager = packager or AssetPackager()

    def update_node_status(
        self,
        layer: str,
        active_load_pct: Optional[float] = None,
        is_online: Optional[bool] = None,
        temperature_c: Optional[float] = None,
    ) -> None:
        """Updates real-time telemetry metrics for a mesh node."""
        if layer not in self.nodes:
            raise KeyError(f"Unknown mesh layer '{layer}'")
        node = self.nodes[layer]
        if active_load_pct is not None:
            node.active_load_pct = max(0.0, min(100.0, active_load_pct))
        if is_online is not None:
            node.is_online = bool(is_online)
        if temperature_c is not None:
            node.temperature_c = float(temperature_c)

    def calculate_reserve_pricing(
        self,
        node: MeshNodeSpec,
        lease_duration_sec: int = 3600,
        min_vram_gb: float = 1.0,
    ) -> MonetizationSpec:
        """
        Calculates dynamic reserve floor and suggested pricing for compute lease.
        
        Pricing Formula:
        Base Compute Value = (NPU_TOPS * w_npu) + (VRAM_GB * w_vram) + (BW_Gbps * w_bw)
        Floor Price (LCT/hr) = Base * Multipliers
        Multipliers:
          - Battery drain factor (1.25x if battery powered to offset battery degradation)
          - Thermal factor (1.50x if throttling > 75C)
          - TB4 Ultra-low latency premium (1.20x if 10Gbps TB4 DMA)
        """
        w_npu = 0.50   # 0.50 LCT per TOPS/hr
        w_vram = 1.00  # 1.00 LCT per GB VRAM/hr
        w_bw = 0.80    # 0.80 LCT per Gbps bandwidth/hr

        effective_tops = node.available_npu_tops
        effective_vram = node.free_vram_gb
        effective_bw = node.bandwidth_gbps

        raw_hourly_value = (
            (effective_tops * w_npu)
            + (max(min_vram_gb, effective_vram) * w_vram)
            + (effective_bw * w_bw)
        )

        # Multipliers
        multiplier = 1.0
        if node.is_battery:
            multiplier *= 1.25
        if node.temperature_c > 75.0:
            multiplier *= 1.50
        if node.bandwidth_gbps >= 10.0:  # TB4 DMA ultra-fast link
            multiplier *= 1.20

        floor_price_lct = round(raw_hourly_value * multiplier, 2)
        # Ensure minimum floor price
        floor_price_lct = max(1.0, floor_price_lct)

        # Suggested price has a margin of 1.5x - 2.0x over floor
        suggested_price_lct = round(floor_price_lct * 1.75, 2)

        # Fiat equivalent
        fiat_aud = round(suggested_price_lct * self.LCT_TO_AUD_RATE, 2)

        return MonetizationSpec(
            pricing_model="hourly_lease",
            floor_price_lct=floor_price_lct,
            suggested_price_lct=suggested_price_lct,
            currency="LCT",
            fiat_equivalent_estimate_aud=fiat_aud,
        )

    def detect_surplus_compute(
        self,
        min_vram_gb: float = 2.0,
        max_load_pct: float = 70.0,
        max_lease_duration_sec: int = 3600,
    ) -> List[ComputeSlice]:
        """
        Discovers idle compute capacity across online mesh nodes.
        Filters nodes that have >= min_vram_gb free and load <= max_load_pct.
        """
        slices: List[ComputeSlice] = []

        for layer, node in sorted(self.nodes.items()):
            # Router itself does not sell its limited 300MB compute
            if layer == "GW":
                continue

            if not node.is_online or node.active_load_pct > max_load_pct:
                continue

            free_vram = node.free_vram_gb
            if free_vram < min_vram_gb:
                continue

            # Unique slice identifier
            slice_seed = f"{layer}_{node.name}_{free_vram}_{time.time()}".encode("utf-8")
            slice_hash = hashlib.sha256(slice_seed).hexdigest()[:12]
            slice_id = f"slice_{layer.lower()}_{slice_hash}"

            pricing = self.calculate_reserve_pricing(
                node=node,
                lease_duration_sec=max_lease_duration_sec,
                min_vram_gb=min_vram_gb,
            )

            c_slice = ComputeSlice(
                slice_id=slice_id,
                node_layer=layer,
                node_name=node.name,
                npu_tops=round(node.available_npu_tops, 1),
                vram_headroom_gb=round(free_vram, 2),
                max_lease_duration_sec=max_lease_duration_sec,
                bandwidth_gbps=node.bandwidth_gbps,
                arch=node.arch,
                pricing=pricing,
            )
            slices.append(c_slice)

        return slices

    def package_compute_slice(
        self,
        c_slice: ComputeSlice,
        discovering_agent_id: str = "smolagi_router_gw",
        verification_run_id: Optional[str] = None,
        merkle_state_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Packages a ComputeSlice into a standardized `surplus_compute` asset payload.
        """
        raw_claim = c_slice.to_claim_payload()
        v_run_id = verification_run_id or f"vr_compute_{c_slice.slice_id}"
        m_root = merkle_state_root or hashlib.sha256(raw_claim).hexdigest()

        title = f"Surplus Compute Lease: {c_slice.node_name} ({c_slice.node_layer})"
        description = (
            f"Idle compute slice on {c_slice.node_name} ({c_slice.node_layer}). "
            f"Allocates {c_slice.vram_headroom_gb} GB VRAM and {c_slice.npu_tops} NPU TOPS "
            f"at {c_slice.bandwidth_gbps} Gbps bandwidth for up to {c_slice.max_lease_duration_sec}s."
        )

        tech_spec = TechnicalSpec(
            target_architecture=[c_slice.arch],
            runtime_environment="opencl_metal_ray",
            ram_footprint_mb=float(c_slice.vram_headroom_gb * 1024.0),
            compute_specs={
                "node_identifier": c_slice.node_name,
                "node_layer": c_slice.node_layer,
                "npu_tops_available": c_slice.npu_tops,
                "vram_headroom_gb": c_slice.vram_headroom_gb,
                "max_lease_duration_sec": c_slice.max_lease_duration_sec,
                "bandwidth_gbps": c_slice.bandwidth_gbps,
            },
        )

        provenance = ProvenanceSpec(
            discovering_agent_id=discovering_agent_id,
            timestamp_utc=c_slice.created_at_utc,
            verification_run_id=v_run_id,
            merkle_state_root=m_root,
        )

        return self.packager.package_asset(
            asset_type="surplus_compute",
            title=title,
            description=description,
            version="1.0.0",
            tags=["surplus_compute", "mesh_lease", c_slice.node_layer.lower(), c_slice.arch],
            technical_spec=tech_spec,
            monetization=c_slice.pricing,
            provenance=provenance,
            raw_content=raw_claim,
            content_encoding="raw_text_json",
        )
