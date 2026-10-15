"""Comprehensive Unit and Integration Test Suite for ScreenpipeService (Milestone 1).

Tests:
1. NormalizedBoundingBox geometric transformations, clamping, and scaling.
2. Security & SQL Sanitization (SELECT-only and LIMIT enforcement).
3. ScreenpipeDirectSqlite (F1_SCREENPIPE_SQLITE) immutable read-only operations.
4. ScreenpipeRestClient (F2_SCREENPIPE_REST_CLIENT) authentication & endpoint operations.
5. ScreenpipeService (F3_SCREENPIPE_METAL_VISION + Fallback) integration and resilience.
6. Asynchronous execution across all methods.
"""

import asyncio
import json
import sqlite3
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

from screenpipe_service import (
    NormalizedBoundingBox,
    ScreenpipeAuthError,
    ScreenpipeConnectionError,
    ScreenpipeDirectSqlite,
    ScreenpipeRestClient,
    ScreenpipeSecurityError,
    ScreenpipeService,
    validate_and_sanitize_sql,
)

# ============================================================================
# 1. Geometry & Normalized Bounding Box Tests
# ============================================================================


class TestNormalizedBoundingBox(unittest.TestCase):
    """Tests for NormalizedBoundingBox data model and coordinates."""

    def test_default_initialization(self) -> None:
        bbox = NormalizedBoundingBox()
        self.assertEqual(bbox.ymin, 0.0)
        self.assertEqual(bbox.xmin, 0.0)
        self.assertEqual(bbox.ymax, 0.0)
        self.assertEqual(bbox.xmax, 0.0)
        self.assertFalse(bbox.is_valid)

    def test_valid_bounding_box(self) -> None:
        bbox = NormalizedBoundingBox(ymin=0.1, xmin=0.2, ymax=0.5, xmax=0.8)
        self.assertAlmostEqual(bbox.width, 0.6)
        self.assertAlmostEqual(bbox.height, 0.4)
        self.assertAlmostEqual(bbox.center_x, 0.5)
        self.assertAlmostEqual(bbox.center_y, 0.3)
        self.assertAlmostEqual(bbox.area, 0.24)
        self.assertTrue(bbox.is_valid)

        coord_list = bbox.to_list()
        self.assertEqual(coord_list, [0.1, 0.2, 0.5, 0.8])

    def test_coordinate_clamping(self) -> None:
        # Out-of-bound coordinates should be clamped to [0.0, 1.0]
        bbox = NormalizedBoundingBox(ymin=-0.5, xmin=-0.2, ymax=1.5, xmax=2.0)
        self.assertEqual(bbox.ymin, 0.0)
        self.assertEqual(bbox.xmin, 0.0)
        self.assertEqual(bbox.ymax, 1.0)
        self.assertEqual(bbox.xmax, 1.0)

    def test_from_bounds_conversion(self) -> None:
        # Screenpipe columns: left=0.2, top=0.1, width=0.4, height=0.3
        bbox = NormalizedBoundingBox.from_bounds(left_bound=0.2, top_bound=0.1, width_bound=0.4, height_bound=0.3)
        self.assertAlmostEqual(bbox.ymin, 0.1)
        self.assertAlmostEqual(bbox.xmin, 0.2)
        self.assertAlmostEqual(bbox.ymax, 0.4)
        self.assertAlmostEqual(bbox.xmax, 0.6)
        self.assertEqual(bbox.to_list(), [0.1, 0.2, 0.4, 0.6])

    def test_from_bounds_with_none(self) -> None:
        bbox = NormalizedBoundingBox.from_bounds(None, None, None, None)
        self.assertEqual(bbox.to_list(), [0.0, 0.0, 0.0, 0.0])

    def test_from_list(self) -> None:
        bbox = NormalizedBoundingBox.from_list([0.05, 0.15, 0.45, 0.85])
        self.assertAlmostEqual(bbox.ymin, 0.05)
        self.assertAlmostEqual(bbox.xmin, 0.15)
        self.assertAlmostEqual(bbox.ymax, 0.45)
        self.assertAlmostEqual(bbox.xmax, 0.85)

        with self.assertRaises(ValueError):
            NormalizedBoundingBox.from_list([0.1, 0.2, 0.3])

    def test_scale_to_pixels(self) -> None:
        bbox = NormalizedBoundingBox(ymin=0.1, xmin=0.2, ymax=0.5, xmax=0.8)
        pixels = bbox.scale_to_pixels(screen_width=1920, screen_height=1080)
        self.assertEqual(pixels["left"], 384)
        self.assertEqual(pixels["top"], 108)
        self.assertEqual(pixels["right"], 1536)
        self.assertEqual(pixels["bottom"], 540)
        self.assertEqual(pixels["width"], 1152)
        self.assertEqual(pixels["height"], 432)


# ============================================================================
# 2. Security & SQL Sanitization Tests
# ============================================================================


class TestSqlSanitization(unittest.TestCase):
    """Tests for SQL safety guards and LIMIT enforcement."""

    def test_safe_select_without_limit(self) -> None:
        query = "SELECT * FROM frames"
        sanitized = validate_and_sanitize_sql(query, default_limit=50)
        self.assertEqual(sanitized, "SELECT * FROM frames LIMIT 50")

    def test_safe_select_with_existing_limit(self) -> None:
        query = "SELECT id, app_name FROM frames LIMIT 25"
        sanitized = validate_and_sanitize_sql(query)
        self.assertEqual(sanitized, "SELECT id, app_name FROM frames LIMIT 25")

    def test_limit_clamped_if_exceeding_max(self) -> None:
        query = "SELECT * FROM elements LIMIT 50000"
        sanitized = validate_and_sanitize_sql(query, max_limit=10000)
        self.assertEqual(sanitized, "SELECT * FROM elements LIMIT 10000")

    def test_safe_with_and_explain_queries(self) -> None:
        query_with = "WITH active AS (SELECT id FROM frames) SELECT * FROM active"
        sanitized_with = validate_and_sanitize_sql(query_with, default_limit=10)
        self.assertTrue(sanitized_with.endswith("LIMIT 10"))

        query_explain = "EXPLAIN QUERY PLAN SELECT * FROM frames"
        sanitized_explain = validate_and_sanitize_sql(query_explain)
        self.assertTrue("LIMIT" in sanitized_explain)

    def test_forbidden_mutating_statements_rejected(self) -> None:
        mutating = [
            "INSERT INTO memories (content) VALUES ('hack')",
            "UPDATE memories SET importance = 1.0",
            "DELETE FROM frames WHERE id = 1",
            "DROP TABLE elements",
            "ALTER TABLE frames ADD COLUMN leak TEXT",
            "CREATE TABLE evil (id INT)",
            "PRAGMA table_info(frames)",
            "ATTACH DATABASE 'leak.db' AS leak",
            "REPLACE INTO memories (id) VALUES (1)",
            "TRUNCATE TABLE ui_events",
            "VACUUM",
        ]
        for bad_sql in mutating:
            with self.assertRaises(ScreenpipeSecurityError, msg=f"Should reject: {bad_sql}"):
                validate_and_sanitize_sql(bad_sql)

    def test_semicolon_injection_rejected(self) -> None:
        injections = [
            "SELECT * FROM frames; DROP TABLE frames;",
            "SELECT 1; SELECT 2;",
            "SELECT * FROM frames WHERE id = 1; DELETE FROM frames;",
        ]
        for inj in injections:
            with self.assertRaises(ScreenpipeSecurityError, msg=f"Should reject: {inj}"):
                validate_and_sanitize_sql(inj)

    def test_empty_query_rejected(self) -> None:
        with self.assertRaises(ScreenpipeSecurityError):
            validate_and_sanitize_sql("")
        with self.assertRaises(ScreenpipeSecurityError):
            validate_and_sanitize_sql("   ")


# ============================================================================
# 3. Direct SQLite Interface Tests (F1_SCREENPIPE_SQLITE)
# ============================================================================


class TestScreenpipeDirectSqlite(unittest.TestCase):
    """Tests for direct SQLite querying with realistic schema and data."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_db.sqlite"
        self._init_mock_database(self.db_path)
        self.sqlite_client = ScreenpipeDirectSqlite(db_path=self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _init_mock_database(self, path: Path) -> None:
        conn = sqlite3.connect(path)
        c = conn.cursor()
        # Create schema
        c.execute("""
            CREATE TABLE frames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                name TEXT,
                app_name TEXT,
                window_name TEXT,
                focused BOOLEAN,
                browser_url TEXT,
                device_name TEXT DEFAULT '',
                snapshot_path TEXT,
                accessibility_text TEXT,
                accessibility_tree_json TEXT,
                full_text TEXT,
                text_json TEXT
            );
        """)
        c.execute("""
            CREATE TABLE elements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frame_id INTEGER NOT NULL REFERENCES frames(id),
                source TEXT NOT NULL,
                role TEXT NOT NULL,
                text TEXT,
                parent_id INTEGER,
                depth INTEGER DEFAULT 0,
                left_bound REAL,
                top_bound REAL,
                width_bound REAL,
                height_bound REAL,
                confidence REAL,
                sort_order INTEGER DEFAULT 0,
                properties TEXT,
                on_screen INTEGER DEFAULT 1
            );
        """)
        c.execute("""
            CREATE TABLE ui_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT,
                relative_ms INTEGER DEFAULT 0,
                event_type TEXT NOT NULL,
                x INTEGER, y INTEGER,
                delta_x INTEGER, delta_y INTEGER,
                button INTEGER, click_count INTEGER,
                key_code INTEGER, modifiers INTEGER,
                text_content TEXT,
                app_name TEXT, app_pid INTEGER,
                window_title TEXT, browser_url TEXT,
                element_role TEXT, element_name TEXT,
                element_bounds TEXT, frame_id INTEGER
            );
        """)
        c.execute("""
            CREATE TABLE audio_transcriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                transcription TEXT NOT NULL,
                device TEXT DEFAULT '',
                transcription_engine TEXT DEFAULT 'Whisper'
            );
        """)
        c.execute("""
            CREATE TABLE memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                source TEXT DEFAULT 'user',
                source_context TEXT,
                tags TEXT DEFAULT '[]',
                importance REAL DEFAULT 0.5,
                frame_id INTEGER,
                created_at TEXT DEFAULT '2026-08-31T00:00:00Z',
                updated_at TEXT DEFAULT '2026-08-31T00:00:00Z'
            );
        """)

        # Insert seed data
        c.execute("""
            INSERT INTO frames (id, timestamp, app_name, window_name, focused, browser_url, full_text, accessibility_text)
            VALUES (1, '2026-08-31T10:00:00Z', 'Google Chrome', 'Lauburu AI - Obsidian Graph', 1, 'http://localhost:4000',
                    'Welcome to Lauburu Mesh Dashboard', 'Button: Submit, Input: Search')
        """)
        c.execute("""
            INSERT INTO frames (id, timestamp, app_name, window_name, focused, browser_url, full_text, accessibility_text)
            VALUES (2, '2026-08-31T10:01:00Z', 'Visual Studio Code', 'screenpipe_service.py - Lauburu', 1, NULL,
                    'class ScreenpipeService: def get_health_status(self):', 'Editor Code Window')
        """)

        # Insert elements for frame 1
        c.execute("""
            INSERT INTO elements (id, frame_id, source, role, text, parent_id, depth, left_bound, top_bound, width_bound, height_bound, confidence, sort_order)
            VALUES (101, 1, 'ocr', 'line', 'Welcome to Lauburu Mesh Dashboard', NULL, 0, 0.1, 0.1, 0.5, 0.05, 98.5, 0)
        """)
        c.execute("""
            INSERT INTO elements (id, frame_id, source, role, text, parent_id, depth, left_bound, top_bound, width_bound, height_bound, confidence, sort_order)
            VALUES (102, 1, 'accessibility', 'AXButton', 'Submit', 101, 1, 0.6, 0.1, 0.1, 0.05, 100.0, 1)
        """)

        # Insert UI events
        c.execute("""
            INSERT INTO ui_events (id, timestamp, event_type, x, y, app_name, window_title, text_content, frame_id)
            VALUES (201, '2026-08-31T10:00:05Z', 'click', 500, 300, 'Google Chrome', 'Lauburu AI - Obsidian Graph', NULL, 1)
        """)
        c.execute("""
            INSERT INTO ui_events (id, timestamp, event_type, x, y, app_name, window_title, text_content, frame_id)
            VALUES (202, '2026-08-31T10:00:10Z', 'key', NULL, NULL, 'Google Chrome', 'Lauburu AI - Obsidian Graph', 'hello world', 1)
        """)

        # Insert memory
        c.execute("""
            INSERT INTO memories (id, content, source, tags, importance, frame_id)
            VALUES (301, 'User opened Lauburu Mesh Dashboard', 'agent', '["dashboard", "navigation"]', 0.85, 1)
        """)

        conn.commit()
        conn.close()

    def test_is_available(self) -> None:
        self.assertTrue(self.sqlite_client.is_available())
        missing_client = ScreenpipeDirectSqlite(db_path="/tmp/non_existent_screenpipe_db.sqlite")
        self.assertFalse(missing_client.is_available())

    def test_get_recent_frames(self) -> None:
        frames = self.sqlite_client.get_recent_frames(limit=5)
        self.assertEqual(len(frames), 2)
        # Verify order DESC
        self.assertEqual(frames[0].id, 2)
        self.assertEqual(frames[0].app_name, "Visual Studio Code")
        self.assertEqual(frames[1].id, 1)
        self.assertEqual(frames[1].app_name, "Google Chrome")
        self.assertEqual(len(frames[1].elements), 2)

    def test_get_elements_for_frame(self) -> None:
        elements = self.sqlite_client.get_elements_for_frame(frame_id=1)
        self.assertEqual(len(elements), 2)
        root_elem = elements[0]
        self.assertEqual(root_elem.id, 101)
        self.assertEqual(root_elem.text, "Welcome to Lauburu Mesh Dashboard")
        self.assertAlmostEqual(root_elem.bbox.ymin, 0.1)
        self.assertAlmostEqual(root_elem.bbox.xmin, 0.1)
        self.assertAlmostEqual(root_elem.bbox.ymax, 0.15)
        self.assertAlmostEqual(root_elem.bbox.xmax, 0.6)
        self.assertAlmostEqual(root_elem.confidence, 0.985)

    def test_get_frame_by_id(self) -> None:
        frame = self.sqlite_client.get_frame_by_id(1)
        self.assertIsNotNone(frame)
        assert frame is not None
        self.assertEqual(frame.id, 1)
        self.assertEqual(frame.app_name, "Google Chrome")
        self.assertEqual(len(frame.elements), 2)

        none_frame = self.sqlite_client.get_frame_by_id(9999)
        self.assertIsNone(none_frame)

    def test_get_recent_ui_events(self) -> None:
        events = self.sqlite_client.get_recent_ui_events(limit=10)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].id, 202)
        self.assertEqual(events[0].event_type, "key")
        self.assertEqual(events[0].text_content, "hello world")

        click_events = self.sqlite_client.get_recent_ui_events(event_type="click")
        self.assertEqual(len(click_events), 1)
        self.assertEqual(click_events[0].event_type, "click")
        self.assertEqual(click_events[0].x, 500)

    def test_get_memories(self) -> None:
        memories = self.sqlite_client.get_memories(limit=10)
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0].id, 301)
        self.assertIn("dashboard", memories[0].tags)
        self.assertAlmostEqual(memories[0].importance, 0.85)

    def test_search_text(self) -> None:
        matches = self.sqlite_client.search_text(query="Lauburu", limit=10)
        self.assertTrue(len(matches) >= 1)
        match_texts = [m["text"] for m in matches]
        self.assertTrue(any("Lauburu" in t for t in match_texts))

    def test_get_active_windows(self) -> None:
        windows = self.sqlite_client.get_active_windows()
        self.assertEqual(len(windows), 2)
        apps = [w["app_name"] for w in windows]
        self.assertIn("Google Chrome", apps)
        self.assertIn("Visual Studio Code", apps)


# ============================================================================
# 4. REST API Client Tests (F2_SCREENPIPE_REST_CLIENT)
# ============================================================================


class TestScreenpipeRestClient(unittest.TestCase):
    """Tests for Screenpipe REST API client with mock HTTP handlers."""

    def setUp(self) -> None:
        self.client = ScreenpipeRestClient(
            base_url="http://127.0.0.1:3030",
            api_key="test-api-key-12345",
        )

    def test_headers_include_bearer_auth(self) -> None:
        headers = self.client._headers()
        self.assertEqual(headers["Authorization"], "Bearer test-api-key-12345")
        self.assertEqual(headers["Content-Type"], "application/json")

    @patch("urllib.request.urlopen")
    def test_get_health(self, mock_urlopen: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps(
            {"status": "ok", "version": "0.1.0", "last_frame_timestamp": "2026-08-31T10:00:00Z"}
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        health = self.client.get_health()
        self.assertEqual(health["status"], "ok")
        self.assertEqual(health["version"], "0.1.0")

    @patch("urllib.request.urlopen")
    def test_search_endpoint(self, mock_urlopen: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps(
            {
                "data": [
                    {
                        "type": "ocr",
                        "content": {
                            "frame_id": 42,
                            "text": "Mesh Telemetry Active",
                            "app_name": "Terminal",
                            "window_name": "zsh",
                        },
                        "score": 0.95,
                    }
                ],
                "pagination": {"limit": 20, "offset": 0, "total": 1},
            }
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = self.client.search(q="Telemetry", content_type="ocr")
        self.assertIn("data", res)
        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["content"]["text"], "Mesh Telemetry Active")

    @patch("urllib.request.urlopen")
    def test_raw_sql_safe_execution(self, mock_urlopen: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps([{"count": 42}]).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = self.client.raw_sql("SELECT count(*) as count FROM frames")
        self.assertEqual(res, [{"count": 42}])

    def test_raw_sql_blocks_mutations(self) -> None:
        with self.assertRaises(ScreenpipeSecurityError):
            self.client.raw_sql("DELETE FROM frames")

    @patch("urllib.request.urlopen")
    def test_auth_failure_raises_screenpipe_auth_error(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://127.0.0.1:3030/search",
            code=403,
            msg="Forbidden",
            hdrs={},
            fp=None,
        )
        with self.assertRaises(ScreenpipeAuthError):
            self.client.search(q="test")

    @patch("urllib.request.urlopen")
    def test_server_down_raises_connection_error(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        with self.assertRaises(ScreenpipeConnectionError):
            self.client.get_health()

    def test_secrets_auto_discovery(self) -> None:
        # Create temporary secrets.sqlite
        with tempfile.TemporaryDirectory() as tmpdir:
            sec_path = Path(tmpdir) / "secrets.sqlite"
            conn = sqlite3.connect(sec_path)
            c = conn.cursor()
            c.execute("CREATE TABLE secrets (key TEXT PRIMARY KEY, value BLOB);")
            # Store base64 encoded token
            c.execute("INSERT INTO secrets (key, value) VALUES ('api_auth_key', ?)", (b"c3AtYXV0b2tleS05ODc2NQ==",))
            conn.commit()
            conn.close()

            client = ScreenpipeRestClient(secrets_path=sec_path)
            self.assertEqual(client.api_key, "sp-autokey-98765")


# ============================================================================
# 5. ScreenpipeService Unified & Fallback Tests (F3_SCREENPIPE_METAL_VISION)
# ============================================================================


class TestScreenpipeService(unittest.TestCase):
    """Tests for the unified ScreenpipeService, fallback resilience, and vision trees."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "db.sqlite"
        self._init_database(self.db_path)

        self.service = ScreenpipeService(
            base_url="http://127.0.0.1:3030",
            api_key="sp-test-key",
            db_path=self.db_path,
            prefer_direct_sqlite=False,
            auto_fallback=True,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _init_database(self, path: Path) -> None:
        conn = sqlite3.connect(path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE frames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                name TEXT,
                app_name TEXT,
                window_name TEXT,
                focused BOOLEAN,
                browser_url TEXT,
                device_name TEXT DEFAULT '',
                snapshot_path TEXT,
                accessibility_text TEXT,
                accessibility_tree_json TEXT,
                full_text TEXT,
                text_json TEXT
            );
        """)
        c.execute("""
            CREATE TABLE elements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frame_id INTEGER NOT NULL REFERENCES frames(id),
                source TEXT NOT NULL,
                role TEXT NOT NULL,
                text TEXT,
                parent_id INTEGER,
                depth INTEGER DEFAULT 0,
                left_bound REAL,
                top_bound REAL,
                width_bound REAL,
                height_bound REAL,
                confidence REAL,
                sort_order INTEGER DEFAULT 0,
                properties TEXT,
                on_screen INTEGER DEFAULT 1
            );
        """)
        c.execute("""
            CREATE TABLE ui_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT,
                relative_ms INTEGER DEFAULT 0,
                event_type TEXT NOT NULL,
                x INTEGER, y INTEGER,
                delta_x INTEGER, delta_y INTEGER,
                button INTEGER, click_count INTEGER,
                key_code INTEGER, modifiers INTEGER,
                text_content TEXT,
                app_name TEXT, app_pid INTEGER,
                window_title TEXT, browser_url TEXT,
                element_role TEXT, element_name TEXT,
                element_bounds TEXT, frame_id INTEGER
            );
        """)
        c.execute("""
            CREATE TABLE memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                source TEXT DEFAULT 'user',
                source_context TEXT,
                tags TEXT DEFAULT '[]',
                importance REAL DEFAULT 0.5,
                frame_id INTEGER,
                created_at TEXT DEFAULT '2026-08-31T00:00:00Z',
                updated_at TEXT DEFAULT '2026-08-31T00:00:00Z'
            );
        """)

        # Add Frame 1 with nested element tree
        c.execute("""
            INSERT INTO frames (id, timestamp, app_name, window_name, focused, browser_url, full_text, accessibility_text)
            VALUES (1, '2026-08-31T12:00:00Z', 'Finder', 'Desktop', 1, NULL, 'Applications Documents Downloads', 'Desktop Window')
        """)
        # Root element 1
        c.execute("""
            INSERT INTO elements (id, frame_id, source, role, text, parent_id, depth, left_bound, top_bound, width_bound, height_bound, confidence, sort_order)
            VALUES (10, 1, 'ocr', 'block', 'Header Menu', NULL, 0, 0.0, 0.0, 1.0, 0.1, 99.0, 0)
        """)
        # Child element of root 1
        c.execute("""
            INSERT INTO elements (id, frame_id, source, role, text, parent_id, depth, left_bound, top_bound, width_bound, height_bound, confidence, sort_order)
            VALUES (11, 1, 'ocr', 'word', 'Applications', 10, 1, 0.05, 0.02, 0.15, 0.05, 95.0, 1)
        """)
        # Child element of root 1
        c.execute("""
            INSERT INTO elements (id, frame_id, source, role, text, parent_id, depth, left_bound, top_bound, width_bound, height_bound, confidence, sort_order)
            VALUES (12, 1, 'ocr', 'word', 'Documents', 10, 1, 0.25, 0.02, 0.15, 0.05, 96.0, 2)
        """)

        conn.commit()
        conn.close()

    def test_parse_element_tree_hierarchy(self) -> None:
        tree = self.service.parse_element_tree(frame_id=1)
        self.assertEqual(len(tree), 1, "Should have 1 root element")
        root = tree[0]
        self.assertEqual(root["id"], 10)
        self.assertEqual(root["role"], "block")
        self.assertEqual(len(root["children"]), 2, "Root should have 2 children")
        self.assertEqual(root["children"][0]["text"], "Applications")
        self.assertEqual(root["children"][1]["text"], "Documents")

    @patch("urllib.request.urlopen")
    def test_automatic_fallback_when_rest_fails(self, mock_urlopen: MagicMock) -> None:
        # Mock REST failure (503 Service Unavailable)
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://127.0.0.1:3030/search",
            code=503,
            msg="Service Unavailable",
            hdrs={},
            fp=None,
        )

        # Calling get_latest_frame_context should seamlessly fall back to SQLite
        contexts = self.service.get_latest_frame_context(limit=5)
        self.assertTrue(self.service.fallback_active)
        self.assertIsNotNone(self.service.last_fallback_reason)
        self.assertEqual(len(contexts), 1)
        self.assertEqual(contexts[0]["app_name"], "Finder")
        self.assertEqual(len(contexts[0]["elements"]), 3)

    @patch("urllib.request.urlopen")
    def test_query_screen_text_fallback(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        matches = self.service.query_screen_text(query="Documents", limit=10)
        self.assertTrue(self.service.fallback_active)
        self.assertTrue(len(matches) >= 1)
        self.assertTrue(any("Documents" in m["text"] for m in matches))

    def test_get_focused_window(self) -> None:
        focused = self.service.get_focused_window()
        self.assertIsNotNone(focused)
        assert focused is not None
        self.assertEqual(focused["app_name"], "Finder")
        self.assertEqual(focused["window_name"], "Desktop")

    def test_execute_sql_direct(self) -> None:
        # In direct sqlite mode
        self.service.prefer_direct_sqlite = True
        res = self.service.execute_sql("SELECT count(*) as total FROM frames")
        self.assertEqual(res, [{"total": 1}])


# ============================================================================
# 6. Async Execution Tests
# ============================================================================


class TestAsyncExecution(unittest.TestCase):
    """Tests async wrapper methods across ScreenpipeService."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "async_test.sqlite"
        self._init_db(self.db_path)
        self.service = ScreenpipeService(
            db_path=self.db_path,
            prefer_direct_sqlite=True,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _init_db(self, path: Path) -> None:
        conn = sqlite3.connect(path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE frames (
                id INTEGER PRIMARY KEY,
                timestamp TIMESTAMP,
                app_name TEXT,
                window_name TEXT,
                focused BOOLEAN,
                browser_url TEXT,
                device_name TEXT DEFAULT '',
                snapshot_path TEXT,
                accessibility_text TEXT,
                accessibility_tree_json TEXT,
                full_text TEXT,
                text_json TEXT
            );
        """)
        c.execute("""
            CREATE TABLE elements (
                id INTEGER PRIMARY KEY,
                frame_id INTEGER,
                source TEXT,
                role TEXT,
                text TEXT,
                parent_id INTEGER,
                depth INTEGER,
                left_bound REAL,
                top_bound REAL,
                width_bound REAL,
                height_bound REAL,
                confidence REAL,
                sort_order INTEGER,
                properties TEXT,
                on_screen INTEGER
            );
        """)
        c.execute("""
            CREATE TABLE memories (
                id INTEGER PRIMARY KEY,
                content TEXT,
                source TEXT,
                source_context TEXT,
                tags TEXT,
                importance REAL,
                frame_id INTEGER,
                created_at TEXT,
                updated_at TEXT
            );
        """)
        c.execute("""
            INSERT INTO frames (id, timestamp, app_name, window_name, focused, full_text)
            VALUES (1, '2026-08-31T15:00:00Z', 'Terminal', 'bash', 1, 'echo hello async')
        """)
        conn.commit()
        conn.close()

    def test_async_service_methods(self) -> None:
        async def run_async_tests() -> None:
            # 1. Health status
            health = await self.service.get_health_status_async()
            self.assertTrue(health["sqlite_healthy"])

            # 2. Latest frame context
            frames = await self.service.get_latest_frame_context_async(limit=5)
            self.assertEqual(len(frames), 1)
            self.assertEqual(frames[0]["app_name"], "Terminal")

            # 3. Query screen text
            matches = await self.service.query_screen_text_async("hello", limit=5)
            self.assertEqual(len(matches), 1)

            # 4. SQL execution
            sql_res = await self.service.execute_sql_async("SELECT count(*) as c FROM frames")
            self.assertEqual(sql_res, [{"c": 1}])

        asyncio.run(run_async_tests())


# ============================================================================
# 7. Live System Integration Tests (If daemon/db available)
# ============================================================================


class TestLiveSystemIntegration(unittest.TestCase):
    """Probes the live local environment (~/.screenpipe/db.sqlite and localhost:3030)."""

    def test_live_sqlite_integration(self) -> None:
        live_db = Path.home() / ".screenpipe" / "db.sqlite"
        if not live_db.exists():
            self.skipTest("Live ~/.screenpipe/db.sqlite not present")

        sqlite_client = ScreenpipeDirectSqlite()
        self.assertTrue(sqlite_client.is_available())
        # Query schema without error
        res = sqlite_client.execute_query("SELECT count(*) as c FROM frames")
        self.assertIsInstance(res, list)
        self.assertEqual(len(res), 1)
        self.assertIn("c", res[0])

    def test_live_rest_client_health(self) -> None:
        rest_client = ScreenpipeRestClient()
        try:
            health = rest_client.get_health()
            self.assertIn("status", health)
        except ScreenpipeConnectionError:
            self.skipTest("Screenpipe daemon is not currently listening on port 3030")

    def test_live_service_unified(self) -> None:
        service = ScreenpipeService()
        status = service.get_health_status()
        self.assertIn("status", status)
        self.assertIn("sqlite_healthy", status)
        # Should not throw any exception even if empty or degraded
        contexts = service.get_latest_frame_context(limit=5)
        self.assertIsInstance(contexts, list)


if __name__ == "__main__":
    unittest.main()
