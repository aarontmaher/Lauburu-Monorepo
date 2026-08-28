"""
Storage Subsystem Test Suite.
Tests SQLite WAL concurrent operations, durability, and ChromaDB vector embeddings.
"""

import asyncio
import os
import sqlite3
import pytest
from app.core.security import generate_session_token


class TestSqliteStorage:
    def test_sqlite_wal_mode_enabled(self, sqlite_test_db):
        conn = sqlite3.connect(sqlite_test_db.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0].lower()
        conn.close()
        assert mode == "wal", f"Expected WAL journal mode, got {mode}"

    @pytest.mark.asyncio
    async def test_concurrent_tick_logging(self, sqlite_test_db):
        session_token = generate_session_token()
        await sqlite_test_db.create_or_get_session(session_token)

        async def log_single_tick(idx: int):
            await sqlite_test_db.log_telemetry_tick(
                session_hash=session_token,
                tick_epoch_ms=1785600000 + idx * 1000,
                delta_time_ms=idx * 1000,
                ptt_ms=220.0 + (idx % 10),
                hr_bpm=130.0 + (idx % 5),
                rr_ms=450.0,
                delta_t_dia_ms=280.0,
                imu_acc_g=1.05,
                e0_elasticity=400.0,
                sbp_calc=125.0 + (idx % 5),
                dbp_calc=80.0 + (idx % 3),
                map_calc=95.0,
                pulse_pressure_calc=45.0,
                vascular_resistance=1.10,
                confidence_score=0.95
            )

        # Execute 50 concurrent async writes
        tasks = [log_single_tick(i) for i in range(50)]
        await asyncio.gather(*tasks)

        summary = await sqlite_test_db.get_session_summary(session_token)
        assert summary is not None
        assert summary["total_ticks"] == 50
        assert summary["mean_sbp"] > 120.0

        ticks = await sqlite_test_db.get_session_ticks(session_token, limit=100)
        assert len(ticks) == 50


class TestVectorStorage:
    @pytest.mark.asyncio
    async def test_vector_document_indexing_and_retrieval(self, chroma_test_store):
        token1 = generate_session_token()
        token2 = generate_session_token()

        doc1 = "Session 1: Zone 2 aerobic cycling ride. Mean HR 135 BPM, SBP 126 mmHg. Minimal cardiac drift."
        doc2 = "Session 2: High intensity VO2 max intervals. Mean HR 178 BPM, SBP 165 mmHg. High vascular fatigue."

        await chroma_test_store.add_session_document(
            session_hash=token1,
            document_text=doc1,
            metadata={"session_hash": token1, "type": "zone2"}
        )
        await chroma_test_store.add_session_document(
            session_hash=token2,
            document_text=doc2,
            metadata={"session_hash": token2, "type": "vo2max"}
        )

        # Query for Zone 2 aerobic ride
        results = await chroma_test_store.query_embeddings("aerobic Zone 2 endurance cycling", top_k=2)
        assert len(results) >= 1
        assert results[0]["id"] == token1
        assert "Zone 2" in results[0]["document"]
