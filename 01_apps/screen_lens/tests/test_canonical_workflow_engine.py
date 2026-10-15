# -*- coding: utf-8 -*-
"""
Verification Tests for Screen Lens Canonical Workflow Engine
============================================================
Subsystem: 01_apps/screen_lens/tests/test_canonical_workflow_engine.py
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

from src.canonical_workflow_engine import ScreenLensCanonicalWorkflowEngine, ObservedProjectEvent


def test_screen_lens_harvest_and_workflow_update():
    """Verifies that the Screen Lens AI harvests observations and updates the workflow document."""
    engine = ScreenLensCanonicalWorkflowEngine()
    events = engine.harvest_active_observations(max_records=10)

    assert len(events) >= 2
    for ev in events:
        assert ev.is_grounded_truth is True
        assert ev.source_device is not None

    verdict = engine.process_and_update_canonical_workflow(events)

    assert verdict.obsidian_synced is True
    assert verdict.lora_pairs_harvested >= len(events)
    assert Path(verdict.canonical_workflow_markdown_path).exists()
    assert Path(verdict.canonical_workflow_markdown_path).stat().st_size > 200


def test_canonical_workflow_obsidian_structure():
    """Verifies the Markdown contains valid Wikilinks and Mermaid diagrams."""
    engine = ScreenLensCanonicalWorkflowEngine()
    events = engine.harvest_active_observations(max_records=5)
    verdict = engine.process_and_update_canonical_workflow(events)

    content = Path(verdict.canonical_workflow_markdown_path).read_text(encoding="utf-8")
    assert "# 👁️ Screen Lens: Canonical Project Development Workflow" in content
    assert "mermaid" in content
    assert "[[Index]]" in content
    assert "[[LIVE_DEVELOPMENT_LOG_2026]]" in content
