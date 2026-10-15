#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
02_ai_models_and_inference/tests/test_cloud_teacher_outperformance_engine.py
================================================================================
Test Suite for Cloud AI Teacher Distillation & Local Outperformance Engine
--------------------------------------------------------------------------------
Lauburu Mesh Ecosystem — 2026
================================================================================
"""

import os
import sys
import pytest
from pathlib import Path

# Dynamic Monorepo Root Resolution
p = Path(__file__).resolve()
while p.parent != p:
    if (p / "PROJECT.md").exists() or (p / "obsidian_vault").exists():
        REPO_ROOT = p
        break
    p = p.parent
else:
    REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")

INFERENCE_DIR = REPO_ROOT / "02_ai_models_and_inference"
PROTOCOLS_DIR = REPO_ROOT / "05_agents_and_swarms" / "training_protocols"

if str(INFERENCE_DIR) not in sys.path:
    sys.path.insert(0, str(INFERENCE_DIR))
if str(PROTOCOLS_DIR) not in sys.path:
    sys.path.insert(0, str(PROTOCOLS_DIR))

from cloud_teacher_distillation_engine import (
    CANONICAL_PROJECT_CHALLENGES,
    CloudOutperformanceIndexEvaluator,
    CloudTeacherDistillationEngine,
    CloudTeacherHub,
    ProjectChallenge,
    assert_significant_outperformance_achieved,
    DistillationResult
)
from cloud_teacher_outperformance_orchestrator import (
    RepoGraphContextSynthesizer,
    CompilerInTheLoopAgent,
    MCTSTestTimeSearch,
    TypeStubIngestionWrapper,
    RLVRGroundTruthVerifier,
    HighResPatchTiler,
    CloudTeacherOutperformanceOrchestrator
)


class TestCloudOutperformanceIndex:
    """Tests the mathematical formulation of Gate 8 Cloud Outperformance Index (COI)."""

    def test_coi_mathematical_formulation(self):
        evaluator = CloudOutperformanceIndexEvaluator()
        # Perfect parity: Acc=100%, Speedup=10x, Airgap=True, Free=True -> COI=1.00
        coi, status = evaluator.compute_coi(100.0, 100.0, 10.0, 100.0, True, True)
        assert coi == 1.00, f"Expected 1.00, got {coi}"
        assert status == "CERTIFIED_OUTPERFORMANCE"

        # Edge-Case: High speedup (100x), Acc=99.5%, Cloud Acc=99.0% -> COI > 1.00
        coi_high, status_high = evaluator.compute_coi(99.5, 99.0, 1.0, 100.0, True, True)
        assert coi_high >= 1.00
        assert status_high == "CERTIFIED_OUTPERFORMANCE"

        # Failure Case: Zero accuracy -> COI must be < 1.0
        coi_zero, status_zero = evaluator.compute_coi(0.0, 100.0, 10.0, 100.0, True, True)
        assert coi_zero < 1.00
        assert status_zero == "SUB_PARITY"


class TestProjectChallengeCatalog:
    """Verifies coverage across all 7 projects of the Lauburu Monorepo."""

    def test_7_projects_coverage(self):
        assert len(CANONICAL_PROJECT_CHALLENGES) == 7
        project_ids = [c.project_id for c in CANONICAL_PROJECT_CHALLENGES]
        expected_ids = [
            "00_core_infrastructure",
            "01_apps",
            "02_ai_models_and_inference",
            "03_biometrics_and_telemetry",
            "04_data_and_memory",
            "05_agents_and_swarms",
            "06_scripts_and_tooling"
        ]
        for p in expected_ids:
            assert p in project_ids, f"Project {p} missing from challenge catalog"

    def test_challenge_verification_commands_valid(self):
        for c in CANONICAL_PROJECT_CHALLENGES:
            assert c.verification_command is not None
            assert len(c.verification_command) > 5
            assert c.target_local_model_id is not None
            assert c.cloud_teacher_model_id is not None

    def test_01_apps_targets_kimi_tandem_titan(self):
        apps_challenge = next(c for c in CANONICAL_PROJECT_CHALLENGES if c.project_id == "01_apps")
        assert apps_challenge.target_local_model_id == "kimi-tandem-titan-72b"
        assert "Kimi Tandem Titan" in apps_challenge.target_local_model_name
        assert "kimi_tandem_titan_multimodal" in apps_challenge.governing_skills


class TestCompoundLocalEnhancements:
    """Verifies all 6 compound AI mechanisms."""

    def test_repo_graph_context_synthesizer(self):
        code = "class A:\n  pass\ndef foo():\n  return 1\nimport os\n"
        symbols = RepoGraphContextSynthesizer.extract_symbols_from_code(code, "test.py")
        assert "A" in symbols["classes"]
        assert "foo" in symbols["functions"]
        assert "os" in symbols["imports"]

        repo_map = RepoGraphContextSynthesizer.build_symbol_map([symbols])
        assert "File: test.py" in repo_map
        assert "Classes: [A]" in repo_map

    def test_compiler_in_the_loop_agent(self):
        agent = CompilerInTheLoopAgent()
        valid_code = "def bar(): return True\n"
        ok, diag, code = agent.validate_code_diff("test.py", valid_code)
        assert ok is True
        assert code == 0

        invalid_code = "def bar(: return True\n"
        bad_ok, bad_diag, bad_code = agent.validate_code_diff("test.py", invalid_code)
        assert bad_ok is False
        assert bad_code != 0
        assert "SyntaxError" in bad_diag

    def test_mcts_test_time_search(self):
        searcher = MCTSTestTimeSearch()
        candidates = ["short", "def solve_mesh_problem(): return True # High quality implementation", ""]
        best_cand, best_score, best_idx = searcher.evaluate_candidates("Problem", candidates)
        assert best_idx == 1
        assert "solve_mesh_problem" in best_cand
        assert best_score >= 0.8

    def test_type_stub_ingestion(self):
        wrapper = TypeStubIngestionWrapper()
        interface = "def calculate_hrv(ecg_samples: list) -> float:\n    pass\nclass MovesenseHub:\n    pass"
        sigs = wrapper.extract_type_signatures(interface)
        assert "def calculate_hrv" in sigs
        assert "class MovesenseHub" in sigs

    def test_rlvr_ground_truth_verifier(self):
        verifier = RLVRGroundTruthVerifier()
        chosen, exit_0 = verifier.verify_and_label("python3 -c 'exit(0)'")
        assert chosen is True
        assert exit_0 == 0

        not_chosen, exit_1 = verifier.verify_and_label("python3 -c 'exit(1)'")
        assert not_chosen is False
        assert exit_1 != 0

    def test_high_res_patch_tiler(self):
        tiler = HighResPatchTiler()
        tiles = tiler.compute_tile_grid(1920, 1080, tile_size=448)
        assert len(tiles) >= 10
        for x0, y0, x1, y1 in tiles:
            assert x0 <= 1920 and y0 <= 1080
            assert x1 <= 1920 and y1 <= 1080

    def test_orchestrator_integration(self):
        orchestrator = CloudTeacherOutperformanceOrchestrator()
        code = "class Engine:\n    def start(self): return True\n"
        res = orchestrator.run_compound_enhancement_cycle(code)
        assert res["status"] == "COMPOUND_ENHANCEMENT_SUCCESS"
        assert res["all_6_mechanisms_active"] is True


class TestFullSweepAndOutperformance:
    """Verifies that running the full 7-project sweep achieves COI >= 1.00 on all projects."""

    def test_full_sweep_and_report_generation(self):
        engine = CloudTeacherDistillationEngine()
        results = engine.run_full_sweep()
        assert len(results) == 7
        for r in results:
            assert r.coi_score >= 1.00, f"Project {r.project_id} failed COI threshold: {r.coi_score} < 1.00"
            assert r.verification_exit_code == 0
            assert len(r.verification_hash) > 0

        # Check report exists and has non-empty size
        report_path = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "CLOUD_TEACHER_LOCAL_OUTPERFORMANCE_REPORT.md"
        assert report_path.exists()
        assert report_path.stat().st_size > 1000


class TestSignificantOutperformanceLoopAndGate:
    """Tests the multi-epoch adaptive training loop and the strict stopping invariant."""

    def test_significant_coi_scaling(self):
        evaluator = CloudOutperformanceIndexEvaluator()
        # High speedup (20x) with compound boost (+10%) should cross 1.15x
        coi, status = evaluator.compute_coi(
            acc_local=100.0,
            acc_cloud=98.5,
            lat_local_ms=45.0,
            lat_cloud_ms=920.0,
            is_private_airgap=True,
            is_zero_cost=True,
            compound_boost=0.10,
            dynamic_speedup=True
        )
        assert coi >= 1.15, f"Expected significant COI >= 1.15, got {coi}"
        assert status == "CERTIFIED_OUTPERFORMANCE"

    def test_stopping_invariant_failure_on_sub_significant(self):
        # Create a synthetic result that is below 1.15
        dummy_result = DistillationResult(
            challenge_id="CHALLENGE_TEST",
            project_id="00_test",
            teacher_name="Cloud Teacher",
            student_name="Local Model",
            prompt="Test prompt",
            teacher_cot_reasoning="CoT",
            chosen_solution="def foo(): pass",
            rejected_baseline="bad",
            local_accuracy_pct=100.0,
            cloud_accuracy_pct=98.0,
            local_latency_ms=10.0,
            cloud_latency_ms=50.0,
            privacy_score=1.0,
            cost_score=1.0,
            coi_score=1.05,  # Sub-significant (< 1.15)
            coi_status="CERTIFIED_OUTPERFORMANCE",
            verification_exit_code=0,
            verification_hash="abc123"
        )
        with pytest.raises(AssertionError) as exc_info:
            assert_significant_outperformance_achieved([dummy_result], target_coi=1.15)
        assert "TRAINING STOPPAGE FORBIDDEN" in str(exc_info.value)
        assert "00_test" in str(exc_info.value)

    def test_stopping_invariant_failure_on_bad_exit_code(self):
        dummy_result = DistillationResult(
            challenge_id="CHALLENGE_TEST",
            project_id="01_test",
            teacher_name="Cloud Teacher",
            student_name="Local Model",
            prompt="Test prompt",
            teacher_cot_reasoning="CoT",
            chosen_solution="def foo(): pass",
            rejected_baseline="bad",
            local_accuracy_pct=100.0,
            cloud_accuracy_pct=98.0,
            local_latency_ms=1.0,
            cloud_latency_ms=100.0,
            privacy_score=1.0,
            cost_score=1.0,
            coi_score=1.35,  # High COI
            coi_status="CERTIFIED_OUTPERFORMANCE",
            verification_exit_code=1,  # FAILED exit code
            verification_hash="abc123"
        )
        with pytest.raises(AssertionError) as exc_info:
            assert_significant_outperformance_achieved([dummy_result], target_coi=1.15)
        assert "TRAINING STOPPAGE FORBIDDEN" in str(exc_info.value)

    def test_stopping_invariant_success(self):
        dummy_result = DistillationResult(
            challenge_id="CHALLENGE_TEST",
            project_id="02_test",
            teacher_name="Cloud Teacher",
            student_name="Local Model",
            prompt="Test prompt",
            teacher_cot_reasoning="CoT",
            chosen_solution="def foo(): pass",
            rejected_baseline="bad",
            local_accuracy_pct=100.0,
            cloud_accuracy_pct=98.0,
            local_latency_ms=1.0,
            cloud_latency_ms=100.0,
            privacy_score=1.0,
            cost_score=1.0,
            coi_score=1.25,
            coi_status="CERTIFIED_OUTPERFORMANCE",
            verification_exit_code=0,
            verification_hash="abc123"
        )
        assert assert_significant_outperformance_achieved([dummy_result], target_coi=1.15) is True

    def test_train_until_significant_outperformance_convergence(self):
        engine = CloudTeacherDistillationEngine()
        target_coi = 1.15
        results, meta = engine.train_until_significant_outperformance(
            target_coi=target_coi,
            max_epochs=5,
            min_epochs=2
        )
        assert len(results) == 7
        assert meta["converged_epoch"] >= 2
        for r in results:
            assert r.coi_score >= target_coi, f"Project {r.project_id} failed significant COI: {r.coi_score} < {target_coi}"
            assert r.verification_exit_code == 0
            assert r.is_significant is True

        # Check Obsidian report
        report_path = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "CLOUD_TEACHER_LOCAL_OUTPERFORMANCE_REPORT.md"
        assert report_path.exists()
        content = report_path.read_text(encoding="utf-8")
        assert "Significant Outperformance Matrix" in content
        assert "Adaptive Multi-Epoch Distillation Convergence Trajectory" in content
        assert "TRAINING COMPLETE: ALL 7 PROJECTS SIGNIFICANTLY OUTPERFORM CLOUD" in content


if __name__ == "__main__":
    pytest.main(["-v", str(__file__)])
