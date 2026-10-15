# -*- coding: utf-8 -*-
"""
Verification Tests for Autonomous Monorepo Canonical Refiner & Lens Harvester
=============================================================================
Subsystem: 05_agents_and_swarms/tests/test_autonomous_monorepo_canonical_refiner.py
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

from autonomous_monorepo_canonical_refiner import AutonomousMonorepoCanonicalRefiner


def test_full_monorepo_refinement_execution():
    """Verifies that all 10 monorepo subsystems are swept and refined."""
    refiner = AutonomousMonorepoCanonicalRefiner()
    summary = refiner.execute_full_monorepo_refinement()

    assert summary["subsystems_audited"] == 10
    assert summary["total_files_audited"] > 0
    assert summary["total_training_pairs_generated"] > 0
    assert Path(summary["training_dataset_target"]).exists()

    # Check that Screen Lens and Software Dev specialists are present
    lead_ais = [r["lead_specialist_ai"] for r in summary["reports"]]
    assert any("Screen Lens" in ai for ai in lead_ais)
    assert any("Qwen" in ai for ai in lead_ais)
    assert any("Mesh Sentinel" in ai for ai in lead_ais)


def test_obsidian_log_and_lora_dataset_written():
    """Verifies that the Tri-Vault layers (Obsidian and PySpark JSONL) receive the logs."""
    refiner = AutonomousMonorepoCanonicalRefiner()
    summary = refiner.execute_full_monorepo_refinement()

    assert refiner.LORA_OUTPUT_PATH.exists()
    assert refiner.OBSIDIAN_LOG_PATH.exists()
    assert refiner.OBSIDIAN_LOG_PATH.stat().st_size > 100
