import json
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class IMUDataPoint:
    timestamp_ms: int
    accel_x: float
    accel_y: float
    accel_z: float
    gyro_x: float
    gyro_y: float
    gyro_z: float
    # Future Phase 2: Heart rate and ECG
    heart_rate_bpm: Optional[int] = None
    ecg_mv: Optional[float] = None

@dataclass
class MovesenseSession:
    session_id: str
    start_time_iso: str
    sample_rate_hz: int
    data_points: List[IMUDataPoint] = field(default_factory=list)

    def to_json(self) -> str:
        # Convert to dictionary and serialize
        # Useful for dumping to Parquet later in the PySpark datalake
        return json.dumps(self, default=lambda o: o.__dict__, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "MovesenseSession":
        data = json.loads(json_str)
        points = [IMUDataPoint(**pt) for pt in data.get("data_points", [])]
        return cls(
            session_id=data["session_id"],
            start_time_iso=data["start_time_iso"],
            sample_rate_hz=data["sample_rate_hz"],
            data_points=points
        )

# Example usage for mock-free testing:
# Real IMU data will stream from L6 (Pixel 10 Pro XL) or L4 (Linux Tablet)
# via Bluetooth PAN and serialize into this schema before fusion with video frames.
