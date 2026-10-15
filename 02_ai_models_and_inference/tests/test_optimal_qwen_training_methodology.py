# -*- coding: utf-8 -*-
"""
Verification Tests for Optimal Qwen Training Methodology Benchmarks
==================================================================
Subsystem: 02_ai_models_and_inference/tests/test_optimal_qwen_training_methodology.py
Lauburu Mesh Ecosystem — 2026
"""

import sys
import pytest
from pathlib import Path

# Add subsystem root to sys.path
_curr_dir = Path(__file__).resolve().parent
_subsystem_root = _curr_dir.parent
if str(_subsystem_root) not in sys.path:
    sys.path.insert(0, str(_subsystem_root))

from benchmarks.optimal_qwen_training_methodology_tester import OptimalTrainingMethodologyTester


def test_training_methodologies_benchmark_execution():
    """Verifies that all 5 training methodologies are evaluated and scored."""
    tester = OptimalTrainingMethodologyTester()
    results = tester.run_all_benchmarks(num_steps=5)

    assert len(results) == 5

    # Verify MLX QLoRA is #1 Champion on Apple Silicon M4
    champ = results[0]
    assert champ.methodology_id == "M1_MLX_QLORA"
    assert champ.tokens_per_second > 400.0
    assert champ.peak_vram_gb < 6.0
    assert champ.zero_oom_safety_score > 95.0


def test_m4_air_16gb_vram_and_thermal_headroom():
    """Verifies that all methodologies respect the 16GB physical RAM ceiling of MacBook Air."""
    tester = OptimalTrainingMethodologyTester()
    results = tester.run_all_benchmarks(num_steps=5)

    for r in results:
        # Every method must stay well under the 16GB ceiling
        assert r.peak_vram_gb < 14.0
        # Thermals must not exceed dangerous throttling threshold (>15C rise)
        assert r.thermal_rise_celsius < 12.0
