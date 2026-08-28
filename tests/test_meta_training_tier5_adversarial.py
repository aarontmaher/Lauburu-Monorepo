"""
Tier 5: Adversarial Hardening & Stress Test Suite
=================================================
Meta-Training Game Dashboard & Tri-Orchestrator AI Debate System.

Covers adversarial edge cases:
1. High-concurrency race conditions during live debate execution & atomic file locking.
2. Corrupt / malformed debate payloads and AST injection attacks.
3. FIDE ELO extreme delta boundary invariance, logistic precision, and multiplier bounds.
4. Zero-cloud-spend bypass attempts and truth audit failures (eta_truth = 0).
"""

import os
import sys
import json
import math
import time
import ast
import tempfile
import shutil
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytest

# Ensure repository paths are in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src"
SCRIPTS_PATH = REPO_ROOT / "06_scripts_and_tooling" / "scripts"

for p in [REPO_ROOT, SRC_PATH, SCRIPTS_PATH]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from canonical_ai_leaderboard import (
    CanonicalAILeaderboardEngine,
    CANONICAL_LEADERBOARD_SCHEMA_V7,
    validate_ledger_schema,
    atomic_save_canonical_ledger,
    calculate_expected_elo,
    compute_expected_outcome,
    compute_eta_size,
    compute_eta_token,
    compute_eta_consensus,
    compute_eta_compute,
    compute_eta_truth,
    compute_dynamic_k_factor,
    compute_elo_delta,
    compute_skill_delta,
)
from task_dispatch_engine import (
    TaskDispatchEngine,
    TaskSpec,
    ALL_13_SUBSYSTEMS,
    SUBSYSTEM_SKILL_TAXONOMY,
)
from tests.test_meta_training_tier1_features import (
    calculate_expected_elo as ref_calculate_expected_elo,
    compute_dynamic_k_factor as ref_compute_dynamic_k_factor,
    ReferenceTaskDispatchEngine,
)


# ===========================================================================
# 1. High-Concurrency Race Conditions & Atomic Locking
# ===========================================================================
class TestTier5AdversarialConcurrency:
    """Stress-tests high-concurrency race conditions and atomic persistence."""

    def test_high_concurrency_parallel_match_recordings(self):
        """25 concurrent threads recording matches on shared ledger simultaneously."""
        temp_dir = tempfile.mkdtemp(prefix="tier5_concurrency_")
        ledger_path = Path(temp_dir) / "canonical_ai_leaderboard.json"

        try:
            engine = CanonicalAILeaderboardEngine(ledger_path=ledger_path)
            engine.get_canonical_leaderboard(persist=True)

            num_threads = 25
            matches_per_thread = 4
            models = ["kimi_tandem_titan", "claude_37_sonnet", "gemini_37_flash", "deepseek_r1_32b"]

            errors = []

            def worker_task(thread_id: int):
                for i in range(matches_per_thread):
                    m_a = models[(thread_id + i) % len(models)]
                    m_b = models[(thread_id + i + 1) % len(models)]
                    payload = {
                        "match_id": f"CONC_MATCH_T{thread_id}_M{i}_{int(time.time()*1000)}",
                        "match_type": "TRI_ORCHESTRATOR_DEBATE",
                        "topic_or_challenge": f"High-Concurrency WebGPU Shading Thread {thread_id}",
                        "model_a_id": m_a,
                        "model_b_id": m_b,
                        "score_a": 1.0,
                        "score_b": 0.0,
                        "consumed_tokens_a": 1024,
                        "consumed_tokens_b": 2048,
                        "agreement_score": 0.95,
                        "rtt_ms": 15.0,
                        "truth_verified": True,
                        "truth_compliance_pct": 100.0,
                        "target_skills": ["debating", "3d_ai_training_game"],
                    }
                    try:
                        res = engine.record_match_victory(payload)
                        assert res is not None
                        assert "match_record" in res
                    except Exception as e:
                        errors.append(f"Thread {thread_id} Iteration {i} failed: {e}")

            threads = []
            for tid in range(num_threads):
                t = threading.Thread(target=worker_task, args=(tid,))
                threads.append(t)
                t.start()

            for t in threads:
                t.join(timeout=15.0)

            assert len(errors) == 0, f"Encountered concurrency errors: {errors[:5]}"

            # Verify on-disk ledger integrity
            with open(ledger_path, "r", encoding="utf-8") as f:
                final_data = json.load(f)

            assert validate_ledger_schema(final_data) is True
            expected_total = num_threads * matches_per_thread
            assert final_data["canonical_summary"]["total_matches_recorded"] == expected_total
            assert len(final_data["match_history"]) == expected_total
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_concurrent_task_dispatch_queries(self):
        """30 concurrent threads querying task dispatch routing across all 13 subsystems."""
        temp_dir = tempfile.mkdtemp(prefix="tier5_dispatch_conc_")
        ledger_path = Path(temp_dir) / "canonical_ai_leaderboard.json"

        try:
            leaderboard_engine = CanonicalAILeaderboardEngine(ledger_path=ledger_path)
            leaderboard_engine.get_canonical_leaderboard(persist=True)
            dispatch_engine = TaskDispatchEngine(ledger_path=ledger_path)

            results = []
            errors = []

            def dispatch_worker(tid: int):
                subsystem = ALL_13_SUBSYSTEMS[tid % len(ALL_13_SUBSYSTEMS)]
                skills = SUBSYSTEM_SKILL_TAXONOMY.get(subsystem, ["debating"])
                spec = TaskSpec(
                    task_id=f"CONC_TASK_{tid}_{subsystem}",
                    subsystem=subsystem,
                    title=f"Parallel Subsystem Workload {tid}",
                    description=f"Concurrency stress test for {subsystem}",
                    required_skills=skills,
                    zero_cloud_spend_required=(tid % 2 == 0),
                    min_truth_compliance_pct=95.0,
                )
                try:
                    routing = dispatch_engine.route_task(spec)
                    results.append(routing)
                except Exception as e:
                    errors.append(f"Worker {tid} error: {e}")

            threads = [threading.Thread(target=dispatch_worker, args=(i,)) for i in range(30)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10.0)

            assert len(errors) == 0, f"Task dispatch concurrency errors: {errors}"
            assert len(results) == 30
            for r in results:
                assert r["status"] in ["DISPATCHED_TO_TOP_ELO_MODEL", "NO_QUALIFIED_CANDIDATE_FOUND"]
                if r["status"] == "DISPATCHED_TO_TOP_ELO_MODEL":
                    assert r["dispatched_model"]["fitness_score"] > 0
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_concurrent_bidirectional_feedback_ast_validation(self):
        """20 parallel threads submitting simultaneous AST validation feedback."""
        temp_dir = tempfile.mkdtemp(prefix="tier5_feedback_conc_")
        ledger_path = Path(temp_dir) / "canonical_ai_leaderboard.json"

        try:
            leaderboard_engine = CanonicalAILeaderboardEngine(ledger_path=ledger_path)
            leaderboard_engine.get_canonical_leaderboard(persist=True)
            dispatch_engine = TaskDispatchEngine(ledger_path=ledger_path)

            valid_code = "def valid_ast_kernel(x):\n    return x * 2\n"
            invalid_code = "def broken_ast(x: return x ++ broken syntax"

            audit_results = []
            errors = []

            def feedback_worker(tid: int):
                is_valid = (tid % 2 == 0)
                code = valid_code if is_valid else invalid_code
                payload = {
                    "task_id": f"FEEDBACK_TASK_{tid}",
                    "model_id": "kimi_tandem_titan",
                    "subsystem": "00_core_infrastructure",
                    "target_skills": ["docker_mesh_rpc_sharding"],
                    "code_snippet": code,
                    "test_suite_passed": is_valid,
                    "execution_latency_ms": 20.0 + tid,
                    "truth_audit_passed": is_valid,
                    "truth_compliance_pct": 100.0 if is_valid else 40.0,
                }
                try:
                    res = dispatch_engine.validate_and_record_execution(payload)
                    audit_results.append((is_valid, res))
                except Exception as e:
                    errors.append(f"Worker {tid} error: {e}")

            threads = [threading.Thread(target=feedback_worker, args=(i,)) for i in range(20)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10.0)

            assert len(errors) == 0, f"Feedback concurrency errors: {errors}"
            assert len(audit_results) == 20

            for is_valid, res in audit_results:
                audit = res["audit_record"]
                if is_valid:
                    assert audit["ast_pass"] is True
                    assert audit["delta_project_elo"] > 0
                else:
                    assert audit["ast_pass"] is False
                    assert audit["delta_project_elo"] < 0
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_atomic_ledger_file_locking_under_stress(self):
        """Verify atomic file replacement pattern prevents partial / corrupt reads."""
        temp_dir = tempfile.mkdtemp(prefix="tier5_atomic_stress_")
        ledger_path = Path(temp_dir) / "canonical_ai_leaderboard.json"

        try:
            engine = CanonicalAILeaderboardEngine(ledger_path=ledger_path)
            data = engine.get_canonical_leaderboard(persist=True)

            read_corruptions = []
            stop_event = threading.Event()

            def writer_loop():
                for i in range(50):
                    if stop_event.is_set():
                        break
                    data["canonical_summary"]["total_matches_recorded"] = i
                    atomic_save_canonical_ledger(data, ledger_path)
                    time.sleep(0.002)

            def reader_loop():
                while not stop_event.is_set():
                    try:
                        with open(ledger_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            if not content.strip():
                                read_corruptions.append("Empty file content read during atomic write")
                            else:
                                parsed = json.loads(content)
                                if "canonical_summary" not in parsed:
                                    read_corruptions.append("Missing root key in concurrent read")
                    except Exception as e:
                        read_corruptions.append(f"JSON read error: {e}")
                    time.sleep(0.001)

            writer_t = threading.Thread(target=writer_loop)
            reader_threads = [threading.Thread(target=reader_loop) for _ in range(5)]

            for rt in reader_threads:
                rt.start()
            writer_t.start()

            writer_t.join(timeout=10.0)
            stop_event.set()
            for rt in reader_threads:
                rt.join(timeout=5.0)

            assert len(read_corruptions) == 0, f"Atomic file lock corruptions detected: {read_corruptions[:5]}"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# ===========================================================================
# 2. Corrupt / Malformed Payloads and AST Injection Attacks
# ===========================================================================
class TestTier5AdversarialPayloadsAndASTInjection:
    """Stress-tests malformed payloads and malicious AST code injection handling."""

    def test_malformed_debate_payload_missing_required_fields(self):
        """Missing required fields in debate payload must raise KeyError or handle cleanly."""
        temp_dir = tempfile.mkdtemp(prefix="tier5_malformed_")
        ledger_path = Path(temp_dir) / "canonical_ai_leaderboard.json"

        try:
            engine = CanonicalAILeaderboardEngine(ledger_path=ledger_path)
            engine.get_canonical_leaderboard(persist=True)

            # Missing model_b_id
            corrupt_payload_1 = {
                "match_id": "CORRUPT_01",
                "model_a_id": "kimi_tandem_titan",
                "score_a": 1.0,
            }
            with pytest.raises(KeyError):
                engine.record_match_victory(corrupt_payload_1)

            # Non-existent model IDs
            corrupt_payload_2 = {
                "match_id": "CORRUPT_02",
                "model_a_id": "non_existent_fake_model_alpha",
                "model_b_id": "non_existent_fake_model_beta",
                "score_a": 1.0,
                "score_b": 0.0,
            }
            with pytest.raises(KeyError):
                engine.record_match_victory(corrupt_payload_2)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_corrupt_data_types_and_extreme_values(self):
        """Malformed types (string numbers, negative tokens, extreme agreement values) handle gracefully."""
        temp_dir = tempfile.mkdtemp(prefix="tier5_types_")
        ledger_path = Path(temp_dir) / "canonical_ai_leaderboard.json"

        try:
            engine = CanonicalAILeaderboardEngine(ledger_path=ledger_path)
            engine.get_canonical_leaderboard(persist=True)

            # String floats and negative numbers
            payload = {
                "match_id": "TYPE_STRESS_01",
                "match_type": "TRI_ORCHESTRATOR_DEBATE",
                "topic_or_challenge": "Adversarial Type Stress",
                "model_a_id": "kimi_tandem_titan",
                "model_b_id": "claude_37_sonnet",
                "score_a": "1.0",  # String instead of float
                "score_b": "0.0",
                "consumed_tokens_a": -500,  # Negative token count
                "consumed_tokens_b": 10000000,  # Massive 10M token count
                "agreement_score": 5.5,  # Out of range agreement
                "rtt_ms": -10.0,  # Negative latency
                "truth_verified": "yes",  # String bool
                "truth_compliance_pct": "150.0",  # Out of range string
            }

            res = engine.record_match_victory(payload)
            assert res is not None
            assert "match_record" in res
            assert res["updated_model_a"]["elo"] > 0
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_ast_code_injection_security_payloads(self):
        """Malicious execution payloads (eval, os.system, subprocess) parsed safely without execution."""
        dispatch_engine = TaskDispatchEngine()

        malicious_snippets = [
            'import os\nos.system("echo INJECTION_ATTEMPT")',
            'import subprocess\nsubprocess.run(["rm", "-rf", "/tmp/fake_target"])',
            'eval("__import__(\'os\').getcwd()")',
            'exec("x = 42\\nprint(x)")',
            '__import__("builtins").__dict__["eval"]("1+1")',
        ]

        for idx, snippet in enumerate(malicious_snippets):
            payload = {
                "task_id": f"INJECTION_TASK_{idx}",
                "model_id": "kimi_tandem_titan",
                "subsystem": "11_security_and_governance",
                "target_skills": ["device_hacking_defence"],
                "code_snippet": snippet,
                "test_suite_passed": True,
                "execution_latency_ms": 15.0,
                "truth_audit_passed": True,
                "truth_compliance_pct": 100.0,
            }

            res = dispatch_engine.validate_and_record_execution(payload)
            audit = res["audit_record"]
            # The parser must parse the AST without executing the malicious command
            assert audit["ast_pass"] is True
            assert "ast.parse()" in audit["ast_details"]

    def test_ast_syntax_error_detection_and_severe_elo_penalty(self):
        """Unclosed strings, invalid operators, and unparsable code result in severe penalties."""
        dispatch_engine = TaskDispatchEngine()

        broken_snippets = [
            "def broken_syntax(a, b: return a +++",
            "class IncompleteClass:\n    def missing_body(",
            "if True\n    x = 10",
            "for i in range(10)\nprint(i)",
            "x = 'unclosed string literal",
            "return 42 outside function",
        ]

        for idx, broken in enumerate(broken_snippets):
            payload = {
                "task_id": f"BROKEN_SYNTAX_TASK_{idx}",
                "model_id": "kimi_tandem_titan",
                "subsystem": "01_apps",
                "target_skills": ["3d_ai_training_game"],
                "code_snippet": broken,
                "test_suite_passed": False,
                "execution_latency_ms": 100.0,
                "truth_audit_passed": False,
                "truth_compliance_pct": 20.0,
            }

            res = dispatch_engine.validate_and_record_execution(payload)
            audit = res["audit_record"]

            assert audit["ast_pass"] is False
            assert "SyntaxError" in audit["ast_details"]
            assert audit["performance_score"] < 0.25
            assert audit["delta_project_elo"] < 0

    def test_ast_extreme_unicode_control_chars_and_null_bytes(self):
        """Code containing emojis, null bytes, BOMs, and RTL unicode strings."""
        dispatch_engine = TaskDispatchEngine()

        unicode_code = """
# 🥋 955-Node OPML Grappling Kinematics WebGPU Shader
# RTL comment: مرحبا بالعالم
def compute_joint_torque(angle_rad: float, tension_nm: float) -> float:
    \"\"\"Calculates torque with unicode identifier safety.\"\"\"
    \u03c0 = 3.141592653589793  # Greek pi
    return tension_nm * angle_rad * \u03c0
"""
        payload = {
            "task_id": "UNICODE_AST_TASK",
            "model_id": "kimi_tandem_titan",
            "subsystem": "10_spatial_grappling_kinematics",
            "target_skills": ["grappling_map_understanding"],
            "code_snippet": unicode_code,
            "test_suite_passed": True,
            "execution_latency_ms": 12.0,
            "truth_audit_passed": True,
            "truth_compliance_pct": 100.0,
        }

        res = dispatch_engine.validate_and_record_execution(payload)
        audit = res["audit_record"]
        assert audit["ast_pass"] is True

    def test_ast_empty_none_and_non_string_code_snippets(self):
        """Empty strings, whitespace, or integer/list payloads passed as code_snippet."""
        dispatch_engine = TaskDispatchEngine()

        invalid_inputs = ["", "   \n\t  ", 12345, ["code", "list"]]

        for idx, code_input in enumerate(invalid_inputs):
            payload = {
                "task_id": f"EMPTY_CODE_TASK_{idx}",
                "model_id": "kimi_tandem_titan",
                "subsystem": "06_scripts_and_tooling",
                "code_snippet": code_input,
                "test_suite_passed": False,
                "execution_latency_ms": 50.0,
                "truth_audit_passed": False,
                "truth_compliance_pct": 50.0,
            }

            res = dispatch_engine.validate_and_record_execution(payload)
            audit = res["audit_record"]
            assert audit["ast_pass"] is False
            assert audit["delta_project_elo"] <= 0

    def test_deeply_nested_ast_payload_resilience(self):
        """Deeply nested expressions parse cleanly without maximum recursion depth crash."""
        dispatch_engine = TaskDispatchEngine()

        depth = 60
        nested_expr = "x"
        for _ in range(depth):
            nested_expr = f"abs({nested_expr})"
        deep_code = f"def deeply_nested_calc(x):\n    return {nested_expr}\n"

        payload = {
            "task_id": "DEEP_AST_TASK",
            "model_id": "kimi_tandem_titan",
            "subsystem": "03_biometrics_and_telemetry",
            "target_skills": ["biometrics_cardiovascular_physiology"],
            "code_snippet": deep_code,
            "test_suite_passed": True,
            "execution_latency_ms": 25.0,
            "truth_audit_passed": True,
            "truth_compliance_pct": 100.0,
        }

        res = dispatch_engine.validate_and_record_execution(payload)
        assert res["audit_record"]["ast_pass"] is True


# ===========================================================================
# 3. FIDE ELO Extreme Delta Boundary Invariance
# ===========================================================================
class TestTier5AdversarialFideEloInvariance:
    """Stress-tests mathematical invariance and boundary stability of FIDE ELO."""

    def test_fide_elo_extreme_disparities_up_to_10000_delta(self):
        """Logistic probability formula stability across massive rating differences."""
        disparities = [
            (10000.0, 10.0),    # Delta = 9990.0
            (10.0, 10000.0),    # Delta = -9990.0
            (5000.0, 500.0),    # Delta = 4500.0
            (2500.0, 2500.0),   # Delta = 0.0
            (1.0, 1.0),         # Ultra-low equal
            (50000.0, 50000.0), # Ultra-high equal
        ]

        for r_a, r_b in disparities:
            e_a = calculate_expected_elo(r_a, r_b)
            e_b = calculate_expected_elo(r_b, r_a)

            # Mathematical invariant: E_A + E_B == 1.0
            assert abs((e_a + e_b) - 1.0) < 1e-12, f"Sum violation for ({r_a}, {r_b}): {e_a + e_b}"
            assert 0.0 <= e_a <= 1.0
            assert 0.0 <= e_b <= 1.0

            if r_a == r_b:
                assert abs(e_a - 0.5) < 1e-12
                assert abs(e_b - 0.5) < 1e-12
            elif r_a > r_b:
                assert e_a > 0.5
                assert e_b < 0.5
            else:
                assert e_a < 0.5
                assert e_b > 0.5

    def test_symmetric_k_zero_sum_delta_conservation(self):
        """Zero-sum conservation: Delta R_A + Delta R_B == 0 when K_A == K_B."""
        k_values = [8.0, 16.0, 32.0, 64.0, 128.0]
        match_scores = [(1.0, 0.0), (0.0, 1.0), (0.5, 0.5), (0.8, 0.2)]

        for k in k_values:
            for score_a, score_b in match_scores:
                d_a, d_b, e_a, e_b = compute_elo_delta(
                    rating_a=2400.0,
                    rating_b=2200.0,
                    score_a=score_a,
                    k_a=k,
                    k_b=k,
                )
                assert abs(d_a + d_b) < 1e-10, f"Zero-sum violated: {d_a} + {d_b} != 0 (k={k})"

    def test_dynamic_k_factor_parameter_size_extreme_clamping(self):
        """Scaling factor eta_size bounded in [0.5, 2.5] across extreme parameter sizes."""
        # Ultra SLM: 0.00001B params -> max clamp 2.5
        eta_micro = compute_eta_size(0.00001)
        assert eta_micro == 2.5

        # 135M SLM -> ~1.5 - 2.5
        eta_135m = compute_eta_size(0.135)
        assert 1.4 <= eta_135m <= 2.5

        # 70B MoE -> ~1.0
        eta_70b = compute_eta_size(70.0)
        assert 0.9 <= eta_70b <= 1.1

        # 10,000B (10T) Mega Titan -> min clamp 0.5
        eta_mega = compute_eta_size(10000.0)
        assert eta_mega == 0.5

    def test_dynamic_k_factor_token_frugality_extreme_clamping(self):
        """Scaling factor eta_token bounded in [0.5, 1.5] across extreme token consumption."""
        # 0 tokens -> max clamp 1.50
        assert compute_eta_token(0) == 1.50

        # Negative tokens -> max clamp 1.50
        assert compute_eta_token(-500) == 1.50

        # Optimal frugality (512 tokens vs 2048 baseline) -> 1.50
        assert compute_eta_token(512) == 1.50

        # Baseline (2048 tokens) -> 1.00
        assert compute_eta_token(2048) == 1.00

        # Heavy waste (1,000,000 tokens) -> min clamp 0.50
        assert compute_eta_token(1000000) == 0.50

    def test_dynamic_k_factor_consensus_deadlock_zero_elo_gain(self):
        """Consensus scaling ranges from 0.50 (complete disagreement) to 1.00 (unanimous accord)."""
        # Canonical engine formula: 0.50 + 0.50 * agreement
        eta_discord = compute_eta_consensus(0.0)
        assert eta_discord == 0.50

        eta_accord = compute_eta_consensus(1.0)
        assert eta_accord == 1.00

        # Reference helper with eta_consensus=0.0 -> K_dyn = 0.0
        k_deadlock = ref_compute_dynamic_k_factor(base_k=32.0, eta_consensus=0.0)
        assert k_deadlock == 0.0

        # Zero K-factor implies zero rating change
        d_a, d_b, _, _ = compute_elo_delta(2400.0, 2200.0, 1.0, k_a=k_deadlock, k_b=k_deadlock)
        assert d_a == 0.0
        assert d_b == 0.0

    def test_dynamic_k_factor_truth_failure_zero_elo_gain(self):
        """Unverified or truth-failed debate yields eta_truth = 0.0 and K_dyn = 0.0."""
        # Unverified debate
        eta_unverified = compute_eta_truth(truth_verified=False, truth_compliance_pct=100.0)
        assert eta_unverified == 0.0

        # 0% compliance
        eta_zero_comp = compute_eta_truth(truth_verified=True, truth_compliance_pct=0.0)
        assert eta_zero_comp == 0.0

        k_truth_fail = compute_dynamic_k_factor(
            matches_played=10,
            match_type="TRI_ORCHESTRATOR_DEBATE",
            eta_truth=eta_unverified,
        )
        assert k_truth_fail == 0.0

        d_a, d_b, _, _ = compute_elo_delta(2400.0, 2200.0, 1.0, k_a=k_truth_fail, k_b=k_truth_fail)
        assert d_a == 0.0
        assert d_b == 0.0

    def test_asymmetric_k_factor_rating_stability_invariants(self):
        """SLM winning over Titan gains more ELO than Titan winning over SLM."""
        # Case 1: SLM (K=80.0) beats Titan (K=16.0)
        d_slm_win, d_titan_loss, _, _ = compute_elo_delta(
            rating_a=2000.0,
            rating_b=2400.0,
            score_a=1.0,
            k_a=80.0,
            k_b=16.0,
        )
        assert d_slm_win > 0
        assert d_titan_loss < 0
        assert d_slm_win > abs(d_titan_loss), "SLM win delta must exceed Titan loss delta due to higher efficiency K-factor"

        # Case 2: Titan (K=16.0) beats SLM (K=80.0)
        d_titan_win, d_slm_loss, _, _ = compute_elo_delta(
            rating_a=2400.0,
            rating_b=2000.0,
            score_a=1.0,
            k_a=16.0,
            k_b=80.0,
        )
        assert d_titan_win > 0
        assert d_slm_loss < 0
        assert d_titan_win < abs(d_slm_loss), "Titan win gain must be smaller than SLM loss penalty"

    def test_specialist_skill_score_asymptotic_progression_and_bounds(self):
        """Specialist skill score progression formula remains strictly within [50.0, 100.0]."""
        # Win from 99.0 skill
        d_win_high = compute_skill_delta(current_skill=99.0, score=1.0)
        assert 0.0 <= d_win_high <= 0.05

        # Win from 50.0 skill
        d_win_low = compute_skill_delta(current_skill=50.0, score=1.0)
        assert d_win_low == 2.0  # +0.4 * (100 - 50) / 10 = 2.0

        # Loss from 50.0 skill
        d_loss_low = compute_skill_delta(current_skill=50.0, score=0.0)
        assert d_loss_low == 0.0  # -0.3 * (50 - 50) / 10 = 0.0

        # Loss from 99.0 skill
        d_loss_high = compute_skill_delta(current_skill=99.0, score=0.0)
        assert d_loss_high == -1.47  # -0.3 * (99 - 50) / 10 = -1.47


# ===========================================================================
# 4. Zero-Cloud-Spend Bypass Attempts and Truth Gating
# ===========================================================================
class TestTier5AdversarialZeroCloudAndTruthGating:
    """Stress-tests zero-cloud spend constraint enforcement and truth audit filtering."""

    def test_zero_cloud_spend_strict_disqualification_of_cloud_titans(self):
        """When zero_cloud_spend_required=True, cloud flagships (Gemini Pro, Claude Opus) are strictly barred."""
        dispatch_engine = TaskDispatchEngine()

        cloud_task = TaskSpec(
            task_id="TASK_STRICT_ZERO_CLOUD",
            subsystem="00_core_infrastructure",
            title="Local RPC Socket Pooling",
            description="Hard sovereign execution test",
            required_skills=["docker_mesh_rpc_sharding", "cpp_metal_llama_optimization"],
            zero_cloud_spend_required=True,
            min_truth_compliance_pct=95.0,
        )

        decision = dispatch_engine.route_task(cloud_task)
        assert decision["status"] == "DISPATCHED_TO_TOP_ELO_MODEL"

        dispatched = decision["dispatched_model"]
        # Dispatched model must be a $0.00 sovereign local model
        cost = str(dispatched["cost_per_m_tokens"]).lower()
        assert "$0.00" in cost or "free" in cost, f"Dispatched non-free model: {dispatched['name']} ({cost})"
        assert not ("CLOUD" in str(dispatched["type"]).upper() or "CLOUD" in str(dispatched["tier"]).upper())

    def test_zero_cloud_spend_masquerade_attempt_resilience(self):
        """Models with masquerading names but paid cost tiers fail zero-cloud-spend checks."""
        # Create a mock leaderboard entry attempting to spoof local tags
        spoofed_leaderboard = {
            "leaderboard": [
                {
                    "id": "spoofed_cloud_model",
                    "name": "Local Sovereign Spoofed Model",
                    "type": "Cloud API Disguised",
                    "tier": "HYBRID_CLOUD",
                    "params_b": 70.0,
                    "cost_per_m_tokens": "$15.00 / $30.00 (Paid Cloud)",
                    "elo": 3200.0,
                    "overall_benchmark_score": 99.0,
                    "orchestrator_metrics": {"truth_audit_compliance": "100.0%"},
                    "specialist_skills": {"docker_mesh_rpc_sharding": 99.0},
                },
                {
                    "id": "genuine_local_model",
                    "name": "Genuine Local Qwen",
                    "type": "Local Sovereign Core",
                    "tier": "LOCAL_SOVEREIGN",
                    "params_b": 32.0,
                    "cost_per_m_tokens": "$0.00 (100% Free)",
                    "elo": 2300.0,
                    "overall_benchmark_score": 95.0,
                    "orchestrator_metrics": {"truth_audit_compliance": "100.0%"},
                    "specialist_skills": {"docker_mesh_rpc_sharding": 95.0},
                },
            ]
        }

        router = ReferenceTaskDispatchEngine(spoofed_leaderboard)
        task_spec = {
            "task_id": "SPOOF_TEST",
            "subsystem": "00_core_infrastructure",
            "required_skills": ["docker_mesh_rpc_sharding"],
            "zero_cloud_spend_required": True,
            "min_truth_compliance_pct": 90.0,
        }

        result = router.route_task(task_spec)
        assert result["routed_model_id"] == "genuine_local_model", "Spoofed paid model was incorrectly routed!"

    def test_truth_compliance_threshold_strict_filtering(self):
        """Models with truth compliance below required threshold are disqualified."""
        dispatch_engine = TaskDispatchEngine()

        # Task requiring 100.0% truth compliance
        task_spec = TaskSpec(
            task_id="TRUTH_STRICT_TASK",
            subsystem="07_docs_and_architecture",
            title="Sovereign Architecture Whitepaper",
            description="Truth-sensitive architectural specification",
            required_skills=["debating", "vision_vlm_truth_auditing"],
            zero_cloud_spend_required=False,
            min_truth_compliance_pct=99.5,
        )

        decision = dispatch_engine.route_task(task_spec)
        assert decision["status"] == "DISPATCHED_TO_TOP_ELO_MODEL"

        dispatched = decision["dispatched_model"]
        orch_metrics = dispatched.get("orchestrator_metrics", {})
        truth_str = str(orch_metrics.get("truth_audit_compliance", "100.0%")).replace("%", "")
        truth_val = float(truth_str)
        assert truth_val >= 99.5, f"Dispatched model truth compliance {truth_val}% < 99.5%"

    def test_zero_qualified_candidates_graceful_fallback(self):
        """When constraints are impossible (e.g. 200% truth compliance), engine raises clear RuntimeError."""
        dispatch_engine = TaskDispatchEngine()

        impossible_task = TaskSpec(
            task_id="IMPOSSIBLE_CONSTRAINTS_TASK",
            subsystem="00_core_infrastructure",
            title="Impossible Requirements",
            description="No model can satisfy this",
            required_skills=["non_existent_skill_xyz"],
            zero_cloud_spend_required=True,
            min_truth_compliance_pct=150.0,  # Impossible truth requirement
        )

        with pytest.raises(RuntimeError) as exc_info:
            dispatch_engine.route_task(impossible_task)

        assert "No eligible AI model found" in str(exc_info.value)

    def test_unverified_debate_victory_zero_elo_gain_enforcement(self):
        """Debate victory with truth_verified=False or truth_compliance_pct=0.0 yields exactly Delta ELO = 0."""
        temp_dir = tempfile.mkdtemp(prefix="tier5_unverified_")
        ledger_path = Path(temp_dir) / "canonical_ai_leaderboard.json"

        try:
            engine = CanonicalAILeaderboardEngine(ledger_path=ledger_path)
            engine.get_canonical_leaderboard(persist=True)

            payload = {
                "match_id": "UNVERIFIED_DEBATE_01",
                "match_type": "TRI_ORCHESTRATOR_DEBATE",
                "topic_or_challenge": "Unverified Fabricated Argument",
                "model_a_id": "kimi_tandem_titan",
                "model_b_id": "claude_37_sonnet",
                "score_a": 1.0,
                "score_b": 0.0,
                "consumed_tokens_a": 1024,
                "consumed_tokens_b": 2048,
                "agreement_score": 0.95,
                "rtt_ms": 15.0,
                "truth_verified": False,  # Truth verification failed!
                "truth_compliance_pct": 0.0,
                "target_skills": ["debating"],
            }

            res = engine.record_match_victory(payload)
            match_rec = res["match_record"]

            # Mathematical guarantee: Delta ELO must be 0.0
            assert match_rec["delta_elo_a"] == 0.0, f"Expected 0.0 Delta ELO for unverified victory, got {match_rec['delta_elo_a']}"
            assert match_rec["delta_elo_b"] == 0.0, f"Expected 0.0 Delta ELO for unverified defeat, got {match_rec['delta_elo_b']}"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_truth_audit_compliance_score_scaling(self):
        """Zero-tolerance Rule #0: 100% compliance yields 1.00; anything below 100% yields 0.00."""
        # 100% verified compliance -> 1.00
        eta_full = compute_eta_truth(truth_verified=True, truth_compliance_pct=100.0)
        assert eta_full == 1.0

        # Sub-100% compliance drops to 0.00 (Zero-Mock Rule #0 gate)
        eta_half = compute_eta_truth(truth_verified=True, truth_compliance_pct=50.0)
        assert eta_half == 0.0

        eta_unverified = compute_eta_truth(truth_verified=False, truth_compliance_pct=100.0)
        assert eta_unverified == 0.0

        # Reference helper scaling
        k_full = ref_compute_dynamic_k_factor(base_k=32.0, eta_truth=1.0)
        assert k_full == 32.0

        k_zero = ref_compute_dynamic_k_factor(base_k=32.0, eta_truth=0.0)
        assert k_zero == 0.0
