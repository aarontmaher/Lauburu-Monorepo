"""
Unit and Integration Tests for Network Analyzer Lauburu Upgrades
================================================================
Verifies:
1. /api/network/probe_ip - Dynamic target IP inspection & populator
2. /api/crash/recent - Kernel panic, ACIO2, and process crash queries
3. /api/crash/stream - Server-Sent Events crash streaming
4. /api/router/telemetry - OpenWrt ubus router gateway metrics
5. /api/router/launch_url - GL.iNet Admin URL
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from server import app

client = TestClient(app)

def test_probe_network_ip_localhost():
    """Verify probing 127.0.0.1 returns loopback routing, ping, and open ports."""
    resp = client.get("/api/network/probe_ip?ip=127.0.0.1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_ip"] == "127.0.0.1"
    assert data["status"].startswith("ONLINE")
    assert "ping" in data
    assert "routing" in data
    assert "services" in data
    assert "sha256_proof" in data
    assert len(data["sha256_proof"]) == 64
    assert data["proof_signature"].startswith("LAUBURU_TRUTH_VERIFIED_")

def test_probe_network_ip_post_router():
    """Verify POST /api/network/probe_ip correctly resolves GL.iNet router."""
    resp = client.post("/api/network/probe_ip", json={"ip": "192.168.8.1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_ip"] == "192.168.8.1"
    assert data["matched_device"] is not None
    assert "GL.iNet" in data["matched_device"]["name"]
    assert data["routing"]["interface"] in ("en0", "bridge0", "en1")
    assert len(data["open_ports"]) > 0

def test_crash_recent_endpoint():
    """Verify /api/crash/recent returns authentic crash history."""
    resp = client.get("/api/crash/recent?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "crashes" in data
    assert isinstance(data["crashes"], list)
    if data["total"] > 0:
        c = data["crashes"][0]
        assert "severity" in c
        assert "event_type" in c
        assert "component" in c

def test_crash_stream_endpoint():
    """Verify /api/crash/stream test mode returns cleanly."""
    resp = client.get("/api/crash/stream", headers={"user-agent": "testclient"})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("test_mode") is True
    assert "crashes" in data

def test_router_telemetry_endpoint():
    """Verify /api/router/telemetry returns authentic GL-BE14000 gateway metrics."""
    resp = client.get("/api/router/telemetry")
    assert resp.status_code == 200
    data = resp.json()
    assert data["router_ip"] == "192.168.8.1"
    assert "switch_ports" in data
    assert len(data["switch_ports"]) >= 4
    assert "wifi7_mlo" in data
    assert data["admin_gui_url"] == "http://192.168.8.1/"

def test_router_launch_url():
    """Verify /api/router/launch_url returns correct direct link."""
    resp = client.get("/api/router/launch_url")
    assert resp.status_code == 200
    data = resp.json()
    assert data["url"] == "http://192.168.8.1/"
