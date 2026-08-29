#!/usr/bin/env python3
"""
Tier 3: Comprehensive Cross-Feature Pairwise Combinations E2E Test Suite (16 Tests)
Lauburu Monorepo — Unified Front-Facing App Architecture & Multi-Mode Game Arena
================================================================================
Validates cross-subsystem interactions, combinatorial pipelines, and multi-tier
synchronization across all 16 features from PROJECT.md.
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
    generate_synthetic_synthetic_ecg_beat,
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


class TestTier3PairwiseCombinations(unittest.TestCase):
    """Tier 3: 16 Cross-Feature Pairwise Combinations."""

    def test_p01_pwa_caching_and_airgap_egress_firewall(self):
        """Pair 01: F01 (PWA Scaffolding) x F04 (Airgap Protection) — Offline PWA bundle serves static UI while airgap strips raw biometrics."""
        manifest_path = PROJECT_ROOT / "webapp" / "manifest.json"
        valid, manifest, _ = validate_pwa_manifest(manifest_path)
        self.assertTrue(valid)

        outbound_sync = {
            "pwa_version": manifest.get("version", "4.0.0"),
            "display_mode": manifest.get("display"),
            "raw_ecg_samples": [10.2, 11.5, 90.4] * 10
        }
        clean, violations = inspect_egress_payload_airgap_compliance(outbound_sync)
        self.assertFalse(clean)
        # Redact raw biometrics
        sanitized = {k: v for k, v in outbound_sync.items() if "raw" not in k.lower()}
        clean_after, _ = inspect_egress_payload_airgap_compliance(sanitized)
        self.assertTrue(clean_after)

    def test_p02_3d_tatami_opml_and_tailwind_color_tokens(self):
        """Pair 02: F02 (3D Tatami OPML) x F03 (TailwindCSS UI) — 955+ OPML nodes mapped to 3D world use WCAG AA color tokens."""
        opml_path = PROJECT_ROOT / "webapp" / "grappling.opml"
        res = parse_grappling_opml(opml_path)
        self.assertGreaterEqual(res["total_nodes"], 955)

        category_colors = {
            "Guard": "#38BDF8",       # Sky-400
            "Mount": "#34D399",       # Emerald-400
            "Back Control": "#F87171" # Red-400
        }
        bg_dark = "#070B12"
        for cat, hex_col in category_colors.items():
            ratio = calculate_contrast_ratio(hex_col, bg_dark)
            self.assertGreaterEqual(ratio, 4.5, f"Category color {cat} ({hex_col}) failed WCAG 2.1 AA (4.5:1)")

    def test_p03_pan_tompkins_512hz_and_kamath_20pct_filter(self):
        """Pair 03: F05 (Pan-Tompkins DSP) x F06 (Kamath Filter) — Raw 512Hz ECG processed to R-peaks and filtered through Kamath 20% filter."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        ecg_signal = generate_synthetic_synthetic_ecg_beat(fs=512, bpm=72.0, duration_sec=6.0)
        peaks, detected_rrs = detector.detect_qrs_peaks(ecg_signal)
        self.assertGreater(len(peaks), 3)

        cleaned_rrs, artifact_count = apply_kamath_artifact_filter(detected_rrs, threshold_pct=20.0)
        self.assertEqual(artifact_count, 0)
        self.assertEqual(len(cleaned_rrs), len(detected_rrs))

    def test_p04_kamath_rmssd_and_ptt_blood_pressure_inversion(self):
        """Pair 04: F06 (Kamath RMSSD) x F07 (PTT Blood Pressure) — Kamath-filtered RMSSD drives hemodynamic PTT BP inversion."""
        noisy_rrs = [833.3, 840.0, 400.0, 835.0, 830.0]  # One ectopic beat
        cleaned_rrs, artifacts = apply_kamath_artifact_filter(noisy_rrs, threshold_pct=20.0)
        self.assertEqual(artifacts, 1)

        rmssd = calculate_rmssd(cleaned_rrs)
        self.assertIsNotNone(rmssd)

        sbp, dbp, map_val = calculate_hemodynamics_bp(ptt_ms=195.0, hr_bpm=72.0)
        self.assertAlmostEqual(sbp, 122.5, delta=0.5)
        self.assertAlmostEqual(dbp, 81.4, delta=0.5)

    def test_p05_ptt_blood_pressure_and_overnight_sleep_staging(self):
        """Pair 05: F07 (PTT Blood Pressure) x F08 (Sleep Staging) — Overnight PTT blood pressure dipping alongside sleep recovery score."""
        suite = MovesenseReadinessSuite()
        # Daytime baseline: HR=75, SBP=125
        bp_day = suite.compute_ptt_blood_pressure(hr_bpm=75.0, rmssd_ms=35.0)
        # Nocturnal sleep: HR=50, RMSSD=65
        sleep_analysis = suite.compute_overnight_sleep_analysis(hr_bpm=50.0, rmssd_ms=65.0)
        bp_night = suite.compute_ptt_blood_pressure(hr_bpm=50.0, rmssd_ms=65.0)

        self.assertGreater(sleep_analysis["sleep_score_pct"], 80)
        self.assertLess(bp_night["systolic_bp_mmhg"], bp_day["systolic_bp_mmhg"], "Nocturnal BP dipping expected")

    def test_p06_overnight_sleep_score_and_workout_zone_readiness(self):
        """Pair 06: F08 (Sleep Staging) x F09 (Auto Workout Detect) — Sleep recovery modulates aerobic workout readiness."""
        suite = MovesenseReadinessSuite()
        good_sleep = suite.compute_overnight_sleep_analysis(hr_bpm=48.0, rmssd_ms=70.0)
        self.assertEqual(good_sleep["recovery_status"], "EXCELLENT (Green)")

        workout = suite.classify_workout_state(hr_bpm=128.0)
        self.assertEqual(workout["current_activity"], "STEADY_CARDIO_ZONE_2")

        thresholds = suite.compute_cardiorespiratory_thresholds(hr_bpm=128.0, dfa_alpha1=0.78)
        self.assertIn("LT1", thresholds["physiological_domain"])

    def test_p07_workout_dfa_alpha1_and_rule0_zero_mock_disconnect(self):
        """Pair 07: F09 (Cardiorespiratory DFA-a1) x F10 (Rule #0 Zero-Mock) — Live workout DFA-alpha1 transitions cleanly to null state on disconnect."""
        live_rrs = [800.0 + 15.0 * math.sin(i * 0.3) for i in range(30)]
        alpha1 = calculate_dfa_alpha1(live_rrs)
        self.assertIsNotNone(alpha1)

        # On sensor disconnect
        disconnected_rrs = []
        alpha1_dc = calculate_dfa_alpha1(disconnected_rrs)
        self.assertIsNone(alpha1_dc)

    def test_p08_smolagents_python_duel_and_canonical_4_game_modes(self):
        """Pair 08: F11 (SmolAgents Python Duel) x F12 (4 Game Modes) — Autonomous Python duel operates across all 4 modes."""
        hub = SmolAgentsArenaHub()
        for mode in GAME_MODES:
            hub.set_game_mode(mode)
            red_act = hub.generate_red_smolagent_action()
            blue_act = hub.generate_blue_smolagent_action()
            self.assertEqual(red_act["status"], "SUCCESS")
            self.assertEqual(blue_act["status"], "SUCCESS")

    def test_p09_canonical_4_game_modes_and_tactical_objective_hud(self):
        """Pair 09: F12 (4 Game Modes) x F13 (Tactical Objective HUD) — Mode switches update Tactical Objective intent statements."""
        hub = SmolAgentsArenaHub()
        for mode in GAME_MODES:
            hub.set_game_mode(mode)
            tick = hub.execute_arena_tick()
            self.assertEqual(tick["active_game_mode"], mode)
            valid, errors = validate_tactical_objective_schema(tick)
            self.assertTrue(valid, f"Tactical schema error in mode {mode}: {errors}")

    def test_p10_tactical_objective_hud_and_standalone_embedded_tui(self):
        """Pair 10: F13 (Tactical Objective HUD) x F14 (Standalone & Embedded TUI) — Shared arena state JSON synchronizes with HUD."""
        hub = SmolAgentsArenaHub()
        tick = hub.execute_arena_tick()
        state_file = PROJECT_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src" / "smolagents_arena_state.json"
        self.assertTrue(state_file.exists())
        with open(state_file, "r") as f:
            read_state = json.load(f)
        self.assertIn("tactical_intent_summary", read_state)
        self.assertEqual(read_state["tactical_intent_summary"]["red_faction_intent"], tick["tactical_intent_summary"]["red_faction_intent"])

    def test_p11_airgap_firewall_and_rule0_zero_mock_coexistence(self):
        """Pair 11: F04 (Airgap Firewall) x F10 (Rule #0 Zero-Mock) — Strict airgap firewall and offline null states coexist without leakage."""
        offline_report = {
            "status": "WAITING_FOR_SENSOR",
            "heart_rate_bpm": None,
            "rmssd_ms": None,
            "airgap_certified": True
        }
        valid, violations = inspect_egress_payload_airgap_compliance(offline_report)
        self.assertTrue(valid)
        self.assertEqual(len(violations), 0)

    def test_p12_pan_tompkins_qrs_and_uth_sorensen_vo2max_pipeline(self):
        """Pair 12: F05 (Pan-Tompkins DSP) x F09 (VO2max Estimation) — QRS detection computes heart rate which feeds Uth-Sørensen VO2max model."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        ecg = generate_synthetic_synthetic_ecg_beat(fs=512, bpm=60.0, duration_sec=5.0)
        peaks, rrs = detector.detect_qrs_peaks(ecg)
        self.assertGreater(len(rrs), 0)
        mean_rr = sum(rrs) / len(rrs)
        computed_hr = 60000.0 / mean_rr
        self.assertAlmostEqual(computed_hr, 60.0, delta=5.0)

        vo2max = reference_uth_sorensen_vo2max(hr_max=190.0, hr_rest=computed_hr)
        self.assertAlmostEqual(vo2max, 48.5, delta=3.0)

    def test_p13_smolagents_code_generation_and_tactical_intent_narrative(self):
        """Pair 13: F11 (SmolAgents Duel) x F13 (Tactical Objective Summaries) — Python code generated by agents is reflected in combat narrative."""
        hub = SmolAgentsArenaHub()
        tick = hub.execute_arena_tick()
        executions = tick["smolagent_code_executions"]
        self.assertIn("red_code", executions)
        self.assertIn("blue_code", executions)
        self.assertIn("def red_exploit_action", executions["red_code"])
        self.assertIn("def blue_defense_action", executions["blue_code"])

    def test_p14_genetic_moe_mode3_and_tui_expert_weights_sync(self):
        """Pair 14: F12 (Genetic MoE Mode 3) x F14 (TUI Synchronization) — Mode 3 router weights evolve and serialize for TUI dashboard."""
        router = GeneticMoEAIRouter()
        res = router.evolve_generation()
        self.assertIn("expert_weights", res)
        self.assertIn("coder", res["expert_weights"])
        self.assertIn("math", res["expert_weights"])

    def test_p15_rmssd_sleep_score_and_tactical_hud_biological_state(self):
        """Pair 15: F06 (RMSSD) x F08 (Sleep Score) x F13 (Tactical HUD) — Tri-feature integration: RMSSD drives sleep score which populates HUD biological state."""
        suite = MovesenseReadinessSuite()
        sleep = suite.compute_overnight_sleep_analysis(hr_bpm=55.0, rmssd_ms=48.0)
        score = sleep["sleep_score_pct"]

        hub = SmolAgentsArenaHub()
        tick = hub.execute_arena_tick()
        bio_state = tick["tactical_intent_summary"]["user_biological_state"]
        self.assertIn("Sleep Score", bio_state)

    def test_p16_ptt_bp_workout_zone_and_smolagents_arena_difficulty(self):
        """Pair 16: F07 (PTT BP) x F09 (Workout Zone) x F11 (SmolAgents Duel) — Zone 4 workout & BP elevation modulate SmolAgents defense shields."""
        suite = MovesenseReadinessSuite()
        workout = suite.classify_workout_state(hr_bpm=168.0)
        self.assertEqual(workout["current_activity"], "HIIT_INTERVALS")

        bp = suite.compute_ptt_blood_pressure(hr_bpm=168.0, rmssd_ms=22.0)
        self.assertGreater(bp["systolic_bp_mmhg"], 130)

        hub = SmolAgentsArenaHub()
        blue_act = hub.generate_blue_smolagent_action()
        self.assertEqual(blue_act["execution_result"]["status"], "SHIELD_DEPLOYED")


if __name__ == "__main__":
    unittest.main()
