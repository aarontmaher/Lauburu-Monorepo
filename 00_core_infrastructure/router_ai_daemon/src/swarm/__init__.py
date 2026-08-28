"""
src/swarm — Hyper-Speed Shadow Swarm Orchestration & Specialist Taxonomy.

Exports specialist registry, dynamic capacity governor, swarm lifecycle controller,
and associated data schemas.
Authoritative Specifications: ORIGINAL_REQUEST.md §R3 & PROJECT.md §F5, §F6.
"""

from src.swarm.capacity_governor import (
    CANONICAL_MESH_MATRIX,
    CapacityGovernor,
    CapacityReport,
    MeshNodeSpec,
    ScalePlan,
    DEFAULT_GOVERNOR,
    get_capacity_governor,
)
from src.swarm.specialist_registry import (
    CANONICAL_SPECIALISTS,
    SpecialistRegistry,
    SpecialistSpec,
    DEFAULT_REGISTRY,
    get_specialist_registry,
)
from src.swarm.swarm_controller import (
    SwarmController,
    SwarmScaleResult,
    TaskDispatchResult,
    WorkerInstance,
    DEFAULT_CONTROLLER,
    get_swarm_controller,
)

__all__ = [
    # Specialist Registry
    "SpecialistSpec",
    "SpecialistRegistry",
    "CANONICAL_SPECIALISTS",
    "DEFAULT_REGISTRY",
    "get_specialist_registry",
    # Capacity Governor
    "MeshNodeSpec",
    "CapacityReport",
    "ScalePlan",
    "CapacityGovernor",
    "CANONICAL_MESH_MATRIX",
    "DEFAULT_GOVERNOR",
    "get_capacity_governor",
    # Swarm Controller
    "WorkerInstance",
    "SwarmScaleResult",
    "TaskDispatchResult",
    "SwarmController",
    "DEFAULT_CONTROLLER",
    "get_swarm_controller",
]
