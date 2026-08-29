"""
Canonical Port 9-Screen NOC & Stability Command Suite.
======================================================
Subsystem: 01_apps/operator_and_dev/canonical_port
Version: 1.0.0-CANONICAL

9-Screen stability command hierarchy monitoring 7 physical mesh nodes,
108GB RAM pool with 82.8GB usable AI VRAM, AI Debate Council, and
Tri-Vault storage invariants.

Subpackages:
- core: Config, data models, state store
- nodes: 7 physical mesh node registry and hardware pool governor
- debate: 4-party AI debate council and genetic router
- views: 9-screen stability hierarchy and dashboard runner
- presentation: TUI presentation adapters
"""

from .core import (
    CanonicalPortConfig,
    MeshNodeInfo,
    StabilityScreenInfo,
    DebateSpeaker,
    DebateCouncilState,
    CanonicalStateStore,
)
from .nodes import (
    MESH_NODES,
    get_hardware_pool_summary,
)
from .debate import (
    DebateCouncilEngine,
    AIDebateRouter,
)
from .views import (
    STABILITY_SCREENS,
    CanonicalPortDashboard,
    run_canonical,
)

__version__ = "1.0.0"

__all__ = [
    "__version__",
    "CanonicalPortConfig",
    "MeshNodeInfo",
    "StabilityScreenInfo",
    "DebateSpeaker",
    "DebateCouncilState",
    "CanonicalStateStore",
    "MESH_NODES",
    "get_hardware_pool_summary",
    "DebateCouncilEngine",
    "AIDebateRouter",
    "STABILITY_SCREENS",
    "CanonicalPortDashboard",
    "run_canonical",
]
