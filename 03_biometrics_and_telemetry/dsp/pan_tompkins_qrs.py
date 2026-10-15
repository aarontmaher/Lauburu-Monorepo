#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Medical-Grade Pan-Tompkins ECG QRS Detector & Real-Time DSP Engine
Subsystem: 03_biometrics_and_telemetry/dsp/pan_tompkins_qrs.py

Implements:
1. Pan-Tompkins 1985 Real-Time QRS Detection:
   - 4th-order Butterworth Bandpass Filter (0.5 Hz - 40.0 Hz) forward-backward zero-phase
   - 5-point Derivative Operator (suppresses P and T waves, highlights QRS slope)
   - Nonlinear Squaring Function
   - Moving Window Integration (MWI) with 150ms window
   - Adaptive Dual-Threshold Peak Detection with 200ms Refractory Period and Searchback
2. Kamath et al. 2004 Clinical 20% RR Artifact Filter
3. HRV Time-Domain Metrics: RMSSD, SDNN, pNN50
4. Strict Rule #0 Zero-Mock Compliance: returns WAITING_FOR_SENSOR / None when sensors are absent.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

try:
    from scipy.signal import butter, filtfilt
    SCIPY_AVAILABLE = True
except ImportError:
    butter = None
    filtfilt = None
    SCIPY_AVAILABLE = False


@dataclass
class QRSResult:
    """Structured output from Pan-Tompkins QRS Detection."""
    peak_indices: List[int]
    rr_intervals_ms: List[float]
    sampling_rate_hz: float
    qrs_count: int
    mean_hr_bpm: Optional[float]
    rmssd_ms: Optional[float]
    sdnn_ms: Optional[float]
    pnn50_pct: Optional[float]
    filtered_signal: List[float]
    rule_0_zero_mock: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "peak_indices": self.peak_indices,
            "rr_intervals_ms": self.rr_intervals_ms,
            "sampling_rate_hz": self.sampling_rate_hz,
            "qrs_count": self.qrs_count,
            "mean_hr_bpm": self.mean_hr_bpm,
            "rmssd_ms": self.rmssd_ms,
            "sdnn_ms": self.sdnn_ms,
            "pnn50_pct": self.pnn50_pct,
            "filtered_signal": self.filtered_signal,
            "rule_0_zero_mock": self.rule_0_zero_mock,
        }


class PanTompkinsQRSDetector:
    """
    Genuine, Real-Time Pan-Tompkins (1985) QRS Detection Algorithm.
    Operates on 512Hz, 256Hz, 128Hz, or variable rate raw ECG microvolt/millivolt sample arrays.
    """

    def __init__(self, sample_rate_hz: int = 512):
        self.fs = max(50, int(sample_rate_hz))
        self.mwi_window = max(2, int(0.150 * self.fs))  # 150ms integration window
        self.refractory_samples = max(2, int(0.200 * self.fs))  # 200ms refractory period

        # Running adaptive peak threshold state
        self.spk: float = 0.0  # Signal peak level
        self.npk: float = 0.0  # Noise peak level
        self.threshold_i1: float = 0.0  # Primary detection threshold
        self.threshold_i2: float = 0.0  # Secondary searchback threshold
        self.initialized: bool = False

    def bandpass_filter(self, ecg_signal: Sequence[float]) -> List[float]:
        """
        4th-order Butterworth bandpass filter (0.5 Hz - 40.0 Hz) to eliminate baseline wander
        and high-frequency muscle noise / mains interference.
        Implements forward-backward zero-phase filtering across any sampling frequency.
        """
        if not ecg_signal:
            return []

        n = len(ecg_signal)
        if n < 8:
            return [float(x) for x in ecg_signal]

        # Subtract baseline mean to eliminate step transient DC offset
        mean_offset = sum(ecg_signal) / float(n)
        centered_signal = [float(x) - mean_offset for x in ecg_signal]

        if SCIPY_AVAILABLE and NUMPY_AVAILABLE and n >= 15:
            try:
                nyquist = 0.5 * self.fs
                low = max(0.005, 0.5 / nyquist)
                high = min(0.99, min(40.0, self.fs * 0.45) / nyquist)
                b, a = butter(2, [low, high], btype="bandpass")
                filtered = filtfilt(b, a, np.array(centered_signal, dtype=float))
                return [round(float(x), 4) for x in filtered]
            except Exception:
                pass

        # Exact Bilinear Transform 2nd-order Highpass (0.5Hz) + 2nd-order Lowpass (40Hz)
        def biquad_coeffs(fc: float, fs: float, is_hp: bool) -> Tuple[float, float, float, float, float]:
            w = math.tan(math.pi * fc / fs)
            w2 = w * w
            sqrt2 = math.sqrt(2.0)
            norm = 1.0 + sqrt2 * w + w2
            if is_hp:
                b0 = 1.0 / norm
                b1 = -2.0 * b0
                b2 = b0
            else:
                b0 = w2 / norm
                b1 = 2.0 * b0
                b2 = b0
            a1 = 2.0 * (w2 - 1.0) / norm
            a2 = (1.0 - sqrt2 * w + w2) / norm
            return (b0, b1, b2, a1, a2)

        hp = biquad_coeffs(0.5, float(self.fs), is_hp=True)
        lp = biquad_coeffs(min(40.0, self.fs * 0.45), float(self.fs), is_hp=False)

        def apply_section(x: Sequence[float], c: Tuple[float, float, float, float, float]) -> List[float]:
            b0, b1, b2, a1, a2 = c
            y = [0.0] * len(x)
            for i in range(len(x)):
                x0 = x[i]
                x1 = x[i - 1] if i >= 1 else 0.0
                x2 = x[i - 2] if i >= 2 else 0.0
                y1 = y[i - 1] if i >= 1 else 0.0
                y2 = y[i - 2] if i >= 2 else 0.0
                y[i] = b0 * x0 + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
            return y

        def filtfilt_section(x: Sequence[float], c: Tuple[float, float, float, float, float]) -> List[float]:
            fwd = apply_section(x, c)
            rev = apply_section(fwd[::-1], c)
            return rev[::-1]

        hp_out = filtfilt_section(centered_signal, hp)
        bp_out = filtfilt_section(hp_out, lp)
        return [round(float(v), 4) for v in bp_out]

    def derivative_filter(self, filtered_signal: Sequence[float]) -> List[float]:
        """
        5-point derivative operator:
        d[n] = (1/8T) * (-x[n-2] - 2*x[n-1] + 2*x[n+1] + x[n+2])
        Provides slope information and suppresses P/T wave components.
        """
        n = len(filtered_signal)
        if n < 5:
            return [0.0] * n

        T = 1.0 / self.fs
        scale = 1.0 / (8.0 * T)
        deriv = [0.0] * n

        for i in range(2, n - 2):
            val = (
                -filtered_signal[i - 2]
                - 2.0 * filtered_signal[i - 1]
                + 2.0 * filtered_signal[i + 1]
                + filtered_signal[i + 2]
            ) * scale
            deriv[i] = val

        return deriv

    def squaring_transform(self, derivative_signal: Sequence[float]) -> List[float]:
        """Nonlinear squaring transform: s[n] = (d[n])^2."""
        return [float(x * x) for x in derivative_signal]

    def moving_window_integration(self, squared_signal: Sequence[float]) -> List[float]:
        """
        Moving Window Integrator (MWI) with N = 150ms window.
        Extracts waveform feature duration.
        """
        n = len(squared_signal)
        if n == 0:
            return []

        mwi = [0.0] * n
        window = self.mwi_window
        running_sum = 0.0

        for i in range(n):
            running_sum += squared_signal[i]
            if i >= window:
                running_sum -= squared_signal[i - window]
            mwi[i] = running_sum / float(min(i + 1, window))

        return mwi

    def detect_qrs_peaks(self, ecg_signal: Sequence[float]) -> Tuple[List[int], List[float]]:
        """
        Executes full Pan-Tompkins pipeline on raw ECG array.
        Returns:
            peak_indices: list of sample index positions where R-peaks occurred.
            rr_intervals_ms: list of RR intervals in milliseconds (sub-millisecond precision).
        """
        if not ecg_signal or len(ecg_signal) < int(self.fs * 0.5):
            return [], []

        # 1. Bandpass Filter
        filtered = self.bandpass_filter(ecg_signal)

        # 2. Derivative Filter
        deriv = self.derivative_filter(filtered)

        # 3. Squaring Transform
        squared = self.squaring_transform(deriv)

        # 4. Moving Window Integration
        mwi = self.moving_window_integration(squared)

        max_mwi = max(mwi) if mwi else 0.0
        if max_mwi <= 1e-6:
            return [], []

        # 5. Adaptive Dual-Threshold Peak Detection
        min_peak_height = max_mwi * 0.05
        local_peaks = []
        n = len(mwi)

        for i in range(1, n - 1):
            if mwi[i] > mwi[i - 1] and mwi[i] >= mwi[i + 1] and mwi[i] >= min_peak_height:
                local_peaks.append((i, mwi[i]))

        if not local_peaks:
            return [], []

        # Adaptive threshold initialization
        peak_vals = [p[1] for p in local_peaks]
        self.spk = max(peak_vals) * 0.5
        self.npk = (sum(peak_vals) / len(peak_vals)) * 0.1
        self.threshold_i1 = self.npk + 0.25 * (self.spk - self.npk)
        self.threshold_i2 = 0.5 * self.threshold_i1

        peaks: List[int] = []
        last_peak_idx = -self.refractory_samples

        for idx, peak_val in local_peaks:
            # Check refractory period (200ms)
            if idx - last_peak_idx < self.refractory_samples:
                continue

            if peak_val >= self.threshold_i1:
                # Search back in filtered signal for true R-peak apex
                search_start = max(0, idx - self.mwi_window)
                search_end = min(len(filtered), idx + max(5, self.mwi_window // 2))
                r_apex = search_start
                r_max = -1e9

                for s_idx in range(search_start, search_end):
                    if filtered[s_idx] > r_max:
                        r_max = filtered[s_idx]
                        r_apex = s_idx

                peaks.append(r_apex)
                last_peak_idx = r_apex
                self.spk = 0.125 * peak_val + 0.875 * self.spk
            elif peak_val >= self.threshold_i2:
                # Searchback peak detection for lower threshold
                search_start = max(0, idx - self.mwi_window)
                search_end = min(len(filtered), idx + max(5, self.mwi_window // 2))
                r_apex = search_start
                r_max = -1e9

                for s_idx in range(search_start, search_end):
                    if filtered[s_idx] > r_max:
                        r_max = filtered[s_idx]
                        r_apex = s_idx

                peaks.append(r_apex)
                last_peak_idx = r_apex
                self.spk = 0.25 * peak_val + 0.75 * self.spk
            else:
                self.npk = 0.125 * peak_val + 0.875 * self.npk

            self.threshold_i1 = self.npk + 0.25 * (self.spk - self.npk)
            self.threshold_i2 = 0.5 * self.threshold_i1

        # Compute sub-millisecond precision RR intervals in ms
        rr_intervals: List[float] = []
        for i in range(1, len(peaks)):
            diff_samples = peaks[i] - peaks[i - 1]
            rr_ms = (diff_samples / float(self.fs)) * 1000.0
            if 250.0 <= rr_ms <= 2200.0:  # Physiological range (27 - 240 BPM)
                rr_intervals.append(round(rr_ms, 1))

        return peaks, rr_intervals

    def detect_peaks(self, signal: Any, fs: Optional[float] = None) -> QRSResult:
        """
        Interface Contract (PROJECT.md):
        Butterworth 0.5-40Hz filtering, derivative, MWI, and Kamath 20% artifact correction.
        """
        if fs is not None and fs > 0:
            self.fs = int(fs)
            self.mwi_window = max(2, int(0.150 * self.fs))
            self.refractory_samples = max(2, int(0.200 * self.fs))

        if signal is None:
            return QRSResult(
                peak_indices=[],
                rr_intervals_ms=[],
                sampling_rate_hz=float(self.fs),
                qrs_count=0,
                mean_hr_bpm=None,
                rmssd_ms=None,
                sdnn_ms=None,
                pnn50_pct=None,
                filtered_signal=[],
                rule_0_zero_mock=True,
            )

        if NUMPY_AVAILABLE and isinstance(signal, np.ndarray):
            sig_list = [float(x) for x in signal.flatten()]
        elif isinstance(signal, (list, tuple)):
            sig_list = [float(x) for x in signal]
        else:
            sig_list = []

        if not sig_list or len(sig_list) < int(self.fs * 0.5):
            return QRSResult(
                peak_indices=[],
                rr_intervals_ms=[],
                sampling_rate_hz=float(self.fs),
                qrs_count=0,
                mean_hr_bpm=None,
                rmssd_ms=None,
                sdnn_ms=None,
                pnn50_pct=None,
                filtered_signal=[],
                rule_0_zero_mock=True,
            )

        filtered = self.bandpass_filter(sig_list)
        peaks, raw_rrs = self.detect_qrs_peaks(sig_list)
        clean_rrs, _ = apply_kamath_artifact_filter(raw_rrs, threshold_pct=20.0)

        mean_hr = round(60000.0 / (sum(clean_rrs) / len(clean_rrs)), 1) if clean_rrs else None
        rmssd = calculate_rmssd(clean_rrs)
        sdnn = calculate_sdnn(clean_rrs)
        pnn50 = calculate_pnn50(clean_rrs)

        return QRSResult(
            peak_indices=peaks,
            rr_intervals_ms=clean_rrs,
            sampling_rate_hz=float(self.fs),
            qrs_count=len(peaks),
            mean_hr_bpm=mean_hr,
            rmssd_ms=rmssd,
            sdnn_ms=sdnn,
            pnn50_pct=pnn50,
            filtered_signal=filtered,
            rule_0_zero_mock=True,
        )


# ============================================================================
# CLINICAL RR ARTIFACT FILTERS & TIME-DOMAIN HRV
# ============================================================================

def apply_kamath_artifact_filter(
    rr_intervals: Sequence[float],
    threshold_pct: float = 20.0
) -> Tuple[List[float], int]:
    """
    Applies the Kamath et al. 2004 Clinical 20% RR Artifact Filter.
    Condition: |RR[i] - RR[i-1]| / RR[i-1] <= 0.20.
    Preserves true physiological baseline during ectopic bursts and interpolates corrupted beats.
    """
    if not rr_intervals or len(rr_intervals) < 2:
        return [float(x) for x in (rr_intervals or [])], 0

    thresh = threshold_pct / 100.0
    r0 = float(rr_intervals[0])

    # Establish robust physiological baseline anchor (250ms - 2200ms)
    valid_cands = [float(x) for x in rr_intervals[:min(5, len(rr_intervals))] if 250.0 <= float(x) <= 2200.0]
    if 250.0 <= r0 <= 2200.0:
        cleaned = [r0]
        artifact_count = 0
    elif valid_cands:
        anchor = valid_cands[0]
        cleaned = [anchor]
        artifact_count = 1
    else:
        all_valid = [float(x) for x in rr_intervals if 250.0 <= float(x) <= 2200.0]
        if all_valid:
            cleaned = [all_valid[0]]
            artifact_count = 1
        else:
            cleaned = [r0]
            artifact_count = 0

    for i in range(1, len(rr_intervals)):
        prev = cleaned[-1]
        curr = float(rr_intervals[i])
        if 250.0 <= curr <= 2200.0 and prev > 0 and (abs(curr - prev) / prev) <= thresh:
            cleaned.append(curr)
        else:
            artifact_count += 1
            # Search ahead for the next valid physiological beat within threshold
            next_val = None
            for j in range(i + 1, len(rr_intervals)):
                cand = float(rr_intervals[j])
                if 250.0 <= cand <= 2200.0 and prev > 0 and (abs(cand - prev) / prev) <= thresh:
                    next_val = cand
                    break
            if next_val is None:
                next_val = prev
            corrected = (prev + next_val) / 2.0
            cleaned.append(round(corrected, 1))

    return cleaned, artifact_count


def apply_kamath_filter(
    rr_intervals: Sequence[float],
    threshold_pct: float = 20.0
) -> List[float]:
    """Convenience wrapper returning filtered RR intervals."""
    cleaned, _ = apply_kamath_artifact_filter(rr_intervals, threshold_pct=threshold_pct)
    return cleaned


def calculate_rmssd(rr_intervals: Sequence[float]) -> Optional[float]:
    """
    Computes Root Mean Square of Successive Differences (RMSSD) in ms.
    RMSSD = sqrt( 1/(N-1) * sum((RR[i+1] - RR[i])^2) )
    Returns None if fewer than 2 valid beats.
    """
    if not rr_intervals or len(rr_intervals) < 2:
        return None

    diffs = [float(rr_intervals[i]) - float(rr_intervals[i - 1]) for i in range(1, len(rr_intervals))]
    sum_sq = sum(d * d for d in diffs)
    mean_sq = sum_sq / float(len(rr_intervals) - 1)
    return round(math.sqrt(mean_sq), 2)


def calculate_sdnn(rr_intervals: Sequence[float]) -> Optional[float]:
    """
    Computes Standard Deviation of NN/RR intervals (SDNN) in ms.
    Returns None if fewer than 2 valid beats.
    """
    if not rr_intervals or len(rr_intervals) < 2:
        return None

    rrs = [float(x) for x in rr_intervals]
    mean_rr = sum(rrs) / float(len(rrs))
    var = sum((x - mean_rr) ** 2 for x in rrs) / float(len(rrs) - 1)
    return round(math.sqrt(var), 2)


def calculate_pnn50(rr_intervals: Sequence[float]) -> Optional[float]:
    """
    Computes percentage of successive RR interval differences > 50 ms (pNN50).
    Returns None if fewer than 2 valid beats.
    """
    if not rr_intervals or len(rr_intervals) < 2:
        return None

    diffs = [abs(float(rr_intervals[i]) - float(rr_intervals[i - 1])) for i in range(1, len(rr_intervals))]
    nn50_count = sum(1 for d in diffs if d > 50.0)
    pnn50 = (nn50_count / float(len(diffs))) * 100.0
    return round(pnn50, 2)
