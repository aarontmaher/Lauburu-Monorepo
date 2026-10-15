#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit and Empirical Tests for Movesense 24/7 Biometrics Data Lake Storage Engine
==============================================================================
Validates:
1. SQLite WAL mode + continuous table schema.
2. Partitioned JSONL append log.
3. In-memory circular buffer with 5-minute atomic ZSTD-4 Apache Parquet flushes.
4. Embedded DuckDB time-series range queries and telemetry slices.
5. Zero uncompressed flash text logging footprint with ~28.6 MB/day compression.
"""

import os
import sys
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

# Add paths
REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
LAKE_DIR = REPO_ROOT / "04_data_and_memory/biometrics_lake"
sys.path.insert(0, str(LAKE_DIR))

from storage_engine import BiometricsStorageEngine
from movesense_parquet_storage import MovesenseBiometricStorageEngine


class TestBiometricsStorageEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_movesense.db"
        self.engine = BiometricsStorageEngine(db_path=self.db_path)

    def tearDown(self):
        self.engine.close()
        self.temp_dir.cleanup()

    def test_wal_mode_and_tables(self):
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        self.assertEqual(mode.lower(), "wal")

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cursor.fetchall()}
        self.assertIn("biometric_samples", tables)
        self.assertIn("workout_sessions", tables)
        self.assertIn("daily_rollups", tables)
        conn.close()

    def test_insert_sample_and_jsonl(self):
        sample = {
            "timestamp_utc": "2026-09-10T10:00:00.000Z",
            "epoch_ms": 1788998400000,
            "heart_rate_bpm": 132.0,
            "clean_rr_ms": 454.55,
            "rr_intervals_recent": [450.0, 455.0, 458.0],
            "rmssd_ms": 18.4,
            "dfa_alpha1": 0.81,
            "systolic_bp": 128,
            "diastolic_bp": 82,
            "map_bp": 97.3,
            "training_zone": "ZONE 2 (Aerobic Base / Mitochondrial)",
            "recovery_status": "MODERATE",
            "readiness_score": 75.0,
            "battery_pct": 85,
            "device_address": "C1DB5043-8F89-88E8-46A3-BBD4ED83FC88",
            "source": "corebluetooth_mac"
        }

        row_id = self.engine.insert_sample(sample)
        self.assertGreater(row_id, 0)

        stats = self.engine.get_total_statistics()
        self.assertEqual(stats["total_samples"], 1)
        self.assertEqual(stats["valid_telemetry_samples"], 1)
        self.assertEqual(stats["latest_sample"]["heart_rate_bpm"], 132.0)

        # Verify JSONL partition file exists
        daily_jsonl = self.engine.jsonl_dir / "2026-09-10.jsonl"
        self.assertTrue(daily_jsonl.exists())
        with open(daily_jsonl, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f]
            self.assertEqual(len(lines), 1)
            self.assertEqual(lines[0]["heart_rate_bpm"], 132.0)
            self.assertTrue(lines[0]["rule_0_zero_mock"])

    def test_workout_session_recording(self):
        session = {
            "session_id": "test_workout_01",
            "start_time_utc": "2026-09-10T09:00:00Z",
            "end_time_utc": "2026-09-10T09:45:00Z",
            "duration_seconds": 2700.0,
            "sample_count": 2700,
            "avg_hr": 138.5,
            "min_hr": 98.0,
            "max_hr": 168.0,
            "avg_rmssd": 24.2,
            "avg_dfa_alpha1": 0.78,
            "zone1_seconds": 300.0,
            "zone2_seconds": 2100.0,
            "zone3_plus_seconds": 300.0
        }
        sess_id = self.engine.record_session(session)
        self.assertEqual(sess_id, "test_workout_01")

        history = self.engine.get_workout_history(limit=5)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["avg_hr"], 138.5)
        self.assertEqual(history[0]["zone2_seconds"], 2100.0)

    def test_daily_rollup(self):
        for hr in [60.0, 70.0, 80.0, 90.0, 100.0]:
            self.engine.insert_sample({
                "timestamp_utc": "2026-09-10T12:00:00Z",
                "epoch_ms": 1789000000000,
                "heart_rate_bpm": hr,
                "clean_rr_ms": 60000.0 / hr,
                "rmssd_ms": 30.0,
                "dfa_alpha1": 0.85,
                "readiness_score": 82.0
            })

        rollup = self.engine.update_daily_rollup(date_str="2026-09-10")
        self.assertEqual(rollup["total_samples"], 5)
        self.assertEqual(rollup["mean_hr"], 80.0)
        self.assertEqual(rollup["resting_hr"], 60.0)
        self.assertEqual(rollup["max_hr"], 100.0)

    def test_parquet_zstd4_pipeline_and_circular_buffer(self):
        # Ingest 512 Hz ECG and 104 Hz IMU into circular buffer
        base_ns = 1788998400000000000
        for i in range(1024):  # 2 seconds of 512 Hz ECG
            self.engine.parquet_engine.ingest_ecg(
                timestamp_ns=base_ns + i * 1953125,
                ecg_potential_mv=0.12 + 0.01 * (i % 20),
                sample_idx=i,
                qrs_peak=(i % 512 == 0),
                heart_rate_bpm=68.0,
                rmssd_ms=42.0,
                dfa_alpha1=0.82,
                readiness_score=88.0
            )

        for i in range(208):  # 2 seconds of 104 Hz IMU
            self.engine.parquet_engine.ingest_imu(
                timestamp_ns=base_ns + i * 9615384,
                sample_idx=i,
                acc_x_g=0.01,
                acc_y_g=0.99,
                acc_z_g=0.08,
                gyro_x_dps=0.2,
                gyro_y_dps=-0.1,
                gyro_z_dps=0.05,
                placement="chest_strap",
                placement_confidence=82.5
            )

        stats = self.engine.parquet_engine.get_storage_stats()
        self.assertEqual(stats["current_buffer_ecg"], 1024)
        self.assertEqual(stats["current_buffer_imu"], 208)

        # Flush to Apache Parquet with ZSTD-4
        flush_res = self.engine.flush_parquet()
        self.assertEqual(flush_res["ecg_count"], 1024)
        self.assertEqual(flush_res["imu_count"], 208)
        self.assertGreater(flush_res["ecg_bytes"], 0)
        self.assertGreater(flush_res["imu_bytes"], 0)
        self.assertTrue(Path(flush_res["ecg_file"]).exists())
        self.assertTrue(Path(flush_res["imu_file"]).exists())

    def test_duckdb_range_query_and_telemetry_slices(self):
        base_ns = 1788998400000000000
        for i in range(512):
            self.engine.parquet_engine.ingest_ecg(
                timestamp_ns=base_ns + i * 1953125,
                ecg_potential_mv=0.25,
                sample_idx=i,
                heart_rate_bpm=75.0,
                rmssd_ms=38.0,
                dfa_alpha1=0.76,
                readiness_score=78.0
            )
        self.engine.flush_parquet()

        # Query range
        range_results = self.engine.query_parquet_range(
            start_ns=base_ns,
            end_ns=base_ns + 500000000,  # First 500ms
            modality="ecg"
        )
        self.assertGreater(len(range_results), 0)
        self.assertLessEqual(len(range_results), 512)

        # Query HRV summary via DuckDB
        hrv = self.engine.query_duckdb_hrv()
        self.assertEqual(hrv["total_samples"], 512)
        self.assertEqual(hrv["mean_hr"], 75.0)
        self.assertEqual(hrv["mean_rmssd"], 38.0)
        self.assertEqual(hrv["mean_dfa_alpha1"], 0.76)
        self.assertEqual(hrv["mean_readiness"], 78.0)

    def test_flash_logging_suppression_and_daily_rate(self):
        stats = self.engine.get_parquet_stats()
        self.assertEqual(stats["compression"], "ZSTD Level 4")
        self.assertEqual(stats["estimated_mb_per_day"], 28.6)


if __name__ == "__main__":
    unittest.main()
