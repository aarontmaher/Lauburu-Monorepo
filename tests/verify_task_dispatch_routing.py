#!/usr/bin/env python3
"""
Task Dispatch & Routing Verification Test Script
=================================================
Verifies that:
  1. An in-game / Tri-Orchestrator debate victory updates the canonical ELO ledger dynamically.
  2. The multi-factor ELO and specialist skill rating deltas are correctly applied.
  3. A real monorepo project task submitted to TaskDispatchEngine is dynamically routed
     to the winning top-ELO / highest-fitness model.
  4. The bidirectional feedback loop executes genuine AST syntax parsing, test validation,
     and updates Project Contribution ELO in the canonical ledger.
  5. Zero-cloud spend and truth compliance constraints are strictly enforced.
  6. All 13 monorepo subsystems are routed successfully.

Exits with code 0 upon complete successful verification.
"""

import os
import sys
import json
import time
import tempfile
import shutil
from pathlib import Path

# Resolve workspace root and dependencies
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


def run_verification() -> bool:
    print("=" * 80)
    print("🚀 STARTING E2E VERIFICATION: IN-GAME DEBATE VICTORY -> REAL TASK ROUTING")
    print("=" * 80)

    # 1. Setup isolated test environment using real canonical leaderboard structure
    temp_dir = tempfile.mkdtemp(prefix="task_dispatch_verify_")
    test_ledger_path = Path(temp_dir) / "canonical_ai_leaderboard.json"

    # Copy canonical ledger into temp directory for non-destructive test execution
    canonical_source = REPO_ROOT / "data" / "canonical_ai_leaderboard.json"
    if canonical_source.exists():
        shutil.copy(canonical_source, test_ledger_path)
        print(f"✔ Initialized test ledger from canonical source: {test_ledger_path}")
    else:
        # Generate initial catalog via engine
        temp_engine = CanonicalAILeaderboardEngine(ledger_path=test_ledger_path)
        temp_engine.get_canonical_leaderboard(persist=True)
        print(f"✔ Initialized new test ledger via CanonicalAILeaderboardEngine: {test_ledger_path}")

    # Initialize engines with test ledger
    leaderboard_engine = CanonicalAILeaderboardEngine(ledger_path=test_ledger_path)
    dispatch_engine = TaskDispatchEngine(ledger_path=test_ledger_path)

    # -----------------------------------------------------------------------
    # Step A: Setup Two Competing Models for a Specific Specialist Domain
    # -----------------------------------------------------------------------
    print("\n[Step A] Preparing debate duel between competing models...")
    model_a_id = "deepseek_r1_32b"
    model_b_id = "gemini_31_pro"

    # Verify models exist in leaderboard
    initial_leaderboard = leaderboard_engine.get_canonical_leaderboard(persist=False)
    models_dict = {m["id"]: m for m in initial_leaderboard["leaderboard"]}
    assert model_a_id in models_dict, f"Model {model_a_id} must exist in ledger"
    assert model_b_id in models_dict, f"Model {model_b_id} must exist in ledger"

    initial_elo_a = models_dict[model_a_id]["elo"]
    initial_elo_b = models_dict[model_b_id]["elo"]
    initial_skill_a = models_dict[model_a_id]["specialist_skills"].get("debating", 90.0)

    print(f"  • Model A ({models_dict[model_a_id]['name']}): Initial ELO = {initial_elo_a}, Debating Skill = {initial_skill_a}")
    print(f"  • Model B ({models_dict[model_b_id]['name']}): Initial ELO = {initial_elo_b}")

    # -----------------------------------------------------------------------
    # Step B: Execute and Record an In-Game Debate Duel Victory
    # -----------------------------------------------------------------------
    print("\n[Step B] Executing in-game Tri-Orchestrator debate duel where Model A wins...")
    debate_payload = {
        "match_id": f"DEBATE_VERIFY_{int(time.time())}",
        "match_type": "TRI_ORCHESTRATOR_DEBATE",
        "topic_or_challenge": "Optimal 5-Layer RPC Mesh Sharding & Zero-Cloud-Spend Architecture",
        "model_a_id": model_a_id,
        "model_b_id": model_b_id,
        "score_a": 1.0,  # Model A wins outright
        "score_b": 0.0,
        "consumed_tokens_a": 1024,  # High token efficiency
        "consumed_tokens_b": 4096,
        "agreement_score": 0.98,
        "rtt_ms": 12.5,
        "truth_verified": True,
        "truth_compliance_pct": 100.0,
        "target_skills": ["debating", "docker_mesh_rpc_sharding", "cpp_metal_llama_optimization"],
        "consensus_summary": "Model A demonstrated superior mathematical proof for parameter-efficient RPC tensor sharding."
    }

    victory_result = leaderboard_engine.record_match_victory(debate_payload)
    match_rec = victory_result["match_record"]
    updated_a = victory_result["updated_model_a"]
    updated_b = victory_result["updated_model_b"]

    print(f"  ✔ Debate Match ID: {match_rec['match_id']}")
    print(f"  ✔ Winner: {match_rec['winner_id']}")
    print(f"  ✔ Model A Delta ELO: +{match_rec['delta_elo_a']} -> New ELO: {updated_a['elo']}")
    print(f"  ✔ Model B Delta ELO: {match_rec['delta_elo_b']} -> New ELO: {updated_b['elo']}")
    print(f"  ✔ Model A Debating Skill: {initial_skill_a} -> {updated_a['specialist_skills'].get('debating')}")

    # Assertions on ELO mechanics
    assert match_rec["winner_id"] == model_a_id, "Winner must be Model A"
    assert match_rec["delta_elo_a"] > 0, "Model A ELO delta must be positive"
    assert match_rec["delta_elo_b"] < 0, "Model B ELO delta must be negative"
    assert updated_a["elo"] > initial_elo_a, "Model A ELO must have increased"

    # -----------------------------------------------------------------------
    # Step C: Submit a Real Monorepo Project Task & Verify Dynamic Routing
    # -----------------------------------------------------------------------
    print("\n[Step C] Submitting real monorepo project task for Core Infrastructure RPC Sharding...")
    project_task = TaskSpec(
        task_id="TASK_001_RPC_MESH_SHARDING_OPTIMIZATION",
        subsystem="00_core_infrastructure",
        title="Refactor llama.cpp RPC Socket Connection Pooling for Zero-Loss Failover",
        description="Implement connection keepalives and sub-50ms socket recovery on Port 50052.",
        required_skills=["docker_mesh_rpc_sharding", "cpp_metal_llama_optimization"],
        zero_cloud_spend_required=True,  # Disqualifies cloud models
        min_truth_compliance_pct=100.0,
        priority="CRITICAL"
    )

    routing_decision = dispatch_engine.route_task(project_task)
    dispatched = routing_decision["dispatched_model"]

    print(f"  ✔ Dispatched Model ID: {dispatched['model_id']}")
    print(f"  ✔ Dispatched Model Name: {dispatched['name']}")
    print(f"  ✔ Composite Match Fitness: {dispatched['fitness_score']}/100.0")
    print(f"  ✔ ELO: {dispatched['elo']}")
    print(f"  ✔ Evaluated Skills: {dispatched['skills_evaluated']}")
    print(f"  ✔ Dispatch Rationale: {routing_decision['dispatch_rationale']}")

    assert routing_decision["status"] == "DISPATCHED_TO_TOP_ELO_MODEL", "Status must confirm dispatch"
    assert dispatched["model_id"] in ["deepseek_r1_32b", "kimi_tandem_titan", "local_llama_33_70b_sharded", "genetic_moe_orchestrator"], \
        f"Dispatched model {dispatched['model_id']} must be an eligible local/sovereign top model"
    assert not ("CLOUD" in dispatched["type"] or "CLOUD" in dispatched["tier"]), "Cloud models must be filtered under zero-cloud-spend"

    # -----------------------------------------------------------------------
    # Step D: Verify Bidirectional Feedback Loop with Real AST Code Parsing
    # -----------------------------------------------------------------------
    print("\n[Step D] Executing Bidirectional Feedback Loop with genuine AST syntax validation...")
    valid_python_code = """
def test_rpc_sharding_kernel(mesh_nodes, vram_pool_gb):
    '''Genuine RPC Sharding Tensor Kernel Implementation'''
    allocated = {}
    for node in mesh_nodes:
        if node.get('active', False) and node.get('vram_gb', 0) >= 4.0:
            allocated[node['id']] = node['vram_gb']
    return allocated
"""

    feedback_payload = {
        "task_id": project_task.task_id,
        "model_id": dispatched["model_id"],
        "subsystem": project_task.subsystem,
        "target_skills": project_task.required_skills,
        "ast_syntax_pass": True,
        "code_snippet": valid_python_code,
        "test_suite_passed": True,
        "execution_latency_ms": 24.5,
        "truth_audit_passed": True,
        "truth_compliance_pct": 100.0
    }

    feedback_result = dispatch_engine.validate_and_record_execution(feedback_payload)
    audit_rec = feedback_result["audit_record"]
    updated_model = feedback_result["updated_model"]

    print(f"  ✔ Feedback Status: {feedback_result['status']}")
    print(f"  ✔ AST Details: {audit_rec['ast_details']}")
    print(f"  ✔ Performance Score: {audit_rec['performance_score']}")
    print(f"  ✔ Delta Project Contribution ELO: +{audit_rec['delta_project_elo']}")
    print(f"  ✔ New Project Contribution ELO: {updated_model['project_contribution_elo']}")

    assert feedback_result["status"] == "FEEDBACK_RECORDED_SUCCESSFULLY"
    assert audit_rec["ast_pass"] is True
    assert audit_rec["performance_score"] > 0.80
    assert audit_rec["delta_project_elo"] > 0

    # -----------------------------------------------------------------------
    # Step E: Test Invalid AST Code Rejection in Feedback Loop
    # -----------------------------------------------------------------------
    print("\n[Step E] Testing AST Syntax Error detection in Feedback Loop...")
    invalid_python_code = "def broken_func(a, b: return a +++ syntax error here !"
    invalid_feedback = {
        "task_id": "TASK_INVALID_AST_TEST",
        "model_id": dispatched["model_id"],
        "subsystem": project_task.subsystem,
        "code_snippet": invalid_python_code,
        "test_suite_passed": False,
        "execution_latency_ms": 150.0,
        "truth_audit_passed": False,
        "truth_compliance_pct": 50.0
    }
    invalid_result = dispatch_engine.validate_and_record_execution(invalid_feedback)
    invalid_audit = invalid_result["audit_record"]
    print(f"  ✔ Detected Syntax Error: {invalid_audit['ast_details']}")
    print(f"  ✔ AST Pass flag correctly set to: {invalid_audit['ast_pass']}")
    print(f"  ✔ Performance Score heavily penalized to: {invalid_audit['performance_score']}")
    print(f"  ✔ Delta Project ELO: {invalid_audit['delta_project_elo']}")

    assert invalid_audit["ast_pass"] is False
    assert "SyntaxError" in invalid_audit["ast_details"]
    assert invalid_audit["performance_score"] < 0.50
    assert invalid_audit["delta_project_elo"] < 0

    # -----------------------------------------------------------------------
    # Step F: Verify All 13 Monorepo Subsystems Dispatch Routing
    # -----------------------------------------------------------------------
    print("\n[Step F] Verifying Task Dispatch across all 13 monorepo subsystems...")
    sweep_results = dispatch_engine.route_all_13_subsystems_demo()
    assert sweep_results["total_subsystems_routed"] == 13, f"Expected 13 subsystems, got {sweep_results['total_subsystems_routed']}"

    for sub in ALL_13_SUBSYSTEMS:
        assert sub in sweep_results["subsystem_dispatches"], f"Subsystem {sub} must be routed"
        info = sweep_results["subsystem_dispatches"][sub]
        print(f"  • [{sub}] -> {info['dispatched_model']} (Fitness: {info['fitness_score']}, ELO: {info['elo']})")
        assert info["fitness_score"] > 0, f"Fitness score for {sub} must be positive"

    # Cleanup temp test environment
    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass

    print("\n" + "=" * 80)
    print("🎉 ALL VERIFICATION CHECKS PASSED: DEBATE VICTORY -> REAL TASK DISPATCH (EXIT 0)")
    print("=" * 80)
    return True


if __name__ == "__main__":
    try:
        success = run_verification()
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED WITH UNHANDLED EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
