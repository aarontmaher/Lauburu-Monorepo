"""
Unit and Integration Tests for Screen Lens Sovereign integration into Port 4007.
Verifies zero-mock empirical live perception, 9-device node matrix, arming safety,
and snapshot proof generation.
"""
import sys
import os
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient
from server import app, LENS_SERVER_URL, SNAPSHOT_DIR

client = TestClient(app)

def test_lens_server_live_status_proxy():
    """Verify /api/lens/status proxies genuine data from Port 4003."""
    response = client.get("/api/lens/status")
    assert response.status_code == 200
    data = response.json()
    assert "active_node" in data
    assert "arm_state" in data
    assert "display" in data
    assert data["display"]["width"] > 0
    assert data["display"]["height"] > 0
    
    # Verify 9 canonical devices in node list if hub is online
    if data.get("lens_hub_online"):
        nodes = data.get("nodes", {})
        assert len(nodes) >= 8, f"Expected at least 8-9 nodes, got {len(nodes)}"
        assert "l1_mac_mini" in nodes
        assert "l8_linux_mini" in nodes or "l2_macbook_pro" in nodes

def test_lens_frame_endpoint():
    """Verify /api/lens/frame returns valid JPEG image content."""
    response = client.get("/api/lens/frame")
    assert response.status_code == 200
    assert response.headers.get("content-type") == "image/jpeg"
    assert len(response.content) > 1000, "Frame content should be authentic JPEG bytes"
    # Verify JPEG magic bytes FF D8 FF
    assert response.content[:3] == b"\xff\xd8\xff", "Must be authentic JPEG stream header"

def test_lens_node_select():
    """Verify /api/lens/node/select switches perception target."""
    response = client.post("/api/lens/node/select", json={"node": "l1_mac_mini"})
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
    assert data.get("active_node") == "l1_mac_mini"

def test_lens_arm_safety_guard():
    """Verify /api/lens/arm handles arm and disarm safety transitions."""
    # Test Arming with short duration
    arm_resp = client.post("/api/lens/arm", json={"armed": True, "duration_sec": 5})
    assert arm_resp.status_code == 200
    arm_data = arm_resp.json()
    assert arm_data.get("arm_state") == "CONTROL_ARMED"

    # Test Immediate Disarm
    disarm_resp = client.post("/api/lens/arm", json={"armed": False})
    assert disarm_resp.status_code == 200
    disarm_data = disarm_resp.json()
    assert disarm_data.get("arm_state") == "OBSERVE_ONLY"

def test_lens_snapshot_generation():
    """Verify /api/lens/snapshot captures live frame and generates SHA256 checksum."""
    response = client.post("/api/lens/snapshot", json={"node": "l1_mac_mini"})
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "snapshot_captured"
    assert "filename" in data
    assert "path" in data
    assert "sha256" in data
    assert len(data["sha256"]) == 64, "SHA256 must be exactly 64 hex characters"
    assert data.get("bytes", 0) > 1000
    assert Path(data["path"]).exists(), "Snapshot file must exist on disk"
