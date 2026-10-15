"""
Regression and Truth Verification Tests for Milestone 1 Remediation.
Enforces Zero-Mock Rule 1 and Rule 0 Canonical Hardware Matrix invariants:
- Zero banned literals ('Tankya', 'Lintes', '240W EPR', 'Qwen 3.8 Max', '144Hz', 'OpenWrt 24', '0.27 ms')
- Dynamic telemetry contract: unreachable or unprobed fields must be null (None), never fallback mock strings
- SharkWire packet engine: 0 fixture preloading, 0 infinite replay loops, clean BPF permission handling
- Port 4003 Screen Lens and Port 4005 Bluetooth Terminal graceful resilience
"""

import sys
from pathlib import Path
import pytest

# Ensure backend is on sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from probes.cable_probe import probe_all_cables, get_whatcable_data
from probes.whatcable_inspector import aggregate_full_network_whatcable
from probes.shark_wire.engine import SharkWirePacketEngine
from probes.network_ip_inspector import probe_network_ip
from probes.speed_probe import probe_network_latencies
from config import LOCAL_AI_MODEL, REVERSE_ENGINEERING_TARGETS


BANNED_LITERAL_SUBSTRINGS = [
    "Lintes Technology Co.",
    "240W EPR (48V / 5A)",
    "Qwen 3.8 Max",
    "qwen_38_max",
    "OpenWrt 24.10",
    "0.27ms RTT",
    "0.56ms RTT",
    "0.28ms RTT",
]


def test_banned_literals_purged_from_cable_probe():
    """Verify cable probe emits no fabricated e-marker or power literals."""
    cables = probe_all_cables()
    assert isinstance(cables, list)
    for cable in cables:
        # Check vendor does not contain fabricated Lintes
        vendor = cable.get("e_marker_vendor")
        if vendor is not None:
            assert "Lintes" not in vendor, f"Fabricated vendor Lintes found in {cable}"
        # Check power rating does not contain fabricated literal string
        pwr = cable.get("power_delivery_rating")
        if pwr is not None:
            assert "240W EPR (48V / 5A)" not in pwr, f"Fabricated power literal found in {cable}"


def test_banned_literals_purged_from_whatcable_inspector():
    """Verify WhatCable inspector emits no banned literals in interconnects and inventory."""
    report = aggregate_full_network_whatcable()
    report_str = str(report)

    for banned in BANNED_LITERAL_SUBSTRINGS:
        assert banned not in report_str, f"Banned literal '{banned}' detected in WhatCable report!"

    # Verify router OS version is authentic probed version
    net_topo = report.get("network_topology", {})
    router_os = net_topo.get("router_os", "")
    assert "OpenWrt 24.10" not in router_os
    if router_os:
        assert "21.02" in router_os or "OpenWrt" in router_os


def test_sharkwire_packet_engine_zero_mock_and_no_replay():
    """Verify SharkWire engine starts with 0 packets and no fixture replay loop."""
    engine = SharkWirePacketEngine(maxlen=100, default_interface="en0")

    # Initial state must be empty
    assert len(engine.ring_buffer) == 0
    stats = engine.get_stats()
    assert stats["captured_count"] == 0
    assert stats["displayed_count"] == 0
    assert stats["state"] == "stopped"

    # Start capture on an interface - if unprivileged, cleanly transitions to bpf_permission_required without synthetic packets
    res = engine.start("dummy_test_interface_not_permitted")
    assert res["status"] == "ok"
    # Wait briefly for worker thread to evaluate permissions
    import time
    time.sleep(0.1)
    engine.stop()

    # Zero-mock invariant: Ring buffer must NOT contain synthetic replayed fixture packets
    assert len(engine.ring_buffer) == 0
    assert engine.packet_counter == 0


def test_speed_probe_null_contract_on_unreachable_target():
    """Verify latency probes return -1.0 / unmeasured when target cannot be reached."""
    from probes.speed_probe import ping_rtt, probe_network_latencies

    # Unreachable target must return -1.0, never a fake 0.27ms literal
    rtt = ping_rtt("169.254.254.254", timeout_ms=100)
    assert rtt == -1.0

    # probe_network_latencies returns genuine dict
    res = probe_network_latencies()
    assert isinstance(res, dict)
    for link_id, data in res.items():
        assert isinstance(data, dict)
        assert "rtt_ms" in data
        # rtt_ms must be either a measured positive float or -1.0 if unreachable
        assert isinstance(data["rtt_ms"], (int, float))


def test_backend_config_models_adhere_to_rule_0_truth():
    """Verify default local model aligns with Rule 0 probed reality (Hermes-3 8B, not Qwen 3.8 Max)."""
    assert "qwen_38_max" not in LOCAL_AI_MODEL.lower()
    assert "hermes" in LOCAL_AI_MODEL.lower() or "8b" in LOCAL_AI_MODEL.lower()

    # REVERSE_ENGINEERING_TARGETS assigned_models should not claim Qwen 3.8 Max on :8082
    for target_key, target in REVERSE_ENGINEERING_TARGETS.items():
        assigned = target.get("assigned_models", {})
        for tier, model_name in assigned.items():
            assert "Qwen 3.8 Max" not in model_name, f"Target {target_key} tier {tier} assigned banned Qwen 3.8 Max literal"


def test_measured_envelope_contract():
    """Verify the measured and unmeasured telemetry contracts conform to Rule 0/1."""
    from probes._measured import measured, unmeasured, provenance

    m = measured(40.0, "system_profiler SPThunderboltDataType -json")
    assert m["value"] == 40.0
    assert m["source_cmd"] == "system_profiler SPThunderboltDataType -json"
    assert isinstance(m["captured_at"], float)
    assert m["measured"] is True

    u = unmeasured("host unreachable")
    assert u["value"] is None
    assert u["source_cmd"] is None
    assert isinstance(u["captured_at"], float)
    assert u["measured"] is False
    assert u["reason"] == "host unreachable"

    p = provenance("ubus call system info", ok=True)
    assert p["source_cmd"] == "ubus call system info"
    assert p["ok"] is True
    assert p["error"] is None
    assert isinstance(p["captured_at"], float)


def test_router_gateway_probe_contract():
    """Verify router gateway probe returns structured telemetry with authentic schema."""
    from probes.router_gateway_probe import get_router_telemetry

    data = get_router_telemetry()
    assert isinstance(data, dict)
    assert "router_ip" in data
    assert "internet_path" in data
    assert "wan" in data
    assert "link_flaps" in data
    assert "switch_ports" in data

    # Verify no fake OpenWrt 24.10 literal
    release = data.get("openwrt_release", {})
    if isinstance(release, dict):
        assert "OpenWrt 24.10" not in str(release)


@pytest.mark.asyncio
async def test_screen_lens_api_endpoints_graceful_fallbacks():
    """Verify server lens endpoints return clean graceful JSON on Port 4003 failure."""
    from server import app
    from httpx import AsyncClient, ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Arm
        resp = await client.post("/api/lens/arm", json={"enabled": True})
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data or "lens_active" in data

        # Select node
        resp = await client.post("/api/lens/node/select", json={"node_id": "L1"})
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data

        # HID action
        resp = await client.post("/api/lens/hid/click", json={"x": 100, "y": 200})
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data


def test_all_four_api_endpoints_free_of_ten_banned_strings():
    """Verify that /api/cables, /api/topology, /api/router/telemetry, and /api/whatcable/details
    responses contain none of the banned strings, with topology scoping 0.27 to latency/rtt/ping fields.
    """
    from fastapi.testclient import TestClient
    from server import app

    ten_banned_strings = [
        "0.27",
        "0.56 ms",
        "Tankya",
        "Lintes",
        "240W EPR",
        "Qwen 3.8 Max",
        "144Hz",
        "OpenWrt 24",
        "10000F",
        "CONNECTED_AND_STREAMING",
    ]
    nine_banned_strings = [
        "0.56 ms",
        "Tankya",
        "Lintes",
        "240W EPR",
        "Qwen 3.8 Max",
        "144Hz",
        "OpenWrt 24",
        "10000F",
        "CONNECTED_AND_STREAMING",
    ]

    client = TestClient(app)

    # 1. /api/cables, /api/router/telemetry, /api/whatcable/details: assert all 10 banned strings are absent from entire text
    text_endpoints = [
        "/api/cables",
        "/api/router/telemetry",
        "/api/whatcable/details",
    ]
    for ep in text_endpoints:
        resp = client.get(ep)
        assert resp.status_code == 200, f"Endpoint {ep} failed with status {resp.status_code}"
        text = resp.text
        for banned in ten_banned_strings:
            assert banned not in text, f"Banned string '{banned}' found in {ep} response: {text[:200]}"

    # 2. /api/topology: assert 9 banned strings absent from entire text, and 0.27 absent as a latency/ping/RTT value
    resp_topo = client.get("/api/topology")
    assert resp_topo.status_code == 200, f"/api/topology failed with status {resp_topo.status_code}"
    topo_text = resp_topo.text
    for banned in nine_banned_strings:
        assert banned not in topo_text, f"Banned string '{banned}' found in /api/topology response: {topo_text[:200]}"

    assert "0.27 ms" not in topo_text, "Prohibited latency constant '0.27 ms' found in /api/topology text"
    assert "0.27ms" not in topo_text, "Prohibited latency constant '0.27ms' found in /api/topology text"

    topo_data = resp_topo.json()
    def assert_no_027_latency(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                curr_path = f"{path}.{k}" if path else k
                if any(lat in k.lower() for lat in ("latency", "rtt", "ping")):
                    assert v != 0.27, f"0.27 latency found at {curr_path}: {v}"
                    assert v != "0.27", f"0.27 latency found at {curr_path}: {v}"
                    assert v != "0.27 ms", f"0.27 ms latency found at {curr_path}: {v}"
                    assert v != "0.27ms", f"0.27ms latency found at {curr_path}: {v}"
                assert_no_027_latency(v, curr_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                assert_no_027_latency(item, f"{path}[{i}]")

    assert_no_027_latency(topo_data)


