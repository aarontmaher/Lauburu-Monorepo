"""
DSP Subpackage for Movesense Hub.
Contains Pan-Tompkins 512Hz/128Hz QRS detection, Kamath 2004 20% RR filter, microsecond RMSSD,
DFA-alpha1 aerobic analysis, continuous PTT blood pressure, overnight sleep staging, and Zone 2 coaching.
"""

from .hemodynamics_bp import (
    ContinuousPttBloodPressureModel,
    calculate_hemodynamics_bp,
)
from .pan_tompkins import (
    MovesenseECGPipeline,
    PanTompkinsQRSDetector,
    apply_kamath_artifact_filter,
    apply_kamath_filter,
    calculate_dfa_alpha1,
    calculate_rmssd,
)
from .sleep_scoring import (
    SleepStagingEngine,
    classify_sleep_epoch,
    compute_overnight_sleep_analysis,
)
from .zone2_coaching import (
    Zone2CoachingEngine,
    classify_workout_state,
    classify_zone2_alignment,
    compute_cardiorespiratory_thresholds,
)

__all__ = [
    "PanTompkinsQRSDetector",
    "MovesenseECGPipeline",
    "apply_kamath_artifact_filter",
    "apply_kamath_filter",
    "calculate_rmssd",
    "calculate_dfa_alpha1",
    "calculate_hemodynamics_bp",
    "ContinuousPttBloodPressureModel",
    "SleepStagingEngine",
    "classify_sleep_epoch",
    "compute_overnight_sleep_analysis",
    "Zone2CoachingEngine",
    "classify_zone2_alignment",
    "classify_workout_state",
    "compute_cardiorespiratory_thresholds",
]
