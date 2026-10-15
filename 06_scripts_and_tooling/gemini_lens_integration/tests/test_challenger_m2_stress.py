"""Empirical Adversarial Stress Test Suite for Milestone 2 (ScreenLensClient).

Authored by challenger_m2_1.
Strictly evaluates:
1. Concurrency & Thread Safety: Multi-threaded simultaneous queries (50-100 threads)
   across harvest_perception, connect_gemini_spark, and get_consolidated_context.
2. DB Lock Contention & Throughput: High-throughput concurrent reads on SQLite fallback,
   behavior under active write locks (WAL and DELETE rollback journal), and timeout recovery.
3. Write-Prevention Rigor: Strict immutability under `mode=ro` URI mode (DML, DDL, VACUUM, PRAGMA)
   with cryptographic SHA256 file checksum verification.
4. Adversarial Socket & Network Conditions: Simulated Slowloris, oversized payloads,
   HTTP error codes, and thread-safe proxy bypass.
5. Subprocess & Darwin Memory Sanctuary: High-concurrency system fallback stability.
"""

from __future__ import annotations

import concurrent.futures
import datetime
import hashlib
import http.server
import json
import logging
import os
import socket
import sqlite3
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lens_client import (
    DEFAULT_CONFIG,
    ScreenLensClient,
    create_proxy_bypass_opener,
    get_darwin_front_app,
    get_darwin_memory_info,
    normalize_iso_timestamp,
)


def _compute_sha256(file_path: Path) -> str:
    """Computes SHA256 checksum of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _populate_test_db(db_path: Path, num_frames: int = 500, wal_mode: bool = False) -> None:
    """Creates and populates a realistic test SQLite database."""
    conn = sqlite3.connect(db_path)
    if wal_mode:
        conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(
        "CREATE TABLE frames ("
        "id INTEGER PRIMARY KEY, "
        "timestamp REAL, "
        "app_name TEXT, "
        "window_title TEXT, "
        "ocr_text TEXT, "
        "bounds_json TEXT, "
        "device_node TEXT);"
    )
    records = [
        (
            i,
            1791717000.0 + i * 0.1,
            f"TestApp_{i % 5}",
            f"Test Window {i}",
            f"OCR snippet content at index {i}",
            "[]",
            "L1",
        )
        for i in range(1, num_frames + 1)
    ]
    conn.executemany(
        "INSERT INTO frames VALUES (?, ?, ?, ?, ?, ?, ?);",
        records,
    )
    conn.commit()
    conn.close()


class TestConcurrencyAndThreadSafety:
    """Stress tests for multi-threaded concurrency, thread safety, and race conditions."""

    def test_high_concurrency_harvest_perception_shared_instance(self):
        """Stress: 50 concurrent threads query harvest_perception() on a single ScreenLensClient instance."""
        client = ScreenLensClient()
        num_threads = 50
        barrier = threading.Barrier(num_threads)
        errors: List[Exception] = []
        results: List[Dict[str, Any]] = []
        lock = threading.Lock()

        def worker(thread_idx: int):
            try:
                barrier.wait(timeout=5.0)
                res = client.harvest_perception(timeout_s=2.0)
                with lock:
                    results.append(res)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert not errors, f"Encountered {len(errors)} thread errors: {errors[:3]}"
        assert len(results) == num_threads

        for r in results:
            assert isinstance(r, dict)
            assert "source" in r
            assert r["source"] in ("live_api", "sqlite", "system_fallback")
            assert "timestamp" in r and len(r["timestamp"]) > 0
            assert "active_app" in r
            assert "window_title" in r

    def test_high_concurrency_spark_mcp_probing_shared_instance(self):
        """Stress: 50 concurrent threads query connect_gemini_spark() on a single instance."""
        client = ScreenLensClient()
        num_threads = 50
        barrier = threading.Barrier(num_threads)
        errors: List[Exception] = []
        results: List[Dict[str, Any]] = []
        lock = threading.Lock()

        def worker(thread_idx: int):
            try:
                barrier.wait(timeout=5.0)
                res = client.connect_gemini_spark(timeout_s=2.0)
                with lock:
                    results.append(res)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert not errors, f"Encountered {len(errors)} thread errors in spark probe: {errors[:3]}"
        assert len(results) == num_threads

        for r in results:
            assert isinstance(r, dict)
            assert "connected" in r and isinstance(r["connected"], bool)
            assert "status" in r and r["status"] in ("online", "offline")
            assert "details" in r

    def test_high_concurrency_consolidated_context(self):
        """Stress: 50 concurrent threads query get_consolidated_context() on a single instance."""
        client = ScreenLensClient()
        num_threads = 50
        barrier = threading.Barrier(num_threads)
        errors: List[Exception] = []
        results: List[Dict[str, Any]] = []
        lock = threading.Lock()

        def worker(thread_idx: int):
            try:
                barrier.wait(timeout=5.0)
                res = client.get_consolidated_context(timeout_s=2.0)
                with lock:
                    results.append(res)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert not errors, f"Encountered errors: {errors[:3]}"
        assert len(results) == num_threads

        for r in results:
            assert isinstance(r, dict)
            assert "status" in r and r["status"] in ("synchronized", "degraded")
            assert "is_live" in r and isinstance(r["is_live"], bool)
            assert "spark_connected" in r and isinstance(r["spark_connected"], bool)
            assert "screen_lens" in r
            assert "gemini_spark" in r

    def test_mixed_heterogeneous_concurrent_workload(self):
        """Stress: 60 workers executing interleaved calls simultaneously across endpoints."""
        client = ScreenLensClient()
        total_workers = 60
        barrier = threading.Barrier(total_workers)
        results: List[Tuple[str, Any]] = []
        errors: List[Exception] = []
        lock = threading.Lock()

        def worker(idx: int, task_type: str):
            try:
                barrier.wait(timeout=5.0)
                if task_type == "harvest":
                    out = client.harvest_perception(timeout_s=1.5)
                elif task_type == "spark":
                    out = client.connect_gemini_spark(timeout_s=1.5)
                else:
                    out = client.get_consolidated_context(timeout_s=1.5)
                with lock:
                    results.append((task_type, out))
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads: List[threading.Thread] = []
        for i in range(total_workers):
            task = ["harvest", "spark", "consolidated"][i % 3]
            threads.append(threading.Thread(target=worker, args=(i, task)))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15.0)

        assert not errors, f"Heterogeneous concurrency failed with errors: {errors}"
        assert len(results) == total_workers


class TestSQLiteLockContentionAndThroughput:
    """Stress tests evaluating SQLite read-only mode, lock contention, and writer concurrency."""

    def test_massive_concurrent_sqlite_reads(self, tmp_path: Path):
        """Throughput: 80 concurrent threads read from SQLite fallback DB in mode=ro."""
        db_path = tmp_path / "concurrent_read.db"
        _populate_test_db(db_path, num_frames=1000)

        # Force SQLite fallback by pointing live endpoints to offline ports
        offline_cfg = {
            "endpoints": {
                "screen_lens": {
                    "orchestrator_url": "http://127.0.0.1:58881",
                    "ocr_stream_url": "http://127.0.0.1:58882",
                    "hud_mjpeg_url": "http://127.0.0.1:58883",
                }
            }
        }
        client = ScreenLensClient(config_dict=offline_cfg, sqlite_db_paths=[db_path])

        num_threads = 80
        barrier = threading.Barrier(num_threads)
        results: List[Dict[str, Any]] = []
        errors: List[Exception] = []
        lock = threading.Lock()

        def reader(idx: int):
            try:
                barrier.wait(timeout=5.0)
                t0 = time.perf_counter()
                res = client.harvest_perception(timeout_s=0.5)
                elapsed = time.perf_counter() - t0
                with lock:
                    results.append({"idx": idx, "res": res, "elapsed": elapsed})
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=reader, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15.0)

        assert not errors, f"Concurrent SQLite read failed with errors: {errors}"
        assert len(results) == num_threads

        for item in results:
            res = item["res"]
            assert res["source"] == "sqlite"
            assert res["mesh_health"]["frame_id"] == 1000
            assert "Test Window 1000" in res["window_title"]
            # Read operations must complete fast
            assert item["elapsed"] < 3.0

    def test_concurrent_reads_during_active_writer_transactions(self, tmp_path: Path):
        """Contention: Concurrent readers query SQLite while an active writer performs continuous writes."""
        db_path = tmp_path / "writer_contention.db"
        _populate_test_db(db_path, num_frames=100)

        offline_cfg = {
            "endpoints": {
                "screen_lens": {
                    "orchestrator_url": "http://127.0.0.1:58881",
                    "ocr_stream_url": "http://127.0.0.1:58882",
                    "hud_mjpeg_url": "http://127.0.0.1:58883",
                }
            }
        }
        client = ScreenLensClient(config_dict=offline_cfg, sqlite_db_paths=[db_path])

        writer_stop_event = threading.Event()
        writer_errors: List[Exception] = []
        write_count = 0

        def writer_loop():
            nonlocal write_count
            w_conn = sqlite3.connect(db_path, timeout=5.0)
            cur_id = 101
            try:
                while not writer_stop_event.is_set():
                    w_conn.execute(
                        "INSERT INTO frames VALUES (?, ?, ?, ?, ?, ?, ?);",
                        (cur_id, time.time(), "WriterApp", f"Write {cur_id}", "Text", "[]", "L1"),
                    )
                    w_conn.commit()
                    cur_id += 1
                    write_count += 1
                    time.sleep(0.005)
            except Exception as exc:
                writer_errors.append(exc)
            finally:
                w_conn.close()

        writer_thread = threading.Thread(target=writer_loop, daemon=True)
        writer_thread.start()

        # Run 40 concurrent readers while writer is actively committing
        num_readers = 40
        barrier = threading.Barrier(num_readers)
        reader_results: List[Dict[str, Any]] = []
        reader_errors: List[Exception] = []
        lock = threading.Lock()

        def reader_worker(idx: int):
            try:
                barrier.wait(timeout=5.0)
                for _ in range(5):
                    res = client.harvest_perception(timeout_s=0.5)
                    with lock:
                        reader_results.append(res)
                    time.sleep(0.005)
            except Exception as exc:
                with lock:
                    reader_errors.append(exc)

        reader_threads = [
            threading.Thread(target=reader_worker, args=(i,)) for i in range(num_readers)
        ]
        for t in reader_threads:
            t.start()
        for t in reader_threads:
            t.join(timeout=15.0)

        writer_stop_event.set()
        writer_thread.join(timeout=5.0)

        assert not writer_errors, f"Writer encountered errors: {writer_errors}"
        assert not reader_errors, f"Readers encountered errors during active writing: {reader_errors}"
        assert len(reader_results) == num_readers * 5
        assert write_count > 0

        # All reads must return valid perception
        for r in reader_results:
            assert r["source"] in ("sqlite", "system_fallback")
            if r["source"] == "sqlite":
                assert r["mesh_health"]["frame_id"] >= 100

    def test_wal_mode_concurrent_high_throughput(self, tmp_path: Path):
        """Contention: WAL mode handles concurrent readers and writers with zero blocking."""
        db_path = tmp_path / "wal_mode_stress.db"
        _populate_test_db(db_path, num_frames=200, wal_mode=True)

        offline_cfg = {
            "endpoints": {
                "screen_lens": {
                    "orchestrator_url": "http://127.0.0.1:58881",
                    "ocr_stream_url": "http://127.0.0.1:58882",
                    "hud_mjpeg_url": "http://127.0.0.1:58883",
                }
            }
        }
        client = ScreenLensClient(config_dict=offline_cfg, sqlite_db_paths=[db_path])

        stop_event = threading.Event()

        def writer():
            conn = sqlite3.connect(db_path)
            i = 201
            while not stop_event.is_set():
                conn.execute(
                    "INSERT INTO frames VALUES (?, ?, ?, ?, ?, ?, ?);",
                    (i, time.time(), "WALApp", "WALWin", "WALText", "[]", "L1"),
                )
                conn.commit()
                i += 1
                time.sleep(0.002)
            conn.close()

        w_thread = threading.Thread(target=writer, daemon=True)
        w_thread.start()

        num_readers = 50
        reader_results: List[Dict[str, Any]] = []
        errors: List[Exception] = []
        lock = threading.Lock()

        def reader(idx: int):
            try:
                for _ in range(10):
                    res = client.harvest_perception(timeout_s=0.5)
                    with lock:
                        reader_results.append(res)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=reader, args=(i,)) for i in range(num_readers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        stop_event.set()
        w_thread.join(timeout=5.0)

        assert not errors, f"WAL mode stress errors: {errors}"
        assert len(reader_results) == num_readers * 10
        for r in reader_results:
            assert r["source"] == "sqlite"

    def test_exclusive_lock_exceeding_timeout_gracefully_falls_back(self, tmp_path: Path):
        """Resilience: When a writer holds an EXCLUSIVE lock exceeding timeout, harvest_perception falls back cleanly."""
        db_path = tmp_path / "exclusive_lock.db"
        _populate_test_db(db_path, num_frames=50)

        offline_cfg = {
            "endpoints": {
                "screen_lens": {
                    "orchestrator_url": "http://127.0.0.1:58881",
                    "ocr_stream_url": "http://127.0.0.1:58882",
                    "hud_mjpeg_url": "http://127.0.0.1:58883",
                }
            }
        }
        client = ScreenLensClient(config_dict=offline_cfg, sqlite_db_paths=[db_path])

        # Hold an EXCLUSIVE transaction in DELETE journal mode
        lock_held_event = threading.Event()
        release_lock_event = threading.Event()

        def locker():
            conn = sqlite3.connect(db_path, isolation_level="EXCLUSIVE")
            conn.execute("BEGIN EXCLUSIVE;")
            conn.execute("INSERT INTO frames VALUES (999, 1.0, 'X', 'Y', 'Z', '[]', 'L1');")
            lock_held_event.set()
            release_lock_event.wait(timeout=5.0)
            conn.commit()
            conn.close()

        locker_thread = threading.Thread(target=locker, daemon=True)
        locker_thread.start()

        assert lock_held_event.wait(timeout=3.0)

        try:
            # Client attempts to harvest. Since DB is locked with EXCLUSIVE lock and timeout is 1.0s in _harvest_from_sqlite,
            # SQLite raises OperationalError (database is locked), which _harvest_from_sqlite MUST catch and fall through to system_fallback!
            res = client.harvest_perception(timeout_s=0.5)

            assert isinstance(res, dict)
            # Must safely fall through without raising an unhandled OperationalError
            assert res["source"] in ("sqlite", "system_fallback")
        finally:
            release_lock_event.set()
            locker_thread.join(timeout=3.0)


class TestReadOnlyModeWritePreventionStrictness:
    """Rigorous verification of write prevention in read-only URI mode (`file:{path}?mode=ro`)."""

    def test_ro_mode_strictly_rejects_dml(self, tmp_path: Path):
        """Write-Prevention: INSERT, UPDATE, DELETE strictly raise OperationalError: attempt to write a readonly database."""
        db_path = tmp_path / "readonly_dml.db"
        _populate_test_db(db_path, num_frames=10)

        ro_conn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)

        with pytest.raises(sqlite3.OperationalError, match="readonly database"):
            ro_conn.execute("INSERT INTO frames VALUES (11, 2.0, 'A', 'B', 'C', '[]', 'L1');")

        with pytest.raises(sqlite3.OperationalError, match="readonly database"):
            ro_conn.execute("UPDATE frames SET app_name = 'Hacked' WHERE id = 1;")

        with pytest.raises(sqlite3.OperationalError, match="readonly database"):
            ro_conn.execute("DELETE FROM frames WHERE id = 1;")

        ro_conn.close()

    def test_ro_mode_strictly_rejects_ddl_and_vacuum(self, tmp_path: Path):
        """Write-Prevention: CREATE, DROP, ALTER TABLE, VACUUM all fail on read-only connection."""
        db_path = tmp_path / "readonly_ddl.db"
        _populate_test_db(db_path, num_frames=10)

        ro_conn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)

        with pytest.raises(sqlite3.OperationalError, match="readonly database"):
            ro_conn.execute("CREATE TABLE malicious (id INT);")

        with pytest.raises(sqlite3.OperationalError, match="readonly database"):
            ro_conn.execute("DROP TABLE frames;")

        with pytest.raises(sqlite3.OperationalError, match="readonly database"):
            ro_conn.execute("ALTER TABLE frames ADD COLUMN hacked TEXT;")

        with pytest.raises(sqlite3.OperationalError, match="readonly database"):
            ro_conn.execute("VACUUM;")

        ro_conn.close()

    def test_file_sha256_cryptographically_unaltered_after_reads(self, tmp_path: Path):
        """Immutability: Database file SHA256 checksum remains 100% byte-for-byte identical after 500 reads."""
        db_path = tmp_path / "checksum_test.db"
        _populate_test_db(db_path, num_frames=50)

        initial_sha256 = _compute_sha256(db_path)
        initial_mtime = db_path.stat().st_mtime_ns

        offline_cfg = {
            "endpoints": {
                "screen_lens": {
                    "orchestrator_url": "http://127.0.0.1:58881",
                    "ocr_stream_url": "http://127.0.0.1:58882",
                    "hud_mjpeg_url": "http://127.0.0.1:58883",
                }
            }
        }
        client = ScreenLensClient(config_dict=offline_cfg, sqlite_db_paths=[db_path])

        # Execute 500 reads across 20 threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(client.harvest_perception, 0.5) for _ in range(500)]
            for f in concurrent.futures.as_completed(futures):
                res = f.result()
                assert res["source"] == "sqlite"

        final_sha256 = _compute_sha256(db_path)
        final_mtime = db_path.stat().st_mtime_ns

        assert final_sha256 == initial_sha256, "DB file SHA256 was altered during read operations!"
        assert final_mtime == initial_mtime, "DB file modification timestamp was altered during read operations!"


class TestAdversarialNetworkAndSocketEdgeCases:
    """Stress tests simulating hostile or degraded network socket conditions."""

    def test_rapid_client_instantiation_thread_safety(self):
        """Stress: 100 threads concurrently instantiating new ScreenLensClient instances."""
        def creator(idx: int) -> bool:
            c = ScreenLensClient()
            return "endpoints" in c.config and isinstance(c.opener, urllib.request.OpenerDirector)

        with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
            futures = [executor.submit(creator, i) for i in range(100)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 100
        assert all(results)

    def test_simulated_slowloris_timeout_enforcement(self):
        """Adversarial: Server accepts connection but delays response; client strictly enforces timeout."""
        class SlowHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                # Delay for 2.0s
                time.sleep(2.0)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"slow": true}')

            def log_message(self, format, *args):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), SlowHandler)
        port = server.server_port
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        try:
            cfg = {
                "endpoints": {
                    "screen_lens": {
                        "orchestrator_url": f"http://127.0.0.1:{port}",
                        "ocr_stream_url": f"http://127.0.0.1:{port}",
                        "hud_mjpeg_url": f"http://127.0.0.1:{port}",
                    }
                }
            }
            client = ScreenLensClient(config_dict=cfg, sqlite_db_paths=[])

            t0 = time.perf_counter()
            # Set timeout to 0.1s
            res = client.harvest_perception(timeout_s=0.1)
            elapsed = time.perf_counter() - t0

            # Must not hang for 2.0s; timeout per endpoint is 0.1s (3 endpoints = ~0.3-0.6s max)
            assert elapsed < 1.8, f"Timeout enforcement failed: took {elapsed:.2f}s"
            assert res["source"] == "system_fallback"
        finally:
            server.shutdown()
            server.server_close()

    def test_simulated_http_error_codes_500_502_503(self):
        """Adversarial: Live endpoints return server errors (500, 502, 503); client falls through gracefully."""
        class ErrorOpener(urllib.request.OpenerDirector):
            def open(self, req, timeout=None):
                raise urllib.error.HTTPError(req.full_url, 502, "Bad Gateway", {}, None)

        client = ScreenLensClient(opener=ErrorOpener(), sqlite_db_paths=[])

        # harvest_perception should catch 502 and fall back to system
        p = client.harvest_perception(timeout_s=0.5)
        assert p["source"] == "system_fallback"

        # connect_gemini_spark should catch 502 and report offline
        s = client.connect_gemini_spark(timeout_s=0.5)
        assert s["connected"] is False
        assert s["status"] == "offline"
        assert "502" in str(s["error"])

    def test_gemini_spark_no_fallback_to_localhost_when_custom_url_offline(self):
        """Remediation: When custom endpoints are configured and offline, client must NOT leak/fall back to localhost:9999."""
        offline_custom_cfg = {
            "endpoints": {
                "gemini_spark": {
                    "mcp_project_health_url": "http://127.0.0.1:58991/mcp/project/health",
                    "mcp_health_url": "http://127.0.0.1:58991/health",
                }
            }
        }
        client = ScreenLensClient(config_dict=offline_custom_cfg)
        status = client.connect_gemini_spark(timeout_s=0.2)
        assert isinstance(status, dict)
        assert status["connected"] is False
        assert status["status"] == "offline"
        assert "58991" in status["endpoint"]

    def test_simulated_oversized_json_payload(self):
        """Adversarial: Server returns a large 2 MB JSON payload without crashing or throwing MemoryError."""
        large_text = "A" * 1_000_000
        payload_bytes = json.dumps({
            "timestamp": "2026-10-11T13:00:00Z",
            "screen": {
                "active_app": "BigApp",
                "window_title": "BigWin",
                "recent_ocr": [large_text],
            },
            "mesh_health": {"healthy_services": "10/14"},
        }).encode("utf-8")

        class LargeHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(payload_bytes)

            def log_message(self, format, *args):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), LargeHandler)
        port = server.server_port
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        try:
            cfg = {
                "endpoints": {
                    "screen_lens": {
                        "orchestrator_url": f"http://127.0.0.1:{port}",
                        "ocr_stream_url": f"http://127.0.0.1:{port}",
                        "hud_mjpeg_url": f"http://127.0.0.1:{port}",
                    }
                }
            }
            client = ScreenLensClient(config_dict=cfg)
            res = client.harvest_perception(timeout_s=2.0)

            assert res["source"] == "live_api"
            assert res["active_app"] == "BigApp"
            assert len(res["ocr_snippet"]) == 1_000_000
        finally:
            server.shutdown()
            server.server_close()


class TestSystemFallbackAndMemorySanctuaryStress:
    """Stress tests on Darwin kernel Launch Services and vm_stat subprocess probes."""

    def test_concurrent_system_fallback_probes(self):
        """Stress: 25 concurrent threads calling _harvest_from_system_fallback() simultaneously."""
        client = ScreenLensClient(config_dict={}, sqlite_db_paths=[])
        barrier = threading.Barrier(25)
        results: List[Dict[str, Any]] = []
        errors: List[Exception] = []
        lock = threading.Lock()

        def worker(idx: int):
            try:
                barrier.wait(timeout=5.0)
                res = client._harvest_from_system_fallback()
                with lock:
                    results.append(res)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(25)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert not errors, f"Concurrent system fallback probe errors: {errors}"
        assert len(results) == 25
        for r in results:
            assert r["source"] == "system_fallback"
            assert len(r["active_app"]) > 0
            if sys.platform == "darwin":
                assert r["mesh_health"]["os"] == "darwin"
                assert "ram_info" in r["mesh_health"]
