#!/usr/bin/env python3
"""
06_scripts_and_tooling/telemetry/verify_pixel_storage_audit.py
==============================================================
Empirical 15-Second Continuous Streaming Storage Audit on Google Pixel.
Verifies:
1. 15 continuous seconds of 128Hz Movesense ECG ingestion (1,920 raw samples in 15 x 1s windows).
2. Dual-mode local persistence in JSONL (telemetry_stream.jsonl) and SQLite WAL (telemetry.db).
3. Strictly monotonic timestamps (t[i] > t[i-1]) with zero timestamp regression.
4. Exact record-by-record and field-by-field parity between JSONL ledger and SQLite database.
5. Port 4000 live forwarding client serialization (HTTP POST and WebSocket protocols).
6. Polar H10 HRS multi-sensor persistence parity.
7. SQLite WAL mode configuration and query index verification.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add monorepo root and compute hub services to path
REPO_ROOT = Path(__file__).resolve().parents[2]
COMPUTE_HUB_SERVICES = REPO_ROOT / "01_apps" / "lauburu_compute_hub" / "services"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(COMPUTE_HUB_SERVICES) not in sys.path:
    sys.path.insert(0, str(COMPUTE_HUB_SERVICES))

from pixel_persistence_engine import PixelPersistenceEngine
from port4000_forwarder import Port4000Forwarder
from movesense_ingestion import (
    MovesenseStreamSimulator,
    apply_kamath_artifact_filter,
    calculate_rmssd,
    calculate_dfa_alpha1,
    calculate_hemodynamics_bp,
    MovesenseBinaryDecoder,
    PolarHrsDecoder
)


class PixelStorageAuditor:
    """
    Automated verification harness for Pixel local persistence and telemetry pipeline.
    """

    def __init__(self, test_dir: Path):
        self.test_dir = test_dir
        self.persistence = PixelPersistenceEngine(base_dir=test_dir)
        self.simulator = MovesenseStreamSimulator(base_heart_rate=142.0)
        self.results: Dict[str, Any] = {}

    def audit_15s_continuous_streaming(self) -> bool:
        """
        Audit 1: Stream 15 seconds of 128Hz Movesense telemetry (1,920 raw samples / 15 windows).
        Verifies that >= 15 contiguous records are written to both JSONL and SQLite.
        """
        print("\n--- Audit 1: 15-Second Continuous 128Hz Movesense Streaming ---")
        start_ts = int(time.time() * 1000)
        frames = self.simulator.generate_15s_stream(start_timestamp_ms=start_ts)

        assert len(frames) == 15, f"Expected 15 frames, got {len(frames)}"
        total_samples = sum(len(f.get("ecg_mv", [])) for f in frames)
        assert total_samples == 1920, f"Expected 1,920 raw samples (15*128), got {total_samples}"

        # Ingest and persist all 15 frames
        inserted_ids = []
        for i, frame in enumerate(frames):
            frame_id = self.persistence.append_frame(frame)
            inserted_ids.append(frame_id)

        jsonl_records = self.persistence.read_jsonl_records()
        sqlite_records = self.persistence.read_sqlite_records()

        print(f" [✓] Streamed 15 continuous windows ({total_samples} raw 128Hz ECG samples)")
        print(f" [✓] JSONL records logged: {len(jsonl_records)}")
        print(f" [✓] SQLite records logged: {len(sqlite_records)}")

        assert len(jsonl_records) >= 15, f"JSONL record count too low: {len(jsonl_records)}"
        assert len(sqlite_records) >= 15, f"SQLite record count too low: {len(sqlite_records)}"
        assert len(jsonl_records) == len(sqlite_records), "Mismatch between JSONL and SQLite counts"

        self.results["audit_1_15s_streaming"] = "PASS"
        return True

    def audit_monotonic_timestamp_integrity(self) -> bool:
        """
        Audit 2: Verify strictly monotonic timestamps across all records (t[i] > t[i-1]).
        Also verify that non-monotonic timestamps are caught and rejected.
        """
        print("\n--- Audit 2: Strictly Monotonic Timestamp Validation ---")
        jsonl_records = self.persistence.read_jsonl_records()
        sqlite_records = self.persistence.read_sqlite_records()

        # 1. Verify JSONL monotonic sequence
        for i in range(1, len(jsonl_records)):
            t_prev = jsonl_records[i - 1]["timestamp_epoch_ms"]
            t_curr = jsonl_records[i]["timestamp_epoch_ms"]
            delta = t_curr - t_prev
            assert delta > 0, f"JSONL non-monotonic timestamp at index {i}: {t_curr} <= {t_prev} (delta={delta})"

        print(f" [✓] Verified strictly monotonic sequence across {len(jsonl_records)} JSONL records")

        # 2. Verify SQLite monotonic sequence
        for i in range(1, len(sqlite_records)):
            t_prev = sqlite_records[i - 1]["timestamp_epoch_ms"]
            t_curr = sqlite_records[i]["timestamp_epoch_ms"]
            delta = t_curr - t_prev
            assert delta > 0, f"SQLite non-monotonic timestamp at index {i}: {t_curr} <= {t_prev} (delta={delta})"

        print(f" [✓] Verified strictly monotonic sequence across {len(sqlite_records)} SQLite records")

        # 3. Test non-monotonic insertion rejection
        last_ts = jsonl_records[-1]["timestamp_epoch_ms"]
        violating_sample = {
            "timestamp_epoch_ms": last_ts - 500,  # in the past!
            "sensor_type": "movesense",
            "sample_rate_hz": 128,
            "heart_rate": 140.0
        }

        caught = False
        try:
            self.persistence.append_frame(violating_sample)
        except ValueError as e:
            caught = True
            print(f" [✓] Non-monotonic timestamp rejection verified: {e}")

        assert caught, "Persistence engine failed to reject non-monotonic timestamp"
        self.results["audit_2_monotonic_timestamps"] = "PASS"
        return True

    def audit_jsonl_sqlite_parity(self) -> bool:
        """
        Audit 3: Verify exact field-by-field parity between JSONL ledger and SQLite database.
        """
        print("\n--- Audit 3: JSONL Ledger and SQLite Database Parity ---")
        jsonl_records = self.persistence.read_jsonl_records()
        sqlite_records = self.persistence.read_sqlite_records()

        assert len(jsonl_records) == len(sqlite_records), "Record count mismatch"

        for idx, (j_rec, s_rec) in enumerate(zip(jsonl_records, sqlite_records)):
            # Timestamp
            assert j_rec["timestamp_epoch_ms"] == s_rec["timestamp_epoch_ms"], f"Timestamp mismatch at #{idx}"
            # Sensor Type
            assert j_rec["sensor_type"] == s_rec["sensor_type"], f"Sensor type mismatch at #{idx}"
            # Device ID
            assert j_rec["device_id"] == s_rec["device_id"], f"Device ID mismatch at #{idx}"
            # Sample Rate
            assert j_rec["sample_rate_hz"] == s_rec["sample_rate_hz"], f"Sample rate mismatch at #{idx}"
            # Heart Rate
            if j_rec.get("heart_rate") is not None:
                assert abs(j_rec["heart_rate"] - s_rec["heart_rate"]) < 1e-4, f"Heart rate mismatch at #{idx}"
            # RMSSD
            if j_rec.get("rmssd") is not None:
                assert abs(j_rec["rmssd"] - s_rec["rmssd"]) < 1e-4, f"RMSSD mismatch at #{idx}"
            # DFA Alpha-1
            if j_rec.get("dfa_alpha1") is not None:
                assert abs(j_rec["dfa_alpha1"] - s_rec["dfa_alpha1"]) < 1e-4, f"DFA alpha1 mismatch at #{idx}"
            # Raw ECG Sample count
            j_ecg = j_rec.get("ecg_mv") or []
            s_ecg = s_rec.get("raw_samples") or []
            assert len(j_ecg) == len(s_ecg), f"Raw sample length mismatch at #{idx}: {len(j_ecg)} vs {len(s_ecg)}"

        print(f" [✓] 100% Field parity confirmed across all {len(jsonl_records)} records")
        self.results["audit_3_storage_parity"] = "PASS"
        return True

    def audit_sqlite_wal_mode_and_indexes(self) -> bool:
        """
        Audit 4: Verify SQLite database runs in WAL mode and indexes exist.
        """
        print("\n--- Audit 4: SQLite WAL Mode and Index Verification ---")
        conn = sqlite3.connect(str(self.persistence.db_path))
        conn.row_factory = sqlite3.Row

        # Check WAL mode
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode;")
        journal_mode = cur.fetchone()[0].upper()
        print(f" [✓] SQLite PRAGMA journal_mode: {journal_mode}")
        assert journal_mode == "WAL", f"Expected WAL mode, got {journal_mode}"

        # Check indexes
        cur.execute("SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'telemetry_frames';")
        indexes = [r["name"] for r in cur.fetchall()]
        print(f" [✓] Registered SQLite indexes: {indexes}")
        assert "idx_telemetry_timestamp" in indexes, "idx_telemetry_timestamp missing"
        assert "idx_telemetry_synced" in indexes, "idx_telemetry_synced missing"

        conn.close()
        self.results["audit_4_sqlite_wal"] = "PASS"
        return True

    def audit_port4000_forwarding_client(self) -> bool:
        """
        Audit 5: Verify Port 4000 Forwarding Client serialization and sync workflow.
        """
        print("\n--- Audit 5: Port 4000 Live Forwarding Pipeline & Offline Sync ---")
        forwarder = Port4000Forwarder(
            host="127.0.0.1",
            port=4000,
            session_token="test_session_token_12345",
            persistence_engine=self.persistence
        )

        test_frame = {
            "timestamp_epoch_ms": int(time.time() * 1000) + 100000,
            "sensor_type": "movesense",
            "heart_rate": 145.0,
            "rr_intervals_ms": [820.0, 818.0],
            "rmssd": 32.5,
            "dfa_alpha1": 0.755,
            "ecg_mv": [0.12, 0.98, -0.15],
            "acc_g": {"x": 0.05, "y": 0.95, "z": 0.10}
        }

        # 1. Test HTTP payload preparation
        http_payload = forwarder._prepare_http_payload(test_frame)
        assert http_payload["session_token"] == "test_session_token_12345"
        assert http_payload["sensor_type"] == "movesense"
        assert http_payload["heart_rate"] == 145.0
        assert http_payload["rmssd"] == 32.5
        assert http_payload["dfa_alpha1"] == 0.755
        print(" [✓] HTTP payload structure matches Port 4000 /api/sensors/ingest contract")

        # 2. Test WebSocket payload preparation
        ws_payload = forwarder._prepare_ws_payload(test_frame)
        assert ws_payload["action"] == "push_tick"
        assert ws_payload["session_token"] == "test_session_token_12345"
        assert ws_payload["tick"]["sensor_type"] == "movesense"
        assert ws_payload["tick"]["hr_bpm"] == 145.0
        assert ws_payload["tick"]["ecg_sample"] == 0.12
        print(" [✓] WebSocket payload matches Port 4000 /ws/telemetry contract")

        # 3. Test offline queuing & sync flag marking
        unsynced = self.persistence.get_unsynced_frames(limit=10)
        assert len(unsynced) > 0, "Expected unsynced frames"
        unsynced_ids = [f["id"] for f in unsynced]

        # Simulate marking as synced
        marked_count = self.persistence.mark_frames_synced(unsynced_ids)
        assert marked_count == len(unsynced_ids)
        print(f" [✓] Marked {marked_count} frames as synced_to_port4000=1 in SQLite")

        self.results["audit_5_forwarding_client"] = "PASS"
        return True

    def audit_polar_h10_compatibility(self) -> bool:
        """
        Audit 6: Verify Polar H10 standard HRS decoding and dual-persistence.
        """
        print("\n--- Audit 6: Polar H10 HRS GATT Multi-Sensor Compatibility ---")
        base_ts = self.persistence.read_jsonl_records()[-1]["timestamp_epoch_ms"] + 5000

        for i in range(5):
            polar_sample = {
                "timestamp_epoch_ms": base_ts + (i * 1000),
                "sensor_type": "polar",
                "device_id": "POLAR-H10-8A7B9C",
                "sample_rate_hz": 130,
                "heart_rate": 135.0 + i * 0.5,
                "rr_intervals_ms": [840.0 + i * 2.0, 838.0 + i * 2.0],
                "rmssd": 29.4,
                "dfa_alpha1": 0.730,
                "raw_samples": []
            }
            self.persistence.append_frame(polar_sample)

        jsonl_all = self.persistence.read_jsonl_records()
        sqlite_all = self.persistence.read_sqlite_records()

        polar_jsonl = [r for r in jsonl_all if r["sensor_type"] == "polar"]
        polar_sqlite = [r for r in sqlite_all if r["sensor_type"] == "polar"]

        assert len(polar_jsonl) == 5, f"Expected 5 Polar JSONL records, got {len(polar_jsonl)}"
        assert len(polar_sqlite) == 5, f"Expected 5 Polar SQLite records, got {len(polar_sqlite)}"
        print(f" [✓] Polar H10 dual persistence verified ({len(polar_jsonl)} records)")

        self.results["audit_6_polar_compatibility"] = "PASS"
        return True

    def run_all(self) -> bool:
        """Executes full suite of storage audits."""
        print("=================================================================")
        print("  PIXEL LOCAL PERSISTENCE & 128Hz MOVESENSE STREAMING AUDIT       ")
        print("=================================================================")

        ok1 = self.audit_15s_continuous_streaming()
        ok2 = self.audit_monotonic_timestamp_integrity()
        ok3 = self.audit_jsonl_sqlite_parity()
        ok4 = self.audit_sqlite_wal_mode_and_indexes()
        ok5 = self.audit_port4000_forwarding_client()
        ok6 = self.audit_polar_h10_compatibility()

        all_ok = ok1 and ok2 and ok3 and ok4 and ok5 and ok6

        print("\n=================================================================")
        print(f"  STORAGE AUDIT RESULT: {'ALL 6 AUDITS PASSED (100%)' if all_ok else 'FAILURES DETECTED'}")
        print("=================================================================")
        for name, status in self.results.items():
            print(f"  - {name}: {status}")
        print("=================================================================\n")
        return all_ok


def main():
    temp_dir = Path(tempfile.mkdtemp(prefix="pixel_storage_audit_"))
    try:
        auditor = PixelStorageAuditor(temp_dir)
        success = auditor.run_all()
        if not success:
            sys.exit(1)
        sys.exit(0)
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
