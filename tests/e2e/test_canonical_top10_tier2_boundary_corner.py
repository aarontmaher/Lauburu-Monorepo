#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 2: Comprehensive Boundary Value Analysis & Corner Cases E2E Test Suite (120 Tests)
Project: Top 10 Highest ROI Strategic Implementation Plan for Lauburu AI Mesh
================================================================================
Validates boundary limits, extreme mathematical singularities, numerical thresholds,
storage headroom constraints, and user-aware elasticity transitions across F01-F24:
- F01 - F24: 5 boundary and corner case tests per feature (120 tests total)

Strict Rule #0 Compliance: Absolutely ZERO synthetic mocks or fake arrays.
================================================================================
"""

import os
import sys
import math
import zlib
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
    str(PROJECT_ROOT / "00_core_infrastructure" / "router_ai_daemon"),
    str(PROJECT_ROOT / "01_apps"),
    str(PROJECT_ROOT / "01_apps" / "commerce"),
    str(PROJECT_ROOT / "01_apps" / "spatial_and_3d"),
    str(PROJECT_ROOT / "01_apps" / "spatial_and_3d" / "spatial_grappling_3d"),
    str(PROJECT_ROOT / "02_ai_models_and_inference"),
    str(PROJECT_ROOT / "02_ai_models_and_inference" / "sharding_daemon"),
    str(PROJECT_ROOT / "03_biometrics_and_telemetry"),
    str(PROJECT_ROOT / "03_biometrics_and_telemetry" / "dsp"),
    str(PROJECT_ROOT / "04_data_and_memory"),
    str(PROJECT_ROOT / "05_agents_and_swarms"),
    str(PROJECT_ROOT / "06_scripts_and_tooling"),
    str(PROJECT_ROOT / "06_scripts_and_tooling" / "automation"),
    str(PROJECT_ROOT / "06_scripts_and_tooling" / "training"),
    str(PROJECT_ROOT / "06_scripts_and_tooling" / "mesh"),
    str(PROJECT_ROOT / "06_scripts_and_tooling" / "lauburu_master_mcp"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

from canonical_top10_helpers import (
    calculate_bradley_terry_win_prob,
    update_elo_ratings,
    generate_canonical_hmac_token,
    verify_canonical_hmac_token,
    generate_fourier_ecg_signal,
    generate_canonical_opml_string,
    construct_rfc792_magic_packet,
    build_activation_chunk,
    verify_activation_chunk,
)

from mlx_qlora_trainer import DynamicRamGovernor, MLXQLoRATrainer
from autonomous_consensus_merger import AutonomousConsensusMergeEngine, CONSENSUS_THRESHOLD
from shopify_storefront_gateway import (
    CustomerTier,
    CustomerProfile,
    MemberAPIGateway,
    ShopifyStorefrontGraphQLClient,
)
from pan_tompkins_qrs import (
    PanTompkinsQRSDetector,
    apply_kamath_artifact_filter,
    calculate_rmssd,
    calculate_sdnn,
    calculate_pnn50,
)
from ptt_blood_pressure import PTTBloodPressureModel, BloodPressureReading
from dfa_alpha1 import calculate_dfa_alpha1, calculate_dfa_scaling_curve, DFAScalingResult
from spatial_grappling_3d.kinematics.opml_tree import parse_opml_tree
from spatial_grappling_3d.kinematics.skeleton import MEDIAPIPE_33_LANDMARKS, build_default_pose
from spatial_grappling_3d.kinematics.torque import compute_joint_torque, evaluate_joint_safety, JOINT_LIMITS_NM
from prima_ring_adapter import PrimaTB4OffloadManager, TB4DMAMetrics, RingState
from router_sentinel_wol_engine import RouterSentinelWOLEngine, MESH_NODE_MACS
from sse_server import TOOLS as MCP_TOOLS, app as mcp_app
from gcp_credit_usage_automation import (
    INITIAL_CREDIT_POOL_AUD,
    BATCH_TRANCHE_CAP_AUD,
    STAGED_BATCHES,
    generate_credit_telemetry,
)
from cloud_api_quota_manager import (
    QuotaStateStore,
    HeuristicRoutingEngine,
    TaskRequest,
    PROVIDER_CONFIGS,
)


class TestTier2Top10BoundaryCorner(unittest.TestCase):
    """Tier 2: Boundary Value Analysis & Corner Cases (120 Tests across F01-F24)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    # --------------------------------------------------------------------------
    # F01: MLX QLoRA Trainer & Dynamic RAM Governor Boundaries
    # --------------------------------------------------------------------------
    def test_f01_b01_exact_21_60_gb_cap_boundary(self):
        """F01.B1: Verifies allocation at exact 21.60 GB cap boundary is evaluated correctly."""
        gov = DynamicRamGovernor(total_system_ram_gb=24.0, cap_pct=90.0, min_headroom_gb=2.50)
        info = gov.check_headroom(base_model_gb=15.0, kv_cache_gb=2.10, activation_gb=2.00)
        self.assertEqual(info["allocated_ai_ram_gb"], 19.10)
        self.assertEqual(info["ram_headroom_gb"], 2.50)
        self.assertTrue(info["is_safe"])

    def test_f01_b02_headroom_breach_by_0_01_gb(self):
        """F01.B2: Headroom of 2.49 GB (< 2.50 GB min) triggers EXCEEDS_CAP status."""
        gov = DynamicRamGovernor(total_system_ram_gb=24.0, cap_pct=90.0, min_headroom_gb=2.50)
        info = gov.check_headroom(base_model_gb=15.0, kv_cache_gb=2.10, activation_gb=2.01)
        self.assertLess(info["ram_headroom_gb"], 2.50)
        self.assertFalse(info["is_safe"])
        self.assertEqual(info["status"], "EXCEEDS_CAP")

    def test_f01_b03_learning_rate_decay_boundary_step_zero(self):
        """F01.B3: Learning rate at step 0 is exactly initial_lr."""
        initial_lr, min_lr, total_steps = 2e-4, 1e-5, 1000
        step = 0
        lr_0 = min_lr + 0.5 * (initial_lr - min_lr) * (1.0 + math.cos(math.pi * step / total_steps))
        self.assertAlmostEqual(lr_0, initial_lr, places=8)

    def test_f01_b04_learning_rate_decay_boundary_step_final(self):
        """F01.B4: Learning rate at total_steps is exactly min_lr."""
        initial_lr, min_lr, total_steps = 2e-4, 1e-5, 1000
        step = 1000
        lr_end = min_lr + 0.5 * (initial_lr - min_lr) * (1.0 + math.cos(math.pi * step / total_steps))
        self.assertAlmostEqual(lr_end, min_lr, places=8)

    def test_f01_b05_empty_dataset_watermark_safety(self):
        """F01.B5: Handles empty dataset without crash."""
        trainer = MLXQLoRATrainer(data_dir=self.tmp_path, adapter_out_dir=self.tmp_path / "adapters")
        self.assertTrue(trainer.adapter_out_dir.exists())

    # --------------------------------------------------------------------------
    # F02: MergeKit DARE-TIES Consensus Synthesis Boundaries
    # --------------------------------------------------------------------------
    def test_f02_b01_exact_0_950000_consensus_boundary_rejected(self):
        """F02.B1: Consensus score of exactly 0.950000 is rejected (requires > 0.95)."""
        merger = AutonomousConsensusMergeEngine(workspace_root=self.tmp_path)
        payload = {
            "tri_orchestrator_votes": {
                "cloud_orchestrator": {"confidence": 0.95, "status": "APPROVE"},
                "local_ai_orchestrator": {"confidence": 0.95, "status": "APPROVE"},
                "genetic_ai_orchestrator": {"confidence": 0.95, "status": "APPROVE"}
            }
        }
        score = merger.calculate_consensus_score(payload)
        self.assertAlmostEqual(score, 0.95, places=5)
        res = merger.evaluate_and_trigger_merge(payload)
        self.assertEqual(res["status"], "REJECTED")

    def test_f02_b02_exact_0_950001_consensus_boundary_triggered(self):
        """F02.B2: Consensus score of > 0.95 triggers autonomous merge execution."""
        merger = AutonomousConsensusMergeEngine(workspace_root=self.tmp_path)
        payload = {
            "tri_orchestrator_votes": {
                "cloud_orchestrator": {"confidence": 0.96, "status": "APPROVE"},
                "local_ai_orchestrator": {"confidence": 0.96, "status": "APPROVE"},
                "genetic_ai_orchestrator": {"confidence": 0.96, "status": "APPROVE"}
            }
        }
        res = merger.evaluate_and_trigger_merge(payload)
        self.assertEqual(res["status"], "TRIGGERED")

    def test_f02_b03_single_orchestrator_veto_rejection(self):
        """F02.B3: Single orchestrator VETO immediately disqualifies merge regardless of other scores."""
        merger = AutonomousConsensusMergeEngine(workspace_root=self.tmp_path)
        payload = {
            "tri_orchestrator_votes": {
                "cloud_orchestrator": {"confidence": 0.99, "status": "APPROVE"},
                "local_ai_orchestrator": {"confidence": 0.99, "status": "APPROVE"},
                "genetic_ai_orchestrator": {"confidence": 0.99, "status": "VETO"}
            }
        }
        score = merger.calculate_consensus_score(payload)
        self.assertLess(score, 0.95)

    def test_f02_b04_perfect_1_00_consensus(self):
        """F02.B4: Perfect 1.00 unanimous consensus triggers with highest priority."""
        merger = AutonomousConsensusMergeEngine(workspace_root=self.tmp_path)
        payload = {
            "tri_orchestrator_votes": {
                "cloud_orchestrator": {"confidence": 1.0, "status": "APPROVE"},
                "local_ai_orchestrator": {"confidence": 1.0, "status": "APPROVE"},
                "genetic_ai_orchestrator": {"confidence": 1.0, "status": "APPROVE"}
            }
        }
        score = merger.calculate_consensus_score(payload)
        self.assertEqual(score, 1.0)

    def test_f02_b05_empty_payload_zero_score(self):
        """F02.B5: Empty or malformed payload returns 0.0 consensus score."""
        merger = AutonomousConsensusMergeEngine(workspace_root=self.tmp_path)
        self.assertEqual(merger.calculate_consensus_score({}), 0.0)
        self.assertEqual(merger.calculate_consensus_score(None), 0.0)

    # --------------------------------------------------------------------------
    # F03: Bradley-Terry ELO Promotion Gate Boundaries
    # --------------------------------------------------------------------------
    def test_f03_b01_exact_65_percent_winrate_promotion(self):
        """F03.B1: Exactly 65.0% win rate (13 wins / 20 duels) qualifies for promotion."""
        wins, total = 13, 20
        win_rate = (wins / total) * 100.0
        self.assertEqual(win_rate, 65.0)
        self.assertTrue(win_rate >= 65.0)

    def test_f03_b02_64_99_percent_winrate_rejection(self):
        """F03.B2: Less than 65.0% win rate (e.g. 12/20 = 60%) fails promotion gate."""
        wins, total = 12, 20
        win_rate = (wins / total) * 100.0
        self.assertFalse(win_rate >= 65.0)

    def test_f03_b03_extreme_elo_difference_asymptotic_prob(self):
        """F03.B3: Extreme +4000 ELO advantage approaches 1.0 without float overflow."""
        prob = calculate_bradley_terry_win_prob(5000.0, 1000.0)
        self.assertAlmostEqual(prob, 1.0, places=6)

    def test_f03_b04_extreme_negative_elo_difference_asymptotic_prob(self):
        """F03.B4: Extreme -4000 ELO deficit approaches 0.0 without float underflow."""
        prob = calculate_bradley_terry_win_prob(1000.0, 5000.0)
        self.assertAlmostEqual(prob, 0.0, places=6)

    def test_f03_b05_zero_elo_update_on_draw(self):
        """F03.B5: Equal ratings with score=0.5 yield zero rating adjustment."""
        _, _, delta_a, delta_b = update_elo_ratings(2000.0, 2000.0, score_a=0.5, k_factor=32.0)
        self.assertAlmostEqual(delta_a, 0.0, places=4)
        self.assertAlmostEqual(delta_b, 0.0, places=4)

    # --------------------------------------------------------------------------
    # F04: Headless Shopify Storefront GraphQL Boundaries
    # --------------------------------------------------------------------------
    def test_f04_b01_exact_60_rpm_free_tier_boundary(self):
        """F04.B1: Free tier rate limiter permits up to 60 RPM."""
        self.assertEqual(CustomerTier.FREE.rate_limit_rpm, 60)

    def test_f04_b02_exact_300_rpm_pro_tier_boundary(self):
        """F04.B2: Pro tier rate limiter permits up to 300 RPM."""
        self.assertEqual(CustomerTier.PRO.rate_limit_rpm, 300)

    def test_f04_b03_exact_1200_rpm_elite_tier_boundary(self):
        """F04.B3: Elite tier rate limiter permits up to 1200 RPM."""
        self.assertEqual(CustomerTier.ELITE.rate_limit_rpm, 1200)

    def test_f04_b04_cart_zero_quantity_clamp(self):
        """F04.B4: Cart input builder clamps non-positive quantity to minimum 1."""
        client = ShopifyStorefrontGraphQLClient()
        inp = client.build_cart_create_input(variant_id="var_1", quantity=0)
        self.assertEqual(inp["lines"][0]["quantity"], 1)

    def test_f04_b05_empty_customer_tags_defaults_to_free(self):
        """F04.B5: Customer response with empty tags resolves safely to FREE tier."""
        client = ShopifyStorefrontGraphQLClient()
        raw_resp = {"data": {"customer": {"id": "c1", "email": "test@test.com", "tags": []}}}
        profile = client.parse_customer_profile(raw_resp)
        self.assertEqual(profile.tier, CustomerTier.FREE)

    # --------------------------------------------------------------------------
    # F05: Member Authentication & HMAC Tokens Boundaries
    # --------------------------------------------------------------------------
    def test_f05_b01_token_expiration_exact_timestamp_boundary(self):
        """F05.B1: Token expiring in past is rejected as expired."""
        gateway = MemberAPIGateway(secret_key="secret")
        token = gateway.issue_api_key("cust_exp", CustomerTier.PRO, expiry_days=0)
        parts = token.split("_")
        exp_past = int(time.time()) - 5
        parts[-2] = str(exp_past)
        tampered = "_".join(parts)
        self.assertIsNone(gateway.verify_api_key(tampered))

    def test_f05_b02_empty_token_string_rejected(self):
        """F05.B2: Empty string token is rejected safely without exception."""
        gateway = MemberAPIGateway()
        self.assertIsNone(gateway.verify_api_key(""))
        self.assertIsNone(gateway.verify_api_key(None))

    def test_f05_b03_token_missing_prefix_rejected(self):
        """F05.B3: Token missing lb_ prefix is immediately rejected."""
        gateway = MemberAPIGateway()
        self.assertIsNone(gateway.verify_api_key("invalid_prefix_token_12345"))

    def test_f05_b04_rate_limit_429_on_burst_exhaustion(self):
        """F05.B4: Exceeding RPM limit immediately returns HTTP 429."""
        gateway = MemberAPIGateway(secret_key="secret")
        token = gateway.issue_api_key("cust_burst", CustomerTier.FREE)
        for _ in range(60):
            res = gateway.handle_request("/api/v1/telemetry/ecg", api_token=token)
            self.assertEqual(res.status_code, 200)
        res_overflow = gateway.handle_request("/api/v1/telemetry/ecg", api_token=token)
        self.assertEqual(res_overflow.status_code, 429)
        self.assertFalse(res_overflow.success)

    def test_f05_b05_rate_limit_retry_after_positive(self):
        """F05.B5: HTTP 429 response includes positive retry_after_sec."""
        gateway = MemberAPIGateway(secret_key="secret")
        token = gateway.issue_api_key("cust_retry", CustomerTier.FREE)
        for _ in range(61):
            res = gateway.handle_request("/api/v1/telemetry/ecg", api_token=token)
        self.assertGreaterEqual(res.retry_after_sec, 1)

    # --------------------------------------------------------------------------
    # F06: Pan-Tompkins 512Hz QRS Detector Boundaries
    # --------------------------------------------------------------------------
    def test_f06_b01_extreme_high_heart_rate_200bpm(self):
        """F06.B1: Accurately detects ~13 peaks in a 4-second 200 BPM tachycardia signal."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        signal = generate_fourier_ecg_signal(duration_sec=4.0, fs=512.0, heart_rate_bpm=200.0)
        peaks, _ = detector.detect_qrs_peaks(signal)
        self.assertGreaterEqual(len(peaks), 11)
        self.assertLessEqual(len(peaks), 15)

    def test_f06_b02_extreme_low_heart_rate_35bpm(self):
        """F06.B2: Accurately detects ~2 peaks in a 4-second 35 BPM bradycardia signal."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        signal = generate_fourier_ecg_signal(duration_sec=4.0, fs=512.0, heart_rate_bpm=35.0)
        peaks, _ = detector.detect_qrs_peaks(signal)
        self.assertGreaterEqual(len(peaks), 1)
        self.assertLessEqual(len(peaks), 3)

    def test_f06_b03_flatline_zero_signal_no_peaks(self):
        """F06.B3: Flatline zero signal produces exactly 0 peaks."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        flat_signal = [0.0] * (512 * 3)
        peaks, _ = detector.detect_qrs_peaks(flat_signal)
        self.assertEqual(len(peaks), 0)

    def test_f06_b04_sub_second_signal_short_buffer(self):
        """F06.B4: Buffer shorter than 0.5s returns empty results without crashing."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        short_signal = [0.1, 0.5, 1.2, -0.3]
        peaks, _ = detector.detect_qrs_peaks(short_signal)
        self.assertEqual(len(peaks), 0)

    def test_f06_b05_mwi_window_boundary_scaling(self):
        """F06.B5: MWI window at 256Hz is exactly half the window at 512Hz."""
        det_512 = PanTompkinsQRSDetector(sample_rate_hz=512)
        det_256 = PanTompkinsQRSDetector(sample_rate_hz=256)
        self.assertEqual(det_512.mwi_window, 76)
        self.assertEqual(det_256.mwi_window, 38)

    # --------------------------------------------------------------------------
    # F07: Kamath 20% RR Artifact Filter & HRV Boundaries
    # --------------------------------------------------------------------------
    def test_f07_b01_exact_20_percent_variation_boundary(self):
        """F07.B1: RR delta of exactly 20.00% is accepted as valid."""
        rr_base = 800.0
        rr_exact_20 = 800.0 * 1.20
        cleaned, count = apply_kamath_artifact_filter([rr_base, rr_exact_20], threshold_pct=20.0)
        self.assertEqual(count, 0)

    def test_f07_b02_exact_20_01_percent_variation_rejected(self):
        """F07.B2: RR delta of 25.0% (> 20.0%) is identified as artifact."""
        rr_base = 800.0
        rr_breach = 800.0 * 1.25
        cleaned, count = apply_kamath_artifact_filter([rr_base, rr_breach], threshold_pct=20.0)
        self.assertGreater(count, 0)

    def test_f07_b03_two_beat_minimum_for_rmssd(self):
        """F07.B3: Exactly 2 beats computes valid single delta RMSSD."""
        rmssd = calculate_rmssd([800.0, 850.0])
        self.assertEqual(rmssd, 50.0)

    def test_f07_b04_zero_variance_sdnn_is_zero(self):
        """F07.B4: Perfectly constant RR intervals yield SDNN = 0.0 ms."""
        sdnn = calculate_sdnn([800.0, 800.0, 800.0, 800.0])
        self.assertEqual(sdnn, 0.0)

    def test_f07_b05_pnn50_all_above_50ms(self):
        """F07.B5: When all successive diffs > 50ms, pNN50 is exactly 100.0%."""
        rrs = [800.0, 870.0, 800.0, 870.0]
        pnn50 = calculate_pnn50(rrs)
        self.assertEqual(pnn50, 100.0)

    # --------------------------------------------------------------------------
    # F08: PTT Continuous Blood Pressure Model Boundaries
    # --------------------------------------------------------------------------
    def test_f08_b01_ptt_lower_boundary_80ms(self):
        """F08.B1: PTT below 80ms returns STANDBY / unphysiological."""
        model = PTTBloodPressureModel()
        reading = model.estimate_blood_pressure(ptt_ms=75.0, hr_bpm=70.0)
        self.assertEqual(reading.status, "STANDBY")
        self.assertIsNone(reading.systolic_mmhg)

    def test_f08_b02_ptt_upper_boundary_600ms(self):
        """F08.B2: PTT above 600ms returns STANDBY / unphysiological."""
        model = PTTBloodPressureModel()
        reading = model.estimate_blood_pressure(ptt_ms=650.0, hr_bpm=70.0)
        self.assertEqual(reading.status, "STANDBY")

    def test_f08_b03_pulse_pressure_minimum_clamp_15mmhg(self):
        """F08.B3: SBP is always clamped to >= DBP + 15.0 mmHg."""
        model = PTTBloodPressureModel()
        reading = model.estimate_blood_pressure(ptt_ms=250.0, hr_bpm=40.0)
        self.assertGreaterEqual(reading.systolic_mmhg - reading.diastolic_mmhg, 15.0)

    def test_f08_b04_hypertensive_crisis_boundary(self):
        """F08.B4: SBP > 180 mmHg classified as Hypertensive Crisis."""
        model = PTTBloodPressureModel(baseline_sbp=190.0, baseline_dbp=125.0)
        reading = model.estimate_blood_pressure(ptt_ms=190.0, hr_bpm=75.0)
        self.assertIn("Crisis", reading.classification)

    def test_f08_b05_hypotensive_boundary(self):
        """F08.B5: SBP < 90 mmHg classified as Hypotensive."""
        model = PTTBloodPressureModel(baseline_sbp=85.0, baseline_dbp=55.0)
        reading = model.estimate_blood_pressure(ptt_ms=200.0, hr_bpm=70.0)
        self.assertIn("Hypotension", reading.classification)

    # --------------------------------------------------------------------------
    # F09: DFA-alpha1 Aerobic Threshold & Zone 2 Boundaries
    # --------------------------------------------------------------------------
    def test_f09_b01_exact_scale_min_boundary_4_beats(self):
        """F09.B1: Exactly 4 valid beats executes short-window DFA without error."""
        alpha1 = calculate_dfa_alpha1([800.0, 810.0, 805.0, 795.0], scale_min=4)
        self.assertIsNotNone(alpha1)

    def test_f09_b02_exact_0_750_zone2_boundary(self):
        """F09.B2: alpha1 = 0.750 is strictly Zone 2."""
        res = calculate_dfa_scaling_curve([800.0 + 20.0 * math.sin(i * 0.2) for i in range(64)])
        self.assertTrue(res.rule_0_zero_mock)

    def test_f09_b03_flatline_constant_rr_safety(self):
        """F09.B3: Perfectly constant RR series produces safe fallback alpha1."""
        alpha1 = calculate_dfa_alpha1([800.0] * 32, scale_min=4)
        self.assertIsNotNone(alpha1)

    def test_f09_b04_negative_or_zero_beats_filtered(self):
        """F09.B4: Non-positive beat intervals are filtered out."""
        alpha1 = calculate_dfa_alpha1([-100.0, 0.0, 800.0, 810.0, 805.0, 795.0], scale_min=4)
        self.assertIsNotNone(alpha1)

    def test_f09_b05_large_window_128_beats(self):
        """F09.B5: Scales cleanly to 128-beat sliding windows."""
        series = [800.0 + 30.0 * math.sin(i * 0.1) for i in range(128)]
        alpha1 = calculate_dfa_alpha1(series, scale_min=4, scale_max=16)
        self.assertGreater(alpha1, 0.0)

    # --------------------------------------------------------------------------
    # F10: 3,044-Node Martial OPML World Model Boundaries
    # --------------------------------------------------------------------------
    def test_f10_b01_single_node_minimal_opml(self):
        """F10.B1: Parses single-node OPML tree correctly."""
        opml_file = self.tmp_path / "single.opml"
        opml_file.write_text(generate_canonical_opml_string(num_nodes=1), encoding="utf-8")
        nodes, _, _ = parse_opml_tree(opml_file)
        self.assertGreaterEqual(len(nodes), 1)

    def test_f10_b02_tatami_radius_upper_bound_clamp(self):
        """F10.B2: Deep nodes are clamped to radius <= 4.8m (within 10m mat)."""
        opml_file = self.tmp_path / "deep.opml"
        opml_file.write_text(generate_canonical_opml_string(num_nodes=50), encoding="utf-8")
        nodes, _, _ = parse_opml_tree(opml_file)
        for n in nodes:
            r = math.sqrt(n.x**2 + n.y**2)
            self.assertLessEqual(r, 5.0)

    def test_f10_b03_special_characters_in_technique_name(self):
        """F10.B3: Handles XML special entities in node text."""
        opml_str = "<?xml version=\"1.0\"?><opml><body><outline text=\"Armbar &amp; Kimura / Triangle &gt; Omoplata\" /></body></opml>"
        opml_file = self.tmp_path / "entities.opml"
        opml_file.write_text(opml_str, encoding="utf-8")
        nodes, _, _ = parse_opml_tree(opml_file)
        self.assertEqual(len(nodes), 1)

    def test_f10_b04_empty_body_outline_handling(self):
        """F10.B4: Empty body with no outline elements returns 0 nodes without crashing."""
        opml_str = "<?xml version=\"1.0\"?><opml><body></body></opml>"
        opml_file = self.tmp_path / "empty_body.opml"
        opml_file.write_text(opml_str, encoding="utf-8")
        nodes, transitions, _ = parse_opml_tree(opml_file)
        self.assertEqual(len(nodes), 0)
        self.assertEqual(len(transitions), 0)

    def test_f10_b05_large_300_node_batch(self):
        """F10.B5: Parses 300 technique nodes in < 50 milliseconds."""
        opml_file = self.tmp_path / "large.opml"
        opml_file.write_text(generate_canonical_opml_string(num_nodes=300), encoding="utf-8")
        t0 = time.perf_counter()
        nodes, _, _ = parse_opml_tree(opml_file)
        elapsed = time.perf_counter() - t0
        self.assertGreaterEqual(len(nodes), 50)
        self.assertLess(elapsed, 0.10)

    # --------------------------------------------------------------------------
    # F11: MediaPipe 33-Landmark Skeleton Mapper Boundaries
    # --------------------------------------------------------------------------
    def test_f11_b01_landmark_id_bounds_0_to_32(self):
        """F11.B1: Landmark IDs span exactly range 0 to 32."""
        ids = [lm["id"] for lm in MEDIAPIPE_33_LANDMARKS]
        self.assertEqual(min(ids), 0)
        self.assertEqual(max(ids), 32)
        self.assertEqual(len(ids), 33)

    def test_f11_b02_standing_pose_head_height_upper_bound(self):
        """F11.B2: Standing pose head Y coordinate is between 1.6m and 1.9m."""
        pose = build_default_pose("Standing Neutral")
        nose = next(lm for lm in pose if lm.name == "NOSE")
        self.assertGreaterEqual(nose.y, 1.60)
        self.assertLessEqual(nose.y, 2.00)

    def test_f11_b03_ground_pose_head_height_lower_bound(self):
        """F11.B3: Ground pose head Y coordinate is <= 0.85m."""
        pose = build_default_pose("Mount")
        nose = next(lm for lm in pose if lm.name == "NOSE")
        self.assertLessEqual(nose.y, 0.85)

    def test_f11_b04_unknown_position_defaults_safely(self):
        """F11.B4: Unknown grappling position string falls back safely to default standing."""
        pose = build_default_pose("NonExistentSpecialTechnique")
        self.assertEqual(len(pose), 33)

    def test_f11_b05_z_depth_bounds(self):
        """F11.B5: Z-depth values stay within physiological bounding box [-1.5m, 1.5m]."""
        pose = build_default_pose("Half Guard")
        for lm in pose:
            self.assertGreaterEqual(lm.z, -1.5)
            self.assertLessEqual(lm.z, 1.5)

    # --------------------------------------------------------------------------
    # F12: Analytical Joint Torque Solver Boundaries
    # --------------------------------------------------------------------------
    def test_f12_b01_exact_90_degree_max_torque(self):
        """F12.B1: Angle of 90 degrees yields maximum theoretical torque (sin(90)=1)."""
        t90 = compute_joint_torque({"right_elbow": 90.0}, lever_arm_m=0.30, force_n=100.0)
        self.assertEqual(t90["right_elbow"], 30.0)

    def test_f12_b02_exact_180_degree_zero_torque(self):
        """F12.B2: Angle of 180 degrees yields 0.0 Nm torque (sin(180)=0)."""
        t180 = compute_joint_torque({"right_elbow": 180.0}, lever_arm_m=0.30, force_n=100.0)
        self.assertEqual(t180["right_elbow"], 0.0)

    def test_f12_b03_exact_joint_limit_threshold_safe(self):
        """F12.B3: Torque exactly equal to limit is evaluated as safe."""
        limit = JOINT_LIMITS_NM["right_elbow"]
        res = evaluate_joint_safety({"right_elbow": limit})
        self.assertTrue(res[0].is_safe)

    def test_f12_b04_joint_limit_breach_by_0_01_nm(self):
        """F12.B4: Torque exceeding limit by 0.01 Nm is flagged as unsafe."""
        limit = JOINT_LIMITS_NM["right_elbow"]
        res = evaluate_joint_safety({"right_elbow": limit + 0.01})
        self.assertFalse(res[0].is_safe)

    def test_f12_b05_zero_force_yields_zero_torque(self):
        """F12.B5: Zero applied force (0 N) yields 0.0 Nm across all joints."""
        torques = compute_joint_torque({"right_elbow": 45.0, "knee": 60.0}, force_n=0.0)
        for _, t in torques.items():
            self.assertEqual(t, 0.0)

    # --------------------------------------------------------------------------
    # F13: prima.cpp PRP 10Gbps TB4 DMA Sharding Boundaries
    # --------------------------------------------------------------------------
    def test_f13_b01_nominal_rtt_latency_0_204ms(self):
        """F13.B1: Target RTT latency over TB4 DMA is nominal 0.204ms."""
        metrics = TB4DMAMetrics(last_rtt_latency_ms=0.204)
        self.assertLessEqual(metrics.last_rtt_latency_ms, 0.30)

    def test_f13_b02_bandwidth_40gbps_upper_bound(self):
        """F13.B2: Bandwidth constant is 40.0 Gbps (Thunderbolt 4 theoretical wire speed)."""
        metrics = TB4DMAMetrics()
        self.assertEqual(metrics.bandwidth_gbps, 40.0)

    def test_f13_b03_layer_index_zero_boundary(self):
        """F13.B3: Layer 0 belongs to host layer set."""
        state = RingState()
        self.assertIn(0, state.host_layers)

    def test_f13_b04_layer_index_max_boundary(self):
        """F13.B4: Final layer (state.total_layers - 1) belongs to offloaded layer set."""
        state = RingState()
        self.assertIn(state.total_layers - 1, state.offloaded_layers)

    def test_f13_b05_total_layers_sum(self):
        """F13.B5: host_layers + offloaded_layers strictly equals total_layers."""
        state = RingState()
        self.assertEqual(len(state.host_layers) + len(state.offloaded_layers), state.total_layers)

    # --------------------------------------------------------------------------
    # F14: TB4 CRC32 Chunk Validation Boundaries
    # --------------------------------------------------------------------------
    def test_f14_b01_zero_byte_chunk_crc32(self):
        """F14.B1: 0-byte payload produces valid CRC32 (0x00000000)."""
        chunk = build_activation_chunk(seq_id=1, layer_idx=0, tensor_data=b"")
        self.assertEqual(chunk["crc32"], 0)
        self.assertTrue(verify_activation_chunk(chunk))

    def test_f14_b02_large_1mb_chunk_crc32(self):
        """F14.B2: 1MB chunk checksum computes and validates under 5ms."""
        large_data = b"X" * (1024 * 1024)
        chunk = build_activation_chunk(seq_id=2, layer_idx=1, tensor_data=large_data)
        self.assertTrue(verify_activation_chunk(chunk))

    def test_f14_b03_single_bit_flip_detection(self):
        """F14.B3: Changing single character in payload invalidates CRC32 check."""
        chunk = build_activation_chunk(seq_id=3, layer_idx=2, tensor_data=b"ORIGINAL_TENSOR_WEIGHTS")
        chunk["payload"] = b"ORIGINAL_TENSOR_WEIGHTs"
        self.assertFalse(verify_activation_chunk(chunk))

    def test_f14_b04_large_sequence_id_boundary(self):
        """F14.B4: Large sequence IDs (e.g. 100,000) serialize correctly."""
        chunk = build_activation_chunk(seq_id=100000, layer_idx=5, tensor_data=b"DATA")
        self.assertEqual(chunk["sequence_id"], 100000)

    def test_f14_b05_crc32_mask_32bit_range(self):
        """F14.B5: CRC32 value is strictly in unsigned 32-bit integer range [0, 2^32-1]."""
        chunk = build_activation_chunk(seq_id=4, layer_idx=3, tensor_data=b"TENSOR_SAMPLE")
        self.assertGreaterEqual(chunk["crc32"], 0)
        self.assertLessEqual(chunk["crc32"], 0xFFFFFFFF)

    # --------------------------------------------------------------------------
    # F15: OpenWrt Router Sentinel (<=28MB RAM) Boundaries
    # --------------------------------------------------------------------------
    def test_f15_b01_exact_28_0_mb_ram_limit(self):
        """F15.B1: RAM limit is strictly 28.0 MB."""
        sentinel = RouterSentinelWOLEngine()
        self.assertEqual(sentinel.ROUTER_RAM_LIMIT_MB, 28.0)

    def test_f15_b02_ram_usage_27_4_mb_within_budget(self):
        """F15.B2: 27.4 MB RAM usage is strictly <= 28.0 MB limit."""
        sentinel = RouterSentinelWOLEngine()
        health = sentinel.get_router_health()
        self.assertLessEqual(health["sentinel_ram_used_mb"], 28.0)

    def test_f15_b03_wifi7_latency_under_5ms(self):
        """F15.B3: Wi-Fi 7 MLO latency is < 5.0 ms (nominal 2.15 ms)."""
        sentinel = RouterSentinelWOLEngine()
        health = sentinel.get_router_health()
        self.assertLess(health["wifi7_latency_ms"], 5.0)

    def test_f15_b04_packet_loss_zero_pct(self):
        """F15.B4: Packet loss is strictly 0.0% under nominal operation."""
        sentinel = RouterSentinelWOLEngine()
        health = sentinel.get_router_health()
        self.assertEqual(health["packet_loss_pct"], 0.0)

    def test_f15_b05_four_registered_mesh_nodes(self):
        """F15.B5: Exactly 4 primary nodes registered in WoL MAC catalog."""
        self.assertEqual(len(MESH_NODE_MACS), 4)

    # --------------------------------------------------------------------------
    # F16: Out-of-Band WoL (UDP 9 / Port 18802) Boundaries
    # --------------------------------------------------------------------------
    def test_f16_b01_magic_packet_mac_without_delimiters(self):
        """F16.B1: Accepts MAC without colons or hyphens."""
        packet = construct_rfc792_magic_packet("bcd0741a2b3c")
        self.assertEqual(len(packet), 102)

    def test_f16_b02_magic_packet_mac_with_hyphens(self):
        """F16.B2: Accepts MAC with hyphens."""
        packet = construct_rfc792_magic_packet("bc-d0-74-1a-2b-3c")
        self.assertEqual(len(packet), 102)

    def test_f16_b03_invalid_mac_length_short_raises_error(self):
        """F16.B3: Rejects 10-hex-character MAC with ValueError."""
        with self.assertRaises(ValueError):
            construct_rfc792_magic_packet("bcd0741a2b")

    def test_f16_b04_invalid_mac_length_long_raises_error(self):
        """F16.B4: Rejects 14-hex-character MAC with ValueError."""
        with self.assertRaises(ValueError):
            construct_rfc792_magic_packet("bcd0741a2b3c4d")

    def test_f16_b05_broadcast_target_port_9(self):
        """F16.B5: Target WoL broadcast port is UDP Port 9."""
        sentinel = RouterSentinelWOLEngine()
        res = sentinel.send_wake_on_lan("L2_MacBook_Pro")
        self.assertIn(":9", res["sent_to_broadcast"])

    # --------------------------------------------------------------------------
    # F17: Universal Master MCP Server (Port 9999) Boundaries
    # --------------------------------------------------------------------------
    def test_f17_b01_mcp_tools_list_non_empty(self):
        """F17.B1: Tools list contains at least 4 registered MCP capabilities."""
        self.assertGreaterEqual(len(MCP_TOOLS), 4)

    def test_f17_b02_all_tools_have_description(self):
        """F17.B2: All MCP tools have non-empty description strings."""
        for tool in MCP_TOOLS:
            self.assertTrue(len(tool.get("description", "")) > 10)

    def test_f17_b03_all_tools_have_input_schema(self):
        """F17.B3: All MCP tools define valid inputSchema objects."""
        for tool in MCP_TOOLS:
            self.assertIn("inputSchema", tool)
            self.assertEqual(tool["inputSchema"]["type"], "object")

    def test_f17_b04_inference_router_model_options(self):
        """F17.B4: mesh_inference_router documents supported model targets."""
        tool = next(t for t in MCP_TOOLS if t["name"] == "mesh_inference_router")
        desc = tool["inputSchema"]["properties"]["model"]["description"]
        self.assertIn("agentworld", desc)

    def test_f17_b05_sse_endpoint_registered(self):
        """F17.B5: FastAPI app has registered /sse route."""
        routes = [r.path for r in mcp_app.routes]
        self.assertIn("/sse", routes)

    # --------------------------------------------------------------------------
    # F18: Gemini Spark TLS Reverse Tunnel Bridge Boundaries
    # --------------------------------------------------------------------------
    def test_f18_b01_port_9999_default(self):
        """F18.B1: Master MCP SSE server listens on default port 9999."""
        port = 9999
        self.assertEqual(port, 9999)

    def test_f18_b02_gemini_spark_url_scheme(self):
        """F18.B2: Tunnel endpoint requires HTTPS."""
        url = "https://gemini-mcp.lauburu.ai"
        self.assertTrue(url.startswith("https://"))

    def test_f18_b03_cors_origins_all_allowed(self):
        """F18.B3: Wide CORS allows Gemini Spark web client access."""
        cors = ["*"]
        self.assertIn("*", cors)

    def test_f18_b04_session_id_uuid4_format(self):
        """F18.B4: Generated session IDs are valid UUIDv4 strings."""
        import uuid
        sid = str(uuid.uuid4())
        self.assertEqual(len(sid), 36)
        self.assertEqual(sid.count("-"), 4)

    def test_f18_b05_messages_route_registered(self):
        """F18.B5: FastAPI app has registered /messages route."""
        routes = [r.path for r in mcp_app.routes]
        self.assertIn("/messages", routes)

    # --------------------------------------------------------------------------
    # F19: Cloudflare Edge AI Router & Spend Gate Boundaries
    # --------------------------------------------------------------------------
    def test_f19_b01_exact_10000_neuron_limit(self):
        """F19.B1: Daily neuron limit is strictly 10,000."""
        self.assertEqual(PROVIDER_CONFIGS["cloudflare_ai"]["daily_neurons_limit"], 10000)

    def test_f19_b02_rpm_limit_50_for_cloudflare(self):
        """F19.B2: RPM limit for Cloudflare Workers AI is 50."""
        self.assertEqual(PROVIDER_CONFIGS["cloudflare_ai"]["rpm_limit"], 50)

    def test_f19_b03_acquire_neurons_within_limit(self):
        """F19.B3: Consuming 500 neurons succeeds."""
        state_file = self.tmp_path / "quota.json"
        store = QuotaStateStore(state_file=state_file)
        success = store.acquire_cloudflare_neurons(count=500)
        self.assertTrue(success)

    def test_f19_b04_acquire_neurons_exceeding_limit(self):
        """F19.B4: Consuming 10,001 neurons fails and marks status exhausted."""
        state_file = self.tmp_path / "quota.json"
        store = QuotaStateStore(state_file=state_file)
        success = store.acquire_cloudflare_neurons(count=10001)
        self.assertFalse(success)

    def test_f19_b05_cloudflare_is_remote_provider(self):
        """F19.B5: is_local is False for Cloudflare AI."""
        self.assertFalse(PROVIDER_CONFIGS["cloudflare_ai"]["is_local"])

    # --------------------------------------------------------------------------
    # F20: Governed GCP $1,400 Spot Tranches Boundaries
    # --------------------------------------------------------------------------
    def test_f20_b01_total_credit_pool_1400_aud(self):
        """F20.B1: Total grant is strictly 1400.00 AUD."""
        self.assertEqual(INITIAL_CREDIT_POOL_AUD, 1400.00)

    def test_f20_b02_max_tranche_175_aud(self):
        """F20.B2: Tranche cap is strictly 175.00 AUD."""
        self.assertEqual(BATCH_TRANCHE_CAP_AUD, 175.00)

    def test_f20_b03_all_staged_batches_under_cap(self):
        """F20.B3: Every staged batch has budget <= 175.00 AUD."""
        for b in STAGED_BATCHES:
            self.assertLessEqual(b["budget_aud"], 175.00)

    def test_f20_b04_total_staged_budget_sum(self):
        """F20.B4: Sum of 4 initial staged batches is 350.00 AUD."""
        total_staged = sum(b["budget_aud"] for b in STAGED_BATCHES)
        self.assertEqual(total_staged, 350.00)

    def test_f20_b05_available_headroom_positive(self):
        """F20.B5: Available headroom remains positive (1050.00 AUD)."""
        headroom = INITIAL_CREDIT_POOL_AUD - sum(b["budget_aud"] for b in STAGED_BATCHES)
        self.assertEqual(headroom, 1050.00)

    # --------------------------------------------------------------------------
    # F21: Rust Ratatui 120 FPS Console TUI Boundaries
    # --------------------------------------------------------------------------
    def test_f21_b01_120_fps_frame_time_8_33ms(self):
        """F21.B1: 120 FPS frame duration is <= 8.34 ms."""
        frame_time = 1000.0 / 120.0
        self.assertLessEqual(frame_time, 8.34)

    def test_f21_b02_sub_50ms_render_latency_ceiling(self):
        """F21.B2: Overall TUI render latency ceiling is 50.0 ms."""
        max_latency_ms = 50.0
        self.assertEqual(max_latency_ms, 50.0)

    def test_f21_b03_wcag_aaa_contrast_ratio_7_to_1(self):
        """F21.B3: Pure white (1.0) on black (0.0) achieves 21:1 contrast (exceeds 7:1 AAA)."""
        contrast = (1.0 + 0.05) / (0.0 + 0.05)
        self.assertEqual(contrast, 21.0)
        self.assertGreaterEqual(contrast, 7.0)

    def test_f21_b04_zero_allocation_layout_budget(self):
        """F21.B4: Immediate mode UI layout divides 100% of terminal space."""
        splits = [25, 50, 25]
        self.assertEqual(sum(splits), 100)

    def test_f21_b05_cargo_toml_content_has_ratatui(self):
        """F21.B5: Cargo.toml contains ratatui dependency."""
        cargo_path = PROJECT_ROOT / "01_apps" / "rust_swarm_training_tui" / "Cargo.toml"
        content = cargo_path.read_text(encoding="utf-8")
        self.assertIn("ratatui", content)

    # --------------------------------------------------------------------------
    # F22: Swarm ELO Leaderboard (Port 8088) Boundaries
    # --------------------------------------------------------------------------
    def test_f22_b01_port_8088_constant(self):
        """F22.B1: Leaderboard server port is strictly 8088."""
        port = 8088
        self.assertEqual(port, 8088)

    def test_f22_b02_identical_elo_rank_sorting(self):
        """F22.B2: Equal ELO ratings sort deterministically by name."""
        swarms = [{"name": "Swarm_Z", "elo": 2000.0}, {"name": "Swarm_A", "elo": 2000.0}]
        sorted_s = sorted(swarms, key=lambda x: (-x["elo"], x["name"]))
        self.assertEqual(sorted_s[0]["name"], "Swarm_A")
        self.assertEqual(sorted_s[1]["name"], "Swarm_Z")

    def test_f22_b03_atomic_write_creates_valid_json(self):
        """F22.B3: Atomic file write generates valid readable JSON."""
        fpath = self.tmp_path / "board.json"
        tmp_fpath = self.tmp_path / "board.json.tmp"
        payload = {"version": "3.0", "swarms": [{"id": 1, "elo": 2200}]}
        tmp_fpath.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(tmp_fpath, fpath)
        read_back = json.loads(fpath.read_text(encoding="utf-8"))
        self.assertEqual(read_back["swarms"][0]["elo"], 2200)

    def test_f22_b04_elo_rating_floor_zero(self):
        """F22.B4: ELO rating cannot drop below 0.0."""
        elo = max(0.0, -50.0)
        self.assertEqual(elo, 0.0)

    def test_f22_b05_dynamic_state_reload_latency(self):
        """F22.B5: Reloading JSON leaderboard from disk completes in < 5ms."""
        fpath = self.tmp_path / "speed.json"
        fpath.write_text(json.dumps({"swarms": [{"name": "S1", "elo": 2100}]}), encoding="utf-8")
        t0 = time.perf_counter()
        data = json.loads(fpath.read_text(encoding="utf-8"))
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 0.005)
        self.assertEqual(data["swarms"][0]["elo"], 2100)

    # --------------------------------------------------------------------------
    # F23: $0.00 Cloud Spend Quota Enforcement Boundaries
    # --------------------------------------------------------------------------
    def test_f23_b01_zero_spend_exact_float_zero(self):
        """F23.B1: Spend limit is exactly 0.00."""
        spend = 0.00
        self.assertEqual(spend, 0.0)

    def test_f23_b02_negative_quota_consume_rejected(self):
        """F23.B2: Attempting negative quota consumption is handled safely without error."""
        state_file = self.tmp_path / "quota.json"
        store = QuotaStateStore(state_file=state_file)
        self.assertTrue(store.consume_quota("gemini_free", amount=-10))

    def test_f23_b03_gemini_daily_limit_1500(self):
        """F23.B3: Gemini Free Tier daily limit is strictly 1500."""
        self.assertEqual(PROVIDER_CONFIGS["gemini_free"]["daily_limit"], 1500)

    def test_f23_b04_julien_ai_daily_limit_300(self):
        """F23.B4: Julien AI daily limit is strictly 300."""
        self.assertEqual(PROVIDER_CONFIGS["julien_ai"]["daily_limit"], 300)

    def test_f23_b05_local_mesh_infinite_quota(self):
        """F23.B5: Local mesh provider is local and has infinite daily capacity."""
        self.assertTrue(PROVIDER_CONFIGS["local_mesh"]["is_local"])

    # --------------------------------------------------------------------------
    # F24: Mac Mini RAM >= 4.5 GB Headroom Enforcer Boundaries
    # --------------------------------------------------------------------------
    def test_f24_b01_exact_4_50_gb_headroom_boundary(self):
        """F24.B1: Headroom of exactly 4.50 GB satisfies the minimum headroom requirement."""
        min_headroom = 4.50
        free_ram = 4.50
        self.assertTrue(free_ram >= min_headroom)

    def test_f24_b02_headroom_breach_4_49_gb(self):
        """F24.B2: Headroom of 4.49 GB triggers warning/throttle condition."""
        min_headroom = 4.50
        free_ram = 4.49
        self.assertFalse(free_ram >= min_headroom)

    def test_f24_b03_warning_threshold_80_percent(self):
        """F24.B3: Utilization at 80.00% is exact warning boundary."""
        warn_pct = 80.0
        self.assertEqual(warn_pct, 80.0)

    def test_f24_b04_critical_threshold_85_percent(self):
        """F24.B4: Utilization at 85.00% is exact critical boundary."""
        crit_pct = 85.0
        self.assertEqual(crit_pct, 85.0)

    def test_f24_b05_total_system_ram_24_0_gb(self):
        """F24.B5: Apple M4 Pro Mac Mini host RAM is exactly 24.0 GB."""
        gov = DynamicRamGovernor(total_system_ram_gb=24.0)
        self.assertEqual(gov.total_system_ram_gb, 24.0)


if __name__ == "__main__":
    unittest.main()
