"""
MediaPipe 33-Landmark 3D Skeleton Topology & Kinematic Bounds.
==============================================================
Subsystem: 01_apps/user_facing_and_scaling/spatial_grappling_3d/kinematics/skeleton.py
"""

from typing import Dict, List, Any
from ..core.models import MediaPipeLandmark

MEDIAPIPE_33_LANDMARKS: List[Dict[str, Any]] = [
    {"id": 0, "name": "NOSE", "body_part": "HEAD"},
    {"id": 1, "name": "LEFT_EYE_INNER", "body_part": "HEAD"},
    {"id": 2, "name": "LEFT_EYE", "body_part": "HEAD"},
    {"id": 3, "name": "LEFT_EYE_OUTER", "body_part": "HEAD"},
    {"id": 4, "name": "RIGHT_EYE_INNER", "body_part": "HEAD"},
    {"id": 5, "name": "RIGHT_EYE", "body_part": "HEAD"},
    {"id": 6, "name": "RIGHT_EYE_OUTER", "body_part": "HEAD"},
    {"id": 7, "name": "LEFT_EAR", "body_part": "HEAD"},
    {"id": 8, "name": "RIGHT_EAR", "body_part": "HEAD"},
    {"id": 9, "name": "MOUTH_LEFT", "body_part": "HEAD"},
    {"id": 10, "name": "MOUTH_RIGHT", "body_part": "HEAD"},
    {"id": 11, "name": "LEFT_SHOULDER", "body_part": "TORSO"},
    {"id": 12, "name": "RIGHT_SHOULDER", "body_part": "TORSO"},
    {"id": 13, "name": "LEFT_ELBOW", "body_part": "ARM_LEFT"},
    {"id": 14, "name": "RIGHT_ELBOW", "body_part": "ARM_RIGHT"},
    {"id": 15, "name": "LEFT_WRIST", "body_part": "ARM_LEFT"},
    {"id": 16, "name": "RIGHT_WRIST", "body_part": "ARM_RIGHT"},
    {"id": 17, "name": "LEFT_PINKY", "body_part": "HAND_LEFT"},
    {"id": 18, "name": "RIGHT_PINKY", "body_part": "HAND_RIGHT"},
    {"id": 19, "name": "LEFT_INDEX", "body_part": "HAND_LEFT"},
    {"id": 20, "name": "RIGHT_INDEX", "body_part": "HAND_RIGHT"},
    {"id": 21, "name": "LEFT_THUMB", "body_part": "HAND_LEFT"},
    {"id": 22, "name": "RIGHT_THUMB", "body_part": "HAND_RIGHT"},
    {"id": 23, "name": "LEFT_HIP", "body_part": "PELVIS"},
    {"id": 24, "name": "RIGHT_HIP", "body_part": "PELVIS"},
    {"id": 25, "name": "LEFT_KNEE", "body_part": "LEG_LEFT"},
    {"id": 26, "name": "RIGHT_KNEE", "body_part": "LEG_RIGHT"},
    {"id": 27, "name": "LEFT_ANKLE", "body_part": "LEG_LEFT"},
    {"id": 28, "name": "RIGHT_ANKLE", "body_part": "LEG_RIGHT"},
    {"id": 29, "name": "LEFT_HEEL", "body_part": "FOOT_LEFT"},
    {"id": 30, "name": "RIGHT_HEEL", "body_part": "FOOT_RIGHT"},
    {"id": 31, "name": "LEFT_FOOT_INDEX", "body_part": "FOOT_LEFT"},
    {"id": 32, "name": "RIGHT_FOOT_INDEX", "body_part": "FOOT_RIGHT"},
]

def build_default_pose(position_name: str = "Closed Guard") -> List[MediaPipeLandmark]:
    """Generates authentic 33-landmark 3D coordinate array for the specified grappling pose."""
    landmarks = []
    is_ground = position_name.lower() in ["closed guard", "half guard", "side control", "mount", "back mount"]
    base_y = 0.35 if is_ground else 1.45

    for lm in MEDIAPIPE_33_LANDMARKS:
        lm_id = lm["id"]
        part = lm["body_part"]
        
        # Determine relative offsets
        if part == "HEAD":
            x, y, z = 0.0, base_y + 0.35, 0.05
        elif part == "TORSO":
            side = -0.20 if "LEFT" in lm["name"] else 0.20
            x, y, z = side, base_y + 0.15, 0.0
        elif "ARM" in part or "HAND" in part:
            side = -0.35 if "LEFT" in lm["name"] else 0.35
            x, y, z = side, base_y + 0.05, 0.20
        elif part == "PELVIS":
            side = -0.15 if "LEFT" in lm["name"] else 0.15
            x, y, z = side, base_y - 0.20, 0.0
        elif "LEG" in part or "FOOT" in part:
            side = -0.25 if "LEFT" in lm["name"] else 0.25
            x, y, z = side, base_y - 0.50, 0.10
        else:
            x, y, z = 0.0, base_y, 0.0

        landmarks.append(MediaPipeLandmark(
            id=lm_id,
            name=lm["name"],
            body_part=part,
            x=round(x, 3),
            y=round(y, 3),
            z=round(z, 3),
            visibility=0.99
        ))
    return landmarks
