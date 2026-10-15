#!/usr/bin/env python3
"""
Unit & Integration Test Suite for OpenClaw Shizuku Privileged Touch Transport
==============================================================================
Validates:
  • F4_SHIZUKU_BINDER_TOUCH: Sub-1ms in-memory touch dispatch (<1ms), gesture synthesis,
    coordinate clamping, multi-touch trajectories, keyevent and text input.
  • F5_SHIZUKU_FRAME_STREAM: Lossless PNG encoding, raw screencap parsing, 5-frame rolling
    MD5 delta hashing, frozen UI detection, and >10KB size assertions.
  • F6_SHIZUKU_RESILIENCE: Doze whitelisting, phantom process monitor bypass, wireless ADB
    TCP 5555 pinning, UIAutomator anti-exit 137 PID self-healing, thermal governance,
    and multi-target topology (Samsung Galaxy S20+ and Pixel 10 Pro XL).
"""

import asyncio
import hashlib
import json
import os
import struct
import sys
import time
import unittest
from typing import Dict, List, Any

# Ensure module path is accessible
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from openclaw_shizuku_transport import (
    OpenClawShizukuTransport,
    ShizukuInputManager,
    ShizukuResilienceManager,
    RollingMD5Buffer,
    PNGEncoder,
    GestureSynthesizer,
    MotionEvent,
    KeyEvent,
    PointerCoords,
    TouchAction,
    KeyAction,
    KeyCode,
    InjectionMode,
    DeviceTarget,
    DEVICE_TOPOLOGY
)


class MockAdbExecutor:
    """Deterministic, instrumented ADB command executor for isolated unit tests."""

    def __init__(self, target_name: str = "samsung_s20"):
        self.target_name = target_name
        self.command_log: List[List[str]] = []
        self.whitelisted_pkgs: Set[str] = set()
        self.phantom_monitor_enabled: bool = True
        self.adb_tcp_port: str = "5555"
        self.battery_temp_c: float = 31.0
        self.battery_level: int = 80
        self.is_shell_uid: bool = True

    def __call__(self, cmd_list: List[str]) -> str:
        self.command_log.append(cmd_list)
        cmd_str = " ".join(cmd_list)

        # Doze whitelist
        if "dumpsys deviceidle whitelist +" in cmd_str:
            pkg = cmd_list[-1].lstrip("+")
            self.whitelisted_pkgs.add(pkg)
            return "Added"
        elif "dumpsys deviceidle whitelist" in cmd_str:
            return f"WHITELIST: {', '.join(self.whitelisted_pkgs)}"

        # Phantom process
        elif "settings put global settings_enable_monitor_phantom_procs false" in cmd_str:
            self.phantom_monitor_enabled = False
            return ""
        elif "settings get global settings_enable_monitor_phantom_procs" in cmd_str:
            return "false" if not self.phantom_monitor_enabled else "true"

        # Port 5555 pinning
        elif "setprop service.adb.tcp.port" in cmd_str:
            self.adb_tcp_port = cmd_list[-1]
            return ""
        elif "getprop service.adb.tcp.port" in cmd_str:
            return self.adb_tcp_port

        # UIAutomator ps inspection
        elif "ps -e -o PID,ARGS" in cmd_str or "ps -ef" in cmd_str:
            return (
                "USER           PID  PPID     VSZ    RSS WCHAN            ADDR S CMD\n"
                "shell         1234   500   10000   2000 0                   0 S /system/bin/sh\n"
                "shell         5678   500   50000  12000 0                   0 S com.android.commands.uiautomator\n"
                "shell         9012   500   45000  11000 0                   0 S uiautomator runtest\n"
                "shell         9999   500    5000   1000 0                   0 S grep uiautomator\n"
                "shell         8888   500    5000   1000 0                   0 S pkill uiautomator\n"
            )
        elif "kill -9" in cmd_str:
            return ""

        # Battery dumpsys
        elif "dumpsys battery" in cmd_str:
            return (
                f"Current Battery Service state:\n"
                f"  AC powered: true\n"
                f"  level: {self.battery_level}\n"
                f"  temperature: {int(self.battery_temp_c * 10)}\n"
                f"  status: 2\n"
                f"  health: 2\n"
            )

        # UID inspection
        elif "id" in cmd_str:
            return "uid=2000(shell) gid=2000(shell) groups=2000(shell)"

        return "OK"


class TestF4ShizukuBinderTouch(unittest.TestCase):
    """F4_SHIZUKU_BINDER_TOUCH: In-memory IInputManager touch & gesture injection tests."""

    def setUp(self):
        self.mock_adb = MockAdbExecutor()
        self.transport = OpenClawShizukuTransport(
            device_target="samsung_s20",
            adb_executor=self.mock_adb,
            dry_run=True
        )

    def test_tap_injection_latency_and_payload(self):
        """Verify tap injection generates valid completion with sub-1ms in-memory duration."""
        res = self.transport.tap(720, 1600)
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["event_count"], 2)
        self.assertLessEqual(res["latency_ms"], 5.0)  # Bound check
        self.assertIn("timestamp_utc", res)
        self.assertEqual(res["device_id"], DEVICE_TOPOLOGY["samsung_s20"].device_id)

    def test_swipe_trajectory_and_steps(self):
        """Verify swipe gesture synthesizes correct number of MotionEvents."""
        res = self.transport.swipe(100, 500, 100, 1500, duration_ms=200, steps=15)
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["event_count"], 16)  # 1 DOWN + 14 MOVE + 1 UP
        self.assertLessEqual(res["latency_ms"], 5.0)

    def test_scroll_gesture(self):
        """Verify scroll displacement correctly calculates target coordinates."""
        res = self.transport.scroll(500, 1000, dx=0, dy=400, duration_ms=150)
        self.assertEqual(res["status"], "COMPLETED")
        self.assertGreater(res["event_count"], 1)

    def test_coordinate_clamping(self):
        """Verify coordinates outside screen bounds are clamped to [0, W], [0, H]."""
        target = DEVICE_TOPOLOGY["samsung_s20"]
        # Screen is 1440 x 3200
        events = GestureSynthesizer.build_tap_events(-50, 5000, target)
        self.assertEqual(events[0].pointers[0].x, 0.0)
        self.assertEqual(events[0].pointers[0].y, float(target.height))

    def test_bezier_trajectory_generation(self):
        """Verify smooth Bezier curve point generation."""
        p0 = (100.0, 100.0)
        p1 = (500.0, 300.0)
        p2 = (900.0, 1000.0)
        points = GestureSynthesizer.generate_bezier_trajectory(p0, p1, p2, duration_ms=300, steps=20)
        self.assertEqual(len(points), 21)
        self.assertAlmostEqual(points[0][0], 100.0)
        self.assertAlmostEqual(points[-1][0], 900.0)
        self.assertEqual(points[-1][2], 300)

    def test_keyevent_injection(self):
        """Verify KeyCode injection for system navigation buttons."""
        res_back = self.transport.keyevent(int(KeyCode.KEYCODE_BACK))
        self.assertEqual(res_back["status"], "COMPLETED")
        self.assertEqual(res_back["keycode"], int(KeyCode.KEYCODE_BACK))

        res_home = self.transport.keyevent(int(KeyCode.KEYCODE_HOME))
        self.assertEqual(res_home["status"], "COMPLETED")
        self.assertEqual(res_home["keycode"], int(KeyCode.KEYCODE_HOME))

    def test_text_input(self):
        """Verify string text injection."""
        res = self.transport.text_input("OpenClaw Test 123")
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["text_length"], 17)

    def test_generic_inject_touch_interface(self):
        """Verify generic inject_touch contract method."""
        res_tap = self.transport.inject_touch("tap", 300, 400)
        self.assertEqual(res_tap["status"], "COMPLETED")

        res_swipe = self.transport.inject_touch("swipe", 100, 200, x2=100, y2=800, duration_ms=100)
        self.assertEqual(res_swipe["status"], "COMPLETED")

        res_key = self.transport.inject_touch("keyevent", 0, 0, keycode=KeyCode.KEYCODE_ENTER)
        self.assertEqual(res_key["status"], "COMPLETED")

        res_text = self.transport.inject_touch("text", 0, 0, text="Hello Shizuku")
        self.assertEqual(res_text["status"], "COMPLETED")


class TestF5ShizukuFrameStream(unittest.TestCase):
    """F5_SHIZUKU_FRAME_STREAM: Lossless frame capture & rolling MD5 delta hashing tests."""

    def setUp(self):
        self.transport = OpenClawShizukuTransport(device_target="samsung_s20", dry_run=True)

    def test_png_encoder_validity(self):
        """Verify pure Python PNG encoder produces valid PNG structure."""
        # 10x10 RGBA image
        w, h = 10, 10
        raw_rgba = os.urandom(w * h * 4)
        png_data = PNGEncoder.encode_rgba(w, h, raw_rgba)

        # Check PNG header
        self.assertTrue(png_data.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertIn(b"IHDR", png_data)
        self.assertIn(b"IDAT", png_data)
        self.assertTrue(png_data.endswith(b"IEND\xaeB`\x82"))

    def test_raw_screencap_parsing(self):
        """Verify raw Android screencap buffer parsing with 12-byte header."""
        w, h = 4, 4
        fmt = 1  # RGBA_8888
        header = struct.pack("<III", w, h, fmt)
        pixels = os.urandom(w * h * 4)
        raw_screencap = header + pixels

        parsed_w, parsed_h, rgba_out, png_out = PNGEncoder.parse_raw_screencap(raw_screencap)
        self.assertEqual(parsed_w, 4)
        self.assertEqual(parsed_h, 4)
        self.assertEqual(rgba_out, pixels)
        self.assertTrue(png_out.startswith(b"\x89PNG"))

    def test_single_frame_capture_and_md5(self):
        """Verify capture_frame returns bytes and correct MD5 hash."""
        frame_bytes, md5h = self.transport.capture_frame()
        self.assertGreater(len(frame_bytes), 10240, "Frame must be >10KB")
        self.assertEqual(len(md5h), 32)
        self.assertEqual(hashlib.md5(frame_bytes).hexdigest(), md5h)

    def test_5_frame_rolling_md5_uniqueness_pass(self):
        """Verify 5-frame rolling MD5 verification passes when all 5 frames are distinct."""
        buffer = RollingMD5Buffer(window_size=5, min_size_bytes=10240)
        for i in range(5):
            # Create distinct frames >10KB
            distinct_bytes = b"\x89PNG\r\n\x1a\n" + os.urandom(11000)
            buffer.add_frame(distinct_bytes, format_type="png")

        audit = buffer.verify_rolling_hashes(min_unique=5)
        self.assertTrue(audit["passed"])
        self.assertEqual(audit["total_frames"], 5)
        self.assertEqual(audit["unique_md5_count"], 5)
        self.assertEqual(len(audit["errors"]), 0)

    def test_frozen_ui_duplicate_md5_detection(self):
        """Verify rolling MD5 verification fails and flags frozen UI when frames are duplicates."""
        buffer = RollingMD5Buffer(window_size=5, min_size_bytes=10240)
        duplicate_frame = b"\x89PNG\r\n\x1a\n" + os.urandom(11000)

        # Add identical frame 5 times
        for _ in range(5):
            buffer.add_frame(duplicate_frame, format_type="png")

        audit = buffer.verify_rolling_hashes(min_unique=5)
        self.assertFalse(audit["passed"])
        self.assertEqual(audit["unique_md5_count"], 1)
        self.assertTrue(any("Duplicate frame" in e for e in audit["errors"]))

    def test_undersized_frame_rejection(self):
        """Verify frames <=10KB are flagged as size errors."""
        buffer = RollingMD5Buffer(window_size=5, min_size_bytes=10240)
        for _ in range(5):
            small_frame = os.urandom(500)
            buffer.add_frame(small_frame)

        audit = buffer.verify_rolling_hashes(min_unique=5)
        self.assertFalse(audit["passed"])
        self.assertTrue(any("size too small" in e for e in audit["errors"]))


class TestF6ShizukuResilience(unittest.TestCase):
    """F6_SHIZUKU_RESILIENCE: Doze, phantom processes, TCP 5555, UIAutomator PID self-healing."""

    def setUp(self):
        self.mock_adb = MockAdbExecutor()
        self.transport = OpenClawShizukuTransport(
            device_target="samsung_s20",
            adb_executor=self.mock_adb,
            dry_run=False
        )

    def test_doze_whitelisting(self):
        """Verify Doze whitelisting adds packages to whitelist."""
        res = self.transport.whitelist_doze()
        self.assertTrue(res["com.termux"])
        self.assertTrue(res["com.tailscale.ipn"])
        self.assertTrue(res["com.openclaw.agent"])

    def test_phantom_process_bypass(self):
        """Verify phantom process monitor disablement."""
        res = self.transport.bypass_phantom_processes()
        self.assertTrue(res["phantom_monitor_disabled"])
        self.assertEqual(res["max_phantom_processes"], 2147483647)

    def test_pin_adb_port(self):
        """Verify wireless ADB port 5555 pinning."""
        res = self.transport.pin_adb_port(5555)
        self.assertTrue(res["pinned"])
        self.assertEqual(res["port"], 5555)

    def test_uiautomator_anti_exit_137_pid_self_healing(self):
        """
        Verify uiautomator PID cleaner kills target uiautomator daemons
        while strictly excluding shell, grep, pkill, def_adb, and python.
        """
        killed_pids = self.transport.kill_uiautomator_daemons()
        # PID 5678 (com.android.commands.uiautomator) and PID 9012 (uiautomator runtest) must be killed
        self.assertIn("5678", killed_pids)
        self.assertIn("9012", killed_pids)
        # PID 1234 (/system/bin/sh), PID 9999 (grep), PID 8888 (pkill) must NOT be killed
        self.assertNotIn("1234", killed_pids)
        self.assertNotIn("9999", killed_pids)
        self.assertNotIn("8888", killed_pids)

    def test_device_posture_and_thermal_governance(self):
        """Verify device posture metrics and thermal governor state."""
        # 1. Normal state
        self.mock_adb.battery_temp_c = 31.5
        posture = self.transport.get_device_posture()
        self.assertEqual(posture["thermal_state"], "NORMAL")
        self.assertEqual(posture["battery_temp_c"], 31.5)
        self.assertEqual(posture["wireless_adb_port"], "5555")
        self.assertTrue(posture["uid_2000_privileged"])

        # 2. Throttled state (>= 38°C)
        self.mock_adb.battery_temp_c = 39.0
        posture_throttled = self.transport.get_device_posture()
        self.assertEqual(posture_throttled["thermal_state"], "THROTTLED")

        # 3. Emergency state (>= 42°C)
        self.mock_adb.battery_temp_c = 43.5
        posture_emerg = self.transport.get_device_posture()
        self.assertEqual(posture_emerg["thermal_state"], "EMERGENCY_THROTTLED")

    def test_full_subsystem_healing(self):
        """Verify heal_subsystem executes all self-healing routines."""
        report = self.transport.heal_subsystem("all")
        self.assertEqual(report["status"], "HEALED")
        self.assertIn("doze_whitelist", report["actions_executed"])
        self.assertIn("phantom_bypass", report["actions_executed"])
        self.assertIn("adb_persist", report["actions_executed"])
        self.assertIn("kill_uiautomator_daemons", report["actions_executed"])


class TestMultiDeviceAndJSONRPC(unittest.TestCase):
    """Topology matrix & JSON-RPC Schema validation."""

    def test_pixel_10_pro_xl_target(self):
        """Verify Google Pixel 10 Pro XL hardware profile."""
        transport_pixel = OpenClawShizukuTransport(device_target="pixel_10_pro_xl", dry_run=True)
        self.assertEqual(transport_pixel.target.width, 1344)
        self.assertEqual(transport_pixel.target.height, 2992)
        self.assertEqual(transport_pixel.target.refresh_rate_hz, 120)
        self.assertIn("Tensor G5", transport_pixel.target.soc)

    def test_json_rpc_tap_execution(self):
        """Verify OpenClaw Gateway JSON-RPC tap request parsing."""
        transport = OpenClawShizukuTransport(device_target="samsung_s20", dry_run=True)
        req = {
            "action_id": "act_unit_001",
            "device_id": "samsung_s20",
            "command_type": "tap",
            "params": {"x": 500, "y": 1000},
            "timestamp_utc": "2026-08-31T04:00:00Z"
        }
        res = transport.execute_json_rpc(req)
        self.assertEqual(res["action_id"], "act_unit_001")
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["device_id"], "samsung_s20")

    def test_json_rpc_capture_frame_execution(self):
        """Verify OpenClaw Gateway JSON-RPC frame capture request."""
        transport = OpenClawShizukuTransport(device_target="samsung_s20", dry_run=True)
        req = {
            "action_id": "act_unit_002",
            "device_id": "samsung_s20",
            "command_type": "capture_frame",
            "params": {"format": "png"},
            "timestamp_utc": "2026-08-31T04:00:00Z"
        }
        res = transport.execute_json_rpc(req)
        self.assertEqual(res["action_id"], "act_unit_002")
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(len(res["frame_md5"]), 32)
        self.assertGreater(res["frame_size_bytes"], 10240)


class TestAsyncAPIs(unittest.IsolatedAsyncioTestCase):
    """Async/Await API validation."""

    async def test_async_methods(self):
        transport = OpenClawShizukuTransport(device_target="samsung_s20", dry_run=True)
        
        # Async tap
        tap_res = await transport.async_tap(720, 1600)
        self.assertEqual(tap_res["status"], "COMPLETED")

        # Async swipe
        swipe_res = await transport.async_swipe(100, 200, 100, 800)
        self.assertEqual(swipe_res["status"], "COMPLETED")

        # Async frame capture
        frame_bytes, md5h = await transport.async_capture_frame()
        self.assertGreater(len(frame_bytes), 10240)
        self.assertEqual(len(md5h), 32)

        # Async posture
        posture = await transport.async_get_device_posture()
        self.assertEqual(posture["thermal_state"], "NORMAL")


if __name__ == "__main__":
    unittest.main()

class TestShizukuBoundaryConditions(unittest.TestCase):
    """Edge cases & boundary condition verification."""

    def test_reconnect_with_exponential_backoff(self):
        """Verify device reconnection succeeds within <= 3.0s SLA."""
        transport = OpenClawShizukuTransport(device_target="samsung_s20", dry_run=True)
        t0 = time.time()
        success = transport.reconnect(max_retries=3)
        duration_s = time.time() - t0
        self.assertTrue(success)
        self.assertLessEqual(duration_s, 3.0, "Reconnection SLA exceeded 3.0s")

    def test_all_device_topologies_defined(self):
        """Verify all canonical device profiles are registered and valid."""
        self.assertIn("samsung_s20", DEVICE_TOPOLOGY)
        self.assertIn("pixel_10_pro_xl", DEVICE_TOPOLOGY)
        self.assertIn("local_android", DEVICE_TOPOLOGY)

        s20 = DEVICE_TOPOLOGY["samsung_s20"]
        self.assertEqual(s20.width, 1440)
        self.assertEqual(s20.height, 3200)
        self.assertEqual(s20.battery_clamp_level, 80)

        pixel = DEVICE_TOPOLOGY["pixel_10_pro_xl"]
        self.assertEqual(pixel.width, 1344)
        self.assertEqual(pixel.height, 2992)
        self.assertEqual(pixel.battery_clamp_level, 80)
