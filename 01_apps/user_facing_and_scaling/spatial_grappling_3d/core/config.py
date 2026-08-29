"""
Spatial Grappling 3D Configuration.
===================================
Subsystem: 01_apps/user_facing_and_scaling/spatial_grappling_3d/core/config.py
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

WORKSPACE_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")

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
