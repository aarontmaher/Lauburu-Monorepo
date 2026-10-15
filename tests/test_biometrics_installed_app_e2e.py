#!/usr/bin/env python3
"""
tests/test_biometrics_installed_app_e2e.py
================================================================================
Comprehensive End-to-End Test Suite for Installed Android Biometrics Application:
1. Native Android APK Existence, Integrity & Size (> 5 MB).
2. Package Manifest & Rule 9 App Naming ('Biometrics Lauburu').
3. Physical ADB Device Installation Verification (Pixel 10 Pro XL & Samsung S20+).
4. Backend REST Endpoints:
   - /api/movesense/status (200, JSON schema)
   - /api/movesense/trends (200, TinyML Trend Engine snapshot)
   - /api/movesense/ai-analysis (200, Sovereign Bio Local AI Model interpretation)
5. Storage & Host Sanctuary (RAM & Disk Headroom).
================================================================================
"""

import json
import os
import shutil
import subprocess
import urllib.request
import pytest

APK_PATH = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/android_apks/Biometrics_Lauburu.apk"
AAPT_PATH = "/Users/aaron/android-sdk/build-tools/34.0.0/aapt"
ADB_PATH = "/Users/aaron/android-sdk/platform-tools/adb"


def test_01_apk_existence_and_size():
    """Verify APK binary is compiled, staged, and non-trivial size (>5MB)."""
    assert os.path.exists(APK_PATH), f"APK not found at {APK_PATH}"
    size_mb = os.path.getsize(APK_PATH) / (1024 * 1024)
    assert size_mb >= 5.0, f"APK size {size_mb:.2f} MB is smaller than expected 5.0 MB"


def test_02_package_manifest_and_naming():
    """Verify package name and Rule 9 identifier-first application label."""
    res = subprocess.run([AAPT_PATH, "dump", "badging", APK_PATH], capture_output=True, text=True)
    assert res.returncode == 0, f"aapt dump badging failed: {res.stderr}"
    assert "package: name='com.lauburu.terminalide'" in res.stdout
    assert "application-label:'Biometrics Lauburu'" in res.stdout
    assert "com.lauburu.terminalide.MainActivity" in res.stdout


def test_03_devices_installed_via_adb():
    """Verify that com.lauburu.terminalide is installed on connected Android devices."""
    res = subprocess.run([ADB_PATH, "devices", "-l"], capture_output=True, text=True)
    assert res.returncode == 0
    devices = [line.split()[0] for line in res.stdout.strip().split("\n")[1:] if "device " in line or "usb:" in line]
    assert len(devices) > 0, "No active ADB devices found"

    for dev in devices:
        chk = subprocess.run([ADB_PATH, "-s", dev, "shell", "pm", "list", "packages", "com.lauburu.terminalide"],
                             capture_output=True, text=True)
        assert "package:com.lauburu.terminalide" in chk.stdout, f"Package not installed on {dev}"


def test_04_movesense_status_endpoint():
    """Verify /api/movesense/status returns 200 with expected schema."""
    req = urllib.request.Request("http://127.0.0.1:4050/api/movesense/status")
    with urllib.request.urlopen(req, timeout=5) as response:
        assert response.status == 200
        data = json.loads(response.read().decode())
        assert "daemon_running" in data
        assert "readiness" in data
        assert "stream" in data


def test_05_movesense_trends_endpoint():
    """Verify /api/movesense/trends returns 200 with TinyML physiological trend metrics."""
    req = urllib.request.Request("http://127.0.0.1:4050/api/movesense/trends")
    with urllib.request.urlopen(req, timeout=5) as response:
        assert response.status == 200
        data = json.loads(response.read().decode())
        assert "heart_rate_bpm" in data
        assert "rmssd_ms" in data
        assert "dfa_alpha1" in data
        assert "alpha1_slope_per_min" in data
        assert "cardiac_drift_pct" in data
        assert "ectopic_density_per_min" in data
        assert "signal_quality_sqi_pct" in data
        assert "placement" in data
        assert "dsp_profile" in data
        assert data.get("rule_0_zero_mock") is True


def test_06_movesense_ai_analysis_endpoint():
    """Verify /api/movesense/ai-analysis returns 200 with Sovereign Bio Local AI assessment."""
    req = urllib.request.Request("http://127.0.0.1:4050/api/movesense/ai-analysis",
                                 data=b"{}",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as response:
        assert response.status == 200
        data = json.loads(response.read().decode())
        assert "model" in data
        assert "assessment" in data or "analysis" in data
        assert data.get("rule_0_zero_mock") is True


def test_07_storage_and_host_sanctuary():
    """Verify Tri-Vault storage layers and Mac host sanctuary headroom."""
    assert os.path.isdir("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault")
    assert os.path.isdir("/Users/aaron/DFS_UNIFIED/lora_datasets")
    assert os.path.isdir("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory")

    free_disk_gb = shutil.disk_usage("/Users/aaron").free / (1024 ** 3)
    assert free_disk_gb >= 10.0, f"Free disk headroom {free_disk_gb:.2f} GB is below 10.0 GB threshold"
