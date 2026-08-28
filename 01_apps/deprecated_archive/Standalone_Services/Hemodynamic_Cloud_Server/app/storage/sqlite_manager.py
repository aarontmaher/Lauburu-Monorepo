"""
SQLite WAL mode database manager for high-frequency telemetry ticks and session summaries.
"""

import asyncio
import os
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional
from app.core.config import settings


class SqliteManager:
    """
    Asynchronous, thread-safe SQLite database manager operating in WAL mode.
    Guarantees Zero-PII time-series persistence.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.SQLITE_DB_PATH
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db_sync()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def _init_db_sync(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Sessions Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_hash TEXT PRIMARY KEY,
                created_at_epoch_ms INTEGER NOT NULL,
                updated_at_epoch_ms INTEGER NOT NULL,
                duration_sec INTEGER DEFAULT 0,
                total_ticks INTEGER DEFAULT 0,
                mean_sbp REAL DEFAULT 0.0,
                mean_dbp REAL DEFAULT 0.0,
                mean_map REAL DEFAULT 0.0,
                mean_hr REAL DEFAULT 0.0,
                mean_rmssd REAL DEFAULT 0.0,
                cardiac_drift_detected INTEGER DEFAULT 0,
                zone2_compliance_ratio REAL DEFAULT 1.0,
                status TEXT DEFAULT 'active'
            );
            """)

            # 2. Telemetry Ticks Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_ticks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_hash TEXT NOT NULL,
                tick_epoch_ms INTEGER NOT NULL,
                delta_time_ms INTEGER NOT NULL,
                ptt_ms REAL NOT NULL,
                hr_bpm REAL NOT NULL,
                rr_ms REAL NOT NULL,
                delta_t_dia_ms REAL NOT NULL,
                imu_acc_g REAL NOT NULL,
                e0_elasticity REAL NOT NULL,
                sbp_calc REAL NOT NULL,
                dbp_calc REAL NOT NULL,
                map_calc REAL NOT NULL,
                pulse_pressure_calc REAL NOT NULL,
                vascular_resistance REAL NOT NULL,
                confidence_score REAL NOT NULL,
                FOREIGN KEY(session_hash) REFERENCES sessions(session_hash) ON DELETE CASCADE
            );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ticks_session_epoch ON telemetry_ticks(session_hash, tick_epoch_ms);")

            # 3. Trend Insights Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS trend_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_hash TEXT NOT NULL,
                timestamp_epoch_ms INTEGER NOT NULL,
                window_size_sec INTEGER NOT NULL,
                arterial_stiffness_drift_pct REAL NOT NULL,
                vascular_fatigue_index REAL NOT NULL,
                cardiac_drift_detected INTEGER NOT NULL,
                endothelial_reserve_status TEXT NOT NULL,
                zone2_compliance TEXT NOT NULL,
                FOREIGN KEY(session_hash) REFERENCES sessions(session_hash) ON DELETE CASCADE
            );
            """)
            conn.commit()

    async def create_or_get_session(
        self,
        session_hash: str,
        created_at_epoch_ms: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new session if not present, or fetch the existing session."""
        now_ms = created_at_epoch_ms or int(time.time() * 1000)

        def _sync_create_or_get():
            with self._lock, self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM sessions WHERE session_hash = ?", (session_hash,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                
                cursor.execute("""
                INSERT INTO sessions (
                    session_hash, created_at_epoch_ms, updated_at_epoch_ms,
                    duration_sec, total_ticks, mean_sbp, mean_dbp, mean_map,
                    mean_hr, mean_rmssd, cardiac_drift_detected, zone2_compliance_ratio, status
                ) VALUES (?, ?, ?, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 1.0, 'active')
                """, (session_hash, now_ms, now_ms))
                conn.commit()
                
                cursor.execute("SELECT * FROM sessions WHERE session_hash = ?", (session_hash,))
                return dict(cursor.fetchone())

        return await asyncio.to_thread(_sync_create_or_get)

    async def log_telemetry_tick(
        self,
        session_hash: str,
        tick_epoch_ms: int,
        delta_time_ms: int,
        ptt_ms: float,
        hr_bpm: float,
        rr_ms: float,
        delta_t_dia_ms: float,
        imu_acc_g: float,
        e0_elasticity: float,
        sbp_calc: float,
        dbp_calc: float,
        map_calc: float,
        pulse_pressure_calc: float,
        vascular_resistance: float,
        confidence_score: float
    ) -> None:
        """Log an inverted telemetry tick and update session cumulative stats."""
        def _sync_log():
            with self._lock, self._get_connection() as conn:
                cursor = conn.cursor()
                # Ensure session exists
                cursor.execute("SELECT created_at_epoch_ms FROM sessions WHERE session_hash = ?", (session_hash,))
                row = cursor.fetchone()
                if not row:
                    cursor.execute("""
                    INSERT INTO sessions (
                        session_hash, created_at_epoch_ms, updated_at_epoch_ms,
                        duration_sec, total_ticks, mean_sbp, mean_dbp, mean_map,
                        mean_hr, mean_rmssd, cardiac_drift_detected, zone2_compliance_ratio, status
                    ) VALUES (?, ?, ?, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 1.0, 'active')
                    """, (session_hash, tick_epoch_ms, tick_epoch_ms))

                # Insert tick
                cursor.execute("""
                INSERT INTO telemetry_ticks (
                    session_hash, tick_epoch_ms, delta_time_ms, ptt_ms, hr_bpm, rr_ms,
                    delta_t_dia_ms, imu_acc_g, e0_elasticity, sbp_calc, dbp_calc,
                    map_calc, pulse_pressure_calc, vascular_resistance, confidence_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_hash, tick_epoch_ms, delta_time_ms, ptt_ms, hr_bpm, rr_ms,
                    delta_t_dia_ms, imu_acc_g, e0_elasticity, sbp_calc, dbp_calc,
                    map_calc, pulse_pressure_calc, vascular_resistance, confidence_score
                ))

                # Update session rolling stats
                cursor.execute("""
                SELECT COUNT(*), AVG(sbp_calc), AVG(dbp_calc), AVG(map_calc), AVG(hr_bpm), MAX(delta_time_ms)
                FROM telemetry_ticks WHERE session_hash = ?
                """, (session_hash,))
                stats = cursor.fetchone()
                if stats and stats[0] > 0:
                    cnt, mean_s, mean_d, mean_m, mean_h, max_delta = stats
                    dur_sec = int(max_delta / 1000) if max_delta else 0
                    cursor.execute("""
                    UPDATE sessions SET
                        updated_at_epoch_ms = ?,
                        duration_sec = ?,
                        total_ticks = ?,
                        mean_sbp = ?,
                        mean_dbp = ?,
                        mean_map = ?,
                        mean_hr = ?
                    WHERE session_hash = ?
                    """, (
                        tick_epoch_ms,
                        dur_sec,
                        cnt,
                        round(float(mean_s or 0.0), 1),
                        round(float(mean_d or 0.0), 1),
                        round(float(mean_m or 0.0), 1),
                        round(float(mean_h or 0.0), 1),
                        session_hash
                    ))
                conn.commit()

        await asyncio.to_thread(_sync_log)

    async def log_trend_insight(
        self,
        session_hash: str,
        timestamp_epoch_ms: int,
        window_size_sec: int,
        arterial_stiffness_drift_pct: float,
        vascular_fatigue_index: float,
        cardiac_drift_detected: bool,
        endothelial_reserve_status: str,
        zone2_compliance: str
    ) -> None:
        """Log a trend insight evaluation for a session."""
        def _sync_log_trend():
            with self._lock, self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO trend_insights (
                    session_hash, timestamp_epoch_ms, window_size_sec,
                    arterial_stiffness_drift_pct, vascular_fatigue_index,
                    cardiac_drift_detected, endothelial_reserve_status, zone2_compliance
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_hash, timestamp_epoch_ms, window_size_sec,
                    arterial_stiffness_drift_pct, vascular_fatigue_index,
                    1 if cardiac_drift_detected else 0,
                    endothelial_reserve_status, zone2_compliance
                ))
                # Update session drift status
                cursor.execute("""
                UPDATE sessions SET
                    cardiac_drift_detected = ?
                WHERE session_hash = ?
                """, (1 if cardiac_drift_detected else 0, session_hash))
                conn.commit()

        await asyncio.to_thread(_sync_log_trend)

    async def get_session_summary(self, session_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve aggregated metrics for a specific session."""
        def _sync_get_summary():
            with self._lock, self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM sessions WHERE session_hash = ?", (session_hash,))
                row = cursor.fetchone()
                if not row:
                    return None
                res = dict(row)
                res["cardiac_drift_detected"] = bool(res["cardiac_drift_detected"])
                return res

        return await asyncio.to_thread(_sync_get_summary)

    async def get_session_ticks(self, session_hash: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Fetch the most recent telemetry ticks for a session."""
        def _sync_get_ticks():
            with self._lock, self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT * FROM telemetry_ticks
                WHERE session_hash = ?
                ORDER BY tick_epoch_ms ASC LIMIT ?
                """, (session_hash, limit))
                return [dict(r) for r in cursor.fetchall()]

        return await asyncio.to_thread(_sync_get_ticks)


_global_sqlite_manager: Optional[SqliteManager] = None


def get_sqlite_manager(db_path: Optional[str] = None) -> SqliteManager:
    global _global_sqlite_manager
    if _global_sqlite_manager is None or db_path is not None:
        _global_sqlite_manager = SqliteManager(db_path)
    return _global_sqlite_manager
