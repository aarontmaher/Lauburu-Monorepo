"""
Movesense Hub Configuration Module.
Defines default hardware parameters, telemetry paths, and physiological baselines.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MovesenseHubConfig:
    """Configuration settings for the Movesense Physiological Readiness Suite."""

    # Hardware & BLE GATT settings
    device_serial: str = "261030002013"
    device_name: str = "Movesense 261030002013"
    device_mac_address: str = "C1DB5043-8F89-88E8-46A3-BBD4ED83FC88"
    default_sample_rate_hz: int = 512
    ecg_sample_rate_hz: int = 512
    imu_sample_rate_hz: int = 52
    ble_timeout_sec: float = 10.0
    reconnect_interval_sec: float = 3.0

    # User physiological baseline parameters
    user_age: int = 30
    hr_rest_baseline: float = 58.0
    user_weight_kg: float = 75.0
    user_height_cm: float = 180.0

    # DSP & algorithm thresholds
    kamath_threshold_pct: float = 20.0
    mwi_window_sec: float = 0.150
    refractory_sec: float = 0.200
    dfa_scale_min: int = 4
    dfa_scale_max: int = 16
    rr_history_max_len: int = 240
    ecg_buffer_window_sec: float = 5.0

    # Telemetry storage paths (Airgapped local storage)
    workspace_root: Path = field(
        default_factory=lambda: Path(os.environ.get("LAUBURU_ROOT", "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"))
    )
    movesense_live_stream_path: Path = field(
        default_factory=lambda: Path(os.environ.get("LAUBURU_ROOT", "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"))
        / "00_core_infrastructure/self_healing_hub/src/movesense_live_stream.json"
    )
    readiness_live_output_path: Path = field(
        default_factory=lambda: Path(os.environ.get("LAUBURU_ROOT", "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"))
        / "03_biometrics_and_telemetry/movesense_readiness_live.json"
    )
    lora_dataset_output_path: Path = field(
        default_factory=lambda: Path(os.environ.get("LAUBURU_ROOT", "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"))
        / "04_data_and_memory/lora_datasets/movesense_readiness_continuous.jsonl"
    )

    @property
    def hr_max(self) -> int:
        """Standard Tanaka / Fox estimation of maximum heart rate."""
        return 220 - self.user_age

    @property
    def lt1_hr_estimate(self) -> int:
        """Heart Rate Reserve (HRR) estimate for LT1 (Aerobic Threshold: 60% HRR)."""
        return int(round(self.hr_rest_baseline + 0.60 * (self.hr_max - self.hr_rest_baseline)))

    @property
    def lt2_hr_estimate(self) -> int:
        """Heart Rate Reserve (HRR) estimate for LT2 (Anaerobic Threshold: 85% HRR)."""
        return int(round(self.hr_rest_baseline + 0.85 * (self.hr_max - self.hr_rest_baseline)))

    @property
    def estimated_vo2max(self) -> float:
        """Uth-Sørensen-Overgaard-Pedersen VO2max estimation from HR ratio."""
        return round(15.3 * (self.hr_max / max(self.hr_rest_baseline, 40.0)), 1)
