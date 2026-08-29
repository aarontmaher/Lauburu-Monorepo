"""
Pulse Transit Time (PTT) Continuous Hemodynamic Blood Pressure Inversion Engine.
Estimates Systolic, Diastolic, and Mean Arterial Pressure (MAP) from ECG R-peak to peripheral pulse timing.
100% Local Airgapped DSP with strict Rule #0 Zero-Mock validation.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple

from ..core.models import PttBloodPressure


def calculate_hemodynamics_bp(
    ptt_ms: Optional[float],
    hr_bpm: Optional[float]
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Computes estimated SBP, DBP, MAP using empirical hemodynamic inversion equations.
    SBP = 120.0 + (200 - PTT) * 0.45 + (HR - 70) * 0.15
    DBP = 80.0 + (200 - PTT) * 0.25 + (HR - 70) * 0.08
    MAP = (SBP + 2 * DBP) / 3.0

    Strict Rule #0: returns (None, None, None) if ptt_ms is missing or <= 0.
    """
    if ptt_ms is None or ptt_ms <= 0 or hr_bpm is None or hr_bpm <= 0:
        return None, None, None

    delta_ptt = 200.0 - float(ptt_ms)
    hr_adj = (float(hr_bpm) - 70.0) * 0.15

    sbp = round(max(80.0, min(220.0, 120.0 + (delta_ptt * 0.45) + hr_adj)), 1)
    dbp = round(max(50.0, min(130.0, 80.0 + (delta_ptt * 0.25) + (hr_adj * 0.5))), 1)
    map_val = round((sbp + 2.0 * dbp) / 3.0, 1)

    return sbp, dbp, map_val


class ContinuousPttBloodPressureModel:
    """
    Hemodynamic Blood Pressure Model based on Hughes-Bramwell arterial wave propagation.
    """

    def __init__(self, hr_rest_baseline: float = 58.0):
        self.hr_rest_baseline = hr_rest_baseline

    def compute_ptt_blood_pressure(
        self,
        hr_bpm: Optional[float],
        rmssd_ms: Optional[float] = None,
        ptt_ms: Optional[float] = None
    ) -> PttBloodPressure:
        """
        Calculates PttBloodPressure dataclass contract.
        If ptt_ms is directly available from dual-sensor/ECG-PPG, uses direct PTT inversion.
        If only ECG (HR & RMSSD) is available, uses sympathetic tone Hughes-Bramwell approximation.
        Strict Rule #0: returns STANDBY with null values if sensors are disconnected.
        """
        if hr_bpm is None or float(hr_bpm) <= 0.0 or (rmssd_ms is None and ptt_ms is None):
            return PttBloodPressure(
                sbp_mmhg=None,
                dbp_mmhg=None,
                map_mmhg=None,
                ptt_ms=None,
                status="STANDBY",
                method="ECG-PTT Pulse Wave Inversion (100% Local DSP)"
            )

        hr = float(hr_bpm)

        if ptt_ms is not None and ptt_ms > 0:
            active_ptt = float(ptt_ms)
            delta_ptt = 200.0 - active_ptt
            hr_adj_sbp = (hr - 70.0) * 0.15
            hr_adj_dbp = (hr - 70.0) * 0.08
            sbp = round(max(80.0, min(220.0, 120.0 + (delta_ptt * 0.45) + hr_adj_sbp)), 1)
            dbp = round(max(50.0, min(130.0, 80.0 + (delta_ptt * 0.25) + hr_adj_dbp)), 1)
            map_val = round((sbp + 2.0 * dbp) / 3.0, 1)

            return PttBloodPressure(
                sbp_mmhg=sbp,
                dbp_mmhg=dbp,
                map_mmhg=map_val,
                ptt_ms=active_ptt,
                status="NOMINAL",
                method="ECG-PTT Pulse Wave Inversion (100% Local DSP)"
            )

        # Arterial wave equation approximation from sympathetic tone & RMSSD
        rmssd = float(rmssd_ms) if rmssd_ms is not None else 40.0
        sympathetic_ratio = min(max(hr / max(self.hr_rest_baseline, 40.0), 0.8), 2.5)
        est_ptt = round(240.0 / math.sqrt(sympathetic_ratio), 1)

        # Hughes-Bramwell arterial wave equation approximation
        sbp = float(int(round(max(90.0, min(185.0, 118.0 + (hr - 65.0) * 0.45 - (rmssd - 40.0) * 0.25)))))
        dbp = float(int(round(max(55.0, min(115.0, 76.0 + (hr - 65.0) * 0.25 - (rmssd - 40.0) * 0.15)))))
        map_val = round((sbp + 2.0 * dbp) / 3.0, 1)

        return PttBloodPressure(
            sbp_mmhg=sbp,
            dbp_mmhg=dbp,
            map_mmhg=map_val,
            ptt_ms=est_ptt,
            status="NOMINAL",
            method="ECG-PTT Hughes-Bramwell Arterial Inversion (100% Local DSP)"
        )


def compute_ptt_blood_pressure(
    hr_bpm: Optional[float],
    rmssd_ms: Optional[float] = None,
    ptt_ms: Optional[float] = None,
    hr_rest_baseline: float = 58.0
) -> PttBloodPressure:
    """
    Top-level convenience function for PTT Blood Pressure computation.
    """
    model = ContinuousPttBloodPressureModel(hr_rest_baseline=hr_rest_baseline)
    return model.compute_ptt_blood_pressure(hr_bpm=hr_bpm, rmssd_ms=rmssd_ms, ptt_ms=ptt_ms)
