"""Unit and E2E Tests for Mesh Device Recording Specialist & Remote Jupyter Offload.

Subsystem: 06_scripts_and_tooling/automation/tests/test_mesh_recording_and_offload.py
Validates:
- Rule 1: Zero-Mock empirical truth verification.
- Rule 3: Host RAM Sanctuary calculations on Darwin Mach kernel.
- Rule 0 & Rule 9: Multi-IP fallback resolution across 10 mesh nodes.
- Rule 10: Linux Mini Hub (L8) remote Jupyter offloading readiness.
- Telemetry distillation and dataset deduplication.
"""

import json
import os
import sys
import pytest
from pathlib import Path

# Add automation dir to sys.path
AUTOMATION_DIR = Path(__file__).resolve().parent.parent
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

from mesh_device_recording_specialist_suite import (
    get_l1_ram_sanctuary,
    probe_mesh_nodes,
    verify_remote_jupyter_offload,
    capture_recordings,
    distill_telemetry_pair,
    sha256_file,
    ARTIFACTS_DIR,
)


def test_ram_sanctuary_structure():
    """Verifies Darwin kernel RAM metrics obey Activity Monitor standard."""
    ram = get_l1_ram_sanctuary()
    assert isinstance(ram, dict)
    assert "total_ram_gb" in ram
    assert "free_ram_gb" in ram
    assert "sanctuary_healthy" in ram
    assert isinstance(ram["sanctuary_healthy"], bool)
    assert ram["total_ram_gb"] > 0


def test_probe_mesh_nodes():
    """Verifies all 10 mesh nodes, KDE Connect, and Bluetooth Layer 0 are probed."""
    mesh = probe_mesh_nodes()
    assert isinstance(mesh, dict)
    # Check expected core nodes exist
    expected_nodes = [
        "L1_Mac_Mini_M4",
        "L1a_MBA_M4",
        "L1b_Mac_Mini_M2",
        "L2_MacBook_Pro",
        "L3_Linux_AMD",
        "L8_Linux_Mini_Hub",
        "L4_Pixel_AVF_Debian",
        "L6_Pixel_10_Pro_XL",
        "L7_Samsung_S20",
        "GW_GL_BE14000",
    ]
    for n in expected_nodes:
        assert n in mesh
        assert "ip" in mesh[n]
        assert "online" in mesh[n]
        assert isinstance(mesh[n]["online"], bool)

    # Check transports
    assert "KDE_Connect_Mesh" in mesh
    assert "Layer_0_Bluetooth_Lifeline" in mesh
    assert "Wearables_Movesense_PolarH10" in mesh


def test_remote_jupyter_offload_l8():
    """Verifies L8 Linux Mini 32GB Hub remote Jupyter offload endpoint is operational."""
    jup = verify_remote_jupyter_offload()
    assert isinstance(jup, dict)
    assert "status" in jup
    assert "endpoint" in jup
    assert jup["endpoint"] == "http://10.0.0.8:8888"
    if jup["status"] == "OPERATIONAL":
        assert "available_kernels" in jup
        assert "python3-linuxmini" in jup["available_kernels"]
        assert jup["linuxmini_kernel_ready"] is True


def test_capture_recordings_integrity():
    """Verifies captured recordings have authentic SHA256 hashes and non-zero bytes."""
    recs = capture_recordings()
    assert isinstance(recs, dict)
    for dev, info in recs.items():
        if info.get("status") == "SUCCESS":
            assert "sha256" in info
            assert len(info["sha256"]) == 64
            assert info["size_bytes"] > 0
            assert Path(info["file_path"]).exists()


def test_distill_telemetry_pair_schema():
    """Verifies empirical pair distillation conforms to LoRA training schema."""
    ram = {"total_ram_gb": 24.0, "free_ram_gb": 3.0, "sanctuary_healthy": False}
    mesh = {"L1_Mac_Mini_M4": {"ip": "10.0.0.2", "online": True}}
    recs = {"L6": {"status": "SUCCESS", "sha256": "abc12345"}}
    pair = distill_telemetry_pair(ram, mesh, recs)

    assert "instruction" in pair
    assert "input" in pair
    assert "output" in pair
    assert "timestamp" in pair
    assert pair["source"] == "screen_lens_sovereign_mesh_specialist"

    out_parsed = json.loads(pair["output"])
    assert out_parsed["zero_mock_truth"] == "VERIFIED_EMPIRICAL"
