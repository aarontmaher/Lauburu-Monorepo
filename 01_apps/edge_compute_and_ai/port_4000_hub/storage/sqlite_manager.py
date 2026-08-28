"""
SQLite WAL mode database manager for Port 4000 Canonical Web & Compute Hub.
Handles users, sessions, high-frequency telemetry ticks, and trend insights.
"""

import asyncio
import hashlib
import json
import logging
import os
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("port_4000_storage")

DEFAULT_DB_PATH = str(
    Path(__file__).resolve().parent.parent / "data" / "port_4000_hub.db"
)


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Generate PBKDF2-HMAC-SHA256 salted hash."""
    if salt is None:
        salt = secrets.token_hex(16)
    iterations = 100000
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations
    )
    return f"pbkdf2_sha256${iterations}${salt}${hash_bytes.hex()}"


def verify_password(stored_hash: str, password: str) -> bool:
    """Verify password against PBKDF2-HMAC-SHA256 or legacy SHA256."""
    if not stored_hash:
        return False
    if "$" in stored_hash:
        parts = stored_hash.split("$")
        if len(parts) == 4 and parts[0] == "pbkdf2_sha256":
            algo, iterations_str, salt, expected_hash = parts
            iterations = int(iterations_str)
            calc_bytes = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                iterations
            )
            return secrets.compare_digest(calc_bytes.hex(), expected_hash)
    # Legacy SHA-256 fallback compatibility
    legacy_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return secrets.compare_digest(legacy_hash, stored_hash)


def generate_session_token() -> str:
    """Generate secure 64-char hex session token."""
    return secrets.token_hex(32)


def generate_user_id() -> str:
    """Generate unique user ID."""
    return f"usr_{secrets.token_hex(5)}"


class SqliteManager:
    """
    Thread-safe, asynchronous SQLite database manager configured with WAL mode.
    Manages users, sessions, telemetry ticks, and trend insights.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
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
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Users Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                password_hash TEXT NOT NULL,
                shopify_customer_id TEXT,
                membership_tier TEXT DEFAULT 'FREE',
                is_paid_subscriber INTEGER DEFAULT 0,
                created_at_epoch INTEGER NOT NULL,
                installed_apps TEXT DEFAULT '[]',
                paired_devices TEXT DEFAULT '[]'
            );
            """)

            # 2. Sessions Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at_epoch_ms INTEGER NOT NULL,
                updated_at_epoch_ms INTEGER NOT NULL,
                expires_at_epoch INTEGER NOT NULL,
                duration_sec INTEGER DEFAULT 0,
                total_ticks INTEGER DEFAULT 0,
                mean_sbp REAL DEFAULT 0.0,
                mean_dbp REAL DEFAULT 0.0,
                mean_map REAL DEFAULT 0.0,
                mean_hr REAL DEFAULT 0.0,
                mean_rmssd REAL DEFAULT 0.0,
                cardiac_drift_detected INTEGER DEFAULT 0,
                zone2_compliance_ratio REAL DEFAULT 1.0,
                status TEXT DEFAULT 'active',
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);")

            # 3. Telemetry Ticks Table (Time-Series)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_ticks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_token TEXT NOT NULL,
                tick_epoch_ms INTEGER NOT NULL,
                delta_time_ms INTEGER NOT NULL,
                sensor_type TEXT NOT NULL,
                ptt_ms REAL,
                hr_bpm REAL,
                rr_ms REAL,
                rmssd_ms REAL,
                dfa_alpha1 REAL,
                ecg_mv REAL,
                imu_acc_g REAL,
                sbp_calc REAL,
                dbp_calc REAL,
                map_calc REAL,
                confidence_score REAL,
                FOREIGN KEY(session_token) REFERENCES sessions(session_token) ON DELETE CASCADE
            );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ticks_session_epoch ON telemetry_ticks(session_token, tick_epoch_ms);")

            # 4. Trend Insights Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS trend_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_token TEXT NOT NULL,
                timestamp_epoch_ms INTEGER NOT NULL,
                window_size_sec INTEGER NOT NULL,
                arterial_stiffness_drift_pct REAL NOT NULL,
                vascular_fatigue_index REAL NOT NULL,
                cardiac_drift_detected INTEGER NOT NULL,
                endothelial_reserve_status TEXT NOT NULL,
                zone2_compliance TEXT NOT NULL,
                FOREIGN KEY(session_token) REFERENCES sessions(session_token) ON DELETE CASCADE
            );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_insights_session ON trend_insights(session_token);")

            conn.commit()

    # ==================== User Management ====================

    def _row_to_user_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        data = dict(row)
        data["is_paid_subscriber"] = bool(data.get("is_paid_subscriber", 0))
        if isinstance(data.get("installed_apps"), str):
            try:
                data["installed_apps"] = json.loads(data["installed_apps"])
            except Exception:
                data["installed_apps"] = []
        if isinstance(data.get("paired_devices"), str):
            try:
                data["paired_devices"] = json.loads(data["paired_devices"])
            except Exception:
                data["paired_devices"] = []
        return data

    async def create_user(
        self,
        email: str,
        password: str,
        name: str,
        role: str = "user",
        membership_tier: str = "FREE",
        shopify_customer_id: Optional[str] = None,
        is_paid_subscriber: bool = False,
        installed_apps: Optional[List[str]] = None,
        paired_devices: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new user with PBKDF2 password hashing."""
        uid = user_id or generate_user_id()
        p_hash = hash_password(password)
        now_sec = int(time.time())
        apps_json = json.dumps(installed_apps or ["lauburu_zone2_endurance", "lauburu_super_app"])
        devices_json = json.dumps(paired_devices or [])
        paid_int = 1 if is_paid_subscriber else 0

        def _sync_create():
            with self._lock, self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO users (
                    id, email, name, role, password_hash, shopify_customer_id,
                    membership_tier, is_paid_subscriber, created_at_epoch,
                    installed_apps, paired_devices
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    uid, email.lower().strip(), name, role, p_hash, shopify_customer_id,
                    membership_tier, paid_int, now_sec, apps_json, devices_json
                ))
                conn.commit()
                cursor.execute("SELECT * FROM users WHERE id = ?", (uid,))
                row = cursor.fetchone()
                return self._row_to_user_dict(row)

        return await asyncio.to_thread(_sync_create)

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user record by user ID."""
        def _sync_get():
            with self._lock, self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                return self._row_to_user_dict(row) if row else None

        return await asyncio.to_thread(_sync_get)

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieve user record by email."""
        def _sync_get():
            with self._lock, self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
                row = cursor.fetchone()
                return self._row_to_user_dict(row) if row else None

        return await asyncio.to_thread(_sync_get)

    async def get_user_by_shopify_id(self, shopify_customer_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user record by Shopify customer ID."""
        def _sync_get():
            with self._lock, self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE shopify_customer_id = ?", (shopify_customer_id,))
                row = cursor.fetchone()
                return self._row_to_user_dict(row) if row else None

        return await asyncio.to_thread(_sync_get)

    async def update_user(self, user_id: str, **fields) -> Optional[Dict[str, Any]]:
        """Update fields of an existing user."""
        allowed = {
            "name", "role", "password_hash", "shopify_customer_id",
            "membership_tier", "is_paid_subscriber", "installed_apps", "paired_devices"
        }
        updates = {}
        for k, v in fields.items():
            if k in allowed:
                if k == "is_paid_subscriber":
                    updates[k] = 1 if v else 0
                elif k in ("installed_apps", "paired_devices") and isinstance(v, (list, dict)):
                    updates[k] = json.dumps(v)
                else:
                    updates[k] = v

        if not updates:
            return await self.get_user_by_id(user_id)

        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [user_id]

        def _sync_update():
            with self._lock, self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
                conn.commit()
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                return self._row_to_user_dict(row) if row else None

        return await asyncio.to_thread(_sync_update)

    # ==================== Session Management ====================

    def _row_to_session_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        data = dict(row)
        data["cardiac_drift_detected"] = bool(data.get("cardiac_drift_detected", 0))
        return data

    async def create_session(
        self,
        user_id: str,
        session_token: Optional[str] = None,
        expires_in_sec: int = 86400 * 30
    ) -> Dict[str, Any]:
        """Create a new session record for a user."""
        token = session_token or generate_session_token()
        now_ms = int(time.time() * 1000)
        expires_epoch = int(time.time()) + expires_in_sec

        def _sync_create_session():
            with self._lock, self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO sessions (
                    session_token, user_id, created_at_epoch_ms, updated_at_epoch_ms,
                    expires_at_epoch, duration_sec, total_ticks, mean_sbp, mean_dbp,
                    mean_map, mean_hr, mean_rmssd, cardiac_drift_detected,
                    zone2_compliance_ratio, status
                ) VALUES (?, ?, ?, ?, ?, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 1.0, 'active')
                """, (token, user_id, now_ms, now_ms, expires_epoch))
                conn.commit()
                cursor.execute("SELECT * FROM sessions WHERE session_token = ?", (token,))
                row = cursor.fetchone()
                return self._row_to_session_dict(row)

        return await asyncio.to_thread(_sync_create_session)

    async def get_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Retrieve session record by session token."""
        def _sync_get_session():
            with self._lock, self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM sessions WHERE session_token = ?", (session_token,))
                row = cursor.fetchone()
                return self._row_to_session_dict(row) if row else None

        return await asyncio.to_thread(_sync_get_session)

    async def get_user_and_session(self, session_token: str) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """Retrieve both user and session in a single lookup."""
        def _sync_lookup():
            with self._lock, self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM sessions WHERE session_token = ?", (session_token,))
                sess_row = cursor.fetchone()
                if not sess_row:
                    return None
                sess_dict = self._row_to_session_dict(sess_row)

                cursor.execute("SELECT * FROM users WHERE id = ?", (sess_dict["user_id"],))
                usr_row = cursor.fetchone()
                if not usr_row:
                    return None
                usr_dict = self._row_to_user_dict(usr_row)
                return usr_dict, sess_dict

        return await asyncio.to_thread(_sync_lookup)

    async def update_session(self, session_token: str, **fields) -> Optional[Dict[str, Any]]:
        """Update arbitrary session fields."""
        allowed = {
            "duration_sec", "total_ticks", "mean_sbp", "mean_dbp", "mean_map",
            "mean_hr", "mean_rmssd", "cardiac_drift_detected", "zone2_compliance_ratio",
            "status", "updated_at_epoch_ms", "expires_at_epoch"
        }
        updates = {}
        for k, v in fields.items():
            if k in allowed:
                if k == "cardiac_drift_detected":
                    updates[k] = 1 if v else 0
                else:
                    updates[k] = v
        updates["updated_at_epoch_ms"] = int(time.time() * 1000)

        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [session_token]

        def _sync_update():
            with self._lock, self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"UPDATE sessions SET {set_clause} WHERE session_token = ?", values)
                conn.commit()
                cursor.execute("SELECT * FROM sessions WHERE session_token = ?", (session_token,))
                row = cursor.fetchone()
                return self._row_to_session_dict(row) if row else None

        return await asyncio.to_thread(_sync_update)

    async def delete_session(self, session_token: str) -> bool:
        """Delete session token."""
        def _sync_delete():
            with self._lock, self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM sessions WHERE session_token = ?", (session_token,))
                conn.commit()
                return cursor.rowcount > 0

        return await asyncio.to_thread(_sync_delete)

    # ==================== Telemetry Ticks ====================

    async def log_telemetry_tick(
        self,
        session_token: str,
        tick_epoch_ms: int,
        delta_time_ms: int,
        sensor_type: str,
        ptt_ms: Optional[float] = None,
        hr_bpm: Optional[float] = None,
        rr_ms: Optional[float] = None,
        rmssd_ms: Optional[float] = None,
        dfa_alpha1: Optional[float] = None,
        ecg_mv: Optional[float] = None,
        imu_acc_g: Optional[float] = None,
        sbp_calc: Optional[float] = None,
        dbp_calc: Optional[float] = None,
        map_calc: Optional[float] = None,
        confidence_score: Optional[float] = None
    ) -> int:
        """Log a telemetry tick and atomically update session cumulative statistics."""
        def _sync_log():
            with self._lock, self._get_connection() as conn:
                cursor = conn.cursor()

                # Verify or auto-create fallback anonymous session if necessary
                cursor.execute("SELECT user_id, created_at_epoch_ms FROM sessions WHERE session_token = ?", (session_token,))
                row = cursor.fetchone()
                if not row:
                    # Auto-provision anonymous user & session
                    anon_uid = "usr_anonymous"
                    cursor.execute("SELECT id FROM users WHERE id = ?", (anon_uid,))
                    if not cursor.fetchone():
                        cursor.execute("""
                        INSERT INTO users (id, email, name, role, password_hash, created_at_epoch)
                        VALUES (?, ?, ?, 'user', 'none', ?)
                        """, (anon_uid, "anon@lauburu.local", "Anonymous Athlete", int(time.time())))
                    cursor.execute("""
                    INSERT INTO sessions (
                        session_token, user_id, created_at_epoch_ms, updated_at_epoch_ms,
                        expires_at_epoch, duration_sec, total_ticks, mean_sbp, mean_dbp,
                        mean_map, mean_hr, mean_rmssd, cardiac_drift_detected,
                        zone2_compliance_ratio, status
                    ) VALUES (?, ?, ?, ?, ?, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 1.0, 'active')
                    """, (session_token, anon_uid, tick_epoch_ms, tick_epoch_ms, int(time.time()) + 86400 * 30))

                cursor.execute("""
                INSERT INTO telemetry_ticks (
                    session_token, tick_epoch_ms, delta_time_ms, sensor_type,
                    ptt_ms, hr_bpm, rr_ms, rmssd_ms, dfa_alpha1, ecg_mv,
                    imu_acc_g, sbp_calc, dbp_calc, map_calc, confidence_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_token, tick_epoch_ms, delta_time_ms, sensor_type,
                    ptt_ms, hr_bpm, rr_ms, rmssd_ms, dfa_alpha1, ecg_mv,
                    imu_acc_g, sbp_calc, dbp_calc, map_calc, confidence_score
                ))
                tick_id = cursor.lastrowid

                # Update session rolling statistics
                cursor.execute("""
                SELECT
                    COUNT(*),
                    AVG(NULLIF(sbp_calc, 0.0)),
                    AVG(NULLIF(dbp_calc, 0.0)),
                    AVG(NULLIF(map_calc, 0.0)),
                    AVG(NULLIF(hr_bpm, 0.0)),
                    AVG(NULLIF(rmssd_ms, 0.0)),
                    MAX(delta_time_ms)
                FROM telemetry_ticks WHERE session_token = ?
                """, (session_token,))
                stats = cursor.fetchone()
                if stats and stats[0] > 0:
                    cnt, mean_s, mean_d, mean_m, mean_h, mean_r, max_delta = stats
                    dur_sec = int((max_delta or 0) / 1000)
                    cursor.execute("""
                    UPDATE sessions SET
                        updated_at_epoch_ms = ?,
                        duration_sec = ?,
                        total_ticks = ?,
                        mean_sbp = ?,
                        mean_dbp = ?,
                        mean_map = ?,
                        mean_hr = ?,
                        mean_rmssd = ?
                    WHERE session_token = ?
                    """, (
                        tick_epoch_ms,
                        dur_sec,
                        cnt,
                        round(float(mean_s or 0.0), 1),
                        round(float(mean_d or 0.0), 1),
                        round(float(mean_m or 0.0), 1),
                        round(float(mean_h or 0.0), 1),
                        round(float(mean_r or 0.0), 1),
                        session_token
                    ))

                conn.commit()
                return tick_id

        return await asyncio.to_thread(_sync_log)

    async def get_session_ticks(
        self,
        session_token: str,
        limit: int = 1000,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieve historical telemetry ticks for a session."""
        def _sync_get_ticks():
            with self._lock, self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT * FROM telemetry_ticks
                WHERE session_token = ?
                ORDER BY tick_epoch_ms ASC
                LIMIT ? OFFSET ?
                """, (session_token, limit, offset))
                return [dict(r) for r in cursor.fetchall()]

        return await asyncio.to_thread(_sync_get_ticks)

    # ==================== Trend Insights ====================

    async def log_trend_insight(
        self,
        session_token: str,
        timestamp_epoch_ms: int,
        window_size_sec: int,
        arterial_stiffness_drift_pct: float,
        vascular_fatigue_index: float,
        cardiac_drift_detected: bool,
        endothelial_reserve_status: str,
        zone2_compliance: str
    ) -> int:
        """Log a trend insight evaluation for a session."""
        drift_int = 1 if cardiac_drift_detected else 0

        def _sync_log_trend():
            with self._lock, self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO trend_insights (
                    session_token, timestamp_epoch_ms, window_size_sec,
                    arterial_stiffness_drift_pct, vascular_fatigue_index,
                    cardiac_drift_detected, endothelial_reserve_status, zone2_compliance
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_token, timestamp_epoch_ms, window_size_sec,
                    arterial_stiffness_drift_pct, vascular_fatigue_index,
                    drift_int, endothelial_reserve_status, zone2_compliance
                ))
                insight_id = cursor.lastrowid
                cursor.execute("""
                UPDATE sessions SET
                    cardiac_drift_detected = ?
                WHERE session_token = ?
                """, (drift_int, session_token))
                conn.commit()
                return insight_id

        return await asyncio.to_thread(_sync_log_trend)

    async def get_trend_insights(
        self,
        session_token: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve trend insights for a session."""
        def _sync_get_insights():
            with self._lock, self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT * FROM trend_insights
                WHERE session_token = ?
                ORDER BY timestamp_epoch_ms ASC
                LIMIT ?
                """, (session_token, limit))
                results = []
                for r in cursor.fetchall():
                    item = dict(r)
                    item["cardiac_drift_detected"] = bool(item["cardiac_drift_detected"])
                    results.append(item)
                return results

        return await asyncio.to_thread(_sync_get_insights)

    async def get_session_summary(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Retrieve detailed session summary with tick counts and user profile."""
        def _sync_summary():
            with self._lock, self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM sessions WHERE session_token = ?", (session_token,))
                sess_row = cursor.fetchone()
                if not sess_row:
                    return None
                summary = self._row_to_session_dict(sess_row)

                cursor.execute("SELECT id, email, name, role, membership_tier, is_paid_subscriber FROM users WHERE id = ?", (summary["user_id"],))
                usr_row = cursor.fetchone()
                if usr_row:
                    summary["user"] = self._row_to_user_dict(usr_row)

                cursor.execute("SELECT COUNT(*) FROM telemetry_ticks WHERE session_token = ?", (session_token,))
                summary["actual_tick_count"] = cursor.fetchone()[0]
                return summary

        return await asyncio.to_thread(_sync_summary)


# Global singleton instance
_global_sqlite_manager: Optional[SqliteManager] = None


def get_sqlite_manager(db_path: Optional[str] = None) -> SqliteManager:
    global _global_sqlite_manager
    if _global_sqlite_manager is None or db_path is not None:
        _global_sqlite_manager = SqliteManager(db_path)
    return _global_sqlite_manager
