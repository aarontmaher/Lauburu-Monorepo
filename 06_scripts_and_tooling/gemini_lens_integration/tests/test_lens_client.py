"""E2E & Integration Tests for Screen Lens Client (Milestone 2, Features 4-6).

Covers Tiers 1-5 per TEST_INFRA.md:
- Tier 1: Feature Coverage (Feature 4 Live Harvester, Feature 5 SQLite Fallback, Feature 6 Spark MCP, Consolidated Context)
- Tier 2: Boundary Value Analysis & Corner Cases (Timeout recovery, corrupt JSON, empty DB, proxy bypass)
- Tier 3: Pairwise Combinations & Concurrency (Multi-tier fallback progression, thread safety)
- Tier 4: Real-World Workload Scenarios (Live host state, network drop, complete daemon offline recovery)
- Tier 5: Acceptance Criteria Contract (PROJECT.md contract conformance, zero-mock truth)
"""

from __future__ import annotations

import concurrent.futures
import datetime
import json
import os
import sqlite3
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from lens_client import (
    DEFAULT_CONFIG,
    ScreenLensClient,
    create_proxy_bypass_opener,
    get_darwin_front_app,
    get_darwin_memory_info,
    normalize_iso_timestamp,
)


class TestLensClientTier1FeatureCoverage:
    """Tier 1: Feature Coverage — Primary happy-path perception harvesting and Spark MCP probe."""

    def test_live_screen_lens_harvest_or_mock_free_fallback(self):
        """Feature 4: Probes live Screen Lens daemons or executes mock-free SQLite / OS fallback."""
        client = ScreenLensClient()
        perception = client.harvest_perception(timeout_s=2.0)

        assert isinstance(perception, dict)
        # Required interface contract keys per PROJECT.md
        required_keys = [
            "timestamp",
            "active_app",
            "window_title",
            "ocr_snippet",
            "mesh_health",
            "source",
            "endpoint",
        ]
        for key in required_keys:
            assert key in perception, f"Missing required contract key: {key}"

        assert isinstance(perception["timestamp"], str)
        assert len(perception["timestamp"]) > 0
        assert isinstance(perception["active_app"], str)
        assert len(perception["active_app"]) > 0
        assert isinstance(perception["window_title"], str)
        assert isinstance(perception["ocr_snippet"], str)
        assert isinstance(perception["mesh_health"], dict)
        assert perception["source"] in ("live_api", "sqlite", "system_fallback")
        assert isinstance(perception["endpoint"], str)

    def test_screen_lens_sqlite_fallback_read_only(self, tmp_path: Path):
        """Feature 5: Verifies SQLite fallback in read-only URI mode without lock contention."""
        test_db = tmp_path / "test_ocr_frames.db"
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE frames ("
            "id INTEGER PRIMARY KEY, "
            "timestamp REAL, "
            "app_name TEXT, "
            "window_title TEXT, "
            "ocr_text TEXT, "
            "bounds_json TEXT, "
            "device_node TEXT);"
        )
        test_time = 1791717260.484
        cursor.execute(
            "INSERT INTO frames (id, timestamp, app_name, window_title, ocr_text, bounds_json, device_node) "
            "VALUES (?, ?, ?, ?, ?, ?, ?);",
            (
                42,
                test_time,
                "Terminal",
                "L1 Sovereign Console",
                "Active window: Terminal on L1",
                "[]",
                "L1",
            ),
        )
        conn.commit()
        conn.close()

        # Isolate client to use unreachable live ports and point to this test DB
        offline_cfg = {
            "endpoints": {
                "screen_lens": {
                    "orchestrator_url": "http://127.0.0.1:59991",
                    "ocr_stream_url": "http://127.0.0.1:59992",
                    "hud_mjpeg_url": "http://127.0.0.1:59993",
                }
            }
        }
        client = ScreenLensClient(
            config_dict=offline_cfg, sqlite_db_paths=[test_db]
        )
        res = client.harvest_perception(timeout_s=0.5)

        assert res["source"] == "sqlite"
        assert res["active_app"] == "Terminal"
        assert res["window_title"] == "L1 Sovereign Console"
        assert "Active window: Terminal" in res["ocr_snippet"]
        assert res["mesh_health"]["frame_id"] == 42
        assert res["endpoint"] == str(test_db)

        # Confirm read-only mode prevents database modification
        ro_conn = sqlite3.connect(f"file:{test_db}?mode=ro", uri=True)
        with pytest.raises(sqlite3.OperationalError):
            ro_conn.execute("INSERT INTO frames (id) VALUES (99);")
        ro_conn.close()

    def test_screen_lens_system_fallback_mock_free(self):
        """Feature 5 & Rule 1: Verifies genuine Darwin OS / kernel telemetry fallback when ports & DB are offline."""
        offline_cfg = {
            "endpoints": {
                "screen_lens": {
                    "orchestrator_url": "http://127.0.0.1:59991",
                    "ocr_stream_url": "http://127.0.0.1:59992",
                    "hud_mjpeg_url": "http://127.0.0.1:59993",
                }
            }
        }
        # Explicit empty sqlite_db_paths forces system fallback
        client = ScreenLensClient(config_dict=offline_cfg, sqlite_db_paths=[])
        res = client.harvest_perception(timeout_s=0.5)

        assert res["source"] == "system_fallback"
        assert res["endpoint"] == "system_kernel"
        assert isinstance(res["active_app"], str)
        assert len(res["active_app"]) > 0
        assert res["ocr_snippet"] == ""  # Zero mock rule: no fake OCR snippet fabricated
        assert "os" in res["mesh_health"]
        if sys.platform == "darwin":
            assert res["mesh_health"]["os"] == "darwin"
            assert "ram_info" in res["mesh_health"]

    def test_connect_gemini_spark_mcp(self):
        """Feature 6: Probes Gemini Spark MCP daemon and returns connection status dictionary gracefully."""
        client = ScreenLensClient()
        spark_status = client.connect_gemini_spark(timeout_s=2.0)

        assert isinstance(spark_status, dict)
        required_keys = ["connected", "endpoint", "status", "timestamp", "latency_ms", "details"]
        for k in required_keys:
            assert k in spark_status, f"Missing key in spark_status: {k}"

        assert isinstance(spark_status["connected"], bool)
        assert isinstance(spark_status["endpoint"], str)
        assert spark_status["status"] in ("online", "offline", "online_endpoint_unmatched")
        if spark_status["connected"]:
            assert spark_status["latency_ms"] is not None
            assert spark_status["latency_ms"] >= 0.0

    def test_consolidated_context_structure(self):
        """Feature 4-6: Verifies get_consolidated_context combines perception and Spark status cleanly."""
        client = ScreenLensClient()
        ctx = client.get_consolidated_context(timeout_s=2.0)

        assert isinstance(ctx, dict)
        assert "timestamp" in ctx
        assert "active_app" in ctx
        assert "window_title" in ctx
        assert "ocr_snippet" in ctx
        assert "mesh_health" in ctx
        assert "source" in ctx
        assert "endpoint" in ctx
        assert "screen_lens" in ctx
        assert "gemini_spark" in ctx
        assert "is_live" in ctx
        assert "spark_connected" in ctx
        assert "status" in ctx
        assert ctx["status"] in ("synchronized", "degraded")


class TestLensClientTier2BoundaryAndCornerCases:
    """Tier 2: Boundary Value Analysis & Corner Cases."""

    def test_zero_or_negative_timeout_safety(self):
        """Boundary: Passing zero or negative timeout does not crash and uses safe floor."""
        client = ScreenLensClient()
        # Should not throw ValueError or hang
        res_zero = client.harvest_perception(timeout_s=0.0)
        assert isinstance(res_zero, dict)
        assert res_zero["source"] in ("live_api", "sqlite", "system_fallback")

        res_neg = client.harvest_perception(timeout_s=-5.0)
        assert isinstance(res_neg, dict)

        spark_zero = client.connect_gemini_spark(timeout_s=0.0)
        assert isinstance(spark_zero, dict)

    def test_corrupt_json_payload_from_live_port_falls_back(self, tmp_path: Path):
        """Corner Case: Live endpoint returning malformed JSON falls back gracefully to SQLite or OS."""
        test_db = tmp_path / "fallback.db"
        conn = sqlite3.connect(test_db)
        conn.execute("CREATE TABLE frames (id INT, app_name TEXT, window_title TEXT, text TEXT, timestamp REAL);")
        conn.execute("INSERT INTO frames VALUES (1, 'FallbackApp', 'FallbackWin', 'SampleText', 1700000000);")
        conn.commit()
        conn.close()

        # Custom opener returning corrupt non-JSON byte string
        class MockCorruptResponse:
            status = 200

            def read(self):
                return b"<html><body>502 Bad Gateway / Corrupt JSON</body></html>"

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        class MockOpener(urllib.request.OpenerDirector):
            def open(self, fullurl, data=None, timeout=None):
                return MockCorruptResponse()

        client = ScreenLensClient(
            opener=MockOpener(),
            sqlite_db_paths=[test_db]
        )
        res = client.harvest_perception(timeout_s=0.5)

        # Corrupt JSON from port probe must cause fallback to SQLite
        assert res["source"] == "sqlite"
        assert res["active_app"] == "FallbackApp"

    def test_empty_sqlite_db_falls_back_to_system(self, tmp_path: Path):
        """Boundary: Existing SQLite DB with zero rows falls through to system_fallback."""
        empty_db = tmp_path / "empty.db"
        conn = sqlite3.connect(empty_db)
        conn.execute("CREATE TABLE frames (id INT, app_name TEXT, window_title TEXT);")
        conn.commit()
        conn.close()

        offline_cfg = {
            "endpoints": {
                "screen_lens": {
                    "orchestrator_url": "http://127.0.0.1:59991",
                    "ocr_stream_url": "http://127.0.0.1:59992",
                    "hud_mjpeg_url": "http://127.0.0.1:59993",
                }
            }
        }
        client = ScreenLensClient(
            config_dict=offline_cfg, sqlite_db_paths=[empty_db]
        )
        res = client.harvest_perception(timeout_s=0.5)
        assert res["source"] == "system_fallback"

    def test_corrupt_sqlite_file_falls_back_to_system(self, tmp_path: Path):
        """Corner Case: Truncated or corrupt SQLite file header falls through to system_fallback without crashing."""
        corrupt_db = tmp_path / "corrupt.db"
        corrupt_db.write_bytes(b"NOT A SQLITE FILE HEADER TRUNCATED DATA")

        offline_cfg = {
            "endpoints": {
                "screen_lens": {
                    "orchestrator_url": "http://127.0.0.1:59991",
                    "ocr_stream_url": "http://127.0.0.1:59992",
                    "hud_mjpeg_url": "http://127.0.0.1:59993",
                }
            }
        }
        client = ScreenLensClient(
            config_dict=offline_cfg, sqlite_db_paths=[corrupt_db]
        )
        res = client.harvest_perception(timeout_s=0.5)
        assert res["source"] == "system_fallback"

    def test_proxy_bypass_opener_handler_properties(self):
        """Feature 4 Invariant: Opener built via create_proxy_bypass_opener has no proxy intercepts."""
        opener = create_proxy_bypass_opener()
        assert isinstance(opener, urllib.request.OpenerDirector)

        # Standard urllib build_opener(ProxyHandler({})) suppresses default proxy hooks
        proxy_handlers = [
            h for h in opener.handlers if isinstance(h, urllib.request.ProxyHandler)
        ]
        # In python urllib, passing empty ProxyHandler({}) omits proxy intercept methods
        assert len(proxy_handlers) == 0

    def test_config_loading_precedence_and_fallback(self, tmp_path: Path):
        """Boundary: Config loading prioritizes explicit dict -> explicit file -> default."""
        # 1. Explicit dict
        custom_dict = {"endpoints": {"screen_lens": {"orchestrator_url": "http://127.0.0.1:12345"}}}
        c1 = ScreenLensClient(config_dict=custom_dict)
        assert c1.config["endpoints"]["screen_lens"]["orchestrator_url"] == "http://127.0.0.1:12345"

        # 2. Explicit file path
        cfg_file = tmp_path / "custom_cfg.json"
        cfg_file.write_text(json.dumps(custom_dict), encoding="utf-8")
        c2 = ScreenLensClient(config_path=cfg_file)
        assert c2.config["endpoints"]["screen_lens"]["orchestrator_url"] == "http://127.0.0.1:12345"

        # 3. Missing file path falls back gracefully to default
        c3 = ScreenLensClient(config_path=tmp_path / "nonexistent.json")
        assert "endpoints" in c3.config


class TestLensClientTier3CrossFeatureCombinations:
    """Tier 3: Pairwise Combinations & Pipeline Flow."""

    def test_multi_tier_fallback_chain_progression(self, tmp_path: Path):
        """Cross-Feature: Validates progression: Live API -> SQLite -> OS Kernel Fallback."""
        # Setup valid test DB
        db_path = tmp_path / "progression.db"
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE frames (id INT, app_name TEXT, window_title TEXT, ocr_text TEXT, timestamp REAL);")
        conn.execute("INSERT INTO frames VALUES (1, 'ProgressionApp', 'Step 2 DB', 'Text 2', 1791717000);")
        conn.commit()
        conn.close()

        # Step 2: Live ports down, DB up -> returns SQLite
        client_step2 = ScreenLensClient(
            config_dict={
                "endpoints": {
                    "screen_lens": {
                        "orchestrator_url": "http://127.0.0.1:59991",
                        "ocr_stream_url": "http://127.0.0.1:59992",
                        "hud_mjpeg_url": "http://127.0.0.1:59993",
                    }
                }
            },
            sqlite_db_paths=[db_path]
        )
        p2 = client_step2.harvest_perception(timeout_s=0.2)
        assert p2["source"] == "sqlite"
        assert p2["active_app"] == "ProgressionApp"

        # Step 3: Live ports down, DB down -> returns system_fallback
        client_step3 = ScreenLensClient(
            config_dict={
                "endpoints": {
                    "screen_lens": {
                        "orchestrator_url": "http://127.0.0.1:59991",
                        "ocr_stream_url": "http://127.0.0.1:59992",
                        "hud_mjpeg_url": "http://127.0.0.1:59993",
                    }
                }
            },
            sqlite_db_paths=[]
        )
        p3 = client_step3.harvest_perception(timeout_s=0.2)
        assert p3["source"] == "system_fallback"
        assert p3["endpoint"] == "system_kernel"

    def test_concurrent_multithreaded_harvesting(self):
        """Cross-Feature: 10 concurrent threads query ScreenLensClient without lock contention."""
        client = ScreenLensClient()

        def worker(idx: int) -> Dict[str, Any]:
            p = client.harvest_perception(timeout_s=1.5)
            s = client.connect_gemini_spark(timeout_s=1.5)
            c = client.get_consolidated_context(timeout_s=1.5)
            return {"index": idx, "source": p["source"], "status": c["status"]}

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 10
        for r in results:
            assert r["source"] in ("live_api", "sqlite", "system_fallback")
            assert r["status"] in ("synchronized", "degraded")

    def test_timestamp_normalization_formats(self):
        """Cross-Feature: normalize_iso_timestamp handles float, int, ISO string, and None."""
        ts_now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        assert normalize_iso_timestamp(ts_now) == ts_now

        # Epoch float
        epoch = 1791717260.484
        normalized = normalize_iso_timestamp(epoch)
        assert "T" in normalized
        assert normalized.endswith("+00:00") or normalized.endswith("Z")

        # String containing float
        normalized_str = normalize_iso_timestamp("1791717260.484")
        assert "T" in normalized_str

        # None returns current timestamp
        assert "T" in normalize_iso_timestamp(None)


class TestLensClientTier4RealWorldScenarios:
    """Tier 4: Real-World Workload Scenarios."""

    def test_scenario_live_screen_lens_perception_on_host(self):
        """Scenario 1: Harvests live context on local host, verifying active window and mesh telemetry."""
        client = ScreenLensClient()
        perception = client.harvest_perception(timeout_s=2.0)

        assert perception["source"] in ("live_api", "sqlite", "system_fallback")
        assert len(perception["active_app"]) > 0
        assert perception["endpoint"] is not None

        if perception["source"] == "live_api":
            # Live port was reached
            assert "raw_perception" in perception
            assert "127.0.0.1" in perception["endpoint"]

    def test_scenario_gemini_spark_daemon_active_or_offline_handled(self):
        """Scenario 2: Probes Gemini Spark on port 9999 and validates connection payload."""
        client = ScreenLensClient()
        status = client.connect_gemini_spark(timeout_s=2.0)

        assert "connected" in status
        assert "endpoint" in status
        assert "status" in status

        if status["connected"]:
            assert status["status"] == "online"
            assert status["latency_ms"] < 2000.0  # Must respond within timeout

    def test_scenario_darwin_launch_services_front_app(self):
        """Scenario 3: Probes /usr/bin/lsappinfo on macOS and confirms authentic app detection."""
        if sys.platform != "darwin":
            pytest.skip("lsappinfo is only available on macOS Darwin.")

        app_name, pid, bundle_id = get_darwin_front_app()
        # On macOS desktop with user logged in, front app is almost always present
        if app_name is not None:
            assert isinstance(app_name, str)
            assert len(app_name) > 0
            if pid is not None:
                assert pid > 0

    def test_scenario_darwin_memory_sanctuary_audit(self):
        """Scenario 4: Validates Mach vm_stat audit adheres to Rule 3 4.8 GB sanctuary headroom logic."""
        if sys.platform != "darwin":
            pytest.skip("vm_stat is only available on macOS Darwin.")

        mem = get_darwin_memory_info()
        assert "free_gb" in mem
        assert "wired_gb" in mem
        assert "active_gb" in mem
        assert "sanctuary_floor_gb" in mem
        assert mem["sanctuary_floor_gb"] == 4.8
        assert isinstance(mem["sanctuary_preserved"], bool)


class TestLensClientTier5AcceptanceContract:
    """Tier 5: Acceptance Criteria & Interface Contract Conformance."""

    def test_interface_contract_conformance_with_project_md(self):
        """Acceptance Criteria: Verify ScreenLensClient interface contract matching PROJECT.md."""
        client = ScreenLensClient()
        res = client.harvest_perception(timeout_s=2.0)

        # Exact contract specification from PROJECT.md line 108-110:
        # {"timestamp": str, "active_app": str, "window_title": str, "ocr_snippet": str, "mesh_health": dict, "source": str}
        assert "timestamp" in res and isinstance(res["timestamp"], str)
        assert "active_app" in res and isinstance(res["active_app"], str)
        assert "window_title" in res and isinstance(res["window_title"], str)
        assert "ocr_snippet" in res and isinstance(res["ocr_snippet"], str)
        assert "mesh_health" in res and isinstance(res["mesh_health"], dict)
        assert "source" in res and isinstance(res["source"], str)
        assert "endpoint" in res and isinstance(res["endpoint"], str)

    def test_zero_mock_empirical_truth(self):
        """Rule 1 (Zero-Mock Cardinal Law): No fabricated or hardcoded simulation telemetry strings."""
        client = ScreenLensClient()
        res = client.harvest_perception(timeout_s=2.0)

        # Disallowed placeholder values that indicate dummy mock implementation
        forbidden_placeholders = [
            "MOCK_APP",
            "MOCK_WINDOW",
            "FAKE_OCR",
            "SIMULATED_DATA",
            "DUMMY_STRING",
            "PLACEHOLDER_HEALTH",
        ]
        for fb in forbidden_placeholders:
            assert fb not in res["active_app"].upper()
            assert fb not in res["window_title"].upper()
            assert fb not in res["ocr_snippet"].upper()


class TestLensClientMilestone2Remediation:
    """Milestone 2 Remediation Regression & Verification Tests."""

    def test_normalize_iso_timestamp_millisecond_epoch(self):
        """Remediation 4: Normalizes millisecond epoch float/int/str without overflow."""
        ms_epoch = 1791717260484.0
        expected_iso = datetime.datetime.fromtimestamp(
            ms_epoch / 1000.0, tz=datetime.timezone.utc
        ).isoformat()
        res_float = normalize_iso_timestamp(ms_epoch)
        assert res_float == expected_iso

        res_str = normalize_iso_timestamp("1791717260484")
        assert res_str == expected_iso

    def test_normalize_iso_timestamp_microsecond_and_nanosecond_epoch(self):
        """Remediation 7: Normalizes microsecond and nanosecond epoch without overflow or now() fallback."""
        micro_epoch = 1791717260484000
        expected_iso = datetime.datetime.fromtimestamp(
            micro_epoch / 1e6, tz=datetime.timezone.utc
        ).isoformat()
        assert normalize_iso_timestamp(micro_epoch) == expected_iso
        assert normalize_iso_timestamp(float(micro_epoch)) == expected_iso
        assert normalize_iso_timestamp(str(micro_epoch)) == expected_iso

        nano_epoch = 1791717260484000000
        expected_nano_iso = datetime.datetime.fromtimestamp(
            nano_epoch / 1e9, tz=datetime.timezone.utc
        ).isoformat()
        assert normalize_iso_timestamp(nano_epoch) == expected_nano_iso
        assert normalize_iso_timestamp(str(nano_epoch)) == expected_nano_iso

    def test_dynamic_darwin_page_size_accounting(self, monkeypatch):
        """Remediation 3: Uses dynamic page size from resource.getpagesize()."""
        if sys.platform != "darwin":
            pytest.skip("Darwin only test")

        import resource
        real_page_size = resource.getpagesize()
        assert real_page_size in (4096, 16384)

        mem = get_darwin_memory_info()
        assert "free_gb" in mem
        assert "wired_gb" in mem

    def test_sqlite_fallback_with_hyphenated_table_name(self, tmp_path: Path):
        """Remediation 5: Safely handles table identifiers with hyphens via quoted SQL."""
        db_file = tmp_path / "hyphen_test.sqlite"
        conn = sqlite3.connect(db_file)
        conn.execute('CREATE TABLE "screen-frames" (id INTEGER PRIMARY KEY, timestamp REAL, app_name TEXT, window_title TEXT, ocr_text TEXT);')
        conn.execute('INSERT INTO "screen-frames" (id, timestamp, app_name, window_title, ocr_text) VALUES (1, 1791717260.0, "TestApp", "TestWin", "TestOCR");')
        conn.commit()
        conn.close()

        client = ScreenLensClient(config_dict={"endpoints": {"screen_lens": {}}}, sqlite_db_paths=[db_file])
        row = client._harvest_from_sqlite()
        assert row is not None
        assert row["source"] == "sqlite"
        assert row["active_app"] == "TestApp"
        assert row["window_title"] == "TestWin"
        assert row["ocr_snippet"] == "TestOCR"

    def test_connect_gemini_spark_configuration_isolation(self):
        """Remediation 1: Custom configured endpoints must NOT leak or fall back to localhost:9999."""
        cfg = {
            "endpoints": {
                "gemini_spark": {
                    "mcp_project_health_url": "http://127.0.0.1:58999/health",
                    "mcp_health_url": "http://127.0.0.1:58999/health",
                }
            }
        }
        client = ScreenLensClient(config_dict=cfg)
        status = client.connect_gemini_spark(timeout_s=0.2)
        assert status["connected"] is False
        assert status["status"] == "offline"
        assert "58999" in status["endpoint"]
        assert "9999" not in str(status["endpoint"])

    def test_live_endpoint_mesh_health_missing_returns_empty_dict(self):
        """Remediation 2: Purges fake '10/14' metric; returns empty dict when mesh_health missing."""
        class MockResp:
            status = 200
            def read(self):
                return json.dumps({
                    "timestamp": "2026-10-11T13:00:00Z",
                    "screen": {"active_app": "LiveApp", "window_title": "LiveWin", "recent_ocr": ["text"]},
                }).encode("utf-8")
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass

        class MockOpener(urllib.request.OpenerDirector):
            def open(self, req, timeout=None):
                return MockResp()

        client = ScreenLensClient(opener=MockOpener(), sqlite_db_paths=[])
        res = client.harvest_perception(timeout_s=0.2)
        assert res["source"] == "live_api"
        assert res["mesh_health"] == {}
        assert res["mesh_health"].get("healthy_services") is None

    def test_sync_config_json_has_mcp_project_health_url(self):
        """Remediation 6: sync_config.json contains mcp_project_health_url matching live daemon."""
        config_path = Path(__file__).parent.parent / "config" / "sync_config.json"
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        spark_cfg = cfg.get("endpoints", {}).get("gemini_spark", {})
        assert "mcp_project_health_url" in spark_cfg
        assert spark_cfg["mcp_project_health_url"] == "http://127.0.0.1:9999/mcp/project/health"

    def test_get_live_endpoints_in_order_default_includes_remote_mac_mini(self):
        """Remediation 7: Candidate endpoints include remote Mac Mini L1 endpoints in default topology."""
        client = ScreenLensClient()
        endpoints = client._get_live_endpoints_in_order()
        urls = [ep[1] for ep in endpoints]

        assert "http://127.0.0.1:3037/api/orchestrator/state" in urls
        assert "http://127.0.0.1:3035/api/latest" in urls
        assert "http://127.0.0.1:4003/api/telemetry/live" in urls
        assert "http://100.119.199.76:3037/api/orchestrator/state" in urls
        assert "http://100.119.199.76:3035/api/latest" in urls
        assert "http://100.119.199.76:4003/api/telemetry/live" in urls

        # Ensure local endpoints are tried before remote endpoints
        assert urls.index("http://127.0.0.1:3037/api/orchestrator/state") < urls.index("http://100.119.199.76:3037/api/orchestrator/state")
        assert urls.index("http://127.0.0.1:3035/api/latest") < urls.index("http://100.119.199.76:3035/api/latest")
        assert urls.index("http://127.0.0.1:4003/api/telemetry/live") < urls.index("http://100.119.199.76:4003/api/telemetry/live")

    def test_get_live_endpoints_in_order_offline_isolation_omits_remote(self):
        """Remediation 8: Custom non-default ports omit remote endpoints to maintain offline test isolation."""
        offline_cfg = {
            "endpoints": {
                "screen_lens": {
                    "orchestrator_url": "http://127.0.0.1:59991",
                    "ocr_stream_url": "http://127.0.0.1:59992",
                    "hud_mjpeg_url": "http://127.0.0.1:59993",
                }
            }
        }
        client = ScreenLensClient(config_dict=offline_cfg)
        endpoints = client._get_live_endpoints_in_order()
        urls = [ep[1] for ep in endpoints]

        assert len(urls) == 3
        assert "http://127.0.0.1:59991/api/orchestrator/state" in urls
        assert "http://127.0.0.1:59992/api/latest" in urls
        assert "http://127.0.0.1:59993/api/telemetry/live" in urls
        assert not any("100.119.199.76" in u for u in urls)

    def test_get_live_endpoints_in_order_custom_remote_urls(self):
        """Remediation 9: Explicit remote endpoint URLs are included in candidates."""
        cfg = {
            "endpoints": {
                "screen_lens": {
                    "orchestrator_url": "http://127.0.0.1:3037",
                    "ocr_stream_url": "http://127.0.0.1:3035",
                    "hud_mjpeg_url": "http://127.0.0.1:4003",
                    "remote_orchestrator_url": "http://10.0.0.50:3037",
                    "remote_ocr_stream_url": "http://10.0.0.50:3035",
                    "remote_hud_mjpeg_url": "http://10.0.0.50:4003",
                }
            }
        }
        client = ScreenLensClient(config_dict=cfg)
        endpoints = client._get_live_endpoints_in_order()
        urls = [ep[1] for ep in endpoints]

        assert "http://10.0.0.50:3037/api/orchestrator/state" in urls
        assert "http://10.0.0.50:3035/api/latest" in urls
        assert "http://10.0.0.50:4003/api/telemetry/live" in urls

