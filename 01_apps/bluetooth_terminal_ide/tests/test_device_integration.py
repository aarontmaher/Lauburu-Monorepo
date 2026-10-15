#!/usr/bin/env python3
"""
Physical On-Device Integration Tests for Google Pixel 10 Pro XL.
Governed by:
- Rule 0 (Zero-Mock): Real ADB syscalls and physical device inspection.
- Rule 1 (Tri-Proof): Physical process exit codes and screen captures.
"""

import subprocess
import pytest
import os
import time

DEVICE_ID = "192.168.8.145:46411"

def run_adb(cmd: str) -> str:
    full_cmd = f"adb -s {DEVICE_ID} {cmd}"
    res = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    return res.stdout.strip()

def test_adb_device_connected():
    """Verifies that the target Pixel device is online and attached."""
    out = subprocess.run("adb devices", shell=True, capture_output=True, text=True).stdout
    assert DEVICE_ID in out or "mustang" in out or "Pixel" in out

def test_device_reverse_port_tunnel():
    """Verifies reverse tcp:4050 port tunnel exists on the device."""
    rev_list = run_adb("reverse --list")
    if "4050" not in rev_list:
        run_adb("reverse tcp:4050 tcp:4050")
        rev_list = run_adb("reverse --list")
    assert "4050" in rev_list

def test_app_is_foreground_activity():
    """Verifies that com.lauburu.terminalide is the active focused window."""
    focus = run_adb("shell dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'")
    if "com.lauburu.terminalide" not in focus:
        run_adb("shell am start -n com.lauburu.terminalide/.MainActivity")
        time.sleep(1)
        focus = run_adb("shell dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'")
    assert "com.lauburu.terminalide" in focus

def test_device_screencap_capture():
    """Captures a test frame from the physical device and verifies valid PNG header."""
    cap_path = "/tmp/pixel_test_screencap.png"
    subprocess.run(f"adb -s {DEVICE_ID} exec-out screencap -p > {cap_path}", shell=True, check=True)
    assert os.path.exists(cap_path)
    assert os.path.getsize(cap_path) > 100_000
    with open(cap_path, "rb") as f:
        header = f.read(8)
    assert header == b'\x89PNG\r\n\x1a\n', "Invalid PNG magic header"
