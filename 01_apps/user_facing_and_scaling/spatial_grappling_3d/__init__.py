"""
3D Spatial Grappling Kinematics Suite.
======================================
Subsystem: 01_apps/user_facing_and_scaling/spatial_grappling_3d
Version: 1.0.0-CANONICAL

Parses the 3,044-node OPML MindMap tree and projects MediaPipe 33-landmark 3D skeletons
and biomechanical joint torque onto a 10m x 10m tatami mat.

Subpackages:
- core: Data models, configs, world states
- kinematics: OPML parser, skeleton topology, joint torque solver, kinematics engine
- presentation: Textual TUI HUD, Web adapter, engine bridges
"""

from .core import (
    SpatialGrapplingConfig,
    MediaPipeLandmark,
    GrapplingNode,
    BiomechanicalTransition,
    JointTorqueResult,
    KinematicPose,
    TatamiWorldState,
)
from .kinematics import (
    MEDIAPIPE_33_LANDMARKS,
    build_default_pose,
    compute_joint_torque,
    evaluate_joint_safety,
    JOINT_LIMITS_NM,
    parse_opml_tree,
    SpatialGrapplingMapEngine,
)
from .presentation import (
    SpatialGrapplingApp,
    run_app,
    run_grappling,
    SpatialGrapplingWebAdapter,
)

__version__ = "1.0.0"

__all__ = [
    "__version__",
    "SpatialGrapplingConfig",
    "MediaPipeLandmark",
    "GrapplingNode",
    "BiomechanicalTransition",
    "JointTorqueResult",
    "KinematicPose",
    "TatamiWorldState",
    "MEDIAPIPE_33_LANDMARKS",
    "build_default_pose",
    "compute_joint_torque",
    "evaluate_joint_safety",
    "JOINT_LIMITS_NM",
    "parse_opml_tree",
    "SpatialGrapplingMapEngine",
    "SpatialGrapplingApp",
    "run_app",
    "run_grappling",
    "SpatialGrapplingWebAdapter",
]
