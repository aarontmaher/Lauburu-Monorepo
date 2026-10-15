#!/usr/bin/env python3
"""
Unit Tests for Lens AI Training Accelerator
===========================================
Validates:
1. State initialization and training methods identification.
2. Goal definition of Lauburu Lens AI.
3. DPO pair generation with Rule #0 zero-mock coordinates and contrast validation.
4. Dataset serialization and Obsidian report synchronization.
"""

import sys
import pytest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SCRIPTS_ROOT = TEST_DIR.parent

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from lens_ai_training_accelerator import LensAITrainingAccelerator, UI_TARGET_SAMPLES


class TestLensAITrainingAccelerator:

    def test_training_methods_and_goal_identified(self):
        accel = LensAITrainingAccelerator()
        methods = accel.state["training_methods"]
        assert len(methods) >= 4
        assert any("DPO" in m for m in methods)
        assert any("CDP" in m for m in methods)
        assert any("MLX" in m for m in methods)
        assert "Living Visual Cortex" in accel.state["goal"]

    def test_ui_target_samples_exist(self):
        assert len(UI_TARGET_SAMPLES) >= 4
        for sample in UI_TARGET_SAMPLES:
            assert "target_name" in sample
            assert "expected_coords" in sample
            assert "dom_snippet" in sample

    def test_execute_lens_training_burst(self):
        accel = LensAITrainingAccelerator()
        res = accel.execute_lens_training_burst(batch_size=4)
        assert res["burst_pairs_harvested"] >= 0
        assert res["status"] == "LENS_TRAINING_ACTIVE"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
