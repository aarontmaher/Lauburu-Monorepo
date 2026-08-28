"""
Unit tests for SQLite WAL Storage Manager in Port 4000 Hub.
Verifies WAL mode, schema compliance, PBKDF2 hashing, user/session CRUD,
telemetry tick accumulation, and trend insights logging.
"""

import os
import sqlite3
import tempfile
import time
import pytest

from ..storage.sqlite_manager import (
    SqliteManager,
    hash_password,
    verify_password,
    generate_session_token,
    generate_user_id
)


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    manager = SqliteManager(db_path=path)
    yield manager
    try:
        os.remove(path)
        for ext in ["-wal", "-shm"]:
            if os.path.exists(path + ext):
                os.remove(path + ext)
    except Exception:
        pass


def test_wal_mode_and_schemas(temp_db):
    """Verify SQLite WAL mode pragmas and expected schema structure."""
    with sqlite3.connect(temp_db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        assert mode.lower() == "wal", f"Expected WAL mode, got {mode}"

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {r[0] for r in cursor.fetchall()}
        assert "users" in tables
        assert "sessions" in tables
        assert "telemetry_ticks" in tables
        assert "trend_insights" in tables

        # Verify users columns
        cursor.execute("PRAGMA table_info(users);")
        user_cols = {r[1] for r in cursor.fetchall()}
        expected_user_cols = {
            "id", "email", "name", "role", "password_hash", "shopify_customer_id",
            "membership_tier", "is_paid_subscriber", "created_at_epoch",
            "installed_apps", "paired_devices"
        }
        assert expected_user_cols.issubset(user_cols)

        # Verify sessions columns
        cursor.execute("PRAGMA table_info(sessions);")
        session_cols = {r[1] for r in cursor.fetchall()}
        expected_session_cols = {
            "session_token", "user_id", "created_at_epoch_ms", "updated_at_epoch_ms",
            "expires_at_epoch", "duration_sec", "total_ticks", "mean_sbp",
            "mean_dbp", "mean_map", "mean_hr", "mean_rmssd", "cardiac_drift_detected",
            "zone2_compliance_ratio", "status"
        }
        assert expected_session_cols.issubset(session_cols)

        # Verify telemetry_ticks columns
        cursor.execute("PRAGMA table_info(telemetry_ticks);")
        tick_cols = {r[1] for r in cursor.fetchall()}
        expected_tick_cols = {
            "id", "session_token", "tick_epoch_ms", "delta_time_ms", "sensor_type",
            "ptt_ms", "hr_bpm", "rr_ms", "rmssd_ms", "dfa_alpha1", "ecg_mv",
            "imu_acc_g", "sbp_calc", "dbp_calc", "map_calc", "confidence_score"
        }
        assert expected_tick_cols.issubset(tick_cols)

        # Verify trend_insights columns
        cursor.execute("PRAGMA table_info(trend_insights);")
        insight_cols = {r[1] for r in cursor.fetchall()}
        expected_insight_cols = {
            "id", "session_token", "timestamp_epoch_ms", "window_size_sec",
            "arterial_stiffness_drift_pct", "vascular_fatigue_index",
            "cardiac_drift_detected", "endothelial_reserve_status", "zone2_compliance"
        }
        assert expected_insight_cols.issubset(insight_cols)


def test_pbkdf2_password_hashing():
    """Verify PBKDF2 salt and hash generation and verification."""
    password = "SuperSecretPassword!2026"
    p_hash = hash_password(password)
    assert p_hash.startswith("pbkdf2_sha256$100000$")
    assert verify_password(p_hash, password) is True
    assert verify_password(p_hash, "WrongPassword") is False
    assert verify_password("", password) is False


@pytest.mark.asyncio
async def test_user_and_session_crud(temp_db):
    """Verify user creation, retrieval, updates, and session management."""
    # 1. Create User
    user = await temp_db.create_user(
        email="athlete@lauburu.ai",
        password="AthletePassword123",
        name="Test Athlete",
        role="user",
        membership_tier="PAID_PRO",
        is_paid_subscriber=True
    )
    assert user["id"].startswith("usr_")
    assert user["email"] == "athlete@lauburu.ai"
    assert user["membership_tier"] == "PAID_PRO"
    assert user["is_paid_subscriber"] is True
    assert isinstance(user["installed_apps"], list)

    # 2. Retrieve User
    by_id = await temp_db.get_user_by_id(user["id"])
    assert by_id is not None
    assert by_id["name"] == "Test Athlete"

    by_email = await temp_db.get_user_by_email("athlete@lauburu.ai")
    assert by_email is not None
    assert by_email["id"] == user["id"]

    # 3. Create Session
    session = await temp_db.create_session(user_id=user["id"])
    assert len(session["session_token"]) == 64
    assert session["user_id"] == user["id"]
    assert session["status"] == "active"

    # 4. Resolve User and Session
    user_sess = await temp_db.get_user_and_session(session["session_token"])
    assert user_sess is not None
    u, s = user_sess
    assert u["id"] == user["id"]
    assert s["session_token"] == session["session_token"]

    # 5. Delete Session
    deleted = await temp_db.delete_session(session["session_token"])
    assert deleted is True
    assert await temp_db.get_session(session["session_token"]) is None


@pytest.mark.asyncio
async def test_telemetry_tick_logging_and_session_stats(temp_db):
    """Verify tick insertion, cumulative statistical aggregation, and trend logging."""
    user = await temp_db.create_user(
        email="runner@lauburu.ai",
        password="RunPassword123",
        name="Runner Athlete"
    )
    session = await temp_db.create_session(user_id=user["id"])
    token = session["session_token"]

    # Log 3 telemetry ticks
    now_ms = int(time.time() * 1000)
    await temp_db.log_telemetry_tick(
        session_token=token,
        tick_epoch_ms=now_ms,
        delta_time_ms=0,
        sensor_type="movesense",
        ptt_ms=195.0,
        hr_bpm=140.0,
        rr_ms=428.5,
        rmssd_ms=42.0,
        dfa_alpha1=0.78,
        ecg_mv=1.2,
        imu_acc_g=0.98,
        sbp_calc=122.0,
        dbp_calc=81.0,
        map_calc=94.7,
        confidence_score=0.98
    )

    await temp_db.log_telemetry_tick(
        session_token=token,
        tick_epoch_ms=now_ms + 1000,
        delta_time_ms=1000,
        sensor_type="movesense",
        ptt_ms=190.0,
        hr_bpm=144.0,
        rr_ms=416.6,
        rmssd_ms=40.5,
        dfa_alpha1=0.76,
        ecg_mv=1.1,
        imu_acc_g=1.02,
        sbp_calc=124.0,
        dbp_calc=82.0,
        map_calc=96.0,
        confidence_score=0.99
    )

    # Check session summary
    summary = await temp_db.get_session_summary(token)
    assert summary is not None
    assert summary["total_ticks"] == 2
    assert summary["actual_tick_count"] == 2
    assert summary["mean_hr"] == 142.0
    assert summary["mean_sbp"] == 123.0
    assert summary["mean_dbp"] == 81.5
    assert summary["user"]["email"] == "runner@lauburu.ai"

    # Query ticks
    ticks = await temp_db.get_session_ticks(token)
    assert len(ticks) == 2
    assert ticks[0]["hr_bpm"] == 140.0
    assert ticks[1]["hr_bpm"] == 144.0

    # Log trend insight
    insight_id = await temp_db.log_trend_insight(
        session_token=token,
        timestamp_epoch_ms=now_ms + 2000,
        window_size_sec=120,
        arterial_stiffness_drift_pct=1.5,
        vascular_fatigue_index=0.22,
        cardiac_drift_detected=False,
        endothelial_reserve_status="OPTIMAL",
        zone2_compliance="IN_ZONE"
    )
    assert insight_id > 0

    trends = await temp_db.get_trend_insights(token)
    assert len(trends) == 1
    assert trends[0]["endothelial_reserve_status"] == "OPTIMAL"
    assert trends[0]["cardiac_drift_detected"] is False
