#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit & Integration Test Suite: 3D Spatial Grappling Kinematics & OPML World Model
================================================================================
Test Target: 01_apps/spatial_and_3d/spatial_grappling_3d/
Subsystem: 01_apps/spatial_and_3d / 10_spatial_grappling_kinematics
Covers:
- Feature 10: 3,044-Node Martial OPML Tree Parser & Cylindrical Tatami Canvas (10m x 10m)
- Feature 11: MediaPipe 33-Landmark Biomechanical Skeleton Mapping Across Anatomical Regions
- Feature 12: Analytical Joint Torque Safety Solver (tau = F * r * sin(theta)) & Danger Limits
- Interface Contract: SpatialGrapplingMapEngine.parse_opml(path) -> List[GrapplingNode]
- Interface Contract: compute_joint_torque(force, lever_arm, angle_rad) -> JointTorqueResult
Rule #0 Compliance: 100% genuine trigonometry and OPML XML parsing, zero mock facades.
"""

import math
import sys
import tempfile
import unittest
from pathlib import Path

# Add spatial_and_3d to sys.path
TEST_DIR = Path(__file__).resolve().parent
SPATIAL_DIR = TEST_DIR.parent
REPO_ROOT = SPATIAL_DIR.parent.parent
for p in [str(REPO_ROOT), str(SPATIAL_DIR), str(SPATIAL_DIR.parent)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from spatial_grappling_3d.core.config import SpatialGrapplingConfig
from spatial_grappling_3d.core.models import (
    GrapplingNode,
    JointTorqueResult,
    MediaPipeLandmark,
)
from spatial_grappling_3d.kinematics.engine import SpatialGrapplingMapEngine
from spatial_grappling_3d.kinematics.opml_tree import parse_opml_tree
from spatial_grappling_3d.kinematics.skeleton import (
    MEDIAPIPE_33_LANDMARKS,
    build_default_pose,
)
from spatial_grappling_3d.kinematics.torque import (
    ANATOMICAL_REGIONS,
    JOINT_LIMITS_NM,
    compute_joint_torque,
    evaluate_joint_safety,
)


class TestOPMLTreeParserAndProjection(unittest.TestCase):
    """Test suite for 3,044-node OPML parser and cylindrical 10m x 10m tatami projection."""

    def setUp(self):
        # Locate authentic repository OPML files
        candidates = [
            REPO_ROOT / "webapp" / "grappling.opml",
            REPO_ROOT / "01_apps" / "spatial_and_3d" / "grapplingmap_web" / "grappling.opml",
            REPO_ROOT / "10_spatial_grappling_kinematics" / "opml_trees" / "grappling.opml",
        ]
        self.opml_file = next((p for p in candidates if p.exists()), None)

    def test_authentic_opml_file_exists(self):
        """Authentic 3,044-node OPML file must exist in the monorepo."""
        self.assertIsNotNone(self.opml_file, "At least one authentic grappling.opml file must exist.")

    def test_parse_3044_nodes_exact_count(self):
        """Parses exactly 3,044 technique nodes and hierarchical transitions."""
        if not self.opml_file:
            self.skipTest("grappling.opml file not found in test environment.")

        nodes, transitions, categories = parse_opml_tree(self.opml_file)

        self.assertEqual(len(nodes), 3044, "Must parse exactly 3,044 technique nodes.")
        self.assertEqual(len(transitions), 3043, "Tree of 3,044 nodes must have 3,043 parent-child transitions.")
        self.assertGreater(len(categories), 50, "Must identify rich categorization across martial disciplines.")

    def test_cylindrical_tatami_projection_bounds(self):
        """All projected node coordinates must lie within the 10m x 10m tatami canvas (radius <= 5.0m)."""
        if not self.opml_file:
            self.skipTest("grappling.opml file not found.")

        nodes, _, _ = parse_opml_tree(self.opml_file)

        for n in nodes:
            r = math.sqrt(n.x ** 2 + n.y ** 2)
            self.assertLessEqual(r, 5.0, f"Node {n.id} radius {r:.2f}m exceeds 5.0m tatami boundary.")
            self.assertGreaterEqual(n.z, 0.0, f"Node {n.id} height z={n.z} must be non-negative above tatami.")

    def test_missing_opml_file_raises_error(self):
        """Rule #0: Missing OPML path raises FileNotFoundError without fabricating dummy data."""
        with self.assertRaises(FileNotFoundError):
            parse_opml_tree(Path("/non/existent/path/to/martial.opml"))

    def test_malformed_opml_xml_raises_error(self):
        """Rule #0: Malformed XML OPML raises ValueError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".opml", delete=False) as tf:
            tf.write("<opml><head></head></opml>")  # Missing <body>
            tf_path = Path(tf.name)

        try:
            with self.assertRaises(ValueError):
                parse_opml_tree(tf_path)
        finally:
            tf_path.unlink(missing_ok=True)


class TestMediaPipe33SkeletonTopology(unittest.TestCase):
    """Test suite for MediaPipe 33-landmark skeleton mapper across anatomical regions."""

    def test_mediapipe_33_landmarks_integrity(self):
        """Verifies 33 unique anatomical landmarks spanning 6 anatomical regions."""
        self.assertEqual(len(MEDIAPIPE_33_LANDMARKS), 33)

        ids = [lm["id"] for lm in MEDIAPIPE_33_LANDMARKS]
        names = [lm["name"] for lm in MEDIAPIPE_33_LANDMARKS]
        parts = {lm["body_part"] for lm in MEDIAPIPE_33_LANDMARKS}

        self.assertEqual(ids, list(range(33)))
        self.assertEqual(len(set(names)), 33)
        self.assertTrue({"HEAD", "TORSO", "PELVIS"}.issubset(parts))

    def test_ground_vs_standing_pose_heights(self):
        """Ground positions (Closed Guard, Mount) have lower baseline z/y than standing poses."""
        ground_landmarks = build_default_pose("Closed Guard")
        standing_landmarks = build_default_pose("Standing Takedown")

        self.assertEqual(len(ground_landmarks), 33)
        self.assertEqual(len(standing_landmarks), 33)

        ground_nose = next(lm for lm in ground_landmarks if lm.name == "NOSE")
        standing_nose = next(lm for lm in standing_landmarks if lm.name == "NOSE")

        self.assertLess(ground_nose.y, standing_nose.y)


class TestJointTorqueAnalyticalSolver(unittest.TestCase):
    """Test suite for analytical joint torque solver tau = F * r * sin(theta) & safety limits."""

    def test_torque_perpendicular_force_maximum(self):
        """Perpendicular force (theta = 90 deg / pi/2 rad) produces maximum torque tau = F * r."""
        force = 120.0
        lever_arm = 0.35
        angle_rad = math.pi / 2.0  # 90 degrees

        res = compute_joint_torque(force=force, lever_arm=lever_arm, angle_rad=angle_rad, joint_name="right_elbow")

        self.assertIsInstance(res, JointTorqueResult)
        expected_torque = round(120.0 * 0.35 * 1.0, 2)  # 42.00 N*m
        self.assertAlmostEqual(res.torque_nm, expected_torque, places=2)
        self.assertEqual(res.angle_deg, 90.0)
        self.assertTrue(res.is_safe)  # 42.00 <= 45.00 limit

    def test_torque_zero_at_zero_angle(self):
        """Zero angle (theta = 0 deg) produces 0.0 N*m torque."""
        res = compute_joint_torque(force=120.0, lever_arm=0.35, angle_rad=0.0, joint_name="right_elbow")
        self.assertEqual(res.torque_nm, 0.0)
        self.assertTrue(res.is_safe)

    def test_critical_danger_hyperextension_threshold(self):
        """Excessive force/extension exceeding joint limit triggers is_safe=False."""
        # Armbar hyperextension: 200 N force at 90 deg -> 70 N*m > 45 N*m elbow limit
        res = compute_joint_torque(force=200.0, lever_arm=0.35, angle_rad=math.pi / 2.0, joint_name="right_elbow")

        self.assertEqual(res.torque_nm, 70.0)
        self.assertEqual(res.safe_limit_nm, 45.0)
        self.assertFalse(res.is_safe)

    def test_cervical_spine_low_threshold_safety(self):
        """Cervical spine has low tolerance (30 N*m) and flags guillotine/can-opener strain."""
        # 120 N force at 90 deg on neck -> 42.0 N*m > 30.0 N*m limit
        res = compute_joint_torque(force=120.0, lever_arm=0.35, angle_rad=math.pi / 2.0, joint_name="cervical_spine")

        self.assertFalse(res.is_safe)
        self.assertEqual(res.safe_limit_nm, 30.0)

    def test_vectorized_multi_joint_safety_evaluation(self):
        """Evaluates torque dictionary and flags dangerous joints across regions."""
        joint_angles = {
            "right_elbow": 90.0,       # 120 * 0.35 * 1.0 = 42.0 N*m <= 45.0 (SAFE)
            "cervical_spine": 90.0,    # 120 * 0.35 * 1.0 = 42.0 N*m > 30.0 (DANGER)
            "right_knee": 45.0,        # 120 * 0.35 * 0.707 = 29.7 N*m <= 110.0 (SAFE)
            "lumbar_spine": 90.0,      # 120 * 0.35 * 1.0 = 42.0 N*m <= 120.0 (SAFE)
        }

        torques_dict = compute_joint_torque(joint_angles, lever_arm_m=0.35, force_n=120.0)
        safety_evals = evaluate_joint_safety(torques_dict)

        self.assertEqual(len(safety_evals), 4)
        cervical_eval = next(e for e in safety_evals if e.joint_name == "cervical_spine")
        elbow_eval = next(e for e in safety_evals if e.joint_name == "right_elbow")

        self.assertFalse(cervical_eval.is_safe)
        self.assertTrue(elbow_eval.is_safe)


class TestSpatialGrapplingEngineIntegration(unittest.TestCase):
    """Test suite for full SpatialGrapplingMapEngine integration and interface contracts."""

    def setUp(self):
        candidates = [
            REPO_ROOT / "webapp" / "grappling.opml",
            REPO_ROOT / "01_apps" / "spatial_and_3d" / "grapplingmap_web" / "grappling.opml",
        ]
        self.opml_file = next((p for p in candidates if p.exists()), None)
        self.engine = SpatialGrapplingMapEngine(opml_path=self.opml_file)

    def test_parse_opml_interface_contract(self):
        """parse_opml returns List[GrapplingNode] matching PROJECT.md interface contract."""
        if not self.opml_file:
            self.skipTest("grappling.opml not available.")

        nodes = self.engine.parse_opml(str(self.opml_file))
        self.assertEqual(len(nodes), 3044)
        self.assertIsInstance(nodes[0], GrapplingNode)

    def test_parse_full_opml_tree_payload(self):
        """parse_full_opml_tree returns complete structured graph payload with kinematics."""
        if not self.opml_file:
            self.skipTest("grappling.opml not available.")

        payload = self.engine.parse_full_opml_tree()

        self.assertEqual(payload["total_nodes"], 3044)
        self.assertEqual(payload["total_transitions"], 3043)
        self.assertIn("categories_breakdown", payload)
        self.assertIn("mediapipe_skeleton", payload)
        self.assertIn("joint_torques_nm", payload)
        self.assertEqual(payload["mediapipe_skeleton"]["total_landmarks"], 33)


if __name__ == "__main__":
    unittest.main()
