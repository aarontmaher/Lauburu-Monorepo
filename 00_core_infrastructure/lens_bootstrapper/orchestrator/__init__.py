"""
00_core_infrastructure/lens_bootstrapper/orchestrator/__init__.py
=================================================================
Milestone 3: Global Prima.cpp Mesh Layer Sharding & Dynamic Rebalancer.

Exports:
- PrimaMeshOrchestrator: Dynamic 7-device physics-aware layer allocator and PRP parameter generator.
- PrimaMeshAllocator: Compatibility alias for PrimaMeshOrchestrator.
- ThermalRebalancer: Sub-100ms thermal spike detector, peer evacuator, and JSON config emitter.
- MeshNodeProfile: Data structure representing physical mesh node parameters.
"""

from .prima_mesh_orchestrator import (
    PrimaMeshOrchestrator,
    PrimaMeshAllocator,
    MeshNodeProfile,
)
from .thermal_rebalancer import ThermalRebalancer

__all__ = [
    "PrimaMeshOrchestrator",
    "PrimaMeshAllocator",
    "ThermalRebalancer",
    "MeshNodeProfile",
]
