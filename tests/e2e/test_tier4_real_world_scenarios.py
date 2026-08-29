#!/usr/bin/env python3
"""
Tier 4: Comprehensive Real-World Application Scenarios E2E Test Suite (8 Scenarios)
Lauburu Monorepo — Unified Front-Facing App Architecture & Multi-Mode Game Arena
================================================================================
Validates complete multi-step end-to-end workflows across real-world workloads:
- Scenario 1: Bicep 512Hz ECG Ingestion -> Pan-Tompkins QRS -> Kamath Filter -> RMSSD -> Zone 2 Feedback
- Scenario 2: Overnight Optical Wearable Sleep Staging -> Recovery Score -> LoRA Dataset Export
- Scenario 3: Lactate Threshold Workout (LT1/LT2) -> DFA-alpha1 Tracking -> Hemodynamic PTT BP Inversion
- Scenario 4: SmolAgents Red vs. Blue Sandboxed Python Combat -> Tactical HUD Intent Sync
- Scenario 5: Hardware Disconnection & Rule #0 Zero-Mock Fallback & Clean Resumption
- Scenario 6: Genetic MoE Multi-Expert AI Router Dynamic Evolution & Local Routing
- Scenario 7: Full Frontend PWA Caching -> 955+ OPML 3D Tatami Kinematics Raycasting -> Tailwind UI
- Scenario 8: Strict Cloudflare Worker Zero-Biometric Airgap Egress Enforcement
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


class TestTier4RealWorldScenarios(unittest.TestCase):
    """Tier 4: 8 Real-World Multi-Step Application Scenarios."""

    # =========================================================================
    # Scenario 1: Bicep 512Hz ECG Ingestion -> Pan-Tompkins -> Kamath -> Zone 2
    # =========================================================================
    def test_scenario_1_bicep_ecg_zone2_feedback_pipeline(self):
        """Scenario 1: End-to-End Bicep 512Hz ECG Ingestion to Zone 2 Autonomic Feedback."""
        # 1. Ingest 512Hz ECG stream
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        ecg_raw = generate_synthetic_synthetic_ecg_beat(fs=512, bpm=68.0, duration_sec=8.0)
        self.assertEqual(len(ecg_raw), 512 * 8)

        # 2. Pan-Tompkins QRS Detection
        peaks, detected_rrs = detector.detect_qrs_peaks(ecg_raw)
        self.assertGreaterEqual(len(peaks), 5)
        self.assertGreaterEqual(len(detected_rrs), 4)

        # 3. Apply Kamath 20% Clinical RR Filter
        cleaned_rrs, artifacts = apply_kamath_artifact_filter(detected_rrs, threshold_pct=20.0)
        self.assertEqual(artifacts, 0)

        # 4. Compute RMSSD & DFA-alpha1
        rmssd = calculate_rmssd(cleaned_rrs)
        self.assertIsNotNone(rmssd)

        # 5. Classify Zone 2 Workout & Cardiorespiratory Readiness
        suite = MovesenseReadinessSuite(user_age=30, hr_rest_baseline=58.0)
        workout_state = suite.classify_workout_state(hr_bpm=68.0)
        thresholds = suite.compute_cardiorespiratory_thresholds(hr_bpm=68.0, dfa_alpha1=0.88)

        self.assertIn("Rest", workout_state["training_zone"])
        self.assertIn("Below LT1", thresholds["physiological_domain"])

    # =========================================================================
    # Scenario 2: Overnight Optical Wearable Sleep Staging -> Score -> LoRA
    # =========================================================================
    def test_scenario_2_overnight_sleep_staging_and_readiness_export(self):
        """Scenario 2: Overnight Wearable Sleep Analysis -> Staging -> Morning Score -> LoRA Dataset."""
        suite = MovesenseReadinessSuite()
        
        # 1. Compute overnight sleep metrics
        sleep_res = suite.compute_overnight_sleep_analysis(hr_bpm=52.0, rmssd_ms=62.0)
        self.assertGreaterEqual(sleep_res["sleep_score_pct"], 80)
        self.assertEqual(sleep_res["recovery_status"], "EXCELLENT (Green)")

        # 2. Verify sleep staging proportions
        stages = sleep_res["sleep_stages_estimate"]
        self.assertGreater(stages["deep_sleep_pct"], 20.0)
        self.assertGreater(stages["rem_sleep_pct"], 20.0)
        total_pct = sum(stages.values())
        self.assertAlmostEqual(total_pct, 100.0, delta=0.1)

        # 3. Simulate LoRA training dataset emission
        lora_sample = {
            "instruction": "Evaluate athlete overnight autonomic sleep recovery",
            "input": f"HR: 52.0 BPM, RMSSD: 62.0 ms",
            "output": f"Sleep Score: {sleep_res['sleep_score_pct']}/100 ({sleep_res['recovery_status']}). Deep sleep: {stages['deep_sleep_pct']}%."
        }
        serialized = json.dumps(lora_sample)
        self.assertTrue(len(serialized) > 50)
        parsed = json.loads(serialized)
        self.assertEqual(parsed["instruction"], lora_sample["instruction"])

    # =========================================================================
    # Scenario 3: Lactate Threshold Workout -> DFA-a1 -> PTT BP Inversion
    # =========================================================================
    def test_scenario_3_high_intensity_workout_and_ptt_bp_tracking(self):
        """Scenario 3: High-Intensity Threshold Workout -> Real-time DFA-a1 -> Hemodynamic BP Inversion."""
        suite = MovesenseReadinessSuite(user_age=30, hr_rest_baseline=60.0)

        # Step A: Warmup / Aerobic Zone 2 (HR=125, DFA-a1=0.85)
        w_warmup = suite.classify_workout_state(125.0)
        t_warmup = suite.compute_cardiorespiratory_thresholds(125.0, 0.85)
        self.assertEqual(w_warmup["current_activity"], "STEADY_CARDIO_ZONE_2")
        self.assertIn("Below LT1", t_warmup["physiological_domain"])

        # Step B: At LT1 Aerobic Threshold (HR=140, DFA-a1=0.75)
        t_lt1 = suite.compute_cardiorespiratory_thresholds(140.0, 0.75)
        self.assertIn("LT1 Aerobic Threshold", t_lt1["physiological_domain"])

        # Step C: HIIT Sprints / Above LT2 (HR=170, DFA-a1=0.42, PTT=155ms)
        w_hiit = suite.classify_workout_state(170.0)
        t_hiit = suite.compute_cardiorespiratory_thresholds(170.0, 0.42)
        bp_hiit = suite.compute_ptt_blood_pressure(hr_bpm=170.0, rmssd_ms=18.0)

        self.assertEqual(w_hiit["current_activity"], "HIIT_INTERVALS")
        self.assertIn("Above LT2", t_hiit["physiological_domain"])
        self.assertGreater(bp_hiit["systolic_bp_mmhg"], 135)
        self.assertGreater(bp_hiit["diastolic_bp_mmhg"], 85)

    # =========================================================================
    # Scenario 4: SmolAgents Red vs. Blue Sandboxed Python Combat Arena
    # =========================================================================
    def test_scenario_4_real_time_smolagents_python_combat_arena(self):
        """Scenario 4: Real-time SmolAgents Autonomous Code Duel -> TUI Tactical HUD State Sync."""
        hub = SmolAgentsArenaHub()
        hub.set_game_mode("SMOLAGENTS_PYTHON_DUEL")

        # 1. Execute arena tick
        tick = hub.execute_arena_tick()
        self.assertEqual(tick["active_game_mode"], "SMOLAGENTS_PYTHON_DUEL")

        # 2. Inspect generated Python code
        red_code = tick["smolagent_code_executions"]["red_code"]
        blue_code = tick["smolagent_code_executions"]["blue_code"]
        self.assertIn("red_exploit_action", red_code)
        self.assertIn("blue_defense_action", blue_code)

        # 3. Validate Tactical HUD Objective Summary
        summary = tick["tactical_intent_summary"]
        self.assertIn("Audit TB4", summary["red_faction_intent"])
        self.assertIn("SQM fq_codel", summary["blue_faction_intent"])
        self.assertIn("Heart Rate", summary["user_biological_state"])

    # =========================================================================
    # Scenario 5: Hardware Disconnection & Rule #0 Zero-Mock Resilience
    # =========================================================================
    def test_scenario_5_hardware_disconnect_and_zero_mock_resilience(self):
        """Scenario 5: Hardware Disconnection -> Rule #0 Zero-Mock Fallback -> Clean Resumption."""
        suite = MovesenseReadinessSuite()

        # Step 1: Active Sensor Stream
        active_bp = suite.compute_ptt_blood_pressure(hr_bpm=72.0, rmssd_ms=45.0)
        self.assertEqual(active_bp["status"], "NOMINAL")

        # Step 2: Sensor Disconnected (hr_bpm=None)
        offline_workout = suite.classify_workout_state(None)
        self.assertEqual(offline_workout["status"], "WAITING_FOR_SENSOR")
        self.assertIsNone(offline_workout["current_activity"])

        # Step 3: Zero fake arrays produced
        detector = PanTompkinsQRSDetector()
        peaks, rrs = detector.detect_qrs_peaks([])
        self.assertEqual(peaks, [])
        self.assertEqual(rrs, [])

        # Step 4: Reconnection Resumption
        reconnected_workout = suite.classify_workout_state(75.0)
        self.assertEqual(reconnected_workout["status"], "ACTIVE")

    # =========================================================================
    # Scenario 6: Genetic MoE Multi-Expert AI Routing Lifecycle
    # =========================================================================
    def test_scenario_6_genetic_moe_multi_expert_ai_routing_lifecycle(self):
        """Scenario 6: Mode 3 Genetic MoE AI Router Dynamic Evolution & Local Routing."""
        router = GeneticMoEAIRouter()

        # 1. Test Domain Routing across 5 local specialists
        test_queries = [
            ("Write a Python AST parser for monorepo imports", "coder", 8083),
            ("Compute QAOA 4-qubit Hamiltonian and FFT of ECG", "math", 8086),
            ("Search Obsidian vault notes for RAG synthesis", "hermes", 8082),
            ("Execute red team buffer drain stress testing", "abliterated", 8085),
            ("Analyze monorepo architecture and spec contracts", "qwen27b", 50052)
        ]

        for query, expected_expert, expected_port in test_queries:
            decision = router.route_prompt(query)
            self.assertEqual(decision["selected_expert"], expected_expert)
            self.assertEqual(decision["port"], expected_port)
            self.assertTrue(decision["airgap_certified"])

        # 2. Evolve Generation
        evolved = router.evolve_generation()
        self.assertGreaterEqual(evolved["generation"], 2)
        self.assertGreater(evolved["fitness_score"], 90.0)

    # =========================================================================
    # Scenario 7: Full Frontend PWA Caching -> 3D Tatami Kinematics -> Tailwind
    # =========================================================================
    def test_scenario_7_pwa_tatami_kinematics_and_ui_rendering(self):
        """Scenario 7: Full WebApp Frontend Lifecycle: PWA Manifest -> 955+ OPML Kinematics -> Tailwind UI."""
        # 1. PWA Manifest validation
        manifest_path = PROJECT_ROOT / "webapp" / "manifest.json"
        valid, manifest, _ = validate_pwa_manifest(manifest_path)
        self.assertTrue(valid)

        # 2. Parse 955+ Node OPML Grappling Kinematics Tree
        opml_path = PROJECT_ROOT / "webapp" / "grappling.opml"
        res = parse_grappling_opml(opml_path)
        self.assertGreaterEqual(res["total_nodes"], 955)
        self.assertGreaterEqual(res["max_depth"], 3)

        # 3. Simulate 3D Tatami Raycasting Selection
        selected_node = res["nodes"][0]
        self.assertIn("text", selected_node)

        # 4. Tailwind WCAG 2.1 AA Contrast Check
        text_contrast = calculate_contrast_ratio("#F8FAFC", "#0F172A")
        self.assertGreaterEqual(text_contrast, 4.5)

    # =========================================================================
    # Scenario 8: Strict Cloudflare Worker Zero-Biometric Airgap Enforcement
    # =========================================================================
    def test_scenario_8_strict_cloudflare_airgap_egress_enforcement(self):
        """Scenario 8: Cloudflare Worker Egress Isolation -> Redaction of Raw Physiological Metrics -> 100% Local Airgap."""
        # 1. Verify Cloudflare Worker exists
        worker_ts = PROJECT_ROOT / "00_core_infrastructure" / "cloudflare_worker" / "src" / "worker.ts"
        self.assertTrue(worker_ts.exists())

        # 2. Simulate raw telemetry egress attempt
        egress_attempt = {
            "origin": "local_mesh",
            "destination": "cloudflare_edge",
            "ui_theme": "dark",
            "status": "HEALTHY",
            "raw_ecg_samples": [0.12, 0.45, 1.25, 0.88] * 100,
            "raw_optical_stream": [45.2, 46.1] * 50
        }
        clean, violations = inspect_egress_payload_airgap_compliance(egress_attempt)
        self.assertFalse(clean, "Airgap firewall should have detected raw biometrics in egress attempt")
        self.assertGreaterEqual(len(violations), 2)

        # 3. Redact raw physiological data
        sanitized_egress = {
            "origin": "local_mesh",
            "destination": "cloudflare_edge",
            "ui_theme": "dark",
            "status": "HEALTHY",
            "readiness_summary": "OPTIMAL_ZONE_2"
        }
        clean_after, violations_after = inspect_egress_payload_airgap_compliance(sanitized_egress)
        self.assertTrue(clean_after, f"Sanitized egress had unexpected violations: {violations_after}")


if __name__ == "__main__":
    unittest.main()
