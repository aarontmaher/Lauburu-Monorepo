"""
tests/test_visual_auditor_pipeline.py
=====================================
Automated Test Suite for Milestone M2:
Tier-0 / Tier-1 Multi-Tier Visual Frame Auditor Pipeline.

Covers:
- Tier-0 rapid edge UI frame audit (<150ms latency SLA, TTFT < 100ms).
- Layout overflow detection (RenderFlex, clipped bounds, overlapping widgets).
- 2D Bounding box extraction [ymin, xmin, ymax, xmax] normalized to [0, 1000].
- Rule #0 Zero-Mock Data & Truth Audit assertion (rejects synthetic strings, accepts real telemetry).
- Seamless escalation to Tier-1 Kimi-VL Thinking (Port 8085) on confidence < 0.85 or 3D kinematics.
- Multi-frame sequential stream audit (5 frames).
- 24/7 LoRA training trace serialization to truth_audit_debate.jsonl.
"""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Ensure monorepo and models directory are in path
REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = REPO_ROOT / "02_ai_models_and_inference" / "models"
LOCAL_LORA_DIR = REPO_ROOT / "data" / "lora_datasets"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))

from visual_frame_auditor import (
    FullMultiTierAuditVerdict,
    MultiTierVisualAuditor,
    Tier0AuditResult,
    Tier0EdgeVisualAuditor,
    Tier1EscalationResult,
    Tier1KimiVLEscalationEngine,
    UIElementBoundingBox,
)


@pytest.fixture
def clean_sample_b64() -> str:
    """Generates valid sample PNG image base64 bytes."""
    header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x048\x00\x00\x09`\x08\x06\x00\x00\x00"
    payload = header + b"\x00" * 128
    return base64.b64encode(payload).decode("ascii")


class TestTier0RapidEdgeVisualAuditor:
    """Tests Tier-0 rapid frame verification, layout overflows, bounding boxes, and zero-mock."""

    def test_tier0_sub_150ms_latency_sla(self, clean_sample_b64):
        """Verify Tier-0 frame audit executes within sub-150ms latency SLA."""
        auditor = Tier0EdgeVisualAuditor()
        result = auditor.audit_frame(
            image_data=clean_sample_b64,
            context_prompt="Clean God-Eye Dashboard UI Audit"
        )
        assert result.latency_ms <= 150.0, f"Latency {result.latency_ms}ms must be <= 150ms"
        assert result.sla_passed is True
        assert result.ttft_ms <= 100.0, f"TTFT {result.ttft_ms}ms must be <= 100ms"
        assert "Qwen2.5-VL-7B" in result.auditor
        assert "Metal Performance Shaders" in result.hardware_backend

    def test_tier0_layout_overflow_detection(self, clean_sample_b64):
        """Verify detection of UI layout overflows and clipping."""
        auditor = Tier0EdgeVisualAuditor()

        # 1. Normal clean layout (no overflow)
        res_clean = auditor.audit_frame(
            clean_sample_b64,
            context_prompt="Standard Clean Dashboard View on Port 3000"
        )
        assert res_clean.layout_overflow_detected is False
        assert res_clean.overflow_summary == "NONE"

        # 2. Trigger layout overflow condition
        res_overflow = auditor.audit_frame(
            clean_sample_b64,
            context_prompt="RenderFlex overflowed by 32 pixels on right boundary"
        )
        assert res_overflow.layout_overflow_detected is True
        assert "RenderFlex" in res_overflow.overflow_summary

    def test_tier0_bounding_box_extraction(self, clean_sample_b64):
        """Verify bounding box coordinates, labels, and [0, 1000] normalization."""
        auditor = Tier0EdgeVisualAuditor()
        result = auditor.audit_frame(
            clean_sample_b64,
            context_prompt="Audit Port 3000 Dashboard Elements"
        )

        assert len(result.bounding_boxes) >= 3, "Must detect major UI component bounding boxes"
        for box in result.bounding_boxes:
            assert 0 <= box.ymin <= 1000
            assert 0 <= box.xmin <= 1000
            assert 0 <= box.ymax <= 1000
            assert 0 <= box.xmax <= 1000
            assert box.ymax >= box.ymin
            assert box.xmax >= box.xmin
            assert box.area >= 0
            assert len(box.label) > 0
            assert box.confidence >= 0.90

    def test_tier0_zero_mock_assertion_pass(self, clean_sample_b64):
        """Verify real physical telemetry passes Rule #0 zero-mock assertion."""
        auditor = Tier0EdgeVisualAuditor()
        result = auditor.audit_frame(
            clean_sample_b64,
            context_prompt="Movesense ECG 128Hz telemetry: DFA-alpha1 0.76, RMSSD 42.1ms, Pooled VRAM 48.8 GB"
        )
        assert result.zero_mock_compliant is True
        assert len(result.flagged_mock_tokens) == 0

    def test_tier0_zero_mock_assertion_reject_fake_data(self, clean_sample_b64):
        """Verify synthetic fake/dummy/mock data is strictly rejected and flagged."""
        auditor = Tier0EdgeVisualAuditor()

        fake_prompts = [
            "UI contains mock telemetry data array for testing",
            "Displaying fake heart rate value of 72 bpm",
            "Dummy user session token tok_fake_123",
            "Lorem ipsum dolor sit amet placeholder text",
            "Simulated sinewave ECG signal generator"
        ]

        for p in fake_prompts:
            res = auditor.audit_frame(clean_sample_b64, context_prompt=p)
            assert res.zero_mock_compliant is False, f"Prompt '{p}' should be rejected as synthetic mock data"
            assert len(res.flagged_mock_tokens) > 0, f"Must flag mock tokens in '{p}'"


class TestTier1KimiVLEscalation:
    """Tests seamless escalation to Tier-1 Kimi-VL Thinking on Port 8085."""

    def test_tier1_escalation_trigger_on_low_confidence(self, clean_sample_b64):
        """Verify escalation triggers when Tier-0 confidence is below 0.85 threshold."""
        auditor = MultiTierVisualAuditor()
        # Trigger low confidence by introducing visual ambiguity
        verdict = auditor.run_full_audit(
            clean_sample_b64,
            context_prompt="RenderFlex overflowed with ambiguous clipped text boundaries"
        )

        assert verdict.tier0_result.escalate_to_tier1 is True
        assert verdict.tier1_escalation is not None
        assert "Kimi-VL Thinking 2506" in verdict.tier1_escalation.auditor
        assert verdict.tier1_escalation.port == 8085
        assert verdict.tier1_escalation.vram_footprint_gb == 9.8
        assert len(verdict.tier1_escalation.deep_reasoning_cot) >= 5
        assert len(verdict.tier1_escalation.resolved_ambiguities) >= 2

    def test_tier1_escalation_trigger_on_3d_kinematic_trees(self, clean_sample_b64):
        """Verify 3D kinematic spatial trees (OPML 955 nodes, joint angles/torques) escalate to Tier-1."""
        auditor = MultiTierVisualAuditor()
        verdict = auditor.run_full_audit(
            clean_sample_b64,
            context_prompt="3D Kinematic Spatial Grappling Tree with OPML tatami nodes and joint torque"
        )

        assert verdict.tier0_result.escalate_to_tier1 is True
        assert verdict.tier1_escalation is not None
        kinematic = verdict.tier1_escalation.kinematic_spatial_analysis
        assert "955-Node OPML" in kinematic["spatial_model"]
        assert kinematic["joint_angle_degrees"] > 0
        assert kinematic["joint_torque_nm"] > 0
        assert kinematic["biomechanical_validity"] == "100%_PHYSICALLY_COHERENT"
        assert verdict.overall_verdict == "TIER1_REASONING_APPROVED_CONVERGED"


class TestMultiFrameStreamAuditAndLoRAPersistence:
    """Tests multi-frame stream verification and 24/7 LoRA training data serialization."""

    def test_multi_frame_5_frame_stream_audit(self, clean_sample_b64):
        """Verify sequential multi-frame audit (5 frames from mobile/browser)."""
        auditor = MultiTierVisualAuditor()
        frames = [clean_sample_b64] * 5
        verdicts = auditor.run_multi_frame_stream_audit(frames, context_prompt="Samsung S20+ OpenClaw UI Stream")

        assert len(verdicts) == 5
        for i, v in enumerate(verdicts):
            assert v.tier0_result.sla_passed is True
            assert v.tier0_result.latency_ms <= 150.0
            assert v.zero_mock_certified is True
            assert v.lora_trace_persisted is True

    def test_lora_dataset_persistence_and_schema(self, clean_sample_b64):
        """Verify visual audit traces serialize to local truth_audit_debate.jsonl."""
        lora_file = LOCAL_LORA_DIR / "truth_audit_debate.jsonl"
        
        # Record initial size
        initial_lines = 0
        if lora_file.exists():
            with open(lora_file, "r", encoding="utf-8") as f:
                initial_lines = len(f.readlines())

        auditor = MultiTierVisualAuditor()
        v = auditor.run_full_audit(clean_sample_b64, context_prompt="LoRA Distillation Verification Audit")
        assert v.lora_trace_persisted is True
        assert lora_file.exists()

        with open(lora_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) >= initial_lines + 1
        last_entry = json.loads(lines[-1])
        assert "timestamp_utc" in last_entry
        assert last_entry["task_type"] == "tier0_tier1_visual_frame_audit"
        assert "instruction" in last_entry
        assert "thought" in last_entry
        assert "output" in last_entry
        assert last_entry["metadata"]["zero_mock_compliance"] is True


class TestAdversarialVisualAuditHardening:
    """Adversarial boundary and corner case test suites."""

    def test_boundary_confidence_threshold_085(self, clean_sample_b64):
        """Verify strict boundary behavior around 0.85 confidence threshold."""
        t0 = Tier0EdgeVisualAuditor()
        # High confidence -> no escalation
        res_high = t0.audit_frame(clean_sample_b64, context_prompt="High Contrast Stable God-Eye Screen")
        if res_high.confidence_score >= 0.85 and not res_high.layout_overflow_detected:
            assert res_high.escalate_to_tier1 is False

    def test_corrupted_and_empty_frame_handling(self):
        """Verify graceful error recovery when passed invalid image data."""
        auditor = MultiTierVisualAuditor()
        # Empty string
        v_empty = auditor.run_full_audit("", context_prompt="Empty Image Test")
        assert v_empty is not None
        assert v_empty.tier0_result.latency_ms <= 150.0

        # Corrupted bytes
        v_corrupt = auditor.run_full_audit(b"corrupted_invalid_header", context_prompt="Corrupted Bytes Test")
        assert v_corrupt is not None
        assert v_corrupt.tier0_result.latency_ms <= 150.0
