"""
Unit tests for Telemetry DSP & Sensor Status Manager in Port 4000 Hub.
Verifies zero-mock status probe (disconnected=false & heart_rate=null),
Kamath 20% artifact filtering, RMSSD calculation, training zone classification,
and stale sensor pruning.
"""

import os
import tempfile
import time
import pytest

from ..services.telemetry_service import (
    TelemetryService,
    apply_kamath_artifact_filter,
    calculate_rmssd,
    classify_training_zone,
    calculate_bp_from_ptt
)
from ..storage.sqlite_manager import SqliteManager


@pytest.fixture
def telemetry_service():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    storage = SqliteManager(db_path=path)
    svc = TelemetryService(sqlite_manager=storage, sensor_timeout_sec=2.0)
    yield svc
    try:
        os.remove(path)
        for ext in ["-wal", "-shm"]:
            if os.path.exists(path + ext):
                os.remove(path + ext)
    except Exception:
        pass


def test_zero_mock_sensor_status_probe(telemetry_service):
    """
    CRITICAL RULE #0: Disconnected sensors strictly return connected=False,
    heart_rate=None (never 0 or fake numbers).
    """
    status = telemetry_service.get_sensor_status()
    assert status["connected_count"] == 0
    assert status["fusion_state"] == "AWAITING_BLUETOOTH_SENSORS"
    assert status["total_supported"] == 4

    for sensor_id, sensor in status["sensors"].items():
        assert sensor["connected"] is False, f"Sensor {sensor_id} must be disconnected initially"
        assert sensor["heart_rate"] is None, f"Sensor {sensor_id} heart_rate must be null when disconnected"
        assert sensor["last_seen_epoch"] is None


def test_kamath_artifact_filtering():
    """Verify Kamath 20% clinical RR artifact filter."""
    # Normal sinus rhythm: ~800ms with small physiological variations
    raw_rr = [800.0, 810.0, 795.0, 1200.0, 805.0, 400.0, 802.0]
    clean_rr, had_artifacts = apply_kamath_artifact_filter(raw_rr)
    assert had_artifacts is True
    # 1200.0 is (+50% jump from 795) -> rejected
    # 400.0 is (-50% drop from 805) -> rejected
    assert 1200.0 not in clean_rr
    assert 400.0 not in clean_rr
    assert clean_rr == [800.0, 810.0, 795.0, 805.0, 802.0]


def test_rmssd_calculation():
    """Verify mathematical calculation of RMSSD."""
    rr = [800.0, 820.0, 810.0, 830.0]
    # diffs: +20, -10, +20
    # squares: 400, 100, 400 -> sum = 900 -> mean = 300 -> sqrt(300) = 17.32
    rmssd = calculate_rmssd(rr)
    assert rmssd == 17.32


def test_training_zone_classification():
    """Verify aerobic zone classification from DFA alpha-1."""
    zone2_name, zone2_col = classify_training_zone(0.85)
    assert "Zone 2" in zone2_name
    assert zone2_col == "#10b981"

    zone3_name, zone3_col = classify_training_zone(0.65)
    assert "Zone 3" in zone3_name
    assert zone3_col == "#f59e0b"

    zone4_name, zone4_col = classify_training_zone(0.40)
    assert "Zone 4/5" in zone4_name
    assert zone4_col == "#ef4444"


def test_blood_pressure_calculation():
    """Verify blood pressure estimation from PTT."""
    sbp, dbp, map_val = calculate_bp_from_ptt(190.0, 140.0)
    assert sbp is not None
    assert dbp is not None
    assert map_val is not None
    assert 100.0 <= sbp <= 160.0
    assert 60.0 <= dbp <= 100.0


@pytest.mark.asyncio
async def test_live_ingest_and_stale_pruning(telemetry_service):
    """Verify ingest updates state and pruning resets disconnected sensors."""
    payload = {
        "sensor_type": "movesense",
        "heart_rate": 142.0,
        "rr_intervals_ms": [422.0, 420.0, 424.0],
        "dfa_alpha1": 0.77,
        "ecg_mv": [1.25, 0.45],
        "acc_g": {"x": 0.05, "y": 0.12, "z": 0.99}
    }

    res = await telemetry_service.ingest_telemetry_payload(payload)
    assert res["status"] == "success"
    assert res["connected_count"] == 1
    assert res["dsp_summary"]["training_zone"] == "Zone 2 (Aerobic Base Endurance)"

    # Probe status after ingest
    status = telemetry_service.get_sensor_status()
    assert status["connected_count"] == 1
    assert status["fusion_state"] == "SINGLE_SENSOR_STREAM"
    assert status["sensors"]["movesense"]["connected"] is True
    assert status["sensors"]["movesense"]["heart_rate"] == 142.0

    # Wait for sensor timeout (>2.0s)
    time.sleep(2.1)
    status_pruned = telemetry_service.get_sensor_status()
    assert status_pruned["connected_count"] == 0
    assert status_pruned["fusion_state"] == "AWAITING_BLUETOOTH_SENSORS"
    assert status_pruned["sensors"]["movesense"]["connected"] is False
    assert status_pruned["sensors"]["movesense"]["heart_rate"] is None
