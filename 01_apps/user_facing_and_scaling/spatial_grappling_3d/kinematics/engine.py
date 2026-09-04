"""
Spatial Grappling Map Engine.
=============================
Subsystem: 01_apps/user_facing_and_scaling/spatial_grappling_3d/kinematics/engine.py
"""

import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..core.config import SpatialGrapplingConfig
from ..core.models import (
    GrapplingNode,
    BiomechanicalTransition,
    KinematicPose,
    TatamiWorldState,
)
from .skeleton import MEDIAPIPE_33_LANDMARKS, build_default_pose
from .torque import compute_joint_torque, evaluate_joint_safety
from .opml_tree import parse_opml_tree

class SpatialGrapplingMapEngine:
    """
    3D Spatial Grappling MindMap & Kinematics Engine.
    Maps 3,044 OPML technique nodes and MediaPipe 33-landmark 3D skeletons
    onto a 10m x 10m tatami canvas.
    """

    def __init__(self, opml_path: Optional[Path] = None, config: Optional[SpatialGrapplingConfig] = None):
        self.config = config or SpatialGrapplingConfig()
        if opml_path:
            self.opml_path = opml_path
        elif self.config.opml_primary_path.exists():
            self.opml_path = self.config.opml_primary_path
        else:
            self.opml_path = self.config.opml_fallback_path

        self.nodes: List[GrapplingNode] = []
        self.transitions: List[BiomechanicalTransition] = []
        self.categories_count: Dict[str, int] = {}
        self.active_position: str = "Closed Guard"

    def parse_opml(self, path: Optional[Any] = None) -> List[GrapplingNode]:
        """
        Interface Contract (PROJECT.md):
        Parses 3,044 nodes and maps to 10m x 10m tatami coordinates.
        """
        if path:
            self.opml_path = Path(path)
        self.nodes, self.transitions, self.categories_count = parse_opml_tree(self.opml_path)
        return self.nodes

    def parse_full_opml_tree(self) -> Dict[str, Any]:
        """Parses the OPML martial tree and returns structured graph payload."""
        self.nodes, self.transitions, self.categories_count = parse_opml_tree(self.opml_path)
        
        # Build live kinematic pose
        landmarks = build_default_pose(self.active_position)
        joint_torques = compute_joint_torque(
            {"right_elbow": 18.5, "left_shoulder": 24.0, "right_knee": 45.0, "cervical_spine": 12.0},
            lever_arm_m=self.config.lever_arm_default_m,
            force_n=self.config.torque_nominal_force_n
        )

        payload = {
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_opml": str(self.opml_path),
            "total_nodes": len(self.nodes),
            "total_transitions": len(self.transitions),
            "categories_breakdown": self.categories_count,
            "mediapipe_skeleton": {
                "total_landmarks": len(MEDIAPIPE_33_LANDMARKS),
                "landmarks": MEDIAPIPE_33_LANDMARKS
            },
            "active_position": self.active_position,
            "joint_torques_nm": joint_torques,
            "nodes": [
                {
                    "id": n.id,
                    "text": n.text,
                    "category": n.category,
                    "depth": n.depth,
                    "parent_id": n.parent_id,
                    "x": n.x,
                    "y": n.y,
                    "z": n.z,
                    "has_children": n.has_children,
                }
                for n in self.nodes[:250]
            ],
            "graph_summary": f"Canonical 3D Grappling Map loaded with {len(self.nodes)} nodes across {len(self.categories_count)} major sub-systems."
        }

        # Write session log
        try:
            self.config.session_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config.session_log_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception:
            pass

        return payload

    def compute_joint_torque(self, joint_angles: Dict[str, float], lever_arm_m: float = 0.35) -> Dict[str, float]:
        """Computes torque vector for joints."""
        return compute_joint_torque(joint_angles, lever_arm_m=lever_arm_m, force_n=self.config.torque_nominal_force_n)
