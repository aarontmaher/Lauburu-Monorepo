"""
Empirical Adversarial Stress Test Suite for Native WhatCable Hardware & E-Marker Inspector Engine
Milestone M1 Verification & Robustness Harness

Tests:
  1. Corrupted or partial IOKit string inputs (empty, truncated, malformed regex patterns).
  2. Non-standard power profiles (0W, 15W, 60W, 100W, 140W, 240W EPR, substring traps like '0.5 A').
  3. DisplayPort bandwidth deficits (negative headroom, 8K 48 Gbps on 1080p link, zero-delivered dead links).
  4. Bottleneck severity transitions and edge cases (CRITICAL, WARNING, INFO, OPTIMAL, None fields).
  5. Zero crashes, zero memory leaks, zero NaN values.
"""

import gc
import json
import math
import sys
import tracemalloc
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import probes.whatcable_inspector as wci


# ==============================================================================
# Helper Assertions & Validators
# ==============================================================================

def assert_no_nan_or_inf(obj: Any, path: str = "root"):
    """Recursively assert that no float in the object tree is NaN or Inf."""
    if isinstance(obj, float):
        assert not math.isnan(obj), f"NaN detected at {path}"
        assert not math.isinf(obj), f"Inf detected at {path}"
    elif isinstance(obj, dict):
        for k, v in obj.items():
            assert_no_nan_or_inf(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            assert_no_nan_or_inf(item, f"{path}[{i}]")


# ==============================================================================
# SECTION 1: Corrupted or Partial IOKit String Inputs
# ==============================================================================

class TestCorruptedOrPartialIOKitInputs:
    """Stress-tests parsing robustness against corrupted, truncated, or malformed IOKit strings."""

    @pytest.mark.parametrize("corrupt_out", [
        "",
        "   \n\t  \n  ",
        "GARBAGE TEXT WITHOUT IOKIT HEADERS",
        "+-o Port-USB-C",  # Missing @receptacle
        "+-o Port-USB-C@abc\n   |   \"ConnectionActive\" = Yes",  # Non-numeric receptacle
        "+-o Port-USB-C@999\n   |   \"ConnectionActive\" = Yes",  # Out of range receptacle
        "+-o Port-USB-C@1\n   |   \"ConnectionActive\" = Yes\n+-o SOP'\n   |   \"Vendor ID\" = NOT_A_NUMBER",
        "+-o Port-USB-C@2\n   |   \"TransportsActive\" = (\"CIO\")\n+-o SOP'\n   |   \"VDOs\" = (INVALID_VDO_CHARS)",
        "+-o Port-USB-C@3\n   |   \"ConnectionActive\" = No\n   |   \"TransportsActive\" = ()",
        "+-o DisplayPort\n   |   \"LinkRateDescription\" = \"GARBAGE_RATE\"\n   |   \"LaneCount\" = 0",
        "+-o DisplayPort\n   |   \"ParentBuiltInPortNumber\" = abc\n   |   \"LinkRateDescription\" = \"8.1 Gbps\"",
    ])
    def test_iokit_raw_output_fuzz_never_crashes(self, corrupt_out):
        """Verify probe_via_darwin_iokit survives corrupted raw IOKit outputs."""
        with patch.object(wci, "run_command", return_value=(0, corrupt_out, "")):
            res = wci.probe_via_darwin_iokit()
            assert isinstance(res, dict)
            assert "ports" in res
            assert "display_ports" in res
            assert isinstance(res["ports"], list)
            assert isinstance(res["display_ports"], list)
            assert_no_nan_or_inf(res)

    @pytest.mark.parametrize("corrupt_json_str", [
        "",
        "[]",
        "42",
        "null",
        "\"unexpected string\"",
        "{\"ports\": null}",
        "{\"ports\": [{\"name\": null, \"status\": null, \"cable\": null}]}",
        "{\"ports\": [{\"name\": \"Port-USB-C@1\", \"cable\": {\"maxWatts\": null, \"maxVolts\": null}}]}",
        "{\"ports\": [{\"name\": \"Port-USB-C@2\", \"dataLink\": {\"negotiated_gbps\": null}}]}",
        "{\"builtInDisplayPorts\": null}",
        "{\"builtInDisplayPorts\": [{\"name\": null, \"displays\": null}]}",
        "{\"builtInDisplayPorts\": [{\"displays\": [{\"deliveredGbps\": null, \"neededGbps\": null}]}]}",
    ])
    def test_whatcable_cli_json_fuzz_never_crashes(self, corrupt_json_str):
        """
        Verify probe_whatcable_hardware_details recovers gracefully from
        malformed or corrupt CLI JSON outputs without unhandled exceptions.
        """
        def mock_run_cmd(cmd, *args, **kwargs):
            if "whatcable" in cmd[0]:
                return 0, corrupt_json_str, ""
            return 0, "", ""

        with patch.object(wci, "run_command", side_effect=mock_run_cmd):
            try:
                res = wci.probe_whatcable_hardware_details(force=True)
                assert isinstance(res, dict)
                assert res.get("status") == "success"
                assert "summary" in res
                assert_no_nan_or_inf(res)
            except (TypeError, AttributeError) as exc:
                pytest.fail(f"VULNERABILITY: probe_whatcable_hardware_details crashed on corrupt JSON '{corrupt_json_str}': {exc}")

    def test_system_profiler_thunderbolt_malformed_json(self):
        """Verify get_thunderbolt_device_details handles corrupted system_profiler JSON."""
        with patch.object(wci, "run_command", return_value=(0, '{"SPThunderboltDataType": [{"_items": null, "receptacle_1_tag": null}]}', "")):
            tb_map = wci.get_thunderbolt_device_details()
            assert isinstance(tb_map, dict)


# ==============================================================================
# SECTION 2: Non-Standard Power Profiles
# ==============================================================================

class TestPowerProfiles:
    """Stress-tests USB-PD power profile calculation and USB-PD 3.1 EPR compliance."""

    def test_power_profile_standard_60w_spr(self):
        """Verify standard 60W SPR profile (20V / 3A)."""
        pd = wci.parse_power_delivery(max_watts=60, max_volts=20, current_rating="3 A")
        assert pd["max_wattage"] == 60
        assert pd["max_voltage"] == 20
        assert pd["max_current_amperes"] == 3.0
        assert pd["pd_range"] == "SPR (Standard Power Range 60W)"
        assert pd["pps_supported"] is True
        assert "60W SPR" in pd["rating_label"]

    def test_power_profile_standard_100w_spr(self):
        """Verify standard 100W SPR profile (20V / 5A)."""
        pd = wci.parse_power_delivery(max_watts=100, max_volts=20, current_rating="5 A")
        assert pd["max_wattage"] == 100
        assert pd["max_voltage"] == 20
        assert pd["max_current_amperes"] == 5.0
        assert pd["pd_range"] == "SPR (Standard Power Range 100W)"
        assert pd["pps_supported"] is True
        assert "100W SPR" in pd["rating_label"]

    def test_power_profile_240w_epr(self):
        """Verify USB-PD 3.1 Extended Power Range (EPR) 240W profile (50V / 5A)."""
        pd = wci.parse_power_delivery(max_watts=240, max_volts=50, current_rating="5 A")
        assert pd["max_wattage"] == 240
        assert pd["max_voltage"] == 50
        assert pd["max_current_amperes"] == 5.0
        assert pd["pd_range"] == "EPR (Extended Power Range 240W)"
        assert pd["pps_supported"] is True
        assert "240W Extended Power" in pd["rating_label"]

    def test_power_profile_0w_unpowered_passive(self):
        """Verify unpowered / 0W passive cable profile."""
        pd = wci.parse_power_delivery(max_watts=0, max_volts=0, current_rating="0 A")
        assert pd["max_wattage"] == 0
        assert pd["max_voltage"] == 0
        assert pd["max_current_amperes"] == 0.0
        assert pd["pd_range"] == "Unadvertised / Bus Power"
        assert pd["pps_supported"] is False

    @pytest.mark.parametrize("watts,volts,curr_str,expected_label_part", [
        (15, 5, "3 A", "15W"),
        (27, 9, "3 A", "27W"),
        (45, 15, "3 A", "45W"),
        (140, 28, "5 A", "140W"),
    ])
    def test_power_profile_intermediate_wattages(self, watts, volts, curr_str, expected_label_part):
        """Verify intermediate wattages like 15W, 27W, 45W, 140W EPR."""
        pd = wci.parse_power_delivery(max_watts=watts, max_volts=volts, current_rating=curr_str)
        assert pd["max_wattage"] == watts
        assert expected_label_part in pd["rating_label"]
        assert_no_nan_or_inf(pd)

    def test_power_profile_substring_bug_detection(self):
        """
        EMPIRICAL CHALLENGE: Detect the substring matching trap where '0.5 A'
        triggers '5 in curr_str' and erroneously escalates to 100W SPR!
        """
        pd = wci.parse_power_delivery(max_watts=0, max_volts=0, current_rating="0.5 A")
        # In a sound implementation, a 0.5A device with 0W must NOT be marked as 100W SPR!
        if pd["pd_range"] == "SPR (Standard Power Range 100W)":
            pytest.fail(
                "VULNERABILITY DETECTED: '0.5 A' current rating matched '5 in curr_str', "
                f"causing 0W cable to be misclassified as '{pd['pd_range']}' ({pd['rating_label']})!"
            )


# ==============================================================================
# SECTION 3: DisplayPort Bandwidth Deficits & Negative Headroom
# ==============================================================================

class TestDisplayPortBandwidthDeficits:
    """Stress-tests DisplayPort Alt Mode bandwidth mathematics and deficit alerts."""

    def test_dp_8k_48gbps_on_1080p_link_critical_bottleneck(self):
        """
        Challenge: 8K @ 60Hz requiring 48 Gbps connected over a 1080p HBR3 link
        delivering only 25.92 Gbps (deficit of -22.08 Gbps).
        Must trigger CRITICAL bottleneck.
        """
        disp = {
            "monitor_name": "ProArt 8K Monitor",
            "delivered_gbps": 25.92,
            "needed_gbps": 48.0,
            "headroom_gbps": -22.08
        }
        btn = wci.detect_display_bottleneck(disp)
        assert btn["is_bottleneck"] is True
        assert btn["severity"] == "CRITICAL"
        assert "bandwidth bottleneck" in btn["summary"].lower()

    def test_dp_moderate_deficit_warning_bottleneck(self):
        """
        Challenge: Delivered bandwidth is between 70% and 100% of needed bandwidth.
        Must trigger WARNING bottleneck.
        """
        disp = {
            "monitor_name": "4K High Refresh Monitor",
            "delivered_gbps": 20.0,
            "needed_gbps": 24.0,  # 20.0 / 24.0 = 83.3% (> 70%, < 100%)
            "headroom_gbps": -4.0
        }
        btn = wci.detect_display_bottleneck(disp)
        assert btn["is_bottleneck"] is True
        assert btn["severity"] == "WARNING"

    def test_dp_exact_zero_headroom_optimal(self):
        """
        Challenge: Delivered bandwidth exactly matches needed bandwidth (0.0 headroom).
        Must be OPTIMAL (no bottleneck).
        """
        disp = {
            "monitor_name": "Studio Display",
            "delivered_gbps": 25.92,
            "needed_gbps": 25.92,
            "headroom_gbps": 0.0
        }
        btn = wci.detect_display_bottleneck(disp)
        assert btn["is_bottleneck"] is False
        assert btn["severity"] == "OPTIMAL"

    def test_dp_dead_link_zero_delivered_bandwidth_alert(self):
        """
        EMPIRICAL CHALLENGE: When a display is connected but link rate / lanes are 0
        (delivered_gbps = 0.0, needed_gbps = 8.16), the system should NOT report OPTIMAL!
        A 0 Gbps link is a disconnected / dead display link, not 'running at full quality'.
        """
        disp = {
            "monitor_name": "External Display",
            "delivered_gbps": 0.0,
            "needed_gbps": 8.16,
            "headroom_gbps": -8.16
        }
        btn = wci.detect_display_bottleneck(disp)
        if btn["severity"] == "OPTIMAL":
            pytest.fail(
                "VULNERABILITY DETECTED: detect_display_bottleneck reports OPTIMAL for a dead display "
                "link with delivered_gbps=0.0 and headroom=-8.16 Gbps!"
            )


# ==============================================================================
# SECTION 4: Bottleneck Severity Transitions & Edge Cases
# ==============================================================================

class TestBottleneckSeverityTransitions:
    """Stress-tests bottleneck detection rules, boundary values, and None handling."""

    def test_bottleneck_critical_high_speed_peer_collapsed(self):
        """Rule 1: High-speed peer (MacBook Pro) throttled to <= 5 Gbps -> CRITICAL."""
        btn = wci.detect_cable_bottleneck(
            port_id="Port-USB-C@1",
            status="thunderboltCable",
            headline="Connected Device",
            cable={"max_bandwidth_gbps": 40.0, "e_marker": True},
            data_link={"negotiated_gbps": 0.48},
            connected_device={"name": "MacBook Pro"},
            raw_datalink_bottleneck=None
        )
        assert btn["is_bottleneck"] is True
        assert btn["severity"] == "CRITICAL"

    def test_bottleneck_warning_charge_only_cable(self):
        """Rule 2: Slow USB or charge-only cable alert -> WARNING."""
        btn = wci.detect_cable_bottleneck(
            port_id="Port-USB-C@6",
            status="dataDevice",
            headline="Slow USB device or charge-only cable",
            cable={"max_bandwidth_gbps": 0.48, "e_marker": False},
            data_link={"negotiated_gbps": 0.48},
            connected_device=None,
            raw_datalink_bottleneck=None
        )
        assert btn["is_bottleneck"] is True
        assert btn["severity"] == "WARNING"

    def test_bottleneck_warning_cable_down_negotiation(self):
        """Rule 3: 20 Gbps cable on 40 Gbps capable link -> WARNING."""
        btn = wci.detect_cable_bottleneck(
            port_id="Port-USB-C@2",
            status="thunderboltCable",
            headline="Connected Device",
            cable={"max_bandwidth_gbps": 20.0, "e_marker": True},
            data_link={"negotiated_gbps": 20.0},
            connected_device={"name": "Connected Peer"},
            raw_datalink_bottleneck="cableLimit"
        )
        assert btn["is_bottleneck"] is True
        assert btn["severity"] == "WARNING"

    def test_bottleneck_info_40g_cable_headroom(self):
        """Rule 4: 40 Gbps cable on 80 Gbps TB5 port -> INFO."""
        btn = wci.detect_cable_bottleneck(
            port_id="Port-USB-C@1",
            status="thunderboltCable",
            headline="Connected Device",
            cable={"max_bandwidth_gbps": 40.0, "e_marker": True},
            data_link={"negotiated_gbps": 40.0},
            connected_device={"name": "MacBook Pro"},
            raw_datalink_bottleneck="cableLimit"
        )
        assert btn["is_bottleneck"] is True
        assert btn["severity"] == "INFO"

    def test_bottleneck_empty_port_optimal(self):
        """Rule 5: Disconnected / empty port -> OPTIMAL."""
        btn = wci.detect_cable_bottleneck(
            port_id="Port-USB-C@5",
            status="empty",
            headline="Nothing connected",
            cable=None,
            data_link=None,
            connected_device=None,
            raw_datalink_bottleneck=None
        )
        assert btn["is_bottleneck"] is False
        assert btn["severity"] == "OPTIMAL"

    def test_bottleneck_detect_handles_none_values_without_crash(self):
        """
        EMPIRICAL CHALLENGE: Verify detect_cable_bottleneck survives None values
        in dictionary fields without raising TypeError or AttributeError.
        """
        try:
            btn = wci.detect_cable_bottleneck(
                port_id="Port-USB-C@1",
                status="dataDevice",
                headline="Connected Device",
                cable={"max_bandwidth_gbps": None, "e_marker": None},
                data_link={"negotiated_gbps": None},
                connected_device={"name": None},
                raw_datalink_bottleneck=None
            )
            assert isinstance(btn, dict)
            assert "severity" in btn
        except (TypeError, AttributeError) as exc:
            pytest.fail(f"VULNERABILITY DETECTED: detect_cable_bottleneck crashed on None values: {exc}")


# ==============================================================================
# SECTION 5: Zero Crashes, Zero Memory Leaks, Zero NaNs
# ==============================================================================

class TestZeroCrashesZeroMemoryLeaksZeroNaNs:
    """Stress harness for memory stability, leak detection, and NaN immunity."""

    def test_zero_nans_in_live_hardware_probe(self):
        """Verify the live system probe returns zero NaN or Inf values across all nodes."""
        data = wci.probe_whatcable_hardware_details(force=True)
        assert_no_nan_or_inf(data)

    def test_zero_nans_in_display_bottleneck_evaluator(self):
        """Verify detect_display_bottleneck handles NaN gracefully without emitting NaN."""
        disp_nan = {
            "monitor_name": "Fuzzed Display",
            "delivered_gbps": float("nan"),
            "needed_gbps": 8.16,
            "headroom_gbps": float("nan")
        }
        btn = wci.detect_display_bottleneck(disp_nan)
        assert isinstance(btn, dict)
        assert_no_nan_or_inf(btn)

    def test_zero_memory_leaks_under_high_frequency_polling(self):
        """
        Stress harness: Execute 150 probe calls and verify memory allocation
        does not grow monotonically (leaks).
        """
        gc.collect()
        tracemalloc.start()
        snapshot_start = tracemalloc.take_snapshot()

        for _ in range(150):
            wci.probe_whatcable_hardware_details(force=False)

        gc.collect()
        snapshot_end = tracemalloc.take_snapshot()
        tracemalloc.stop()

        diff = snapshot_end.compare_to(snapshot_start, "lineno")
        total_growth_kb = sum(stat.size_diff for stat in diff if stat.size_diff > 0) / 1024.0

        # Memory growth across 150 cached calls should be negligible (< 100 KB)
        assert total_growth_kb < 100.0, f"Potential memory leak: grew by {total_growth_kb:.2f} KB"

    @pytest.mark.parametrize("speed_str", [
        "", "unknown", "1000 Mbps", "100 Mbps", "2.5 Gbps", "12 Mbps", "480 Mbps",
        "120 Gbps", "Thunderbolt 5", "SuperSpeed+ 10Gbps", "0.012 Gbps"
    ])
    def test_parse_speed_to_gbps_never_crashes(self, speed_str):
        """Verify speed string parser never crashes or emits NaN."""
        val = wci.parse_speed_to_gbps(speed_str)
        assert isinstance(val, float)
        assert not math.isnan(val)
        assert not math.isinf(val)
        assert val >= 0.0

    @pytest.mark.parametrize("vendor_id", [
        None, 0, -1, 11037, 11564, 1452, 999999, 0xFFFF
    ])
    def test_resolve_vendor_name_never_crashes(self, vendor_id):
        """Verify vendor name resolver never crashes on any integer or None."""
        name = wci.resolve_vendor_name(vendor_id)
        assert isinstance(name, str)
        assert len(name) > 0

    @pytest.mark.parametrize("speed_str,expected_gbps", [
        ("1000 Mbps", 1.0),
        ("100 Mbps", 0.1),
        ("2.5 Gbps", 2.5),
    ])
    def test_parse_speed_to_gbps_accurately_parses_sub_gigabit_and_fractional_speeds(self, speed_str, expected_gbps):
        """
        EMPIRICAL CHALLENGE: Detect substring matching traps where '1000 Mbps'
        or '100 Mbps' matches '10 in s' returning 10.0 Gbps instead of 1.0/0.1 Gbps,
        or '2.5 Gbps' matches '5 in s' returning 5.0 Gbps instead of 2.5 Gbps!
        """
        val = wci.parse_speed_to_gbps(speed_str)
        if val != expected_gbps:
            pytest.fail(
                f"VULNERABILITY DETECTED: parse_speed_to_gbps('{speed_str}') returned {val} Gbps "
                f"instead of {expected_gbps} Gbps due to raw substring matching!"
            )

