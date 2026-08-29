"""
Spatial Grappling 3D Data Models.
=================================
Subsystem: 01_apps/user_facing_and_scaling/spatial_grappling_3d/core/models.py
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class MediaPipeLandmark:
    id: int
    name: str
    body_part: str
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    visibility: float = 1.0

@dataclass
class GrapplingNode:
    id: str
    text: str
    category: str
    depth: int
    parent_id: str
    x: float
    y: float
    z: float
    has_children: bool = False
    attributes: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BiomechanicalTransition:
    from_node: str
    to_node: str
    relationship: str = "hierarchical_transition"
    torque_cost_nm: float = 0.0

@dataclass
class JointTorqueResult:
    joint_name: str
    angle_deg: float
    torque_nm: float
    safe_limit_nm: float
    is_safe: bool

@dataclass
class KinematicPose:
    timestamp_utc: str
    active_position: str
    landmarks: List[MediaPipeLandmark]
    joint_torques: Dict[str, float]
    tatami_center_distance_m: float
    is_ground_pinned: bool

@dataclass
class TatamiWorldState:
    total_nodes: int
    total_transitions: int
    active_node_id: str
    categories_breakdown: Dict[str, int]
    kinematic_pose: Optional[KinematicPose] = None
