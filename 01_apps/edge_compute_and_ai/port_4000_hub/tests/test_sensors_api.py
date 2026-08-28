"""
Integration tests for Sensors & Telemetry Ingestion API on Port 4000 Hub.
Tests /api/sensors/status (zero-mock probe), /api/sensors/ingest,
and session-telemetry linking without sync errors.
"""

import os
import tempfile
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
    # Reset telemetry service state
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


def test_sensor_status_zero_mock(client):
    """Verify that /api/sensors/status strictly returns zero-mock nulls when disconnected."""
    resp = client.get("/api/sensors/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_supported"] == 4
    assert data["simultaneous_capable"] is True

    for s_name, s_data in data["sensors"].items():
        if not s_data["connected"]:
            assert s_data["heart_rate"] is None, f"{s_name} heart_rate must be null when disconnected"


def test_sensor_ingest_and_session_association(client):
    """
    R1 / AC1 Requirement: Register account -> Ingest telemetry -> Query session
    -> Verify immediate association without sync errors.
    """
    # 1. Register User & Session
    reg_resp = client.post("/api/auth/register", json={
        "email": "grappler@lauburu.ai",
        "password": "GrapplePassword123",
        "name": "Grappler Pro"
    })
    session_token = reg_resp.json()["session_token"]

    # 2. Ingest Movesense Telemetry
    ingest_resp = client.post("/api/sensors/ingest", json={
        "session_token": session_token,
        "sensor_type": "movesense",
        "heart_rate": 145.0,
        "rr_intervals_ms": [415.0, 412.0, 416.0],
        "dfa_alpha1": 0.78,
        "ecg_mv": [1.15, 0.42],
        "acc_g": {"x": 0.08, "y": 0.15, "z": 0.98},
        "ptt_ms": 192.0
    })
    assert ingest_resp.status_code == 200
    res_data = ingest_resp.json()
    assert res_data["status"] == "success"
    assert res_data["sensor"] == "movesense"
    assert res_data["connected_count"] >= 1
    assert "Zone 2" in res_data["dsp_summary"]["training_zone"]
    assert res_data["dsp_summary"]["sbp_calc"] is not None

    # 3. Query Session Details
    sess_resp = client.get(f"/api/sessions/{session_token}")
    assert sess_resp.status_code == 200
    sess_data = sess_resp.json()
    assert sess_data["total_ticks"] >= 1
    assert sess_data["mean_hr"] == 145.0
    assert sess_data["user"]["email"] == "grappler@lauburu.ai"

    # 4. Query Historical Ticks
    ticks_resp = client.get(f"/api/sessions/{session_token}/ticks")
    assert ticks_resp.status_code == 200
    ticks_data = ticks_resp.json()
    assert ticks_data["count"] >= 1
    assert ticks_data["ticks"][0]["hr_bpm"] == 145.0
    assert ticks_data["ticks"][0]["sensor_type"] == "movesense"


def test_trend_insights_logging_and_query(client):
    """Verify logging and querying trend insights."""
    reg_resp = client.post("/api/auth/register", json={
        "email": "trend_tester@lauburu.ai",
        "password": "TrendPassword123",
        "name": "Trend Tester"
    })
    session_token = reg_resp.json()["session_token"]

    # Log trend insight
    trend_resp = client.post(f"/api/sessions/{session_token}/trends", json={
        "session_token": session_token,
        "window_size_sec": 120,
        "arterial_stiffness_drift_pct": 2.1,
        "vascular_fatigue_index": 0.18,
        "cardiac_drift_detected": False,
        "endothelial_reserve_status": "OPTIMAL",
        "zone2_compliance": "IN_ZONE"
    })
    assert trend_resp.status_code == 201
    assert trend_resp.json()["status"] == "success"

    # Query trend insights
    get_trends = client.get(f"/api/sessions/{session_token}/trends")
    assert get_trends.status_code == 200
    data = get_trends.json()
    assert data["count"] == 1
    assert data["insights"][0]["zone2_compliance"] == "IN_ZONE"
