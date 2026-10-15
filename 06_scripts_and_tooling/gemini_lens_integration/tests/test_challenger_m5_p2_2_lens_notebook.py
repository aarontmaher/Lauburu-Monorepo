"""Empirical Adversarial Challenge Suite for Phase 2 Tier 5 Hardening (Milestone 5).

Authored by challenger_m5_p2_2 (teamwork_preview_challenger).
Target modules: lens_client.py, notebook_sync.py

Adversarially challenges, stress-tests, and empirically audits:
1. ScreenLensClient 3-Port Cascade Fallthrough (3037 500 -> 3035 corrupt JSON -> 4003 valid).
2. ScreenLensClient SQLite Corrupted Primary Fallback to secondary valid DB.
3. ScreenLensClient Dynamic SQLite Table & Column Schema Discovery (app, window, snippet, etc.).
4. ScreenLensClient Gemini Spark SSE Non-JSON Stream Handling (Port 9999 text/event-stream).
5. ScreenLensClient Extreme Timestamp Normalization (nanoseconds 1e18, seconds, None, invalid strings).
6. NotebookSynchronizer Malformed recentProjects.xml Regex Recovery (unclosed XML, build & workspaceId).
7. NotebookSynchronizer Corrupted Existing .ipynb Recovery (invalid JSON -> canonical v4.5 notebook).
8. NotebookSynchronizer Sync Cell Deduplication (updates only first sync cell, cell count invariant).
9. NotebookSynchronizer 5-Rule Colab GPU Offload Combinatorial Decision Matrix.
10. NotebookSynchronizer 20-Thread Concurrent File Write Race Safety (100% valid JSON, no corruption).
"""

from __future__ import annotations

import concurrent.futures
import datetime
import json
import logging
import os
import sqlite3
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lens_client import ScreenLensClient, normalize_iso_timestamp
from notebook_sync import (
    DEFAULT_MIN_RAM_SANCTUARY_GB,
    SYNC_HEADER_PREFIX,
    SYNC_TAG,
    NotebookSynchronizer,
)


# ============================================================================
# Test Fixtures & Mock Helpers
# ============================================================================

class MockHTTPResponse:
    """Mock context-managed HTTP response for urllib OpenerDirector."""

    def __init__(
        self,
        status: int,
        body: bytes,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.status = status
        self.code = status
        self._body = body
        self.headers = headers or {}

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> MockHTTPResponse:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass


class CascadeMockOpener(urllib.request.OpenerDirector):
    """OpenerDirector simulating multi-port endpoints and routing failures."""

    def __init__(
        self, routing_map: Dict[str, Union[MockHTTPResponse, Exception]]
    ) -> None:
        super().__init__()
        self.routing_map = routing_map
        self.call_history: List[str] = []

    def open(
        self, fullurl: Union[str, urllib.request.Request], data: Any = None, timeout: Any = None
    ) -> MockHTTPResponse:
        url = fullurl.full_url if hasattr(fullurl, "full_url") else str(fullurl)
        self.call_history.append(url)
        for pattern, response in self.routing_map.items():
            if pattern in url:
                if isinstance(response, Exception):
                    raise response
                return response
        raise urllib.error.URLError(f"Connection refused to {url}")


@pytest.fixture
def isolated_env(tmp_path: Path):
    """Provides isolated filesystem directories for hermetic testing."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    idea_dir = repo_dir / ".idea"
    idea_dir.mkdir(parents=True, exist_ok=True)
    options_dir = tmp_path / "options"
    options_dir.mkdir(parents=True, exist_ok=True)
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    nb_path = repo_dir / "lens_global_orchestrator.ipynb"
    meta_path = idea_dir / "lens_context.json"
    recent_xml = options_dir / "recentProjects.xml"

    return {
        "root": tmp_path,
        "repo_dir": repo_dir,
        "idea_dir": idea_dir,
        "options_dir": options_dir,
        "workspace_dir": workspace_dir,
        "nb_path": nb_path,
        "meta_path": meta_path,
        "recent_xml": recent_xml,
    }


# ============================================================================
# Vector 1: ScreenLensClient 3-Port Cascade Fallthrough
# ============================================================================

class TestChallengerM5LensClientCascade:
    """Vector 1: 3-Port cascade fallthrough across Ports 3037, 3035, and 4003."""

    def test_three_port_cascade_fallthrough_3037_500_3035_corrupt_4003_success(self):
        """Port 3037 returns 500, Port 3035 returns corrupt JSON, Port 4003 returns valid data -> harvests from 4003."""
        valid_stream_data = {
            "timestamp": 1791717260,
            "active_app": "ScreenStream4003",
            "window_title": "HUD Live Stream 4003",
            "ocr_snippet": "telemetry text on display",
            "node_id": "L1",
            "fps": 15.0,
            "cpu_pct": 24.5,
            "ram_free_gb": 8.5,
        }

        routing = {
            ":3037": urllib.error.HTTPError(
                "http://127.0.0.1:3037/api/orchestrator/state",
                500,
                "Internal Server Error",
                {},
                None,
            ),
            ":3035": MockHTTPResponse(200, b"<html><body>502 Bad Gateway or malformed JSON {[["),
            ":4003": MockHTTPResponse(200, json.dumps(valid_stream_data).encode("utf-8")),
        }

        opener = CascadeMockOpener(routing)
        client = ScreenLensClient(opener=opener)

        harvest = client.harvest_perception(timeout_s=1.0)

        assert harvest is not None
        assert harvest["source"] == "live_api"
        assert harvest["active_app"] == "ScreenStream4003"
        assert harvest["window_title"] == "HUD Live Stream 4003"
        assert harvest["ocr_snippet"] == "telemetry text on display"
        assert harvest["mesh_health"]["port"] == 4003
        assert harvest["mesh_health"]["status"] == "online"
        assert harvest["mesh_health"]["fps"] == 15.0
        assert harvest["endpoint"].endswith("4003/api/telemetry/live")

        # Verify exact call order: 3037 was tried first, then 3035, then 4003
        assert len(opener.call_history) == 3
        assert ":3037" in opener.call_history[0]
        assert ":3035" in opener.call_history[1]
        assert ":4003" in opener.call_history[2]

    def test_three_port_cascade_all_fail_falls_back_to_sqlite(self, tmp_path: Path):
        """When Ports 3037, 3035, and 4003 all fail, harvests from SQLite database."""
        db_path = tmp_path / "fallback.db"
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE frames (id INTEGER PRIMARY KEY, timestamp TEXT, app_name TEXT, window_title TEXT, ocr_text TEXT);"
        )
        conn.execute(
            "INSERT INTO frames VALUES (1, '2026-10-11T12:00:00Z', 'SqliteApp', 'SqliteWindow', 'sqlite ocr');"
        )
        conn.commit()
        conn.close()

        routing = {
            ":3037": urllib.error.HTTPError("http://127.0.0.1:3037", 500, "Error", {}, None),
            ":3035": urllib.error.HTTPError("http://127.0.0.1:3035", 503, "Unavailable", {}, None),
            ":4003": urllib.error.URLError("Connection refused"),
        }

        opener = CascadeMockOpener(routing)
        client = ScreenLensClient(opener=opener, sqlite_db_paths=[db_path])

        harvest = client.harvest_perception(timeout_s=1.0)

        assert harvest["source"] == "sqlite"
        assert harvest["active_app"] == "SqliteApp"
        assert harvest["window_title"] == "SqliteWindow"
        assert harvest["ocr_snippet"] == "sqlite ocr"
        assert harvest["mesh_health"]["status"] == "sqlite_cached"

    def test_three_port_cascade_first_port_success_bypasses_subsequent_ports(self):
        """When Port 3037 returns 200, ports 3035 and 4003 are never called."""
        orchestrator_data = {
            "timestamp": "2026-10-11T12:00:00Z",
            "screen": {
                "active_app": "Port3037App",
                "window_title": "Port3037Window",
                "recent_ocr": ["orchestrator OCR line 1"],
            },
            "mesh_health": {"status": "all_healthy", "healthy_count": "10/10"},
        }

        routing = {
            ":3037": MockHTTPResponse(200, json.dumps(orchestrator_data).encode("utf-8")),
            ":3035": MockHTTPResponse(200, b"should not be called"),
            ":4003": MockHTTPResponse(200, b"should not be called"),
        }

        opener = CascadeMockOpener(routing)
        client = ScreenLensClient(opener=opener)

        harvest = client.harvest_perception(timeout_s=1.0)

        assert harvest["source"] == "live_api"
        assert harvest["active_app"] == "Port3037App"
        assert len(opener.call_history) == 1
        assert ":3037" in opener.call_history[0]


# ============================================================================
# Vector 2: ScreenLensClient SQLite Corrupted Primary Fallback
# ============================================================================

class TestChallengerM5LensClientSQLiteFallback:
    """Vector 2: Corrupted primary SQLite file falling back to secondary valid database."""

    def test_corrupted_primary_sqlite_db_falls_back_to_secondary_valid_db(self, tmp_path: Path):
        """Primary DB contains non-SQLite corrupted bytes; client recovers and queries secondary DB."""
        # 1. Primary corrupt database (random non-sqlite binary garbage)
        primary_corrupt = tmp_path / "primary_corrupted.db"
        primary_corrupt.write_bytes(b"\xde\xad\xbe\xef" * 256)

        # 2. Secondary valid SQLite database
        secondary_valid = tmp_path / "secondary_valid.db"
        conn = sqlite3.connect(secondary_valid)
        conn.execute(
            "CREATE TABLE frames (id INTEGER PRIMARY KEY, timestamp TEXT, app_name TEXT, window_title TEXT, ocr_text TEXT);"
        )
        conn.execute(
            "INSERT INTO frames VALUES (10, '2026-10-11T15:30:00Z', 'SecondaryApp', 'SecondaryWindow', 'secondary OCR data');"
        )
        conn.commit()
        conn.close()

        # All network ports offline
        all_down_opener = CascadeMockOpener({})
        client = ScreenLensClient(
            opener=all_down_opener,
            sqlite_db_paths=[primary_corrupt, secondary_valid],
        )

        harvest = client.harvest_perception(timeout_s=0.5)

        assert harvest is not None
        assert harvest["source"] == "sqlite"
        assert harvest["active_app"] == "SecondaryApp"
        assert harvest["window_title"] == "SecondaryWindow"
        assert harvest["ocr_snippet"] == "secondary OCR data"
        assert harvest["endpoint"] == str(secondary_valid)
        assert harvest["mesh_health"]["db_path"] == str(secondary_valid)
        assert harvest["mesh_health"]["frame_id"] == 10

    def test_multiple_corrupted_sqlite_dbs_before_valid_db(self, tmp_path: Path):
        """Tests chain: primary corrupted -> secondary zero-byte -> tertiary valid."""
        primary_corrupt = tmp_path / "corrupt1.db"
        primary_corrupt.write_bytes(b"NOT_A_VALID_SQLITE_FILE_AT_ALL_0123456789")

        secondary_zero = tmp_path / "zero.db"
        secondary_zero.write_bytes(b"")

        tertiary_valid = tmp_path / "tertiary_valid.db"
        conn = sqlite3.connect(tertiary_valid)
        conn.execute(
            "CREATE TABLE frames (id INTEGER PRIMARY KEY, timestamp TEXT, app_name TEXT, window_title TEXT, ocr_text TEXT);"
        )
        conn.execute(
            "INSERT INTO frames VALUES (99, '2026-10-11T16:00:00Z', 'TertiaryApp', 'TertiaryWindow', 'tertiary ocr');"
        )
        conn.commit()
        conn.close()

        client = ScreenLensClient(
            opener=CascadeMockOpener({}),
            sqlite_db_paths=[primary_corrupt, secondary_zero, tertiary_valid],
        )

        harvest = client.harvest_perception(timeout_s=0.5)

        assert harvest["source"] == "sqlite"
        assert harvest["active_app"] == "TertiaryApp"
        assert harvest["mesh_health"]["frame_id"] == 99

    def test_all_sqlite_corrupt_falls_back_to_system_kernel(self, tmp_path: Path):
        """When all candidate SQLite databases are corrupted, safely degrades to system_fallback."""
        corrupt1 = tmp_path / "c1.db"
        corrupt1.write_bytes(b"\x00\x01\x02\x03")
        corrupt2 = tmp_path / "c2.db"
        corrupt2.write_bytes(b"\xff\xfe\xfd\xfc")

        client = ScreenLensClient(
            opener=CascadeMockOpener({}),
            sqlite_db_paths=[corrupt1, corrupt2],
        )

        harvest = client.harvest_perception(timeout_s=0.5)

        assert harvest["source"] == "system_fallback"
        assert harvest["endpoint"] == "system_kernel"
        assert harvest["mesh_health"]["status"] == "system_fallback"


# ============================================================================
# Vector 3: ScreenLensClient Dynamic SQLite Table & Column Schema Discovery
# ============================================================================

class TestChallengerM5LensClientDynamicSchemaDiscovery:
    """Vector 3: Dynamic SQLite table and column discovery (non-standard schema)."""

    def test_dynamic_sqlite_discovery_non_standard_table_and_columns(self, tmp_path: Path):
        """Table has non-standard name 'edge_ai_telemetry' and columns ('app', 'window', 'snippet')."""
        db_path = tmp_path / "custom_schema.db"
        conn = sqlite3.connect(db_path)
        # No 'frames' table, non-standard column names
        conn.execute(
            """CREATE TABLE edge_ai_telemetry (
                custom_pk INTEGER PRIMARY KEY,
                epoch_ms INTEGER,
                app TEXT,
                window TEXT,
                snippet TEXT
            );"""
        )
        conn.execute(
            """INSERT INTO edge_ai_telemetry VALUES (
                101,
                1791717260484,
                'Obsidian',
                'Notes - Lauburu Architecture',
                'Rule 3 Host Sanctuary Ram Invariant 4.8 GB'
            );"""
        )
        conn.commit()
        conn.close()

        client = ScreenLensClient(
            opener=CascadeMockOpener({}),
            sqlite_db_paths=[db_path],
        )

        harvest = client.harvest_perception(timeout_s=0.5)

        assert harvest["source"] == "sqlite"
        assert harvest["active_app"] == "Obsidian"
        assert harvest["window_title"] == "Notes - Lauburu Architecture"
        assert harvest["ocr_snippet"] == "Rule 3 Host Sanctuary Ram Invariant 4.8 GB"
        assert harvest["mesh_health"]["table"] == "edge_ai_telemetry"
        # Epoch ms parsed into valid ISO 8601 string
        dt = datetime.datetime.fromisoformat(harvest["timestamp"])
        assert dt.year == 2026

    def test_dynamic_sqlite_discovery_alternative_column_synonyms(self, tmp_path: Path):
        """Tests alternative column synonyms: 'application', 'title', 'content', 'capture_id'."""
        db_path = tmp_path / "sensor_data.db"
        conn = sqlite3.connect(db_path)
        conn.execute(
            """CREATE TABLE raw_sensor_feed (
                capture_id INTEGER PRIMARY KEY,
                created_at TEXT,
                application TEXT,
                title TEXT,
                content TEXT
            );"""
        )
        conn.execute(
            """INSERT INTO raw_sensor_feed VALUES (
                505,
                '2026-10-11T18:45:00Z',
                'GhosttyTerminal',
                'tmux: window 0',
                'cargo test --all-targets'
            );"""
        )
        conn.commit()
        conn.close()

        client = ScreenLensClient(
            opener=CascadeMockOpener({}),
            sqlite_db_paths=[db_path],
        )

        harvest = client.harvest_perception(timeout_s=0.5)

        assert harvest["source"] == "sqlite"
        assert harvest["active_app"] == "GhosttyTerminal"
        assert harvest["window_title"] == "tmux: window 0"
        assert harvest["ocr_snippet"] == "cargo test --all-targets"
        assert harvest["mesh_health"]["frame_id"] == 505

    def test_dynamic_sqlite_discovery_empty_table_falls_back(self, tmp_path: Path):
        """Database has table definition but 0 rows; falls through to next DB or system fallback."""
        db_path = tmp_path / "empty_table.db"
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE frames (id INTEGER PRIMARY KEY, app TEXT);")
        conn.commit()
        conn.close()

        client = ScreenLensClient(
            opener=CascadeMockOpener({}),
            sqlite_db_paths=[db_path],
        )

        harvest = client.harvest_perception(timeout_s=0.5)

        assert harvest["source"] == "system_fallback"


# ============================================================================
# Vector 4: ScreenLensClient Gemini Spark SSE Non-JSON Stream Handling
# ============================================================================

class TestChallengerM5LensClientGeminiSparkSSE:
    """Vector 4: Gemini Spark non-JSON SSE stream handling (Port 9999 text/event-stream)."""

    def test_gemini_spark_non_json_sse_stream_handling(self):
        """Port 9999 returning text/event-stream payload populates response_preview without JSON error."""
        sse_payload = (
            b": keepalive\n\n"
            b"event: endpoint\n"
            b"data: /messages?session_id=session_uuid_9999\n\n"
            b"event: status\n"
            b"data: {\"status\": \"active\", \"mcp_version\": \"2026.2\"}\n\n"
        )

        routing = {
            ":9999": MockHTTPResponse(200, sse_payload),
        }

        opener = CascadeMockOpener(routing)
        client = ScreenLensClient(opener=opener)

        spark_status = client.connect_gemini_spark(timeout_s=1.0)

        assert spark_status["connected"] is True
        assert spark_status["status"] == "online"
        assert spark_status["error"] is None
        assert "response_preview" in spark_status["details"]
        assert "keepalive" in spark_status["details"]["response_preview"]
        assert spark_status["latency_ms"] is not None

    def test_gemini_spark_multi_url_failover_404_to_200_sse(self):
        """Candidate 1 returns HTTP 404, candidate 2 returns HTTP 200 SSE stream -> connects via candidate 2."""
        routing = {
            "/mcp/project/health": urllib.error.HTTPError(
                "http://127.0.0.1:9999/mcp/project/health", 404, "Not Found", {}, None
            ),
            "/health": urllib.error.HTTPError(
                "http://127.0.0.1:9999/health", 404, "Not Found", {}, None
            ),
            "/sse": MockHTTPResponse(200, b"event: ping\ndata: pong\n\n"),
        }

        opener = CascadeMockOpener(routing)
        client = ScreenLensClient(opener=opener)

        spark_status = client.connect_gemini_spark(timeout_s=1.0)

        assert spark_status["connected"] is True
        assert spark_status["status"] == "online"
        assert spark_status["endpoint"].endswith("/sse")
        assert "response_preview" in spark_status["details"]

    def test_gemini_spark_all_endpoints_down(self):
        """When all candidate URLs fail, returns connected=False and status=offline cleanly."""
        routing = {
            ":9999": urllib.error.URLError("Connection refused"),
        }

        opener = CascadeMockOpener(routing)
        client = ScreenLensClient(opener=opener)

        spark_status = client.connect_gemini_spark(timeout_s=0.5)

        assert spark_status["connected"] is False
        assert spark_status["status"] == "offline"
        assert spark_status["latency_ms"] is None
        assert spark_status["error"] is not None


# ============================================================================
# Vector 5: ScreenLensClient Extreme Timestamp Normalization
# ============================================================================

class TestChallengerM5LensClientTimestampNormalization:
    """Vector 5: Extreme timestamp normalization across nanoseconds, strings, and edge values."""

    REF_NS = 1791717260484000000
    REF_US = 1791717260484000
    REF_MS = 1791717260484
    REF_S = 1791717260

    def test_extreme_timestamp_normalization_nanoseconds_all_types(self):
        """Nanoseconds (1e18) as int, float, str, and scientific notation."""
        for val in [
            self.REF_NS,
            float(self.REF_NS),
            str(self.REF_NS),
            f"  {self.REF_NS}  ",
            "1.791717260484e18",
            1.791717260484e18,
        ]:
            res = normalize_iso_timestamp(val)
            assert res.startswith("2026-10-11T11:14:20"), f"Failed on input {val!r}: got {res}"
            dt = datetime.datetime.fromisoformat(res)
            assert dt.year == 2026
            assert dt.month == 10

    def test_extreme_timestamp_normalization_microseconds_milliseconds_seconds(self):
        """Microseconds (1e15), milliseconds (1e12), and seconds (1e9) normalize accurately."""
        # Microseconds
        res_us = normalize_iso_timestamp(self.REF_US)
        assert res_us.startswith("2026-10-11T11:14:20")

        # Milliseconds
        res_ms = normalize_iso_timestamp(self.REF_MS)
        assert res_ms.startswith("2026-10-11T11:14:20")

        # Seconds
        res_s = normalize_iso_timestamp(self.REF_S)
        assert res_s.startswith("2026-10-11T11:14:20")

        # Seconds float
        res_sf = normalize_iso_timestamp(1791717260.5)
        assert res_sf.startswith("2026-10-11T11:14:20")

    def test_extreme_timestamp_normalization_none_and_empty(self):
        """None, empty string, and whitespace return current UTC timestamp."""
        now = datetime.datetime.now(datetime.timezone.utc)
        for val in [None, "", "   ", "\t\n"]:
            res = normalize_iso_timestamp(val)
            assert isinstance(res, str)
            dt = datetime.datetime.fromisoformat(res)
            assert abs((dt - now).total_seconds()) < 5

    def test_extreme_timestamp_normalization_non_finite_floats(self):
        """Non-finite floats (inf, -inf, nan) return current UTC timestamp without crashing."""
        for val in [float("inf"), float("-inf"), float("nan")]:
            res = normalize_iso_timestamp(val)
            assert isinstance(res, str)
            dt = datetime.datetime.fromisoformat(res)
            assert dt.year >= 2026

    def test_extreme_timestamp_normalization_non_primitive_types(self):
        """Lists, dicts, tuples, and bytes default safely to current UTC timestamp."""
        for val in [[], {}, (1, 2), b"bytes_not_str"]:
            res = normalize_iso_timestamp(val)
            assert isinstance(res, str)
            dt = datetime.datetime.fromisoformat(res)
            assert dt.year >= 2026

    def test_adversarial_timestamp_string_bypass_behavior(self):
        """Empirically asserts behavior of strings containing 'T' or '-':

        Observation: lens_client.py lines 108-109 contain:
        `if 'T' in val or '-' in val: return val`
        Strings containing 'T' or '-' are returned verbatim.
        Strings without 'T' or '-' (e.g. 'INVALID_EPOCH') fall back to current UTC.
        """
        # String without 'T' or '-' falls back to current UTC
        res_no_t = normalize_iso_timestamp("INVALID_NUMERIC")
        dt_fallback = datetime.datetime.fromisoformat(res_no_t)
        assert dt_fallback.year >= 2026

        # String with valid ISO format is preserved
        res_valid = normalize_iso_timestamp("2026-10-11T19:39:11Z")
        assert res_valid == "2026-10-11T19:39:11Z"

        # Adversarial observation: string containing 'T' returns verbatim
        res_adversarial = normalize_iso_timestamp("NOT_A_DATE")
        assert res_adversarial == "NOT_A_DATE"


# ============================================================================
# Vector 6: NotebookSynchronizer Malformed recentProjects.xml Regex Recovery
# ============================================================================

class TestChallengerM5NotebookSyncRecentProjectsXMLRegex:
    """Vector 6: Malformed/truncated recentProjects.xml regex recovery."""

    def test_malformed_truncated_recent_projects_xml_regex_recovery(self, isolated_env):
        """Truncated XML with unclosed tags parsed successfully via regex; recovers workspaceId and build."""
        recent_xml = isolated_env["recent_xml"]
        # Abruptly truncated XML missing closing </entry>, </component>, </application>
        recent_xml.write_text(
            """<application>
  <component name="RecentProjectsManager">
    <entry key="/Volumes/Lauburu-Monorepo">
      <value>
        <RecentProjectMetaInfo opened="true" projectWorkspaceId="3KVuyxqTNZxKVuAAf4tq3bxSOYz">
          <option name="build" value="PY-262.10968.92" />
          <option name="productionCode" value="true" />
    <!-- TRUNCATED END OF FILE ABRUPT CRASH
""",
            encoding="utf-8",
        )

        sync = NotebookSynchronizer(
            repo_root=isolated_env["root"],
            options_dir=isolated_env["options_dir"],
            notebook_path=isolated_env["nb_path"],
            metadata_path=isolated_env["meta_path"],
        )
        sync.pycharm_port = 63399  # Ensure offline port to isolate file probe

        res = sync.detect_pycharm_workspace(options_dir=isolated_env["options_dir"])

        assert res["workspace_id"] == "3KVuyxqTNZxKVuAAf4tq3bxSOYz"
        assert res["version"] == "PY-262.10968.92"
        assert res["source"] == "options_xml"

    def test_truncated_xml_inverted_attributes_build_regex(self, isolated_env):
        """Inverted attribute ordering: <option value="PY-262.99" name="build" /> in truncated file."""
        recent_xml = isolated_env["recent_xml"]
        recent_xml.write_text(
            """<entry key="/Volumes/Lauburu-Monorepo">
  <RecentProjectMetaInfo opened="true" projectWorkspaceId="WS_INVERTED_ATTRS">
    <option value="PY-262.99" name="build" />
<!-- unclosed
""",
            encoding="utf-8",
        )

        sync = NotebookSynchronizer(
            repo_root=isolated_env["root"],
            options_dir=isolated_env["options_dir"],
            notebook_path=isolated_env["nb_path"],
            metadata_path=isolated_env["meta_path"],
        )
        sync.pycharm_port = 63399

        res = sync.detect_pycharm_workspace(options_dir=isolated_env["options_dir"])

        assert res["workspace_id"] == "WS_INVERTED_ATTRS"
        assert res["version"] == "PY-262.99"

    def test_truncated_xml_last_opened_fallback(self, isolated_env):
        """No opened='true', but lastOpenedProject option present in truncated file."""
        recent_xml = isolated_env["recent_xml"]
        recent_xml.write_text(
            """<application>
  <option name="lastOpenedProject" value="/Volumes/Lauburu-Monorepo" />
  <entry key="/Volumes/Lauburu-Monorepo">
    <RecentProjectMetaInfo projectWorkspaceId="WS_LAST_OPENED_123">
      <option name="build" value="PY-262.777" />
""",
            encoding="utf-8",
        )

        sync = NotebookSynchronizer(
            repo_root=isolated_env["root"],
            options_dir=isolated_env["options_dir"],
            notebook_path=isolated_env["nb_path"],
            metadata_path=isolated_env["meta_path"],
        )
        sync.pycharm_port = 63399

        res = sync.detect_pycharm_workspace(options_dir=isolated_env["options_dir"])

        assert res["workspace_id"] == "WS_LAST_OPENED_123"
        assert res["version"] == "PY-262.777"

    def test_severely_fragmented_xml_broad_regex_recovery(self, isolated_env):
        """Severely fragmented XML without proper <entry> tags matches Step 3 broad regex fallback."""
        recent_xml = isolated_env["recent_xml"]
        recent_xml.write_text(
            """entry key="/Volumes/Lauburu-Monorepo"
projectWorkspaceId="WS_BROAD_FRAGMENTED"
<option name="build" value="PY-262.BROAD" />
""",
            encoding="utf-8",
        )

        sync = NotebookSynchronizer(
            repo_root=isolated_env["root"],
            options_dir=isolated_env["options_dir"],
            notebook_path=isolated_env["nb_path"],
            metadata_path=isolated_env["meta_path"],
        )
        sync.pycharm_port = 63399

        res = sync.detect_pycharm_workspace(options_dir=isolated_env["options_dir"])

        assert res["workspace_id"] == "WS_BROAD_FRAGMENTED"
        assert res["version"] == "PY-262.BROAD"


# ============================================================================
# Vector 7: NotebookSynchronizer Corrupted Existing .ipynb Recovery
# ============================================================================

class TestChallengerM5NotebookSyncCorruptedNotebookRecovery:
    """Vector 7: Corrupted existing .ipynb file fallback recovery."""

    def test_corrupted_existing_ipynb_file_fallback_recovery(self, isolated_env):
        """Target .ipynb contains invalid JSON; recovers canonical v4.5 notebook and injects sync cell."""
        nb_path = isolated_env["nb_path"]
        # Write corrupted JSON to target notebook
        nb_path.write_text('{"cells": [ { INVALID_JSON_SYNTAX :::: corrupt', encoding="utf-8")

        sync = NotebookSynchronizer(
            repo_root=isolated_env["root"],
            notebook_path=nb_path,
            metadata_path=isolated_env["meta_path"],
        )

        res = sync.sync_notebook(
            payload={"window_title": "Recovered Window", "timestamp_utc": "2026-10-11T20:00:00Z"},
            dry_run=False,
        )

        assert res["status"] == "success"
        assert res["notebook_modified"] is True
        assert res["cell_action"] == "inserted"

        # Verify disk file is now 100% valid JSON
        disk_data = json.loads(nb_path.read_text(encoding="utf-8"))
        assert disk_data["nbformat"] == 4
        assert disk_data["nbformat_minor"] == 5
        assert len(disk_data["cells"]) == 3

        # Header cell
        assert disk_data["cells"][0]["cell_type"] == "markdown"
        # Sync cell inserted at index 1
        sync_cell = disk_data["cells"][1]
        assert sync_cell["cell_type"] == "code"
        assert SYNC_TAG in sync_cell["metadata"]["tags"]
        assert "LENS_CONTEXT =" in "".join(sync_cell["source"])
        assert "Recovered Window" in "".join(sync_cell["source"])

    def test_corrupted_binary_garbage_ipynb_recovery(self, isolated_env):
        """Target .ipynb contains binary random bytes; recovers valid JSON cleanly."""
        nb_path = isolated_env["nb_path"]
        nb_path.write_bytes(os.urandom(512))

        sync = NotebookSynchronizer(
            repo_root=isolated_env["root"],
            notebook_path=nb_path,
            metadata_path=isolated_env["meta_path"],
        )

        res = sync.sync_notebook(payload={"active_app": "PyCharmTest"})
        assert res["status"] == "success"

        disk_data = json.loads(nb_path.read_text(encoding="utf-8"))
        assert len(disk_data["cells"]) == 3
        assert SYNC_TAG in disk_data["cells"][1]["metadata"]["tags"]

    def test_zero_byte_existing_ipynb_recovery(self, isolated_env):
        """Target .ipynb exists but has size 0; recovers canonical notebook."""
        nb_path = isolated_env["nb_path"]
        nb_path.touch()

        sync = NotebookSynchronizer(
            repo_root=isolated_env["root"],
            notebook_path=nb_path,
            metadata_path=isolated_env["meta_path"],
        )

        res = sync.sync_notebook(payload={"active_app": "PyCharmTest"})
        assert res["status"] == "success"

        disk_data = json.loads(nb_path.read_text(encoding="utf-8"))
        assert len(disk_data["cells"]) == 3


# ============================================================================
# Vector 8: NotebookSynchronizer Sync Cell Deduplication
# ============================================================================

class TestChallengerM5NotebookSyncCellDeduplication:
    """Vector 8: Sync cell deduplication (notebook with multiple existing sync cells)."""

    def test_sync_cell_deduplication_updates_only_first_matching_cell(self, isolated_env):
        """Notebook with 3 pre-existing sync cells has only the first updated; total cell count invariant."""
        nb_path = isolated_env["nb_path"]

        # Initial notebook with 6 cells containing 3 distinct sync cells:
        # Cell 0: Header markdown
        # Cell 1: Sync cell 1 (tagged)
        # Cell 2: User code
        # Cell 3: Sync cell 2 (tagged)
        # Cell 4: User markdown
        # Cell 5: Sync cell 3 (header prefix)
        initial_nb = {
            "cells": [
                {"cell_type": "markdown", "id": "header_0", "metadata": {}, "source": ["# Title\n"]},
                {
                    "cell_type": "code",
                    "id": "sync_cell_1",
                    "metadata": {"tags": [SYNC_TAG]},
                    "source": [f"{SYNC_HEADER_PREFIX}\n", "LENS_CONTEXT = {'timestamp': 'OLD_1'}\n"],
                },
                {"cell_type": "code", "id": "user_code_2", "metadata": {}, "source": ["x = 10\n"]},
                {
                    "cell_type": "code",
                    "id": "sync_cell_3",
                    "metadata": {"tags": [SYNC_TAG]},
                    "source": [f"{SYNC_HEADER_PREFIX}\n", "LENS_CONTEXT = {'timestamp': 'OLD_2'}\n"],
                },
                {"cell_type": "markdown", "id": "user_md_4", "metadata": {}, "source": ["## User Notes\n"]},
                {
                    "cell_type": "code",
                    "id": "sync_cell_5",
                    "metadata": {},
                    "source": [f"{SYNC_HEADER_PREFIX}\n", "LENS_CONTEXT = {'timestamp': 'OLD_3'}\n"],
                },
            ],
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 5,
        }
        nb_path.write_text(json.dumps(initial_nb), encoding="utf-8")

        sync = NotebookSynchronizer(
            repo_root=isolated_env["root"],
            notebook_path=nb_path,
            metadata_path=isolated_env["meta_path"],
        )

        res = sync.sync_notebook(
            payload={"timestamp_utc": "2026-10-11T22:00:00Z", "window_title": "Deduplicated Window"},
            dry_run=False,
        )

        assert res["status"] == "success"
        assert res["cell_action"] == "updated"
        assert res["sync_cell_index"] == 1
        assert res["cell_count"] == 6

        disk_data = json.loads(nb_path.read_text(encoding="utf-8"))
        cells = disk_data["cells"]
        assert len(cells) == 6  # Zero extra cells inserted

        # Cell 1 was updated with new timestamp and window title
        cell1_source = "".join(cells[1]["source"])
        assert "2026-10-11T22:00:00Z" in cell1_source
        assert "Deduplicated Window" in cell1_source

        # Cells 3 and 5 retain their original content (only the first sync cell is modified)
        cell3_source = "".join(cells[3]["source"])
        assert "'timestamp': 'OLD_2'" in cell3_source
        cell5_source = "".join(cells[5]["source"])
        assert "'timestamp': 'OLD_3'" in cell5_source

    def test_repeated_sync_cell_count_invariant(self, isolated_env):
        """Repeated sequential sync calls preserve cell count identically across 10 iterations."""
        nb_path = isolated_env["nb_path"]
        sync = NotebookSynchronizer(
            repo_root=isolated_env["root"],
            notebook_path=nb_path,
            metadata_path=isolated_env["meta_path"],
        )

        # Initial sync creates 3 cells
        res_init = sync.sync_notebook(payload={"iteration": 0})
        assert res_init["cell_count"] == 3

        for i in range(1, 11):
            res = sync.sync_notebook(payload={"iteration": i, "timestamp_utc": f"2026-10-11T22:{i:02d}:00Z"})
            assert res["cell_action"] == "updated"
            assert res["sync_cell_index"] == 1
            assert res["cell_count"] == 3

        disk_data = json.loads(nb_path.read_text(encoding="utf-8"))
        assert len(disk_data["cells"]) == 3


# ============================================================================
# Vector 9: NotebookSynchronizer 5-Rule Colab GPU Offload Combinatorial Matrix
# ============================================================================

class TestChallengerM5NotebookSyncColabOffloadMatrix:
    """Vector 9: 5-rule Colab GPU offload combinatorial decision matrix."""

    @pytest.fixture
    def synchronizer(self, isolated_env):
        return NotebookSynchronizer(
            repo_root=isolated_env["root"],
            notebook_path=isolated_env["nb_path"],
            metadata_path=isolated_env["meta_path"],
        )

    def test_colab_gpu_offload_baseline_healthy(self, synchronizer, monkeypatch):
        """Baseline healthy: Free RAM 12.0 GB, sanctuary preserved, pressure 1, task 1.0 GB -> READY."""
        monkeypatch.setattr(
            synchronizer,
            "get_host_memory_status",
            lambda: {
                "total_ram_gb": 24.0,
                "free_ram_gb": 12.0,
                "free_gb": 12.0,
                "sanctuary_preserved": True,
                "memory_pressure_level": 1,
            },
        )

        res = synchronizer.check_colab_gpu_offload(estimated_task_ram_gb=1.0, force_offload=False)

        assert res["colab_offload_recommended"] is False
        assert res["should_offload_to_colab"] is False
        assert res["colab_offload_status"] == "READY"
        assert res["target_runtime"] == "Local Metal GPU"
        assert "within safe sanctuary headroom" in res["reason"]

    def test_colab_gpu_offload_rule1_forced_offload(self, synchronizer, monkeypatch):
        """Rule 1: force_offload=True alone triggers RECOMMENDED status."""
        monkeypatch.setattr(
            synchronizer,
            "get_host_memory_status",
            lambda: {
                "total_ram_gb": 24.0,
                "free_ram_gb": 15.0,
                "free_gb": 15.0,
                "sanctuary_preserved": True,
                "memory_pressure_level": 1,
            },
        )

        res = synchronizer.check_colab_gpu_offload(estimated_task_ram_gb=0.0, force_offload=True)

        assert res["colab_offload_recommended"] is True
        assert res["colab_offload_status"] == "RECOMMENDED"
        assert res["target_runtime"] == "Google Colab Tesla T4"
        assert "Forced offload requested" in res["reason"]

    def test_colab_gpu_offload_rule2_low_ram_sanctuary_breach(self, synchronizer, monkeypatch):
        """Rule 2: free_ram_gb (3.5 GB) below 4.8 GB sanctuary floor triggers RECOMMENDED."""
        monkeypatch.setattr(
            synchronizer,
            "get_host_memory_status",
            lambda: {
                "total_ram_gb": 24.0,
                "free_ram_gb": 3.5,
                "free_gb": 3.5,
                "sanctuary_preserved": True,
                "memory_pressure_level": 1,
            },
        )

        res = synchronizer.check_colab_gpu_offload(estimated_task_ram_gb=0.0, force_offload=False)

        assert res["colab_offload_recommended"] is True
        assert res["colab_offload_status"] == "RECOMMENDED"
        assert "below 4.8 GB sanctuary floor" in res["reason"]

    def test_colab_gpu_offload_rule3_sanctuary_condition_violated(self, synchronizer, monkeypatch):
        """Rule 3: sanctuary_preserved=False alone triggers RECOMMENDED."""
        monkeypatch.setattr(
            synchronizer,
            "get_host_memory_status",
            lambda: {
                "total_ram_gb": 24.0,
                "free_ram_gb": 10.0,
                "free_gb": 10.0,
                "sanctuary_preserved": False,
                "memory_pressure_level": 1,
            },
        )

        res = synchronizer.check_colab_gpu_offload(estimated_task_ram_gb=0.0, force_offload=False)

        assert res["colab_offload_recommended"] is True
        assert "Host sanctuary condition violated" in res["reason"]

    def test_colab_gpu_offload_rule4_task_headroom_breach(self, synchronizer, monkeypatch):
        """Rule 4: (free_gb - estimated_task_ram_gb) < 4.8 GB triggers RECOMMENDED."""
        # 5.5 GB free >= 4.8, but task requires 2.0 GB -> headroom 3.5 GB < 4.8 GB
        monkeypatch.setattr(
            synchronizer,
            "get_host_memory_status",
            lambda: {
                "total_ram_gb": 24.0,
                "free_ram_gb": 5.5,
                "free_gb": 5.5,
                "sanctuary_preserved": True,
                "memory_pressure_level": 1,
            },
        )

        res = synchronizer.check_colab_gpu_offload(estimated_task_ram_gb=2.0, force_offload=False)

        assert res["colab_offload_recommended"] is True
        assert "Headroom after estimated task" in res["reason"]

    def test_colab_gpu_offload_rule5_mach_vm_pressure_elevated(self, synchronizer, monkeypatch):
        """Rule 5: memory_pressure_level >= 2 (Warning or Critical) triggers RECOMMENDED."""
        for level in [2, 3]:
            monkeypatch.setattr(
                synchronizer,
                "get_host_memory_status",
                lambda lvl=level: {
                    "total_ram_gb": 24.0,
                    "free_ram_gb": 8.0,
                    "free_gb": 8.0,
                    "sanctuary_preserved": True,
                    "memory_pressure_level": lvl,
                },
            )

            res = synchronizer.check_colab_gpu_offload(estimated_task_ram_gb=0.0, force_offload=False)

            assert res["colab_offload_recommended"] is True
            assert f"pressure level ({level}) is elevated" in res["reason"]

    def test_colab_gpu_offload_combinatorial_multiple_triggers(self, synchronizer, monkeypatch):
        """Combinatorial triggers: Rule 2 + Rule 3 + Rule 5 simultaneously."""
        monkeypatch.setattr(
            synchronizer,
            "get_host_memory_status",
            lambda: {
                "total_ram_gb": 24.0,
                "free_ram_gb": 2.5,
                "free_gb": 2.5,
                "sanctuary_preserved": False,
                "memory_pressure_level": 3,
            },
        )

        res = synchronizer.check_colab_gpu_offload(estimated_task_ram_gb=0.0, force_offload=False)

        assert res["colab_offload_recommended"] is True
        assert "below 4.8 GB sanctuary floor" in res["reason"]
        assert "Host sanctuary condition violated" in res["reason"]
        assert "pressure level (3) is elevated" in res["reason"]

    def test_colab_gpu_offload_combinatorial_all_five_triggers(self, synchronizer, monkeypatch):
        """Combinatorial test: all 5 rules triggered simultaneously."""
        monkeypatch.setattr(
            synchronizer,
            "get_host_memory_status",
            lambda: {
                "total_ram_gb": 24.0,
                "free_ram_gb": 2.0,
                "free_gb": 2.0,
                "sanctuary_preserved": False,
                "memory_pressure_level": 3,
            },
        )

        res = synchronizer.check_colab_gpu_offload(estimated_task_ram_gb=1.0, force_offload=True)

        assert res["colab_offload_recommended"] is True
        assert res["colab_offload_status"] == "RECOMMENDED"
        assert "Forced offload requested" in res["reason"]
        assert "below 4.8 GB sanctuary floor" in res["reason"]
        assert "Host sanctuary condition violated" in res["reason"]
        assert "Headroom after estimated task" in res["reason"]
        assert "pressure level (3) is elevated" in res["reason"]


# ============================================================================
# Vector 10: NotebookSynchronizer 20-Thread Concurrent File Write Race Safety
# ============================================================================

class TestChallengerM5NotebookSyncConcurrentWriteSafety:
    """Vector 10: 20-thread concurrent notebook write race safety."""

    def test_20_thread_concurrent_notebook_write_race_safety(self, isolated_env):
        """20 threads simultaneously invoking sync_notebook_and_ide yield 100% valid JSON."""
        nb_path = isolated_env["nb_path"]
        meta_path = isolated_env["meta_path"]

        sync = NotebookSynchronizer(
            repo_root=isolated_env["root"],
            notebook_path=nb_path,
            metadata_path=meta_path,
        )

        # Pre-seed initial notebook
        sync.sync_notebook({"initial": True})

        def worker(thread_idx: int) -> Dict[str, Any]:
            payload = {
                "thread_id": thread_idx,
                "active_app": f"App_Thread_{thread_idx}",
                "window_title": f"Window_Thread_{thread_idx}",
                "ocr_snippet": f"OCR snippet from thread {thread_idx}",
                "timestamp_utc": f"2026-10-11T23:00:{thread_idx:02d}Z",
            }
            return sync.sync_notebook_and_ide(payload, dry_run=False)

        # Launch 20 concurrent threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            results = [f.result() for f in futures]

        # 1. Assert all 20 threads succeeded
        assert len(results) == 20
        for r in results:
            assert r["status"] == "success"
            assert r["notebook_modified"] is True
            assert r["metadata_modified"] is True

        # 2. Assert target notebook is 100% valid JSON
        nb_raw = nb_path.read_text(encoding="utf-8")
        nb_json = json.loads(nb_raw)
        assert nb_json["nbformat"] == 4
        assert len(nb_json["cells"]) == 3
        sync_cell = nb_json["cells"][1]
        assert SYNC_TAG in sync_cell["metadata"]["tags"]
        assert "LENS_CONTEXT =" in "".join(sync_cell["source"])

        # 3. Assert target .idea/lens_context.json is 100% valid JSON
        meta_raw = meta_path.read_text(encoding="utf-8")
        meta_json = json.loads(meta_raw)
        assert meta_json["status"] == "IN_SYNC"
        assert "dual_accounts" in meta_json
        assert len(meta_json["dual_accounts"]) == 2

        # 4. Assert zero orphaned .tmp files remain in directories
        parent_dir = nb_path.parent
        leftover_nb_tmps = list(parent_dir.glob(f".{nb_path.name}.*.tmp"))
        leftover_meta_tmps = list(meta_path.parent.glob(f".{meta_path.name}.*.tmp"))
        assert len(leftover_nb_tmps) == 0, f"Orphaned notebook tmp files: {leftover_nb_tmps}"
        assert len(leftover_meta_tmps) == 0, f"Orphaned metadata tmp files: {leftover_meta_tmps}"

    def test_concurrent_writes_with_simultaneous_reads_consistency(self, isolated_env):
        """Simultaneous concurrent writers and readers observe consistent valid JSON states."""
        nb_path = isolated_env["nb_path"]
        meta_path = isolated_env["meta_path"]

        sync = NotebookSynchronizer(
            repo_root=isolated_env["root"],
            notebook_path=nb_path,
            metadata_path=meta_path,
        )
        sync.sync_notebook({"initial": True})

        read_errors: List[str] = []

        def writer_task(idx: int) -> None:
            sync.sync_notebook_and_ide(
                {"writer_id": idx, "timestamp_utc": f"2026-10-11T23:10:{idx:02d}Z"}
            )

        def reader_task() -> None:
            try:
                data = json.loads(nb_path.read_text(encoding="utf-8"))
                assert "cells" in data
            except Exception as exc:
                read_errors.append(str(exc))

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            write_futures = [executor.submit(writer_task, i) for i in range(10)]
            read_futures = [executor.submit(reader_task) for _ in range(10)]
            concurrent.futures.wait(write_futures + read_futures)

        assert not read_errors, f"Readers observed invalid JSON state: {read_errors}"
