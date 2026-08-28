"""
Comprehensive Test Suite for David vs Goliath ELO Engine & Waste Tax Calculator.
Features F7, F8, F9.
"""

import json
import math
import os
import threading
from pathlib import Path
import pytest

from src.elo import (
    CodeOffMatch,
    EloEngine,
    EloLedger,
    EloUpdateResult,
    ResourceUsage,
    WasteTaxCalculator,
    WasteTaxPenaltyEvent,
    calculate_mesh_drain_index,
    calculate_optimization_score,
    calculate_waste_tax,
    evaluate_disciplinary_action,
    DEFAULT_LAMBDA_BASE,
    ELO_QUARANTINE_THRESHOLD,
    MAX_DAVID_ELO_GAIN,
    MAX_TAX_DEDUCTION,
)


class TestEloEngineMath:
    """Mathematical verification of David vs Goliath ELO calculations (Feature F8)."""

    def test_expected_score_symmetry_and_range(self):
        engine = EloEngine()
        ea, eb = engine.calculate_expected_score(2100.0, 2800.0)
        assert 0.0 < ea < 0.05
        assert 0.95 < eb < 1.0
        assert math.isclose(ea + eb, 1.0, rel_tol=1e-6)

        # Equal ratings
        ea_eq, eb_eq = engine.calculate_expected_score(2000.0, 2000.0)
        assert math.isclose(ea_eq, 0.5, rel_tol=1e-6)
        assert math.isclose(eb_eq, 0.5, rel_tol=1e-6)

    def test_david_multiplier_scaling_and_clamping(self):
        engine = EloEngine()
        
        # High leverage case: 70B Goliath vs 0.36B David, 42GB vs 98MB, hard task (2.5)
        mu_d = engine.calculate_david_multiplier(
            param_goliath_b=70.0,
            param_david_b=0.36,
            ram_goliath_mb=42000.0,
            ram_david_mb=98.0,
            tokens_goliath=1500,
            tokens_david=350,
            task_complexity=2.5,
        )
        assert 20.0 < mu_d <= 50.0

        # Maximum clamp test: astronomical ratio
        mu_d_max = engine.calculate_david_multiplier(
            param_goliath_b=500.0,
            param_david_b=0.01,
            ram_goliath_mb=100000.0,
            ram_david_mb=10.0,
            tokens_goliath=10000,
            tokens_david=50,
            task_complexity=3.0,
        )
        assert mu_d_max == 50.0

        # Minimum clamp test: trivial task, equal size
        mu_d_min = engine.calculate_david_multiplier(
            param_goliath_b=1.0,
            param_david_b=1.0,
            ram_goliath_mb=100.0,
            ram_david_mb=100.0,
            tokens_goliath=100,
            tokens_david=100,
            task_complexity=0.1,
        )
        assert mu_d_min == 1.0

    def test_goliath_multiplier_scaling_and_clamping(self):
        engine = EloEngine()

        # Goliath on trivial task (complexity 0.20)
        mu_g = engine.calculate_goliath_multiplier(
            param_david_b=0.36,
            param_goliath_b=70.0,
            ram_david_mb=98.0,
            ram_goliath_mb=42000.0,
            task_complexity=0.20,
        )
        assert 0.01 <= mu_g < 0.50

        # Min clamp test (with normal task complexity)
        mu_g_min = engine.calculate_goliath_multiplier(
            param_david_b=0.001,
            param_goliath_b=1000.0,
            ram_david_mb=1.0,
            ram_goliath_mb=500000.0,
            task_complexity=2.0,
        )
        assert mu_g_min == 0.01

        # Max clamp test: equal sizes on hard task
        mu_g_max = engine.calculate_goliath_multiplier(
            param_david_b=10.0,
            param_goliath_b=10.0,
            ram_david_mb=1000.0,
            ram_goliath_mb=1000.0,
            task_complexity=1.0,
        )
        assert mu_g_max == 1.00

    def test_k_factor_dynamic_tiers(self):
        engine = EloEngine()
        k_init = engine.calculate_k_factor(matches_played=5, challenge_type="SHADOW_CODING_CHALLENGE")
        assert k_init == 48.0 * 1.5

        k_mid = engine.calculate_k_factor(matches_played=25, challenge_type="SHADOW_CODING_CHALLENGE")
        assert k_mid == 32.0 * 1.5

        k_veteran = engine.calculate_k_factor(matches_played=100, challenge_type="SHADOW_CODING_CHALLENGE")
        assert k_veteran == 24.0 * 1.5

        k_standard = engine.calculate_k_factor(matches_played=100, challenge_type="STANDARD_MATCH")
        assert k_standard == 24.0

    def test_david_victory_extreme_gain_clamped(self):
        engine = EloEngine()
        david_res = ResourceUsage(params_b=0.36, ram_mb=98.0, tokens=290)
        goliath_res = ResourceUsage(params_b=70.0, ram_mb=42000.0, tokens=1850)

        match = CodeOffMatch(
            task_id="task_refactor_c",
            david_model="SmolLM2-360M",
            goliath_model="Llama-3.3-70B",
            task_difficulty=2.8,
            david_solved=True,
            goliath_solved=False,
            david_resources=david_res,
            goliath_resources=goliath_res,
        )

        res = engine.record_code_off_result(match, current_elo_david=2100.0, current_elo_goliath=2850.0)
        assert res.delta_elo_david == MAX_DAVID_ELO_GAIN
        assert res.new_elo_david == 2100.0 + MAX_DAVID_ELO_GAIN

    def test_goliath_victory_on_trivial_task_yields_near_zero(self):
        engine = EloEngine()
        david_res = ResourceUsage(params_b=0.36, ram_mb=98.0, tokens=500)
        goliath_res = ResourceUsage(params_b=70.0, ram_mb=42000.0, tokens=2000)

        match = CodeOffMatch(
            task_id="task_regex_easy",
            david_model="SmolLM2-360M",
            goliath_model="Llama-3.3-70B",
            task_difficulty=0.20,
            david_solved=False,
            goliath_solved=True,
            david_resources=david_res,
            goliath_resources=goliath_res,
        )

        res = engine.record_code_off_result(match, current_elo_david=2100.0, current_elo_goliath=2800.0)
        assert 0.0 < res.delta_elo_goliath < 1.0

    def test_both_failing_asymmetric_scoring(self):
        engine = EloEngine()
        david_res = ResourceUsage(params_b=0.36, ram_mb=98.0, tokens=300)
        goliath_res = ResourceUsage(params_b=70.0, ram_mb=42000.0, tokens=3000)

        match = CodeOffMatch(
            task_id="task_impossible",
            david_model="SmolLM2-360M",
            goliath_model="Llama-3.3-70B",
            task_difficulty=3.0,
            david_solved=False,
            goliath_solved=False,
            david_resources=david_res,
            goliath_resources=goliath_res,
        )

        res = engine.record_code_off_result(match, current_elo_david=2100.0, current_elo_goliath=2800.0)
        # David loses minimal points (~ -1.3 ELO) because expected score was near zero (~0.017) and not amplified
        # Goliath loses substantial points (~ -35.4 ELO) because expected score was near 1.0 (~0.983) and full penalty applies
        assert abs(res.delta_elo_david) < 5.0
        assert abs(res.delta_elo_goliath) > 30.0
        assert abs(res.delta_elo_david) < abs(res.delta_elo_goliath)


class TestWasteTaxEngine:
    """Verification of Economic Realignment Penalty (Feature F9)."""

    def test_mesh_resource_drain_index_calculation(self):
        psi = calculate_mesh_drain_index(
            ram_locked_mb=150.0,
            excess_rtt_ms=45.0,
            battery_drain_high=True,
            flash_writes_detected=False,
        )
        assert math.isclose(psi, 0.5 + 0.45 + 1.5, rel_tol=1e-5)

        # Flash write detected
        psi_flash = calculate_mesh_drain_index(
            ram_locked_mb=0.0,
            excess_rtt_ms=0.0,
            battery_drain_high=False,
            flash_writes_detected=True,
        )
        assert psi_flash == 5.0

    def test_optimization_score_calculation(self):
        # 100% test pass rate, AST valid (0.4), 50% latency reduction (0.15), 50% RAM reduction (0.15)
        score = calculate_optimization_score(
            test_pass_rate=1.0,
            ast_valid=True,
            latency_old_ms=100.0,
            latency_new_ms=50.0,
            ram_old_mb=200.0,
            ram_new_mb=100.0,
        )
        assert math.isclose(score, 0.40 + 0.15 + 0.15, rel_tol=1e-5)

        # Failed tests => 0 optimization score
        score_fail = calculate_optimization_score(
            test_pass_rate=0.0,
            ast_valid=True,
            latency_old_ms=100.0,
            latency_new_ms=50.0,
        )
        assert score_fail == 0.0

    def test_waste_tax_four_severity_tiers(self):
        calc = WasteTaxCalculator()
        # Tier 1: Minor Inefficiency
        t1 = calc.calculate_tax(spend_usd=0.01, tokens_wasted=500, spurious_calls=0, mesh_drain_index=0.2, optimization_score=0.40)
        # Tier 2: Hallucination / Build Break
        t2 = calc.calculate_tax(spend_usd=0.05, tokens_wasted=2048, spurious_calls=2, mesh_drain_index=0.8, optimization_score=0.0)
        # Tier 3: Severe Resource Gluttony
        t3 = calc.calculate_tax(spend_usd=0.20, tokens_wasted=8192, spurious_calls=6, mesh_drain_index=2.0, optimization_score=0.0)
        # Tier 4: Mesh Threat / Flash Invariant Violation
        t4 = calc.calculate_tax(spend_usd=0.50, tokens_wasted=16384, spurious_calls=10, mesh_drain_index=5.0, optimization_score=0.0)

        assert abs(t1) < abs(t2) < abs(t3) < abs(t4)
        assert t4 >= MAX_TAX_DEDUCTION  # Respects max deduction cap

    def test_zero_waste_tax_when_threshold_met(self):
        tax = calculate_waste_tax(
            spend_usd=0.50,
            tokens_wasted=10000,
            spurious_calls=5,
            mesh_drain_index=3.0,
            optimization_score=0.85,
            threshold=0.50,
        )
        assert tax == 0.0

    def test_super_linear_scaling_gamma(self):
        # 2x spend leads to >2x penalty due to gamma = 1.25
        tax_1x = calculate_waste_tax(spend_usd=0.05, tokens_wasted=0, spurious_calls=0, mesh_drain_index=0.0, optimization_score=0.0)
        tax_2x = calculate_waste_tax(spend_usd=0.10, tokens_wasted=0, spurious_calls=0, mesh_drain_index=0.0, optimization_score=0.0)
        
        ratio = abs(tax_2x) / abs(tax_1x)
        assert ratio > 2.0  # 2^1.25 ≈ 2.378

    def test_auto_revocation_below_1500_elo(self):
        verdict = evaluate_disciplinary_action(
            tax_amount=-75.0,
            current_elo=1550.0,
        )
        # 1550 - 75 = 1475 (< 1500 quarantine threshold)
        assert verdict.new_elo == 1475.0
        assert verdict.revoke_cloud is True
        assert "Auto-revoked cloud credentials below 1500.0 ELO" in verdict.action

    def test_waste_tax_penalty_event_json_schema(self):
        calc = WasteTaxCalculator()
        event, verdict = calc.evaluate_penalty_event(
            agent_id="agent_rogue_01",
            current_elo=1800.0,
            spend_usd=0.15,
            tokens_wasted=4096,
            spurious_calls=4,
            mesh_drain_index=2.0,
            optimization_score=0.0,
        )

        d = event.to_dict()
        assert d["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert d["agent_id"] == "agent_rogue_01"
        assert d["elo_deduction"] < -75.0
        assert d["cost_spent_usd"] == 0.15
        assert d["tokens_wasted"] == 4096
        assert "Tier" in d["disciplinary_action"] or "Tier" in d["disciplinary_tier"]


class TestEloLedger:
    """Verification of Atomic Transaction Ledger (Features F7.5, F8, F9)."""

    def test_record_match_and_retrieve_history(self, tmp_path):
        ledger_file = tmp_path / "elo_ledger.jsonl"
        ledger = EloLedger(str(ledger_file))

        ledger.record_match({
            "match_id": "match_001",
            "david_model": "SmolLM2-360M",
            "goliath_model": "Llama-3.3-70B",
            "task_id": "task_ast_refactor",
            "david_solved": True,
            "goliath_solved": False,
            "delta_elo_david": 350.0,
            "delta_elo_goliath": -35.0,
            "new_elo_david": 2450.0,
            "new_elo_goliath": 2765.0,
        })

        history = ledger.get_history()
        assert len(history) == 1
        assert history[0]["match_id"] == "match_001"

        history_david = ledger.get_history(agent_id="SmolLM2-360M")
        assert len(history_david) == 1

        history_unknown = ledger.get_history(agent_id="NonExistent")
        assert len(history_unknown) == 0

    def test_leaderboard_aggregation_and_ratings(self, tmp_path):
        ledger_file = tmp_path / "elo_ledger.jsonl"
        ledger = EloLedger(str(ledger_file))

        ledger.record_match({
            "david_model": "SmolLM2-360M",
            "goliath_model": "Llama-3.3-70B",
            "david_solved": True,
            "goliath_solved": False,
            "new_elo_david": 2450.0,
            "new_elo_goliath": 2765.0,
        })

        board = ledger.get_leaderboard()
        assert "SmolLM2-360M" in board
        assert board["SmolLM2-360M"]["rating"] == 2450.0
        assert board["SmolLM2-360M"]["wins"] == 1
        assert board["SmolLM2-360M"]["losses"] == 0

        assert "Llama-3.3-70B" in board
        assert board["Llama-3.3-70B"]["rating"] == 2765.0
        assert board["Llama-3.3-70B"]["losses"] == 1

        assert ledger.get_rating("SmolLM2-360M") == 2450.0
        assert ledger.get_match_count("SmolLM2-360M") == 1

    def test_waste_tax_penalty_updates_rating_and_quarantine(self, tmp_path):
        ledger_file = tmp_path / "elo_ledger.jsonl"
        ledger = EloLedger(str(ledger_file))

        ledger.record_penalty({
            "agent_id": "rogue_model_01",
            "cost_spent_usd": 0.30,
            "tokens_wasted": 8000,
            "elo_deduction": -700.0,
            "new_elo": 1400.0,
            "disciplinary_action": "Quarantined",
        })

        assert ledger.get_rating("rogue_model_01") == 1400.0
        assert ledger.is_quarantined("rogue_model_01") is True

    def test_concurrent_multithreaded_writes(self, tmp_path):
        ledger_file = tmp_path / "concurrent_ledger.jsonl"
        ledger = EloLedger(str(ledger_file))

        num_threads = 10
        records_per_thread = 20

        def worker(thread_idx: int):
            for i in range(records_per_thread):
                ledger.record_match({
                    "match_id": f"th_{thread_idx}_m_{i}",
                    "david_model": f"model_{thread_idx}",
                    "goliath_model": "frontier_base",
                    "david_solved": True,
                    "goliath_solved": False,
                    "delta_elo_david": 10.0,
                    "delta_elo_goliath": -2.0,
                })

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        history = ledger.get_history()
        assert len(history) == num_threads * records_per_thread

    def test_export_canonical_leaderboard(self, tmp_path):
        ledger_file = tmp_path / "elo_ledger.jsonl"
        export_file = tmp_path / "canonical_ai_leaderboard.json"

        ledger = EloLedger(str(ledger_file))
        ledger.record_match({
            "david_model": "SmolLM2-360M",
            "goliath_model": "Llama-3.3-70B",
            "david_solved": True,
            "goliath_solved": True,
            "new_elo_david": 2450.0,
            "new_elo_goliath": 2800.2,
        })

        ledger.export_canonical_leaderboard(str(export_file))
        assert export_file.exists()

        content = json.loads(export_file.read_text(encoding="utf-8"))
        assert content["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert content["title"] == "CanonicalAILeaderboard"
        assert content["total_agents"] == 2
        assert "SmolLM2-360M" in content["agents"]


class TestEloIntegration:
    """Full lifecycle integration between EloEngine, WasteTaxCalculator, and EloLedger."""

    def test_full_match_and_waste_tax_lifecycle(self, tmp_path):
        ledger_file = tmp_path / "full_lifecycle_ledger.jsonl"
        ledger = EloLedger(str(ledger_file))
        engine = EloEngine()

        david_res = ResourceUsage(
            params_b=0.36,
            ram_mb=98.0,
            tokens=280,
            execution_time_s=0.45,
            spend_usd=0.0,
        )
        goliath_res = ResourceUsage(
            params_b=70.0,
            ram_mb=42000.0,
            tokens=1850,
            execution_time_s=12.5,
            spend_usd=0.15,
            spurious_calls=3,
            mesh_drain_index=1.8,
        )

        # Match: David solves, Goliath fails and wastes $0.15 API spend
        match = CodeOffMatch(
            task_id="challenge_openwrt_healing",
            david_model="SmolLM2-360M",
            goliath_model="Cloud-70B-Rogue",
            task_difficulty=2.5,
            david_solved=True,
            goliath_solved=False,
            david_resources=david_res,
            goliath_resources=goliath_res,
        )

        result = engine.record_code_off_result(
            match=match,
            current_elo_david=2100.0,
            current_elo_goliath=2800.0,
            ledger=ledger,
        )

        assert result.delta_elo_david == 350.0
        assert result.new_elo_david == 2450.0
        # Goliath lost base ELO + waste tax deduction
        assert result.waste_tax_applied < -75.0
        assert result.new_elo_goliath == 2800.0 + result.delta_elo_goliath

        # Check ledger recorded match
        history = ledger.get_history()
        assert len(history) == 1
        assert history[0]["task_id"] == "challenge_openwrt_healing"
        assert history[0]["david_model"] == "SmolLM2-360M"

        # Check leaderboard
        board = ledger.get_leaderboard()
        assert board["SmolLM2-360M"]["rating"] == 2450.0
        assert board["SmolLM2-360M"]["wins"] == 1
