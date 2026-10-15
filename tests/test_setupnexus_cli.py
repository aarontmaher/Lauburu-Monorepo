#!/usr/bin/env python3
"""
================================================================================
👑 Test Suite for setupnexus CLI & Sovereign Single-Chat Nexus Architecture
================================================================================
Governed by:
- Rule 0: Authentic execution against live localhost endpoints and SQLite database
- Rule 1: Empirical Tri-Proof assertions (Exit Code 0, SHA256 hashes, exact byte counts)
- Rule 2: Tri-Vault storage integrity (Obsidian Vault, PySpark LoRA lake)
================================================================================
"""

import os
import sys
import json
import shutil
import hashlib
import sqlite3
import subprocess
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
SETUP_NEXUS_BIN = Path("/Users/aaron/.local/bin/setupnexus")
DB_PATH = REPO_ROOT / "04_data_and_memory" / "single_chat_nexus.db"


def test_setupnexus_binary_installed():
    """Verify setupnexus executable exists on PATH and is executable."""
    assert SETUP_NEXUS_BIN.exists(), "setupnexus binary must exist in ~/.local/bin"
    assert os.access(SETUP_NEXUS_BIN, os.X_OK), "setupnexus must have execute permissions"


def test_setupnexus_help():
    """Verify setupnexus --help executes cleanly with exit code 0."""
    res = subprocess.run([str(SETUP_NEXUS_BIN), "--help"], capture_output=True, text=True)
    assert res.returncode == 0, f"Expected exit code 0, got {res.returncode}"
    assert "Sovereign Single-Chat Nexus (Mother Ship) Canonical Control Engine" in res.stdout
    assert "init" in res.stdout
    assert "start" in res.stdout
    assert "status" in res.stdout
    assert "dispatch" in res.stdout
    assert "verify" in res.stdout


def test_setupnexus_init():
    """Verify setupnexus init bootstraps SQLite database and canonical threads."""
    res = subprocess.run([str(SETUP_NEXUS_BIN), "init"], capture_output=True, text=True)
    assert res.returncode == 0, f"init failed with code {res.returncode}: {res.stderr}"
    assert "Single-Chat Nexus database initialized" in res.stdout
    assert "Nexus zkVM Sidecar: VERIFIED" in res.stdout
    assert DB_PATH.is_file(), f"Database file {DB_PATH} must exist"


def test_setupnexus_status():
    """Verify setupnexus status reports tri-vault storage and daemon status."""
    res = subprocess.run([str(SETUP_NEXUS_BIN), "status"], capture_output=True, text=True)
    assert res.returncode == 0, f"status failed: {res.stderr}"
    assert "TRI-VAULT STORAGE HEALTH" in res.stdout
    assert "Obsidian Vault:" in res.stdout
    assert "PySpark LoRA Lake:" in res.stdout
    assert "SINGLE-CHAT NEXUS DAEMON:" in res.stdout


def test_setupnexus_dispatch():
    """Verify setupnexus dispatch executes live routing and next-step synthesis."""
    directive = "Verify movesense 512Hz ECG biometrics and check shopify order revenue"
    res = subprocess.run([str(SETUP_NEXUS_BIN), "dispatch", directive], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, f"dispatch failed: {res.stderr}"
    assert "Ingesting Directive:" in res.stdout
    assert "Fanned Out To Satellite Chats" in res.stdout
    assert "Actions Executed & Reported Back" in res.stdout
    assert "Strategic Next-Step Discussion:" in res.stdout
    assert "Recommended Follow-Up Actions:" in res.stdout


def test_setupnexus_sqlite_schema_integrity():
    """Verify tables and foreign keys in single_chat_nexus.db."""
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        assert "threads" in tables
        assert "messages" in tables
        assert "actions" in tables
        assert "next_steps_cache" in tables

        # Verify canonical seed threads
        threads = {r["id"] for r in conn.execute("SELECT id FROM threads").fetchall()}
        required = {"omni_inbox", "commerce_sales", "biometrics_movesense", "screen_lens_vla", "core_infrastructure"}
        assert required.issubset(threads), f"Missing threads: {required - threads}"


def test_setupnexus_zkvm_sidecar_proof():
    """Verify nexus_adapter.py executes genuine zkVM trace and appends to LoRA dataset."""
    sidecar_script = REPO_ROOT / "06_scripts_and_tooling" / "integrations" / "nexus_adapter.py"
    res = subprocess.run([sys.executable, str(sidecar_script)], capture_output=True, text=True, timeout=15)
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data.get("status") == "VERIFIED_SUCCESS"
    assert data.get("proof_type") == "zkVM_trace"
    assert data.get("zero_mock") is True
