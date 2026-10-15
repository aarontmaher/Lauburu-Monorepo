#!/usr/bin/env python3
"""
06_scripts_and_tooling/tests/test_local_vlm_cloud_auditor.py
============================================================
Comprehensive Test Suite for Local AI Visual Truth Auditor &
Cloud Free Tier Maximizer Engine.

Validates:
1. Visual perception and Bounding-Box ROI cropping (>85% token reduction).
2. Adaptive cloud challenge dispatching.
3. Gate 1 Code & AST integrity audit (Rule #0 zero-mock assertor).
4. Gate 2 Visual layout audit (RenderFlex overflow detection).
5. Multimodal DPO & SFT LoRA dataset synthesis.
6. State persistence and Obsidian telemetry publishing.
"""

import os
import sys
import json
import pytest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
TOOLING_ROOT = TEST_DIR.parent
REPO_ROOT = TOOLING_ROOT.parent

for p in [str(REPO_ROOT), str(TOOLING_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from local_vlm_cloud_truth_auditor import (
    VisualPerceptionEngine,
    AdaptiveCloudOptimizerDispatcher,
    DualGateTruthAuditor,
    MultimodalLoRADistillationEngine,
    LocalVLMCloudTruthConductor,
    VISUAL_LORA_DATASET,
    CONTINUOUS_LORA_DATASET,
    STATE_FILE,
    OBSIDIAN_TELEMETRY
)


class TestVisualPerception:
    """Verifies screen capture perception and ROI cropping."""

    def test_capture_active_ui_state(self):
        perception = VisualPerceptionEngine()
        state = perception.capture_active_ui_state()
        assert "app" in state
        assert "window_title" in state
        assert "status" in state

    def test_crop_bounding_box_roi(self):
        perception = VisualPerceptionEngine()
        ui_state = perception.capture_active_ui_state()
        roi = perception.crop_bounding_box_roi(ui_state, "TestWidget")
        assert roi["widget"] == "TestWidget"
        assert roi["token_reduction_pct"] > 80.0
        assert roi["crop_width"] > 0
        assert roi["crop_height"] > 0


class TestAdaptiveCloudDispatcher:
    """Verifies cloud challenge dispatching and suggestions."""

    def test_dispatch_ui_refactor(self):
        dispatcher = AdaptiveCloudOptimizerDispatcher()
        res = dispatcher.dispatch_ui_refactor({
            "prompt": "Fix Flutter overflow in card",
            "domain": "flutter_ui"
        })
        assert "code_diff" in res
        assert res["duration_sec"] > 0.0
        assert res["tokens_out"] > 0


class TestDualGateTruthAuditor:
    """Verifies Gate 1 (AST/Code) and Gate 2 (Visual Layout) audits."""

    def test_gate_1_clean_code_passes(self):
        auditor = DualGateTruthAuditor()
        valid_code = "def calculate_hr(samples):\n    return sum(samples) / len(samples)\n"
        passed, violations = auditor.audit_gate_1_code_ast(valid_code)
        assert passed is True
        assert len(violations) == 0

    def test_gate_1_rule_0_violation_caught(self):
        auditor = DualGateTruthAuditor()
        fake_code = "def get_telemetry():\n    return random.randint(60, 100)\n"
        passed, violations = auditor.audit_gate_1_code_ast(fake_code)
        assert passed is False
        assert any("RULE_0_VIOLATION" in v for v in violations)

    def test_gate_2_clean_scroll_layout_passes(self):
        auditor = DualGateTruthAuditor()
        valid_flutter = """
Padding(
  child: SingleChildScrollView(
    child: Column(children: [Text("Title"), Text("Subtitle")]),
  ),
)
"""
        passed, findings = auditor.audit_gate_2_visual_layout(valid_flutter, {})
        assert passed is True
        assert findings["overflow_detected"] is False
        assert findings["visual_quality_score"] > 0.90

    def test_gate_2_unconstrained_overflow_caught(self):
        auditor = DualGateTruthAuditor()
        overflow_flutter = """
Padding(
  child: Column(children: [Text("Title"), ListView(children: [])]),
)
"""
        passed, findings = auditor.audit_gate_2_visual_layout(overflow_flutter, {})
        assert passed is False
        assert findings["overflow_detected"] is True
        assert findings["visual_quality_score"] < 0.70


class TestMultimodalLoRADistillation:
    """Verifies dataset logging and Obsidian telemetry generation."""

    def test_record_audit_cycle(self):
        distiller = MultimodalLoRADistillationEngine()
        challenge = {"prompt": "Fix biometrics layout"}
        cloud_res = {"code_diff": "def clean(): pass", "tokens_out": 25}
        dpo = distiller.record_audit_cycle(
            challenge, cloud_res, True, [], True, {"visual_quality_score": 0.98}
        )
        assert dpo["approved"] is True
        assert dpo["id"].startswith("VISUAL_DPO_")
        assert VISUAL_LORA_DATASET.exists()
        assert CONTINUOUS_LORA_DATASET.exists()
        assert OBSIDIAN_TELEMETRY.exists()


class TestFullConductorEndToEnd:
    """Verifies full end-to-end audit cycle."""

    def test_run_audit_cycle_end_to_end(self):
        conductor = LocalVLMCloudTruthConductor()
        result = conductor.run_audit_cycle("Test Flutter ECG widget optimization")
        assert result["gate1_passed"] is True
        assert result["gate2_passed"] is True
        assert result["approved"] is True
        assert result["dpo_id"] is not None


if __name__ == "__main__":
    pytest.main(["-v", __file__])
