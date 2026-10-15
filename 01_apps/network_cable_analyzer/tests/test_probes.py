"""
Unit Tests for Lauburu Hardware, Cable, RAM, NPU, Bluetooth Terminal, and Local AI Probes.
Verifies zero-mock empirical data invariants across the 7-layer mesh.
"""
import sys
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import pytest
from probes.cable_probe import (
    probe_all_cables,
    get_whatcable_data,
    get_thunderbolt_device_map,
    get_bluetooth_anchor_map,
    evaluate_bottleneck_and_transfer
)
from probes.ram_npu_probe import (
    probe_local_macos_ram_npu,
    probe_all_devices_ram_npu
)
from probes.speed_probe import (
    get_realtime_throughput,
    probe_network_latencies,
    probe_all_speed_metrics
)
from probes.bt_terminal_probe import (
    probe_bluetooth_terminal_and_ai,
    query_bluetooth_terminal,
    reconnect_via_bluetooth,
    parse_bluetooth_wake_events,
    pull_all_from_bluetooth_terminal,
    parse_terminal_nodes,
    parse_terminal_cables,
    parse_terminal_power
)
from probes.dynamic_ip_finder import find_dynamic_mesh_ips, get_node_dynamic_ips, get_adb_target, get_tb4_bridge_ip
from probes.active_connections_probe import (
    get_all_active_connections,
    probe_active_bluetooth_connections,
    probe_active_ssh_connections,
    probe_active_tailscale_connections,
    probe_active_wifi_connections,
    probe_active_usb_connections,
    probe_active_thunderbolt_connections
)
from probes.mesh_topology import build_full_topology
from neo_bridge import NeoBridge

def test_cable_probe_fields_and_integrity():
    cables = probe_all_cables()
    assert isinstance(cables, list)
    assert len(cables) > 0, "Should detect at least one active cable or physical link"

    # Find the Thunderbolt 4 cable to MacBook Pro
    tb4_cables = [c for c in cables if c.get("id") == "cable_tb4_mac_mini_to_mbp"]
    assert len(tb4_cables) > 0, "Thunderbolt 4 smart cable must be detected"
    tb4 = tb4_cables[0]
    assert tb4["max_bandwidth_gbps"] == 40.0
    assert tb4["e_marker"] is True
    assert tb4.get("e_marker_vendor") is None or isinstance(tb4.get("e_marker_vendor"), str)

    # Validate schema for all cables
    for c in cables:
        assert "id" in c
        assert "source_device_id" in c
        assert "target_device_id" in c
        assert "cable_type" in c
        assert "max_bandwidth_gbps" in c
        assert c["max_bandwidth_gbps"] > 0
        assert "protocol" in c

    # Ensure synthetic Pixel-to-SSD cable is not present
    assert not any(c.get("id") == "cable_pixel_usb_storage" for c in cables)

def test_local_macos_ram_and_ane():
    data = probe_local_macos_ram_npu()
    assert data["device_id"] == "l1_mac_mini"
    assert data["online"] is True
    
    ram = data["ram"]
    assert ram["total_gb"] == 24.0, "Mac Mini M4 Pro must report 24.0 GB physical RAM"
    assert ram["used_gb"] > 0
    assert ram["available_gb"] > 0
    assert 0 <= ram["usage_pct"] <= 100

    npu = data["npu"]
    assert "Apple Neural Engine" in npu["name"]
    assert npu["cores"] == 16
    assert npu["max_tops"] == 38.0

def test_all_devices_ram_npu_aggregation():
    devices = probe_all_devices_ram_npu()
    assert "l1_mac_mini" in devices
    assert "l2_macbook_pro" in devices
    assert "l3_linux_head" in devices
    assert "l4_linux_tablet" in devices
    assert "l5_macbook_air" in devices
    assert "l6_pixel_10" in devices
    assert "gw_router" in devices
    assert "l7_samsung_s20" in devices

    # Check Linux Head Node specs
    linux = devices["l3_linux_head"]
    assert linux["ram"]["total_gb"] >= 14.0

    # Check Linux Tablet specs (4 GB physical LPDDR4 / 3.73 GB kernel or 8 GB profile)
    tablet = devices["l4_linux_tablet"]
    assert tablet["ram"]["total_gb"] in (8.0, 3.73) or tablet["ram"]["total_gb"] >= 3.5

    # Check MacBook Air specs
    mba = devices["l5_macbook_air"]
    assert mba["ram"]["total_gb"] == 16.0

    # Check Pixel 10 Pro XL specs
    pixel = devices["l6_pixel_10"]
    assert pixel["ram"]["total_gb"] >= 14.0
    assert "Tensor G5" in pixel["npu"]["name"]

    # Check Samsung S20 standby zero-mock contract (no fake used_gb)
    s20 = devices["l7_samsung_s20"]
    if not s20["online"]:
        assert s20["ram"]["used_gb"] is None or s20["ram"]["used_gb"] == 0.0

def test_speed_probe_throughput_and_latencies():
    speed = probe_all_speed_metrics()
    assert "throughput" in speed
    assert "latencies" in speed
    assert "link_specs" in speed

    tp = speed["throughput"]
    assert "en0" in tp or "en1" in tp

    lat = speed["latencies"]
    assert "tb4_mac_bridge" in lat
    tb4_lat = lat["tb4_mac_bridge"]["rtt_ms"]
    assert isinstance(tb4_lat, float)

def test_bluetooth_terminal_and_local_ai():
    res = probe_bluetooth_terminal_and_ai(force=False)
    assert "raw_terminal_stream" in res
    assert "ai_synthesis" in res
    ai = res["ai_synthesis"]
    assert "ai_model" in ai
    assert "identified_devices" in ai
    assert isinstance(ai["identified_devices"], list)

def test_full_mesh_topology_assembly():
    topo = build_full_topology()
    assert "timestamp" in topo
    assert "mesh_summary" in topo
    assert "devices" in topo
    assert "cables" in topo
    assert "speed_metrics" in topo
    assert "bluetooth_terminal" in topo

    summary = topo["mesh_summary"]
    assert summary["total_nodes"] >= 8
    assert summary["total_ram_gb"] >= 80.0, "Pooled mesh RAM should exceed 80 GB"
    assert summary["total_npu_tops"] > 50.0, "Pooled mesh NPU TOPS should exceed 50 TOPS"
    assert summary["active_cables"] > 0
    assert summary["bluetooth_terminal"] == "CONNECTED"

def test_neo_bridge_recommendations():
    topo = build_full_topology()
    bridge = NeoBridge()
    recs = bridge.generate_ai_cable_recommendations(topo)
    assert isinstance(recs, list)
    assert len(recs) > 0, "Should generate at least one optimization recommendation"
    for r in recs:
        assert "title" in r
        assert "recommendation" in r
        assert "benefit" in r

def test_dynamic_ip_finder():
    data = find_dynamic_mesh_ips(force=True)
    assert "timestamp" in data
    assert "resolution_latency_ms" in data
    assert data["resolution_latency_ms"] > 0
    assert "nodes" in data
    nodes = data["nodes"]

    # Verify all 8 mesh layers resolved plus auto-discovered peers
    assert len(nodes) >= 8
    expected_nodes = [
        "l1_mac_mini", "l2_macbook_pro", "l3_linux_head", "l4_linux_tablet",
        "l5_macbook_air", "l6_pixel_10", "l7_samsung_s20", "gw_router"
    ]
    for nid in expected_nodes:
        assert nid in nodes, f"Node {nid} must be in dynamic IP map"
        n = nodes[nid]
        assert "local_ip" in n
        assert "tailscale_ip" in n
        assert n["local_ip"] is not None, f"Node {nid} must have resolved local_ip"
        assert n["tailscale_ip"] is not None, f"Node {nid} must have resolved tailscale_ip"

    # Test helper functions
    tb4_ip = get_tb4_bridge_ip()
    assert tb4_ip.startswith("169.254.") and not tb4_ip.endswith(".255.255")
    assert get_adb_target("l6_pixel_10") is not None
    assert get_adb_target("l7_samsung_s20") is not None
    assert get_node_dynamic_ips("l1_mac_mini")["tailscale_ip"] == "100.119.199.76"

def test_bluetooth_reconnect():
    res = reconnect_via_bluetooth()
    assert "status" in res
    assert res["status"] == "reconnection_completed"
    assert "duration_ms" in res
    assert res["duration_ms"] > 0
    assert "reconnected_devices" in res
    assert isinstance(res["reconnected_devices"], list)
    assert "bluetooth_wake_events" in res
    assert isinstance(res["bluetooth_wake_events"], list)
    assert "raw_output" in res

    # Verify parser with a full sample dump covering all laptops and Mac Mini
    sample_dump = """
[RECONNECTING MESH: EXECUTING LINE 1 BLUETOOTH PROXIMITY WAKE]...
• Target Matrix: All Laptops (MBP L2, Linux L3, MBA L5), Mac Mini (L1 Host), & Mobile Peripherals (L6, L7)
  • Line 1 Bluetooth Controller -> Host Mac Mini M4 Pro (L1) [1c-f6-4c-81-0b-28]: CONTROLLER ACTIVE (Power: ON)
  • Line 1 Bluetooth Wake -> MacBook Pro Vault (L2 Laptop) [2c-ca-16-08-c0-27]: PULSE DISPATCHED
  • Line 1 Bluetooth Wake -> Linux Head Node (L3 Laptop) [00-41-0e-14-28-44]: CONNECTED
  • Line 1 Bluetooth Wake -> MacBook Air M4 (L5 Laptop) [dc-29-55-d6-fc-0b]: PULSE DISPATCHED
  • Line 1 Bluetooth Wake -> Pixel 10 Pro XL (L6 Mobile) [30-e0-44-6d-18-ec]: CONNECTED
  • Line 1 Bluetooth Wake -> Samsung Galaxy S20+ (L7 Mobile) [5c-cb-99-05-81-41]: CONNECTED
"""
    events = parse_bluetooth_wake_events(sample_dump)
    assert len(events) == 6
    dev_names = [e["device"] for e in events]
    assert any("Host Mac Mini M4 Pro" in d for d in dev_names)
    assert any("MacBook Pro Vault" in d for d in dev_names)
    assert any("Linux Head Node" in d for d in dev_names)
    assert any("MacBook Air M4" in d for d in dev_names)
    assert any("Pixel 10 Pro XL" in d for d in dev_names)
    assert any("Samsung Galaxy S20+" in d for d in dev_names)

def test_device_capabilities_bottleneck_and_bluetooth_foundation():
    # 1. Test Thunderbolt dynamic device map
    tb_map = get_thunderbolt_device_map()
    assert isinstance(tb_map, dict)
    # On M4 Pro with connected nodes, 1 or 3 should map to MBP or MBA
    if tb_map:
        for receptacle, dev_info in tb_map.items():
            assert "device_name" in dev_info
            assert "device_id" in dev_info

    # 2. Test Bluetooth anchor map
    bt_map = get_bluetooth_anchor_map()
    assert isinstance(bt_map, dict)
    assert "l1_mac_mini" in bt_map
    assert bt_map["l1_mac_mini"]["is_anchor"] is True
    assert bt_map["l1_mac_mini"]["status"] == "Host Controller Active"

    # 3. Test bottleneck evaluation logic
    # Scenario A: Samsung S20 (5 Gbps capable) on 480 Mbps USB 2.0 link
    s20_eval = evaluate_bottleneck_and_transfer(
        device_id="l7_samsung_s20",
        port_name="Port-USB-C@2",
        cable_type="USB-C E-Marker Smart Cable",
        negotiated_gbps=0.48,
        negotiated_speed_str="480 Mbps (High Speed USB 2.0)",
        cable_max_gbps=0.48,
        vendor_warning="Cable running in USB 2.0 High Speed mode (480 Mbps)."
    )
    assert s20_eval["bottleneck_analysis"]["is_bottleneck"] is True
    assert s20_eval["bottleneck_analysis"]["severity"] in ("CRITICAL", "WARNING")
    assert "Wi-Fi 6" in s20_eval["best_transfer_method"]["optimal_method"]
    assert "2.5x" in s20_eval["best_transfer_method"]["speed_multiplier"]
    assert "faster" in s20_eval["best_transfer_method"]["speed_multiplier"]

    # Scenario B: MacBook Pro (40 Gbps capable) on 40 Gbps TB4 link
    mbp_eval = evaluate_bottleneck_and_transfer(
        device_id="l2_macbook_pro",
        port_name="Port-USB-C@3",
        cable_type="Thunderbolt 4 / USB4 Smart E-Marker Cable",
        negotiated_gbps=40.0,
        negotiated_speed_str="40.0 Gbps",
        cable_max_gbps=40.0,
        vendor_warning=None
    )
    assert mbp_eval["bottleneck_analysis"]["is_bottleneck"] is False
    assert mbp_eval["bottleneck_analysis"]["severity"] == "OPTIMAL"
    assert "Thunderbolt 4" in mbp_eval["best_transfer_method"]["optimal_method"]

    # 4. Verify all cables produced by probe_all_cables include the new fields
    cables = probe_all_cables()
    for c in cables:
        assert "device_capabilities" in c
        assert "bluetooth_foundation" in c
        assert "best_transfer_method" in c
        assert "bottleneck_analysis" in c

@pytest.mark.asyncio
async def test_reverse_engineering_targets_and_curriculum():
    from config import REVERSE_ENGINEERING_TARGETS
    from server import api_reverse_engineering_targets
    import json

    # 1. Verify WhatCable target configuration
    assert "whatcable_vdm_emarker_decoder" in REVERSE_ENGINEERING_TARGETS
    wc = REVERSE_ENGINEERING_TARGETS["whatcable_vdm_emarker_decoder"]
    assert wc["id"] == "TASK-RE-04"
    assert "SOP'" in wc["name"] or "VDM" in wc["name"]
    assert "in-process" in wc["feature_value"].lower() or "eliminates" in wc["feature_value"].lower()
    assert len(wc["target_subprotocols"]) >= 4
    assert "Local Spec Model" in wc["assigned_models"]["tier_a_spec"] or "8082" in wc["assigned_models"]["tier_a_spec"]

    # 2. Verify Shark Wire target configuration
    assert "sharkwire_link_frame_dissector" in REVERSE_ENGINEERING_TARGETS
    sw = REVERSE_ENGINEERING_TARGETS["sharkwire_link_frame_dissector"]
    assert sw["id"] == "TASK-RE-05"
    assert "CRC" in sw["category"] or "Wire" in sw["category"]
    assert "wire health" in sw["feature_value"].lower() or "crc" in sw["feature_value"].lower()
    assert len(sw["target_subprotocols"]) >= 4
    assert "Rust" in sw["clean_room_language"]

    # 3. Verify API endpoint actuation
    response = await api_reverse_engineering_targets()
    assert response.status_code == 200
    data = json.loads(response.body.decode("utf-8"))
    assert data["status"] == "active_curriculum"
    assert "whatcable_vdm_emarker_decoder" in data["targets"]
    assert "sharkwire_link_frame_dissector" in data["targets"]

def test_network_diagnostics_ping_and_jitter():
    from probes.network_diagnostics import run_ping_test
    res = run_ping_test("127.0.0.1", count=3)
    assert res["host"] == "127.0.0.1"
    assert res["packets_transmitted"] == 3
    assert res["packets_received"] > 0
    assert res["packet_loss_pct"] == 0.0
    assert res["min_rtt_ms"] >= 0.0
    assert res["avg_rtt_ms"] >= 0.0
    assert res["jitter_ms"] >= 0.0
    assert len(res["rtt_samples"]) > 0
    assert res["status"] == "PASS"

def test_network_diagnostics_port_scan():
    from probes.network_diagnostics import run_mesh_port_scan
    res = run_mesh_port_scan("127.0.0.1", custom_ports=[4003, 12345])
    assert res["host"] == "127.0.0.1"
    assert res["total_ports_scanned"] == 2
    ports_map = {p["port"]: p for p in res["ports"]}
    assert 4003 in ports_map
    assert 12345 in ports_map
    assert ports_map[4003]["is_open"] is True
    assert ports_map[12345]["is_open"] is False

def test_cpdt_storage_and_memory_benchmark():
    from probes.network_diagnostics import run_storage_memory_benchmark
    res = run_storage_memory_benchmark()
    assert "ram_benchmark" in res
    assert "disk_benchmark" in res
    ram = res["ram_benchmark"]
    disk = res["disk_benchmark"]
    assert ram["tested_size_mb"] == 64
    assert ram["ram_bandwidth_gb_per_sec"] > 0
    assert "performance_rating" in ram
    assert disk["tested_size_mb"] == 16
    assert disk["sequential_write_mbps"] > 0
    assert disk["sequential_read_mbps"] > 0
    assert disk["io_type"] == "Direct fsync Unbuffered"

def test_battery_charging_probe():
    from probes.network_diagnostics import probe_mobile_battery_charging
    res = probe_mobile_battery_charging("100.73.38.87:5555")
    assert "device" in res
    assert "status" in res
    if res["status"] == "ONLINE":
        assert "battery_level_pct" in res
        assert "voltage_v" in res
        assert "instant_power_watts" in res
        assert "temperature_c" in res

@pytest.mark.asyncio
async def test_diagnostics_api_endpoints():
    import json
    from server import (
        api_diagnostics_ping,
        api_diagnostics_port_scan,
        api_diagnostics_benchmark,
        api_diagnostics_power_delivery
    )
    # 1. Ping endpoint
    p_res = await api_diagnostics_ping("127.0.0.1", count=2)
    assert p_res.status_code == 200
    p_data = json.loads(p_res.body.decode("utf-8"))
    assert p_data["status"] == "PASS"

    # 2. Port scan endpoint
    ps_res = await api_diagnostics_port_scan("127.0.0.1")
    assert ps_res.status_code == 200
    ps_data = json.loads(ps_res.body.decode("utf-8"))
    assert ps_data["total_ports_scanned"] > 0

    # 3. Benchmark endpoint
    bm_res = await api_diagnostics_benchmark()
    assert bm_res.status_code == 200
    bm_data = json.loads(bm_res.body.decode("utf-8"))
    assert "ram_benchmark" in bm_data

    # 4. Power delivery endpoint
    pd_res = await api_diagnostics_power_delivery("100.73.38.87:5555")
    assert pd_res.status_code == 200
    pd_data = json.loads(pd_res.body.decode("utf-8"))
    assert "device" in pd_data

def test_macbook_air_online_and_dynamic_discovery():
    """Verify MacBook Air M4 reports online and dynamic peers like sentinel are auto-discovered."""
    from probes.dynamic_ip_finder import find_dynamic_mesh_ips
    from probes.ram_npu_probe import probe_all_devices_ram_npu
    from config import get_dynamic_mesh_nodes

    ip_data = find_dynamic_mesh_ips(force=True)
    nodes = ip_data["nodes"]
    
    # 1. MacBook Air M4 online verification
    assert "l5_macbook_air" in nodes
    mba = nodes["l5_macbook_air"]
    assert mba["tailscale_ip"] == "100.121.202.34"
    assert mba["local_ip"].startswith("192.168.8.")
    assert mba["online"] is True, "MacBook Air M4 must be detected ONLINE via multi-factor reachability"

    # 2. Canonical mesh discovery (including 9 nodes)
    assert len(nodes) >= 8
    assert "l8_linux_mini" in nodes or "node_lauburu_sentinel_node" in nodes
    if "node_lauburu_sentinel_node" in nodes:
        sentinel = nodes["node_lauburu_sentinel_node"]
        assert sentinel["tailscale_ip"] == "100.85.182.55"

    # 3. Dynamic mesh nodes merging in config
    dynamic_nodes = get_dynamic_mesh_nodes(force=True)
    assert len(dynamic_nodes) >= 8

    # 4. RAM & NPU probe verification
    ram_npu = probe_all_devices_ram_npu()
    assert "l5_macbook_air" in ram_npu
    assert ram_npu["l5_macbook_air"]["online"] is True
    assert ram_npu["l5_macbook_air"]["ram"]["total_gb"] == 16.0
    assert ram_npu["l5_macbook_air"]["npu"]["max_tops"] == 38.0

def test_prima_mesh_status_probe():
    """Verify prima.cpp status probe accurately assesses ring and worker connectivity."""
    from probes.prima_probe import probe_prima_mesh_status
    status = probe_prima_mesh_status()
    assert "all_devices_connected" in status
    assert "connected_nodes_count" in status
    assert "total_nodes_count" in status
    assert "sovereign_duo" in status
    assert "local_triumvirate" in status

    # L1 Sovereign Master Orchestrator must be online
    assert status["sovereign_duo"]["master_orchestrator_8082"]["online"] is True
    assert status["sovereign_duo"]["master_orchestrator_8082"]["port"] == 8082
    assert "red_team_auditor_8083" in status["sovereign_duo"]
    # Verify accurate empirical count
    assert status["connected_nodes_count"] >= 2
    # L1 must be connected
    assert status["nodes"]["l1_mac_mini"]["connected_to_prima"] is True

@pytest.mark.asyncio
async def test_prima_api_endpoint():
    """Verify /api/prima/status returns valid JSON and accurate connectivity."""
    import json
    from server import api_prima_status
    res = await api_prima_status()
    assert res.status_code == 200
    data = json.loads(res.body.decode("utf-8"))
    assert "all_devices_connected" in data
    assert "answer_summary" in data
    assert len(data["nodes"]) >= 8


def test_bluetooth_terminal_pull_all_direct():
    """Verify pull_all_from_bluetooth_terminal directly ingests authentic metrics from Port 4005."""
    res = pull_all_from_bluetooth_terminal(force=True)
    assert res["telemetry_source"] == "BLUETOOTH_TERMINAL_DIRECT_LAYER_0"
    assert res["terminal_connection"] == "CONNECTED"
    assert res["daemon_port"] == 4005
    assert res["nodes_count"] >= 7, f"Expected at least 7 mesh nodes from BT terminal, got {res['nodes_count']}"
    assert res["cables_count"] >= 8, f"Expected at least 8 cables from BT terminal, got {res['cables_count']}"

    nodes = res["nodes"]
    assert "l1_mac_mini" in nodes
    assert "l7_samsung_s20" in nodes
    assert "l3_linux_head" in nodes
    assert "l2_macbook_pro" in nodes

    # L1 Host
    l1 = nodes["l1_mac_mini"]
    assert l1["ram"]["total_gb"] == 24.0
    assert l1["online"] is True
    assert l1["data_source"] == "BLUETOOTH_TERMINAL_DIRECT_STREAM"
    assert l1["bluetooth_terminal_verified"] is True

    # S20+ via Kai Morich
    s20 = nodes["l7_samsung_s20"]
    assert s20["online"] is True
    assert "Kai Morich" in s20.get("terminal_app", "")
    assert s20["ram"]["total_gb"] >= 10.0
    assert s20["data_source"] == "BLUETOOTH_TERMINAL_DIRECT_STREAM"
    assert s20["bluetooth_terminal_verified"] is True


def test_bluetooth_terminal_node_parsing():
    """Verify deterministic parsing of NODE: stream from Bluetooth serial terminal."""
    raw = (
        "NODE: l1_mac_mini | NAME: Mac Mini M4 Pro | ROLE: Primary Host | "
        "RAM_TOTAL: 24.0 | RAM_USED: 18.5 | RAM_AVAIL: 5.5 | NPU: 38.0 (Apple ANE 16-Core) | "
        "LINK: TB4/GbE/Wi-Fi 7 | BT: CONTROLLER (1c-f6-4c-81-0b-28) | STATUS: HOST_ACTIVE\n"
        "NODE: l7_samsung_s20 | NAME: Samsung Galaxy S20+ | MODEL: SM-G986B | "
        "RAM_TOTAL: 10.65 | RAM_USED: 5.73 | RAM_AVAIL: 4.92 | NPU: 10.0 (Exynos 990 NPU) | "
        "BATTERY_PCT: 84 | BATTERY_MV: 4122 | TEMP_C: 29.4 | LINK: USB-C@2 | "
        "BT: CONNECTED | TERMINAL: Kai Morich v1.52 | STATUS: ONLINE"
    )
    nodes = parse_terminal_nodes(raw)
    assert len(nodes) == 2
    assert "l1_mac_mini" in nodes
    assert nodes["l1_mac_mini"]["ram"]["total_gb"] == 24.0
    assert nodes["l1_mac_mini"]["ram"]["available_gb"] == 5.5
    assert nodes["l1_mac_mini"]["npu"]["max_tops"] == 38.0
    assert "Apple ANE" in nodes["l1_mac_mini"]["npu"]["name"]

    assert "l7_samsung_s20" in nodes
    s20 = nodes["l7_samsung_s20"]
    assert s20["model"] == "SM-G986B"
    assert s20["battery"]["level_pct"] == 84
    assert s20["battery"]["voltage_mv"] == 4122
    assert s20["battery"]["temp_c"] == 29.4
    assert s20["terminal_app"] == "Kai Morich v1.52"


def test_bluetooth_terminal_cable_parsing():
    """Verify deterministic parsing of CABLE: stream from Bluetooth serial terminal."""
    raw = (
        "CABLE: cable_tb4 | SOURCE: l1_mac_mini | TARGET: l2_macbook_pro | NAME: TB4 Cable | "
        "BANDWIDTH_GBPS: 40.0 | RTT_MS: 0.43 | BOTTLENECK: false | TRANSFER_METHOD: Thunderbolt 4 PCIe DMA | "
        "RECOMMENDATION: Optimal high-throughput 40Gbps DMA bridge.\n"
        "CABLE: cable_s20_usb2 | SOURCE: l1_mac_mini | TARGET: l7_samsung_s20 | NAME: USB 2.0 Cable | "
        "BANDWIDTH_GBPS: 0.48 | RTT_MS: 1.2 | BOTTLENECK: true | TRANSFER_METHOD: USB 3.2 Gen 2 Direct | "
        "RECOMMENDATION: S20 bottlenecked by USB 2.0 cable."
    )
    cables = parse_terminal_cables(raw)
    assert len(cables) == 2
    tb4 = cables[0]
    assert tb4["id"] == "cable_tb4"
    assert tb4["max_bandwidth_gbps"] == 40.0
    assert tb4["is_bottleneck"] is False
    assert tb4["data_source"] == "BLUETOOTH_TERMINAL_DIRECT_STREAM"

    s20_c = cables[1]
    assert s20_c["id"] == "cable_s20_usb2"
    assert s20_c["max_bandwidth_gbps"] == 0.48
    assert s20_c["is_bottleneck"] is True
    assert s20_c["bottleneck_analysis"]["severity"] == "CRITICAL_BOTTLENECK"


def test_bluetooth_terminal_power_parsing():
    """Verify deterministic parsing of DEVICE: power stream from Bluetooth serial terminal."""
    raw = (
        "DEVICE: l7_samsung_s20 | LEVEL: 84% | VOLTAGE_MV: 4122 | TEMP_C: 29.4 | "
        "STATUS: Fast Charging / USB-PD Active | WATTAGE: 18.5W | PROTOCOL: USB-PD 3.0 PPS\n"
        "DEVICE: l1_mac_mini | POWER_SOURCE: AC Line Power (100-240V) | "
        "STATUS: Nominal Line Power | WATTAGE: 34.2W | PROTOCOL: Internal 150W PSU"
    )
    power = parse_terminal_power(raw)
    assert "l7_samsung_s20" in power
    assert power["l7_samsung_s20"]["wattage"] == "18.5W"
    assert power["l7_samsung_s20"]["protocol"] == "USB-PD 3.0 PPS"
    assert power["l7_samsung_s20"]["level"] == "84%"

    assert "l1_mac_mini" in power
    assert power["l1_mac_mini"]["wattage"] == "34.2W"


def test_topology_fuses_bluetooth_terminal_layer_0():
    """Verify build_full_topology fuses Bluetooth terminal data as master ground truth."""
    topo = build_full_topology(force_ai=False)
    summary = topo["mesh_summary"]
    assert summary["telemetry_source"] == "BLUETOOTH_TERMINAL_DIRECT_LAYER_0"
    assert summary["bluetooth_terminal_status"] in ("CONNECTED", "--")
    assert summary["bluetooth_terminal_verified_nodes"] >= 7
    assert summary["bluetooth_terminal_verified_cables"] >= 6
    assert "Hermes" in summary["local_ai_model"] or "Llama" in summary["local_ai_model"] or "8090" in summary["local_ai_model"] or "qwen" in summary["local_ai_model"].lower()
    assert "bluetooth_terminal_direct" in topo

    # Check verified nodes
    bt_nodes = [d for d in topo["devices"] if d.get("bluetooth_terminal_verified")]
    assert len(bt_nodes) >= 7
    for n in bt_nodes:
        assert n["data_source"] == "BLUETOOTH_TERMINAL_DIRECT_STREAM"

    # Check verified cables
    bt_cables = [c for c in topo["cables"] if c.get("bluetooth_terminal_verified")]
    assert len(bt_cables) >= 6
    for c in bt_cables:
        assert c["data_source"] == "BLUETOOTH_TERMINAL_DIRECT_STREAM"


@pytest.mark.asyncio
async def test_terminal_telemetry_api_endpoints():
    """Verify the 5 new Bluetooth terminal REST endpoints on the server."""
    import json
    from server import (
        api_terminal_telemetry,
        api_terminal_devices,
        api_terminal_cables,
        api_terminal_power,
        api_terminal_pull
    )

    # /api/terminal/telemetry
    res_tel = await api_terminal_telemetry(force=False)
    assert res_tel.status_code == 200
    data_tel = json.loads(res_tel.body.decode("utf-8"))
    assert data_tel["telemetry_source"] == "BLUETOOTH_TERMINAL_DIRECT_LAYER_0"
    assert data_tel["nodes_count"] >= 7
    assert data_tel["cables_count"] >= 8

    # /api/terminal/devices
    res_dev = await api_terminal_devices(force=False)
    assert res_dev.status_code == 200
    data_dev = json.loads(res_dev.body.decode("utf-8"))
    assert "l1_mac_mini" in data_dev
    assert "l7_samsung_s20" in data_dev

    # /api/terminal/cables
    res_cab = await api_terminal_cables(force=False)
    assert res_cab.status_code == 200
    data_cab = json.loads(res_cab.body.decode("utf-8"))
    assert isinstance(data_cab, list)
    assert len(data_cab) >= 8

    # /api/terminal/power
    res_pwr = await api_terminal_power(force=False)
    assert res_pwr.status_code == 200
    data_pwr = json.loads(res_pwr.body.decode("utf-8"))
    assert "l1_mac_mini" in data_pwr

    # /api/terminal/pull
    res_pull = await api_terminal_pull()
    assert res_pull.status_code == 200
    data_pull = json.loads(res_pull.body.decode("utf-8"))
    assert data_pull["status"] == "pulled_from_bluetooth_terminal"
    assert data_pull["telemetry_source"] == "BLUETOOTH_TERMINAL_DIRECT_LAYER_0"
    assert "topology" in data_pull


def test_active_connections_individual_probes():
    """Verify each of the 6 active connection probes returns authentic data."""
    # 1. Bluetooth
    bt_res = probe_active_bluetooth_connections()
    assert isinstance(bt_res, dict)
    assert bt_res["category"] == "bluetooth"
    bt_conns = bt_res["connections"]
    assert isinstance(bt_conns, list)
    for c in bt_conns:
        assert "transport" in c
        assert c["status"] in ("connected", "paired", "standby")

    # 2. SSH
    ssh_res = probe_active_ssh_connections()
    assert isinstance(ssh_res, dict)
    assert ssh_res["category"] == "ssh"
    ssh_conns = ssh_res["connections"]
    assert isinstance(ssh_conns, list)
    for c in ssh_conns:
        assert "endpoint" in c
        assert c["state"] in ("ESTABLISHED", "LISTENING", "ACTIVE")

    # 3. Tailscale
    ts_res = probe_active_tailscale_connections()
    assert isinstance(ts_res, dict)
    assert ts_res["category"] == "tailscale"
    ts_conns = ts_res["connections"]
    assert isinstance(ts_conns, list)
    assert len(ts_conns) > 0, "Tailscale should report active peers"
    for c in ts_conns:
        assert "endpoint" in c
        assert "transport" in c

    # 4. Wi-Fi Multi-Band / MLO
    wifi_res = probe_active_wifi_connections()
    assert isinstance(wifi_res, dict)
    assert wifi_res["category"] == "wifi"
    wifi_conns = wifi_res["connections"]
    assert isinstance(wifi_conns, list)
    assert len(wifi_conns) > 0, "Host must report active Wi-Fi interface (en1)"
    wifi = wifi_conns[0]
    assert "channel" in wifi
    assert "band" in wifi
    assert "ssid" in wifi
    assert "transport" in wifi
    assert "Wi-Fi" in wifi["transport"] or "MLO" in wifi["transport"]

    # 5. USB
    usb_res = probe_active_usb_connections()
    assert isinstance(usb_res, dict)
    assert usb_res["category"] == "usb"
    usb_conns = usb_res["connections"]
    assert isinstance(usb_conns, list)
    assert len(usb_conns) > 0, "USB hierarchy must report connected devices/hubs"
    for c in usb_conns:
        assert "speed" in c or "bandwidth" in c
        assert "transport" in c

    # 6. Thunderbolt
    tb_res = probe_active_thunderbolt_connections()
    assert isinstance(tb_res, dict)
    assert tb_res["category"] == "thunderbolt"
    tb_conns = tb_res["connections"]
    assert isinstance(tb_conns, list)
    assert len(tb_conns) > 0, "Thunderbolt bridge0 must be detected"
    tb = tb_conns[0]
    assert "bridge0" in tb["interface"]
    assert tb_res["dma_rtt_latency_ms"] is not None
    assert tb_res["dma_rtt_latency_ms"] < 5.0, "TB4 bridge RTT must be low-latency"


def test_get_all_active_connections_aggregation():
    """Verify get_all_active_connections aggregates all 6 categories."""
    data = get_all_active_connections(force=True)
    assert "timestamp" in data
    assert "total_active_connections" in data
    assert "categories_active" in data
    assert data["total_active_connections"] >= 6
    assert data["categories_active"] >= 4

    summary = data["summary"]
    assert "bluetooth" in summary
    assert "ssh" in summary
    assert "tailscale" in summary
    assert "wifi" in summary
    assert "usb" in summary
    assert "thunderbolt" in summary

    conns = data["connections"]
    assert isinstance(conns["bluetooth"], list)
    assert isinstance(conns["ssh"], list)
    assert isinstance(conns["tailscale"], list)
    assert isinstance(conns["wifi"], list)
    assert isinstance(conns["usb"], list)
    assert isinstance(conns["thunderbolt"], list)


def test_mesh_topology_includes_active_connections():
    """Verify build_full_topology embeds active_connections and summary metrics."""
    topo = build_full_topology(force_ai=False)
    assert "active_connections" in topo
    ac = topo["active_connections"]
    assert ac["total_active_connections"] >= 6
    assert ac["categories_active"] >= 4

    ms = topo["mesh_summary"]
    assert "active_connections_total" in ms
    assert "active_categories_count" in ms
    assert ms["active_connections_total"] == ac["total_active_connections"]
    assert ms["active_categories_count"] == ac["categories_active"]


@pytest.mark.asyncio
async def test_active_connections_api_endpoints():
    """Verify FastAPI endpoints for active connections."""
    import json
    from server import api_connections_active, api_connections_category

    # /api/connections/active
    res_all = await api_connections_active(force=False)
    assert res_all.status_code == 200
    data_all = json.loads(res_all.body.decode("utf-8"))
    assert "total_active_connections" in data_all
    assert data_all["total_active_connections"] >= 6
    assert data_all["categories_active"] >= 4

    # Test each category endpoint
    for cat in ["bluetooth", "ssh", "tailscale", "wifi", "usb", "thunderbolt"]:
        res_cat = await api_connections_category(cat)
        assert res_cat.status_code == 200
        data_cat = json.loads(res_cat.body.decode("utf-8"))
        assert data_cat["category"] == cat
        assert isinstance(data_cat["connections"], list)

    # Test invalid category
    res_invalid = await api_connections_category("non_existent_category")
    assert res_invalid.status_code == 404







