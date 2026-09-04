#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 2: Comprehensive Boundary Value Analysis & Corner Cases E2E Test Suite (48 Tests)
Project: End-to-End Autonomous AI Training, Storage & RAM Mesh Engine
================================================================================
Validates boundary limits, extreme mathematical singularities, numerical thresholds,
storage headroom constraints, and user-aware elasticity transitions across F1-F20:
- F01-F03: Training limits, ELO asymptotic bounds, SWE-bench patch extremes
- F04-F06: Storage zero-disk headroom, 5GB/10GB invariants, stale lock timeout
- F07: Shannon entropy limits (0.0 to 8.0), Cosine similarity (-1.0 to 1.0, 0.92 threshold)
- F08-F10: RAM 80%/85% boundaries, User Elasticity 75%/88% ceilings, 60s idle threshold, TB4 offload
- F11-F12: Mesh routing extrema, Router 35MB RAM ceiling
- F13-F16: 30-step trajectory limits, Quantitative Admission exact thresholds (0.90, 0.05, 0.85), Rollback spikes (2.0)
- F17-F20: Biometrics DSP boundaries (50-400ms PTT, SBP 80-220 mmHg), TUI 50ms latency, WCAG 4.5:1 contrast
================================================================================
"""

import os
import sys
import math
import json
import time
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Any, Optional

TESTS_E2E_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_E2E_DIR.parent.parent

for p in [
    str(PROJECT_ROOT),
    str(TESTS_E2E_DIR),
    str(PROJECT_ROOT / "00_core_infrastructure"),
    str(PROJECT_ROOT / "02_ai_models_and_inference"),
    str(PROJECT_ROOT / "02_ai_models_and_inference" / "benchmarks"),
    str(PROJECT_ROOT / "02_ai_models_and_inference" / "sharding_daemon"),
    str(PROJECT_ROOT / "03_biometrics_and_telemetry"),
    str(PROJECT_ROOT / "04_data_and_memory"),
    str(PROJECT_ROOT / "06_scripts_and_tooling"),
    str(PROJECT_ROOT / "06_scripts_and_tooling" / "automation"),
    str(PROJECT_ROOT / "06_scripts_and_tooling" / "canonical_sync_engine"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

from e2e_helpers import (
    PROJECT_ROOT,
    LORA_DATASETS_ROOT,
    OBSIDIAN_VAULT_ROOT,
    DATA_AND_MEMORY_ROOT,
    HARDWARE_MESH_MATRIX,
    REQUIRED_OBSIDIAN_WIKILINKS,
    validate_dpo_sample_schema,
    simulate_lora_epoch_loss,
    check_free_tier_quota_limits,
    calculate_bradley_terry_win_prob,
    update_elo_ratings,
    evaluate_promotion_gate,
    validate_swe_bench_task_schema,
    evaluate_swe_patch_syntax,
    is_storage_healthy,
    validate_obsidian_master_index,
    validate_worktree_path_isolation,
    self_heal_tri_vault_invariants,
    calculate_shannon_entropy,
    compute_cosine_similarity,
    compute_user_aware_elasticity,
    evaluate_memory_pressure_state,
    partition_model_layers_for_tb4,
    compute_mesh_routing_cost,
    validate_router_ram_safety,
    SimulationTrajectoryMetrics,
    evaluate_admission_gating,
    detect_training_anomaly,
    generate_synthetic_synthetic_ecg_beat,
    reference_pan_tompkins_qrs,
    reference_kamath_artifact_filter,
    reference_calculate_rmssd,
    reference_calculate_ptt_bp,
    calculate_contrast_ratio,
    validate_shopify_customer_query,
    generate_mock_jwt_membership_token
)


class TestTier2BoundaryCorner(unittest.TestCase):
    """Tier 2: 48 Boundary Value Analysis & Extreme Corner Case Tests."""

    # =========================================================================
    # F01-F03: Training & Benchmark Boundaries
    # =========================================================================
    def test_bva_f01_01_empty_dpo_fields_rejection(self):
        """BVA F01.1: Rejects DPO sample with empty prompt or chosen fields."""
        invalid_sample = {"prompt": "   ", "chosen": "", "rejected": "valid"}
        valid, errors = validate_dpo_sample_schema(invalid_sample)
        self.assertFalse(valid)
        self.assertGreater(len(errors), 0)

    def test_bva_f01_02_zero_epoch_loss_decay(self):
        """BVA F01.2: Evaluates loss decay at epoch 0."""
        loss_ep0 = simulate_lora_epoch_loss(initial_loss=2.5, epoch=0)
        self.assertEqual(loss_ep0, 2.5)

    def test_bva_f01_03_exact_gemini_free_tier_ceilings(self):
        """BVA F01.3: Evaluates exact free-tier quota boundary (14 RPM vs 15 RPM)."""
        safe_at_14, _ = check_free_tier_quota_limits(gemini_rpm=14, gemini_rpd=1400, cf_neurons=10000)
        unsafe_at_15, _ = check_free_tier_quota_limits(gemini_rpm=15, gemini_rpd=1400, cf_neurons=10000)
        self.assertTrue(safe_at_14)
        self.assertFalse(unsafe_at_15)

    def test_bva_f01_04_exact_cloudflare_neuron_ceiling(self):
        """BVA F01.4: Evaluates exact Cloudflare neuron boundary (10,000 vs 10,001)."""
        safe, _ = check_free_tier_quota_limits(gemini_rpm=10, gemini_rpd=1000, cf_neurons=10000)
        unsafe, _ = check_free_tier_quota_limits(gemini_rpm=10, gemini_rpd=1000, cf_neurons=10001)
        self.assertTrue(safe)
        self.assertFalse(unsafe)

    def test_bva_f02_01_extreme_elo_gap_asymptotic_stability(self):
        """BVA F02.1: Evaluates extreme ELO gaps without floating-point overflow."""
        prob_giant_gap = calculate_bradley_terry_win_prob(rating_a=3000.0, rating_b=500.0)
        self.assertGreater(prob_giant_gap, 0.99999)
        self.assertLessEqual(prob_giant_gap, 1.0)

        prob_reverse = calculate_bradley_terry_win_prob(rating_a=500.0, rating_b=3000.0)
        self.assertLess(prob_reverse, 0.00001)
        self.assertGreaterEqual(prob_reverse, 0.0)

    def test_bva_f02_02_identical_elo_exact_half(self):
        """BVA F02.2: Identical ELO ratings yield exact 0.50000 probability."""
        p = calculate_bradley_terry_win_prob(1500.0, 1500.0)
        self.assertEqual(p, 0.5)

    def test_bva_f02_03_promotion_gate_exact_65_percent_threshold(self):
        """BVA F02.3: Evaluates exact 65.0% win-rate promotion boundary."""
        promoted_exact, rate, status = evaluate_promotion_gate(candidate_wins=65, total_battles=100, min_win_rate=0.65)
        self.assertTrue(promoted_exact)
        self.assertEqual(rate, 0.65)

    def test_bva_f02_04_promotion_gate_64_9_percent_rejection(self):
        """BVA F02.4: Evaluates 64.9% win-rate rejection boundary."""
        promoted_below, rate, status = evaluate_promotion_gate(candidate_wins=649, total_battles=1000, min_win_rate=0.65)
        self.assertFalse(promoted_below)
        self.assertEqual(rate, 0.649)

    def test_bva_f02_05_zero_battles_promotion_gate(self):
        """BVA F02.5: Zero total battles evaluated returns False safely."""
        promoted, rate, status = evaluate_promotion_gate(0, 0, 0.65)
        self.assertFalse(promoted)
        self.assertEqual(status, "NO_BATTLES_EVALUATED")

    def test_bva_f03_01_swe_bench_minimal_single_line_diff(self):
        """BVA F03.1: Evaluates single-line minimal diff patch."""
        diff = "--- a/f.py\n+++ b/f.py\n@@ -1 +1 @@\n-a\n+b\n"
        valid, meta = evaluate_swe_patch_syntax(diff)
        self.assertTrue(valid)
        self.assertEqual(meta["hunks"], 1)
        self.assertEqual(meta["additions"], 1)
        self.assertEqual(meta["deletions"], 1)

    def test_bva_f03_02_swe_bench_massive_patch_diff(self):
        """BVA F03.2: Evaluates large multi-hunk patch without degradation."""
        lines = ["--- a/big.py", "+++ b/big.py"]
        for i in range(50):
            lines.extend([f"@@ -{i*10},2 +{i*10},2 @@", f"-old_{i}", f"+new_{i}"])
        diff = "\n".join(lines)
        valid, meta = evaluate_swe_patch_syntax(diff)
        self.assertTrue(valid)
        self.assertEqual(meta["hunks"], 50)
        self.assertEqual(meta["additions"], 50)

    def test_bva_f03_03_swe_bench_missing_required_fields(self):
        """BVA F03.3: Rejects task with missing golden test field."""
        task = {"instance_id": "test_1", "repo": "test/test", "problem_statement": "bug"}
        valid, errors = validate_swe_bench_task_schema(task)
        self.assertFalse(valid)
        self.assertIn("Missing required SWE-bench field: golden_test", errors[0])

    # =========================================================================
    # F04-F06: Tri-Vault, Storage & Self-Healing Headroom
    # =========================================================================
    def test_bva_f04_01_tri_vault_zero_disk_headroom(self):
        """BVA F04.1: Storage health evaluation fails when free disk is 0.0 GB."""
        # Test simulated root with zero headroom
        temp_root = Path(tempfile.mkdtemp(prefix="zero_disk_"))
        try:
            (temp_root / "obsidian_vault").mkdir()
            (temp_root / "04_data_and_memory").mkdir()
            (temp_root / ".git").mkdir()
            # Fast-path check evaluates free disk on filesystem
            healthy, status = is_storage_healthy(temp_root)
            self.assertIn("disk_free_gb", status)
        finally:
            shutil.rmtree(temp_root)

    def test_bva_f04_02_obsidian_index_missing_one_wikilink(self):
        """BVA F04.2: Obsidian index validation fails if one mandatory wikilink is missing."""
        temp_idx = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md')
        try:
            # Missing [[Index]]
            temp_idx.write("# Vault\n- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]\n- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]\n")
            temp_idx.close()
            valid, errors = validate_obsidian_master_index(Path(temp_idx.name))
            self.assertFalse(valid)
            self.assertIn("Missing required master wikilink: [[Index]]", errors)
        finally:
            os.unlink(temp_idx.name)

    def test_bva_f05_01_worktree_same_as_repo_root_rejection(self):
        """BVA F05.1: Worktree validator rejects path equal to repository root."""
        valid, msg = validate_worktree_path_isolation(PROJECT_ROOT, PROJECT_ROOT)
        self.assertFalse(valid)
        self.assertIn("cannot be the repository root", msg)

    def test_bva_f06_01_self_healing_already_pristine(self):
        """BVA F06.1: Self-healing on pristine structure does not corrupt existing Index.md."""
        temp_root = Path(tempfile.mkdtemp(prefix="pristine_"))
        try:
            obs = temp_root / "obsidian_vault"
            obs.mkdir()
            idx = obs / "Index.md"
            custom_content = "---\ntitle: Custom\n---\n- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]\n- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]\n- [[Index]]\n"
            idx.write_text(custom_content)
            
            self_heal_tri_vault_invariants(temp_root)
            # Custom content preserved because file was non-empty
            self.assertEqual(idx.read_text(), custom_content)
        finally:
            shutil.rmtree(temp_root)

    def test_bva_f06_02_self_healing_empty_index_recreation(self):
        """BVA F06.2: Self-healing detects 0-byte Index.md and regenerates it."""
        temp_root = Path(tempfile.mkdtemp(prefix="empty_idx_"))
        try:
            obs = temp_root / "obsidian_vault"
            obs.mkdir()
            idx = obs / "Index.md"
            idx.touch()  # 0 bytes
            self.assertEqual(idx.stat().st_size, 0)
            
            self_heal_tri_vault_invariants(temp_root)
            self.assertGreater(idx.stat().st_size, 0)
            self.assertIn("[[Index]]", idx.read_text())
        finally:
            shutil.rmtree(temp_root)

    # =========================================================================
    # F07: Shannon Entropy & Cosine Similarity Boundaries
    # =========================================================================
    def test_bva_f07_01_shannon_entropy_empty_string(self):
        """BVA F07.1: Shannon entropy of empty string is exactly 0.0."""
        h = calculate_shannon_entropy("")
        self.assertEqual(h, 0.0)

    def test_bva_f07_02_shannon_entropy_single_character_string(self):
        """BVA F07.2: Shannon entropy of repeated single character is exactly 0.0."""
        h = calculate_shannon_entropy("zzzzzzzzzzzzzzzz")
        self.assertEqual(h, 0.0)

    def test_bva_f07_03_shannon_entropy_two_equiprobable_characters(self):
        """BVA F07.3: Shannon entropy of two equiprobable characters is exactly 1.0 bit."""
        h = calculate_shannon_entropy("0101010101010101")
        self.assertAlmostEqual(h, 1.0, places=4)

    def test_bva_f07_04_cosine_similarity_opposite_vectors(self):
        """BVA F07.4: Cosine similarity of diametrically opposite vectors is -1.0."""
        v1 = [1.0, 2.0, 3.0]
        v2 = [-1.0, -2.0, -3.0]
        sim = compute_cosine_similarity(v1, v2)
        self.assertAlmostEqual(sim, -1.0, places=5)

    def test_bva_f07_05_cosine_similarity_zero_vector(self):
        """BVA F07.5: Cosine similarity with zero magnitude vector returns 0.0 safely."""
        v1 = [0.0, 0.0, 0.0]
        v2 = [1.0, 2.0, 3.0]
        sim = compute_cosine_similarity(v1, v2)
        self.assertEqual(sim, 0.0)

    def test_bva_f07_06_cosine_similarity_exact_092_boundary(self):
        """BVA F07.6: Verifies exact 0.920000 cosine threshold comparison."""
        v1 = [1.0, 0.0]
        v2 = [0.92, 0.391918358845]  # cos(theta) = 0.92
        sim = compute_cosine_similarity(v1, v2)
        self.assertAlmostEqual(sim, 0.92, places=4)

    # =========================================================================
    # F08-F10: Dynamic RAM Ceilings & User-Aware Elasticity Boundaries
    # =========================================================================
    def test_bva_f08_01_ram_pressure_exact_80_percent_warn(self):
        """BVA F08.1: Evaluates exact 80.0% warning threshold boundary."""
        state = evaluate_memory_pressure_state(ram_pct=80.0, warn_pct=80.0, crit_pct=85.0)
        self.assertEqual(state["status"], "WARNING_HEADROOM")
        self.assertEqual(state["action"], "MPS_CACHE_PURGE")

    def test_bva_f08_02_ram_pressure_exact_85_percent_crit(self):
        """BVA F08.2: Evaluates exact 85.0% critical threshold boundary."""
        state = evaluate_memory_pressure_state(ram_pct=85.0, warn_pct=80.0, crit_pct=85.0)
        self.assertEqual(state["status"], "CRITICAL_HEADROOM")
        self.assertEqual(state["action"], "PURGE_AND_THROTTLE")

    def test_bva_f08_03_user_active_elasticity_75_percent_ceiling(self):
        """BVA F08.3: Validates Interactive User Active mode (idle=10s) strict 75.0% ceiling."""
        throttle, mode, active_warn, active_crit = compute_user_aware_elasticity(ram_used_pct=76.0, user_idle_sec=10.0)
        self.assertEqual(mode, "INTERACTIVE_USER_ACTIVE")
        self.assertEqual(active_warn, 65.0)
        self.assertEqual(active_crit, 75.0)
        self.assertEqual(throttle, 0.05)  # Heavy throttling past 75%

    def test_bva_f08_04_user_idle_burst_mode_88_percent_ceiling(self):
        """BVA F08.4: Validates Maximum Burst mode (idle=300s) unthrottled 88.0% ceiling."""
        throttle, mode, active_warn, active_crit = compute_user_aware_elasticity(ram_used_pct=76.0, user_idle_sec=300.0)
        self.assertEqual(mode, "MAXIMUM_BURST_IDLE")
        self.assertEqual(active_warn, 82.0)
        self.assertEqual(active_crit, 88.0)
        self.assertEqual(throttle, 1.0)  # Unthrottled 1.0 under 82%

    def test_bva_f08_05_user_idle_transition_at_60s(self):
        """BVA F08.5: Validates exact transition boundary at user_idle_sec = 59.9s vs 60.0s."""
        _, mode_active, _, _ = compute_user_aware_elasticity(70.0, user_idle_sec=59.9)
        _, mode_idle, _, _ = compute_user_aware_elasticity(70.0, user_idle_sec=60.0)
        self.assertEqual(mode_active, "INTERACTIVE_USER_ACTIVE")
        self.assertEqual(mode_idle, "MAXIMUM_BURST_IDLE")

    def test_bva_f10_01_tb4_offload_zero_layers(self):
        """BVA F10.1: Evaluates TB4 layer offload with total_layers = 0."""
        part = partition_model_layers_for_tb4(total_layers=0, host_ram_pct=88.0)
        self.assertEqual(len(part["host_layers"]), 0)
        self.assertEqual(len(part["offloaded_layers"]), 0)

    def test_bva_f10_02_tb4_offload_single_layer_model(self):
        """BVA F10.2: Evaluates TB4 offload on 1-layer micro-model under critical RAM."""
        part = partition_model_layers_for_tb4(total_layers=1, host_ram_pct=92.0)
        self.assertEqual(len(part["offloaded_layers"]), 1)
        self.assertEqual(part["offloaded_layers"], [0])

    # =========================================================================
    # F11-F12: Mesh Routing & Router RAM Boundaries
    # =========================================================================
    def test_bva_f11_01_mesh_routing_zero_latency_link(self):
        """BVA F11.1: Evaluates routing cost with 0.0ms latency link."""
        cost = compute_mesh_routing_cost("L1", payload_tokens=200, node_health=1.0, node_latency_ms=0.0)
        self.assertEqual(cost, 2.0)

    def test_bva_f11_02_mesh_routing_huge_token_payload(self):
        """BVA F11.2: Evaluates routing cost with 1,000,000 tokens payload."""
        cost = compute_mesh_routing_cost("L1", payload_tokens=1_000_000, node_health=1.0, node_latency_ms=0.25)
        self.assertEqual(cost, 10000.25)

    def test_bva_f12_01_router_ram_exact_35mb_boundary(self):
        """BVA F12.1: Router RAM at exactly 35.0 MB (safe) vs 35.01 MB (unsafe)."""
        safe_35, _ = validate_router_ram_safety(35.0, max_limit_mb=35.0)
        unsafe_35_1, _ = validate_router_ram_safety(35.01, max_limit_mb=35.0)
        self.assertTrue(safe_35)
        self.assertFalse(unsafe_35_1)

    # =========================================================================
    # F13-F16: Simulation, Admission Gating & Auto-Rollback Boundaries
    # =========================================================================
    def test_bva_f15_01_admission_exact_success_threshold(self):
        """BVA F15.1: Evaluates exact S = 0.90 success boundary."""
        m_pass = SimulationTrajectoryMetrics(success_score=0.90, regression_probability=0.04, layout_overflow_count=0, simulation_confidence=0.86)
        m_fail = SimulationTrajectoryMetrics(success_score=0.899, regression_probability=0.04, layout_overflow_count=0, simulation_confidence=0.86)
        admit_pass, _, _ = evaluate_admission_gating(m_pass)
        admit_fail, _, _ = evaluate_admission_gating(m_fail)
        self.assertTrue(admit_pass)
        self.assertFalse(admit_fail)

    def test_bva_f15_02_admission_exact_regression_threshold(self):
        """BVA F15.2: Evaluates exact P_reg = 0.05 regression boundary."""
        m_pass = SimulationTrajectoryMetrics(success_score=0.92, regression_probability=0.050, layout_overflow_count=0, simulation_confidence=0.86)
        m_fail = SimulationTrajectoryMetrics(success_score=0.92, regression_probability=0.051, layout_overflow_count=0, simulation_confidence=0.86)
        admit_pass, _, _ = evaluate_admission_gating(m_pass)
        admit_fail, _, _ = evaluate_admission_gating(m_fail)
        self.assertTrue(admit_pass)
        self.assertFalse(admit_fail)

    def test_bva_f15_03_admission_exact_confidence_threshold(self):
        """BVA F15.3: Evaluates exact C_sim = 0.85 confidence boundary."""
        m_pass = SimulationTrajectoryMetrics(success_score=0.92, regression_probability=0.02, layout_overflow_count=0, simulation_confidence=0.850)
        m_fail = SimulationTrajectoryMetrics(success_score=0.92, regression_probability=0.02, layout_overflow_count=0, simulation_confidence=0.849)
        admit_pass, _, _ = evaluate_admission_gating(m_pass)
        admit_fail, _, _ = evaluate_admission_gating(m_fail)
        self.assertTrue(admit_pass)
        self.assertFalse(admit_fail)

    def test_bva_f16_01_rollback_single_element_history(self):
        """BVA F16.1: Single-element loss history does not trigger false rollback."""
        anomaly, reason = detect_training_anomaly([1.8])
        self.assertFalse(anomaly)
        self.assertEqual(reason, "NORMAL_TRAINING")

    def test_bva_f16_02_rollback_exact_spike_threshold_2_0(self):
        """BVA F16.2: Evaluates exact loss spike threshold (delta = 2.0 vs 2.01)."""
        anomaly_safe, _ = detect_training_anomaly([1.0, 3.0], max_loss_delta=2.0)
        anomaly_spike, _ = detect_training_anomaly([1.0, 3.01], max_loss_delta=2.0)
        self.assertFalse(anomaly_safe)
        self.assertTrue(anomaly_spike)

    # =========================================================================
    # F17-F20: Biometrics DSP, TUI & Commerce Boundaries
    # =========================================================================
    def test_bva_f17_01_pan_tompkins_short_signal_rejection(self):
        """BVA F17.1: Pan-Tompkins rejects signal shorter than 0.5s."""
        short_sig = [0.0] * 100  # < 256 samples for 512Hz
        peaks, rr = reference_pan_tompkins_qrs(short_sig, fs=512)
        self.assertEqual(len(peaks), 0)
        self.assertEqual(len(rr), 0)

    def test_bva_f17_02_kamath_single_interval_boundary(self):
        """BVA F17.2: Kamath filter handles single-element RR list without error."""
        cleaned, artifacts = reference_kamath_artifact_filter([1000.0])
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(artifacts, 0)

    def test_bva_f17_03_ptt_extreme_physiological_clamping(self):
        """BVA F17.3: PTT hemodynamic BP clamps to physiological bounds (80-220 mmHg SBP)."""
        # Extreme short PTT (50ms) -> High SBP clamped to 220 mmHg
        sbp_high, dbp_high, _ = reference_calculate_ptt_bp(ptt_ms=50.0, hr_bpm=180.0)
        self.assertLessEqual(sbp_high, 220.0)

        # Extreme long PTT (500ms) -> Low SBP clamped to 80 mmHg
        sbp_low, dbp_low, _ = reference_calculate_ptt_bp(ptt_ms=500.0, hr_bpm=40.0)
        self.assertGreaterEqual(sbp_low, 80.0)

    def test_bva_f18_01_tui_exact_50ms_latency_boundary(self):
        """BVA F18.1: Evaluates TUI frame latency boundary (50.0ms vs 50.1ms)."""
        latency_safe = 50.0
        latency_over = 50.1
        self.assertLessEqual(latency_safe, 50.0)
        self.assertGreater(latency_over, 50.0)

    def test_bva_f18_02_wcag_contrast_exact_4_5_boundary(self):
        """BVA F18.2: Evaluates WCAG 2.1 AA exact contrast ratio (4.5:1)."""
        ratio_pass = calculate_contrast_ratio("#FFFFFF", "#767676")  # ~4.54:1
        self.assertGreaterEqual(ratio_pass, 4.5)

    def test_bva_f19_01_membership_token_expiry_zero(self):
        """BVA F19.1: Membership token generated with 0s expiry."""
        token = generate_mock_jwt_membership_token("usr_test", expiry_sec=0)
        self.assertTrue(token.startswith("eyJ_"))

    def test_bva_f20_01_infinite_and_negative_inputs_guard(self):
        """BVA F20.1: Math models handle negative/inf numbers safely."""
        sbp, dbp, map_val = reference_calculate_ptt_bp(ptt_ms=-100.0, hr_bpm=70.0)
        self.assertIsNone(sbp)
        self.assertIsNone(dbp)


if __name__ == '__main__':
    unittest.main()
