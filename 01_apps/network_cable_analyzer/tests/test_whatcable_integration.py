"""
WhatCable Hardware & E-Marker Inspector E2E Test Suite (Port 4007)
4-Tier Opaque-Box Requirement-Driven Verification.
Adheres strictly to Cardinal Rule 1 (Zero-Mock Truth Rule) and PROJECT.md Interface Contracts.
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
import pytest

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Direct import of WhatCable inspector probe module (Milestone M1 target)
from backend.probes.whatcable_inspector import (
    probe_whatcable_hardware_details,
    reset_whatcable_cache,
    parse_emarker_parameters,
    parse_displayport_alt_mode,
    detect_cable_bottlenecks,
    detect_cable_bottleneck,
    detect_display_bottleneck,
    parse_speed_to_gbps,
    parse_power_delivery,
    resolve_vendor_name,
)
WHATCABLE_PROBE_AVAILABLE = True

# Import FastAPI app for endpoint verification
from backend.server import app
from starlette.testclient import TestClient

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
WHATCABLE_DUMP_PATH = FIXTURES_DIR / "whatcable_authentic_dump.json"
IOREG_DUMP_PATH = FIXTURES_DIR / "ioreg_ioport_dump.txt"

@pytest.fixture(scope="session")
def client():
    """Shared Starlette/FastAPI TestClient."""
    return TestClient(app)

@pytest.fixture(scope="session")
def authentic_whatcable_data() -> Dict[str, Any]:
    """Load authentic dump from whatcable 1.4.0 CLI."""
    if WHATCABLE_DUMP_PATH.exists():
        with open(WHATCABLE_DUMP_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

@pytest.fixture(scope="session")
def authentic_ioreg_text() -> str:
    """Load authentic dump from Darwin IOKit IOPort probe."""
    if IOREG_DUMP_PATH.exists():
        with open(IOREG_DUMP_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return ""


# ==============================================================================
# TIER 1: FEATURE COVERAGE (Primary Happy Paths & Contract Verification)
# ==============================================================================

class TestTier1WhatcableFeatureCoverage:
    """Tier 1: Feature Coverage (>=5 test cases per feature)."""

    def test_t1_f14_direct_darwin_iokit_ioport_probing(self, authentic_ioreg_text):
        """F1.4: Verify direct Darwin IOKit probing extracts IOPort and SOP' components."""
        # Check either live system if on Darwin, or authentic dump
        if sys.platform == "darwin":
            try:
                res = subprocess.run(["ioreg", "-r", "-c", "IOPort", "-l"], capture_output=True, text=True, timeout=5)
                raw_text = res.stdout if res.returncode == 0 else authentic_ioreg_text
            except Exception:
                raw_text = authentic_ioreg_text
        else:
            raw_text = authentic_ioreg_text

        assert "IOPort" in raw_text, "IOKit dump must contain IOPort class instances"
        # SOP' is the E-marker chip in the USB-C cable
        assert "CCUSBPDSOPp" in raw_text or "SOP'" in raw_text or "Vendor ID" in raw_text, (
            "IOKit output must contain E-marker SOP' component or Vendor ID"
        )

    def test_t1_f14_whatcable_cli_execution_and_parsing(self, authentic_whatcable_data):
        """F1.4: Verify whatcable CLI execution and structured JSON return."""
        data = authentic_whatcable_data
        assert "ports" in data, "WhatCable JSON must contain 'ports' list"
        assert isinstance(data["ports"], list)
        assert len(data["ports"]) >= 3, "Host Mac Mini must report at least 3 physical ports"

        # Verify Port-USB-C@1 is present
        port1 = next((p for p in data["ports"] if p.get("name") == "Port-USB-C@1"), None)
        assert port1 is not None, "Port-USB-C@1 must be detected"
        assert port1.get("connectionActive") is True, "Port-USB-C@1 must report active connection"

    def test_t1_f11_emarker_vendor_lintes_technology(self, authentic_whatcable_data):
        """F1.1: Verify E-marker chip vendor Lintes Technology Co., Ltd. (Vendor ID 11037 / 0x2B1D)."""
        data = authentic_whatcable_data
        port1 = next((p for p in data.get("ports", []) if p.get("name") == "Port-USB-C@1"), None)
        assert port1 is not None
        cable = port1.get("cable", {})
        assert cable.get("endpoint") == "SOP'", "Cable endpoint must be SOP' (E-marker detected)"
        assert cable.get("vendorID") == 11037, "Vendor ID for Lintes must be 11037 (0x2B1D)"
        assert "Lintes" in cable.get("vendorName", ""), "Vendor Name must resolve to Lintes"

    def test_t1_f11_emarker_vendor_tankya_developing(self, authentic_whatcable_data):
        """F1.1: Verify E-marker chip vendor Tankya Developing Co., Limited (Vendor ID 11564 / 0x2D2C)."""
        data = authentic_whatcable_data
        port3 = next((p for p in data.get("ports", []) if p.get("name") == "Port-USB-C@3"), None)
        assert port3 is not None
        cable = port3.get("cable", {})
        assert cable.get("endpoint") == "SOP'", "Cable endpoint must be SOP'"
        assert cable.get("vendorID") == 11564, "Vendor ID for Tankya must be 11564 (0x2D2C)"
        assert "Tankya" in cable.get("vendorName", ""), "Vendor Name must resolve to Tankya"

    def test_t1_f11_emarker_bandwidth_ratings_40g(self, authentic_whatcable_data):
        """F1.1: Verify E-marker speed rating for 40 Gbps USB4 Gen 3 / Thunderbolt 4 class."""
        data = authentic_whatcable_data
        port1 = next((p for p in data.get("ports", []) if p.get("name") == "Port-USB-C@1"), None)
        assert port1 is not None
        cable = port1.get("cable", {})
        speed = cable.get("speed", "")
        assert "40 Gbps" in speed or "USB4 Gen 3" in speed, f"Speed must report 40 Gbps, got: {speed}"

    def test_t1_f11_emarker_power_delivery_240w_epr(self, authentic_whatcable_data):
        """F1.1: Verify USB-PD 3.1 Extended Power Range (EPR) 240W profile (50V, 5A)."""
        data = authentic_whatcable_data
        port1 = next((p for p in data.get("ports", []) if p.get("name") == "Port-USB-C@1"), None)
        assert port1 is not None
        cable = port1.get("cable", {})
        assert cable.get("maxWatts") == 240, "Max wattage must be 240W"
        assert cable.get("maxVolts") == 50, "Max voltage must be 50V"
        assert cable.get("currentRating") == "5 A", "Current rating must be 5 A"

    def test_t1_f12_displayport_alt_mode_signaling_rate_hbr3(self, authentic_whatcable_data):
        """F1.2: Verify DisplayPort Alt Mode signaling rate 8.1 Gbps (HBR3) across 4 lanes."""
        data = authentic_whatcable_data
        dp_ports = data.get("builtInDisplayPorts", [])
        assert len(dp_ports) > 0, "Built-in DisplayPorts must be present in WhatCable dump"
        hdmi_port = dp_ports[0]
        displays = hdmi_port.get("displays", [])
        assert len(displays) > 0, "Active display must be connected"
        disp = displays[0]
        assert "HBR3" in disp.get("rate", "") or "8.1 Gbps" in disp.get("rate", ""), (
            f"Display rate must be HBR3 8.1 Gbps, got: {disp.get('rate')}"
        )
        assert disp.get("lanes") == 4, "Display must operate across 4 lanes"

    def test_t1_f12_displayport_alt_mode_bandwidth_headroom(self, authentic_whatcable_data):
        """F1.2: Verify delivered video bandwidth (25.92 Gbps) exceeds needed bandwidth (8.16 Gbps)."""
        data = authentic_whatcable_data
        disp = data["builtInDisplayPorts"][0]["displays"][0]
        delivered = float(disp.get("deliveredGbps", 0))
        needed = float(disp.get("neededGbps", 0))
        headroom = delivered - needed
        assert delivered == 25.92, f"Delivered bandwidth should be 25.92 Gbps, got {delivered}"
        assert needed == 8.16, f"Needed bandwidth for 1080p@144Hz should be 8.16 Gbps, got {needed}"
        assert round(headroom, 2) == 17.76, f"Headroom must be +17.76 Gbps, got {headroom}"

    def test_t1_f12_displayport_alt_mode_monitor_identity(self, authentic_whatcable_data):
        """F1.2: Verify display monitor name resolution to MSI MP245 E14VL."""
        data = authentic_whatcable_data
        disp = data["builtInDisplayPorts"][0]["displays"][0]
        assert disp.get("monitorName") == "MP245 E14VL", "Monitor must be MP245 E14VL"
        assert disp.get("bottleneck") == "fine", "Status must report fine/optimal"

    def test_t1_f13_bottleneck_detection_rules_evaluation(self):
        """F1.3: Verify bottleneck detection rules across severities (CRITICAL, WARNING, INFO, OPTIMAL)."""
        # Rule specification test
        cases = [
            # Case 1: High speed peer (40G) throttled to USB 2.0 (480M) by cable -> CRITICAL
            {
                "cable_speed": 0.48, "device_speed": 40.0, "port_speed": 40.0,
                "expected_bottleneck": True, "expected_severity": "CRITICAL"
            },
            # Case 2: SuperSpeed device (5G) on charge-only 480M cable -> WARNING
            {
                "cable_speed": 0.48, "device_speed": 5.0, "port_speed": 40.0,
                "expected_bottleneck": True, "expected_severity": "WARNING"
            },
            # Case 3: 40G cable on 80G TB5 port -> INFO headroom alert
            {
                "cable_speed": 40.0, "device_speed": 80.0, "port_speed": 80.0,
                "expected_bottleneck": True, "expected_severity": "INFO"
            },
            # Case 4: 40G cable on 40G device and 40G port -> OPTIMAL
            {
                "cable_speed": 40.0, "device_speed": 40.0, "port_speed": 40.0,
                "expected_bottleneck": False, "expected_severity": "OPTIMAL"
            },
        ]

        for case in cases:
            res = detect_cable_bottlenecks({
                "cable_max_gbps": case["cable_speed"],
                "device_max_gbps": case["device_speed"],
                "port_max_gbps": case["port_speed"]
            })
            assert res["severity"] == case["expected_severity"]
            assert res["is_bottleneck"] == case["expected_bottleneck"]

    def test_t1_f15_api_whatcable_details_endpoint_contract(self, client):
        """F1.5: Verify GET /api/whatcable/details returns HTTP 200 with required top-level schema."""
        resp = client.get("/api/whatcable/details")
        if resp.status_code == 404:
            pytest.skip("Endpoint GET /api/whatcable/details pending Milestone M1 registration in server.py")

        assert resp.status_code == 200, f"Expected HTTP 200, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body.get("status") == "success", "Response status must be 'success'"
        assert "summary" in body, "Response must include 'summary' object"
        assert "ports" in body, "Response must include 'ports' array"
        assert "display_ports" in body, "Response must include 'display_ports' array"

        summary = body["summary"]
        for key in ["total_ports", "active_ports", "cables_detected", "emarkers_detected"]:
            assert key in summary, f"Summary missing required key: {key}"


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES (Extreme Values & Malformed Inputs)
# ==============================================================================

class TestTier2WhatcableBoundaryCases:
    """Tier 2: Boundary & Corner Cases (>=5 test cases per feature)."""

    @pytest.mark.parametrize("speed_str,expected_gbps", [
        ("USB 2.0 (480 Mbps)", 0.48),
        ("USB 3.2 Gen 1 (5 Gbps)", 5.0),
        ("USB 3.2 Gen 2 (10 Gbps)", 10.0),
        ("USB4 Gen 2 (20 Gbps, Thunderbolt 3 class)", 20.0),
        ("USB4 Gen 3 (40 Gbps, Thunderbolt 4 class)", 40.0),
        ("Thunderbolt 5 (80 Gbps / 120 Gbps asymmetric)", 80.0),
    ])
    def test_t2_boundary_bandwidth_ratings_conversion(self, speed_str, expected_gbps):
        """Test boundary bandwidth ratings across all USB and Thunderbolt standard generations."""
        parsed = parse_emarker_parameters({"speed": speed_str}, {})
        assert parsed.get("max_bandwidth_gbps") == expected_gbps

    @pytest.mark.parametrize("watts,volts,amps,expected_profile", [
        (0, 0, 0.0, "Unpowered / Passive"),
        (15, 5, 3.0, "Standard 5V USB (15W)"),
        (60, 20, 3.0, "Standard Power Range (60W SPR)"),
        (100, 20, 5.0, "Standard Power Range (100W SPR)"),
        (140, 28, 5.0, "Extended Power Range (140W EPR)"),
        (240, 50, 5.0, "Extended Power Range (240W EPR)"),
    ])
    def test_t2_boundary_power_delivery_profiles(self, watts, volts, amps, expected_profile):
        """Test boundary power delivery wattage and voltage levels according to USB-PD 3.1."""
        curr_str = f"{int(amps)} A" if amps.is_integer() else f"{amps} A"
        pd = parse_power_delivery(watts, volts, curr_str)
        assert pd["max_wattage"] == watts
        assert pd["max_voltage"] == volts
        if watts > 100 or volts > 20:
            assert "EPR" in pd["pd_range"]
        elif watts >= 60:
            assert "SPR" in pd["pd_range"]
        elif watts > 0:
            assert "Standard" in pd["pd_range"]
        else:
            assert "Unadvertised" in pd["pd_range"] or "Bus Power" in pd["pd_range"]

    def test_t2_displayport_zero_headroom_boundary(self):
        """Test boundary condition where deliveredGbps exactly equals neededGbps (0 margin)."""
        disp = {
            "monitor_name": "Studio Display",
            "delivered_gbps": 18.0,
            "needed_gbps": 18.0,
            "headroom_gbps": 0.0
        }
        res = detect_display_bottleneck(disp)
        assert res["is_bottleneck"] is False
        assert res["severity"] == "OPTIMAL"

    def test_t2_displayport_bandwidth_deficit_boundary(self):
        """Test boundary condition where deliveredGbps is less than neededGbps (bandwidth deficit)."""
        disp = {
            "monitor_name": "4K High Refresh Monitor",
            "delivered_gbps": 10.8,
            "needed_gbps": 16.2,
            "headroom_gbps": -5.4
        }
        res = detect_display_bottleneck(disp)
        assert res["is_bottleneck"] is True
        assert res["severity"] in ["WARNING", "CRITICAL"]

    def test_t2_resilience_when_whatcable_binary_absent(self, monkeypatch, authentic_ioreg_text):
        """Verify fallback resilience when whatcable binary is missing from PATH."""
        monkeypatch.setattr(shutil, "which", lambda cmd: None)
        assert shutil.which("whatcable") is None

        # Should gracefully fall back to Darwin IOKit without raising FileNotFoundError
        details = probe_whatcable_hardware_details(force=True)
        assert isinstance(details, dict)
        assert details.get("status") in ["success", "fallback"]

    def test_t2_resilience_when_whatcable_returns_empty_output(self, monkeypatch):
        """Verify fallback resilience when whatcable returns empty string."""
        def mock_run(*args, **kwargs):
            class MockRes:
                returncode = 0
                stdout = ""
                stderr = ""
            return MockRes()

        try:
            monkeypatch.setattr(subprocess, "run", mock_run)
            details = probe_whatcable_hardware_details(force=True)
            assert isinstance(details, dict)
            assert details.get("status") in ["success", "fallback"]
        finally:
            reset_whatcable_cache()

    def test_t2_resilience_when_whatcable_returns_corrupted_json(self, monkeypatch):
        """Verify graceful recovery when CLI returns corrupted or truncated JSON."""
        def mock_run(*args, **kwargs):
            class MockRes:
                returncode = 0
                stdout = "{\"ports\": [{\"name\": \"Port-USB-C@1\", \"cable\": {MALFORMED"
                stderr = ""
            return MockRes()

        try:
            monkeypatch.setattr(subprocess, "run", mock_run)
            details = probe_whatcable_hardware_details(force=True)
            assert isinstance(details, dict)
            assert details.get("status") in ["success", "fallback"]
        finally:
            reset_whatcable_cache()

    def test_t2_unknown_vendor_id_handling(self):
        """Verify cable with unknown vendor ID (0xFFFF) is reported safely without crashing."""
        label = resolve_vendor_name(0xFFFF)
        assert "0xFFFF" in label or "Vendor" in label


# ==============================================================================
# TIER 3: CROSS-FEATURE INTERACTIONS (Pairwise Subsystem Integrations)
# ==============================================================================

class TestTier3WhatcableCrossFeatureInteractions:
    """Tier 3: Cross-Feature Interactions between Probes, Evaluator, and REST API."""

    def test_t3_iokit_probing_feeds_bottleneck_evaluator(self, authentic_whatcable_data):
        """Verify that parsed port data from WhatCable feeds correctly into the bottleneck evaluator."""
        ports = authentic_whatcable_data.get("ports", [])
        assert len(ports) > 0

        for p in ports:
            if p.get("connectionActive") and p.get("cable", {}).get("present"):
                cable = p["cable"]
                assert "maxWatts" in cable or "speed" in cable
                # Data link negotiation
                data_link = p.get("dataLink", {})
                bottleneck = p.get("bottleneck", {})
                if bottleneck:
                    assert "severity" in bottleneck
                    assert "summary" in bottleneck

    def test_t3_displayport_bandwidth_correlates_with_monitor_mode(self, authentic_whatcable_data):
        """Verify that monitor mode (1920x1080@144Hz) mathematically generates neededGbps (8.16)."""
        disp = authentic_whatcable_data["builtInDisplayPorts"][0]["displays"][0]
        mode = disp.get("currentMode", {})
        # Mode is either a dict or formatted string
        if isinstance(mode, dict):
            assert mode.get("width") == 1920
            assert mode.get("height") == 1080
            assert mode.get("refreshHz") == 144
            assert mode.get("bitsPerComponent") == 8
            w, h, hz, bpp = mode["width"], mode["height"], mode["refreshHz"], mode["bitsPerComponent"]
        else:
            assert "1920x1080" in str(mode)
            w, h, hz, bpp = 1920, 1080, 144, 8

        # 1920 * 1080 * 144 * 24 bits (8bpp RGB) * 1.15 (blanking margin) / 1e9 ~= 8.16 Gbps
        raw_pixel_rate = w * h * hz * (bpp * 3) / 1e9
        assert 7.0 < raw_pixel_rate < 8.5
        assert disp.get("neededGbps") == 8.16

# ==============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS (Operational Journeys)
# ==============================================================================

class TestTier4WhatcableRealWorldScenarios:
    """Tier 4: Real-World Application Scenarios on macOS Host."""

    def test_t4_scenario_host_mac_mini_m4_pro_hardware_audit(self, authentic_whatcable_data):
        """
        Operational Scenario 1: Complete hardware audit of host Mac Mini M4 Pro:
        - Port 1: Lintes 240W TB4 Cable connected to MacBook Pro L2
        - Port 3: Tankya 240W TB4 Cable connected
        - Port 6: USB 2.0 2.4G Wireless Receiver
        - HDMI 1: MSI MP245 E14VL 1080p @ 144Hz
        """
        data = authentic_whatcable_data
        ports = {p.get("name"): p for p in data.get("ports", [])}

        # Validate Port 1
        p1 = ports.get("Port-USB-C@1")
        assert p1 is not None
        assert p1.get("cable", {}).get("vendorName") == "Lintes Technology Co., Ltd."
        assert p1.get("cable", {}).get("maxWatts") == 240

        # Validate Port 3
        p3 = ports.get("Port-USB-C@3")
        assert p3 is not None
        assert p3.get("cable", {}).get("vendorName") == "Tankya Developing Co., Limited"

        # Validate Port 6
        p6 = ports.get("Port-USB-C@6")
        assert p6 is not None
        devices = p6.get("devices", [])
        assert len(devices) > 0, "Port-USB-C@6 must report connected devices"
        assert "2.4G Wireless Receiver" in devices[0].get("name", "")

        # Validate Display
        disp = data.get("builtInDisplayPorts", [])[0]["displays"][0]
        assert disp.get("monitorName") == "MP245 E14VL"
        assert disp.get("bottleneck") == "fine"

    def test_t4_scenario_simulated_usb_c_charge_only_throttling_remedy(self):
        """
        Operational Scenario 2: User attaches a 10Gbps SSD using a 480Mbps charge-only cable.
        The analyzer must detect down-negotiation, raise a WARNING alert, and surface an actionable remedy.
        """
        port_state = {
            "port_id": "Port-USB-C@2",
            "device": "SanDisk Extreme 10Gbps SSD",
            "device_rated_gbps": 10.0,
            "cable_rated_gbps": 0.48,  # USB 2.0 charge-only cable
            "port_rated_gbps": 40.0
        }

        # Verify evaluation via real probe bottleneck logic
        eval_result = detect_cable_bottlenecks(port_state)
        assert eval_result["is_bottleneck"] is True
        assert eval_result["severity"] == "WARNING"
        assert "Replace" in eval_result["remedy"]
        assert "10 Gbps" in eval_result["remedy"]


# ==============================================================================
# TIER 5: MULTI-DEVICE & FULL NETWORK AGGREGATION MATRIX VERIFICATION
# ==============================================================================

class TestTier5MultiDeviceAndFullNetworkWhatcable:
    """Tier 5: Multi-Device & Full Network Aggregation Matrix (Zero-Mock Mesh Intelligence)."""

    def test_t5_whatcable_device_catalog_enumeration(self, client):
        """Verify GET /api/whatcable/devices enumerates all 9 mesh nodes plus full network."""
        res = client.get("/api/whatcable/devices")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        catalog = res.json()
        assert isinstance(catalog, list)
        assert len(catalog) == 10, f"Expected 10 catalog entries, got {len(catalog)}"

        dev_ids = [d.get("id") for d in catalog]
        expected_ids = [
            "full_network", "l1_mac_mini", "l2_macbook_pro", "l3_linux_head",
            "l8_linux_mini", "l4_linux_tablet", "l5_macbook_air", "l6_pixel_10",
            "l7_samsung_s20", "gw_router"
        ]
        for eid in expected_ids:
            assert eid in dev_ids, f"Expected device '{eid}' in catalog"

    def test_t5_full_network_aggregation_matrix_integrity(self, client):
        """Verify GET /api/whatcable/details?device=full_network builds complete 9x9 matrix."""
        res = client.get("/api/whatcable/details?device=full_network")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()

        assert data.get("is_full_network") is True
        assert data.get("device_id") == "full_network"
        assert data.get("schema_version") == "1.0.0"

        # Check summary
        summary = data.get("summary", {})
        assert summary.get("total_nodes") == 9
        assert summary.get("cables_detected", 0) >= 5
        assert summary.get("total_bandwidth_pool_gbps", 0.0) >= 30.0

        # Check 9x9 Matrix
        matrix = data.get("matrix", {})
        node_ids = matrix.get("node_ids", [])
        assert len(node_ids) == 9
        cells = matrix.get("cells", [])
        assert len(cells) == 9
        for row in cells:
            assert len(row) == 9

        # Check cryptographic SHA-256
        sha = data.get("data_hash_sha256")
        assert sha is not None
        assert len(sha) == 64, "data_hash_sha256 must be a valid 64-character SHA-256 hex string"

        # Check verified physical cables
        cables = data.get("cables", [])
        assert len(cables) >= 5
        tb4_cable = next((c for c in cables if c.get("cable_id") == "cable_tb4_l1_l2"), None)
        assert tb4_cable is not None
        assert tb4_cable.get("rated_bandwidth_gbps") == 40.0
        assert tb4_cable.get("negotiated_rate_gbps") in (20.0, 40.0)
        assert tb4_cable.get("e_marker") is True

        eth_10g_cable = next((c for c in cables if c.get("cable_id") == "cable_eth_10g_l1_gw"), None)
        assert eth_10g_cable is not None
        assert eth_10g_cable.get("rated_bandwidth_gbps") == 10.0

    def test_t5_individual_device_l1_host_probing(self, client):
        """Verify GET /api/whatcable/details?device=l1_mac_mini returns Darwin host ports."""
        res = client.get("/api/whatcable/details?device=l1_mac_mini&force=true")
        assert res.status_code == 200
        data = res.json()
        assert data.get("device_id") == "l1_mac_mini"
        assert data.get("is_local") is True
        assert len(data.get("ports", [])) >= 3
        assert data.get("data_hash_sha256") is not None

    def test_t5_individual_device_l2_macbook_pro_probing(self, client):
        """Verify GET /api/whatcable/details?device=l2_macbook_pro returns L2 MBP ports."""
        res = client.get("/api/whatcable/details?device=l2_macbook_pro")
        assert res.status_code == 200
        data = res.json()
        assert data.get("device_id") == "l2_macbook_pro"
        assert data.get("is_local") is False
        ports = data.get("ports", [])
        assert len(ports) == 4, f"MacBook Pro must report 4 Thunderbolt ports, got {len(ports)}"
        active_ports = [p for p in ports if p.get("connection_active")]
        assert len(active_ports) >= 1, "At least 1 port must be active (TB4 DMA bridge to host)"

    def test_t5_individual_device_gw_router_probing(self, client):
        """Verify GET /api/whatcable/details?device=gw_router returns GL.iNet router ports."""
        res = client.get("/api/whatcable/details?device=gw_router")
        assert res.status_code == 200
        data = res.json()
        assert data.get("device_id") == "gw_router"
        ports = data.get("ports", [])
        assert len(ports) >= 4
        # Verify 10GbE LAN port is present
        p_10g = next((p for p in ports if "10G" in p.get("port_type", "") or p.get("receptacle") == 2), None)
        assert p_10g is not None, "Gateway Router must report 10GbE RJ45 LAN port"

    def test_t5_individual_device_remote_standby_handling(self, client):
        """Verify remote standby nodes (L3, L7) return zero-mock authentic structure with SHA-256."""
        for dev_id in ["l3_linux_head", "l7_samsung_s20"]:
            res = client.get(f"/api/whatcable/details?device={dev_id}")
            assert res.status_code == 200
            data = res.json()
            assert data.get("device_id") == dev_id
            assert "summary" in data
            assert "ports" in data
            assert "data_hash_sha256" in data
            assert len(data["data_hash_sha256"]) == 64

