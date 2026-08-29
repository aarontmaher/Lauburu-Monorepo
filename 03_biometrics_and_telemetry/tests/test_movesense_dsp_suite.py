#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dedicated Standalone Unit & Integration Test Suite: Movesense Physiological Readiness & 512Hz DSP
Subsystem: 03_biometrics_and_telemetry/tests/test_movesense_dsp_suite.py
Milestone: M2 Specialist Verification

Tests:
1. 512Hz Pan-Tompkins QRS Detection, Butterworth Bandpass, Derivative, MWI, Dual-Threshold Peak Search.
2. Microsecond Precision R-R Interval Calculation and Kamath et al. 2004 20% Clinical RR Artifact Filter.
3. RMSSD Mathematical Precision & Boundary Handling.
4. Detrended Fluctuation Analysis (DFA-alpha1) 120s Rolling Aerobic & Anaerobic Thresholds (LT1 @ 0.75, LT2 @ 0.50).
5. Pulse Transit Time (PTT) Continuous Hemodynamic Blood Pressure Inversion Model (SBP, DBP, MAP).
6. Overnight PPG Sleep Staging (Deep, REM, Light, Awake), Nocturnal Dipping %, and 0-100 Recovery Score.
7. Auto Workout & Physical Activity Detection (Rest, Zone 2, Tempo, HIIT, Grappling).
8. Cardiorespiratory Thresholds & Uth-Sørensen VO2max Estimation (15.3 * HR_max / HR_rest).
9. Strict Rule #0 Zero-Mock Compliance & Interface Contracts Invariant Verification.
10. End-to-End Streaming Pipeline Integration.
"""

import math
import os
import sys
from typing import Dict, Any, List, Optional
import pytest

# Ensure local subsystem and project root are in sys.path
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
DSP_DIR = os.path.dirname(TEST_DIR)
REPO_ROOT = os.path.dirname(DSP_DIR)

for p in [DSP_DIR, REPO_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

from pan_tompkins_dsp import (
    PanTompkinsQRSDetector,
    apply_kamath_artifact_filter,
    apply_kamath_filter,
    calculate_rmssd,
    calculate_dfa_alpha1,
    calculate_hemodynamics_bp,
    classify_zone2_alignment,
    MovesenseECGPipeline,
)
from movesense_readiness_suite import MovesenseReadinessSuite


# ============================================================================
# 1. 512Hz PAN-TOMPKINS QRS DETECTION & SIGNAL PROCESSING
# ============================================================================

class TestPanTompkins512HzQRSDetector:
    """Empirical verification of 512Hz Pan-Tompkins (1985) digital signal processing."""

    def test_detector_initialization_parameters_512hz(self):
        """Validates sampling rate, MWI window size, and refractory period at 512Hz."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        assert detector.fs == 512
        # 150ms MWI window at 512Hz: 0.150 * 512 = 76 samples
        assert detector.mwi_window == 76
        # 200ms refractory period at 512Hz: 0.200 * 512 = 102 samples
        assert detector.refractory_samples == 102

    def test_detector_initialization_parameters_128hz(self):
        """Validates sampling rate, MWI window size, and refractory period at 128Hz."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=128)
        assert detector.fs == 128
        assert detector.mwi_window == 19  # int(0.150 * 128)
        assert detector.refractory_samples == 25  # int(0.200 * 128)

    def test_butterworth_bandpass_attenuates_dc_and_high_noise(self):
        """Verifies that 0.5-40Hz bandpass filter eliminates DC offset and high-frequency noise."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        n = 512 * 2  # 2 seconds
        # DC baseline wander (+10.0 mV) + 120Hz high frequency noise (+2.0 mV)
        t = [i / 512.0 for i in range(n)]
        dc_and_noise = [10.0 + 2.0 * math.sin(2 * math.pi * 120.0 * ti) for ti in t]

        filtered = detector.bandpass_filter(dc_and_noise)
        assert len(filtered) == n
        # Filtered output should remove steady DC offset (+10.0 mV -> ~0.0 mV)
        steady_state = filtered[256:-256]
        mean_filtered = sum(steady_state) / len(steady_state)
        assert abs(mean_filtered) < 1.0

    def test_5point_derivative_filter_slope_amplification(self):
        """Verifies 5-point central derivative operator slope response."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        # Linear ramp with slope 100 mV/s: x[n] = 100 * (n / 512)
        ramp = [100.0 * (i / 512.0) for i in range(20)]
        deriv = detector.derivative_filter(ramp)
        # For linear ramp with slope S, central derivative returns S
        for d in deriv[3:-3]:
            assert abs(d - 100.0) < 1.0

    def test_squaring_transform_non_negativity(self):
        """Verifies that squaring transform enforces strict non-negativity and non-linear gain."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        inputs = [-50.0, -10.0, 0.0, 10.0, 50.0]
        squared = detector.squaring_transform(inputs)
        assert squared == [2500.0, 100.0, 0.0, 100.0, 2500.0]

    def test_moving_window_integration_window_duration(self):
        """Verifies that MWI produces smooth energy envelope with 150ms width."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        # Single unit impulse at index 100
        impulse = [0.0] * 300
        impulse[100] = 76.0
        mwi = detector.moving_window_integration(impulse)
        assert len(mwi) == 300
        # MWI should spread energy across 76 samples
        assert mwi[100] == 1.0
        assert mwi[175] == 1.0
        assert mwi[176] == 0.0

    def test_qrs_detection_synthetic_multibeat_512hz(self):
        """Tests full Pan-Tompkins QRS peak detection on 512Hz multi-beat signal."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        fs = 512
        total_seconds = 5
        signal = [0.0] * (fs * total_seconds)

        # Inject R-peaks at exactly 1.0s, 2.0s, 3.0s, 4.0s (60 BPM, RR = 1000.0 ms)
        for t_beat in [1.0, 2.0, 3.0, 4.0]:
            idx = int(t_beat * fs)
            signal[idx - 2] = 0.5
            signal[idx - 1] = 2.0
            signal[idx] = 4.5  # R-peak apex
            signal[idx + 1] = -1.2
            signal[idx + 2] = -0.4

        peaks, rrs = detector.detect_qrs_peaks(signal)
        assert len(peaks) == 4
        assert len(rrs) == 3

        # Peak sample locations should match timestamps within ~5 samples (<10ms)
        for expected_t, detected_idx in zip([1.0, 2.0, 3.0, 4.0], peaks):
            detected_t = detected_idx / float(fs)
            assert abs(detected_t - expected_t) < 0.02

        # RR intervals should be exactly 1000.0 ms
        for rr in rrs:
            assert abs(rr - 1000.0) < 5.0

    def test_qrs_empty_and_short_signal_handling(self):
        """Ensures QRS detector returns empty lists on empty or sub-0.5s signals."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        assert detector.detect_qrs_peaks([]) == ([], [])
        assert detector.detect_qrs_peaks([0.0] * 100) == ([], [])


# ============================================================================
# 2. KAMATH 2004 20% CLINICAL RR ARTIFACT FILTER
# ============================================================================

class TestKamath2004ClinicalRRFilter:
    """Clinical validation of Kamath et al. (2004) 20% RR Artifact Filter."""

    def test_kamath_dense_alternating_ectopic_bursts(self):
        """Verifies rejection of alternating ectopic bursts while preserving baseline."""
        raw_rrs = [800.0, 1600.0, 350.0, 1700.0, 380.0, 805.0, 795.0, 810.0]
        cleaned_interpolated, count = apply_kamath_artifact_filter(raw_rrs)
        assert count == 4
        assert len(cleaned_interpolated) == len(raw_rrs)
        assert cleaned_interpolated[0] == 800.0
        assert cleaned_interpolated[-1] == 810.0

        # Test filter alias (pure valid beats)
        cleaned_list = apply_kamath_filter(raw_rrs)
        assert len(cleaned_list) == len(raw_rrs)

    def test_kamath_pvc_with_compensatory_pause(self):
        """Verifies Premature Ventricular Contraction rejection (short beat + long pause)."""
        raw_rrs = [800.0, 805.0, 450.0, 1150.0, 802.0, 798.0]
        cleaned, count = apply_kamath_artifact_filter(raw_rrs)
        assert count == 2  # 450 and 1150 are ectopic
        assert cleaned[0] == 800.0
        assert cleaned[1] == 805.0
        assert cleaned[-1] == 798.0

    def test_kamath_preserves_respiratory_sinus_arrhythmia(self):
        """Verifies that 10-15% physiological RSA swings are 100% preserved without rejection."""
        # 12 breaths/min RSA oscillation (+-8% around 800ms)
        rsa_series = [round(800.0 + 64.0 * math.sin(i * 0.35), 1) for i in range(30)]
        cleaned, count = apply_kamath_artifact_filter(rsa_series)
        assert count == 0
        assert cleaned == rsa_series

    def test_kamath_empty_and_single_element_buffers(self):
        """Verifies behavior for empty or 1-element buffers."""
        assert apply_kamath_artifact_filter([]) == ([], 0)
        assert apply_kamath_artifact_filter([800.0]) == ([800.0], 0)
        assert apply_kamath_filter([]) == []
        assert apply_kamath_filter([800.0]) == [800.0]


# ============================================================================
# 3. RMSSD MATHEMATICAL PRECISION
# ============================================================================

class TestRMSSDPrecision:
    """Mathematical precision and boundary verification for RMSSD."""

    def test_rmssd_exact_analytical_derivation(self):
        """Asserts exact match with manual algebraic derivation."""
        # RR: [750, 780, 760, 810, 770]
        # diffs: [+30, -20, +50, -40]
        # diffs^2: [900, 400, 2500, 1600] -> sum = 5400
        # mean sq diff = 5400 / 4 = 1350.0
        # rmssd = sqrt(1350.0) = 36.7423... -> 36.74 ms
        rrs = [750.0, 780.0, 760.0, 810.0, 770.0]
        expected = round(math.sqrt((900 + 400 + 2500 + 1600) / 4.0), 2)
        assert expected == 36.74
        assert calculate_rmssd(rrs) == expected

    def test_rmssd_insufficient_samples(self):
        """Ensures RMSSD returns None when fewer than 2 beats are available."""
        assert calculate_rmssd([]) is None
        assert calculate_rmssd([800.0]) is None

    def test_rmssd_identical_beats_zero_variance(self):
        """Verifies RMSSD is 0.0 for identical intervals."""
        assert calculate_rmssd([800.0, 800.0, 800.0, 800.0]) == 0.0


# ============================================================================
# 4. DFA-ALPHA1 AEROBIC & ANAEROBIC THRESHOLDS
# ============================================================================

class TestDFAAlpha1AerobicThresholds:
    """Verification of 120s rolling Detrended Fluctuation Analysis (DFA-alpha1)."""

    def test_dfa_alpha1_short_window_invariance(self):
        """Verifies DFA-alpha1 returns None for N < 4 and estimates for N >= 4."""
        assert calculate_dfa_alpha1([]) is None
        assert calculate_dfa_alpha1([800.0]) is None
        assert calculate_dfa_alpha1([800.0, 810.0, 805.0]) is None

        # 4 <= N <= 20
        for n in [4, 8, 16, 20]:
            rrs = [800.0 + 15.0 * math.sin(i * 0.4) for i in range(n)]
            alpha = calculate_dfa_alpha1(rrs)
            assert alpha is not None
            assert 0.40 <= alpha <= 1.50

    def test_dfa_alpha1_zone2_boundary_mapping(self):
        """Verifies DFA-alpha1 Zone 2 (>=0.75), Zone 3 (0.50-0.75), and Zone 4/5 (<0.50)."""
        z2_desc, z2_color = classify_zone2_alignment(0.82)
        assert "Zone 2" in z2_desc
        assert z2_color == "#10b981"

        z3_desc, z3_color = classify_zone2_alignment(0.65)
        assert "Zone 3" in z3_desc
        assert z3_color == "#f59e0b"

        z4_desc, z4_color = classify_zone2_alignment(0.44)
        assert "Zone 4/5" in z4_desc
        assert z4_color == "#ef4444"

        none_desc, none_color = classify_zone2_alignment(None)
        assert "Awaiting" in none_desc
        assert none_color == "#94a3b8"


# ============================================================================
# 5. PULSE TRANSIT TIME (PTT) CONTINUOUS BLOOD PRESSURE INVERSION
# ============================================================================

class TestHemodynamicPTTBloodPressure:
    """Verification of continuous cuffless blood pressure inversion from PTT & HR."""

    def test_ptt_bp_empirical_equations_nominal(self):
        """Verifies SBP, DBP, MAP at baseline (PTT=200ms, HR=70 BPM)."""
        sbp, dbp, map_val = calculate_hemodynamics_bp(ptt_ms=200.0, hr_bpm=70.0)
        # SBP = 120 + 0 + 0 = 120.0
        # DBP = 80 + 0 + 0 = 80.0
        # MAP = (120 + 160) / 3 = 93.3
        assert sbp == 120.0
        assert dbp == 80.0
        assert map_val == 93.3

    def test_ptt_bp_empirical_equations_exercise(self):
        """Verifies SBP, DBP, MAP during high intensity exercise (PTT=160ms, HR=150 BPM)."""
        # delta_ptt = 40.0 -> SBP_ptt = 40 * 0.45 = 18.0, DBP_ptt = 40 * 0.25 = 10.0
        # hr_adj = (150 - 70) * 0.15 = 12.0
        # SBP = 120 + 18.0 + 12.0 = 150.0
        # DBP = 80 + 10.0 + 6.0 = 96.0
        # MAP = (150 + 192) / 3 = 114.0
        sbp, dbp, map_val = calculate_hemodynamics_bp(ptt_ms=160.0, hr_bpm=150.0)
        assert sbp == 150.0
        assert dbp == 96.0
        assert map_val == 114.0

    def test_ptt_bp_invalid_inputs_return_none(self):
        """Ensures missing, zero, or negative PTT returns strictly (None, None, None)."""
        assert calculate_hemodynamics_bp(ptt_ms=None, hr_bpm=70.0) == (None, None, None)
        assert calculate_hemodynamics_bp(ptt_ms=0.0, hr_bpm=70.0) == (None, None, None)
        assert calculate_hemodynamics_bp(ptt_ms=-180.0, hr_bpm=70.0) == (None, None, None)

    def test_movesense_readiness_suite_ptt_bp_method(self):
        """Verifies PTT BP calculation in MovesenseReadinessSuite."""
        suite = MovesenseReadinessSuite(user_age=30, hr_rest_baseline=58.0)
        # Direct PTT provided
        res_direct = suite.compute_ptt_blood_pressure(hr_bpm=70.0, rmssd_ms=45.0, ptt_ms=200.0)
        assert res_direct["status"] == "NOMINAL"
        assert res_direct["systolic_bp_mmhg"] == 120.0
        assert res_direct["diastolic_bp_mmhg"] == 80.0
        assert res_direct["mean_arterial_pressure_mmhg"] == 93.3

        # Disconnected state
        res_null = suite.compute_ptt_blood_pressure(hr_bpm=None, rmssd_ms=None)
        assert res_null["status"] == "STANDBY"
        assert res_null["systolic_bp_mmhg"] is None
        assert res_null["diastolic_bp_mmhg"] is None
        assert res_null["estimated_ptt_ms"] is None


# ============================================================================
# 6. OVERNIGHT PPG SLEEP STAGING & RECOVERY SCORE
# ============================================================================

class TestOvernightPPGSleepStaging:
    """Validation of overnight sleep staging, nocturnal dipping, and recovery scoring."""

    def test_sleep_epoch_classification_rules(self):
        """Verifies 30s epoch staging: AWAKE, DEEP, REM, LIGHT."""
        suite = MovesenseReadinessSuite(user_age=30, hr_rest_baseline=58.0)

        # High motion -> AWAKE
        assert suite.classify_sleep_epoch(hr_bpm=60.0, rmssd_ms=50.0, motion_g=0.25) == "AWAKE"

        # Low HR (<1.08*58 = 62.6) & High RMSSD (>=45) -> DEEP
        assert suite.classify_sleep_epoch(hr_bpm=54.0, rmssd_ms=65.0, motion_g=0.01) == "DEEP"

        # Low RMSSD (<30) & Elevated HR (>1.05*58 = 60.9) -> REM
        assert suite.classify_sleep_epoch(hr_bpm=64.0, rmssd_ms=22.0, motion_g=0.02) == "REM"

        # Baseline -> LIGHT
        assert suite.classify_sleep_epoch(hr_bpm=59.0, rmssd_ms=38.0, motion_g=0.02) == "LIGHT"

    def test_overnight_hypnogram_epoch_sequence_analysis(self):
        """Verifies overnight hypnogram analysis over epoch sequence."""
        suite = MovesenseReadinessSuite(user_age=30, hr_rest_baseline=58.0)
        # 100 epochs: 25 DEEP (25%), 20 REM (20%), 50 LIGHT (50%), 5 AWAKE (5%)
        epochs = ["DEEP"] * 25 + ["REM"] * 20 + ["LIGHT"] * 50 + ["AWAKE"] * 5
        analysis = suite.compute_overnight_sleep_analysis(
            hr_bpm=52.0,
            rmssd_ms=58.0,
            epoch_stages=epochs,
            daytime_hr_rest=65.0
        )

        assert analysis["status"] == "COMPLETED"
        assert analysis["sleep_stages_estimate"]["deep_sleep_pct"] == 25.0
        assert analysis["sleep_stages_estimate"]["rem_sleep_pct"] == 20.0
        assert analysis["sleep_stages_estimate"]["light_sleep_pct"] == 50.0
        assert analysis["sleep_stages_estimate"]["awake_pct"] == 5.0
        # Nocturnal dipping: (65 - 52) / 65 * 100 = 20.0%
        assert analysis["nocturnal_dip_pct"] == 20.0
        assert analysis["sleep_score_pct"] >= 80
        assert "EXCELLENT" in analysis["recovery_status"]

    def test_overnight_sleep_analysis_disconnected_null_state(self):
        """Ensures compute_overnight_sleep_analysis returns WAITING_FOR_SENSOR when inputs are missing."""
        suite = MovesenseReadinessSuite()
        res = suite.compute_overnight_sleep_analysis(hr_bpm=None, rmssd_ms=None)
        assert res["status"] == "WAITING_FOR_SENSOR"
        assert res["sleep_score_pct"] is None
        assert res["sleep_stages_estimate"] is None
        assert res["nocturnal_rmssd_ms"] is None


# ============================================================================
# 7. AUTO WORKOUT DETECTION & CARDIORESPIRATORY THRESHOLDS
# ============================================================================

class TestAutoWorkoutAndCardiorespiratoryThresholds:
    """Validation of real-time workout auto-detection, LT1, LT2, and VO2max."""

    def test_workout_state_transitions_across_hr_zones(self):
        """Verifies activity classification from Rest through Zone 5 Maximal Grappling."""
        suite = MovesenseReadinessSuite(user_age=30)  # HR max = 190

        # Rest (< 55% = < 104.5 BPM)
        rest = suite.classify_workout_state(hr_bpm=65.0)
        assert rest["current_activity"] == "RESTING"
        assert "Rest" in rest["training_zone"]

        # Zone 2 (55% - 72% = 104.5 - 136.8 BPM)
        z2 = suite.classify_workout_state(hr_bpm=125.0)
        assert z2["current_activity"] == "STEADY_CARDIO_ZONE_2"
        assert "Zone 2" in z2["training_zone"]

        # Zone 3 (72% - 85% = 136.8 - 161.5 BPM)
        z3 = suite.classify_workout_state(hr_bpm=150.0)
        assert z3["current_activity"] == "TEMPO_TRAINING"
        assert "Zone 3" in z3["training_zone"]

        # Zone 4 (85% - 92% = 161.5 - 174.8 BPM)
        z4 = suite.classify_workout_state(hr_bpm=168.0)
        assert z4["current_activity"] == "HIIT_INTERVALS"
        assert "Zone 4" in z4["training_zone"]

        # Zone 5 (>= 92% = >= 174.8 BPM)
        z5 = suite.classify_workout_state(hr_bpm=182.0)
        assert z5["current_activity"] == "MAXIMAL_EFFORT_GRAPPLING"
        assert "Zone 5" in z5["training_zone"]

        # Disconnected state
        z_null = suite.classify_workout_state(hr_bpm=None)
        assert z_null["status"] == "WAITING_FOR_SENSOR"
        assert z_null["current_activity"] is None

    def test_cardiorespiratory_thresholds_lt1_lt2_vo2max(self):
        """Verifies LT1 (0.75), LT2 (0.50), and Uth-Sørensen VO2max equation."""
        suite = MovesenseReadinessSuite(user_age=30, hr_rest_baseline=58.0)
        # VO2max = 15.3 * (190 / 58) = 15.3 * 3.27586 = 50.1 mL/kg/min
        # LT1 HR = 58 + 0.60 * (190 - 58) = 58 + 0.60 * 132 = 58 + 79.2 = 137 BPM
        # LT2 HR = 58 + 0.85 * (190 - 58) = 58 + 0.85 * 132 = 58 + 112.2 = 170 BPM
        thresh = suite.compute_cardiorespiratory_thresholds(hr_bpm=135.0, dfa_alpha1=0.76)
        assert thresh["status"] == "ACTIVE"
        assert thresh["estimated_vo2max_ml_kg_min"] == 50.1
        assert thresh["lt1_aerobic_threshold_bpm"] == 137
        assert thresh["lt2_anaerobic_threshold_bpm"] == 170
        assert "At LT1" in thresh["physiological_domain"]

        # Above LT2 (severe acidosis)
        thresh_lt2 = suite.compute_cardiorespiratory_thresholds(hr_bpm=178.0, dfa_alpha1=0.42)
        assert "Above LT2" in thresh_lt2["physiological_domain"]

        # Disconnected state
        thresh_null = suite.compute_cardiorespiratory_thresholds(hr_bpm=None, dfa_alpha1=None)
        assert thresh_null["status"] == "WAITING_FOR_SENSOR"
        assert thresh_null["current_dfa_alpha1"] is None


# ============================================================================
# 8. STRICT RULE #0 ZERO-MOCK & INTERFACE CONTRACT VERIFICATION
# ============================================================================

class TestStrictRuleZeroMockAndInterfaceContract:
    """Forensic verification of zero-mock null states and interface contracts."""

    def test_pipeline_disconnected_emits_waiting_for_sensor(self):
        """Validates that MovesenseECGPipeline emits WAITING_FOR_SENSOR when no signal is present."""
        pipeline = MovesenseECGPipeline(sample_rate_hz=512)
        out = pipeline.process_raw_ecg_window([])

        assert out["status"] == "WAITING_FOR_SENSOR"
        assert out["connected"] is False
        assert out["heart_rate_bpm"] is None
        assert out["rr_intervals_ms"] == []
        assert out["clean_rr_intervals_ms"] == []
        assert out["rmssd_ms"] is None
        assert out["dfa_alpha1"] is None
        assert out["ptt_blood_pressure"]["status"] == "STANDBY"
        assert out["ptt_blood_pressure"]["systolic_mmhg"] is None
        assert out["rule_0_zero_mock"] is True

    def test_readiness_suite_interface_contract_disconnected(self):
        """Verifies that get_interface_contract_payload adheres to PROJECT.md schema in disconnected state."""
        suite = MovesenseReadinessSuite()
        payload = suite.get_interface_contract_payload(live_data={"connected": False})

        assert payload["status"] == "WAITING_FOR_SENSOR"
        assert payload["heart_rate_bpm"] is None
        assert payload["rmssd_ms"] is None
        assert payload["dfa_alpha1"] is None
        assert payload["ptt_blood_pressure"]["systolic_bp_mmhg"] is None
        assert payload["ptt_blood_pressure"]["diastolic_bp_mmhg"] is None
        assert payload["ptt_blood_pressure"]["map_mmhg"] is None
        assert payload["sleep_recovery"]["sleep_score_pct"] is None
        assert payload["cardiorespiratory"]["lt1_threshold_bpm"] is None
        assert payload["cardiorespiratory"]["vo2max_estimate"] is None

    def test_readiness_suite_interface_contract_streaming(self):
        """Verifies that get_interface_contract_payload adheres to PROJECT.md schema in streaming state."""
        suite = MovesenseReadinessSuite()
        live_mock = {
            "connected": True,
            "heart_rate_bpm": 135.0,
            "rmssd_ms": 38.5,
            "dfa_alpha1": 0.78,
            "device_id": "Movesense Medical Unit 1"
        }
        payload = suite.get_interface_contract_payload(live_data=live_mock)

        assert payload["status"] == "STREAMING"
        assert payload["heart_rate_bpm"] == 135.0
        assert payload["rmssd_ms"] == 38.5
        assert payload["dfa_alpha1"] == 0.78
        assert payload["ptt_blood_pressure"]["systolic_bp_mmhg"] is not None
        assert payload["ptt_blood_pressure"]["diastolic_bp_mmhg"] is not None
        assert payload["ptt_blood_pressure"]["map_mmhg"] is not None
        assert payload["sleep_recovery"]["sleep_score_pct"] is not None
        assert payload["cardiorespiratory"]["lt1_threshold_bpm"] == 137
        assert payload["cardiorespiratory"]["lt2_threshold_bpm"] == 170
        assert payload["cardiorespiratory"]["vo2max_estimate"] == 50.1
        assert payload["cardiorespiratory"]["activity_state"] == "STEADY_CARDIO_ZONE_2"


# ============================================================================
# 9. END-TO-END PIPELINE INTEGRATION
# ============================================================================

class TestMovesensePipelineEndToEndIntegration:
    """End-to-end integration of raw 512Hz ECG stream into readiness and interface contracts."""

    def test_full_pipeline_raw_ecg_to_readiness_contract(self):
        """Tests complete pipeline: raw ECG -> QRS -> Kamath -> RMSSD -> PTT BP -> Readiness Report."""
        pipeline = MovesenseECGPipeline(sample_rate_hz=512)
        fs = 512
        # 4 seconds of ECG at 75 BPM (RR = 800ms)
        signal = [0.0] * (fs * 4)
        for t_beat in [0.8, 1.6, 2.4, 3.2]:
            idx = int(t_beat * fs)
            signal[idx - 2] = 0.5
            signal[idx - 1] = 2.5
            signal[idx] = 4.0
            signal[idx + 1] = -1.5
            signal[idx + 2] = -0.5

        dsp_out = pipeline.process_raw_ecg_window(signal, ptt_ms=190.0, device_id="Movesense Bicep 512Hz")
        assert dsp_out["status"] == "ACTIVE_STREAMING"
        assert dsp_out["connected"] is True
        assert dsp_out["heart_rate_bpm"] is not None
        assert abs(dsp_out["heart_rate_bpm"] - 75.0) < 5.0
        assert dsp_out["ptt_blood_pressure"]["status"] == "NOMINAL"

        # Pass DSP results to Readiness Suite
        suite = MovesenseReadinessSuite(user_age=30, hr_rest_baseline=58.0)
        contract = suite.get_interface_contract_payload(live_data={
            "connected": True,
            "heart_rate_bpm": dsp_out["heart_rate_bpm"],
            "rmssd_ms": dsp_out["rmssd_ms"] or 40.0,
            "dfa_alpha1": dsp_out["dfa_alpha1"] or 0.85,
            "device_id": dsp_out["device_id"]
        })

        assert contract["status"] == "STREAMING"
        assert contract["heart_rate_bpm"] == dsp_out["heart_rate_bpm"]
        assert contract["ptt_blood_pressure"]["systolic_bp_mmhg"] is not None
        assert contract["cardiorespiratory"]["vo2max_estimate"] == 50.1


if __name__ == "__main__":
    pytest.main(["-v", __file__])
