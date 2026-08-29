"""
Movesense Physiological Readiness & Biometrics Hub.
===================================================
Subsystem: 01_apps/biometrics/movesense_hub
Version: 1.0.0-CANONICAL
100% Strict Local Airgap Protected Biometrics DSP & Presentation Suite.

Sub-packages:
- core: Config, data models, state store, interface contracts
- dsp: 512Hz/128Hz Pan-Tompkins QRS, Kamath 2004 20% filter, RMSSD, DFA-alpha1, PTT BP, Sleep Staging, VO2max
- transport: Bleak GATT daemon (Movesense 261030002013), Web Bluetooth bridge
- presentation: Native Textual TUI HUD, Web-TUI adapter (/readiness), Next.js Canvas Oscilloscope PWA
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from .core import (
    BiometricsStateStore,
    MovesenseHubConfig,
    PttBloodPressure,
    QrsDetectionResult,
    RawEcgFrame,
    ReadinessReport,
    SleepStagingResult,
    WorkoutState,
    Zone2CardioResult,
)
from .dsp import (
    ContinuousPttBloodPressureModel,
    MovesenseECGPipeline,
    PanTompkinsQRSDetector,
    SleepStagingEngine,
    Zone2CoachingEngine,
    apply_kamath_artifact_filter,
    apply_kamath_filter,
    calculate_dfa_alpha1,
    calculate_hemodynamics_bp,
    calculate_rmssd,
    classify_sleep_epoch,
    classify_workout_state,
    classify_zone2_alignment,
    compute_cardiorespiratory_thresholds,
    compute_overnight_sleep_analysis,
)
from .presentation import (
    MovesenseReadinessTUIApp,
    OscilloscopePwaConnector,
    ReadinessRestAdapter,
    WebTuiAdapter,
    run_app,
)
from .transport import (
    MovesenseBleakDaemon,
    WebBleBridge,
    decode_movesense_ecg_packet,
    decode_sig_heart_rate_measurement,
)

__version__ = "1.0.0"

__all__ = [
    "__version__",
    # Core
    "MovesenseHubConfig",
    "RawEcgFrame",
    "QrsDetectionResult",
    "PttBloodPressure",
    "SleepStagingResult",
    "Zone2CardioResult",
    "WorkoutState",
    "ReadinessReport",
    "BiometricsStateStore",
    # DSP
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
    # Transport
    "MovesenseBleakDaemon",
    "WebBleBridge",
    "decode_sig_heart_rate_measurement",
    "decode_movesense_ecg_packet",
    # Presentation
    "MovesenseReadinessTUIApp",
    "run_app",
    "WebTuiAdapter",
    "OscilloscopePwaConnector",
    "ReadinessRestAdapter",
    # Convenience functions
    "create_hub",
    "process_raw_ecg",
    "get_readiness_contract",
]


def create_hub(
    config: Optional[MovesenseHubConfig] = None
) -> Tuple[BiometricsStateStore, MovesenseECGPipeline, WebBleBridge]:
    """
    Initializes and wires the full Movesense Hub subsystem.
    """
    cfg = config or MovesenseHubConfig()
    state_store = BiometricsStateStore(
        persistence_path=cfg.readiness_live_output_path,
        lora_dataset_path=cfg.lora_dataset_output_path,
    )
    pipeline = MovesenseECGPipeline(sample_rate_hz=cfg.ecg_sample_rate_hz)
    bridge = WebBleBridge(config=cfg, state_store=state_store)
    return state_store, pipeline, bridge


def process_raw_ecg(
    samples_mv: Sequence[float],
    sample_rate_hz: int = 512,
    ptt_ms: Optional[float] = None,
    device_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Top-level convenience function to process an ECG sample window through Pan-Tompkins DSP.
    """
    pipe = MovesenseECGPipeline(sample_rate_hz=sample_rate_hz)
    return pipe.process_raw_ecg_window(samples_mv, ptt_ms=ptt_ms, device_id=device_id)


def get_readiness_contract(report: Optional[ReadinessReport] = None) -> Dict[str, Any]:
    """
    Returns standard PROJECT.md Interface Contract payload.
    """
    rep = report or ReadinessReport()
    return rep.to_interface_contract()
