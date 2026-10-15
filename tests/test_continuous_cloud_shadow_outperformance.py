#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
tests/test_continuous_cloud_shadow_outperformance.py
================================================================================
Comprehensive Test Suite for Continuous Local AI Training with Cloud Model Shadowing
--------------------------------------------------------------------------------
Lauburu Mesh Ecosystem — 2026
================================================================================
"""

import json
import os
import sys
from pathlib import Path
import pytest

# Dynamic Monorepo Root Resolution
p = Path(__file__).resolve()
while p.parent != p:
    if (p / "PROJECT.md").exists() or (p / "obsidian_vault").exists():
        REPO_ROOT = p
        break
    p = p.parent
else:
    REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")

PROTOCOLS_DIR = REPO_ROOT / "05_agents_and_swarms" / "training_protocols"
INFERENCE_DIR = REPO_ROOT / "02_ai_models_and_inference"
for d in [str(PROTOCOLS_DIR), str(INFERENCE_DIR)]:
    if d not in sys.path:
        sys.path.insert(0, d)

from continuous_cloud_shadow_outperformance_engine import (
    AIDebateCouncil,
    CloudModelShadowEvaluator,
    ScreenLensSovereignBridge,
    NeoExecutionTracker,
    ContinuousCloudShadowOutperformanceEngine,
    check_host_ram_headroom,
    CANONICAL_PROJECT_CHALLENGES,
    DistillationResult
)


class TestAIDebateCouncil:
    """Tests the /ai-debate Tri-Orchestrator deliberative consensus."""

    def test_debate_deliberation_consensus_threshold(self):
        council = AIDebateCouncil()
        consensus = council.conduct_deliberation(
            topic="Deterministic Failover and Zero TCP Resets",
            subsystem="Self-Healing Hub & Multi-WAN",
            min_consensus=0.98,
            max_rounds=3
        )
        assert consensus.final_agreement_score >= 0.98, (
            f"Expected consensus >= 0.98, got {consensus.final_agreement_score}"
        )
        assert len(consensus.rounds) >= 1
        assert "Consensus reached" in consensus.synthesized_decision

        # Verify Devil's Advocate critique exists in all rounds
        for r in consensus.rounds:
            assert "Qwen 27B Abliterated" in r.devils_advocate_critique
            assert len(r.devils_advocate_critique) > 20

    def test_debate_persists_to_obsidian_vault(self):
        council = AIDebateCouncil()
        consensus = council.conduct_deliberation(
            topic="WebGPU Rust Shader Pipeline and ShowUI Grounding",
            subsystem="Edge Applications & UI",
            min_consensus=0.98
        )
        debate_md = REPO_ROOT / "obsidian_vault" / "05_SWARMS" / "debates" / "AI_DEBATE_CLOUD_SHADOW_OUTPERFORMANCE_LATEST.md"
        assert debate_md.exists()
        content = debate_md.read_text(encoding="utf-8")
        assert "[[Index]]" in content
        assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in content
        assert "Tri-Orchestrator AI Debate" in content


class TestCloudModelShadowEvaluator:
    """Tests Cloud Model Shadowing quality audit and DPO pair harvesting."""

    def test_detect_mocks_enforces_rule_0(self):
        evaluator = CloudModelShadowEvaluator()
        # Flawed mock code
        bad_code = "def get_ecg():\n    return [1, 2, 3] # mock_data placeholder"
        assert evaluator._detect_mocks(bad_code) is True

        # Clean production code
        clean_code = "def get_ecg():\n    return read_kernel_telemetry()"
        assert evaluator._detect_mocks(clean_code) is False

    def test_harvest_dpo_pair_serialization(self):
        evaluator = CloudModelShadowEvaluator()
        challenge = CANONICAL_PROJECT_CHALLENGES[0]
        student_code = "def execute_contract():\n    return True\n"
        
        pair = evaluator.evaluate_and_harvest_dpo_pair(
            challenge=challenge,
            student_solution=student_code,
            student_exit_code=0,
            epoch=1
        )
        assert pair["rule0_passed"] is True
        assert pair["project_id"] == challenge.project_id
        assert "Step 1" in pair["teacher_cot"]
        assert len(pair["chosen"]) > 10
        assert len(pair["rejected"]) > 10

        # Verify dataset files exist and have records
        distill_file = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/cloud_teacher_distillation_pairs.jsonl")
        assert distill_file.exists()
        assert distill_file.stat().st_size > 0


class TestScreenLensSovereignBridge:
    """Tests /screen-lens-sovereign MLX Metal GPU training step."""

    def test_mlx_metal_gpu_step_execution(self):
        bridge = ScreenLensSovereignBridge()
        res = bridge.execute_metal_gpu_step(batch_size=4, loss_target=0.82)
        assert res["status"] == "MLX_METAL_STEP_SUCCESS"
        assert res["loss"] > 0.0
        assert res["tokens_per_second"] > 0.0
        assert "Apple Silicon" in res["device"] or "Darwin" in res["device"]

    def test_observation_logged_to_obsidian(self):
        bridge = ScreenLensSovereignBridge()
        bridge.execute_metal_gpu_step(batch_size=2, loss_target=0.79)
        obs_file = REPO_ROOT / "obsidian_vault" / "APPS_AND_FEATURES" / "SCREEN_LENS_LIVE_OBSERVATIONS.md"
        assert obs_file.exists()
        content = obs_file.read_text(encoding="utf-8")
        assert "Screen Lens Sovereign MLX Training Step" in content


class TestNeoExecutionTracker:
    """Tests /neo task registration and telemetry tracking."""

    def test_register_task_updates_state(self):
        tracker = NeoExecutionTracker()
        entry = tracker.register_or_update_task(
            task_name="Continuous Outperformance Test",
            project_id="00_core_infrastructure",
            coi_achieved=1.28,
            status="COMPLETED"
        )
        assert "neo_thread_" in entry["thread_id"]
        assert entry["status"] == "COMPLETED"
        assert entry["coi_achieved"] == 1.28

        state_file = REPO_ROOT / "04_data_and_memory" / "neo_training_task_state.json"
        assert state_file.exists()
        state = json.loads(state_file.read_text(encoding="utf-8"))
        assert state["count"] >= 1
        assert any(t["thread_id"] == entry["thread_id"] for t in state["tasks"])


class TestContinuousCloudShadowEngine:
    """Tests end-to-end multi-project continuous training and outperformance."""

    def test_single_project_cycle_execution(self):
        engine = ContinuousCloudShadowOutperformanceEngine()
        challenge = CANONICAL_PROJECT_CHALLENGES[0]
        res = engine.execute_project_cycle(challenge, epoch=1, target_coi=1.15)
        assert isinstance(res, DistillationResult)
        assert res.verification_exit_code == 0
        assert res.coi_score >= 1.00
        assert len(res.verification_hash) > 0

    def test_multi_epoch_continuous_training_convergence(self):
        engine = ContinuousCloudShadowOutperformanceEngine()
        target_coi = 1.15
        results, meta = engine.run_continuous_training_loop(
            min_epochs=2,
            max_epochs=4,
            target_coi=target_coi,
            verify_significant=True
        )
        assert len(results) == 7
        assert meta["converged"] is True
        assert meta["converged_epoch"] >= 2

        # All 7 projects must achieve COI >= 1.15x and Exit Code 0
        for r in results:
            assert r.coi_score >= target_coi, (
                f"Project {r.project_id} failed significant COI threshold: {r.coi_score} < {target_coi}"
            )
            assert r.verification_exit_code == 0
            assert r.is_significant is True

        # Verify Obsidian report
        report_path = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "CLOUD_TEACHER_LOCAL_OUTPERFORMANCE_REPORT.md"
        assert report_path.exists()
        content = report_path.read_text(encoding="utf-8")
        assert "Significant Outperformance Matrix" in content
        assert "PASSED — ALL 7 PROJECTS SIGNIFICANTLY OUTPERFORM CLOUD" in content


if __name__ == "__main__":
    pytest.main(["-v", str(__file__)])
