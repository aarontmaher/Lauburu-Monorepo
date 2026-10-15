#!/usr/bin/env python3
"""
Mesh Timeline & Dynamic Audio Election Hub
Provides cross-device event aggregation and real-time acoustic election for ambient mic handoff.
"""
import os
import time
import json
import sqlite3
import threading
from typing import Dict, Any, Optional, List

DB_PATH = "/Volumes/Lauburu-Monorepo/04_data_and_memory/screen_lens_timeline.db"
AUDIO_DIR = "/Volumes/Lauburu-Monorepo/04_data_and_memory/audio_chunks"

class MeshElectionEngine:
    def __init__(self, expiry_seconds: float = 2.5, hysteresis_db: float = 2.0):
        self.expiry_seconds = expiry_seconds
        self.hysteresis_db = hysteresis_db
        self.lock = threading.Lock()
        self.reports: Dict[str, Dict[str, Any]] = {}
        self.current_winner: Optional[str] = None
        self.winner_since: float = 0.0

    def report_amplitude(self, device_id: str, amplitude_db: float) -> Dict[str, Any]:
        with self.lock:
            now = time.time()
            self.reports[device_id] = {
                "amplitude_db": float(amplitude_db),
                "timestamp": now
            }
            # Clean expired
            active = {
                dev: rep for dev, rep in self.reports.items()
                if (now - rep["timestamp"]) <= self.expiry_seconds
            }
            self.reports = active

            if not active:
                self.current_winner = None
                return {"winning_device": None, "winner_amplitude": -160.0, "active_devices": {}}

            # Find device with highest amplitude
            sorted_devs = sorted(active.items(), key=lambda x: x[1]["amplitude_db"], reverse=True)
            candidate_id, candidate_rep = sorted_devs[0]
            candidate_amp = candidate_rep["amplitude_db"]

            if self.current_winner is None or self.current_winner not in active:
                self.current_winner = candidate_id
                self.winner_since = now
            else:
                current_amp = active[self.current_winner]["amplitude_db"]
                # Require candidate to exceed current winner by hysteresis_db
                if candidate_id != self.current_winner and (candidate_amp - current_amp) > self.hysteresis_db:
                    self.current_winner = candidate_id
                    self.winner_since = now

            return {
                "winning_device": self.current_winner,
                "winner_amplitude": active[self.current_winner]["amplitude_db"],
                "active_devices": {
                    d: {"amplitude_db": r["amplitude_db"], "age_sec": round(now - r["timestamp"], 2)}
                    for d, r in active.items()
                },
                "winner_duration_sec": round(now - self.winner_since, 2)
            }

    def get_status(self) -> Dict[str, Any]:
        with self.lock:
            now = time.time()
            active = {
                d: {"amplitude_db": r["amplitude_db"], "age_sec": round(now - r["timestamp"], 2)}
                for d, r in self.reports.items()
                if (now - r["timestamp"]) <= self.expiry_seconds
            }
            return {
                "current_winner": self.current_winner,
                "active_devices": active,
                "total_reporting": len(active)
            }

class TimelineStorage:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS timeline (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL DEFAULT 'L1_Mac_Node',
                    event_type TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    window_title TEXT,
                    element_text TEXT,
                    audio_transcript TEXT,
                    metadata TEXT
                )
            """)
            conn.commit()

    def insert_event(self, device_id: str, event_type: str, timestamp: Optional[int] = None,
                     window_title: Optional[str] = None, element_text: Optional[str] = None,
                     audio_transcript: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> int:
        if timestamp is None:
            timestamp = int(time.time() * 1000)
        meta_str = json.dumps(metadata) if metadata else None

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO timeline (device_id, event_type, timestamp, window_title, element_text, audio_transcript, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (device_id, event_type, timestamp, window_title, element_text, audio_transcript, meta_str))
            conn.commit()
            return cur.lastrowid

    def get_recent_events(self, limit: int = 50, device_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            if device_id:
                cur.execute("""
                    SELECT id, device_id, event_type, timestamp, window_title, element_text, audio_transcript, metadata
                    FROM timeline WHERE device_id = ? ORDER BY timestamp DESC LIMIT ?
                """, (device_id, limit))
            else:
                cur.execute("""
                    SELECT id, device_id, event_type, timestamp, window_title, element_text, audio_transcript, metadata
                    FROM timeline ORDER BY timestamp DESC LIMIT ?
                """, (limit,))
            rows = cur.fetchall()
            return [dict(row) for row in rows]

# Global singletons
election_engine = MeshElectionEngine()
timeline_storage = TimelineStorage()
