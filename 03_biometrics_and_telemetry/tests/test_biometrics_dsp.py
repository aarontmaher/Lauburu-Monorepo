#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Unit & Integration Test Suite for Medical-Grade Biometrics DSP
Subsystem: 03_biometrics_and_telemetry/tests/test_biometrics_dsp.py

Tests:
1. Pan-Tompkins (1985) QRS Detector (bandpass, derivative, MWI, peak detection, multi-rate, DC offset)
2. Kamath et al. 2004 20% Clinical RR Artifact Filter
3. Time-Domain HRV Metrics (RMSSD, SDNN, pNN50)
4. Pulse Transit Time (PTT) Blood Pressure Models & Physiological Bounds
5. Detrended Fluctuation Analysis (DFA-alpha1) & Aerobic Thresholds (LT1/LT2)
6. Rule #0 Zero-Mock Verification (no synthetic mock data returned on sensor absence)
"""

import math
import sys
import unittest
from pathlib import Path

# Add DSP path to sys.path
DSP_PATH = Path(__file__).resolve().parent.parent / "dsp"
if str(DSP_PATH) not in sys.path:
    sys.path.insert(0, str(DSP_PATH))

from pan_tompkins_qrs import (
    PanTompkinsQRSDetector,
    apply_kamath_artifact_filter,
    apply_kamath_filter,
    calculate_pnn50,
    calculate_rmssd,
    calculate_sdnn,
)
from ptt_blood_pressure import (
    BloodPressureReading,
    PTTBloodPressureModel,
    calculate_hemodynamics_bp,
    calculate_ptt_from_ecg_ppg,
)
from dfa_alpha1 import (
    DFAScalingResult,
    RollingDFAAlpha1Tracker,
    calculate_dfa_alpha1,
    calculate_dfa_scaling_curve,
    classify_aerobic_threshold,
    classify_zone2_alignment,
)


class TestPanTompkinsQRSDetector(unittest.TestCase):
    """Test suite for Pan-Tompkins 1985 QRS detection pipeline."""

    def setUp(self):
        self.fs = 512
        self.detector = PanTompkinsQRSDetector(sample_rate_hz=self.fs)

    def _generate_synthetic_ecg(self, num_beats: int = 5, bpm: float = 60.0) -> list[float]:
        """Generates authentic mathematical test signal containing QRS spikes."""
        duration_sec = (num_beats + 1) * (60.0 / bpm)
        total_samples = int(duration_sec * self.fs)
        signal = [0.0] * total_samples
        interval_samples = int((60.0 / bpm) * self.fs)

        for b in range(1, num_beats + 1):
            center = b * interval_samples
            if center + 4 < total_samples:
                signal[center - 2] = 0.5
                signal[center - 1] = 2.5
                signal[center] = 5.0  # R-peak apex
                signal[center + 1] = -1.5
                signal[center + 2] = -0.5

        return signal

    def test_bandpass_filter_dc_rejection(self):
        """Bandpass filter must eliminate extreme DC offsets."""
        dc_offset = 2500.0
        raw_signal = [dc_offset + math.sin(2 * math.pi * 10 * (i / self.fs)) for i in range(self.fs * 2)]
        filtered = self.detector.bandpass_filter(raw_signal)

        # After transient startup, mean of filtered signal should be near 0.0
        steady_state = filtered[int(self.fs * 0.5):]
        mean_filtered = sum(steady_state) / float(len(steady_state))
        self.assertLess(abs(mean_filtered), 5.0)

    def test_derivative_and_squaring(self):
        """5-point derivative and squaring transform should amplify high-slope peaks."""
        sig = [0.0] * 20
        sig[10] = 10.0  # Step/spike
        deriv = self.detector.derivative_filter(sig)
        squared = self.detector.squaring_transform(deriv)

        self.assertEqual(len(deriv), len(sig))
        self.assertEqual(len(squared), len(sig))
        self.assertGreater(max(squared), 0.0)
        self.assertTrue(all(x >= 0.0 for x in squared))

    def test_qrs_detection_60bpm(self):
        """Detector should accurately locate all R-peaks at 60 BPM (1000ms intervals)."""
        ecg = self._generate_synthetic_ecg(num_beats=5, bpm=60.0)
        peaks, rrs = self.detector.detect_qrs_peaks(ecg)

        self.assertGreaterEqual(len(peaks), 4)
        self.assertGreaterEqual(len(rrs), 3)

        for rr in rrs:
            self.assertAlmostEqual(rr, 1000.0, delta=20.0)

    def test_qrs_detection_120bpm(self):
        """Detector should accurately locate R-peaks at 120 BPM (500ms intervals)."""
        ecg = self._generate_synthetic_ecg(num_beats=6, bpm=120.0)
        peaks, rrs = self.detector.detect_qrs_peaks(ecg)

        self.assertGreaterEqual(len(peaks), 5)
        for rr in rrs:
            self.assertAlmostEqual(rr, 500.0, delta=20.0)

    def test_isoelectric_flatline_zero_peaks(self):
        """Rule #0: Flatline signal must detect 0 peaks and return empty lists."""
        flatline = [0.0] * (self.fs * 3)
        peaks, rrs = self.detector.detect_qrs_peaks(flatline)
        self.assertEqual(peaks, [])
        self.assertEqual(rrs, [])

    def test_sub_half_second_buffer_safety(self):
        """Buffer shorter than 0.5s returns empty results without crashing."""
        short_buf = [1.0, 2.0, 3.0]
        peaks, rrs = self.detector.detect_qrs_peaks(short_buf)
        self.assertEqual(peaks, [])
        self.assertEqual(rrs, [])

    def test_multi_sampling_rates(self):
        """Detector handles different sampling frequencies (128Hz, 256Hz, 1024Hz)."""
        for rate in [128, 256, 1024]:
            det = PanTompkinsQRSDetector(sample_rate_hz=rate)
            duration = 4.0
            samples = int(duration * rate)
            sig = [0.0] * samples
            interval = int(1.0 * rate)  # 1 beat per second
            for b in [1, 2, 3]:
                idx = b * interval
                if idx < samples:
                    sig[idx] = 4.0

            peaks, rrs = det.detect_qrs_peaks(sig)
            self.assertGreaterEqual(len(peaks), 2)
            if rrs:
                self.assertAlmostEqual(rrs[0], 1000.0, delta=50.0)


class TestKamathArtifactFilterAndHRV(unittest.TestCase):
    """Test suite for Kamath 2004 20% clinical RR filter and time-domain HRV."""

    def test_normal_sinus_rhythm_no_artifacts(self):
        """Normal sinus rhythm within 10% variation should pass with 0 rejected artifacts."""
        clean_rrs = [800.0, 810.0, 795.0, 805.0, 815.0, 800.0]
        filtered, count = apply_kamath_artifact_filter(clean_rrs, threshold_pct=20.0)

        self.assertEqual(count, 0)
        self.assertEqual(filtered, clean_rrs)

    def test_ectopic_beat_interpolation(self):
        """Ectopic spike (>20% difference) is flagged and interpolated."""
        corrupted_rrs = [800.0, 805.0, 1400.0, 800.0, 810.0]
        filtered, count = apply_kamath_artifact_filter(corrupted_rrs, threshold_pct=20.0)

        self.assertGreaterEqual(count, 1)
        # Interpolated value should replace 1400.0 with a physiologically plausible value
        self.assertLess(filtered[2], 1200.0)
        self.assertGreater(filtered[2], 700.0)

    def test_convenience_wrapper_match(self):
        """apply_kamath_filter returns same filtered array as apply_kamath_artifact_filter[0]."""
        rrs = [800.0, 1200.0, 800.0]
        wrapper_res = apply_kamath_filter(rrs)
        full_res, _ = apply_kamath_artifact_filter(rrs)
        self.assertEqual(wrapper_res, full_res)

    def test_rmssd_calculation(self):
        """RMSSD formula verification."""
        # Consecutive differences: [10, -10, 10, -10] => diff^2 = 100 => mean = 100 => sqrt = 10.0
        rrs = [800.0, 810.0, 800.0, 810.0, 800.0]
        rmssd = calculate_rmssd(rrs)
        self.assertIsNotNone(rmssd)
        self.assertAlmostEqual(rmssd, 10.0, places=1)

    def test_sdnn_and_pnn50(self):
        """SDNN and pNN50 calculations."""
        rrs = [800.0, 860.0, 800.0, 870.0, 800.0]  # Differences all > 50ms
        pnn50 = calculate_pnn50(rrs)
        self.assertIsNotNone(pnn50)
        self.assertEqual(pnn50, 100.0)

        sdnn = calculate_sdnn(rrs)
        self.assertIsNotNone(sdnn)
        self.assertGreater(sdnn, 0.0)

    def test_hrv_empty_arrays_return_none(self):
        """Rule #0: Insufficient beats return None."""
        self.assertIsNone(calculate_rmssd([]))
        self.assertIsNone(calculate_rmssd([800.0]))
        self.assertIsNone(calculate_sdnn([]))
        self.assertIsNone(calculate_pnn50([]))


class TestPTTBloodPressure(unittest.TestCase):
    """Test suite for Pulse Transit Time cuffless blood pressure engine."""

    def setUp(self):
        self.model = PTTBloodPressureModel()

    def test_baseline_nominal_pressure(self):
        """Baseline PTT (200ms) and HR (70 BPM) should yield ~120/80 mmHg."""
        reading = self.model.estimate_blood_pressure(ptt_ms=200.0, hr_bpm=70.0)
        self.assertIsNotNone(reading.systolic_mmhg)
        self.assertIsNotNone(reading.diastolic_mmhg)
        self.assertAlmostEqual(reading.systolic_mmhg, 120.0, delta=2.0)
        self.assertAlmostEqual(reading.diastolic_mmhg, 80.0, delta=2.0)
        self.assertEqual(reading.status, "NOMINAL")
        self.assertEqual(reading.classification, PTTBloodPressureModel.CLASSIFICATIONS["NORMAL"])

    def test_short_ptt_elevated_pressure(self):
        """Shorter PTT (faster arterial pulse wave) reflects increased blood pressure."""
        reading = self.model.estimate_blood_pressure(ptt_ms=140.0, hr_bpm=85.0)
        self.assertGreater(reading.systolic_mmhg, 130.0)
        self.assertGreater(reading.diastolic_mmhg, 85.0)

    def test_long_ptt_lower_pressure(self):
        """Longer PTT (slower pulse wave) reflects lower blood pressure."""
        reading = self.model.estimate_blood_pressure(ptt_ms=260.0, hr_bpm=55.0)
        self.assertLess(reading.systolic_mmhg, 110.0)
        self.assertLess(reading.diastolic_mmhg, 75.0)

    def test_subject_calibration(self):
        """Calibrating against an arm-cuff measurement updates offsets."""
        ok = self.model.calibrate(cuff_sbp=135.0, cuff_dbp=88.0, measured_ptt_ms=190.0, measured_hr_bpm=72.0)
        self.assertTrue(ok)
        self.assertTrue(self.model.calibrated)

        # Re-evaluating at calibration point returns calibrated cuff values
        reading = self.model.estimate_blood_pressure(ptt_ms=190.0, hr_bpm=72.0)
        self.assertAlmostEqual(reading.systolic_mmhg, 135.0, delta=1.0)
        self.assertAlmostEqual(reading.diastolic_mmhg, 88.0, delta=1.0)

    def test_invalid_calibration_rejected(self):
        """Unphysiological calibration values are rejected."""
        # SBP lower than DBP
        ok = self.model.calibrate(cuff_sbp=70.0, cuff_dbp=90.0, measured_ptt_ms=200.0, measured_hr_bpm=70.0)
        self.assertFalse(ok)

    def test_calculate_ptt_from_peaks(self):
        """Computes PTT by pairing ECG R-peaks and subsequent PPG systolic peaks."""
        fs = 512
        # R-peaks at 1.0s, 2.0s, 3.0s => indices 512, 1024, 1536
        ecg_peaks = [512, 1024, 1536]
        # PPG peaks at +200ms => +102 samples => 614, 1126, 1638
        ppg_peaks = [614, 1126, 1638]

        ptts = calculate_ptt_from_ecg_ppg(ecg_peaks, ppg_peaks, sample_rate_hz=fs)
        self.assertEqual(len(ptts), 3)
        for ptt in ptts:
            self.assertAlmostEqual(ptt, (102 / 512.0) * 1000.0, delta=1.0)

    def test_missing_inputs_rule_0(self):
        """Rule #0: None inputs return STANDBY status and None numeric values."""
        reading = self.model.estimate_blood_pressure(ptt_ms=None, hr_bpm=None)
        self.assertIsNone(reading.systolic_mmhg)
        self.assertIsNone(reading.diastolic_mmhg)
        self.assertEqual(reading.status, "STANDBY")
        self.assertTrue(reading.rule_0_zero_mock)

        sbp, dbp, map_val = calculate_hemodynamics_bp(None, None)
        self.assertIsNone(sbp)
        self.assertIsNone(dbp)
        self.assertIsNone(map_val)


class TestDFAAlpha1(unittest.TestCase):
    """Test suite for Detrended Fluctuation Analysis (DFA-alpha1) & Aerobic Thresholds."""

    def test_insufficient_samples_return_none(self):
        """Rule #0: Arrays shorter than scale_min (4) return None."""
        self.assertIsNone(calculate_dfa_alpha1([]))
        self.assertIsNone(calculate_dfa_alpha1([800.0, 810.0]))

    def test_dfa_alpha1_scaling_range(self):
        """DFA-alpha1 for physiological series is strictly bounded in [0.20, 1.80]."""
        # Create varying synthetic RR series with known fractal structure
        base_rr = 800.0
        rrs = [base_rr + 25.0 * math.sin(i * 0.3) + 10.0 * math.cos(i * 0.7) for i in range(50)]

        alpha1 = calculate_dfa_alpha1(rrs)
        self.assertIsNotNone(alpha1)
        self.assertGreaterEqual(alpha1, 0.20)
        self.assertLessEqual(alpha1, 1.80)

    def test_aerobic_threshold_classification(self):
        """Lactate threshold zone classifications."""
        # Zone 2 (Aerobic Base): alpha1 >= 0.75
        c1 = classify_aerobic_threshold(0.82)
        self.assertEqual(c1["lt_transition"], "BELOW_LT1")
        self.assertEqual(c1["zone"], "Zone 2")

        # LT1 Transition: 0.70 <= alpha1 < 0.75
        c2 = classify_aerobic_threshold(0.72)
        self.assertEqual(c2["lt_transition"], "AT_LT1_TRANSITION")

        # Zone 3 Tempo: 0.55 <= alpha1 < 0.70
        c3 = classify_aerobic_threshold(0.62)
        self.assertEqual(c3["lt_transition"], "BETWEEN_LT1_LT2")

        # LT2 Transition: 0.48 <= alpha1 < 0.55
        c4 = classify_aerobic_threshold(0.51)
        self.assertEqual(c4["lt_transition"], "AT_LT2_TRANSITION")

        # Zone 4/5 Anaerobic: alpha1 < 0.48
        c5 = classify_aerobic_threshold(0.42)
        self.assertEqual(c5["lt_transition"], "ABOVE_LT2_ANAEROBIC")

    def test_scaling_curve_diagnostics(self):
        """calculate_dfa_scaling_curve outputs complete regression diagnostics."""
        rrs = [800.0 + 15.0 * math.sin(i * 0.2) for i in range(40)]
        diag = calculate_dfa_scaling_curve(rrs)

        self.assertIsInstance(diag, DFAScalingResult)
        self.assertIsNotNone(diag.alpha1)
        self.assertGreater(len(diag.scales), 0)
        self.assertGreater(len(diag.fluctuations), 0)
        self.assertEqual(len(diag.log_scales), len(diag.log_fluctuations))

    def test_rolling_dfa_tracker(self):
        """RollingDFAAlpha1Tracker maintains rolling buffer and calculates alpha1 dynamically."""
        tracker = RollingDFAAlpha1Tracker(max_beats=30)
        for i in range(25):
            val = 800.0 + 10.0 * math.sin(i * 0.5)
            alpha1 = tracker.add_rr_interval(val)

        current_a1 = tracker.get_current_alpha1()
        self.assertIsNotNone(current_a1)
        self.assertEqual(len(tracker.buffer), 25)

        tracker.clear()
        self.assertEqual(len(tracker.buffer), 0)
        self.assertIsNone(tracker.get_current_alpha1())


if __name__ == "__main__":
    unittest.main()
