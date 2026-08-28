"""
Comprehensive PyTest Suite for Task Dispatch Engine & Routing Verifier
========================================================================
Validates:
  1. Complete 13 Subsystems Domain Taxonomy & Specialist Skills Mapping.
  2. Multi-factor composite match fitness calculations.
  3. Strict zero-cloud-spend ($0 target) and truth compliance gating.
  4. In-game debate victory -> ELO ledger update -> Task routing elevation.
  5. Bidirectional feedback loop with genuine AST parsing & test validation.
  6. Empirical Project Contribution ELO calibration in canonical JSON ledger.
  7. End-to-end multi-subsystem task routing sweeps.
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src"

for p in [REPO_ROOT, SRC_PATH]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from canonical_ai_leaderboard import (
    CanonicalAILeaderboardEngine,
    atomic_save_canonical_ledger
)
from task_dispatch_engine import (
    TaskDispatchEngine,
    TaskSpec,
    ALL_13_SUBSYSTEMS,
    SUBSYSTEM_SKILL_TAXONOMY
)


@pytest.fixture
def isolated_ledger(tmp_path):
    """Creates an isolated test canonical ledger for non-destructive testing."""
    test_ledger = tmp_path / "canonical_ai_leaderboard.json"
    canonical_source = REPO_ROOT / "data" / "canonical_ai_leaderboard.json"
    if canonical_source.exists():
        shutil.copy(canonical_source, test_ledger)
    else:
        engine = CanonicalAILeaderboardEngine(ledger_path=test_ledger)
        engine.get_canonical_leaderboard(persist=True)
    return test_ledger


class TestTaskDispatchTaxonomy:
    """Validates 13 Subsystems domain taxonomy and metadata completeness."""

    def test_all_13_subsystems_present(self):
        assert len(ALL_13_SUBSYSTEMS) == 13
        for sub in ALL_13_SUBSYSTEMS:
            assert sub in SUBSYSTEM_SKILL_TAXONOMY
            entry = SUBSYSTEM_SKILL_TAXONOMY[sub]
            assert "name" in entry and len(entry["name"]) > 0
            assert "primary_skills" in entry and len(entry["primary_skills"]) >= 1
            assert "default_priority" in entry
            assert "description" in entry

    def test_task_spec_instantiation_and_defaults(self):
        spec = TaskSpec.from_dict({"subsystem": "03_biometrics_and_telemetry"})
        assert spec.subsystem == "03_biometrics_and_telemetry"
        assert "biometrics_cardiovascular_physiology" in spec.required_skills
        assert spec.zero_cloud_spend_required is False
        assert spec.min_truth_compliance_pct == 100.0


class TestTaskDispatchMathematics:
    """Validates normalization, fitness scoring, and constraints."""

    def test_elo_normalization_bounds(self):
        assert TaskDispatchEngine.normalize_elo(1200.0) == 0.0
        assert TaskDispatchEngine.normalize_elo(2000.0) == 50.0
        assert TaskDispatchEngine.normalize_elo(2800.0) == 100.0
        assert TaskDispatchEngine.normalize_elo(3500.0) == 100.0  # Clamped upper bound
        assert TaskDispatchEngine.normalize_elo(500.0) == 0.0    # Clamped lower bound

    def test_composite_fitness_formula(self):
        # Fitness = 0.40 * ELO_norm + 0.40 * Skill_score + 0.20 * Benchmark_score
        # ELO = 2000 -> ELO_norm = 50.0
        # Skill = 90.0, Bench = 95.0
        # Fitness = 0.40 * 50.0 + 0.40 * 90.0 + 0.20 * 95.0 = 20.0 + 36.0 + 19.0 = 75.0
        fit = TaskDispatchEngine.compute_composite_fitness(
            elo=2000.0,
            avg_skill_score=90.0,
            benchmark_score=95.0
        )
        assert fit == 75.0

    def test_zero_cloud_spend_filtering(self, isolated_ledger):
        engine = TaskDispatchEngine(ledger_path=isolated_ledger)
        task = TaskSpec(
            task_id="TASK_LOCAL_ONLY",
            subsystem="00_core_infrastructure",
            required_skills=["docker_mesh_rpc_sharding"],
            zero_cloud_spend_required=True
        )
        decision = engine.route_task(task)
        dispatched = decision["dispatched_model"]
        assert "CLOUD" not in dispatched["type"]
        assert "CLOUD" not in dispatched["tier"]
        assert decision["zero_cloud_spend_enforced"] is True

    def test_truth_compliance_gate(self, isolated_ledger):
        engine = TaskDispatchEngine(ledger_path=isolated_ledger)
        task = TaskSpec(
            task_id="TASK_TRUTH_STRICT",
            subsystem="01_apps",
            min_truth_compliance_pct=99.0
        )
        decision = engine.route_task(task)
        assert decision["dispatched_model"]["truth_compliance_pct"] >= 99.0


class TestInGameDebateToProjectRouting:
    """Verifies that an in-game debate victory directly elevates a model's task routing priority."""

    def test_debate_victory_elevates_task_routing(self, isolated_ledger):
        lb_engine = CanonicalAILeaderboardEngine(ledger_path=isolated_ledger)
        dispatch_engine = TaskDispatchEngine(ledger_path=isolated_ledger)

        # Baseline check between two local contenders
        model_a_id = "deepseek_r1_32b"
        model_b_id = "local_llama_33_70b_sharded"

        # Record decisive debate victory for Model A on specific domain
        debate_payload = {
            "match_id": "DEBATE_TEST_001",
            "match_type": "TRI_ORCHESTRATOR_DEBATE",
            "topic_or_challenge": "Biometrics movesense signal processing",
            "model_a_id": model_a_id,
            "model_b_id": model_b_id,
            "score_a": 1.0,
            "score_b": 0.0,
            "consumed_tokens_a": 800,
            "consumed_tokens_b": 2500,
            "agreement_score": 0.99,
            "rtt_ms": 15.0,
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
            "target_skills": ["biometrics_cardiovascular_physiology"]
        }
        res = lb_engine.record_match_victory(debate_payload)
        assert res["match_record"]["winner_id"] == model_a_id

        # Route task requiring the updated skill
        task = TaskSpec(
            task_id="TASK_BIOMETRICS_ROUTING",
            subsystem="03_biometrics_and_telemetry",
            required_skills=["biometrics_cardiovascular_physiology"],
            zero_cloud_spend_required=True
        )
        decision = dispatch_engine.route_task(task)
        assert decision["status"] == "DISPATCHED_TO_TOP_ELO_MODEL"

        # Check candidate rankings
        candidates = {c["model_id"]: c for c in decision["all_ranked_candidates"]}
        assert candidates[model_a_id]["fitness_score"] >= candidates[model_b_id]["fitness_score"]


class TestBidirectionalFeedbackLoop:
    """Verifies empirical code execution, AST parsing, and Project Contribution ELO update."""

    def test_successful_task_execution_feedback(self, isolated_ledger):
        dispatch_engine = TaskDispatchEngine(ledger_path=isolated_ledger)

        code_snippet = """
def process_ecg_buffer(signal_array, sample_rate_hz=128):
    '''Bandpass filter 0.5Hz - 40Hz for ECG QRS identification'''
    filtered = [float(x) * 0.98 for x in signal_array if abs(x) < 5000.0]
    return filtered
"""
        feedback_payload = {
            "task_id": "TASK_ECG_FILTER_001",
            "model_id": "kimi_tandem_titan",
            "subsystem": "03_biometrics_and_telemetry",
            "target_skills": ["biometrics_cardiovascular_physiology"],
            "ast_syntax_pass": True,
            "code_snippet": code_snippet,
            "test_suite_passed": True,
            "execution_latency_ms": 18.2,
            "truth_audit_passed": True,
            "truth_compliance_pct": 100.0
        }

        result = dispatch_engine.validate_and_record_execution(feedback_payload)
        audit = result["audit_record"]

        assert result["status"] == "FEEDBACK_RECORDED_SUCCESSFULLY"
        assert audit["ast_pass"] is True
        assert audit["performance_score"] > 0.85
        assert audit["delta_project_elo"] > 0.0

    def test_invalid_syntax_penalizes_feedback(self, isolated_ledger):
        dispatch_engine = TaskDispatchEngine(ledger_path=isolated_ledger)

        invalid_code = "def syntax_error_here(x, y: return x +++ y !!"
        feedback_payload = {
            "task_id": "TASK_BROKEN_SYNTAX",
            "model_id": "kimi_tandem_titan",
            "subsystem": "00_core_infrastructure",
            "code_snippet": invalid_code,
            "test_suite_passed": False,
            "execution_latency_ms": 200.0,
            "truth_audit_passed": False,
            "truth_compliance_pct": 0.0
        }

        result = dispatch_engine.validate_and_record_execution(feedback_payload)
        audit = result["audit_record"]

        assert audit["ast_pass"] is False
        assert "SyntaxError" in audit["ast_details"]
        assert audit["performance_score"] < 0.50
        assert audit["delta_project_elo"] < 0.0


class TestAll13SubsystemsSweep:
    """Verifies that all 13 monorepo subsystems can be systematically routed."""

    def test_route_all_13_subsystems(self, isolated_ledger):
        dispatch_engine = TaskDispatchEngine(ledger_path=isolated_ledger)
        sweep = dispatch_engine.route_all_13_subsystems_demo()
        assert sweep["total_subsystems_routed"] == 13
        for sub in ALL_13_SUBSYSTEMS:
            assert sub in sweep["subsystem_dispatches"]
            d = sweep["subsystem_dispatches"][sub]
            assert d["fitness_score"] > 0.0
            assert len(d["dispatched_model"]) > 0
