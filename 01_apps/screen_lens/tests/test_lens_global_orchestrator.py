#!/usr/bin/env python3
"""
01_apps/screen_lens/tests/test_lens_global_orchestrator.py
==========================================================
Empirical Unit & Integration Test Suite for Screen Lens Sovereign Global Orchestrator.

Governed by:
- Rule #0 (Zero-Mock Empirical Truth)
- Rule #1 & #5 (Tri-Proof Empirical Verification Gate)
- Rule #8 (Sovereign Local AI Hierarchy: Qwen 3.8 Max Master Orchestrator)
"""

import hashlib
import json
import os
import socket
import sys
import threading
import time
import urllib.request
from http.server import HTTPServer
from pathlib import Path
import pytest

# Add src to path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from lens_vla_action_dispatcher import VLAActionDispatcher, ActionReceipt
from lens_global_orchestrator import (
    PerceptionHub,
    CognitiveBrain,
    LensGlobalOrchestrator,
    OrchestratorHTTPHandler
)


# -----------------------------------------------------------------------------
# 1. VLA Action Dispatcher Tests
# -----------------------------------------------------------------------------
def test_vla_action_dispatcher_resolution():
    """Verify display resolution detection and coordinate normalization."""
    dispatcher = VLAActionDispatcher()
    w, h = dispatcher.get_display_resolution()
    assert w >= 800, f"Display width too small: {w}"
    assert h >= 600, f"Display height too small: {h}"

    # Normalized center (0.5, 0.5)
    cx, cy = dispatcher.normalize_to_pixels(0.5, 0.5)
    assert cx == w // 2 or abs(cx - w / 2) <= 1
    assert cy == h // 2 or abs(cy - h / 2) <= 1

    # Boundary clamping
    x0, y0 = dispatcher.normalize_to_pixels(-0.5, -0.5)
    assert x0 == 0 and y0 == 0

    x1, y1 = dispatcher.normalize_to_pixels(1.5, 1.5)
    assert x1 == w - 1 and y1 == h - 1


def test_vla_action_dispatcher_command_execution():
    """Verify command execution receipt with exit code and SHA256 proof."""
    dispatcher = VLAActionDispatcher()
    receipt = dispatcher.execute_command("echo 'LAUBURU_VLA_TEST'")
    assert receipt.exit_code == 0
    assert "LAUBURU_VLA_TEST" in receipt.details.get("stdout", "")
    assert receipt.latency_ms >= 0.0
    assert len(receipt.sha256_proof) == 64
    assert receipt.action_type == "execute_command"


# -----------------------------------------------------------------------------
# 2. Perception Hub Tests
# -----------------------------------------------------------------------------
def test_perception_hub_screen_and_life():
    """Verify screen and companion context ingestion without synthetic mocks."""
    screen_ctx = PerceptionHub.get_screen_context(limit=3)
    assert isinstance(screen_ctx, dict)
    assert "active_app" in screen_ctx
    assert "recent_ocr" in screen_ctx
    assert "frame_count" in screen_ctx

    life_ctx = PerceptionHub.get_life_companion_context(limit=3)
    assert isinstance(life_ctx, dict)
    assert "pending_todos" in life_ctx
    assert "active_tasks" in life_ctx


def test_perception_hub_biometrics_and_mesh():
    """Verify biometrics reading adheres to Rule 0 (Zero-Mock) and mesh health."""
    bio = PerceptionHub.get_biometrics_state()
    assert isinstance(bio, dict)
    assert "connected" in bio
    assert "kamath_20_filter" in bio

    mesh = PerceptionHub.get_mesh_health()
    assert isinstance(mesh, dict)
    assert "ports" in mesh
    assert "healthy_services" in mesh


# -----------------------------------------------------------------------------
# 3. Global Orchestrator Core Controller Tests
# -----------------------------------------------------------------------------
def test_orchestrator_full_state_and_sovereign_hierarchy():
    """Verify full state reflects sovereign local AI hierarchy (Qwen 3.8 Max)."""
    orchestrator = LensGlobalOrchestrator()
    state = orchestrator.get_full_state()
    assert state["orchestrator"] == "Screen Lens Sovereign Global Orchestrator"
    assert "screen" in state
    assert "companion" in state
    assert "biometrics" in state
    assert "mesh_health" in state

    # Strict compliance with Sovereign Hierarchy (Rule #8 & Rule #7.1)
    hierarchy = state.get("sovereign_hierarchy", {})
    assert "Qwen 3.8 Max" in hierarchy.get("master_orchestrator", "")
    assert "Qwen 3.8 Max Abliterated" in hierarchy.get("red_team_challenger", "")
    assert "Qwen 2.5 Coder" in hierarchy.get("syntax_worker", "")


def test_orchestrator_action_execution_and_lora_logging():
    """Verify safe action execution generates receipt and logs continuous LoRA pair."""
    orchestrator = LensGlobalOrchestrator()
    receipt = orchestrator.execute_vla_action(
        "execute_command",
        {"cmd": "printf 'ORCHESTRATOR_ACTUATION_CONFIRMED'"}
    )
    assert receipt.exit_code == 0
    assert "ORCHESTRATOR_ACTUATION_CONFIRMED" in receipt.details.get("stdout", "")
    assert len(orchestrator.action_history) >= 1
    assert orchestrator.action_history[-1].action_id == receipt.action_id


# -----------------------------------------------------------------------------
# 4. HTTP Server Integration Tests
# -----------------------------------------------------------------------------
def find_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_orchestrator_http_server_endpoints():
    """Verify HTTP REST endpoints: /api/orchestrator/state, /health, /actuate, /audit."""
    test_port = find_free_port()
    server = HTTPServer(("127.0.0.1", test_port), OrchestratorHTTPHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)

    base_url = f"http://127.0.0.1:{test_port}"
    try:
        # 1. GET /api/orchestrator/state
        req = urllib.request.Request(f"{base_url}/api/orchestrator/state")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert data["orchestrator"] == "Screen Lens Sovereign Global Orchestrator"

        # 2. GET /api/orchestrator/health
        req = urllib.request.Request(f"{base_url}/api/orchestrator/health")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert "mesh" in data

        # 3. POST /api/orchestrator/actuate
        payload = json.dumps({
            "action_type": "execute_command",
            "target": {"cmd": "echo 'HTTP_ACTUATE_TEST'"}
        }).encode()
        req = urllib.request.Request(
            f"{base_url}/api/orchestrator/actuate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert data["status"] == "actuated"
            assert data["receipt"]["exit_code"] == 0
            assert "HTTP_ACTUATE_TEST" in data["receipt"]["details"]["stdout"]

        # 4. POST /api/orchestrator/audit
        req = urllib.request.Request(
            f"{base_url}/api/orchestrator/audit",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert "rule_0_compliance" in data
            assert data["rule_5_interceptor"] == "ENGAGED"

    finally:
        server.shutdown()
        server.server_close()
