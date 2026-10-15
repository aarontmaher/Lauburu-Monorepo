#!/usr/bin/env python3
"""
test_omni_serial_and_layered_self_healer.py
Unit tests for OmniSerialTerminalController and LayeredMeshCascadingSelfHealer.
"""

import sys
from pathlib import Path

# Add core infrastructure to path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "00_core_infrastructure"))

from omni_serial_terminal_and_layered_self_healer import (
    OmniSerialTerminalController,
    LayeredMeshCascadingSelfHealer,
    MESH_LAYERS,
    TRANSPORT_CASCADE_LADDER
)


def test_omni_serial_terminal_lifecycle():
    controller = OmniSerialTerminalController(buffer_size=1024)
    sess = controller.open_terminal_session("sess_unit_01", "L1", 115200)
    assert sess["session_id"] == "sess_unit_01"
    assert sess["status"] == "OPEN"
    assert sess["baud_rate"] == 115200

    # Write data
    payload = b"\x1b[32mHello Lauburu\x1b[0m\n"
    written = controller.write_stream("sess_unit_01", payload)
    assert written == len(payload)

    # Read tail
    tail = controller.read_tail(256)
    assert b"Hello Lauburu" in tail

    # Close session
    controller.close_terminal_session("sess_unit_01")
    assert controller.active_sessions["sess_unit_01"]["status"] == "CLOSED"


def test_ring_buffer_wraparound():
    controller = OmniSerialTerminalController(buffer_size=64)
    controller.open_terminal_session("sess_wrap", "L2", 9600)

    # Write 40 bytes
    controller.write_stream("sess_wrap", b"A" * 40)
    # Write another 40 bytes (triggers circular wraparound)
    controller.write_stream("sess_wrap", b"B" * 40)

    tail = controller.read_tail(64)
    assert len(tail) == 64
    assert tail.endswith(b"B" * 40)
    assert tail.startswith(b"A" * 24)


def test_cascading_self_healer_stability_ranking():
    healer = LayeredMeshCascadingSelfHealer()
    
    # Degrade L3 with failures
    for _ in range(3):
        healer.record_probe("L3", success=False, latency_ms=180.0)
    
    status = healer.layer_health["L3"]
    assert status["status"] in ["DEGRADED", "FAILED"]
    assert status["stability_score"] < 0.5

    # Identify next most stable layer (should be L1, L2, or L5 based on rank & health)
    next_layer = healer.find_next_most_stable_layer("L3")
    assert next_layer in ["L1", "L2", "L5"]
    assert next_layer != "L3"


def test_trigger_self_healing_reflex():
    healer = LayeredMeshCascadingSelfHealer()

    # Trigger reflex on L6 (Android)
    record = healer.trigger_self_healing_reflex("L6", "ADB_HEARTBEAT_TIMEOUT")
    assert record["recovery_verified"] is True
    assert record["effective_rate"] == 1.0
    assert "ADB" in record["healing_action"] or "CASCADE" in record["healing_action"]
    assert healer.layer_health["L6"]["status"] == "HEALED"

    # Verify history
    matrix = healer.get_layer_matrix_status()
    assert matrix["total_heal_events"] >= 1
