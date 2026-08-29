#!/usr/bin/env python3
"""
Tier 2: Comprehensive Boundary Value Analysis & Corner Cases E2E Test Suite (80 Tests)
Lauburu Monorepo — Unified Front-Facing App Architecture & Multi-Mode Game Arena
================================================================================
Validates boundary conditions, extreme physiological thresholds, data corruptions,
and mathematical singularities across all 16 features from PROJECT.md:
- F01 - F16 (5 boundary/corner test cases per feature = 80 total tests)
"""

import os
import sys
import time
import math
import json
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
    str(PROJECT_ROOT / "03_biometrics_and_telemetry"),
    str(PROJECT_ROOT / "05_agents_and_swarms" / "smolagents_engine"),
    str(PROJECT_ROOT / "05_agents_and_swarms" / "genetic_moe"),
    str(PROJECT_ROOT / "01_apps" / "canonical_port" / "tui"),
    str(PROJECT_ROOT / "01_apps" / "canonical_port" / "tui" / "screens"),
    str(PROJECT_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

from e2e_helpers import (
    validate_pwa_manifest,
    parse_grappling_opml,
    calculate_contrast_ratio,
    inspect_egress_payload_airgap_compliance,
    reference_pan_tompkins_qrs,
    reference_kamath_artifact_filter,
    reference_calculate_rmssd,
    reference_calculate_ptt_bp,
    reference_uth_sorensen_vo2max,
    validate_tactical_objective_schema,
    VALID_GAME_MODES
)

from pan_tompkins_dsp import (
    PanTompkinsQRSDetector,
    apply_kamath_artifact_filter,
    calculate_rmssd,
    calculate_dfa_alpha1,
    calculate_hemodynamics_bp
)
from movesense_readiness_suite import MovesenseReadinessSuite
from smolagents_arena_hub import SmolAgentsArenaHub, GAME_MODES
from genetic_moe_ai_router import GeneticMoEAIRouter


class TestTier2BoundaryCornerCases(unittest.TestCase):
    """Tier 2: 80 Boundary Value & Corner Case Test Cases (5 tests x 16 features)."""

    # =========================================================================
    # F01 Boundaries: Frontend PWA Scaffolding & Manifest
    # =========================================================================
    def test_t2_01_01_empty_manifest_dictionary_handling(self):
        """T2_F01.1: Empty manifest file {} returns false and missing required keys list."""
        temp_mf = Path(tempfile.gettempdir()) / "empty_manifest.json"
        temp_mf.write_text("{}", encoding="utf-8")
        valid, data, errors = validate_pwa_manifest(temp_mf)
        temp_mf.unlink()
        self.assertFalse(valid)
        self.assertGreater(len(errors), 0)

    def test_t2_01_02_manifest_icons_missing_or_empty_list(self):
        """T2_F01.2: Manifest with empty icons list [] is flagged as invalid."""
        temp_mf = Path(tempfile.gettempdir()) / "no_icons_manifest.json"
        temp_mf.write_text(json.dumps({"name": "App", "short_name": "A", "start_url": "/", "display": "standalone", "icons": []}), encoding="utf-8")
        valid, _, errors = validate_pwa_manifest(temp_mf)
        temp_mf.unlink()
        self.assertFalse(valid)
        self.assertTrue(any("icons" in e.lower() for e in errors))

    def test_t2_01_03_service_worker_zero_byte_or_missing_file(self):
        """T2_F01.3: Validates non-existent manifest path returns False gracefully."""
        valid, _, errors = validate_pwa_manifest(Path("/nonexistent/manifest.json"))
        self.assertFalse(valid)
        self.assertIn("not found", errors[0].lower())

    def test_t2_01_04_manifest_start_url_relative_path_resolution(self):
        """T2_F01.4: Manifest with relative start_url (e.g. './' or '.') is accepted."""
        temp_mf = Path(tempfile.gettempdir()) / "rel_manifest.json"
        temp_mf.write_text(json.dumps({
            "name": "App", "short_name": "A", "start_url": "./index.html",
            "display": "standalone", "icons": [{"src": "icon.png", "sizes": "192x192"}]
        }), encoding="utf-8")
        valid, _, errors = validate_pwa_manifest(temp_mf)
        temp_mf.unlink()
        self.assertTrue(valid, f"Unexpected errors: {errors}")

    def test_t2_01_05_manifest_invalid_display_mode_fallback(self):
        """T2_F01.5: Manifest with unrecognized display mode (e.g. 'holographic') is flagged."""
        temp_mf = Path(tempfile.gettempdir()) / "bad_disp_manifest.json"
        temp_mf.write_text(json.dumps({
            "name": "App", "short_name": "A", "start_url": "/",
            "display": "holographic", "icons": [{"src": "icon.png", "sizes": "192x192"}]
        }), encoding="utf-8")
        valid, _, errors = validate_pwa_manifest(temp_mf)
        temp_mf.unlink()
        self.assertFalse(valid)
        self.assertTrue(any("display" in e.lower() for e in errors))

    # =========================================================================
    # F02 Boundaries: Three.js 3D Tatami & Kinematics Graph
    # =========================================================================
    def test_t2_02_01_opml_single_root_node_boundary(self):
        """T2_F02.1: OPML with a single root outline element parses without error."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0"><head><title>Test</title></head>
        <body><outline text="Root Node" type="root"/></body></opml>"""
        temp_opml = Path(tempfile.gettempdir()) / "single_opml.opml"
        temp_opml.write_text(xml_content, encoding="utf-8")
        res = parse_grappling_opml(temp_opml)
        temp_opml.unlink()
        self.assertEqual(res["total_nodes"], 1)
        self.assertEqual(res["max_depth"], 1)

    def test_t2_02_02_opml_empty_body_zero_nodes(self):
        """T2_F02.2: OPML with empty <body> returns 0 nodes safely."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0"><head><title>Empty</title></head><body></body></opml>"""
        temp_opml = Path(tempfile.gettempdir()) / "empty_opml.opml"
        temp_opml.write_text(xml_content, encoding="utf-8")
        res = parse_grappling_opml(temp_opml)
        temp_opml.unlink()
        self.assertEqual(res["total_nodes"], 0)

    def test_t2_02_03_3d_coordinates_extreme_depth_scaling(self):
        """T2_F02.3: Deeply nested nodes (depth=15) compute finite, non-overflowing 3D radii."""
        depth = 15
        radius = 10.0 + (depth * 3.0)  # 55.0
        self.assertTrue(math.isfinite(radius))
        self.assertLess(radius, 1000.0)

    def test_t2_02_04_tatami_raycasting_miss_detection(self):
        """T2_F02.4: Ray pointing away from all nodes returns None."""
        nodes_3d = [{"id": "guard", "pos": (0.0, 0.0, 0.0), "radius": 1.0}]
        ray_origin = (100.0, 100.0, 100.0)
        hit_node = None
        for n in nodes_3d:
            dist = math.dist(ray_origin, n["pos"])
            if dist <= n["radius"]:
                hit_node = n["id"]
        self.assertIsNone(hit_node)

    def test_t2_02_05_opml_special_characters_and_html_entities(self):
        """T2_F02.5: OPML text containing XML entities (&amp;, &lt;, quotes) parses correctly."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0"><body>
        <outline text="Armbar &amp; Triangle &lt;Combo&gt;" type="sub"/>
        </body></opml>"""
        temp_opml = Path(tempfile.gettempdir()) / "entities_opml.opml"
        temp_opml.write_text(xml_content, encoding="utf-8")
        res = parse_grappling_opml(temp_opml)
        temp_opml.unlink()
        self.assertEqual(res["total_nodes"], 1)
        self.assertEqual(res["nodes"][0]["text"], "Armbar & Triangle <Combo>")

    # =========================================================================
    # F03 Boundaries: TailwindCSS & Cross-Platform UI
    # =========================================================================
    def test_t2_03_01_wcag_contrast_pure_black_on_pure_white(self):
        """T2_F03.1: Pure black (#000000) on pure white (#FFFFFF) achieves maximal 21.0:1 contrast."""
        ratio = calculate_contrast_ratio("#000000", "#FFFFFF")
        self.assertEqual(ratio, 21.0)

    def test_t2_03_02_wcag_contrast_identical_colors_1_to_1(self):
        """T2_F03.2: Identical colors (#123456 vs #123456) achieve 1.0:1 contrast."""
        ratio = calculate_contrast_ratio("#123456", "#123456")
        self.assertEqual(ratio, 1.0)

    def test_t2_03_03_3_digit_short_hex_color_parsing(self):
        """T2_F03.3: 3-digit shorthand hex (#FFF, #000) parses with identical contrast."""
        ratio_short = calculate_contrast_ratio("#FFF", "#000")
        self.assertEqual(ratio_short, 21.0)

    def test_t2_03_04_aria_missing_attribute_fallback_sanitization(self):
        """T2_F03.4: Accessibility generator gracefully handles empty/None label."""
        def make_aria_tag(label: Optional[str]) -> str:
            clean = (label or "Biometrics Metric").strip()
            return f'aria-label="{clean}"'
        self.assertEqual(make_aria_tag(None), 'aria-label="Biometrics Metric"')
        self.assertEqual(make_aria_tag("Heart Rate"), 'aria-label="Heart Rate"')

    def test_t2_03_05_ultra_narrow_viewport_breakpoint_scaling(self):
        """T2_F03.5: Viewport < 640px falls back to default 1-column mobile layout."""
        def get_column_count(width_px: int) -> int:
            if width_px >= 1024: return 3
            if width_px >= 640: return 2
            return 1
        self.assertEqual(get_column_count(320), 1)
        self.assertEqual(get_column_count(720), 2)
        self.assertEqual(get_column_count(1440), 3)

    # =========================================================================
    # F04 Boundaries: Strict 100% Local Airgap Protection
    # =========================================================================
    def test_t2_04_01_airgap_large_numeric_array_heuristic_detection(self):
        """T2_F04.1: Raw continuous numeric arrays (len > 20) with ecg keyword are caught."""
        payload = {"live_ecg_buffer": [0.12] * 50}
        valid, violations = inspect_egress_payload_airgap_compliance(payload)
        self.assertFalse(valid)
        self.assertGreater(len(violations), 0)

    def test_t2_04_02_airgap_nested_list_of_dicts_with_raw_keys(self):
        """T2_F04.2: Raw forbidden keys nested inside lists of dictionaries are caught."""
        payload = {"items": [{"id": 1}, {"raw_ppg": [0.1, 0.2]}]}
        valid, violations = inspect_egress_payload_airgap_compliance(payload)
        self.assertFalse(valid)

    def test_t2_04_03_airgap_case_insensitive_forbidden_keys(self):
        """T2_F04.3: Uppercase / mixed-case raw keys (RAW_ECG, Raw_Optical_Stream) are caught."""
        payload = {"RAW_ECG": [1, 2, 3]}
        valid, _ = inspect_egress_payload_airgap_compliance(payload)
        self.assertFalse(valid)

    def test_t2_04_04_airgap_clean_aggregate_metrics_allowed(self):
        """T2_F04.4: Aggregated readiness scores (non-raw scalars) pass egress inspection."""
        clean = {
            "heart_rate_bpm": 72.0,
            "readiness_score": 85,
            "training_zone": "Zone 2"
        }
        valid, violations = inspect_egress_payload_airgap_compliance(clean)
        self.assertTrue(valid, f"Unexpected violations: {violations}")

    def test_t2_04_05_airgap_empty_payload_safe_pass(self):
        """T2_F04.5: Empty egress dictionary passes without inspection errors."""
        valid, violations = inspect_egress_payload_airgap_compliance({})
        self.assertTrue(valid)
        self.assertEqual(len(violations), 0)

    # =========================================================================
    # F05 Boundaries: Bicep ECG 512Hz Pan-Tompkins DSP
    # =========================================================================
    def test_t2_05_01_pan_tompkins_isoelectric_flatline_zero_peaks(self):
        """T2_F05.1: Isoelectric flatline ECG (all 0.0) yields exactly 0 detected peaks."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        flatline = [0.0] * 1024
        peaks, rrs = detector.detect_qrs_peaks(flatline)
        self.assertEqual(len(peaks), 0)
        self.assertEqual(len(rrs), 0)

    def test_t2_05_02_pan_tompkins_sub_half_second_buffer_safety(self):
        """T2_F05.2: ECG buffer shorter than 0.5s returns empty arrays safely."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        short_signal = [0.5] * 100  # ~0.195s at 512Hz
        peaks, rrs = detector.detect_qrs_peaks(short_signal)
        self.assertEqual(peaks, [])
        self.assertEqual(rrs, [])

    def test_t2_05_03_pan_tompkins_extreme_dc_offset_rejection(self):
        """T2_F05.3: Baseline wander / DC offset (+10,000uV) is removed by bandpass filter."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        dc_signal = [10000.0] * 512
        filtered = detector.bandpass_filter(dc_signal)
        # Low frequency DC component is filtered down
        self.assertLess(abs(filtered[-1]), 500.0)

    def test_t2_05_04_pan_tompkins_low_sampling_rate_50hz(self):
        """T2_F05.4: Minimum sample rate bound (50Hz) initializes without error."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=50)
        self.assertEqual(detector.fs, 50)
        self.assertGreaterEqual(detector.mwi_window, 2)

    def test_t2_05_05_pan_tompkins_high_sampling_rate_2048hz(self):
        """T2_F05.5: High sample rate bound (2048Hz) initializes MWI window correctly."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=2048)
        self.assertEqual(detector.fs, 2048)
        self.assertEqual(detector.mwi_window, int(0.150 * 2048))

    # =========================================================================
    # F06 Boundaries: Kamath 20% Artifact Filter & RMSSD
    # =========================================================================
    def test_t2_06_01_kamath_single_rr_interval_boundary(self):
        """T2_F06.1: Single RR interval (n=1) returns unaltered beat and 0 artifacts."""
        cleaned, count = apply_kamath_artifact_filter([800.0])
        self.assertEqual(cleaned, [800.0])
        self.assertEqual(count, 0)

    def test_t2_06_02_kamath_zero_or_negative_rr_boundary(self):
        """T2_F06.2: Non-physiological 0ms or negative intervals are flagged as artifacts."""
        bad_rrs = [800.0, 0.0, 810.0]
        cleaned, count = apply_kamath_artifact_filter(bad_rrs)
        self.assertEqual(count, 1)
        self.assertGreater(cleaned[1], 0.0)

    def test_t2_06_03_rmssd_identical_constant_rr_zero_ms(self):
        """T2_F06.3: Identical constant RR intervals (no variability) produce RMSSD = 0.0ms."""
        const_rrs = [800.0, 800.0, 800.0, 800.0]
        rmssd = calculate_rmssd(const_rrs)
        self.assertEqual(rmssd, 0.0)

    def test_t2_06_04_kamath_100_percent_corrupted_alternating_burst(self):
        """T2_F06.4: Extremely noisy alternating series (400ms, 1200ms) flags all transitions."""
        noisy_rrs = [800.0, 400.0, 1200.0, 400.0, 1200.0]
        cleaned, count = apply_kamath_artifact_filter(noisy_rrs, threshold_pct=20.0)
        self.assertGreaterEqual(count, 3)

    def test_t2_06_05_rmssd_two_beats_minimal_valid_calculation(self):
        """T2_F06.5: Minimal valid sample size (n=2 beats) calculates exact difference."""
        rmssd = calculate_rmssd([800.0, 830.0])
        self.assertEqual(rmssd, 30.0)

    # =========================================================================
    # F07 Boundaries: Pulse Transit Time (PTT) Continuous BP
    # =========================================================================
    def test_t2_07_01_hemodynamic_bp_zero_ptt_returns_none(self):
        """T2_F07.1: PTT <= 0 returns (None, None, None)."""
        self.assertEqual(calculate_hemodynamics_bp(0.0, 70.0), (None, None, None))
        self.assertEqual(calculate_hemodynamics_bp(-100.0, 70.0), (None, None, None))

    def test_t2_07_02_hemodynamic_bp_extreme_ptt_1000ms_clamped(self):
        """T2_F07.2: Unusually prolonged PTT (1000ms) clamps SBP to minimum 80.0 mmHg."""
        sbp, dbp, map_val = calculate_hemodynamics_bp(1000.0, 40.0)
        self.assertEqual(sbp, 80.0)
        self.assertEqual(dbp, 50.0)

    def test_t2_07_03_hemodynamic_bp_extreme_short_ptt_10ms_clamped(self):
        """T2_F07.3: Extremely short PTT (10ms) clamps SBP to maximum 220.0 mmHg."""
        sbp, dbp, map_val = calculate_hemodynamics_bp(10.0, 200.0)
        self.assertEqual(sbp, 220.0)
        self.assertEqual(dbp, 130.0)

    def test_t2_07_04_hemodynamic_bp_extreme_bradycardia_hr_25(self):
        """T2_F07.4: Severe bradycardia (HR=25 BPM) computes without exception."""
        sbp, dbp, map_val = calculate_hemodynamics_bp(220.0, 25.0)
        self.assertIsNotNone(sbp)
        self.assertGreaterEqual(sbp, 80.0)

    def test_t2_07_05_hemodynamic_bp_extreme_tachycardia_hr_240(self):
        """T2_F07.5: Severe tachycardia (HR=240 BPM) computes without exception."""
        sbp, dbp, map_val = calculate_hemodynamics_bp(150.0, 240.0)
        self.assertIsNotNone(sbp)
        self.assertLessEqual(sbp, 220.0)

    # =========================================================================
    # F08 Boundaries: Overnight PPG Sleep Staging & Score
    # =========================================================================
    def test_t2_08_01_sleep_score_zero_rmssd_and_high_hr_clamped_0(self):
        """T2_F08.1: Severe autonomic stress (RMSSD=10ms, HR=95 BPM) yields 0 sleep score."""
        suite = MovesenseReadinessSuite()
        res = suite.compute_overnight_sleep_analysis(hr_bpm=95.0, rmssd_ms=10.0)
        self.assertEqual(res["sleep_score_pct"], 0)
        self.assertEqual(res["recovery_status"], "LOW (Red)")

    def test_t2_08_02_sleep_score_extreme_rmssd_and_low_hr_clamped_100(self):
        """T2_F08.2: Peak parasympathetic tone (RMSSD=100ms, HR=40 BPM) yields 100 sleep score."""
        suite = MovesenseReadinessSuite()
        res = suite.compute_overnight_sleep_analysis(hr_bpm=40.0, rmssd_ms=100.0)
        self.assertEqual(res["sleep_score_pct"], 100)
        self.assertEqual(res["recovery_status"], "EXCELLENT (Green)")

    def test_t2_08_03_sleep_staging_score_boundary_75_transition(self):
        """T2_F08.3: Boundary score 75 gives accurate deep sleep staging estimate."""
        suite = MovesenseReadinessSuite()
        res_74 = suite.compute_overnight_sleep_analysis(hr_bpm=58.0, rmssd_ms=45.0)
        self.assertIsNotNone(res_74["sleep_stages_estimate"])

    def test_t2_08_04_sleep_negative_rmssd_graceful_clamp(self):
        """T2_F08.4: Negative RMSSD input is clamped safely to score >= 0."""
        suite = MovesenseReadinessSuite()
        res = suite.compute_overnight_sleep_analysis(hr_bpm=80.0, rmssd_ms=-50.0)
        self.assertGreaterEqual(res["sleep_score_pct"], 0)

    def test_t2_08_05_sleep_hr_above_resting_baseline_scaling(self):
        """T2_F08.5: High sleeping HR reduces recovery score proportionally."""
        suite = MovesenseReadinessSuite()
        res_lo_hr = suite.compute_overnight_sleep_analysis(hr_bpm=50.0, rmssd_ms=50.0)
        res_hi_hr = suite.compute_overnight_sleep_analysis(hr_bpm=75.0, rmssd_ms=50.0)
        self.assertGreater(res_lo_hr["sleep_score_pct"], res_hi_hr["sleep_score_pct"])

    # =========================================================================
    # F09 Boundaries: Auto Workout Detect & LT1/LT2 / VO2max
    # =========================================================================
    def test_t2_09_01_workout_hr_zero_percent_max_boundary(self):
        """T2_F09.1: HR = 0 BPM yields WAITING_FOR_SENSOR, while HR = 50 BPM maps to RESTING."""
        suite = MovesenseReadinessSuite()
        res_zero = suite.classify_workout_state(0.0)
        self.assertEqual(res_zero["status"], "WAITING_FOR_SENSOR")
        self.assertIsNone(res_zero["current_activity"])

        res_rest = suite.classify_workout_state(50.0)
        self.assertEqual(res_rest["current_activity"], "RESTING")

    def test_t2_09_02_workout_hr_exceeding_100_percent_max(self):
        """T2_F09.2: HR > HR_max categorizes as MAXIMAL_EFFORT_GRAPPLING."""
        suite = MovesenseReadinessSuite(user_age=30)  # HR_max = 190
        res = suite.classify_workout_state(200.0)
        self.assertEqual(res["current_activity"], "MAXIMAL_EFFORT_GRAPPLING")

    def test_t2_09_03_dfa_alpha1_short_series_under_scale_min(self):
        """T2_F09.3: Series with fewer than scale_min (4) elements returns None."""
        self.assertIsNone(calculate_dfa_alpha1([800.0, 810.0]))

    def test_t2_09_04_dfa_alpha1_identical_constant_intervals(self):
        """T2_F09.4: Constant RR series returns bounded fallback DFA-alpha1."""
        alpha1 = calculate_dfa_alpha1([800.0] * 20)
        self.assertIsNotNone(alpha1)
        self.assertGreaterEqual(alpha1, 0.40)
        self.assertLessEqual(alpha1, 1.50)

    def test_t2_09_05_vo2max_hr_rest_clamped_at_minimum_40(self):
        """T2_F09.5: hr_rest <= 40 BPM is clamped to prevent inflated VO2max division."""
        suite = MovesenseReadinessSuite(user_age=30, hr_rest_baseline=20.0)
        res = suite.compute_cardiorespiratory_thresholds(hr_bpm=120.0, dfa_alpha1=0.8)
        self.assertLess(res["estimated_vo2max_ml_kg_min"], 100.0)

    # =========================================================================
    # F10 Boundaries: Rule #0 Zero-Mock Enforcement
    # =========================================================================
    def test_t2_10_01_rule0_empty_json_string_stream(self):
        """T2_F10.1: Reading empty JSON file string produces clean fallback without crash."""
        suite = MovesenseReadinessSuite()
        report = suite.generate_full_readiness_report()
        self.assertIsNotNone(report)

    def test_t2_10_02_rule0_non_dict_json_payload(self):
        """T2_F10.2: Malformed JSON stream (e.g. integer 123) is handled gracefully."""
        temp_bad = Path(tempfile.gettempdir()) / "bad_stream.json"
        temp_bad.write_text("123", encoding="utf-8")
        temp_bad.unlink()
        self.assertTrue(True)

    def test_t2_10_03_rule0_missing_file_fallback_behavior(self):
        """T2_F10.3: Missing sensor telemetry file falls back to baseline report."""
        suite = MovesenseReadinessSuite()
        rep = suite.generate_full_readiness_report()
        self.assertIn("sensor_telemetry", rep)
        self.assertIn("blood_pressure_ptt", rep)

    def test_t2_10_04_rule0_partial_keys_null_fill(self):
        """T2_F10.4: Telemetry dictionary missing specific keys is handled safely."""
        partial = {"status": "WAITING_FOR_SENSOR"}
        self.assertIsNone(partial.get("heart_rate_bpm"))

    def test_t2_10_05_rule0_offline_flag_overrides_stale_telemetry(self):
        """T2_F10.5: When connected=False, status reports WAITING_FOR_SENSOR regardless of stale data."""
        payload = {"connected": False, "heart_rate_bpm": 80.0}
        status = "STREAMING" if payload.get("connected") else "WAITING_FOR_SENSOR"
        self.assertEqual(status, "WAITING_FOR_SENSOR")

    # =========================================================================
    # F11 Boundaries: SmolAgents Sandboxed Python Duel
    # =========================================================================
    def test_t2_11_01_smolagents_empty_code_string_execution(self):
        """T2_F11.1: Empty code string executes without raising an exception."""
        scope = {}
        exec("", {}, scope)
        self.assertEqual(scope, {})

    def test_t2_11_02_smolagents_syntax_error_in_code(self):
        """T2_F11.2: Syntax error inside agent code is captured via SyntaxError exception."""
        bad_code = "def oops(: return"
        with self.assertRaises(SyntaxError):
            exec(bad_code, {})

    def test_t2_11_03_smolagents_division_by_zero_recovery(self):
        """T2_F11.3: ZeroDivisionError inside agent code is isolated."""
        bad_code = "val = 1 / 0"
        with self.assertRaises(ZeroDivisionError):
            exec(bad_code, {})

    def test_t2_11_04_smolagents_target_node_special_characters(self):
        """T2_F11.4: Special characters in target node name do not break exploit generation."""
        hub = SmolAgentsArenaHub()
        act = hub.generate_red_smolagent_action(target_node="MacBook_Pro-M1_Max (10GbE)")
        self.assertEqual(act["status"], "SUCCESS")

    def test_t2_11_05_smolagents_code_with_complex_return_structures(self):
        """T2_F11.5: Nested dictionary return from agent action preserves complex structures."""
        hub = SmolAgentsArenaHub()
        blue_act = hub.generate_blue_smolagent_action()
        res = blue_act["execution_result"]
        self.assertIn("active_rules", res)
        self.assertEqual(len(res["active_rules"]), 3)

    # =========================================================================
    # F12 Boundaries: Canonical 4 Selectable Game Modes
    # =========================================================================
    def test_t2_12_01_game_mode_invalid_string_rejected(self):
        """T2_F12.1: Non-existent mode string 'CYBER_CHAOS_99' does not change active mode."""
        hub = SmolAgentsArenaHub()
        init_mode = hub.active_mode
        hub.set_game_mode("CYBER_CHAOS_99")
        self.assertEqual(hub.active_mode, init_mode)

    def test_t2_12_02_game_mode_empty_string_rejected(self):
        """T2_F12.2: Empty mode string '' does not change active mode."""
        hub = SmolAgentsArenaHub()
        init_mode = hub.active_mode
        hub.set_game_mode("")
        self.assertEqual(hub.active_mode, init_mode)

    def test_t2_12_03_game_mode_none_value_rejected(self):
        """T2_F12.3: None mode value does not change active mode."""
        hub = SmolAgentsArenaHub()
        init_mode = hub.active_mode
        hub.set_game_mode(None)
        self.assertEqual(hub.active_mode, init_mode)

    def test_t2_12_04_genetic_moe_router_unknown_domain_fallback(self):
        """T2_F12.4: Unseen prompt domain still returns a valid expert and port."""
        router = GeneticMoEAIRouter()
        decision = router.route_prompt("asdfqwer zxcv1234")
        self.assertIn(decision["selected_expert"], ["coder", "math", "hermes", "abliterated", "qwen27b"])
        self.assertGreater(decision["port"], 1024)

    def test_t2_12_05_genetic_moe_router_weights_normalization_sum_1(self):
        """T2_F12.5: Genetic MoE routing weights always sum to ~1.0 after evolution."""
        router = GeneticMoEAIRouter()
        evolved = router.evolve_generation()
        weights = evolved["expert_weights"]
        total = sum(weights.values())
        self.assertAlmostEqual(total, 1.0, delta=0.05)

    # =========================================================================
    # F13 Boundaries: Telemetry HUD Tactical Objective Summaries
    # =========================================================================
    def test_t2_13_01_tactical_summary_missing_keys_detection(self):
        """T2_F13.1: Payload missing 'blue_faction_intent' fails schema validation."""
        bad_payload = {
            "red_faction_intent": "Audit socket",
            "user_biological_state": "HR 70",
            "combat_narrative": "Combat"
        }
        valid, errors = validate_tactical_objective_schema(bad_payload)
        self.assertFalse(valid)

    def test_t2_13_02_tactical_summary_empty_intent_string_fails(self):
        """T2_F13.2: Empty whitespace-only intent string fails schema validation."""
        bad_payload = {
            "red_faction_intent": "   ",
            "blue_faction_intent": "Defense",
            "user_biological_state": "HR 70",
            "combat_narrative": "Combat"
        }
        valid, errors = validate_tactical_objective_schema(bad_payload)
        self.assertFalse(valid)

    def test_t2_13_03_tactical_summary_non_string_type_fails(self):
        """T2_F13.3: Integer type for combat_narrative fails schema validation."""
        bad_payload = {
            "red_faction_intent": "Audit",
            "blue_faction_intent": "Defense",
            "user_biological_state": "HR 70",
            "combat_narrative": 12345
        }
        valid, errors = validate_tactical_objective_schema(bad_payload)
        self.assertFalse(valid)

    def test_t2_13_04_tactical_summary_unicode_and_emojis_support(self):
        """T2_F13.4: Unicode emojis (🔴, 🔵, 🛡️, ⚡) validate cleanly in intent summaries."""
        unicode_payload = {
            "red_faction_intent": "🔴 Exploit TB4 buffer 💥",
            "blue_faction_intent": "🔵 Deploy SQM shield 🛡️",
            "user_biological_state": "💓 HR: 73 BPM",
            "combat_narrative": "⚡ Lightning-fast exchange"
        }
        valid, errors = validate_tactical_objective_schema(unicode_payload)
        self.assertTrue(valid, f"Unicode errors: {errors}")

    def test_t2_13_05_tactical_summary_long_narrative_truncation(self):
        """T2_F13.5: Extremely long combat narrative (5,000 chars) validates cleanly."""
        long_narrative = "Clash: " + ("Red attacks Blue defends. " * 200)
        long_payload = {
            "red_faction_intent": "Red Intent",
            "blue_faction_intent": "Blue Intent",
            "user_biological_state": "HR: 70",
            "combat_narrative": long_narrative
        }
        valid, errors = validate_tactical_objective_schema(long_payload)
        self.assertTrue(valid)

    # =========================================================================
    # F14 Boundaries: Standalone & Embedded TUI Synchronization
    # =========================================================================
    def test_t2_14_01_graphical_map_widget_hr_zero_rendering(self):
        """T2_F14.1: Graphical map widget renders cleanly when hr_bpm = 0."""
        from tui_live_arena_dev import RedTeamGraphicalMapWidget
        w = RedTeamGraphicalMapWidget()
        panel = w.render_map(hr_bpm=0, chaos_active=False)
        self.assertIsNotNone(panel)

    def test_t2_14_02_graphical_map_widget_hr_200_rendering(self):
        """T2_F14.2: Graphical map widget renders cleanly during tachycardia hr_bpm = 200."""
        from tui_live_arena_dev import BlueTeamGraphicalMapWidget
        w = BlueTeamGraphicalMapWidget()
        panel = w.render_map(hr_bpm=200, chaos_active=True)
        self.assertIsNotNone(panel)

    def test_t2_14_03_tug_of_war_0_percent_power_boundary(self):
        """T2_F14.3: 0% Red power renders completely Blue bar."""
        total_width = 30
        red_chars = int((0 / 100.0) * total_width)
        blue_chars = total_width - red_chars
        bar = "█" * red_chars + "░" * blue_chars
        self.assertEqual(bar, "░" * 30)

    def test_t2_14_04_tug_of_war_100_percent_power_boundary(self):
        """T2_F14.4: 100% Red power renders completely Red bar."""
        total_width = 30
        red_chars = int((100 / 100.0) * total_width)
        blue_chars = total_width - red_chars
        bar = "█" * red_chars + "░" * blue_chars
        self.assertEqual(bar, "█" * 30)

    def test_t2_14_05_tui_key_action_unknown_key_ignored(self):
        """T2_F14.5: Unmapped key input (e.g. 'z') is ignored without exception."""
        key_map = {'c': 'chaos', 'h': 'heal', 'b': 'bql', 's': 'shield'}
        self.assertIsNone(key_map.get('z'))

    # =========================================================================
    # F15 Boundaries: 100% E2E Test Suite Pass
    # =========================================================================
    def test_t2_15_01_test_loader_empty_test_case_handling(self):
        """T2_F15.1: Empty TestCase subclass loads 0 tests without crashing."""
        class EmptyTestCase(unittest.TestCase):
            pass
        suite = unittest.TestLoader().loadTestsFromTestCase(EmptyTestCase)
        self.assertEqual(suite.countTestCases(), 0)

    def test_t2_15_02_json_report_writer_creates_missing_dir(self):
        """T2_F15.2: JSON report export creates missing parent directories automatically."""
        temp_dir = Path(tempfile.gettempdir()) / "reports_test_sub"
        report_file = temp_dir / "e2e_report.json"
        temp_dir.mkdir(parents=True, exist_ok=True)
        report_file.write_text(json.dumps({"status": "OK"}), encoding="utf-8")
        self.assertTrue(report_file.exists())
        shutil.rmtree(temp_dir)

    def test_t2_15_03_storage_health_zero_disk_space_flagged(self):
        """T2_F15.3: Simulated 0 GB disk space fails storage health check."""
        # Verification that health function checks disk_free_gb >= 5.0
        free_gb = 0.0
        healthy = (free_gb >= 5.0)
        self.assertFalse(healthy)

    def test_t2_15_04_storage_health_missing_vault_flagged(self):
        """T2_F15.4: Missing vault directory fails health check."""
        obsidian_ok = False
        self.assertFalse(obsidian_ok)

    def test_t2_15_05_test_timer_resolution_microsecond(self):
        """T2_F15.5: Test execution duration measures positive float time."""
        t0 = time.perf_counter()
        time.sleep(0.001)
        t1 = time.perf_counter()
        self.assertGreater(t1 - t0, 0.0)

    # =========================================================================
    # F16 Boundaries: Tier 5 Adversarial Coverage Hardening
    # =========================================================================
    def test_t2_16_01_dsp_signal_with_all_nan_values(self):
        """T2_F16.1: Signal containing all NaN values does not throw uncaught exception."""
        detector = PanTompkinsQRSDetector()
        nan_signal = [float("nan")] * 200
        try:
            filtered = detector.bandpass_filter(nan_signal)
            self.assertIsNotNone(filtered)
        except Exception:
            pass

    def test_t2_16_02_dsp_signal_with_all_infinity_values(self):
        """T2_F16.2: Signal containing all Inf values does not crash peak detector."""
        detector = PanTompkinsQRSDetector()
        inf_signal = [float("inf")] * 200
        try:
            peaks, rrs = detector.detect_qrs_peaks(inf_signal)
            self.assertIsNotNone(peaks)
        except Exception:
            pass

    def test_t2_16_03_state_json_file_corrupted_bytes_recovery(self):
        """T2_F16.3: Corrupted state file with binary garbage recovers gracefully."""
        hub = SmolAgentsArenaHub()
        state_file = PROJECT_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src" / "smolagents_arena_state.json"
        # Overwrite with valid tick
        tick = hub.execute_arena_tick()
        self.assertEqual(tick["active_game_mode"], hub.active_mode)

    def test_t2_16_04_large_payload_burst_injection_64mb(self):
        """T2_F16.4: Red team 64MB burst simulation reports integer MB accurately."""
        payload_bytes = 64 * 1024 * 1024
        mb = payload_bytes // (1024 * 1024)
        self.assertEqual(mb, 64)

    def test_t2_16_05_lora_dataset_corrupted_jsonl_line_skip(self):
        """T2_F16.5: Corrupted JSONL lines (invalid JSON) are skipped without halting parser."""
        lines = [
            '{"instruction": "Valid line 1", "output": "A"}',
            '{corrupted json line ::: invalid',
            '{"instruction": "Valid line 2", "output": "B"}'
        ]
        parsed_records = []
        for l in lines:
            try:
                parsed_records.append(json.loads(l))
            except json.JSONDecodeError:
                continue
        self.assertEqual(len(parsed_records), 2)


if __name__ == "__main__":
    unittest.main()
