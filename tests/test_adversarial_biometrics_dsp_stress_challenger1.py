"""
================================================================================
ADVERSARIAL STRESS TEST SUITE — CHALLENGER 1
Milestone M1: Flagship Movesense Physiological Readiness Suite DSP Engine
================================================================================
Empirically stress-tests:
1. Pan-Tompkins QRS Detection (512Hz/128Hz, baseline wander, 220 BPM tachycardia, 35 BPM bradycardia, PVCs)
2. Kamath 20% RR Artifact Filter (Large spikes, bursts, initial beat corruption, RSA preservation)
3. Pulse Transit Time (PTT) Blood Pressure Inversion Bounds (50ms - 500ms, extreme HR, Rule #0 compliance)
4. Sleep Scoring (0-100 score invariance, stage distribution) and DFA-alpha1 boundary cases
================================================================================
"""

import math
import sys
import numpy as np
import pytest

sys.path.insert(0, "01_apps/biometrics")

from movesense_hub.dsp.pan_tompkins import (
    PanTompkinsQRSDetector,
    apply_kamath_artifact_filter,
    apply_kamath_filter,
    calculate_rmssd,
    calculate_dfa_alpha1,
    MovesenseECGPipeline,
)
from movesense_hub.dsp.hemodynamics_bp import (
    calculate_hemodynamics_bp,
    ContinuousPttBloodPressureModel,
    compute_ptt_blood_pressure,
)
from movesense_hub.dsp.sleep_scoring import (
    classify_sleep_epoch,
    SleepStagingEngine,
    compute_overnight_sleep_analysis,
)
from movesense_hub.dsp.zone2_coaching import (
    classify_zone2_alignment,
    classify_workout_state,
    compute_cardiorespiratory_thresholds,
    Zone2CoachingEngine,
)


def generate_synthetic_ecg(
    duration_sec: float = 10.0,
    sample_rate_hz: int = 512,
    bpm: float = 60.0,
    baseline_wander_hz: float = 0.0,
    baseline_wander_mv: float = 0.0,
    noise_mv: float = 0.0,
    powerline_hz: float = 0.0,
    powerline_mv: float = 0.0,
    pvc_indices: list = None,
) -> tuple[list[float], list[int]]:
    """
    Generates synthetic ECG signal with ground-truth R-peak sample indices.
    """
    total_samples = int(duration_sec * sample_rate_hz)
    rr_samples = int((60.0 / bpm) * sample_rate_hz)
    
    t = np.linspace(0, duration_sec, total_samples, endpoint=False)
    signal = np.zeros(total_samples)
    ground_truth_peaks = []
    
    cur_sample = int(0.5 * rr_samples)
    beat_count = 0
    pvc_set = set(pvc_indices or [])
    
    while cur_sample < total_samples - int(0.3 * sample_rate_hz):
        ground_truth_peaks.append(cur_sample)
        is_pvc = beat_count in pvc_set
        
        # P-wave
        p_offset = int(-0.16 * sample_rate_hz)
        p_width = int(0.04 * sample_rate_hz)
        p_amp = 0.15 if not is_pvc else 0.0
        
        # Q-wave
        q_offset = int(-0.04 * sample_rate_hz)
        q_width = int(0.015 * sample_rate_hz)
        q_amp = -0.15
        
        # R-peak
        r_offset = 0
        r_width = int(0.02 * sample_rate_hz) if not is_pvc else int(0.05 * sample_rate_hz)
        r_amp = 1.2 if not is_pvc else -1.5
        
        # S-wave
        s_offset = int(0.04 * sample_rate_hz)
        s_width = int(0.02 * sample_rate_hz)
        s_amp = -0.3 if not is_pvc else 0.4
        
        # T-wave
        t_offset = int(0.20 * sample_rate_hz)
        t_width = int(0.07 * sample_rate_hz)
        t_amp = 0.35 if not is_pvc else -0.5
        
        waves = [
            (p_offset, p_width, p_amp),
            (q_offset, q_width, q_amp),
            (r_offset, r_width, r_amp),
            (s_offset, s_width, s_amp),
            (t_offset, t_width, t_amp),
        ]
        
        for off, width, amp in waves:
            if width <= 0 or amp == 0.0:
                continue
            center = cur_sample + off
            idx_range = np.arange(max(0, center - 3 * width), min(total_samples, center + 3 * width + 1))
            if len(idx_range) > 0:
                signal[idx_range] += amp * np.exp(-0.5 * ((idx_range - center) / width) ** 2)
        
        beat_count += 1
        if is_pvc:
            cur_sample += int(rr_samples * 1.3)
        else:
            cur_sample += rr_samples

    if baseline_wander_mv > 0 and baseline_wander_hz > 0:
        signal += baseline_wander_mv * np.sin(2 * np.pi * baseline_wander_hz * t)
        
    if powerline_mv > 0 and powerline_hz > 0:
        signal += powerline_mv * np.sin(2 * np.pi * powerline_hz * t)
        
    if noise_mv > 0:
        np.random.seed(42)
        signal += np.random.normal(0, noise_mv, total_samples)
        
    return signal.tolist(), ground_truth_peaks


# ==============================================================================
# CHALLENGE 1: Pan-Tompkins QRS Detection
# ==============================================================================

class TestPanTompkinsAdversarial:
    
    @pytest.mark.parametrize("sample_rate_hz", [512, 128])
    def test_nominal_ecg_detection(self, sample_rate_hz):
        """Test clean nominal ECG at 60 BPM."""
        ecg, true_peaks = generate_synthetic_ecg(
            duration_sec=10.0, sample_rate_hz=sample_rate_hz, bpm=60.0
        )
        detector = PanTompkinsQRSDetector(sample_rate_hz=sample_rate_hz)
        detected_peaks, rr_intervals = detector.detect_qrs_peaks(ecg)
        
        assert len(detected_peaks) > 0
        assert abs(len(detected_peaks) - len(true_peaks)) <= 1
        for rr in rr_intervals:
            assert 950.0 <= rr <= 1050.0

    @pytest.mark.parametrize("sample_rate_hz", [128])
    def test_extreme_tachycardia_220_bpm_128hz(self, sample_rate_hz):
        """Test extreme tachycardia at 128Hz (220 BPM, RR ~ 272.7ms)."""
        ecg, true_peaks = generate_synthetic_ecg(
            duration_sec=10.0, sample_rate_hz=sample_rate_hz, bpm=220.0
        )
        detector = PanTompkinsQRSDetector(sample_rate_hz=sample_rate_hz)
        detected_peaks, rr_intervals = detector.detect_qrs_peaks(ecg)
        
        assert len(detected_peaks) >= len(true_peaks) - 2
        for rr in rr_intervals:
            assert 250.0 <= rr <= 320.0

    def test_empirical_mwi_accumulator_flaw_at_512hz(self):
        """
        VERIFICATION OF FIX #1:
        Moving Window Integrator double-accumulation fixed — 512Hz 220 BPM tachycardia correctly detected.
        """
        ecg, true_peaks = generate_synthetic_ecg(
            duration_sec=10.0, sample_rate_hz=512, bpm=220.0
        )
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        detected_peaks, rr_intervals = detector.detect_qrs_peaks(ecg)
        
        # 512Hz 220BPM tachycardia: genuine peaks are cleanly detected without false index-0 impulse suppression
        print(f"512Hz 220BPM: True={len(true_peaks)}, Detected={len(detected_peaks)}")
        assert len(detected_peaks) >= len(true_peaks) - 2
        for rr in rr_intervals:
            assert 250.0 <= rr <= 320.0

    @pytest.mark.parametrize("sample_rate_hz", [512, 128])
    def test_extreme_bradycardia_35_bpm(self, sample_rate_hz):
        """Test extreme bradycardia (35 BPM, RR ~ 1714.3ms)."""
        ecg, true_peaks = generate_synthetic_ecg(
            duration_sec=20.0, sample_rate_hz=sample_rate_hz, bpm=35.0
        )
        detector = PanTompkinsQRSDetector(sample_rate_hz=sample_rate_hz)
        detected_peaks, rr_intervals = detector.detect_qrs_peaks(ecg)
        
        assert len(detected_peaks) >= len(true_peaks) - 1
        for rr in rr_intervals:
            assert 1600.0 <= rr <= 1800.0

    @pytest.mark.parametrize("sample_rate_hz", [512, 128])
    def test_severe_baseline_wander(self, sample_rate_hz):
        """Test 2.0mV baseline wander at 0.25Hz (respiratory drift)."""
        ecg, true_peaks = generate_synthetic_ecg(
            duration_sec=10.0, sample_rate_hz=sample_rate_hz, bpm=72.0,
            baseline_wander_hz=0.25, baseline_wander_mv=2.0
        )
        detector = PanTompkinsQRSDetector(sample_rate_hz=sample_rate_hz)
        detected_peaks, rr_intervals = detector.detect_qrs_peaks(ecg)
        
        assert len(detected_peaks) >= len(true_peaks) - 2

    @pytest.mark.parametrize("sample_rate_hz", [512, 128])
    def test_noise_and_powerline_interference(self, sample_rate_hz):
        """Test with 50Hz powerline hum (0.3mV) + Gaussian EMG noise (0.15mV)."""
        ecg, true_peaks = generate_synthetic_ecg(
            duration_sec=10.0, sample_rate_hz=sample_rate_hz, bpm=70.0,
            powerline_hz=50.0, powerline_mv=0.3, noise_mv=0.15
        )
        detector = PanTompkinsQRSDetector(sample_rate_hz=sample_rate_hz)
        detected_peaks, rr_intervals = detector.detect_qrs_peaks(ecg)
        
        assert len(detected_peaks) >= len(true_peaks) - 2

    def test_ectopic_beats_pvc(self):
        """Test ECG containing premature ventricular contractions (PVCs)."""
        ecg, true_peaks = generate_synthetic_ecg(
            duration_sec=12.0, sample_rate_hz=512, bpm=65.0,
            pvc_indices=[3, 7]
        )
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        detected_peaks, rr_intervals = detector.detect_qrs_peaks(ecg)
        
        assert len(detected_peaks) > 0

    def test_empty_and_flatline_signals(self):
        """Test empty, zero, and single-value inputs for zero-mock compliance."""
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        
        # Empty
        p, rr = detector.detect_qrs_peaks([])
        assert p == [] and rr == []
        
        # Too short (< 0.5s)
        p, rr = detector.detect_qrs_peaks([1.0] * 100)
        assert p == [] and rr == []
        
        # Flatline (zero signal)
        p, rr = detector.detect_qrs_peaks([0.0] * 2000)
        assert p == [] and rr == []
        
        # Constant non-zero DC offset
        p, rr = detector.detect_qrs_peaks([1.5] * 2000)
        assert p == [] and rr == []


# ==============================================================================
# CHALLENGE 2: Kamath 20% RR Artifact Filter
# ==============================================================================

class TestKamathFilterAdversarial:
    
    def test_single_large_artifact_spike(self):
        """Single 5000ms artifact in normal 800ms stream."""
        rrs = [800.0, 800.0, 5000.0, 800.0, 800.0]
        cleaned, count = apply_kamath_artifact_filter(rrs)
        assert count == 1
        assert len(cleaned) == 5
        assert cleaned[2] == 800.0
        assert cleaned == [800.0, 800.0, 800.0, 800.0, 800.0]

    def test_multiple_consecutive_artifacts(self):
        """Burst of 3 consecutive artifact spikes."""
        rrs = [800.0, 2000.0, 2100.0, 2200.0, 800.0]
        cleaned, count = apply_kamath_artifact_filter(rrs)
        assert count == 3
        for val in cleaned:
            assert val == 800.0

    def test_initial_beat_corrupted_lockin_vulnerability(self):
        """
        VERIFICATION OF FIX #2:
        First beat corrupted outlier is properly rejected and anchored to physiological baseline.
        """
        rrs = [5000.0, 800.0, 805.0, 810.0, 800.0]
        cleaned, count = apply_kamath_artifact_filter(rrs)
        print("Initial beat corrupted output:", cleaned, "count:", count)
        assert len(cleaned) == 5
        # The initial 5000ms outlier is rejected (count = 1) and anchored to 800.0
        assert count == 1
        assert 790.0 <= cleaned[0] <= 810.0
        assert cleaned[1:] == [800.0, 805.0, 810.0, 800.0]

    def test_extreme_underflow_artifact(self):
        """Sudden false short RR (e.g. 50ms artifact)."""
        rrs = [850.0, 850.0, 50.0, 850.0, 850.0]
        cleaned, count = apply_kamath_artifact_filter(rrs)
        assert count == 1
        assert cleaned[2] == 850.0

    def test_physiological_respiratory_sinus_arrhythmia(self):
        """Normal RSA variation within 15%: should NOT be rejected."""
        rrs = [800.0, 880.0, 960.0, 890.0, 810.0, 750.0, 800.0]
        cleaned, count = apply_kamath_artifact_filter(rrs)
        assert count == 0
        assert cleaned == rrs

    def test_empty_and_single_element(self):
        """Edge cases: empty, 1-element, wrapper functions."""
        assert apply_kamath_artifact_filter([]) == ([], 0)
        assert apply_kamath_artifact_filter([800.0]) == ([800.0], 0)
        assert apply_kamath_filter([]) == []
        assert apply_kamath_filter([800.0]) == [800.0]


# ==============================================================================
# CHALLENGE 3: PTT Blood Pressure Bounds
# ==============================================================================

class TestPttBloodPressureAdversarial:
    
    @pytest.mark.parametrize("ptt_ms, hr_bpm", [
        (50.0, 60.0),    # Extremely short PTT (hypertensive/stiff)
        (50.0, 220.0),   # Extremely short PTT + extreme tachycardia
        (100.0, 70.0),   # Short PTT
        (200.0, 70.0),   # Baseline nominal
        (350.0, 60.0),   # Long PTT
        (500.0, 40.0),   # Extremely long PTT (vasodilated/delay)
        (500.0, 220.0),  # Extremely long PTT + extreme tachycardia
    ])
    def test_ptt_bp_ranges(self, ptt_ms, hr_bpm):
        """Ensure SBP, DBP, MAP remain within strict physiological boundaries."""
        sbp, dbp, map_val = calculate_hemodynamics_bp(ptt_ms, hr_bpm)
        assert sbp is not None
        assert dbp is not None
        assert map_val is not None
        
        assert 80.0 <= sbp <= 220.0, f"SBP {sbp} out of bounds for ptt={ptt_ms}, hr={hr_bpm}"
        assert 50.0 <= dbp <= 130.0, f"DBP {dbp} out of bounds for ptt={ptt_ms}, hr={hr_bpm}"
        assert sbp > dbp, f"SBP ({sbp}) must be greater than DBP ({dbp})"
        assert dbp <= map_val <= sbp, f"MAP ({map_val}) must be between DBP ({dbp}) and SBP ({sbp})"
        expected_map = round((sbp + 2.0 * dbp) / 3.0, 1)
        assert abs(map_val - expected_map) <= 0.1

    def test_ptt_bp_zero_mock_and_invalid_inputs(self):
        """Rule #0 compliance on missing or non-positive PTT or non-positive HR."""
        assert calculate_hemodynamics_bp(None, 70.0) == (None, None, None)
        assert calculate_hemodynamics_bp(0.0, 70.0) == (None, None, None)
        assert calculate_hemodynamics_bp(-100.0, 70.0) == (None, None, None)
        assert calculate_hemodynamics_bp(200.0, 0.0) == (None, None, None)
        assert calculate_hemodynamics_bp(200.0, -10.0) == (None, None, None)

    def test_continuous_model_dataclass_contract(self):
        """Test ContinuousPttBloodPressureModel full contract."""
        model = ContinuousPttBloodPressureModel(hr_rest_baseline=58.0)
        
        # Disconnected state
        res_disconnected = model.compute_ptt_blood_pressure(hr_bpm=None)
        assert res_disconnected.status == "STANDBY"
        assert res_disconnected.sbp_mmhg is None
        assert res_disconnected.dbp_mmhg is None

        # Non-positive HR (asystole / sensor drop) -> Rule #0 STANDBY
        res_zero_hr = model.compute_ptt_blood_pressure(hr_bpm=0.0, rmssd_ms=40.0)
        assert res_zero_hr.status == "STANDBY"
        assert res_zero_hr.sbp_mmhg is None
        assert res_zero_hr.dbp_mmhg is None

        res_neg_hr = model.compute_ptt_blood_pressure(hr_bpm=-15.0, rmssd_ms=40.0)
        assert res_neg_hr.status == "STANDBY"
        assert res_neg_hr.sbp_mmhg is None
        
        # Direct PTT mode
        res_direct = model.compute_ptt_blood_pressure(hr_bpm=72.0, ptt_ms=180.0)
        assert res_direct.status == "NOMINAL"
        assert 80.0 <= res_direct.sbp_mmhg <= 220.0
        assert 50.0 <= res_direct.dbp_mmhg <= 130.0
        assert res_direct.ptt_ms == 180.0

        # Hughes-Bramwell approximation fallback (ECG only)
        res_approx = model.compute_ptt_blood_pressure(hr_bpm=72.0, rmssd_ms=45.0, ptt_ms=None)
        assert res_approx.status == "NOMINAL"
        assert 90.0 <= res_approx.sbp_mmhg <= 185.0
        assert 55.0 <= res_approx.dbp_mmhg <= 115.0
        assert res_approx.ptt_ms is not None


# ==============================================================================
# CHALLENGE 4: Sleep Score (0-100) & DFA-alpha1 Boundaries
# ==============================================================================

class TestSleepScoreAndDfaAdversarial:
    
    @pytest.mark.parametrize("stages, hr, rmssd", [
        # 100% Deep sleep with high RMSSD and low HR -> should be near 100
        (["DEEP"] * 20, 45.0, 65.0),
        # 100% Awake with high HR and low RMSSD -> should be near 0
        (["AWAKE"] * 20, 95.0, 15.0),
        # 100% REM
        (["REM"] * 20, 65.0, 25.0),
        # 100% LIGHT
        (["LIGHT"] * 20, 58.0, 35.0),
        # Mixed physiological distribution
        (["LIGHT"] * 10 + ["DEEP"] * 5 + ["REM"] * 4 + ["AWAKE"] * 1, 55.0, 48.0),
    ])
    def test_sleep_score_0_to_100_invariance(self, stages, hr, rmssd):
        """Verify sleep score is strictly integer in [0, 100]."""
        engine = SleepStagingEngine(hr_rest_baseline=58.0)
        res = engine.compute_overnight_sleep_analysis(
            hr_bpm=hr, rmssd_ms=rmssd, epoch_stages=stages
        )
        assert res.status == "COMPLETED"
        assert res.sleep_score_100 is not None
        assert 0 <= res.sleep_score_100 <= 100
        assert isinstance(res.sleep_score_100, int)
        assert 0.0 <= res.deep_pct <= 100.0
        assert 0.0 <= res.rem_pct <= 100.0
        assert 0.0 <= res.efficiency_pct <= 100.0

    def test_sleep_score_zero_mock(self):
        """Rule #0 compliance: returns WAITING_FOR_SENSOR and None score when empty."""
        engine = SleepStagingEngine()
        res = engine.compute_overnight_sleep_analysis(hr_bpm=None, rmssd_ms=None, epoch_stages=None)
        assert res.status == "WAITING_FOR_SENSOR"
        assert res.sleep_score_100 is None
        assert res.deep_pct is None

    def test_dfa_alpha1_edge_cases(self):
        """Test DFA-alpha1 with zero variance, short buffers, and extreme patterns."""
        # Flatline / zero variance (identical RR intervals)
        flat_rrs = [800.0] * 50
        alpha_flat = calculate_dfa_alpha1(flat_rrs)
        assert alpha_flat is not None
        assert 0.40 <= alpha_flat <= 1.50
        
        # Extremely short buffer (< 4 beats)
        assert calculate_dfa_alpha1([]) is None
        assert calculate_dfa_alpha1([800.0, 810.0]) is None
        assert calculate_dfa_alpha1([800.0, 810.0, 805.0]) is None
        
        # Buffer length = 4 (minimum allowed)
        alpha_4 = calculate_dfa_alpha1([800.0, 820.0, 790.0, 810.0])
        assert alpha_4 is not None
        assert 0.40 <= alpha_4 <= 1.50

        # Highly correlated brownian noise / drift (alpha ~ 1.0 - 1.5)
        np.random.seed(42)
        drift = np.cumsum(np.random.randn(60) * 10) + 800.0
        alpha_drift = calculate_dfa_alpha1(drift.tolist())
        assert alpha_drift is not None
        assert 0.40 <= alpha_drift <= 1.50

        # White noise / uncorrelated (alpha ~ 0.5)
        noise = (np.random.randn(60) * 20 + 800.0).tolist()
        alpha_noise = calculate_dfa_alpha1(noise)
        assert alpha_noise is not None
        assert 0.40 <= alpha_noise <= 1.50

    def test_zone2_thresholds_and_domains(self):
        """Verify cardiorespiratory domain boundaries based on DFA-alpha1."""
        c_high = compute_cardiorespiratory_thresholds(hr_bpm=120.0, dfa_alpha1=0.90)
        assert c_high.current_zone == "Zone 2 (Aerobic Base Endurance)"
        assert "Below LT1" in c_high.physiological_domain
        
        c_lt1 = compute_cardiorespiratory_thresholds(hr_bpm=135.0, dfa_alpha1=0.75)
        assert c_lt1.current_zone == "Zone 2 (Aerobic Base Endurance)"
        assert "At LT1" in c_lt1.physiological_domain
        
        c_mid = compute_cardiorespiratory_thresholds(hr_bpm=155.0, dfa_alpha1=0.60)
        assert c_mid.current_zone == "Zone 3 (Tempo / Aerobic Power)"
        assert "Between LT1 and LT2" in c_mid.physiological_domain
        
        c_low = compute_cardiorespiratory_thresholds(hr_bpm=175.0, dfa_alpha1=0.42)
        assert c_low.current_zone == "Zone 4/5 (Anaerobic Threshold / Fatigue)"
        assert "Above LT2" in c_low.physiological_domain

        c_none = compute_cardiorespiratory_thresholds(hr_bpm=None, dfa_alpha1=None)
        assert c_none.status == "WAITING_FOR_SENSOR"
        assert c_none.dfa_alpha1 is None

    def test_sleep_score_zero_division_guard_daytime_hr_rest_zero(self):
        """Verify daytime_hr_rest <= 0.0 does not trigger ZeroDivisionError."""
        engine = SleepStagingEngine(hr_rest_baseline=58.0)
        
        # daytime_hr_rest = 0.0
        res_zero = engine.compute_overnight_sleep_analysis(
            hr_bpm=60.0, rmssd_ms=40.0, epoch_stages=["LIGHT"] * 10, daytime_hr_rest=0.0
        )
        assert res_zero.status == "COMPLETED"
        assert res_zero.dip_pct == 0.0

        # daytime_hr_rest = -10.0
        res_neg = engine.compute_overnight_sleep_analysis(
            hr_bpm=60.0, rmssd_ms=40.0, epoch_stages=["LIGHT"] * 10, daytime_hr_rest=-10.0
        )
        assert res_neg.status == "COMPLETED"
        assert res_neg.dip_pct == 0.0

    def test_zone2_zero_division_guard_hr_max_zero(self):
        """Verify hr_max <= 0 does not trigger ZeroDivisionError in workout classification."""
        state_zero = classify_workout_state(120.0, hr_max=0)
        assert state_zero.status == "WAITING_FOR_SENSOR"
        assert state_zero.hr_pct_max is None

        state_neg = classify_workout_state(120.0, hr_max=-50)
        assert state_neg.status == "WAITING_FOR_SENSOR"
        assert state_neg.hr_pct_max is None

        # Also test compute_cardiorespiratory_thresholds with hr_max=0
        cardio = compute_cardiorespiratory_thresholds(hr_bpm=120.0, dfa_alpha1=0.80, hr_max=0)
        assert cardio.status == "ACTIVE"
        assert cardio.vo2max_ml_kg_min is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
