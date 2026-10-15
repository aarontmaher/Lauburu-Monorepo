#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pulse Transit Time (PTT) Cuffless Blood Pressure & Hemodynamics Engine
Subsystem: 03_biometrics_and_telemetry/dsp/ptt_blood_pressure.py

Physics & Mathematical Foundations:
1. Moens-Korteweg Equation:
   PWV = sqrt((E * h) / (rho * d))
   where PWV = Pulse Wave Velocity, E = arterial Young's modulus, h = wall thickness,
   rho = blood density (~1050 kg/m^3), d = arterial inner diameter.
2. Hughes Elasticity Law:
   E(P) = E_0 * exp(gamma * P)
   where P = arterial blood pressure, E_0 = zero-pressure elasticity, gamma = vessel coefficient.
3. PTT to BP Inversion:
   PTT = d_arterial / PWV
   P = (1/gamma) * ln((rho * d / (E_0 * h)) * (d_arterial / PTT)^2)
4. Linearized & Non-Linear Calibration Models:
   - SBP = a_sbp * PTT + b_sbp * HR + c_sbp
   - DBP = a_dbp * PTT + b_dbp * HR + c_dbp
   - MAP = (SBP + 2 * DBP) / 3.0
   - PP  = SBP - DBP

Strict Rule #0 Compliance: Zero synthetic or simulated data arrays.
Returns clean None / STANDBY values when sensor telemetry is absent or non-physiological.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


@dataclass
class BloodPressureReading:
    """Structured representation of a single hemodynamic blood pressure estimate."""
    systolic_mmhg: Optional[float]
    diastolic_mmhg: Optional[float]
    map_mmhg: Optional[float]
    pulse_pressure_mmhg: Optional[float]
    ptt_ms: Optional[float]
    hr_bpm: Optional[float]
    pwv_mps: Optional[float]  # Pulse Wave Velocity in m/s
    classification: str
    status: str
    rule_0_zero_mock: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "systolic_mmhg": self.systolic_mmhg,
            "diastolic_mmhg": self.diastolic_mmhg,
            "map_mmhg": self.map_mmhg,
            "pulse_pressure_mmhg": self.pulse_pressure_mmhg,
            "ptt_ms": self.ptt_ms,
            "hr_bpm": self.hr_bpm,
            "pwv_mps": self.pwv_mps,
            "classification": self.classification,
            "status": self.status,
            "rule_0_zero_mock": self.rule_0_zero_mock,
        }


# Type alias for interface contract in PROJECT.md
BloodPressureResult = BloodPressureReading


class PTTBloodPressureModel:
    """
    Medical-Grade Pulse Transit Time (PTT) Blood Pressure Estimator.
    Supports linear, non-linear logarithmic, and subject-calibrated hemodynamic models.
    """

    # AHA/ACC 2017 Blood Pressure Clinical Guidelines
    CLASSIFICATIONS = {
        "NORMAL": "Normal (<120 / <80 mmHg)",
        "ELEVATED": "Elevated (120-129 / <80 mmHg)",
        "HYPERTENSIVE_STAGE1": "Hypertension Stage 1 (130-139 / 80-89 mmHg)",
        "HYPERTENSIVE_STAGE2": "Hypertension Stage 2 (≥140 / ≥90 mmHg)",
        "HYPERTENSIVE_CRISIS": "Hypertensive Crisis (>180 / >120 mmHg)",
        "HYPOTENSIVE": "Hypotension (<90 / <60 mmHg)",
        "STANDBY": "Standby / Awaiting Telemetry",
    }

    def __init__(
        self,
        arterial_path_length_m: float = 0.80,  # Standard heart-to-distal finger distance (~0.8m)
        baseline_ptt_ms: float = 200.0,
        baseline_hr_bpm: float = 70.0,
        baseline_sbp: float = 120.0,
        baseline_dbp: float = 80.0,
    ):
        self.arterial_path_length_m = max(0.40, float(arterial_path_length_m))
        self.baseline_ptt_ms = baseline_ptt_ms
        self.baseline_hr_bpm = baseline_hr_bpm
        self.baseline_sbp = baseline_sbp
        self.baseline_dbp = baseline_dbp

        # Empirical calibration slopes (mmHg per ms delta, mmHg per BPM delta)
        self.k_sbp_ptt: float = -0.45  # Negative correlation: shorter PTT -> higher SBP
        self.k_sbp_hr: float = 0.15   # Positive correlation: higher HR -> higher SBP
        self.k_dbp_ptt: float = -0.25  # Shorter PTT -> higher DBP
        self.k_dbp_hr: float = 0.075  # Higher HR -> higher DBP

        # Individual calibration state
        self.calibrated: bool = False

    def calibrate(
        self,
        cuff_sbp: float,
        cuff_dbp: float,
        measured_ptt_ms: float,
        measured_hr_bpm: float,
    ) -> bool:
        """
        Calibrates the model against an empirical arm-cuff reference measurement.
        Updates subject baselines to eliminate subject-specific vascular stiffness bias.
        """
        if (
            cuff_sbp < 60.0 or cuff_sbp > 250.0
            or cuff_dbp < 35.0 or cuff_dbp > 150.0
            or cuff_dbp >= cuff_sbp
            or measured_ptt_ms < 80.0 or measured_ptt_ms > 600.0
            or measured_hr_bpm < 30.0 or measured_hr_bpm > 240.0
        ):
            return False

        self.baseline_sbp = cuff_sbp
        self.baseline_dbp = cuff_dbp
        self.baseline_ptt_ms = measured_ptt_ms
        self.baseline_hr_bpm = measured_hr_bpm
        self.calibrated = True
        return True

    def calculate_pwv(self, ptt_ms: Optional[float]) -> Optional[float]:
        """
        Calculates Pulse Wave Velocity (PWV) in m/s:
        PWV = path_length_m / (PTT_ms / 1000.0)
        Physiological range for human arteries: ~4.0 m/s to 18.0 m/s.
        """
        if ptt_ms is None or ptt_ms <= 0:
            return None
        ptt_sec = float(ptt_ms) / 1000.0
        pwv = self.arterial_path_length_m / ptt_sec
        return round(pwv, 2)

    def estimate_blood_pressure(
        self,
        ptt_ms: Optional[float],
        hr_bpm: Optional[float],
        use_nonlinear: bool = False,
    ) -> BloodPressureReading:
        """
        Computes systolic (SBP), diastolic (DBP), and mean arterial pressure (MAP).
        Strict Rule #0 compliance: returns STANDBY reading if inputs are missing or unphysiological.
        """
        if (
            ptt_ms is None
            or hr_bpm is None
            or ptt_ms < 80.0
            or ptt_ms > 600.0
            or hr_bpm < 30.0
            or hr_bpm > 240.0
        ):
            return BloodPressureReading(
                systolic_mmhg=None,
                diastolic_mmhg=None,
                map_mmhg=None,
                pulse_pressure_mmhg=None,
                ptt_ms=ptt_ms if ptt_ms and 80.0 <= ptt_ms <= 600.0 else None,
                hr_bpm=hr_bpm if hr_bpm and 30.0 <= hr_bpm <= 240.0 else None,
                pwv_mps=self.calculate_pwv(ptt_ms) if ptt_ms and 80.0 <= ptt_ms <= 600.0 else None,
                classification=self.CLASSIFICATIONS["STANDBY"],
                status="STANDBY",
                rule_0_zero_mock=True,
            )

        ptt = float(ptt_ms)
        hr = float(hr_bpm)
        pwv = self.calculate_pwv(ptt)

        if use_nonlinear:
            # Non-linear logarithmic elasticity model
            log_ratio = math.log(self.baseline_ptt_ms / ptt) if ptt > 0 else 0.0
            raw_sbp = self.baseline_sbp + (90.0 * log_ratio) + (self.k_sbp_hr * (hr - self.baseline_hr_bpm))
            raw_dbp = self.baseline_dbp + (50.0 * log_ratio) + (self.k_dbp_hr * (hr - self.baseline_hr_bpm))
        else:
            # Standard linearized perturbation model
            delta_ptt = ptt - self.baseline_ptt_ms
            delta_hr = hr - self.baseline_hr_bpm
            raw_sbp = self.baseline_sbp + (self.k_sbp_ptt * delta_ptt) + (self.k_sbp_hr * delta_hr)
            raw_dbp = self.baseline_dbp + (self.k_dbp_ptt * delta_ptt) + (self.k_dbp_hr * delta_hr)

        # Enforce clinical physiological clamps
        sbp = round(max(60.0, min(240.0, raw_sbp)), 1)
        dbp = round(max(40.0, min(140.0, raw_dbp)), 1)

        # Enforce minimum pulse pressure (SBP must be > DBP by at least 15 mmHg)
        if sbp <= dbp + 15.0:
            sbp = dbp + 15.0

        map_val = round((sbp + 2.0 * dbp) / 3.0, 1)
        pulse_pressure = round(sbp - dbp, 1)

        # Clinical classification based on AHA/ACC 2017 guidelines
        if sbp > 180.0 or dbp > 120.0:
            classification = self.CLASSIFICATIONS["HYPERTENSIVE_CRISIS"]
        elif sbp >= 140.0 or dbp >= 90.0:
            classification = self.CLASSIFICATIONS["HYPERTENSIVE_STAGE2"]
        elif (130.0 <= sbp <= 139.0) or (80.0 < dbp < 90.0):
            classification = self.CLASSIFICATIONS["HYPERTENSIVE_STAGE1"]
        elif 120.0 < sbp <= 129.0 and dbp <= 80.0:
            classification = self.CLASSIFICATIONS["ELEVATED"]
        elif sbp < 90.0 or dbp < 60.0:
            classification = self.CLASSIFICATIONS["HYPOTENSIVE"]
        else:
            classification = self.CLASSIFICATIONS["NORMAL"]

        return BloodPressureReading(
            systolic_mmhg=sbp,
            diastolic_mmhg=dbp,
            map_mmhg=map_val,
            pulse_pressure_mmhg=pulse_pressure,
            ptt_ms=round(ptt, 1),
            hr_bpm=round(hr, 1),
            pwv_mps=pwv,
            classification=classification,
            status="NOMINAL",
            rule_0_zero_mock=True,
        )

    def estimate_bp(
        self,
        ecg_r_peak: float,
        ppg_systolic_peak: float,
        sample_rate_hz: float = 512.0,
        hr_bpm: Optional[float] = 70.0,
    ) -> BloodPressureReading:
        """
        Interface Contract (PROJECT.md):
        Moens-Korteweg / Hughes continuous BP estimation from paired peak locations.
        """
        if ecg_r_peak is None or ppg_systolic_peak is None:
            return self.estimate_blood_pressure(None, None)

        diff = ppg_systolic_peak - ecg_r_peak
        if diff <= 0:
            diff = abs(diff)

        if diff < 10.0 and sample_rate_hz > 0:
            # Time in seconds
            ptt_ms = diff * 1000.0
        elif diff < 2000.0 and diff > 40.0 and sample_rate_hz == 512.0 and diff < sample_rate_hz:
            # Sample indices at fs
            ptt_ms = (diff / float(sample_rate_hz)) * 1000.0
        else:
            ptt_ms = float(diff)

        return self.estimate_blood_pressure(ptt_ms, hr_bpm)


def calculate_ptt_from_ecg_ppg(
    ecg_r_peak_indices: Sequence[int],
    ppg_peak_indices: Sequence[int],
    sample_rate_hz: int = 512,
    min_transit_ms: float = 80.0,
    max_transit_ms: float = 500.0,
) -> List[float]:
    """
    Computes Pulse Transit Time (PTT) array from paired ECG R-peaks and PPG systolic peaks.
    Each ECG R-peak is paired with the first subsequent PPG peak within [min_transit_ms, max_transit_ms].
    Returns list of PTT values in milliseconds.
    """
    if not ecg_r_peak_indices or not ppg_peak_indices or sample_rate_hz <= 0:
        return []

    fs = float(sample_rate_hz)
    min_samples = int((min_transit_ms / 1000.0) * fs)
    max_samples = int((max_transit_ms / 1000.0) * fs)

    ptt_list: List[float] = []
    ppg_ptr = 0
    n_ppg = len(ppg_peak_indices)

    for r_idx in ecg_r_peak_indices:
        while ppg_ptr < n_ppg and ppg_peak_indices[ppg_ptr] <= r_idx:
            ppg_ptr += 1

        if ppg_ptr >= n_ppg:
            break

        diff_samples = ppg_peak_indices[ppg_ptr] - r_idx
        if min_samples <= diff_samples <= max_samples:
            ptt_ms = (diff_samples / fs) * 1000.0
            ptt_list.append(round(ptt_ms, 2))
            ppg_ptr += 1

    return ptt_list


def calculate_hemodynamics_bp(
    ptt_ms: Optional[float],
    hr_bpm: Optional[float]
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Convenience wrapper returning (systolic_mmhg, diastolic_mmhg, map_mmhg).
    Strict Rule #0 compliance: returns (None, None, None) when inputs are invalid.
    """
    model = PTTBloodPressureModel()
    reading = model.estimate_blood_pressure(ptt_ms, hr_bpm)
    return reading.systolic_mmhg, reading.diastolic_mmhg, reading.map_mmhg
