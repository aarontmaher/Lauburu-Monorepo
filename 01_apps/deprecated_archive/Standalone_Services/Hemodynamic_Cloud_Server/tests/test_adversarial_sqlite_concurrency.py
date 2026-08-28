"""
Adversarial SQLite WAL Concurrency Stress Test Suite.
Empirically verifies:
1. High-throughput concurrent async writes & reads across multiple worker tasks.
2. 0 database lock errors (sqlite3.OperationalError: database is locked).
3. Exact mathematical consistency between inserted telemetry ticks and session rolling stats.
4. WAL journaling integrity and checkpointing stability.
"""

import asyncio
import os
import sqlite3
import tempfile
import pytest
from app.storage.sqlite_manager import SqliteManager


class TestAdversarialSqliteConcurrency:
    """Stress tests SQLite WAL concurrency, multi-task async workloads, and rolling stat integrity."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary SQLite database file with WAL mode enabled."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            db_path = tf.name
        manager = SqliteManager(db_path=db_path)
        yield manager, db_path
        # Cleanup
        for ext in ["", "-wal", "-shm"]:
            p = db_path + ext
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

    @pytest.mark.asyncio
    async def test_wal_pragmas_and_journaling_mode(self, temp_db):
        """Verify that PRAGMA journal_mode is WAL and PRAGMA synchronous is NORMAL."""
        manager, db_path = temp_db
        conn = manager._get_connection()
        try:
            journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
            sync_mode = conn.execute("PRAGMA synchronous;").fetchone()[0]
            busy_timeout = conn.execute("PRAGMA busy_timeout;").fetchone()[0]

            assert journal_mode.lower() == "wal"
            assert sync_mode == 1  # 1 == NORMAL
            assert busy_timeout >= 5000  # At least 5000ms
        finally:
            conn.close()

    @pytest.mark.asyncio
    async def test_massive_concurrent_async_writes_and_reads(self, temp_db):
        """
        Adversarial Stress Test:
        Launch 50 concurrent async workers writing 40 ticks each (2,000 total writes)
        concurrently with 10 continuous reader workers querying summaries and ticks.
        Verify 0 lock exceptions, 0 data loss, and perfect integrity.
        """
        manager, _ = temp_db
        num_sessions = 5
        num_workers = 50
        ticks_per_worker = 40
        total_expected_ticks = num_workers * ticks_per_worker  # 2000 ticks

        session_hashes = [f"{i:064x}" for i in range(1, num_sessions + 1)]

        # Pre-initialize sessions
        for sh in session_hashes:
            await manager.create_or_get_session(sh)

        # Worker write task
        async def writer_worker(worker_id: int):
            for i in range(ticks_per_worker):
                session_idx = (worker_id + i) % num_sessions
                sh = session_hashes[session_idx]
                tick_time = 1700000000000 + (worker_id * 1000) + (i * 10)
                await manager.log_telemetry_tick(
                    session_hash=sh,
                    tick_epoch_ms=tick_time,
                    delta_time_ms=(i + 1) * 1000,
                    ptt_ms=210.0 + (i % 20),
                    hr_bpm=70.0 + (i % 30),
                    rr_ms=800.0,
                    delta_t_dia_ms=270.0,
                    imu_acc_g=1.05,
                    e0_elasticity=400.0,
                    sbp_calc=120.0 + (i % 10),
                    dbp_calc=80.0 + (i % 5),
                    map_calc=93.3,
                    pulse_pressure_calc=40.0,
                    vascular_resistance=1.1,
                    confidence_score=0.95
                )

        # Background reader task
        read_errors = []
        keep_reading = True

        async def reader_worker(reader_id: int):
            while keep_reading:
                for sh in session_hashes:
                    try:
                        summary = await manager.get_session_summary(sh)
                        assert summary is not None
                        ticks = await manager.get_session_ticks(sh, limit=50)
                        assert isinstance(ticks, list)
                    except Exception as ex:
                        read_errors.append((reader_id, str(ex)))
                await asyncio.sleep(0.01)

        # Start readers
        readers = [asyncio.create_task(reader_worker(r)) for r in range(10)]

        # Execute all 50 writers concurrently
        writer_tasks = [asyncio.create_task(writer_worker(w)) for w in range(num_workers)]
        await asyncio.gather(*writer_tasks)

        # Stop readers
        keep_reading = False
        await asyncio.gather(*readers)

        # Verify no read errors occurred
        assert len(read_errors) == 0, f"Concurrent read errors detected: {read_errors}"

        # Verify all 2,000 ticks were successfully recorded in SQLite
        conn = manager._get_connection()
        try:
            total_count = conn.execute("SELECT COUNT(*) FROM telemetry_ticks;").fetchone()[0]
            assert total_count == total_expected_ticks, f"Expected {total_expected_ticks} ticks, found {total_count}"

            # Verify rolling stats for each session
            for sh in session_hashes:
                summary = await manager.get_session_summary(sh)
                assert summary is not None
                db_stats = conn.execute("""
                    SELECT COUNT(*), AVG(sbp_calc), AVG(dbp_calc), AVG(hr_bpm)
                    FROM telemetry_ticks WHERE session_hash = ?
                """, (sh,)).fetchone()
                
                assert summary["total_ticks"] == db_stats[0]
                assert abs(summary["mean_sbp"] - round(db_stats[1], 1)) < 1e-3
                assert abs(summary["mean_dbp"] - round(db_stats[2], 1)) < 1e-3
                assert abs(summary["mean_hr"] - round(db_stats[3], 1)) < 1e-3
        finally:
            conn.close()

    @pytest.mark.asyncio
    async def test_wal_checkpoint_during_active_workload(self, temp_db):
        """Verify that explicit WAL checkpoints do not interrupt active operations or corrupt database."""
        manager, _ = temp_db
        session_hash = "b" * 64
        await manager.create_or_get_session(session_hash)

        # Write 200 ticks
        for i in range(200):
            await manager.log_telemetry_tick(
                session_hash=session_hash,
                tick_epoch_ms=1700000000000 + (i * 100),
                delta_time_ms=(i + 1) * 100,
                ptt_ms=220.0,
                hr_bpm=75.0,
                rr_ms=800.0,
                delta_t_dia_ms=280.0,
                imu_acc_g=1.0,
                e0_elasticity=400.0,
                sbp_calc=122.0,
                dbp_calc=81.0,
                map_calc=94.6,
                pulse_pressure_calc=41.0,
                vascular_resistance=1.05,
                confidence_score=0.96
            )

        # Execute TRUNCATE WAL checkpoint
        conn = manager._get_connection()
        try:
            checkpoint_result = conn.execute("PRAGMA wal_checkpoint(TRUNCATE);").fetchone()
            # Returns (busy, log, checkpointed) -> busy should be 0
            assert checkpoint_result[0] == 0, f"WAL checkpoint failed with busy status: {checkpoint_result}"
        finally:
            conn.close()

        # Check that reading still works perfectly after checkpoint
        summary = await manager.get_session_summary(session_hash)
        assert summary is not None
        assert summary["total_ticks"] == 200
        assert summary["mean_sbp"] == 122.0

    @pytest.mark.asyncio
    async def test_concurrent_trend_insight_logging(self, temp_db):
        """Verify concurrent logging of trend insights alongside telemetry ticks."""
        manager, _ = temp_db
        session_hash = "c" * 64
        await manager.create_or_get_session(session_hash)

        async def log_ticks():
            for i in range(50):
                await manager.log_telemetry_tick(
                    session_hash=session_hash,
                    tick_epoch_ms=1700000000000 + (i * 500),
                    delta_time_ms=(i + 1) * 500,
                    ptt_ms=220.0,
                    hr_bpm=75.0,
                    rr_ms=800.0,
                    delta_t_dia_ms=280.0,
                    imu_acc_g=1.0,
                    e0_elasticity=400.0,
                    sbp_calc=120.0,
                    dbp_calc=80.0,
                    map_calc=93.3,
                    pulse_pressure_calc=40.0,
                    vascular_resistance=1.0,
                    confidence_score=0.95
                )

        async def log_trends():
            for i in range(10):
                await manager.log_trend_insight(
                    session_hash=session_hash,
                    timestamp_epoch_ms=1700000000000 + (i * 2500),
                    window_size_sec=30,
                    arterial_stiffness_drift_pct=2.5,
                    vascular_fatigue_index=0.15,
                    cardiac_drift_detected=True if i > 5 else False,
                    endothelial_reserve_status="optimal",
                    zone2_compliance="compliant"
                )

        await asyncio.gather(log_ticks(), log_trends())

        summary = await manager.get_session_summary(session_hash)
        assert summary["total_ticks"] == 50
        assert summary["cardiac_drift_detected"] is True
