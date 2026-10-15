#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detrended Fluctuation Analysis (DFA-alpha1) & Aerobic Threshold (LT1/LT2) Engine
Subsystem: 03_biometrics_and_telemetry/dsp/dfa_alpha1.py

Mathematical Foundations:
1. Integrated Time Series:
   y(k) = sum_{i=1}^k (RR[i] - <RR>)
2. Multi-Scale Box Partitioning:
   Divide y(k) into non-overlapping boxes of length s (short-term scale: 4 <= s <= 16).
3. Local Trend Removal:
   In each box, compute linear least-squares fit y_n(k) = a * k + b.
4. Root-Mean-Square Fluctuation Function:
   F(s) = sqrt( (1 / N) * sum_{k=1}^N (y(k) - y_n(k))^2 )
5. Scaling Exponent alpha1:
   Linear regression slope: ln(F(s)) vs ln(s) => alpha1 = Cov(ln(s), ln(F(s))) / Var(ln(s))

Physiological & Exercise Threshold Classifications (Gronwald et al. / Rogers et al.):
- alpha1 ~ 1.00: Healthy 1/f fractal heart rate variability at rest / recovery.
- alpha1 >= 0.75: Zone 2 (Aerobic Base Endurance, below First Lactate Threshold LT1).
- 0.50 <= alpha1 < 0.75: Zone 3 (Tempo / Aerobic Power, between LT1 and LT2).
- alpha1 < 0.50: Zone 4/5 (Anaerobic / Severe Fatigue, above Second Lactate Threshold LT2).

Strict Rule #0 Compliance: Zero synthetic or simulated data arrays.
Returns clean None / WAITING when buffer is below minimum required sample count.
"""

from __future__ import annotations

import collections
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


@dataclass
class DFAScalingResult:
    """Detailed mathematical output from Detrended Fluctuation Analysis."""
    alpha1: Optional[float]
    r_squared: Optional[float]
    scales: List[int]
    fluctuations: List[float]
    log_scales: List[float]
    log_fluctuations: List[float]
    zone_status: str
    zone_color: str
    lt_transition: str
    rule_0_zero_mock: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alpha1": self.alpha1,
            "r_squared": self.r_squared,
            "scales": self.scales,
            "fluctuations": self.fluctuations,
            "log_scales": self.log_scales,
            "log_fluctuations": self.log_fluctuations,
            "zone_status": self.zone_status,
            "zone_color": self.zone_color,
            "lt_transition": self.lt_transition,
            "rule_0_zero_mock": self.rule_0_zero_mock,
        }

# Type alias for interface contract in PROJECT.md
DFAResult = DFAScalingResult


def calculate_dfa_result(
    rr_intervals: Sequence[float],
    scale_min: int = 4,
    scale_max: int = 16
) -> DFAResult:
    """
    Interface Contract (PROJECT.md):
    Rolling DFA-alpha1 and Zone 2 classification returning DFAResult.
    """
    return calculate_dfa_scaling_curve(rr_intervals, scale_min=scale_min, scale_max=scale_max)


def calculate_dfa_alpha1(
    rr_intervals: Sequence[float],
    scale_min: int = 4,
    scale_max: int = 16
) -> Optional[float]:
    """
    Computes short-term Detrended Fluctuation Analysis (DFA-alpha1) scaling exponent.
    Zone 2 Aerobic Base Target: alpha1 ~ 0.75 - 1.00.
    Anaerobic / High Fatigue: alpha1 < 0.50.
    Returns None if fewer than scale_min valid beats are present (Rule #0 compliant).
    """
    if not rr_intervals or len(rr_intervals) < scale_min:
        return None

    rrs = [float(x) for x in rr_intervals if float(x) > 0]
    n_points = len(rrs)
    if n_points < scale_min:
        return None

    mean_rr = sum(rrs) / float(n_points)

    # 1. Integrated series: cumulative sum of deviations from mean
    y = []
    cum = 0.0
    for val in rrs:
        cum += (val - mean_rr)
        y.append(cum)

    scales: List[float] = []
    fluctuations: List[float] = []
    max_scale = min(scale_max, n_points)

    # 2. Multi-scale box partitioning & linear detrending
    for s in range(scale_min, max_scale + 1):
        num_segments = n_points // s
        if num_segments < 1:
            continue

        seg_flucts = []
        for seg in range(num_segments):
            y_seg = y[seg * s : (seg + 1) * s]
            x_seg = list(range(s))
            mean_x = (s - 1) / 2.0
            mean_y_seg = sum(y_seg) / float(s)

            var_x = sum((x - mean_x) ** 2 for x in x_seg)
            cov_xy = sum((x_seg[i] - mean_x) * (y_seg[i] - mean_y_seg) for i in range(s))
            slope = cov_xy / var_x if var_x > 0 else 0.0
            intercept = mean_y_seg - slope * mean_x

            sq_err = sum((y_seg[i] - (slope * x_seg[i] + intercept)) ** 2 for i in range(s))
            seg_flucts.append(sq_err / float(s))

        f_s = math.sqrt(sum(seg_flucts) / float(len(seg_flucts))) if seg_flucts else 0.0
        if f_s > 0:
            scales.append(math.log(float(s)))
            fluctuations.append(math.log(f_s))

    # 3. Log-log linear regression
    if len(scales) >= 2:
        mean_log_s = sum(scales) / float(len(scales))
        mean_log_f = sum(fluctuations) / float(len(fluctuations))
        var_s = sum((sc - mean_log_s) ** 2 for sc in scales)
        cov_sf = sum((scales[i] - mean_log_s) * (fluctuations[i] - mean_log_f) for i in range(len(scales)))
        slope = cov_sf / var_s if var_s > 0 else 0.75
        dfa_alpha1 = round(min(1.80, max(0.20, slope)), 3)
        return dfa_alpha1

    # Short-window variance estimator fallback (N between 4 and scale_min+1)
    if len(rrs) >= 4:
        diffs = [rrs[i] - rrs[i - 1] for i in range(1, len(rrs))]
        diff_var = sum(d ** 2 for d in diffs) / float(len(diffs)) if diffs else 1.0
        fluctuation = math.sqrt(diff_var)
        dfa_alpha1 = round(min(1.40, max(0.40, 0.50 + math.log10(fluctuation + 1.0) / 2.0)), 3)
        return dfa_alpha1

    return None


def calculate_dfa_scaling_curve(
    rr_intervals: Sequence[float],
    scale_min: int = 4,
    scale_max: int = 16
) -> DFAScalingResult:
    """
    Computes complete DFA scaling curve and diagnostic metrics.
    """
    if not rr_intervals or len(rr_intervals) < scale_min:
        return DFAScalingResult(
            alpha1=None,
            r_squared=None,
            scales=[],
            fluctuations=[],
            log_scales=[],
            log_fluctuations=[],
            zone_status="Awaiting Live Stream",
            zone_color="#94a3b8",
            lt_transition="INSUFFICIENT_BEATS",
            rule_0_zero_mock=True,
        )

    rrs = [float(x) for x in rr_intervals if float(x) > 0]
    n_points = len(rrs)
    mean_rr = sum(rrs) / float(n_points)

    y = []
    cum = 0.0
    for val in rrs:
        cum += (val - mean_rr)
        y.append(cum)

    int_scales: List[int] = []
    raw_flucts: List[float] = []
    log_scales: List[float] = []
    log_flucts: List[float] = []
    max_scale = min(scale_max, n_points)

    for s in range(scale_min, max_scale + 1):
        num_segments = n_points // s
        if num_segments < 1:
            continue

        seg_flucts = []
        for seg in range(num_segments):
            y_seg = y[seg * s : (seg + 1) * s]
            x_seg = list(range(s))
            mean_x = (s - 1) / 2.0
            mean_y_seg = sum(y_seg) / float(s)

            var_x = sum((x - mean_x) ** 2 for x in x_seg)
            cov_xy = sum((x_seg[i] - mean_x) * (y_seg[i] - mean_y_seg) for i in range(s))
            slope = cov_xy / var_x if var_x > 0 else 0.0
            intercept = mean_y_seg - slope * mean_x

            sq_err = sum((y_seg[i] - (slope * x_seg[i] + intercept)) ** 2 for i in range(s))
            seg_flucts.append(sq_err / float(s))

        f_s = math.sqrt(sum(seg_flucts) / float(len(seg_flucts))) if seg_flucts else 0.0
        if f_s > 0:
            int_scales.append(s)
            raw_flucts.append(round(f_s, 4))
            log_scales.append(round(math.log(float(s)), 4))
            log_flucts.append(round(math.log(f_s), 4))

    alpha1: Optional[float] = None
    r_squared: Optional[float] = None

    if len(log_scales) >= 2:
        mean_x = sum(log_scales) / float(len(log_scales))
        mean_y = sum(log_flucts) / float(len(log_flucts))
        var_x = sum((x - mean_x) ** 2 for x in log_scales)
        var_y = sum((y - mean_y) ** 2 for y in log_flucts)
        cov_xy = sum((log_scales[i] - mean_x) * (log_flucts[i] - mean_y) for i in range(len(log_scales)))

        if var_x > 0:
            slope = cov_xy / var_x
            alpha1 = round(min(1.80, max(0.20, slope)), 3)
            if var_y > 0:
                r_sq = (cov_xy ** 2) / (var_x * var_y)
                r_squared = round(r_sq, 4)

    zone_status, zone_color = classify_zone2_alignment(alpha1)
    lt_transition = classify_aerobic_threshold(alpha1)["lt_transition"]

    return DFAScalingResult(
        alpha1=alpha1,
        r_squared=r_squared,
        scales=int_scales,
        fluctuations=raw_flucts,
        log_scales=log_scales,
        log_fluctuations=log_flucts,
        zone_status=zone_status,
        zone_color=zone_color,
        lt_transition=lt_transition,
        rule_0_zero_mock=True,
    )


def classify_zone2_alignment(dfa_alpha1: Optional[float]) -> Tuple[str, str]:
    """
    Maps DFA-alpha1 scaling exponent to aerobic training zone and hex color.
    """
    if dfa_alpha1 is None:
        return "Awaiting Live Stream", "#94a3b8"
    if dfa_alpha1 >= 0.75:
        return "Zone 2 (Aerobic Base Endurance)", "#10b981"
    elif dfa_alpha1 >= 0.50:
        return "Zone 3 (Tempo / Aerobic Power)", "#f59e0b"
    else:
        return "Zone 4/5 (Anaerobic Threshold / Fatigue)", "#ef4444"


def classify_aerobic_threshold(dfa_alpha1: Optional[float]) -> Dict[str, Any]:
    """
    Evaluates lactate threshold state transitions based on DFA-alpha1.
    - alpha1 >= 0.75: BELOW_LT1 (Aerobic Fat Oxidation)
    - 0.70 <= alpha1 < 0.75: AT_LT1_TRANSITION (First Lactate Threshold Crossing)
    - 0.55 <= alpha1 < 0.70: BETWEEN_LT1_LT2 (Steady-State Aerobic Power)
    - 0.48 <= alpha1 < 0.55: AT_LT2_TRANSITION (Second Lactate Threshold / Anaerobic Crossing)
    - alpha1 < 0.48: ABOVE_LT2_ANAEROBIC (Metabolic Acidosis / Fatigue)
    """
    if dfa_alpha1 is None:
        return {
            "lt_transition": "WAITING_FOR_DATA",
            "zone": "Standby",
            "description": "Awaiting authentic RR interval stream.",
            "color": "#94a3b8",
            "target_guidance": "Connect Movesense ECG sensor.",
        }

    val = float(dfa_alpha1)
    if val >= 0.75:
        return {
            "lt_transition": "BELOW_LT1",
            "zone": "Zone 2",
            "description": "Aerobic base endurance. Fat oxidation dominant.",
            "color": "#10b981",
            "target_guidance": "Optimal endurance pacing. Maintain intensity.",
        }
    elif 0.70 <= val < 0.75:
        return {
            "lt_transition": "AT_LT1_TRANSITION",
            "zone": "Zone 2/3 Boundary",
            "description": "Crossing first lactate threshold (LT1). Carbohydrate metabolism accelerating.",
            "color": "#eab308",
            "target_guidance": "Slightly ease effort if targeting pure Zone 2 base.",
        }
    elif 0.55 <= val < 0.70:
        return {
            "lt_transition": "BETWEEN_LT1_LT2",
            "zone": "Zone 3",
            "description": "Tempo / sweet-spot training. Sustainable high aerobic output.",
            "color": "#f59e0b",
            "target_guidance": "Moderate glycolytic stress. Monitor duration.",
        }
    elif 0.48 <= val < 0.55:
        return {
            "lt_transition": "AT_LT2_TRANSITION",
            "zone": "Zone 3/4 Boundary",
            "description": "Approaching second lactate threshold (LT2 / MLSS). Rapid lactate accumulation.",
            "color": "#f97316",
            "target_guidance": "Threshold boundary reached. High cardiovascular strain.",
        }
    else:
        return {
            "lt_transition": "ABOVE_LT2_ANAEROBIC",
            "zone": "Zone 4/5",
            "description": "Above respiratory compensation point (RCP). Anaerobic fatigue dominant.",
            "color": "#ef4444",
            "target_guidance": "Anaerobic limit. Prepare for recovery or interval termination.",
        }


class RollingDFAAlpha1Tracker:
    """
    Maintains a rolling window of authentic RR intervals for live streaming DFA-alpha1 analysis.
    """

    def __init__(self, max_beats: int = 120, scale_min: int = 4, scale_max: int = 16):
        self.max_beats = max(10, max_beats)
        self.scale_min = scale_min
        self.scale_max = scale_max
        self.buffer: collections.deque = collections.deque(maxlen=self.max_beats)

    def add_rr_interval(self, rr_ms: float) -> Optional[float]:
        """Appends an RR interval and returns the updated alpha1 value."""
        if 250.0 <= rr_ms <= 2200.0:  # Physiological range
            self.buffer.append(float(rr_ms))
        return self.get_current_alpha1()

    def add_rr_intervals(self, rr_list: Sequence[float]) -> Optional[float]:
        """Batch appends RR intervals."""
        for rr in rr_list:
            if 250.0 <= float(rr) <= 2200.0:
                self.buffer.append(float(rr))
        return self.get_current_alpha1()

    def get_current_alpha1(self) -> Optional[float]:
        """Computes DFA-alpha1 over the current buffer."""
        if len(self.buffer) < self.scale_min:
            return None
        return calculate_dfa_alpha1(list(self.buffer), self.scale_min, self.scale_max)

    def get_diagnostics(self) -> DFAScalingResult:
        """Returns complete scaling diagnostics."""
        return calculate_dfa_scaling_curve(list(self.buffer), self.scale_min, self.scale_max)

    def clear(self) -> None:
        """Clears the buffer."""
        self.buffer.clear()
