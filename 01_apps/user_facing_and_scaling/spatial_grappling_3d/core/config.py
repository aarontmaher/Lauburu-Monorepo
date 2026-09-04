"""
Spatial Grappling 3D Configuration.
===================================
Subsystem: 01_apps/user_facing_and_scaling/spatial_grappling_3d/core/config.py
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

# Dynamically resolve monorepo root
def _resolve_workspace_root() -> Path:
    env_root = os.environ.get("WORKSPACE_ROOT")
    if env_root and Path(env_root).exists():
        return Path(env_root)
    current = Path(__file__).resolve()
    for parent in [current.parents[4], current.parents[3], current.parents[2], Path.cwd()]:
        if parent.exists() and (parent / "PROJECT.md").exists():
            return parent
    return Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")

WORKSPACE_ROOT = _resolve_workspace_root()

@dataclass
class SpatialGrapplingConfig:
    tatami_width_m: float = 10.0
    tatami_length_m: float = 10.0
    tatami_boundary_m: float = 1.0
    camera_default_pos: Tuple[float, float, float] = (0.0, 5.0, 12.0)
    camera_fov_deg: float = 60.0
    opml_primary_path: Path = WORKSPACE_ROOT / "webapp/grappling.opml"
    opml_fallback_path: Path = WORKSPACE_ROOT / "01_apps/spatial_and_3d/grapplingmap_web/grappling.opml"
    session_log_path: Path = WORKSPACE_ROOT / "session_logs/spatial_grappling_map.json"
    fps_target: int = 120
    torque_nominal_force_n: float = 120.0
    lever_arm_default_m: float = 0.35

