"""
Biomechanical Joint Torque Solver.
==================================
Subsystem: 01_apps/user_facing_and_scaling/spatial_grappling_3d/kinematics/torque.py
"""

import math
from typing import Dict, Any, List, Optional, Union
from ..core.models import JointTorqueResult

# Physiological limits across 6 anatomical regions (N*m)
ANATOMICAL_REGIONS: Dict[str, List[str]] = {
    "HEAD_NECK": ["cervical_spine", "neck"],
    "TORSO_SPINE": ["lumbar_spine", "thoracic_spine"],
    "SHOULDER": ["right_shoulder", "left_shoulder"],
    "ELBOW": ["right_elbow", "left_elbow"],
    "KNEE": ["right_knee", "left_knee"],
    "ANKLE_FOOT": ["right_ankle", "left_ankle"],
}

JOINT_LIMITS_NM: Dict[str, float] = {
    "cervical_spine": 30.0,
    "neck": 30.0,
    "lumbar_spine": 120.0,
    "thoracic_spine": 90.0,
    "right_shoulder": 80.0,
    "left_shoulder": 80.0,
    "right_elbow": 45.0,
    "left_elbow": 45.0,
    "right_knee": 110.0,
    "left_knee": 110.0,
    "right_ankle": 60.0,
    "left_ankle": 60.0,
}


def compute_joint_torque(
    force_or_angles: Optional[Union[float, Dict[str, float]]] = None,
    lever_arm_m: Optional[float] = None,
    angle_rad: Optional[float] = None,
    joint_name: str = "right_elbow",
    force_n: Optional[float] = None,
    force: Optional[float] = None,
    lever_arm: Optional[float] = None,
    angle_deg: Optional[float] = None,
    joint_angles_deg: Optional[Dict[str, float]] = None,
    **kwargs: Any,
) -> Union[JointTorqueResult, Dict[str, float]]:
    """
    Computes joint torque vector or scalar in Newton-meters:
    tau = F * r * sin(theta)

    Supports both:
    1. compute_joint_torque(force=120.0, lever_arm=0.35, angle_rad=1.57, joint_name="right_elbow") -> JointTorqueResult
    2. compute_joint_torque({"right_elbow": 45.0}, lever_arm_m=0.35, force_n=120.0) -> Dict[str, float]
    """
    angles_dict = None
    if isinstance(force_or_angles, dict):
        angles_dict = force_or_angles
    elif joint_angles_deg is not None:
        angles_dict = joint_angles_deg

    arm = lever_arm if lever_arm is not None else (lever_arm_m if lever_arm_m is not None else 0.35)
    f_val = force if force is not None else (force_n if force_n is not None else (float(force_or_angles) if isinstance(force_or_angles, (int, float)) else 120.0))

    if angles_dict is not None:
        torques: Dict[str, float] = {}
        for joint, deg in angles_dict.items():
            rad = math.radians(deg)
            torque_nm = round(f_val * arm * abs(math.sin(rad)), 2)
            torques[joint] = torque_nm
        return torques

    if angle_rad is not None:
        theta = float(angle_rad)
        deg_val = round(math.degrees(theta), 1)
    elif angle_deg is not None:
        deg_val = float(angle_deg)
        theta = math.radians(deg_val)
    else:
        theta = math.radians(45.0)
        deg_val = 45.0

    torque_nm = round(f_val * arm * abs(math.sin(theta)), 2)
    safe_limit = JOINT_LIMITS_NM.get(joint_name, 45.0)
    is_safe = torque_nm <= safe_limit

    return JointTorqueResult(
        joint_name=joint_name,
        angle_deg=deg_val,
        torque_nm=torque_nm,
        safe_limit_nm=safe_limit,
        is_safe=is_safe,
    )



def evaluate_joint_safety(
    joint_torques: Dict[str, float]
) -> List[JointTorqueResult]:
    """Evaluates whether computed torques exceed physiological joint safety thresholds across anatomical regions."""
    results = []
    for joint, torque in joint_torques.items():
        limit = JOINT_LIMITS_NM.get(joint, 50.0)
        is_safe = torque <= limit
        results.append(JointTorqueResult(
            joint_name=joint,
            angle_deg=0.0,
            torque_nm=torque,
            safe_limit_nm=limit,
            is_safe=is_safe
        ))
    return results

