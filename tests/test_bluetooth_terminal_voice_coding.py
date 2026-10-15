#!/usr/bin/env python3
"""
tests/test_bluetooth_terminal_voice_coding.py
================================================================================
Comprehensive verification suite for Hands-Free Voice Coding in the
Lauburu Bluetooth Terminal IDE and Mesh Transport Ecosystem.

Governed by:
- Rule #0 (Zero-Mock): Authentic local execution, real exit codes & checksums.
- Rule #1 (Tri-Proof): Actuation, line-by-line inspection, live telemetry.
- Rule #3 (Host Sanctuary): Memory headroom verified.
- Rule #8 (Local AI Hierarchy): prima.cpp (:8082) Master Local Orchestrator.
================================================================================
"""

import os
import sys
import json
import time
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

WORKSPACE_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(WORKSPACE_ROOT / "01_apps/bluetooth_terminal_ide/backend"))
sys.path.insert(0, str(WORKSPACE_ROOT / "06_scripts_and_tooling"))

from server import app, process_voice_directive, VoiceDirectiveRequest
from bluetooth_serial_terminal_daemon import execute_voice_coding_directive

client = TestClient(app)

LORA_DATASET = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl")


def test_voice_system_status():
    """Verify GET /api/voice/status reports active Whisper Small STT and Sovereign AI."""
    resp = client.get("/api/voice/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ONLINE"
    assert "whisper_small" in data
    assert data["whisper_small"]["present"] is True
    assert data["whisper_small"]["elo"] >= 1800.0
    assert "sovereign_master_orchestrator" in data


def test_voice_directive_git_status():
    """Verify spoken git status directive executes authentic git query and spoken summary."""
    resp = client.post(
        "/api/voice/directive",
        json={"directive": "check git status", "caller": "pytest_voice_test"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["action_executed"] == "QUERY_GIT_STATUS"
    assert "spoken_summary" in data
    assert len(data["spoken_summary"]) > 0
    assert "output" in data
    assert data["lora_logged"] is True


def test_voice_directive_git_diff():
    """Verify spoken diff inspection directive returns git diff and concise voice summary."""
    resp = client.post(
        "/api/voice/directive",
        json={"directive": "explain diff", "caller": "pytest_voice_test"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["action_executed"] == "EXPLAIN_GIT_DIFF"
    assert "spoken_summary" in data
    assert "diff" in data["spoken_summary"].lower() or "clean" in data["spoken_summary"].lower()


def test_voice_directive_host_sanctuary_audit():
    """Verify spoken audit directive returns genuine RAM headroom and Host Sanctuary status."""
    resp = client.post(
        "/api/voice/directive",
        json={"directive": "audit host memory", "caller": "pytest_voice_test"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["action_executed"] == "HOST_SANCTUARY_AUDIT"
    assert "Host Sanctuary" in data["spoken_summary"]
    assert "available RAM" in data["spoken_summary"] or "gigabytes" in data["spoken_summary"]


def test_voice_directive_internal_macros():
    """Verify internal terminal macros are accessible through hands-free speech."""
    for macro in ["models", "mesh"]:
        resp = client.post(
            "/api/voice/directive",
            json={"directive": macro, "caller": "pytest_macro_test"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert len(data["spoken_summary"]) > 0


def test_voice_directive_shell_execution():
    """Verify shell commands spoken with 'run' or known commands execute with real exit codes."""
    resp = client.post(
        "/api/voice/directive",
        json={"directive": "run echo 'Hands-Free Voice Active'", "caller": "pytest_shell_test"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["action_executed"] == "EXECUTE_SHELL_COMMAND"
    assert data["exit_code"] == 0
    assert "Hands-Free Voice Active" in data["output"]
    assert "completed successfully" in data["spoken_summary"]


def test_voice_directive_ai_pair_programming():
    """Verify natural code directive routes to Qwen 3.8 Max with concise spoken summary."""
    resp = client.post(
        "/api/voice/directive",
        json={"directive": "write a python function to compute moving average", "caller": "pytest_ai_test"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["action_executed"] == "AI_PAIR_PROGRAMMING_DIRECTIVE"
    assert len(data["spoken_summary"]) > 0
    assert len(data["spoken_summary"]) <= 220  # Concise for earbud/vehicle listening
    assert data["lora_logged"] is True


def test_terminal_cli_voice_macro():
    """Verify 'voice <directive>' and 'v <directive>' in terminal run endpoint."""
    resp = client.post(
        "/api/terminal/run",
        json={"command": "voice audit"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "[🎙️ Voice Directive Executed" in data["output"]
    assert "Spoken:" in data["output"]


def test_lora_dataset_entry_persisted():
    """Verify that voice interactions are authentically written to continuous_lora_dataset.jsonl."""
    assert LORA_DATASET.exists()
    with open(LORA_DATASET, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) > 0
    has_voice_entry = any("Voice Directive" in line for line in lines[-50:])
    assert has_voice_entry is True


def test_bluetooth_serial_voice_helper():
    """Verify bluetooth serial daemon helper function fallback handling."""
    res = execute_voice_coding_directive("check git status")
    assert "status" in res
    assert "spoken_summary" in res
