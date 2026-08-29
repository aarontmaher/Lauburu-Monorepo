"""
Movesense Biometrics Data Models & Interface Contracts.
Defines strong dataclasses and serialization contracts conforming to PROJECT.md § Interface Contracts.
Enforces Rule #0 (Zero-Mock / Disconnected State Invariants).
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


@dataclass
class RawEcgFrame:
    """Raw ECG Sample Frame from Movesense MDS 2.0 or simulator/replay."""
    timestamp_us: int
    sample_rate_hz: int
    samples_mv: List[float] = field(default_factory=list)


@dataclass
class QrsDetectionResult:
    """Pan-Tompkins 1985 QRS detection output."""
    r_peaks: List[int] = field(default_factory=list)
    rr_intervals_ms: List[float] = field(default_factory=list)
    filtered_rr_ms: List[float] = field(default_factory=list)
    artifacts_rejected: int = 0
    hr_bpm: Optional[float] = None
    rmssd_ms: Optional[float] = None
    sample_rate_hz: int = 512
    status: str = "WAITING_FOR_SENSOR"


@dataclass
class PttBloodPressure:
    """Continuous Pulse Transit Time (PTT) Blood Pressure inversion."""
    sbp_mmhg: Optional[float] = None
    dbp_mmhg: Optional[float] = None
    map_mmhg: Optional[float] = None
    ptt_ms: Optional[float] = None
    status: str = "STANDBY"
    method: str = "ECG-PTT Pulse Wave Inversion (100% Local DSP)"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "estimated_ptt_ms": self.ptt_ms,
            "systolic_bp_mmhg": self.sbp_mmhg,
            "diastolic_bp_mmhg": self.dbp_mmhg,
            "mean_arterial_pressure_mmhg": self.map_mmhg,
            "status": self.status,
            "method": self.method,
        }


@dataclass
class SleepStagingResult:
    """Overnight PPG/ECG Sleep Staging & Recovery Score."""
    epoch_stages: List[str] = field(default_factory=list)
    sleep_score_100: Optional[int] = None
    deep_pct: Optional[float] = None
    rem_pct: Optional[float] = None
    light_pct: Optional[float] = None
    awake_pct: Optional[float] = None
    efficiency_pct: Optional[float] = None
    dip_pct: Optional[float] = None
    recovery_status: str = "Awaiting Nocturnal Stream"
    status: str = "WAITING_FOR_SENSOR"

    def to_dict(self) -> Dict[str, Any]:
        stages_estimate = None
        if self.deep_pct is not None or self.rem_pct is not None:
            stages_estimate = {
                "deep_sleep_pct": self.deep_pct,
                "rem_sleep_pct": self.rem_pct,
                "light_sleep_pct": self.light_pct,
                "awake_pct": self.awake_pct,
            }
        return {
            "status": self.status,
            "sleep_score_pct": self.sleep_score_100,
            "recovery_status": self.recovery_status,
            "nocturnal_rmssd_ms": None,
            "nocturnal_hr_bpm": None,
            "nocturnal_dip_pct": self.dip_pct,
            "sleep_stages_estimate": stages_estimate,
        }


@dataclass
class Zone2CardioResult:
    """DFA-alpha1 Aerobic Coaching & Thresholds."""
    dfa_alpha1: Optional[float] = None
    current_zone: str = "Awaiting Live Stream"
    zone_color: str = "#94a3b8"
    lt1_hr: Optional[float] = None
    lt2_hr: Optional[float] = None
    vo2max_ml_kg_min: Optional[float] = None
    physiological_domain: str = "Awaiting Live DFA-alpha1 Stream"
    status: str = "WAITING_FOR_SENSOR"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "estimated_vo2max_ml_kg_min": self.vo2max_ml_kg_min,
            "lt1_aerobic_threshold_bpm": int(self.lt1_hr) if self.lt1_hr is not None else None,
            "lt2_anaerobic_threshold_bpm": int(self.lt2_hr) if self.lt2_hr is not None else None,
            "current_dfa_alpha1": self.dfa_alpha1,
            "physiological_domain": self.physiological_domain,
        }


@dataclass
class WorkoutState:
    """Automatic Activity & Workout Detection."""
    activity_type: Optional[str] = None
    training_zone: str = "Awaiting Sensor Stream"
    hr_pct_max: Optional[float] = None
    status: str = "WAITING_FOR_SENSOR"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "current_activity": self.activity_type,
            "training_zone": self.training_zone,
            "hr_pct_max": self.hr_pct_max,
        }


@dataclass
class ReadinessReport:
    """Full Canonical Physiological Readiness Composite."""
    timestamp_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    status: str = "WAITING_FOR_SENSOR"
    device_name: str = "Movesense 261030002013"
    connected: bool = False
    heart_rate_bpm: Optional[float] = None
    rmssd_ms: Optional[float] = None
    dfa_alpha1: Optional[float] = None
    blood_pressure: PttBloodPressure = field(default_factory=PttBloodPressure)
    sleep_analysis: SleepStagingResult = field(default_factory=SleepStagingResult)
    workout: WorkoutState = field(default_factory=WorkoutState)
    cardiorespiratory: Zone2CardioResult = field(default_factory=Zone2CardioResult)
    rule_0_zero_mock: bool = True

    def to_full_dict(self) -> Dict[str, Any]:
        """Returns standard full readiness payload matching movesense_readiness_live.json."""
        return {
            "timestamp_utc": self.timestamp_utc,
            "status": self.status,
            "sensor_telemetry": {
                "device": self.device_name,
                "connected": self.connected,
                "heart_rate_bpm": int(self.heart_rate_bpm) if self.heart_rate_bpm is not None else None,
                "rmssd_ms": round(self.rmssd_ms, 2) if self.rmssd_ms is not None else None,
                "dfa_alpha1": round(self.dfa_alpha1, 3) if self.dfa_alpha1 is not None else None,
                "stream_mode": "100% STRICT LOCAL AIRGAP BLE",
            },
            "blood_pressure_ptt": self.blood_pressure.to_dict(),
            "overnight_sleep_analysis": self.sleep_analysis.to_dict(),
            "activity_and_workout": self.workout.to_dict(),
            "cardiorespiratory_thresholds": self.cardiorespiratory.to_dict(),
            "rule_0_zero_mock": self.rule_0_zero_mock,
        }

    def to_interface_contract(self) -> Dict[str, Any]:
        """Returns standard PROJECT.md Interface Contract payload for frontend / PWA."""
        if not self.connected or self.heart_rate_bpm is None:
            return {
                "status": "WAITING_FOR_SENSOR",
                "heart_rate_bpm": None,
                "rmssd_ms": None,
                "dfa_alpha1": None,
                "ptt_blood_pressure": {
                    "systolic_bp_mmhg": None,
                    "diastolic_bp_mmhg": None,
                    "map_mmhg": None,
                },
                "sleep_recovery": {
                    "sleep_score_pct": None,
                    "deep_sleep_pct": None,
                    "rem_sleep_pct": None,
                },
                "cardiorespiratory": {
                    "lt1_threshold_bpm": None,
                    "lt2_threshold_bpm": None,
                    "vo2max_estimate": None,
                    "activity_state": None,
                },
            }

        return {
            "status": "STREAMING",
            "heart_rate_bpm": float(self.heart_rate_bpm),
            "rmssd_ms": float(self.rmssd_ms) if self.rmssd_ms is not None else None,
            "dfa_alpha1": float(self.dfa_alpha1) if self.dfa_alpha1 is not None else None,
            "ptt_blood_pressure": {
                "systolic_bp_mmhg": float(self.blood_pressure.sbp_mmhg) if self.blood_pressure.sbp_mmhg is not None else None,
                "diastolic_bp_mmhg": float(self.blood_pressure.dbp_mmhg) if self.blood_pressure.dbp_mmhg is not None else None,
                "map_mmhg": float(self.blood_pressure.map_mmhg) if self.blood_pressure.map_mmhg is not None else None,
            },
            "sleep_recovery": {
                "sleep_score_pct": int(self.sleep_analysis.sleep_score_100) if self.sleep_analysis.sleep_score_100 is not None else None,
                "deep_sleep_pct": float(self.sleep_analysis.deep_pct) if self.sleep_analysis.deep_pct is not None else None,
                "rem_sleep_pct": float(self.sleep_analysis.rem_pct) if self.sleep_analysis.rem_pct is not None else None,
            },
            "cardiorespiratory": {
                "lt1_threshold_bpm": float(self.cardiorespiratory.lt1_hr) if self.cardiorespiratory.lt1_hr is not None else None,
                "lt2_threshold_bpm": float(self.cardiorespiratory.lt2_hr) if self.cardiorespiratory.lt2_hr is not None else None,
                "vo2max_estimate": float(self.cardiorespiratory.vo2max_ml_kg_min) if self.cardiorespiratory.vo2max_ml_kg_min is not None else None,
                "activity_state": self.workout.activity_type,
            },
        }


class BiometricsStateStore:
    """
    Thread-safe and async-friendly in-memory state repository for live biometrics.
    Dispatches state updates to listeners and serializes to disk.
    """

    def __init__(self, persistence_path: Optional[Path] = None, lora_dataset_path: Optional[Path] = None):
        self._lock = threading.RLock()
        self._listeners: List[Callable[[ReadinessReport], None]] = []
        self._report = ReadinessReport()
        self.persistence_path = persistence_path
        self.lora_dataset_path = lora_dataset_path

    def update_report(self, report: ReadinessReport) -> None:
        """Atomically updates the current report and notifies listeners."""
        with self._lock:
            self._report = report
            # Save to disk if configured
            if self.persistence_path:
                try:
                    self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(self.persistence_path, "w") as f:
                        json.dump(report.to_full_dict(), f, indent=2)
                except Exception:
                    pass

            # If streaming, log to continuous LoRA dataset
            if report.connected and report.heart_rate_bpm is not None and self.lora_dataset_path:
                try:
                    sample = {
                        "instruction": "Analyze live 512Hz bicep ECG, PTT blood pressure, sleep readiness, and cardiorespiratory thresholds to output medical-grade physiological coaching.",
                        "input": json.dumps({
                            "hr": report.heart_rate_bpm,
                            "rmssd": report.rmssd_ms,
                            "dfa_alpha1": report.dfa_alpha1,
                        }),
                        "output": json.dumps({
                            "blood_pressure": f"{report.blood_pressure.sbp_mmhg}/{report.blood_pressure.dbp_mmhg} mmHg",
                            "sleep_score": f"{report.sleep_analysis.sleep_score_100}/100",
                            "activity": report.workout.training_zone,
                            "vo2max": f"{report.cardiorespiratory.vo2max_ml_kg_min} mL/kg/min",
                            "domain": report.cardiorespiratory.physiological_domain,
                        }),
                        "metadata": {"rule_0_verified": True, "local_airgap": True},
                    }
                    self.lora_dataset_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(self.lora_dataset_path, "a") as f:
                        f.write(json.dumps(sample) + "\n")
                except Exception:
                    pass

            listeners = list(self._listeners)

        for cb in listeners:
            try:
                cb(report)
            except Exception:
                pass

    def get_report(self) -> ReadinessReport:
        with self._lock:
            return self._report

    def get_interface_contract(self) -> Dict[str, Any]:
        with self._lock:
            return self._report.to_interface_contract()

    def add_listener(self, callback: Callable[[ReadinessReport], None]) -> None:
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[ReadinessReport], None]) -> None:
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)
