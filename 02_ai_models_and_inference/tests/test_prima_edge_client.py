# -*- coding: utf-8 -*-
"""
Unit & Integration Test Suite for prima.cpp Edge Client & 3B MoE Chat Runtime
=============================================================================
Subsystem: 02_ai_models_and_inference / tests / test_prima_edge_client.py
Lauburu Mesh Ecosystem — 2026
"""

import os
import sys
import time
import pytest
from pathlib import Path

# Add subsystem root to sys.path
_curr_dir = Path(__file__).resolve().parent
_subsystem_root = _curr_dir.parent
if str(_subsystem_root) not in sys.path:
    sys.path.insert(0, str(_subsystem_root))

from prima_edge_client import PrimaEdgeClient, EdgeClientConfig, EdgeInferenceResult


def test_edge_device_ram_envelope_gate_9():
    """
    Verifies that the on-device 3B MoE model and runtime strictly satisfy Gate 9:
    Total VRAM/RAM <= 1,500 MB for customer mobile devices.
    """
    client = PrimaEdgeClient()
    envelope = client.verify_customer_device_envelope()

    assert envelope["gate_9_compliant"] is True
    assert envelope["total_edge_ram_mb"] <= 1500.0
    assert envelope["total_edge_ram_mb"] == 1300.0  # 1180 MB weights + 120 MB KV
    assert envelope["margin_mb"] >= 200.0
    assert envelope["active_parameters"] == "0.8B"
    assert envelope["offline_autonomous"] is True


def test_offline_standalone_mode():
    """
    Verifies 100% offline standalone conversational generation when off-grid.
    Zero WAN egress, 0ms network latency.
    """
    client = PrimaEdgeClient()
    result = client.generate_chat("Summarize the meeting notes.", force_local=True)

    assert result.mode == "OFFLINE_STANDALONE"
    assert result.mesh_connected is False
    assert result.tokens_generated > 0
    assert result.tokens_per_second >= 85.0
    assert result.acceptance_rate == 1.0
    assert result.cluster_speedup_multiplier == 1.0
    assert result.memory_rss_mb <= 1500.0
    assert "Local 3B MoE Chat" in result.response_text


def test_mesh_probe_handshake_timeout_invariant():
    """
    Verifies the 150ms handshake timeout invariant against invalid/hung endpoints.
    """
    # Test with non-existent local port
    cfg = EdgeClientConfig(mesh_daemon_url="http://127.0.0.1:59999", handshake_timeout_ms=100.0)
    client = PrimaEdgeClient(cfg)

    start = time.perf_counter()
    is_online, rtt_ms, info = client.probe_mesh_daemon(timeout_ms=100.0)
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    assert is_online is False
    # Must fail fast without blocking
    assert elapsed_ms < 500.0


def test_speculative_ring_coupling_or_clean_fallback():
    """
    Verifies automatic mode resolution:
    - If Port 8082 PRP daemon is active: SPECULATIVE_RING_COUPLED with speedup >= 2.0x
    - If Port 8082 is down: clean graceful degradation to OFFLINE_STANDALONE with 0 errors.
    """
    client = PrimaEdgeClient()
    result = client.generate_chat("Decompile the binary and audit the AST.")

    assert result.mode in ("SPECULATIVE_RING_COUPLED", "OFFLINE_STANDALONE")
    assert result.tokens_generated > 0
    assert result.tokens_per_second > 0

    if result.mode == "SPECULATIVE_RING_COUPLED":
        assert result.mesh_connected is True
        assert result.draft_tokens_count == 5
        assert result.accepted_tokens_count >= 1
        assert result.cluster_speedup_multiplier >= 2.0
        assert "Speculative 80B Mesh Verified" in result.response_text
    else:
        assert result.mesh_connected is False
        assert result.cluster_speedup_multiplier == 1.0


def test_telemetry_reporting_and_battery_governance():
    """
    Verifies telemetry metrics and estimated thermal battery draw (<1.5W active).
    """
    client = PrimaEdgeClient()
    client.generate_chat("First message", force_local=True)
    client.generate_chat("Second message", force_local=True)

    telemetry = client.get_telemetry()
    assert telemetry["total_sessions"] == 2
    assert telemetry["total_local_tokens"] >= 32
    assert telemetry["device_envelope"]["gate_9_compliant"] is True
    assert client.config.power_watts_active < 1.5
