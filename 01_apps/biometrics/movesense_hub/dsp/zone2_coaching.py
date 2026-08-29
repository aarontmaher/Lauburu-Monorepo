"""
Zone 2 Aerobic Base Coaching & Cardiorespiratory Thresholds Engine.
Implements:
1. DFA-alpha1 Aerobic / Anaerobic Domain Mapping (LT1 @ 0.75, LT2 @ 0.50)
2. Automatic Workout & Activity Detection (% HRmax classification)
3. Uth-Sørensen-Overgaard-Pedersen VO2max Estimation
4. Heart Rate Reserve (HRR) Karvonen LT1 & LT2 Thresholds
5. Strict Rule #0 Zero-Mock validation.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from ..core.models import WorkoutState, Zone2CardioResult


def classify_zone2_alignment(dfa_alpha1: Optional[float]) -> Tuple[str, str]:
    """
    Maps DFA-alpha1 scaling exponent to aerobic training zone and color.
    """
    if dfa_alpha1 is None:
        return "Awaiting Live Stream", "#94a3b8"
    if dfa_alpha1 >= 0.75:
        return "Zone 2 (Aerobic Base Endurance)", "#10b981"
    elif dfa_alpha1 >= 0.50:
        return "Zone 3 (Tempo / Aerobic Power)", "#f59e0b"
    else:
        return "Zone 4/5 (Anaerobic Threshold / Fatigue)", "#ef4444"


def classify_workout_state(
    hr_bpm: Optional[float],
    hr_max: int = 190
) -> WorkoutState:
    """
    Automatically detects current physical activity and training zone based on % HRmax.
    Strict Rule #0: returns null metrics and WAITING_FOR_SENSOR if hr_bpm is None.
    """
    if hr_bpm is None or float(hr_bpm) <= 0.0 or hr_max is None or int(hr_max) <= 0:
        return WorkoutState(
            activity_type=None,
            training_zone="Awaiting Sensor Stream",
            hr_pct_max=None,
            status="WAITING_FOR_SENSOR"
        )

    effective_hr_max = max(60, int(hr_max))
    pct_max = (float(hr_bpm) / float(effective_hr_max)) * 100.0
    if pct_max < 55.0:
        zone = "Rest / Passive Recovery"
        activity = "RESTING"
    elif pct_max < 72.0:
        zone = "Zone 2 (Aerobic Base / Fat Oxidation)"
        activity = "STEADY_CARDIO_ZONE_2"
    elif pct_max < 85.0:
        zone = "Zone 3 (Tempo / Aerobic Power)"
        activity = "TEMPO_TRAINING"
    elif pct_max < 92.0:
        zone = "Zone 4 (Threshold / Lactate Build)"
        activity = "HIIT_INTERVALS"
    else:
        zone = "Zone 5 (Neuromuscular / VO2max)"
        activity = "MAXIMAL_EFFORT_GRAPPLING"

    return WorkoutState(
        activity_type=activity,
        training_zone=zone,
        hr_pct_max=round(pct_max, 1),
        status="ACTIVE"
    )


def compute_cardiorespiratory_thresholds(
    hr_bpm: Optional[float],
    dfa_alpha1: Optional[float],
    hr_max: int = 190,
    hr_rest_baseline: float = 58.0
) -> Zone2CardioResult:
    """
    Computes LT1 (Aerobic Threshold), LT2 (Anaerobic Threshold), and VO2max.
    LT1 corresponds to DFA-alpha1 = 0.75; LT2 corresponds to DFA-alpha1 = 0.50.
    VO2max estimation via Uth-Sørensen formula: 15.3 * (HR_max / HR_rest).
    Strict Rule #0: returns WAITING_FOR_SENSOR if inputs are None.
    """
    effective_hr_max = max(60, int(hr_max)) if (hr_max is not None and int(hr_max) > 0) else 190
    effective_hr_rest = max(40.0, float(hr_rest_baseline)) if (hr_rest_baseline is not None and float(hr_rest_baseline) > 0.0) else 58.0
    vo2_max_ml_kg_min = round(15.3 * (effective_hr_max / effective_hr_rest), 1)
    lt1_hr_estimate = int(round(effective_hr_rest + 0.60 * (effective_hr_max - effective_hr_rest)))
    lt2_hr_estimate = int(round(effective_hr_rest + 0.85 * (effective_hr_max - effective_hr_rest)))

    if dfa_alpha1 is None:
        physio_state = "Awaiting Live DFA-alpha1 Stream"
        status = "WAITING_FOR_SENSOR" if hr_bpm is None else "ACTIVE_NO_DFA"
        zone_desc, zone_color = "Awaiting Live Stream", "#94a3b8"
    else:
        alpha = float(dfa_alpha1)
        status = "ACTIVE"
        zone_desc, zone_color = classify_zone2_alignment(alpha)
        if alpha >= 0.85:
            physio_state = "Below LT1 (Aerobic Recovery / Low Systemic Stress)"
        elif alpha >= 0.70:
            physio_state = "At LT1 Aerobic Threshold (Optimal Zone 2 Fat Max)"
        elif alpha >= 0.50:
            physio_state = "Between LT1 and LT2 (Moderate Lactate Accumulation)"
        else:
            physio_state = "Above LT2 (Severe Acidosis / Anaerobic Domain)"

    return Zone2CardioResult(
        dfa_alpha1=round(float(dfa_alpha1), 3) if dfa_alpha1 is not None else None,
        current_zone=zone_desc,
        zone_color=zone_color,
        lt1_hr=float(lt1_hr_estimate),
        lt2_hr=float(lt2_hr_estimate),
        vo2max_ml_kg_min=vo2_max_ml_kg_min,
        physiological_domain=physio_state,
        status=status
    )


class Zone2CoachingEngine:
    """
    Engine for pacing, aerobic base coaching, and real-time biofeedback.
    """

    def __init__(self, user_age: int = 30, hr_rest_baseline: float = 58.0):
        self.user_age = user_age
        self.hr_max = 220 - user_age
        self.hr_rest_baseline = hr_rest_baseline

    def get_coaching_recommendation(
        self,
        hr_bpm: Optional[float],
        dfa_alpha1: Optional[float]
    ) -> Dict[str, Any]:
        """
        Generates real-time pacing advice based on DFA-alpha1 and target Zone 2 range.
        """
        if hr_bpm is None:
            return {
                "recommendation": "Wear Movesense sensor to begin Zone 2 pacing.",
                "action": "STANDBY",
                "target_hr_range": f"{self.hr_rest_baseline + 0.55*(self.hr_max - self.hr_rest_baseline):.0f}-{self.hr_rest_baseline + 0.72*(self.hr_max - self.hr_rest_baseline):.0f} BPM"
            }

        if dfa_alpha1 is None or dfa_alpha1 >= 0.85:
            return {
                "recommendation": "Pace is very comfortable. You can slightly increase intensity while staying aerobic.",
                "action": "MAINTAIN_OR_INCREASE",
                "target_hr_range": f"{self.hr_rest_baseline + 0.60*(self.hr_max - self.hr_rest_baseline):.0f} BPM"
            }
        elif dfa_alpha1 >= 0.75:
            return {
                "recommendation": "Optimal Zone 2 Aerobic Base. Excellent mitochondrial fat oxidation.",
                "action": "PERFECT_PACE",
                "target_hr_range": f"{self.hr_rest_baseline + 0.65*(self.hr_max - self.hr_rest_baseline):.0f} BPM"
            }
        elif dfa_alpha1 >= 0.60:
            return {
                "recommendation": "Approaching aerobic threshold (LT1). Ease off pace 5-10% to remain in Zone 2.",
                "action": "EASE_PACE",
                "target_hr_range": f"{self.hr_rest_baseline + 0.60*(self.hr_max - self.hr_rest_baseline):.0f} BPM"
            }
        else:
            return {
                "recommendation": "Above LT2 Anaerobic Threshold. Lactate is accumulating. Reduce pace immediately.",
                "action": "REDUCE_PACE_NOW",
                "target_hr_range": f"{self.hr_rest_baseline + 0.50*(self.hr_max - self.hr_rest_baseline):.0f} BPM"
            }
