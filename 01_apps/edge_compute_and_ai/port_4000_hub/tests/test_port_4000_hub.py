"""
Comprehensive Test Suite for Port 4000 Canonical Web & Compute Hub.
Validates all Milestone 1 objectives:
1. SQLite WAL mode schema and ACID operations (users, sessions, telemetry_ticks, trend_insights).
2. PBKDF2-HMAC-SHA256 password hashing and secure session generation.
3. Shopify Storefront GraphQL Customer Account verification and dev token fallback.
4. 128Hz Movesense & Polar H10 telemetry processing, Kamath 20% filter, Zone 2 classification.
5. Zero-mock sensor status probe (connected=False, heart_rate=null when disconnected).
6. REST API routes: /api/auth/register, /api/auth/login, /api/auth/shopify-login, /api/auth/me,
   /api/sensors/ingest, /api/sensors/status, /api/apps, /api/sessions/{token}.
7. WebSocket /ws/telemetry live streaming and broadcast.
"""

import os
import tempfile
import time
import pytest
from fastapi.testclient import TestClient

from ..server import app, CATALOG_APPS
from ..storage.sqlite_manager import SqliteManager, get_sqlite_manager, hash_password, verify_password
from ..services.shopify_service import ShopifyService, get_shopify_service
from ..services.telemetry_service import (
    TelemetryService,
    get_telemetry_service,
    apply_kamath_artifact_filter,
    calculate_rmssd,
    classify_training_zone,
    calculate_bp_from_ptt
)


@pytest.fixture(autouse=True)
def temp_sqlite_manager():
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
def client(temp_sqlite_manager):
    return TestClient(app)


# ==================== 1. SQLite WAL & Schema Tests ====================

@pytest.mark.asyncio
async def test_sqlite_wal_schemas_and_crud(temp_sqlite_manager):
    """Verify SQLite tables creation, WAL journal mode, and CRUD operations."""
    with temp_sqlite_manager._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        assert mode.lower() == "wal", "Database must operate in WAL mode"

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cursor.fetchall()}
        required = {"users", "sessions", "telemetry_ticks", "trend_insights"}
        assert required.issubset(tables), f"Missing required tables: {required - tables}"

    # User CRUD
    user = await temp_sqlite_manager.create_user(
        email="wal_tester@lauburu.ai",
        password="WalPass2026!",
        name="WAL Tester",
        role="user",
        membership_tier="PAID_PRO",
        is_paid_subscriber=True
    )
    assert user["id"].startswith("usr_")
    assert user["email"] == "wal_tester@lauburu.ai"
    assert user["is_paid_subscriber"] is True

    # Session creation
    session = await temp_sqlite_manager.create_session(user_id=user["id"])
    token = session["session_token"]
    assert len(token) == 64

    # Log telemetry tick
    tick_id = await temp_sqlite_manager.log_telemetry_tick(
        session_token=token,
        tick_epoch_ms=int(time.time() * 1000),
        delta_time_ms=1000,
        sensor_type="movesense",
        ptt_ms=195.0,
        hr_bpm=142.0,
        rr_ms=422.5,
        rmssd_ms=45.2,
        dfa_alpha1=0.78,
        ecg_mv=1.25,
        imu_acc_g=0.99,
        sbp_calc=122.5,
        dbp_calc=81.2,
        map_calc=95.0,
        confidence_score=0.98
    )
    assert tick_id is not None and tick_id > 0

    # Verify session summary update
    summary = await temp_sqlite_manager.get_session_summary(token)
    assert summary["total_ticks"] == 1
    assert summary["mean_hr"] == 142.0
    assert summary["mean_sbp"] == 122.5
    assert summary["user"]["email"] == "wal_tester@lauburu.ai"

    # Log trend insight
    insight_id = await temp_sqlite_manager.log_trend_insight(
        session_token=token,
        timestamp_epoch_ms=int(time.time() * 1000),
        window_size_sec=120,
        arterial_stiffness_drift_pct=1.5,
        vascular_fatigue_index=0.12,
        cardiac_drift_detected=False,
        endothelial_reserve_status="OPTIMAL",
        zone2_compliance="IN_ZONE"
    )
    assert insight_id is not None and insight_id > 0

    insights = await temp_sqlite_manager.get_trend_insights(token)
    assert len(insights) == 1
    assert insights[0]["zone2_compliance"] == "IN_ZONE"


def test_pbkdf2_password_hashing():
    """Verify PBKDF2-HMAC-SHA256 salted hashing and verification."""
    password = "SecretPassword123!"
    hashed = hash_password(password)
    assert hashed.startswith("pbkdf2_sha256$")
    assert verify_password(hashed, password) is True
    assert verify_password(hashed, "WrongPassword") is False


# ==================== 2. Shopify Service Tests ====================

@pytest.mark.asyncio
async def test_shopify_dev_token_and_credentials():
    """Verify Shopify Service dev token fallback and tag parsing."""
    service = ShopifyService()

    # Dev token bypass
    valid, profile = await service.verify_customer_access_token("tok_dev_aaron_999")
    assert valid is True
    assert profile["tier"] == "PAID_PRO"
    assert profile["is_paid_subscriber"] is True

    # Dev credentials bypass
    valid_cred, cred_res = await service.authenticate_customer_credentials(
        email="dev_aaron@lauburu.ai",
        password="any_password"
    )
    assert valid_cred is True
    assert cred_res["token"].startswith("tok_dev_")
    assert cred_res["profile"]["tier"] == "PAID_PRO"

    # Tag extraction
    tier, is_paid = service._extract_tier_from_tags(["tier_enterprise", "gym_b2b"])
    assert tier == "ENTERPRISE" and is_paid is True

    tier, is_paid = service._extract_tier_from_tags(["tier_pro"])
    assert tier == "PAID_PRO" and is_paid is True

    tier, is_paid = service._extract_tier_from_tags(["standard_user"])
    assert tier == "FREE" and is_paid is False

    # Empty token rejection
    valid_empty, empty_err = await service.verify_customer_access_token("")
    assert valid_empty is False


# ==================== 3. Telemetry DSP & Zone 2 Classification Tests ====================

def test_telemetry_dsp_algorithms():
    """Verify Kamath 20% filter, RMSSD, Zone 2 classification, and PTT blood pressure."""
    # Kamath 20% filter
    raw_rr = [400.0, 408.0, 750.0, 412.0]  # 750.0 is an ectopic spike
    clean_rr, had_artifacts = apply_kamath_artifact_filter(raw_rr)
    assert had_artifacts is True
    assert 750.0 not in clean_rr
    assert len(clean_rr) == 3

    # RMSSD
    rr_series = [400.0, 410.0, 405.0, 415.0]
    rmssd = calculate_rmssd(rr_series)
    assert rmssd is not None and rmssd > 0.0

    # Zone Classification
    zone_name, color = classify_training_zone(0.82)
    assert "Zone 2" in zone_name
    assert color == "#10b981"

    zone_name, color = classify_training_zone(0.62)
    assert "Zone 3" in zone_name
    assert color == "#f59e0b"

    zone_name, color = classify_training_zone(0.42)
    assert "Zone 4/5" in zone_name
    assert color == "#ef4444"

    # Blood pressure from PTT
    sbp, dbp, map_val = calculate_bp_from_ptt(ptt_ms=200.0, hr_bpm=70.0)
    assert sbp == 120.0
    assert dbp == 80.0
    assert map_val == 93.3


# ==================== 4. Zero-Mock Sensor Status & Ingestion REST API Tests ====================

def test_zero_mock_sensor_status_probe(client):
    """Verify zero-mock status: disconnected sensors return null/None, never synthetic data."""
    resp = client.get("/api/sensors/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_supported"] == 4
    assert data["simultaneous_capable"] is True
    assert data["connected_count"] == 0

    for s_id, s_obj in data["sensors"].items():
        assert s_obj["connected"] is False
        assert s_obj["heart_rate"] is None


def test_auth_and_session_lifecycle(client):
    """Test registration, login, shopify-login, auth/me endpoints."""
    # Register
    reg_resp = client.post("/api/auth/register", json={
        "email": "test_pilot@lauburu.ai",
        "password": "PilotPass2026",
        "name": "Test Pilot"
    })
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    token = reg_data["session_token"]
    assert token is not None
    assert reg_data["user"]["email"] == "test_pilot@lauburu.ai"

    # Login
    login_resp = client.post("/api/auth/login", json={
        "email": "test_pilot@lauburu.ai",
        "password": "PilotPass2026"
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["token"] is not None

    # Auth Me
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["authenticated"] is True
    assert me_data["user"]["email"] == "test_pilot@lauburu.ai"

    # Shopify Login (dev token bypass)
    shop_resp = client.post("/api/auth/shopify-login", json={
        "token": "tok_dev_customer_888"
    })
    assert shop_resp.status_code == 200
    shop_data = shop_resp.json()
    assert shop_data["success"] is True
    assert shop_data["membership"]["tier"] == "PAID_PRO"


def test_telemetry_ingest_and_session_association(client):
    """Test ingesting telemetry frames and verifying session association."""
    reg_resp = client.post("/api/auth/register", json={
        "email": "athlete_stream@lauburu.ai",
        "password": "StreamPassword2026",
        "name": "Stream Athlete"
    })
    token = reg_resp.json()["session_token"]

    # Ingest Movesense tick
    ingest_resp = client.post("/api/sensors/ingest", json={
        "session_token": token,
        "sensor_type": "movesense",
        "heart_rate": 148.0,
        "rr_intervals_ms": [410.0, 408.0, 412.0],
        "dfa_alpha1": 0.77,
        "ecg_mv": [1.4, 0.5],
        "acc_g": {"x": 0.05, "y": 0.10, "z": 0.99},
        "ptt_ms": 190.0,
        "delta_time_ms": 1000
    })
    assert ingest_resp.status_code == 200
    res = ingest_resp.json()
    assert res["status"] == "success"
    assert res["dsp_summary"]["training_zone"] == "Zone 2 (Aerobic Base Endurance)"

    # Query session details
    sess_resp = client.get(f"/api/sessions/{token}")
    assert sess_resp.status_code == 200
    sess_data = sess_resp.json()
    assert sess_data["total_ticks"] == 1
    assert sess_data["mean_hr"] == 148.0
    assert sess_data["user"]["email"] == "athlete_stream@lauburu.ai"

    # Query sensor status - movesense should now be connected
    status_resp = client.get("/api/sensors/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["connected_count"] >= 1
    assert status_data["sensors"]["movesense"]["connected"] is True
    assert status_data["sensors"]["movesense"]["heart_rate"] == 148.0
    assert status_data["sensors"]["polar"]["connected"] is False
    assert status_data["sensors"]["polar"]["heart_rate"] is None


def test_app_catalog(client):
    """Test /api/apps returns full catalog registry."""
    resp = client.get("/api/apps")
    assert resp.status_code == 200
    apps = resp.json()
    assert len(apps) >= 16
    app_ids = {a["id"] for a in apps}
    assert "lauburu_super_app" in app_ids
    assert "lauburu_zone2_endurance" in app_ids
    assert "lauburu_movesense_hub" in app_ids
    assert "lauburu_app_store" in app_ids


# ==================== 5. WebSocket Telemetry Streaming Test ====================

def test_websocket_telemetry_flow(client):
    """Verify WebSocket bidirectional push_tick and broadcast."""
    with client.websocket_connect("/ws/telemetry") as ws:
        # Ping/pong
        ws.send_json({"action": "ping"})
        resp = ws.receive_json()
        assert resp.get("action") == "pong"

        # Push tick
        ws.send_json({
            "action": "push_tick",
            "session_token": "ws_test_token_123",
            "tick": {
                "epoch_ms": int(time.time() * 1000),
                "sensor_type": "movesense",
                "hr_bpm": 138.0,
                "rr_ms": [435.0, 432.0],
                "dfa_alpha1": 0.79,
                "ecg_sample": 1.1,
                "accel": {"x": 0.02, "y": 0.05, "z": 1.0}
            }
        })

        broadcast = ws.receive_json()
        assert broadcast.get("type") == "live_telemetry_broadcast"
        assert broadcast.get("sensor_type") == "movesense"
        assert broadcast["biometrics"]["heart_rate_bpm"] == 138.0
        assert broadcast["biometrics"]["training_zone"] == "Zone 2 (Aerobic Base Endurance)"
