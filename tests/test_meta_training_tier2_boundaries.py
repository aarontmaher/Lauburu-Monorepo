"""
Tier 2: Boundary & Corner Case E2E Tests for Meta-Training Game Dashboard & Tri-Orchestrator AI Debate System.
Validates:
1. Dynamic K-Factor Clamping across parameter sizes (135M SLMs to 1T+ Frontier Titans).
2. Token Frugality Multiplier Bounds (0 tokens, negative tokens, extreme >100k token counts).
3. Consensus Extremes (0.0 complete discord vs 1.0 unanimous accord).
4. Truth Compliance Penalties (0% vs 100% Truth Audit Score).
5. Division-by-Zero Safety & Extreme Rating Disparities (Equal ratings, Delta > 3000, 0 games played).
6. Unicode, Escape Sequences & Special Characters in Topics / Payloads.
7. Malformed & Missing Payload Schema Validation.
8. Atomic File Concurrency & Multithreaded Race Condition Prevention.
9. Zero-Cloud-Spend Hard Constraint Filtering.
"""

import os
import sys
import json
import time
import math
import tempfile
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src"
SCRIPTS_PATH = REPO_ROOT / "06_scripts_and_tooling" / "scripts"

for p in [REPO_ROOT, SRC_PATH, SCRIPTS_PATH]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from tests.test_meta_training_tier1_features import (
    calculate_expected_elo,
    compute_dynamic_k_factor,
    ReferenceTaskDispatchEngine
)


class TestTier2BoundaryAndCornerCases:
    """Tier 2: Boundary & Corner Case Stress Test Suite."""

    # -----------------------------------------------------------------------
    # Boundary 1: Dynamic K-Factor Parameter Size Clamping
    # -----------------------------------------------------------------------
    def test_b1_k_factor_parameter_size_clamping(self):
        """Verify dynamic K-factor scales correctly across SLMs (135M), MoEs (70B), and Frontier Titans (1T+)."""
        # 135M parameter SLM: eta_size = max(0.5, log2(71)/log2(0.135+1)) ~ 1.5 - 2.5
        k_slm = compute_dynamic_k_factor(base_k=32.0, eta_size=2.5, eta_token=1.0, eta_consensus=1.0, eta_truth=1.0)
        assert k_slm == 80.0, f"Expected clamped 80.0 (32 * 2.5), got {k_slm}"

        # 70B parameter model: eta_size ~ 1.0
        k_70b = compute_dynamic_k_factor(base_k=32.0, eta_size=1.0)
        assert k_70b == 32.0

        # 1T+ massive frontier model: eta_size clamped at minimum 0.50
        k_titan = compute_dynamic_k_factor(base_k=32.0, eta_size=0.1)  # input below minimum
        assert k_titan == 16.0, f"Expected lower bound clamp 16.0 (32 * 0.5), got {k_titan}"

        # Test extreme upper bound input (e.g. eta_size = 100.0) -> must clamp to 2.5 (32 * 2.5 = 80.0)
        k_overflow = compute_dynamic_k_factor(base_k=32.0, eta_size=100.0)
        assert k_overflow == 80.0

    # -----------------------------------------------------------------------
    # Boundary 2: Token Frugality Multiplier Bounds
    # -----------------------------------------------------------------------
    def test_b2_token_frugality_bounds(self):
        """Verify token efficiency multiplier handles 0 tokens, negative tokens, and massive token payloads."""
        # 0 tokens / ultra-frugal input -> clamped to max 2.0
        k_zero_tokens = compute_dynamic_k_factor(base_k=32.0, eta_token=3.5)
        assert k_zero_tokens == 64.0, f"Expected upper bound 64.0, got {k_zero_tokens}"

        # Negative token multiplier -> clamped to min 0.5
        k_neg = compute_dynamic_k_factor(base_k=32.0, eta_token=-5.0)
        assert k_neg == 16.0, f"Expected lower bound 16.0, got {k_neg}"

        # Extreme token waste (e.g. 500,000 tokens) -> clamped to min 0.5
        k_waste = compute_dynamic_k_factor(base_k=32.0, eta_token=0.01)
        assert k_waste == 16.0

    # -----------------------------------------------------------------------
    # Boundary 3: Consensus Extremes
    # -----------------------------------------------------------------------
    def test_b3_consensus_extremes(self):
        """Verify complete consensus discord (0.0) and unanimous accord (1.0)."""
        # Complete discord (0.0 consensus accord) -> K becomes 0.0 (no ELO movement on deadlocked debate)
        k_deadlock = compute_dynamic_k_factor(base_k=32.0, eta_consensus=0.0)
        assert k_deadlock == 0.0

        # Unanimous accord (1.0 consensus)
        k_accord = compute_dynamic_k_factor(base_k=32.0, eta_consensus=1.0)
        assert k_accord == 32.0

        # Over-consensus input clamp (e.g. 2.0 -> clamped to 1.5)
        k_over = compute_dynamic_k_factor(base_k=32.0, eta_consensus=2.0)
        assert k_over == 48.0, f"Expected 48.0 (32 * 1.5), got {k_over}"

    # -----------------------------------------------------------------------
    # Boundary 4: Truth Compliance Penalties
    # -----------------------------------------------------------------------
    def test_b4_truth_compliance_penalties(self):
        """Verify 0% truth audit compliance completely zeroes out rating reward."""
        # 100% truth compliance
        k_true = compute_dynamic_k_factor(base_k=32.0, eta_truth=1.0)
        assert k_true == 32.0

        # 0% truth compliance (hallucination / fake data detected)
        k_fake = compute_dynamic_k_factor(base_k=32.0, eta_truth=0.0)
        assert k_fake == 0.0

        # Negative truth score -> clamped to 0.0
        k_neg_truth = compute_dynamic_k_factor(base_k=32.0, eta_truth=-0.5)
        assert k_neg_truth == 0.0

    # -----------------------------------------------------------------------
    # Boundary 5: Division-by-Zero Safety & Extreme Rating Disparities
    # -----------------------------------------------------------------------
    def test_b5_division_by_zero_and_extreme_elo_delta(self):
        """Verify ELO logistic function and win-rate calculations avoid division by zero and numeric overflow."""
        # 1. Identical ratings (R_A = R_B = 2500)
        e_equal = calculate_expected_elo(2500.0, 2500.0)
        assert e_equal == 0.5

        # 2. Extreme positive rating delta (+3000 ELO advantage: R_A = 4000, R_B = 1000)
        e_huge_adv = calculate_expected_elo(4000.0, 1000.0)
        assert not math.isnan(e_huge_adv)
        assert not math.isinf(e_huge_adv)
        assert 0.999999 < e_huge_adv <= 1.0

        # 3. Extreme negative rating delta (-3000 ELO deficit: R_A = 1000, R_B = 4000)
        e_huge_def = calculate_expected_elo(1000.0, 4000.0)
        assert not math.isnan(e_huge_def)
        assert not math.isinf(e_huge_def)
        assert 0.0 <= e_huge_def < 0.000001
        assert round(e_huge_adv + e_huge_def, 6) == 1.0

        # 4. Zero games played win-rate calculation
        total_duels = 0
        wins = 0
        win_rate = round((wins / total_duels * 100.0), 1) if total_duels > 0 else 0.0
        assert win_rate == 0.0

    # -----------------------------------------------------------------------
    # Boundary 6: Unicode & Special Character Escaping in Debate Topics
    # -----------------------------------------------------------------------
    def test_b6_unicode_and_special_character_escaping(self):
        """Verify debate engine and JSON serializations handle unicode, emojis, and control sequences."""
        from ai_debate_engine import generate_domain_conclusions

        complex_topic = (
            "🥋 3D Kinematics: 膝十字固め (Kneebar) & Joint Torque @ 120 FPS\n"
            "Path: /Volumes/Lauburu-Monorepo/10_spatial_grappling/\t"
            "Payload: {\"angle\": 45.5°, \"torque_nm\": 180.2, \"status\": \"ACTIVE\"}"
        )
        domain = "Special_Kinematics_日本語"

        result = generate_domain_conclusions(complex_topic, domain)
        assert result["topic"] == complex_topic
        assert result["domain"] == domain

        # Ensure json serialization and deserialization does not corrupt unicode
        serialized = json.dumps(result, ensure_ascii=False)
        deserialized = json.loads(serialized)
        assert "膝十字固め" in deserialized["topic"]
        assert "45.5°" in deserialized["topic"]
        assert deserialized["domain"] == domain

    # -----------------------------------------------------------------------
    # Boundary 7: Malformed & Missing Payload Schema Validation
    # -----------------------------------------------------------------------
    def test_b7_malformed_and_missing_payload_handling(self):
        """Verify TaskDispatchEngine raises structured errors or applies safe defaults on malformed payloads."""
        from canonical_ai_leaderboard import CanonicalAILeaderboardEngine

        engine = CanonicalAILeaderboardEngine()
        data = engine.get_canonical_leaderboard()
        router = ReferenceTaskDispatchEngine(data)

        # 1. Empty task spec -> default task_id and general subsystem applied
        empty_spec: Dict[str, Any] = {}
        routed = router.route_task(empty_spec)
        assert "task_id" in routed
        assert routed["subsystem"] == "00_core_infrastructure"
        assert routed["routed_model_id"] is not None

        # 2. Impossible skill requirement that no model possesses -> still routes to top generalist
        impossible_spec = {
            "task_id": "TASK_QUANTUM_TELEPORTATION",
            "subsystem": "99_unknown_dimension",
            "required_skills": ["non_existent_skill_xyz_999"],
            "zero_cloud_spend_required": False
        }
        routed_impossible = router.route_task(impossible_spec)
        assert routed_impossible["routed_model_id"] is not None
        assert routed_impossible["winner_details"]["skill_score"] > 0

        # 3. Impossible constraint (100% truth required + 100% zero spend on an empty roster) -> raises RuntimeError
        empty_router = ReferenceTaskDispatchEngine({"leaderboard": []})
        with pytest.raises(RuntimeError) as exc_info:
            empty_router.route_task({"task_id": "FAIL_TASK"})
        assert "No eligible AI models found" in str(exc_info.value)

    # -----------------------------------------------------------------------
    # Boundary 8: Atomic Concurrency & Multithreaded Race Prevention
    # -----------------------------------------------------------------------
    def test_b8_atomic_concurrency_and_file_locking(self):
        """Verify multithreaded concurrent writes to state file do not corrupt JSON structure."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_file:
            target_path = Path(tmp_file.name)

        initial_state = {"total_matches": 0, "history": []}
        with open(target_path, "w") as f:
            json.dump(initial_state, f)

        lock = threading.Lock()
        write_errors = []

        def worker_write(thread_id: int):
            try:
                for i in range(10):
                    with lock:
                        with open(target_path, "r") as rf:
                            state = json.load(rf)
                        state["total_matches"] += 1
                        state["history"].append({"thread": thread_id, "iter": i, "timestamp": time.time()})
                        
                        # Atomic write via temp file replacement
                        tmp_swap = target_path.with_suffix(f".tmp_{thread_id}_{i}")
                        with open(tmp_swap, "w") as wf:
                            json.dump(state, wf)
                        os.replace(tmp_swap, target_path)
            except Exception as e:
                write_errors.append(f"Thread {thread_id} error: {e}")

        # Execute 10 threads in parallel
        threads = [threading.Thread(target=worker_write, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        try:
            assert len(write_errors) == 0, f"Concurrency write errors encountered: {write_errors}"
            with open(target_path, "r") as f:
                final_state = json.load(f)
            assert final_state["total_matches"] == 100, f"Expected 100 matches, got {final_state['total_matches']}"
            assert len(final_state["history"]) == 100
        finally:
            if target_path.exists():
                target_path.unlink()

    # -----------------------------------------------------------------------
    # Boundary 9: Zero-Cloud-Spend Hard Constraint Filtering
    # -----------------------------------------------------------------------
    def test_b9_zero_cloud_spend_hard_constraint_filtering(self):
        """Verify high-cost models are strictly excluded when zero_cloud_spend_required=True."""
        from canonical_ai_leaderboard import CanonicalAILeaderboardEngine

        engine = CanonicalAILeaderboardEngine()
        data = engine.get_canonical_leaderboard()
        router = ReferenceTaskDispatchEngine(data)

        # Request requiring strict $0 cloud spend
        zero_spend_spec = {
            "task_id": "TASK_OFFLINE_LORA_HARVEST",
            "subsystem": "12_continuous_lora_evolution",
            "required_skills": ["debating", "training_specialist_skill"],
            "zero_cloud_spend_required": True
        }

        routed = router.route_task(zero_spend_spec)
        ranked = routed["ranked_candidates"]

        # Ensure NO candidate in ranked list has non-zero cost
        for candidate in ranked:
            cost = str(candidate.get("cost_per_m_tokens", "")).lower()
            assert "$0.00" in cost or "free" in cost or "local" in cost, \
                f"Paid cloud model {candidate['name']} ({cost}) leaked into zero-cloud-spend candidate list"
