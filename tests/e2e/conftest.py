#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pytest fixtures and test harnesses for Decentralized Syncthing Dependency,
Server & Screen Lens Replication Cluster E2E tests (Tiers 1 - 4).
"""

import os
import sys
import shutil
import sqlite3
import tempfile
import threading
from pathlib import Path
from http.server import HTTPServer
import pytest

TESTS_E2E_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_E2E_DIR.parent.parent

for p in [
    str(PROJECT_ROOT),
    str(TESTS_E2E_DIR),
    str(PROJECT_ROOT / "00_core_infrastructure"),
    str(PROJECT_ROOT / "06_scripts_and_tooling"),
    str(PROJECT_ROOT / "06_scripts_and_tooling" / "mesh"),
    str(PROJECT_ROOT / "06_scripts_and_tooling" / "network"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

from syncthing_lens_helpers import (
    find_free_port,
    MockSyncthingRequestHandler,
    MockPrimaryEndpointHandler,
    CANONICAL_DEVICE_MATRIX,
    CANONICAL_SHARED_FOLDERS,
    CANONICAL_STIGNORE_PATTERNS,
)


@pytest.fixture(scope="function")
def syncthing_mock_server():
    """
    Spins up an ephemeral HTTP server serving Syncthing REST API endpoints.
    Cleans up state on teardown.
    """
    port = find_free_port()
    # Reset handler state
    MockSyncthingRequestHandler.registered_devices = [
        {"deviceID": CANONICAL_DEVICE_MATRIX["L6"]["device_id"], "name": "Pixel-10-Pro-XL", "addresses": ["dynamic"]},
        {"deviceID": CANONICAL_DEVICE_MATRIX["L5"]["device_id"], "name": "MacBook-Air-L5", "addresses": ["dynamic"]},
    ]
    MockSyncthingRequestHandler.configured_folders = [
        {
            "id": "lauburu-obsidian",
            "label": "obsidian_vault",
            "path": "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault",
            "type": "sendreceive",
            "devices": [{"deviceID": CANONICAL_DEVICE_MATRIX["L1"]["device_id"]}],
        }
    ]
    MockSyncthingRequestHandler.folder_completion = {}
    MockSyncthingRequestHandler.folder_status = {}

    server = HTTPServer(("127.0.0.1", port), MockSyncthingRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    ctx = {
        "port": port,
        "url": f"http://127.0.0.1:{port}",
        "api_key": MockSyncthingRequestHandler.api_key,
        "handler": MockSyncthingRequestHandler,
    }

    yield ctx

    server.shutdown()
    server.server_close()


@pytest.fixture(scope="function")
def primary_mock_server():
    """
    Spins up an ephemeral HTTP server simulating primary endpoints (SeaweedFS, Orchestrator, Port 4000).
    """
    port = find_free_port()
    MockPrimaryEndpointHandler.healthy = True
    MockPrimaryEndpointHandler.delay = 0.0

    server = HTTPServer(("127.0.0.1", port), MockPrimaryEndpointHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    ctx = {
        "port": port,
        "url": f"http://127.0.0.1:{port}",
        "handler": MockPrimaryEndpointHandler,
    }

    yield ctx

    server.shutdown()
    server.server_close()


@pytest.fixture(scope="function")
def temp_monorepo_env():
    """
    Creates an isolated temporary monorepo directory tree with sample folders,
    test files, binary caches (.venv, node_modules, target, LevelDB), and marker states.
    """
    temp_dir = tempfile.mkdtemp(prefix="lauburu_e2e_test_")

    # Structure
    c_infra = Path(temp_dir) / "00_core_infrastructure"
    s_tooling = Path(temp_dir) / "06_scripts_and_tooling"
    o_vault = Path(temp_dir) / "obsidian_vault"
    d_mesh = Path(temp_dir) / "data" / "mesh"

    c_infra.mkdir(parents=True)
    s_tooling.mkdir(parents=True)
    o_vault.mkdir(parents=True)
    d_mesh.mkdir(parents=True)

    # Bloat directories that must be excluded by .stignore
    (c_infra / "self_healing_hub" / ".venv" / "bin").mkdir(parents=True)
    (c_infra / "self_healing_hub" / ".venv" / "bin" / "python").write_text("#!/bin/sh\n")
    (c_infra / "cloudflare_worker" / "node_modules" / "esbuild").mkdir(parents=True)
    (c_infra / "cloudflare_worker" / "node_modules" / "esbuild" / "package.json").write_text("{}")
    (c_infra / "filerldb2").mkdir(parents=True)
    (c_infra / "filerldb2" / "CURRENT").write_text("MANIFEST-000001\n")
    (c_infra / "filerldb2" / "LOCK").write_text("")

    (s_tooling / "network" / "rust_bonding_engine" / "target" / "debug").mkdir(parents=True)
    (s_tooling / "network" / "rust_bonding_engine" / "target" / "debug" / "bonding_engine").write_bytes(b"\x7fELF")
    (s_tooling / "__pycache__").mkdir(parents=True)
    (s_tooling / "__pycache__" / "test.cpython-312.pyc").write_bytes(b"\x00\x00\x00\x00")

    # Clean source files
    (c_infra / "self_healing_hub.py").write_text("# Self Healing Hub Core\n")
    (s_tooling / "speculative_cli_data_engine.py").write_text("# CLI Engine\n")
    (o_vault / "Index.md").write_text("# Master Knowledge Vault\n[[Index]]\n")
    (d_mesh / "syncthing_mesh_config.json").write_text('{"mesh": "lauburu"}\n')

    ctx = {
        "root": Path(temp_dir),
        "00_core_infrastructure": c_infra,
        "06_scripts_and_tooling": s_tooling,
        "obsidian_vault": o_vault,
        "data_mesh": d_mesh,
    }

    yield ctx

    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def sample_sqlite_dbs():
    """
    Creates temporary SQLite databases initialized with Screen Lens and Companion schemas.
    """
    temp_dir = tempfile.mkdtemp(prefix="lauburu_sqlite_test_")
    lens_db = Path(temp_dir) / "screen_lens.sqlite"
    companion_db = Path(temp_dir) / "screen_life_companion.sqlite"

    # Initialize screen_lens.sqlite
    conn = sqlite3.connect(lens_db)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE captures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            unix_ts_ms INTEGER NOT NULL,
            display_id INTEGER DEFAULT 1,
            active_app_name TEXT,
            active_window_title TEXT,
            raw_text_summary TEXT,
            change_hash TEXT
        )
    """
    )
    cur.execute(
        """
        INSERT INTO captures (timestamp, unix_ts_ms, active_app_name, active_window_title, raw_text_summary, change_hash)
        VALUES ('2026-09-30T07:00:00Z', 1790751600000, 'Terminal', 'zsh - pytest', 'running e2e tests', 'abc123hash')
    """
    )
    conn.commit()
    conn.close()

    # Initialize companion
    conn2 = sqlite3.connect(companion_db)
    cur2 = conn2.cursor()
    cur2.execute(
        """
        CREATE TABLE life_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            importance INTEGER DEFAULT 1,
            app_name TEXT,
            completed INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """
    )
    cur2.execute(
        """
        INSERT INTO life_memories (category, content, importance, app_name, completed, created_at)
        VALUES ('work', 'Complete E2E test suite for Syncthing and Screen Lens', 5, 'Terminal', 0, '2026-09-30T07:00:00Z')
    """
    )
    conn2.commit()
    conn2.close()

    ctx = {
        "dir": Path(temp_dir),
        "screen_lens_db": lens_db,
        "companion_db": companion_db,
    }

    yield ctx

    shutil.rmtree(temp_dir, ignore_errors=True)
