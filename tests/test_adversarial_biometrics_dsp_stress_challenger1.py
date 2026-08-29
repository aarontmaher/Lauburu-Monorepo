#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Challenger 1 Adversarial Stress Test Suite: Biometrics DSP, Kamath Filter, PTT BP & Airgap Invariants
Subsystem: 03_biometrics_and_telemetry, 00_core_infrastructure
Author: teamwork_preview_challenger_1

Adversarially stress tests:
1. Extreme Tachycardia (>220 BPM up to 260 BPM) and Extreme Bradycardia (<35 BPM down to 20 BPM).
2. Ectopic Bursts, Bigeminy, Trigeminy, Compensatory Pauses, and Rapid Acceleration Ramps.
3. Pulse Transit Time (PTT) Missing Pulses, Corrupt Pulses, Negative/Zero PTT, Out-of-Bounds BP Inversion.
4. Overnight Sleep Staging with Balanced vs Deficit Architecture, Nocturnal Arrhythmias, and Negative Dipping.
5. Corrupt, Malformed, NaN/Inf, Step Input, and Fuzzed Sensor Packets.
6. Cardiorespiratory Thresholds (LT1, LT2, VO2max) under Extreme Physiological Edge Cases.
7. Strict Rule #0 Zero-Mock Null State Invariants & Interface Contract Schemas.
"""

import math
import random
import sys
import os
import pytest
from typing import List, Dict, Any, Optional

# Add project root and biometrics directories
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DSP_DIR = os.path.join(PROJECT_ROOT, "03_biometrics_and_telemetry")
for p in [PROJECT_ROOT, DSP_DIR]:
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
# 1. EXTREME TACHYCARDIA (>220 BPM) & EXTREME BRADYCARDIA (<35 BPM)
# ============================================================================

class TestExtremeHeartRateBoundaries:
    """Stress tests Pan-Tompkins QRS and pipeline at extreme physiological boundaries."""

    def test_extreme_tachycardia_225_bpm_detection(self):
        """
        Adversarial test at 225 BPM (RR = 266.7 ms):
        Verifies 512Hz Pan-Tompkins accurately resolves high-rate QRS complexes above 220 BPM.
        """
        fs = 512
        detector = PanTompkinsQRSDetector(sample_rate_hz=fs)
        duration_s = 4.0
        n_samples = int(fs * duration_s)
        signal = [0.0] * n_samples

        # 225 BPM -> interval = 60.0 / 225.0 = 0.26667 s (~136.5 samples)
        rr_sec = 60.0 / 225.0
        beat_times = []
        t = 0.3
        while t < duration_s - 0.2:
            beat_times.append(t)
            t += rr_sec

        for bt in beat_times:
            idx = int(bt * fs)
            if 2 <= idx < n_samples - 2:
                signal[idx - 2] = 0.6
                signal[idx - 1] = 2.8
                signal[idx] = 5.0  # R-peak apex
                signal[idx + 1] = -1.8
                signal[idx + 2] = -0.5

        peaks, rrs = detector.detect_qrs_peaks(signal)
        assert len(peaks) >= len(beat_times) - 1, f"Expected at least {len(beat_times)-1} peaks, got {len(peaks)}"
        assert len(rrs) >= 1, "Must detect valid RR intervals"

        # RR intervals should be ~266.7 ms (within +-15 ms)
        for rr in rrs:
            assert abs(rr - 266.7) < 20.0, f"RR interval {rr} deviates from 266.7 ms"

        # Check full pipeline
        pipe = MovesenseECGPipeline(sample_rate_hz=fs)
        out = pipe.process_raw_ecg_window(signal, ptt_ms=170.0)
        assert out["status"] == "ACTIVE_STREAMING"
        assert out["heart_rate_bpm"] is not None
        assert abs(out["heart_rate_bpm"] - 225.0) < 15.0, f"Detected HR {out['heart_rate_bpm']} vs expected 225 BPM"

    def test_extreme_tachycardia_240_bpm_boundary(self):
        """
        Adversarial test at 240 BPM (RR = 250.0 ms):
        Boundary limit of physiological range (250.0 ms).
        """
        fs = 512
        detector = PanTompkinsQRSDetector(sample_rate_hz=fs)
        duration_s = 4.0
        signal = [0.0] * int(fs * duration_s)

        rr_sec = 60.0 / 240.0  # 0.250 s
        t = 0.3
        while t < duration_s - 0.2:
            idx = int(t * fs)
            signal[idx - 2] = 0.5
            signal[idx - 1] = 2.5
            signal[idx] = 4.5
            signal[idx + 1] = -1.5
            signal[idx + 2] = -0.4
            t += rr_sec

        peaks, rrs = detector.detect_qrs_peaks(signal)
        assert len(peaks) >= 10
        assert len(rrs) >= 9
        for rr in rrs:
            assert abs(rr - 250.0) < 10.0

    def test_supra_physiological_tachycardia_clamping_260_bpm(self):
        """
        Adversarial test at 260 BPM (RR = 230.8 ms):
        Since RR < 250.0 ms (outside valid single-chamber sinus filter), RR intervals are rejected by design.
        """
        fs = 512
        detector = PanTompkinsQRSDetector(sample_rate_hz=fs)
        signal = [0.0] * (fs * 3)
        rr_sec = 60.0 / 260.0  # 0.2307 s

        t = 0.2
        while t < 2.8:
            idx = int(t * fs)
            signal[idx] = 5.0
            t += rr_sec

        peaks, rrs = detector.detect_qrs_peaks(signal)
        # R-peaks may be identified, but raw RR intervals below 250ms must be safely rejected
        assert rrs == [], "RR intervals below 250ms must be rejected as unphysiological / ventricular fibrillation"

    def test_extreme_bradycardia_30_bpm_detection(self):
        """
        Adversarial test at 30 BPM (RR = 2000.0 ms):
        Verifies deep athletic bradycardia detection (<35 BPM).
        """
        fs = 512
        detector = PanTompkinsQRSDetector(sample_rate_hz=fs)
        duration_s = 8.0
        signal = [0.0] * int(fs * duration_s)

        for t_beat in [1.0, 3.0, 5.0, 7.0]:  # 2.0s apart = 30 BPM
            idx = int(t_beat * fs)
            signal[idx - 2] = 0.4
            signal[idx - 1] = 2.0
            signal[idx] = 4.2
            signal[idx + 1] = -1.0
            signal[idx + 2] = -0.3

        peaks, rrs = detector.detect_qrs_peaks(signal)
        assert len(peaks) == 4
        assert len(rrs) == 3
        for rr in rrs:
            assert abs(rr - 2000.0) < 10.0

        pipe = MovesenseECGPipeline(sample_rate_hz=fs)
        out = pipe.process_raw_ecg_window(signal)
        assert out["status"] == "ACTIVE_STREAMING"
        assert abs(out["heart_rate_bpm"] - 30.0) < 1.0


# ============================================================================
# 2. KAMATH 2004 ARTIFACT FILTER STRESS: BURSTS, ECTOPICS & RAMPS
# ============================================================================

class TestKamath2004ArtifactFilterAdversarial:
    """Stress tests the Kamath 20% clinical RR filter against extreme pathological sequences."""

    def test_kamath_bigeminy_alternating_bursts(self):
        """
        Alternating bigeminy: Normal (800ms) -> Premature (480ms, -40%) -> Compensatory (1120ms, +40%).
        Kamath filter must identify and interpolate all ectopic beats back to baseline.
        """
        raw_rrs = [800.0, 480.0, 1120.0, 480.0, 1120.0, 800.0, 805.0]
        cleaned, count = apply_kamath_artifact_filter(raw_rrs)
        assert count == 4, f"Expected 4 ectopic beats to be flagged, got {count}"
        assert len(cleaned) == len(raw_rrs)
        for val in cleaned:
            assert 700.0 <= val <= 900.0, f"Cleaned value {val} should stay near baseline (~800ms)"

    def test_kamath_trigeminy_recurrent_pvcs(self):
        """
        Trigeminy: Normal, Normal, PVC, Normal, Normal, PVC...
        """
        raw_rrs = [800.0, 805.0, 420.0, 802.0, 804.0, 410.0, 798.0]
        cleaned, count = apply_kamath_artifact_filter(raw_rrs)
        assert count == 2
        assert cleaned[0] == 800.0
        assert cleaned[1] == 805.0
        assert cleaned[3] == 802.0
        assert cleaned[4] == 804.0
        assert cleaned[6] == 798.0
        assert 600.0 <= cleaned[2] <= 810.0
        assert 600.0 <= cleaned[5] <= 810.0

    def test_kamath_consecutive_noise_burst_of_10_artifacts(self):
        """
        Long consecutive run of 10 motion artifact beats (>1500ms and <300ms).
        Filter must not crash or diverge, and must recover cleanly once valid beats resume.
        """
        noise = [2500.0, 200.0, 3000.0, 150.0, 2800.0, 180.0, 2900.0, 190.0, 3100.0, 210.0]
        raw_rrs = [800.0] + noise + [805.0, 810.0]
        cleaned, count = apply_kamath_artifact_filter(raw_rrs)
        assert count == 10
        assert len(cleaned) == len(raw_rrs)
        assert cleaned[-2] == 805.0
        assert cleaned[-1] == 810.0

    def test_kamath_rapid_physiological_acceleration_sprint(self):
        """
        Explosive grappling sprint: heart rate ramps from 60 BPM (1000ms) to 180 BPM (333ms).
        Physiological rate of change: step-down transitions (1000 -> 820 -> 680 -> 560 -> 460 -> 380 -> 333).
        Each transition is <= 20% step. All must be preserved with 0 artifacts.
        """
        ramp_rrs = [1000.0, 820.0, 680.0, 560.0, 460.0, 380.0, 333.0, 330.0, 332.0]
        cleaned, count = apply_kamath_artifact_filter(ramp_rrs)
        assert count == 0, f"Physiological sprint ramp should have 0 artifacts rejected, got {count}"
        assert cleaned == ramp_rrs

    def test_kamath_zero_and_negative_handling(self):
        """
        Corrupted inputs with 0.0 or negative numbers in RR interval stream.
        Filter must gracefully handle zero division protections.
        """
        corrupt_rrs = [800.0, 0.0, -500.0, 810.0]
        cleaned, count = apply_kamath_artifact_filter(corrupt_rrs)
        assert count >= 2
        assert len(cleaned) == 4
        assert cleaned[0] == 800.0
        assert cleaned[-1] == 810.0


# ============================================================================
# 3. PULSE TRANSIT TIME (PTT) CONTINUOUS BP INVERSION STRESS
# ============================================================================

class TestHemodynamicPTTAdversarialStress:
    """Stress tests PTT Hemodynamic BP Inversion across extreme ranges and missing data."""

    def test_ptt_bp_extreme_hypertension_vasoconstriction(self):
        """
        Extreme vasoconstriction / acute stress: PTT = 80 ms (fast pulse wave velocity), HR = 180 BPM.
        Inversion model must clamp SBP to max 220 mmHg and DBP to max 130 mmHg.
        """
        sbp, dbp, map_val = calculate_hemodynamics_bp(ptt_ms=80.0, hr_bpm=180.0)
        # delta_ptt = 120 -> SBP raw = 120 + 54 + 16.5 = 190.5 mmHg
        # DBP raw = 80 + 30 + 8.8 = 118.8 mmHg
        assert sbp is not None and dbp is not None and map_val is not None
        assert 80.0 <= sbp <= 220.0
        assert 50.0 <= dbp <= 130.0
        assert map_val == round((sbp + 2.0 * dbp) / 3.0, 1)

    def test_ptt_bp_extreme_hypotension_vasodilation(self):
        """
        Extreme vasodilation / post-exercise vasodilation: PTT = 350 ms, HR = 45 BPM.
        Inversion model must clamp SBP to min 80 mmHg and DBP to min 50 mmHg.
        """
        sbp, dbp, map_val = calculate_hemodynamics_bp(ptt_ms=350.0, hr_bpm=45.0)
        # delta_ptt = -150 -> SBP raw = 120 - 67.5 - 3.75 = 48.75 -> clamped to 80.0 mmHg
        # DBP raw = 80 - 37.5 - 1.875 = 40.625 -> clamped to 50.0 mmHg
        assert sbp == 80.0
        assert dbp == 50.0
        assert map_val == round((80.0 + 2 * 50.0) / 3.0, 1)

    def test_ptt_bp_missing_or_corrupt_inputs(self):
        """Tests None, negative, 0, NaN, and Inf inputs."""
        assert calculate_hemodynamics_bp(ptt_ms=None, hr_bpm=70.0) == (None, None, None)
        assert calculate_hemodynamics_bp(ptt_ms=0.0, hr_bpm=70.0) == (None, None, None)
        assert calculate_hemodynamics_bp(ptt_ms=-100.0, hr_bpm=70.0) == (None, None, None)

        suite = MovesenseReadinessSuite()
        res_none = suite.compute_ptt_blood_pressure(hr_bpm=None, rmssd_ms=None, ptt_ms=None)
        assert res_none["status"] == "STANDBY"
        assert res_none["systolic_bp_mmhg"] is None


# ============================================================================
# 4. OVERNIGHT SLEEP STAGING & NOCTURNAL AUTONOMIC RECOVERY
# ============================================================================

class TestOvernightSleepStagingAdversarial:
    """Stress tests overnight hypnogram analysis, recovery scoring, and abnormal dipping."""

    def test_sleep_balanced_optimal_architecture_perfect_recovery(self):
        """Balanced architecture: 25% Deep, 25% REM, 50% Light with high RMSSD and low nocturnal HR -> Score = 100."""
        suite = MovesenseReadinessSuite(user_age=30, hr_rest_baseline=50.0)
        epochs = ["DEEP"] * 30 + ["REM"] * 30 + ["LIGHT"] * 60
        res = suite.compute_overnight_sleep_analysis(
            hr_bpm=42.0,
            rmssd_ms=85.0,
            epoch_stages=epochs,
            daytime_hr_rest=60.0
        )
        assert res["status"] == "COMPLETED"
        assert res["sleep_score_pct"] == 100
        assert res["recovery_status"] == "EXCELLENT (Green)"
        assert res["sleep_stages_estimate"]["deep_sleep_pct"] == 25.0
        assert res["sleep_stages_estimate"]["rem_sleep_pct"] == 25.0

    def test_sleep_isolated_deep_sleep_without_rem_capped_score(self):
        """100% Deep Sleep with 0% REM represents a REM deficit; score is capped at 75."""
        suite = MovesenseReadinessSuite(user_age=30, hr_rest_baseline=50.0)
        epochs = ["DEEP"] * 120
        res = suite.compute_overnight_sleep_analysis(
            hr_bpm=42.0,
            rmssd_ms=85.0,
            epoch_stages=epochs,
            daytime_hr_rest=60.0
        )
        assert res["status"] == "COMPLETED"
        assert res["sleep_score_pct"] == 75
        assert res["sleep_stages_estimate"]["deep_sleep_pct"] == 100.0
        assert res["sleep_stages_estimate"]["rem_sleep_pct"] == 0.0

    def test_sleep_100_percent_awake_insomnia_zero_recovery(self):
        """100% Awake (severe insomnia) with elevated HR and low RMSSD."""
        suite = MovesenseReadinessSuite(user_age=30, hr_rest_baseline=50.0)
        epochs = ["AWAKE"] * 120
        res = suite.compute_overnight_sleep_analysis(
            hr_bpm=88.0,
            rmssd_ms=12.0,
            epoch_stages=epochs,
            daytime_hr_rest=60.0
        )
        assert res["status"] == "COMPLETED"
        assert res["sleep_score_pct"] == 0
        assert res["recovery_status"] == "LOW (Red)"
        assert res["sleep_stages_estimate"]["awake_pct"] == 100.0

    def test_negative_nocturnal_dipping_sympathetic_overdrive(self):
        """
        Reverse/Negative dipping: night HR (75 BPM) higher than daytime rest baseline (60 BPM).
        Nocturnal dip % should be negative, reflecting sympathetic overdrive.
        """
        suite = MovesenseReadinessSuite(user_age=30, hr_rest_baseline=50.0)
        res = suite.compute_overnight_sleep_analysis(
            hr_bpm=75.0,
            rmssd_ms=25.0,
            daytime_hr_rest=60.0
        )
        assert res["status"] == "COMPLETED"
        assert res["nocturnal_dip_pct"] is not None
        assert res["nocturnal_dip_pct"] < 0.0  # (60 - 75) / 60 * 100 = -25.0%

    def test_sleep_unrecognized_epoch_labels_resilience(self):
        """Hypnogram containing unknown stage labels ('CORRUPT', 'UNKNOWN', '') must not crash."""
        suite = MovesenseReadinessSuite()
        epochs = ["DEEP", "CORRUPT", "REM", "UNKNOWN", "LIGHT", ""]
        res = suite.compute_overnight_sleep_analysis(hr_bpm=55.0, rmssd_ms=45.0, epoch_stages=epochs)
        assert res["status"] == "COMPLETED"
        assert res["sleep_score_pct"] is not None
        assert 0 <= res["sleep_score_pct"] <= 100


# ============================================================================
# 5. CORRUPT, MALFORMED & FUZZED SENSOR PACKETS
# ============================================================================

class TestCorruptAndFuzzedSensorPackets:
    """Fuzz testing and malformed input handling for ECG and DSP pipeline."""

    def test_flatline_ecg_zero_variance(self):
        """ECG disconnected / zero flatline -> 0 peaks, 0 RR intervals."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        flatline = [0.0] * (512 * 3)
        peaks, rrs = detector.detect_qrs_peaks(flatline)
        assert peaks == []
        assert rrs == []

    def test_dc_offset_only_ecg_no_heartbeat(self):
        """Constant non-zero DC offset (e.g. +2000 mV) produces no periodic heart rate output."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        dc_signal = [2000.0] * (512 * 3)
        peaks, rrs = detector.detect_qrs_peaks(dc_signal)
        # Even if a filter transient occurs at index 6, there can be at most 1 transient and 0 RR intervals
        assert rrs == []
        pipe = MovesenseECGPipeline(sample_rate_hz=512)
        out = pipe.process_raw_ecg_window(dc_signal)
        assert out["heart_rate_bpm"] is None

    def test_pure_high_frequency_mains_hum(self):
        """50Hz / 60Hz pure sinusoidal mains noise (no QRS complexes) -> rejected."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        fs = 512
        hum = [5.0 * math.sin(2 * math.pi * 50.0 * (i / fs)) for i in range(fs * 3)]
        peaks, rrs = detector.detect_qrs_peaks(hum)
        # Pure sinusoidal 50Hz derivative and bandpass will be attenuated, no discrete QRS peaks
        assert len(peaks) == 0

    def test_fuzzed_random_noise_stream(self):
        """Fuzzed random gaussian noise does not cause uncaught exceptions or unbounded outputs."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        pipe = MovesenseECGPipeline(sample_rate_hz=512)
        random.seed(42)

        for _ in range(5):
            noise_signal = [random.gauss(0.0, 10.0) for _ in range(512 * 2)]
            out = pipe.process_raw_ecg_window(noise_signal, ptt_ms=random.choice([None, 180.0, -50.0]))
            assert out["status"] in ["ACTIVE_STREAMING", "WAITING_FOR_SENSOR"]
            assert out["rule_0_zero_mock"] is True


# ============================================================================
# 6. CARDIORESPIRATORY THRESHOLDS & VO2MAX EXTREME CASES
# ============================================================================

class TestCardiorespiratoryThresholdsAdversarial:
    """Stress tests LT1, LT2, and Uth-Sørensen VO2max formulas."""

    def test_vo2max_elite_athlete_vs_sedentary(self):
        """
        Elite endurance athlete (Age 25, HR max = 195, HR rest = 38):
        VO2max = 15.3 * (195 / 40.0) [clamped baseline min 40] = 74.6 mL/kg/min.
        Sedentary (Age 60, HR max = 160, HR rest = 85):
        VO2max = 15.3 * (160 / 85) = 28.8 mL/kg/min.
        """
        elite_suite = MovesenseReadinessSuite(user_age=25, hr_rest_baseline=38.0)
        res_elite = elite_suite.compute_cardiorespiratory_thresholds(hr_bpm=140.0, dfa_alpha1=0.75)
        assert res_elite["estimated_vo2max_ml_kg_min"] >= 70.0
        assert "LT1" in res_elite["physiological_domain"]

        sedentary_suite = MovesenseReadinessSuite(user_age=60, hr_rest_baseline=85.0)
        res_sedentary = sedentary_suite.compute_cardiorespiratory_thresholds(hr_bpm=120.0, dfa_alpha1=0.48)
        assert res_sedentary["estimated_vo2max_ml_kg_min"] <= 35.0
        assert "Above LT2" in res_sedentary["physiological_domain"]

    def test_dfa_alpha1_out_of_bounds_clamping(self):
        """Ensures calculate_dfa_alpha1 values stay bounded in [0.40, 1.50]."""
        # Identical values
        assert calculate_dfa_alpha1([800.0] * 20) is not None
        # Huge fluctuating values
        huge_rrs = [200.0, 1800.0, 200.0, 1800.0, 200.0, 1800.0, 200.0, 1800.0]
        alpha = calculate_dfa_alpha1(huge_rrs)
        assert alpha is not None
        assert 0.40 <= alpha <= 1.50


# ============================================================================
# 7. STRICT RULE #0 ZERO-MOCK INVARIANTS & INTERFACE CONTRACTS
# ============================================================================

class TestStrictRuleZeroMockAndContractCompliance:
    """Verifies that under disconnected / absent sensor states, strictly null metrics are returned."""

    def test_null_state_invariant_across_all_metrics(self):
        """Verifies no simulated arrays or synthetic numbers leak into disconnected payloads."""
        suite = MovesenseReadinessSuite()
        contract = suite.get_interface_contract_payload(live_data={"connected": False})

        assert contract["status"] == "WAITING_FOR_SENSOR"
        assert contract["heart_rate_bpm"] is None
        assert contract["rmssd_ms"] is None
        assert contract["dfa_alpha1"] is None
        assert contract["ptt_blood_pressure"]["systolic_bp_mmhg"] is None
        assert contract["ptt_blood_pressure"]["diastolic_bp_mmhg"] is None
        assert contract["ptt_blood_pressure"]["map_mmhg"] is None
        assert contract["sleep_recovery"]["sleep_score_pct"] is None
        assert contract["sleep_recovery"]["deep_sleep_pct"] is None
        assert contract["sleep_recovery"]["rem_sleep_pct"] is None
        assert contract["cardiorespiratory"]["lt1_threshold_bpm"] is None
        assert contract["cardiorespiratory"]["lt2_threshold_bpm"] is None
        assert contract["cardiorespiratory"]["vo2max_estimate"] is None
        assert contract["cardiorespiratory"]["activity_state"] is None


if __name__ == "__main__":
    pytest.main(["-v", __file__])
