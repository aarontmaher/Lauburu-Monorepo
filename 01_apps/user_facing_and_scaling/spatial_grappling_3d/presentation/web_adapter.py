"""
Spatial Grappling Web Adapter.
==============================
Subsystem: 01_apps/user_facing_and_scaling/spatial_grappling_3d/presentation/web_adapter.py
"""

from typing import Dict, Any
from ..kinematics.engine import SpatialGrapplingMapEngine

class SpatialGrapplingWebAdapter:
    """Provides Web-TUI and REST/WebGL endpoints for 3D Tatami Kinematics."""

    def __init__(self, engine: SpatialGrapplingMapEngine):
        self.engine = engine

    def get_tatami_graph(self) -> Dict[str, Any]:
        """Returns 3D node coordinates, skeleton, and category breakdown."""
        return self.engine.parse_full_opml_tree()

    def get_active_pose(self) -> Dict[str, Any]:
        """Returns active kinematic pose and torque calculations."""
        return {
            "active_position": self.engine.active_position,
            "joint_torques_nm": self.engine.compute_joint_torque({"right_elbow": 18.5, "left_shoulder": 24.0})
        }
