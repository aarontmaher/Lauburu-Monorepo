"""
Biomechanical Joint Torque Solver.
==================================
Subsystem: 01_apps/user_facing_and_scaling/spatial_grappling_3d/kinematics/torque.py
"""

import math
from typing import Dict, Any, List
from ..core.models import JointTorqueResult

JOINT_LIMITS_NM: Dict[str, float] = {
    "right_elbow": 45.0,
    "left_elbow": 45.0,
    "right_shoulder": 80.0,
    "left_shoulder": 80.0,
    "right_knee": 110.0,
    "left_knee": 110.0,
    "cervical_spine": 30.0,
    "lumbar_spine": 120.0,
}

def compute_joint_torque(
    joint_angles_deg: Dict[str, float],
    lever_arm_m: float = 0.35,
    force_n: float = 120.0
) -> Dict[str, float]:
    """
    Computes joint torque vector in Newton-meters:
    Torque = Force (N) * lever_arm (m) * sin(theta_rad)
    """
    torques: Dict[str, float] = {}
    for joint, angle_deg in joint_angles_deg.items():
        rad = math.radians(angle_deg)
        torque_nm = round(force_n * lever_arm_m * abs(math.sin(rad)), 2)
        torques[joint] = torque_nm
    return torques

def evaluate_joint_safety(
    joint_torques: Dict[str, float]
) -> List[JointTorqueResult]:
    """Evaluates whether computed torques exceed physiological joint safety thresholds."""
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
