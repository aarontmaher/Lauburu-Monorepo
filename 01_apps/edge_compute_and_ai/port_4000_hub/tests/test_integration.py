"""
End-to-End Integration Tests for Port 4000 Canonical Web & Compute Hub.
Exercises account registration, Shopify verification, continuous 128Hz Movesense
telemetry streaming, trend insights, and sensor status validation.
"""

import os
import tempfile
import time
import pytest
from fastapi.testclient import TestClient

from ..server import app
from ..storage.sqlite_manager import get_sqlite_manager
from ..services.telemetry_service import get_telemetry_service


@pytest.fixture(autouse=True)
def override_sqlite_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    manager = get_sqlite_manager(db_path=path)
    telemetry_svc = get_telemetry_service()
    telemetry_svc.sqlite_manager = manager
    telemetry_svc.reset()
    yield manager
    try:
        os.remove(path)
        for ext in ["-wal", "-shm"]:
            if os.path.exists(path + ext):
                os.remove(path + ext)
    except Exception:
        pass


@pytest.fixture
def client():
    return TestClient(app)


def test_full_athlete_telemetry_lifecycle(client):
    """
    Comprehensive lifecycle:
    1. Register athlete account -> receive session token
    2. Check auth/me -> verify user profile
    3. Stream 15 consecutive 128Hz telemetry ticks -> verify DSP calculations
    4. Query session details -> verify accumulated mean statistics
    5. Log trend insights -> verify persistence
    6. Verify sensor status probe reflects active Movesense connection
    """
    # 1. Register Athlete
    reg_resp = client.post("/api/auth/register", json={
        "email": "triathlete@lauburu.ai",
        "password": "TriathlonPassword2026",
        "name": "Triathlon Athlete",
        "role": "user"
    })
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    token = reg_data["session_token"]
    assert token is not None

    # 2. Check Auth Me
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["authenticated"] is True

    # 3. Stream 15 consecutive telemetry ticks (simulating 15 seconds)
    base_time = int(time.time() * 1000)
    for i in range(15):
        tick_resp = client.post("/api/sensors/ingest", json={
            "session_token": token,
            "sensor_type": "movesense",
            "heart_rate": 140.0 + (i * 0.5),
            "rr_intervals_ms": [425.0 - (i * 1.5), 423.0 - (i * 1.5)],
            "dfa_alpha1": 0.78 - (i * 0.001),
            "ecg_mv": [1.2, 0.4, -0.2],
            "acc_g": {"x": 0.05, "y": 0.12, "z": 0.98},
            "ptt_ms": 195.0 - (i * 0.5),
            "delta_time_ms": i * 1000,
            "epoch_ms": base_time + (i * 1000)
        })
        assert tick_resp.status_code == 200
        data = tick_resp.json()
        assert data["status"] == "success"
        assert data["dsp_summary"]["training_zone"] == "Zone 2 (Aerobic Base Endurance)"

    # 4. Query Session Details
    sess_resp = client.get(f"/api/sessions/{token}")
    assert sess_resp.status_code == 200
    sess_data = sess_resp.json()
    assert sess_data["total_ticks"] == 15
    assert sess_data["actual_tick_count"] == 15
    assert sess_data["mean_hr"] > 140.0
    assert sess_data["duration_sec"] == 14

    # 5. Query Historical Ticks
    ticks_resp = client.get(f"/api/sessions/{token}/ticks?limit=50")
    assert ticks_resp.status_code == 200
    ticks_data = ticks_resp.json()
    assert ticks_data["count"] == 15

    # 6. Log Trend Insight
    trend_resp = client.post(f"/api/sessions/{token}/trends", json={
        "session_token": token,
        "window_size_sec": 120,
        "arterial_stiffness_drift_pct": 1.2,
        "vascular_fatigue_index": 0.15,
        "cardiac_drift_detected": False,
        "endothelial_reserve_status": "OPTIMAL",
        "zone2_compliance": "IN_ZONE"
    })
    assert trend_resp.status_code == 201

    # 7. Check Sensor Status Probe
    status_resp = client.get("/api/sensors/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["connected_count"] >= 1
    assert status_data["sensors"]["movesense"]["connected"] is True
    assert status_data["sensors"]["movesense"]["heart_rate"] is not None
    # Verify disconnected sensors are still strictly null
    assert status_data["sensors"]["polar"]["connected"] is False
    assert status_data["sensors"]["polar"]["heart_rate"] is None
