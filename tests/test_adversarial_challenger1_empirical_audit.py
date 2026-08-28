"""
tests/test_adversarial_challenger1_empirical_audit.py
=====================================================
Challenger 1 Empirical Verification & Adversarial Stress Test Suite.

Authoritative stress test suite executing:
  - Challenge 1: High-concurrency telemetry ingestion stress test against Port 4000 Hub
                 (50 concurrent sensor tick requests, 0 dropped ticks, SQLite storage verification,
                  plus 100-burst multi-session stress test).
  - Challenge 2: Zero-Mock Disconnected Sensor Oracle
                 (Probe /api/sensors/status after reset, verify strictly null values, zero synthetic floats,
                  and heterogeneous multi-sensor connect/disconnect lifecycles).
  - Challenge 3: 15-Second Continuous Movesense Streaming Audit on Pixel storage
                 (1,920 raw 128Hz samples, strict monotonic sequence t[i] > t[i-1], 100% JSONL/SQLite parity,
                  plus 30s 3,840-sample stress test and out-of-order rejection).
  - Challenge 4: Bloat Absence Verification
                 (Full codebase scan for 0 instances of fl_chart in pubspecs and 0 legacy whoop driver references).
"""

import asyncio
import copy
import json
import math
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

# Add 01_apps to sys.path so packages inside can be imported directly
if str(REPO_ROOT / "01_apps") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "01_apps"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from port_4000_hub.server import app
from port_4000_hub.storage.sqlite_manager import SqliteManager, hash_password, verify_password
from port_4000_hub.services.telemetry_service import TelemetryService, SENSOR_METADATA_TEMPLATE
from lauburu_compute_hub.services.pixel_persistence_engine import PixelPersistenceEngine
from lauburu_compute_hub.services.movesense_ingestion import (
    MovesenseStreamSimulator,
    MovesenseBinaryDecoder,
    PolarHrsDecoder,
    apply_kamath_artifact_filter,
    calculate_rmssd,
    calculate_dfa_alpha1,
)


# ============================================================================
# CHALLENGE 1: High-Concurrency Telemetry Ingestion Stress Test
# ============================================================================

class TestChallenge1HighConcurrencyIngestion:
    """
    Simulates 50 concurrent sensor tick requests against Port 4000 Hub.
    Verifies 0 dropped ticks, lock-free SQLite concurrency, and exact data parity.
    """

    @pytest.mark.asyncio
    async def test_50_concurrent_telemetry_ticks_ingestion(self):
        """
        Adversarial Stress Test:
        Fire 50 concurrent sensor ticks with varying biometric parameters.
        Assert that all 50 requests are processed without 500 errors or lock contention.
        Assert that SQLite WAL logs exactly 50 ticks with updated session stats.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test_concurrency_hub.db")
            sqlite_mgr = SqliteManager(db_path=db_path)
            telemetry_svc = TelemetryService(sqlite_manager=sqlite_mgr)

            # 1. Create user and active session
            user = await sqlite_mgr.create_user(
                email="concurrency_athlete@lauburu.local",
                password="SecurePassword123!",
                name="Concurrency Athlete",
                membership_tier="PAID_PRO"
            )
            session = await sqlite_mgr.create_session(user_id=user["id"])
            session_token = session["session_token"]

            assert session_token is not None
            assert len(session_token) == 64

            # 2. Prepare 50 distinct telemetry payloads
            start_epoch = int(time.time() * 1000)
            payloads = []
            for i in range(50):
                tick_ms = start_epoch + (i * 200)  # 5Hz ticks over 10 seconds
                payload = {
                    "session_token": session_token,
                    "sensor_type": "movesense",
                    "heart_rate": 135.0 + (i * 0.4),
                    "rr_intervals_ms": [820.0 - i, 825.0 - i],
                    "rmssd": 35.0 + (i * 0.1),
                    "dfa_alpha1": 0.78 - (i * 0.002),
                    "ecg_mv": [0.05 * math.sin(i), 1.2, -0.4],
                    "acc_g": {"x": 0.02, "y": 0.98, "z": 0.15},
                    "skin_temp_c": 36.5 + (i * 0.01),
                    "ptt_ms": 195.0 - (i * 0.2),
                    "delta_time_ms": i * 200,
                    "epoch_ms": tick_ms
                }
                payloads.append(payload)

            # 3. Fire all 50 concurrently via asyncio.gather on the telemetry service
            start_wall_time = time.perf_counter()
            results = await asyncio.gather(*[
                telemetry_svc.ingest_telemetry_payload(p) for p in payloads
            ], return_exceptions=True)
            elapsed_sec = time.perf_counter() - start_wall_time

            # 4. Assert all returned successfully without exception
            errors = [r for r in results if isinstance(r, Exception)]
            assert len(errors) == 0, f"Encountered {len(errors)} errors during 50 concurrent ticks: {errors}"
            assert len(results) == 50

            for idx, res in enumerate(results):
                assert isinstance(res, dict)
                assert res["status"] == "success"
                assert res["sensor"] == "movesense"
                assert res["tick_id"] is not None
                assert res["tick_id"] > 0
                assert res["dsp_summary"]["rmssd_ms"] is not None

            # 5. Verify SQLite Storage Parity
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Verify tick count
            cur.execute("SELECT COUNT(*) as cnt FROM telemetry_ticks WHERE session_token = ?", (session_token,))
            row = cur.fetchone()
            assert row["cnt"] == 50, f"Expected 50 ticks stored in SQLite, found {row['cnt']} (DROPPED TICKS DETECTED)"

            # Verify all tick IDs are unique
            cur.execute("SELECT id FROM telemetry_ticks WHERE session_token = ?", (session_token,))
            tick_ids = [r["id"] for r in cur.fetchall()]
            assert len(set(tick_ids)) == 50, "Duplicate tick IDs detected in SQLite"

            # Verify session summary statistics roll-up
            summary = await sqlite_mgr.get_session_summary(session_token)
            assert summary is not None
            assert summary["actual_tick_count"] == 50
            assert summary["total_ticks"] == 50
            assert summary["mean_hr"] > 130.0
            assert summary["mean_rmssd"] > 30.0
            assert summary["mean_sbp"] > 100.0
            assert summary["mean_dbp"] > 60.0
            assert summary["duration_sec"] >= 9  # 49 * 200ms = 9800ms = ~9s

            conn.close()

    @pytest.mark.asyncio
    async def test_50_concurrent_http_post_ingest_via_fastapi(self):
        """
        Adversarial Stress Test:
        Fire 50 concurrent HTTP POST requests to `/api/sensors/ingest` using httpx AsyncClient.
        Verifies FastAPI router, dependency injection, Pydantic parsing, and SQLite WAL throughput.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test_http_concurrency.db")
            
            # Monkeypatch default DB path for this test
            from port_4000_hub.storage import sqlite_manager as sm_mod
            from port_4000_hub import server as srv_mod
            from port_4000_hub.services import telemetry_service as ts_mod

            test_sqlite_mgr = SqliteManager(db_path=db_path)
            test_telemetry_svc = TelemetryService(sqlite_manager=test_sqlite_mgr)

            # Override singletons
            sm_mod._global_sqlite_manager = test_sqlite_mgr
            ts_mod._global_telemetry_service = test_telemetry_svc

            # Create test user and session
            user = await test_sqlite_mgr.create_user(
                email="fastapi_athlete@lauburu.local",
                password="SecretPassword123!",
                name="FastAPI Athlete"
            )
            session = await test_sqlite_mgr.create_session(user_id=user["id"])
            session_token = session["session_token"]

            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                now_ms = int(time.time() * 1000)
                tasks = []
                for i in range(50):
                    payload = {
                        "session_token": session_token,
                        "sensor_type": "polar" if i % 2 == 0 else "movesense",
                        "heart_rate": 140.0 + (i * 0.5),
                        "rr_intervals_ms": [800.0 + i, 805.0 + i],
                        "rmssd": 42.0,
                        "dfa_alpha1": 0.75,
                        "ecg_mv": [0.12, 0.45, -0.2],
                        "acc_g": {"x": 0.01, "y": 0.99, "z": 0.10},
                        "skin_temp_c": 36.6,
                        "ptt_ms": 190.0,
                        "delta_time_ms": i * 100,
                        "epoch_ms": now_ms + (i * 100)
                    }
                    tasks.append(client.post("/api/sensors/ingest", json=payload))

                responses = await asyncio.gather(*tasks, return_exceptions=True)

            # Validate responses
            for resp in responses:
                assert not isinstance(resp, Exception)
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "success"
                assert data["tick_id"] is not None

            # Verify SQLite DB
            ticks = await test_sqlite_mgr.get_session_ticks(session_token, limit=100)
            assert len(ticks) == 50, f"Expected 50 ticks in DB, found {len(ticks)}"

    @pytest.mark.asyncio
    async def test_100_burst_concurrent_multi_session_ingest(self):
        """
        Adversarial Stress Test:
        Fire 100 concurrent ticks across 5 distinct sessions (20 ticks per session).
        Verifies SQLite WAL concurrency isolation across multiple sessions simultaneously.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test_100_burst.db")
            sqlite_mgr = SqliteManager(db_path=db_path)
            telemetry_svc = TelemetryService(sqlite_manager=sqlite_mgr)

            # Create 5 distinct sessions
            session_tokens = []
            for s_idx in range(5):
                user = await sqlite_mgr.create_user(
                    email=f"athlete_{s_idx}@lauburu.local",
                    password=f"PassWord_{s_idx}!",
                    name=f"Athlete {s_idx}"
                )
                sess = await sqlite_mgr.create_session(user_id=user["id"])
                session_tokens.append(sess["session_token"])

            # 100 payloads (20 per session)
            now_ms = int(time.time() * 1000)
            payloads = []
            for i in range(100):
                s_token = session_tokens[i % 5]
                payload = {
                    "session_token": s_token,
                    "sensor_type": "movesense",
                    "heart_rate": 130.0 + (i % 20),
                    "rr_intervals_ms": [800.0, 810.0],
                    "rmssd": 38.0,
                    "dfa_alpha1": 0.77,
                    "epoch_ms": now_ms + i * 50
                }
                payloads.append(payload)

            results = await asyncio.gather(*[
                telemetry_svc.ingest_telemetry_payload(p) for p in payloads
            ], return_exceptions=True)

            errors = [r for r in results if isinstance(r, Exception)]
            assert len(errors) == 0, f"Encountered errors in 100 burst: {errors}"
            assert len(results) == 100

            # Verify each of the 5 sessions received exactly 20 ticks
            for s_token in session_tokens:
                ticks = await sqlite_mgr.get_session_ticks(s_token, limit=100)
                assert len(ticks) == 20, f"Expected 20 ticks for session, got {len(ticks)}"


# ============================================================================
# CHALLENGE 2: Zero-Mock Disconnected Sensor Oracle
# ============================================================================

class TestChallenge2ZeroMockDisconnectedSensorOracle:
    """
    Probes /api/sensors/status after reset and under simulated disconnects.
    Enforces Rule #0: Strictly null/None values, zero synthetic floats (e.g. 72.0 or 0.0).
    """

    def test_status_after_reset_has_strictly_null_telemetry(self):
        """
        Oracle Verification:
        Immediately after reset, all sensor metrics MUST be None.
        Zero synthetic floats, zero mock heart rate arrays.
        """
        telemetry_svc = TelemetryService()
        telemetry_svc.reset()

        status = telemetry_svc.get_sensor_status()

        assert status["connected_count"] == 0
        assert status["total_supported"] == 4
        assert status["simultaneous_capable"] is True
        assert status["fusion_state"] == "AWAITING_BLUETOOTH_SENSORS"

        sensors = status["sensors"]
        assert len(sensors) == 4

        for sensor_id, sensor_meta in sensors.items():
            assert sensor_meta["connected"] is False, f"Sensor {sensor_id} must be disconnected after reset"
            assert sensor_meta["heart_rate"] is None, f"Sensor {sensor_id} heart_rate must be None, got {sensor_meta['heart_rate']}"
            assert sensor_meta["last_seen_epoch"] is None, f"Sensor {sensor_id} last_seen_epoch must be None"

            if "rr_intervals_ms" in sensor_meta:
                assert sensor_meta["rr_intervals_ms"] is None, f"{sensor_id} rr_intervals_ms must be None"
            if "rmssd" in sensor_meta:
                assert sensor_meta["rmssd"] is None, f"{sensor_id} rmssd must be None"
            if "dfa_alpha1" in sensor_meta:
                assert sensor_meta["dfa_alpha1"] is None, f"{sensor_id} dfa_alpha1 must be None"
            if "ecg_mv" in sensor_meta:
                assert sensor_meta["ecg_mv"] is None, f"{sensor_id} ecg_mv must be None"
            if "acc_g" in sensor_meta:
                assert sensor_meta["acc_g"] is None, f"{sensor_id} acc_g must be None"
            if "skin_temp_c" in sensor_meta:
                assert sensor_meta["skin_temp_c"] is None, f"{sensor_id} skin_temp_c must be None"

    @pytest.mark.asyncio
    async def test_stale_sensor_pruning_oracle(self):
        """
        Oracle Verification:
        When a sensor connects and then ceases transmission past the timeout,
        prune_stale_sensors() must flip connected=False and set all biometrics strictly back to None.
        """
        telemetry_svc = TelemetryService(sensor_timeout_sec=0.05)  # 50ms timeout for test
        telemetry_svc.reset()

        # Ingest live telemetry for Movesense and Polar
        await telemetry_svc.ingest_telemetry_payload({
            "sensor_type": "movesense",
            "heart_rate": 152.0,
            "rr_intervals_ms": [394.7, 395.1],
            "rmssd": 28.5,
            "dfa_alpha1": 0.68,
            "ecg_mv": [1.4, -0.3]
        })
        await telemetry_svc.ingest_telemetry_payload({
            "sensor_type": "polar",
            "heart_rate": 151.0,
            "rr_intervals_ms": [396.0, 398.0]
        })

        # Immediately probe status: both connected
        live_status = telemetry_svc.get_sensor_status()
        assert live_status["connected_count"] == 2
        assert live_status["fusion_state"] == "DUAL_SENSOR_FUSION"
        assert live_status["sensors"]["movesense"]["connected"] is True
        assert live_status["sensors"]["movesense"]["heart_rate"] == 152.0
        assert live_status["sensors"]["polar"]["connected"] is True
        assert live_status["sensors"]["polar"]["heart_rate"] == 151.0

        # Wait for timeout (60ms > 50ms)
        await asyncio.sleep(0.06)

        # Probe status again: both should be pruned to disconnected null state
        pruned_status = telemetry_svc.get_sensor_status()
        assert pruned_status["connected_count"] == 0
        assert pruned_status["fusion_state"] == "AWAITING_BLUETOOTH_SENSORS"

        movesense = pruned_status["sensors"]["movesense"]
        assert movesense["connected"] is False
        assert movesense["heart_rate"] is None
        assert movesense["rmssd"] is None
        assert movesense["dfa_alpha1"] is None
        assert movesense["ecg_mv"] is None
        assert movesense["last_seen_epoch"] is None

        polar = pruned_status["sensors"]["polar"]
        assert polar["connected"] is False
        assert polar["heart_rate"] is None
        assert polar["rr_intervals_ms"] is None
        assert polar["last_seen_epoch"] is None

    @pytest.mark.asyncio
    async def test_heterogeneous_sensor_lifecycle(self):
        """
        Oracle Verification:
        When Movesense continues streaming but Polar disconnects,
        Movesense stays connected while Polar is strictly pruned to null.
        """
        telemetry_svc = TelemetryService(sensor_timeout_sec=0.08)
        telemetry_svc.reset()

        # Connect Polar and Movesense
        await telemetry_svc.ingest_telemetry_payload({
            "sensor_type": "polar",
            "heart_rate": 140.0
        })
        await telemetry_svc.ingest_telemetry_payload({
            "sensor_type": "movesense",
            "heart_rate": 142.0
        })

        assert telemetry_svc.get_sensor_status()["connected_count"] == 2

        # Sleep 50ms, then refresh ONLY Movesense
        await asyncio.sleep(0.05)
        await telemetry_svc.ingest_telemetry_payload({
            "sensor_type": "movesense",
            "heart_rate": 143.0
        })

        # Sleep another 40ms (total Polar age = 90ms > 80ms; Movesense age = 40ms < 80ms)
        await asyncio.sleep(0.04)

        status = telemetry_svc.get_sensor_status()
        assert status["connected_count"] == 1
        assert status["fusion_state"] == "SINGLE_SENSOR_STREAM"
        assert status["sensors"]["movesense"]["connected"] is True
        assert status["sensors"]["movesense"]["heart_rate"] == 143.0
        assert status["sensors"]["polar"]["connected"] is False
        assert status["sensors"]["polar"]["heart_rate"] is None


# ============================================================================
# CHALLENGE 3: 15-Second Continuous Movesense Streaming Audit (1,920 Samples)
# ============================================================================

class TestChallenge3ContinuousMovesenseStreamingAudit:
    """
    Executes 15 seconds of continuous 128Hz Movesense streaming (1,920 raw ECG samples).
    Asserts strict monotonic sequence t[i] > t[i-1], and verifies 100% JSONL/SQLite parity.
    """

    def test_15s_continuous_movesense_streaming_1920_samples(self):
        """
        Continuous Streaming Audit:
        1. Generate 15 contiguous 1-second windows @ 128Hz (15 * 128 = 1,920 samples).
        2. Persist to Pixel Local Storage (JSONL & SQLite).
        3. Assert strict monotonic timestamp sequence across both ledgers.
        4. Assert 100% field-for-field parity between JSONL and SQLite.
        5. Verify monotonic violation guard halts out-of-order writes.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            engine = PixelPersistenceEngine(base_dir=base_path, enforce_monotonic=True)

            start_epoch_ms = 1724536800000  # Canonical baseline timestamp
            sim = MovesenseStreamSimulator(base_heart_rate=142.0)
            stream_15s = sim.generate_15s_stream(start_timestamp_ms=start_epoch_ms)

            assert len(stream_15s) == 15, f"Expected 15 windows, got {len(stream_15s)}"

            # 1. Ingest all 15 windows
            frame_ids = []
            total_raw_samples_count = 0
            for idx, window in enumerate(stream_15s):
                fid = engine.append_frame(window)
                frame_ids.append(fid)
                total_raw_samples_count += len(window["ecg_mv"])

            assert len(frame_ids) == 15
            assert total_raw_samples_count == 1920, f"Expected 1,920 raw ECG samples, got {total_raw_samples_count}"

            # 2. Read back from JSONL and SQLite
            jsonl_records = engine.read_jsonl_records()
            sqlite_records = engine.read_sqlite_records()

            assert len(jsonl_records) == 15, f"Expected 15 JSONL records, got {len(jsonl_records)}"
            assert len(sqlite_records) == 15, f"Expected 15 SQLite records, got {len(sqlite_records)}"

            # 3. Monotonic Sequence Assertion (t[i] > t[i-1])
            for i in range(1, 15):
                prev_ts_jsonl = jsonl_records[i - 1]["timestamp_epoch_ms"]
                curr_ts_jsonl = jsonl_records[i]["timestamp_epoch_ms"]
                assert curr_ts_jsonl > prev_ts_jsonl, (
                    f"JSONL monotonicity violation at index {i}: {curr_ts_jsonl} <= {prev_ts_jsonl}"
                )
                assert curr_ts_jsonl - prev_ts_jsonl == 1000, (
                    f"JSONL 1s interval mismatch at index {i}: delta = {curr_ts_jsonl - prev_ts_jsonl}"
                )

                prev_ts_sql = sqlite_records[i - 1]["timestamp_epoch_ms"]
                curr_ts_sql = sqlite_records[i]["timestamp_epoch_ms"]
                assert curr_ts_sql > prev_ts_sql, (
                    f"SQLite monotonicity violation at index {i}: {curr_ts_sql} <= {prev_ts_sql}"
                )
                assert curr_ts_sql - prev_ts_sql == 1000, (
                    f"SQLite 1s interval mismatch at index {i}: delta = {curr_ts_sql - prev_ts_sql}"
                )

            # 4. 100% JSONL / SQLite Field-by-Field Parity Verification
            for j in range(15):
                j_rec = jsonl_records[j]
                s_rec = sqlite_records[j]

                assert j_rec["timestamp_epoch_ms"] == s_rec["timestamp_epoch_ms"]
                assert j_rec["sensor_type"] == s_rec["sensor_type"]
                assert j_rec["device_id"] == s_rec["device_id"]
                assert j_rec["sample_rate_hz"] == s_rec["sample_rate_hz"]
                assert j_rec["sample_rate_hz"] == 128
                assert j_rec["heart_rate"] == pytest.approx(s_rec["heart_rate"], 0.01)
                assert j_rec["rmssd"] == pytest.approx(s_rec["rmssd"], 0.01)
                assert j_rec["dfa_alpha1"] == pytest.approx(s_rec["dfa_alpha1"], 0.001)

                # Raw sample count in SQLite vs JSONL
                s_raw = s_rec["raw_samples"]
                if isinstance(s_raw, str):
                    s_raw = json.loads(s_raw)
                assert len(j_rec["ecg_mv"]) == 128
                assert len(s_raw) == 128
                assert j_rec["ecg_mv"] == pytest.approx(s_raw, abs=1e-4)

            # 5. Engine Self-Verification Integrity Oracle
            integrity = engine.verify_integrity()
            assert integrity["valid"] is True
            assert integrity["counts_match"] is True
            assert integrity["jsonl_record_count"] == 15
            assert integrity["sqlite_record_count"] == 15
            assert integrity["jsonl_monotonic"] is True
            assert integrity["sqlite_monotonic"] is True
            assert integrity["field_parity"] is True
            assert len(integrity["jsonl_violations"]) == 0
            assert len(integrity["sqlite_violations"]) == 0

            # 6. Monotonic Violation Guard Assertion
            # Attempt to append a duplicate timestamp or regress in time
            last_ts = jsonl_records[-1]["timestamp_epoch_ms"]
            violating_frame = copy.deepcopy(stream_15s[0])
            violating_frame["timestamp_epoch_ms"] = last_ts - 500  # Regress 500ms

            with pytest.raises(ValueError) as excinfo:
                engine.append_frame(violating_frame)
            assert "Monotonic timestamp violation" in str(excinfo.value)

    def test_30s_continuous_streaming_and_corrupt_line_handling(self):
        """
        Stress Test:
        Stream 30 contiguous 1-second windows (3,840 raw ECG samples).
        Then simulate partial corruption in JSONL file, asserting parser gracefully skips corrupted lines.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            engine = PixelPersistenceEngine(base_dir=base_path, enforce_monotonic=True)

            sim = MovesenseStreamSimulator(base_heart_rate=150.0)
            start_ms = 1724537000000

            total_samples = 0
            for i in range(30):
                w = sim.generate_1s_window(window_idx=i, timestamp_epoch_ms=start_ms + (i * 1000))
                engine.append_frame(w)
                total_samples += len(w["ecg_mv"])

            assert total_samples == 3840, f"Expected 3,840 samples, got {total_samples}"
            assert len(engine.read_jsonl_records()) == 30
            assert len(engine.read_sqlite_records()) == 30

            # Manually inject a corrupt line into JSONL
            with open(engine.jsonl_path, "a", encoding="utf-8") as f:
                f.write("CORRUPTED_JSON_GARBAGE_LINE\n")

            # Reading should cleanly skip the invalid line
            records = engine.read_jsonl_records()
            assert len(records) == 30, "read_jsonl_records must cleanly skip corrupt lines"


# ============================================================================
# CHALLENGE 4: Bloat Absence Verification
# ============================================================================

class TestChallenge4BloatAbsenceVerification:
    """
    Scans entire repository to confirm 0 instances of `fl_chart` in pubspecs,
    and 0 legacy whoop driver references in active code.
    """

    def test_zero_fl_chart_in_all_pubspecs(self):
        """
        Bloat Audit:
        Find all pubspec.yaml files across the monorepo.
        Assert that none contain `fl_chart` in raw content or parsed YAML dependencies.
        """
        pubspec_files = list(REPO_ROOT.glob("**/pubspec.yaml"))
        assert len(pubspec_files) > 0, "Expected to find at least one pubspec.yaml in repository"

        violations = []
        for pubspec_path in pubspec_files:
            # Skip gitignored or agent dirs
            if ".git" in pubspec_path.parts or ".agents" in pubspec_path.parts:
                continue

            content = pubspec_path.read_text(encoding="utf-8", errors="ignore")
            if "fl_chart" in content:
                violations.append((str(pubspec_path), "fl_chart string present in file"))

            try:
                parsed = yaml.safe_load(content)
                if isinstance(parsed, dict):
                    deps = parsed.get("dependencies", {}) or {}
                    dev_deps = parsed.get("dev_dependencies", {}) or {}
                    if "fl_chart" in deps:
                        violations.append((str(pubspec_path), "fl_chart in dependencies"))
                    if "fl_chart" in dev_deps:
                        violations.append((str(pubspec_path), "fl_chart in dev_dependencies"))
            except Exception as e:
                violations.append((str(pubspec_path), f"YAML parse error: {e}"))

        assert len(violations) == 0, f"Found fl_chart bloat in pubspecs: {violations}"

    def test_zero_legacy_whoop_drivers_in_active_codebase(self):
        """
        Bloat Audit:
        Scans 01_apps/lauburu_compute_hub and 03_biometrics_and_telemetry.
        Confirms zero legacy whoop driver implementations (e.g. IngestWhoop, WhoopDriver, WhoopBleService).
        """
        target_dirs = [
            REPO_ROOT / "01_apps" / "lauburu_compute_hub",
            REPO_ROOT / "03_biometrics_and_telemetry",
        ]

        forbidden_patterns = [
            r"class\s+WhoopDriver",
            r"class\s+WhoopBleService",
            r"def\s+ingest_whoop",
            r"void\s+ingestWhoop",
            r"enum\s+WearableSource\s*\{[^}]*whoop[^}]*\}",
        ]

        violations = []
        for target_dir in target_dirs:
            if not target_dir.exists():
                continue
            for file_path in target_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.suffix not in (".py", ".dart", ".kt", ".ts", ".js"):
                    continue

                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for pattern in forbidden_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        violations.append((str(file_path), pattern, match.group(0)))

        assert len(violations) == 0, f"Found legacy whoop driver references: {violations}"

    def test_monorepo_wide_bloat_scan(self):
        """
        Exhaustive Deep Scan:
        Scan all source code files in 01_apps/ for fl_chart references.
        """
        apps_dir = REPO_ROOT / "01_apps"
        violations = []
        for file_path in apps_dir.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix in (".dart", ".yaml", ".lock", ".kt", ".gradle"):
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if "fl_chart" in content:
                    violations.append(str(file_path))

        assert len(violations) == 0, f"fl_chart detected in 01_apps: {violations}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
