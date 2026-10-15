#!/opt/homebrew/bin/python3
# -*- coding: utf-8 -*-
"""
Unit Test Suite for Polar H10 Host-Side Edge AI Inference Pipeline
Target: 03_biometrics_and_telemetry/polar_h10_edge_ai.py
"""

import sys
import unittest
from pathlib import Path
import numpy as np

# Ensure root of biometrics module is in sys.path
BIOMETRICS_DIR = Path(__file__).resolve().parent.parent
if str(BIOMETRICS_DIR) not in sys.path:
    sys.path.insert(0, str(BIOMETRICS_DIR))

import polar_h10_edge_ai as polar


class TestPolarH10EdgeAI(unittest.TestCase):
    """Test suite for Polar H10 physiological feature extraction and INT8 MLP classification."""

    def setUp(self):
        self.fs = 130
        self.t = np.linspace(0, 1.0, self.fs, endpoint=False)

    def test_baseline_mean_inference(self):
        """Baseline reference vector should evaluate to Class 0 (Normal Sinus) with zero logits."""
        class_id, logits = polar.infer(polar.FEAT_MEAN.copy())
        self.assertEqual(class_id, 0)
        self.assertEqual(polar.CLASS_NAMES[class_id], "NORMAL_SINUS")
        np.testing.assert_allclose(logits, [0.0, 0.0, 0.0], atol=1e-5)

    def test_feature_extraction_structure(self):
        """extract_features must produce 14 valid float32 values without NaNs or Infs."""
        ecg = [400.0 * np.sin(2 * np.pi * 2.0 * ti) for ti in self.t]
        rr = [800.0, 810.0, 790.0, 805.0]
        feats = polar.extract_features(ecg, rr)

        self.assertIsInstance(feats, np.ndarray)
        self.assertEqual(len(feats), 14)
        self.assertEqual(feats.dtype, np.float32)
        self.assertFalse(np.isnan(feats).any(), "Extracted features contain NaN")
        self.assertFalse(np.isinf(feats).any(), "Extracted features contain Inf")

    def test_normal_sinus_rhythm_classification(self):
        """Normal Sinus Rhythm ECG should classify as Class 0 (NORMAL_SINUS)."""
        ecg_normal = (
            400.0 * np.exp(-((self.t - 0.40) / 0.04) ** 2)
            + 50.0 * np.exp(-((self.t - 0.70) / 0.06) ** 2)
        )
        rr_normal = [800.0, 805.0, 795.0, 800.0]
        feats = polar.extract_features(list(ecg_normal), rr_normal)
        class_id, logits = polar.infer(feats)

        self.assertEqual(class_id, 0)
        self.assertEqual(polar.CLASS_NAMES[class_id], "NORMAL_SINUS")
        self.assertGreater(logits[0], logits[1])
        self.assertGreater(logits[0], logits[2])

    def test_ectopic_pvc_classification(self):
        """Ectopic PVC with wide QRS, secondary repolarization, and premature RR should classify as Class 1."""
        ecg_pvc = 400.0 * np.exp(-((self.t - 0.30) / 0.05) ** 2)
        ecg_pvc[int(self.fs * 0.65):] += 1200.0
        rr_pvc = [800.0, 520.0, 1080.0, 800.0]
        feats = polar.extract_features(list(ecg_pvc), rr_pvc)
        class_id, logits = polar.infer(feats)

        self.assertEqual(class_id, 1)
        self.assertEqual(polar.CLASS_NAMES[class_id], "ECTOPIC_PVC")
        self.assertGreater(logits[1], logits[0])
        self.assertGreater(logits[1], logits[2])

    def test_motion_artifact_classification(self):
        """High motion artifact (vigorous baseline wander / tremor) should classify as Class 2."""
        ecg_artifact = (
            400.0 * np.exp(-((self.t - 0.40) / 0.04) ** 2)
            + 800.0 * np.sin(2 * np.pi * 5.0 * self.t)
            + 400.0 * np.sin(2 * np.pi * 12.0 * self.t)
        )
        rr_artifact = [800.0, 820.0, 780.0, 810.0]
        feats = polar.extract_features(list(ecg_artifact), rr_artifact)
        class_id, logits = polar.infer(feats)

        self.assertEqual(class_id, 2)
        self.assertEqual(polar.CLASS_NAMES[class_id], "MOTION_ARTIFACT")
        self.assertGreater(logits[2], logits[0])
        self.assertGreater(logits[2], logits[1])

    def test_cli_verification_suite(self):
        """polar.run_verification() should execute all 4 test vectors and return True."""
        result = polar.run_verification()
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
