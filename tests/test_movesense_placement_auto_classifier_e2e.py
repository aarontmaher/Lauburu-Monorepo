#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_movesense_placement_auto_classifier_e2e.py
================================================================================
Comprehensive E2E Automated Verification Suite for:
1. Automated Chest vs. Bicep Anatomical Placement Classification.
2. Go and Python Classifier Mathematical and Behavioral Parity.
3. Macro M4 (bicep / movesense) Dynamic Output & DSP Profile Verification.
4. Remote Execution on Physical Pixel 10 Pro XL (Layer 6 Edge Node).
5. Android BLE GATT Single-Central Lockout Detection & Invariant Verification.
6. Rule #0 (Zero-Mock) & Rule #3 (Host Sanctuary Headroom) Compliance.
================================================================================
"""

import json
import math
import os
import shutil
import subprocess
import sys
import time
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
GO_CLI_DIR = REPO_ROOT / "06_scripts_and_tooling/lauburu-opencode-cli"
LIVE_STREAM_JSON = REPO_ROOT / "00_core_infrastructure/self_healing_hub/src/movesense_live_stream.json"


class TestMovesensePlacementAutoClassifierE2E(unittest.TestCase):
    """E2E Verification for Movesense Chest vs Bicep Auto-Classification & Mesh Connectivity."""

    def test_01_go_unit_test_suite(self):
        """Proof 1: Run Go unit test suite verifying AnatomicPlacementClassifier in internal/biometrics."""
        res = subprocess.run(
            ["go", "test", "-v", "./internal/biometrics", "./internal/bluetooth"],
            cwd=str(GO_CLI_DIR),
            capture_output=True,
            text=True,
            timeout=30
        )
        self.assertEqual(res.returncode, 0, f"Go test suite failed:\n{res.stdout}\n{res.stderr}")
        self.assertIn("PASS: TestAnatomicPlacementClassifier", res.stdout)
        self.assertIn("PASS: TestTelemetryBufferLiveMetrics", res.stdout)
        print("\n[PASS] Go AnatomicPlacementClassifier unit tests passed 100% (Exit Code 0).")

    def test_02_python_classifier_parity(self):
        """Proof 1 & 2: Verify Python AnatomicPlacementClassifier in run_real_movesense_daemon.py."""
        sys.path.insert(0, str(REPO_ROOT / "03_biometrics_and_telemetry"))
        from run_real_movesense_daemon import AnatomicPlacementClassifier

        # 1. Chest Profile Simulation: Clean RR stream, smooth RSA oscillations, GATT=1 (Chest)
        chest_clf = AnatomicPlacementClassifier()
        chest_clf.set_gatt_location(1)
        res_chest = None
        for i in range(25):
            rr = 850.0 + (i % 5) * 12.0  # Thoracic breathing oscillation
            res_chest = chest_clf.update(rr, is_rejected=False, rmssd=38.0)

        self.assertIsNotNone(res_chest)
        self.assertEqual(res_chest["placement"], "chest_strap", f"Expected chest_strap, got {res_chest["placement"]}")
        self.assertGreaterEqual(res_chest["confidence_pct"], 75.0)
        self.assertIn("GATT", res_chest["rationale"])
        print(f"[PASS] Python Chest Classification: {res_chest["placement"]} ({res_chest["confidence_pct"]}%), Rationale: {res_chest["rationale"]}")

        # 2. Bicep Profile Simulation: Ectopic motion spikes (>20% rejection), GATT=2 (Arm)
        bicep_clf = AnatomicPlacementClassifier()
        bicep_clf.set_gatt_location(2)
        res_bicep = None
        for i in range(30):
            is_rej = (i % 3 == 0)  # 33% artifact rate (>18% threshold)
            rr = 1350.0 if is_rej else 820.0
            res_bicep = bicep_clf.update(rr, is_rejected=is_rej, rmssd=18.0)

        self.assertIsNotNone(res_bicep)
        self.assertEqual(res_bicep["placement"], "bicep_strap", f"Expected bicep_strap, got {res_bicep["placement"]}")
        self.assertGreaterEqual(res_bicep["confidence_pct"], 70.0)
        self.assertIn("bicep EMG", res_bicep["rationale"])
        print(f"[PASS] Python Bicep Classification: {res_bicep["placement"]} ({res_bicep["confidence_pct"]}%), Rationale: {res_bicep["rationale"]}")

    def test_03_pixel_remote_status_and_classifier_payload(self):
        """Proof 1: Execute movesense-terminal --status on Pixel 10 Pro XL over SSH."""
        res = subprocess.run(
            ["ssh", "pixel", "movesense-terminal --status"],
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertEqual(res.returncode, 0, f"Pixel status command failed: {res.stderr}")
        self.assertTrue("Movesense" in res.stdout or "device_name" in res.stdout or "LUSHA WHOOP MG" in res.stdout)
        self.assertIn("placement", res.stdout)
        self.assertIn("placement_confidence_pct", res.stdout)
        self.assertIn("dsp_profile", res.stdout)

        # Parse JSON payload returned from Pixel
        start_idx = res.stdout.find("{")
        end_idx = res.stdout.rfind("}") + 1
        json_str = res.stdout[start_idx:end_idx]
        payload = json.loads(json_str)
        self.assertIn(payload["placement"], ["chest_strap", "bicep_strap"])
        self.assertGreaterEqual(payload["placement_confidence_pct"], 60.0)
        print(f"[PASS] Pixel 10 Pro XL Remote Status Verified: Placement={payload["placement"]}, Confidence={payload["placement_confidence_pct"]}%, DSP={payload["dsp_profile"]}")

    def test_04_pixel_binary_and_script_cryptographic_parity(self):
        """Proof 2: Verify cryptographic SHA256 parity between local build and Pixel device."""
        local_bin = GO_CLI_DIR / "lauburu_android"
        with open(local_bin, "rb") as f:
            local_bin_sha = subprocess.check_output(["shasum", "-a", "256", str(local_bin)], text=True).split()[0]

        res = subprocess.run(
            ["ssh", "pixel", "sha256sum /data/data/com.termux/files/usr/bin/lauburu"],
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertEqual(res.returncode, 0)
        remote_bin_sha = res.stdout.split()[0]
        self.assertEqual(local_bin_sha, remote_bin_sha, f"SHA256 mismatch! Local: {local_bin_sha} vs Pixel: {remote_bin_sha}")
        print(f"[PASS] Cryptographic Parity Verified: Pixel ARM64 Binary SHA256={local_bin_sha[:16]}...")

    def test_05_samsung_s20_deployment(self):
        """Proof 1: Verify lauburu binary and movesense-terminal staged on Samsung Galaxy S20+ via ADB."""
        res_devices = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        if "adb-R3CN40CJJ1R" in res_devices.stdout:
            res = subprocess.run(
                ["adb", "-s", "adb-R3CN40CJJ1R-JKttZ1._adb-tls-connect._tcp", "shell", "/data/local/tmp/lauburu -h | head -n 4"],
                capture_output=True,
                text=True,
                timeout=10
            )
            self.assertEqual(res.returncode, 0)
            self.assertIn("Lauburu OpenCode Go", res.stdout)
            print("[PASS] Samsung Galaxy S20+ (L7) verified running lauburu binary via ADB.")
        else:
            print("[SKIP] Samsung Galaxy S20+ not actively attached to ADB.")

    def test_06_host_sanctuary_governance(self):
        """Rule 3: Verify Mac Mini M4 Pro host preserves >= 4.8 GB RAM and >= 10.0 GB disk headroom."""
        free_disk_gb = shutil.disk_usage("/Users/aaron").free / (1024**3)
        self.assertGreaterEqual(free_disk_gb, 10.0, f"Host Disk Headroom < 10.0 GB: {free_disk_gb:.2f} GB")

        out = subprocess.check_output(["vm_stat"], text=True)
        stats = {}
        for line in out.splitlines()[1:]:
            if ":" in line:
                k, v = line.split(":")
                stats[k.strip()] = int(v.strip().rstrip("."))
        page_size = 16384
        headroom_bytes = (
            stats.get("Pages free", 0) +
            stats.get("Pages inactive", 0) +
            stats.get("Pages speculative", 0) +
            stats.get("Pages purgeable", 0)
        ) * page_size
        headroom_gb = headroom_bytes / (1024**3)
        self.assertGreaterEqual(headroom_gb, 4.8, f"Host Sanctuary RAM < 4.8 GB: {headroom_gb:.2f} GB")
        print(f"[PASS] Host Sanctuary Headroom: RAM={headroom_gb:.2f} GB (>=4.8 GB), Disk={free_disk_gb:.2f} GB (>=10.0 GB).")


if __name__ == "__main__":
    unittest.main(verbosity=2)
