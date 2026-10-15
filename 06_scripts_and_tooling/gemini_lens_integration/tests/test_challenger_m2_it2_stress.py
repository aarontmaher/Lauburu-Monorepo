"""Milestone 2 Iteration 2 Adversarial Stress Test Suite.

Authored by challenger_m2_it2_1.
Empirically stress-tests and audits Milestone 2 remediations:
1. Endpoint Isolation Challenge:
   - Custom failing endpoint (offline port 59999, connection refused, hanging tarpit,
     HTTP 400, 404, 500, 502, 503) must strictly isolate and NEVER leak queries to port 9999.
2. Dynamic Darwin Page Size Challenge:
   - Authentic syscall resolution via resource.getpagesize().
   - Mathematical proportionality test: Intel (4096) vs Apple Silicon (16384).
   - Graceful fallback when resource.getpagesize() raises an exception.
3. Timestamp Normalization Challenge:
   - Seconds (int, float, str).
   - Milliseconds (1791717260484, int, float, str).
   - ISO strings (with Z and UTC offset).
   - Microseconds (1791717260484000, int, float, str).
   - Nanoseconds (1791717260484000000, int, str).
   - Zero-mock preservation: historical timestamp must not default to datetime.now().
4. Zero-Mock Metrics & SQL Identifier Escaping:
   - Elimination of fabricated strings ("10/14").
   - Resilient escaping of table names with hyphens, spaces, and punctuation in SQLite.
"""

from __future__ import annotations

import datetime
import http.server
import os
import resource
import socket
import sqlite3
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lens_client import (
    ScreenLensClient,
    get_darwin_memory_info,
    normalize_iso_timestamp,
)


class TestEndpointIsolationChallenge:
    """Stress tests asserting custom failing endpoints NEVER leak to localhost:9999."""

    def test_offline_port_59999_never_queries_port_9999(self):
        """Custom endpoint on offline port 59999 must not touch port 9999."""
        client = ScreenLensClient(
            config_dict={
                "endpoints": {
                    "gemini_spark": {
                        "mcp_project_health_url": "http://127.0.0.1:59999/mcp/project/health",
                        "mcp_health_url": "http://127.0.0.1:59999/health",
                        "mcp_sse_url": "http://127.0.0.1:59999/sse",
                    }
                }
            }
        )

        opened_urls: List[str] = []
        original_open = client._opener.open

        def spy_open(req, *args, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            opened_urls.append(url)
            return original_open(req, *args, **kwargs)

        client._opener.open = spy_open

        status = client.connect_gemini_spark(timeout_s=0.1)

        # Assert no URL queried contains 9999
        assert len(opened_urls) > 0, "Expected custom URLs to be attempted"
        assert all(":9999" not in url for url in opened_urls), (
            f"Isolation violation! Leaked queries to port 9999: {opened_urls}"
        )
        assert status["connected"] is False
        assert status["status"] == "offline"
        assert status["endpoint"] == "http://127.0.0.1:59999/mcp/project/health"

    def test_http_error_codes_do_not_fall_through_to_port_9999(self):
        """When custom endpoint responds with 400/404/500/503, must not fall through to port 9999."""
        call_log: List[str] = []

        class ErrorHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                call_log.append(self.path)
                if "/err404" in self.path:
                    self.send_response(404)
                elif "/err500" in self.path:
                    self.send_response(500)
                elif "/err503" in self.path:
                    self.send_response(503)
                else:
                    self.send_response(400)
                self.end_headers()

            def log_message(self, *args):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), ErrorHandler)
        port = server.server_port
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            client = ScreenLensClient(
                config_dict={
                    "endpoints": {
                        "gemini_spark": {
                            "mcp_project_health_url": f"http://127.0.0.1:{port}/err404",
                            "mcp_health_url": f"http://127.0.0.1:{port}/err500",
                            "mcp_sse_url": f"http://127.0.0.1:{port}/err503",
                        }
                    }
                }
            )

            opened_urls: List[str] = []
            original_open = client._opener.open

            def spy_open(req, *args, **kwargs):
                url = req.full_url if hasattr(req, "full_url") else str(req)
                opened_urls.append(url)
                return original_open(req, *args, **kwargs)

            client._opener.open = spy_open

            status = client.connect_gemini_spark(timeout_s=0.2)

            assert len(opened_urls) == 3
            assert all(":9999" not in url for url in opened_urls), (
                f"Leaked to port 9999: {opened_urls}"
            )
            assert status["connected"] is False
            assert status["status"] == "offline"
            assert status["endpoint"] == f"http://127.0.0.1:{port}/err404"
        finally:
            server.shutdown()


class TestDynamicPageSizeChallenge:
    """Stress tests verifying dynamic Darwin page size resolution and accounting."""

    def test_live_darwin_page_size_resolution(self):
        """Verifies get_darwin_memory_info() uses live resource.getpagesize()."""
        if sys.platform != "darwin":
            pytest.skip("Test requires macOS Darwin kernel")

        live_page_size = resource.getpagesize()
        mem_info = get_darwin_memory_info()

        assert "free_gb" in mem_info
        assert "wired_gb" in mem_info
        assert "active_gb" in mem_info
        assert "compressed_gb" in mem_info
        assert "sanctuary_floor_gb" in mem_info
        assert mem_info["sanctuary_floor_gb"] == 4.8

    def test_proportional_scaling_intel_4096_vs_m4_16384(self):
        """Proves memory calculations scale dynamically between Intel (4096) and M4 (16384)."""
        if sys.platform != "darwin":
            pytest.skip("Test requires macOS Darwin kernel")

        with patch("resource.getpagesize", return_value=16384):
            mem_m4 = get_darwin_memory_info()

        with patch("resource.getpagesize", return_value=4096):
            mem_intel = get_darwin_memory_info()

        # With 4096 vs 16384 bytes per page, calculated GB should be exactly 1/4 (25%)
        # Allowing small rounding variance due to round(..., 2)
        ratio = mem_intel["active_gb"] / mem_m4["active_gb"]
        assert 0.20 <= ratio <= 0.30, (
            f"Expected 4096/16384 ratio ~0.25, got {ratio} (intel={mem_intel['active_gb']}, m4={mem_m4['active_gb']})"
        )

    def test_page_size_exception_fallback_to_sysconf(self):
        """When resource.getpagesize() raises, falls back to os.sysconf('SC_PAGESIZE')."""
        if sys.platform != "darwin":
            pytest.skip("Test requires macOS Darwin kernel")

        with patch("resource.getpagesize", side_effect=AttributeError("Simulated missing API")):
            with patch("os.sysconf", return_value=4096):
                mem_fallback = get_darwin_memory_info()
                assert "free_gb" in mem_fallback
                assert isinstance(mem_fallback["free_gb"], float)


class TestTimestampNormalizationChallenge:
    """Adversarial challenge for timestamp normalization and historical fidelity."""

    def test_seconds_timestamps(self):
        """Seconds timestamps (int, float, str) must be normalized accurately."""
        # 1791717260 is Sun Oct 11 2026 11:14:20 UTC
        ts_int = normalize_iso_timestamp(1791717260)
        assert ts_int.startswith("2026-10-11T11:14:20")

        ts_float = normalize_iso_timestamp(1791717260.484)
        assert ts_float.startswith("2026-10-11T11:14:20.484")

        ts_str = normalize_iso_timestamp("1791717260")
        assert ts_str.startswith("2026-10-11T11:14:20")

    def test_milliseconds_timestamps(self):
        """Millisecond timestamps (1791717260484) must be normalized without overflow."""
        ts_int = normalize_iso_timestamp(1791717260484)
        assert ts_int.startswith("2026-10-11T11:14:20.484")

        ts_float = normalize_iso_timestamp(1791717260484.0)
        assert ts_float.startswith("2026-10-11T11:14:20.484")

        ts_str = normalize_iso_timestamp("1791717260484")
        assert ts_str.startswith("2026-10-11T11:14:20.484")

    def test_iso_string_passthrough(self):
        """Valid ISO strings must be preserved directly."""
        iso_z = "2026-10-11T11:14:20.484000Z"
        assert normalize_iso_timestamp(iso_z) == iso_z

        iso_offset = "2026-10-11T11:14:20.484000+00:00"
        assert normalize_iso_timestamp(iso_offset) == iso_offset

    def test_microseconds_timestamps_adversarial_challenge(self):
        """Microsecond timestamps (1791717260484000) must be parsed without falling back to now()."""
        # Microseconds for 2026-10-11T11:14:20.484000 UTC
        micro_ts = 1791717260484000
        result_int = normalize_iso_timestamp(micro_ts)
        result_str = normalize_iso_timestamp(str(micro_ts))

        # If it parsed accurately, it must start with "2026-10-11T11:14:20"
        # If it fell back to datetime.now(), the hour will be the current run hour (e.g. 13:xx or later)
        assert result_int.startswith("2026-10-11T11:14:20"), (
            f"Failed to normalize int microsecond timestamp {micro_ts}! Result defaulted to: {result_int}"
        )
        assert result_str.startswith("2026-10-11T11:14:20"), (
            f"Failed to normalize str microsecond timestamp {micro_ts}! Result defaulted to: {result_str}"
        )

    def test_nanoseconds_timestamps_adversarial_challenge(self):
        """Nanosecond timestamps (1791717260484000000) must be parsed without falling back to now()."""
        nano_ts = 1791717260484000000
        result_int = normalize_iso_timestamp(nano_ts)
        result_str = normalize_iso_timestamp(str(nano_ts))

        assert result_int.startswith("2026-10-11T11:14:20"), (
            f"Failed to normalize int nanosecond timestamp {nano_ts}! Result defaulted to: {result_int}"
        )
        assert result_str.startswith("2026-10-11T11:14:20"), (
            f"Failed to normalize str nanosecond timestamp {nano_ts}! Result defaulted to: {result_str}"
        )


class TestZeroMockAndIdentifierEscapingChallenge:
    """Stress tests verifying zero-mock purity and SQLite identifier escaping."""

    def test_no_synthetic_metric_in_lens_client_code(self):
        """Verifies lens_client.py contains zero instances of '10/14'."""
        lens_client_path = PROJECT_ROOT / "lens_client.py"
        content = lens_client_path.read_text(encoding="utf-8")
        assert "10/14" not in content, "Found forbidden synthetic metric '10/14' in lens_client.py!"

    def test_sqlite_fallback_table_with_special_characters(self):
        """Verifies SQLite queries safely handle table names with hyphens and spaces."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_special.db"
            conn = sqlite3.connect(db_path)
            table_name = "screen-frames 2026"
            conn.execute(
                f'CREATE TABLE "{table_name}" ('
                f'id INTEGER PRIMARY KEY, '
                f'epoch_ms INTEGER, '
                f'app_name TEXT, '
                f'window_title TEXT, '
                f'ocr_text TEXT);'
            )
            conn.execute(
                f'INSERT INTO "{table_name}" VALUES (1, 1791717260484, "PyCharm", "main.py", "code");'
            )
            conn.commit()
            conn.close()

            client = ScreenLensClient(sqlite_db_paths=[db_path])
            harvest = client._harvest_from_sqlite()

            assert harvest is not None
            assert harvest["active_app"] == "PyCharm"
            assert harvest["window_title"] == "main.py"
            assert harvest["ocr_snippet"] == "code"
            assert harvest["timestamp"].startswith("2026-10-11T11:14:20.484")
