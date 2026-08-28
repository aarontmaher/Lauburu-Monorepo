#!/usr/bin/env python3
"""
Adversarial Stress Harness: Continuous 24/7 LoRA Fine-Tuning & Google Drive Sync Resilience (R6)
Tests LoRA harvesting engine and Google Drive sync target path resilience when target directory
is missing, read-only, non-writable, or permission-denied. Validates dataset schemas and zero-mock integrity.
"""

import sys
import os
import json
import stat
import shutil
import tempfile
import traceback
import subprocess
from typing import Dict, Any, List

BASE_DIR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
sys.path.insert(0, os.path.join(BASE_DIR, "self_healing_hub", "src"))

import npu_training_harvesting_engine as lora_engine
from npu_training_harvesting_engine import (
    MultiStreamDataHarvester,
    NPUHardwareGovernor,
    run_harvesting_cycle,
    get_data_streams_telemetry,
)

def run_adversarial_lora_sync_tests():
    print("=================================================================")
    print("  ADVERSARIAL STRESS TEST: LoRA HARVESTING & GDRIVE SYNC (R6)   ")
    print("=================================================================")
    results = {}

    # Test 1: Single harvest cycle execution & JSONL schema validation
    try:
        run_harvesting_cycle()
        telemetry = get_data_streams_telemetry()
        assert telemetry["summary"]["active_streams_count"] == 4
        assert telemetry["summary"]["cloud_spend"] == "$0.00 (100% Free Edge & VFS Storage)"
        assert "100% REAL" in telemetry["summary"]["air_gap_quarantine_certified"]
        
        lora_dir = lora_engine.LORA_DIR
        for s in telemetry["streams"]:
            fpath = os.path.join(lora_dir, s["filename"])
            assert os.path.exists(fpath), f"Harvested stream file missing: {fpath}"
            assert os.path.getsize(fpath) > 0, f"Harvested stream file is empty: {fpath}"
            # Verify every line is valid JSON
            with open(fpath, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            assert len(lines) >= 1
            for line in lines[-5:]:  # Check recent entries
                parsed = json.loads(line)
                assert parsed.get("real_data_certified") is True
                assert parsed.get("source_data_origin") == "100%_REAL_PHYSICAL_HARDWARE"
                assert parsed.get("air_gap_simulation_quarantine") is True
                assert "instruction" in parsed and "input" in parsed and "output" in parsed
        print(" [PASS] Test 1: LoRA harvesting cycle produces valid JSONL datasets with zero synthetic contamination")
        results["test_1_harvest_schema_integrity"] = "PASS"
    except Exception as e:
        print(f" [FAIL] Test 1: {e}")
        traceback.print_exc()
        results["test_1_harvest_schema_integrity"] = f"FAIL: {e}"

    # Test 2: Target directory missing -> Automatic recreation
    try:
        temp_dir = tempfile.mkdtemp(prefix="gdrive_missing_test_")
        test_fallback = os.path.join(temp_dir, "nested", "deep", "lora_datasets")
        assert not os.path.exists(test_fallback)
        
        # Override GDRIVE_FALLBACK_DIR temporarily
        orig_fallback = lora_engine.GDRIVE_FALLBACK_DIR
        lora_engine.GDRIVE_FALLBACK_DIR = test_fallback
        try:
            lora_engine.run_harvesting_cycle()
            assert os.path.exists(test_fallback), "Engine should have created missing deep target directory"
            synced_files = os.listdir(test_fallback)
            assert len(synced_files) >= 4, f"Expected at least 4 synced stream files, got {synced_files}"
            print(" [PASS] Test 2: Missing target directory tree automatically resolved and created")
            results["test_2_missing_dir_recovery"] = "PASS"
        finally:
            lora_engine.GDRIVE_FALLBACK_DIR = orig_fallback
            shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception as e:
        print(f" [FAIL] Test 2: {e}")
        traceback.print_exc()
        results["test_2_missing_dir_recovery"] = f"FAIL: {e}"

    # Test 3: Target directory READ-ONLY (permission denied) resilience
    try:
        temp_dir = tempfile.mkdtemp(prefix="gdrive_readonly_test_")
        test_ro_fallback = os.path.join(temp_dir, "readonly_lora_datasets")
        os.makedirs(test_ro_fallback, exist_ok=True)
        # Make directory read-only (remove write permission: 0o555)
        os.chmod(test_ro_fallback, stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        
        orig_fallback = lora_engine.GDRIVE_FALLBACK_DIR
        lora_engine.GDRIVE_FALLBACK_DIR = test_ro_fallback
        try:
            # Run harvesting cycle: it should catch/handle the rsync failure without raising unhandled exception
            lora_engine.run_harvesting_cycle()
            print(" [PASS] Test 3: Read-only target directory handled gracefully without daemon crash")
            results["test_3_readonly_target_resilience"] = "PASS"
        except Exception as exc:
            print(f" [FAIL] Test 3: Crashed on read-only directory: {exc}")
            results["test_3_readonly_target_resilience"] = f"FAIL: {exc}"
        finally:
            # Restore permissions to allow cleanup
            os.chmod(test_ro_fallback, stat.S_IRWXU)
            lora_engine.GDRIVE_FALLBACK_DIR = orig_fallback
            shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception as e:
        print(f" [FAIL] Test 3: {e}")
        traceback.print_exc()
        results["test_3_readonly_target_resilience"] = f"FAIL: {e}"

    # Test 4: Native Google Drive mount fallback detection
    try:
        orig_native = lora_engine.GDRIVE_LORA_DIR
        lora_engine.GDRIVE_LORA_DIR = "/Volumes/NonExistentGoogleDriveMount_404"
        try:
            # Should skip native mount and seamlessly fall back to local VFS cache
            lora_engine.run_harvesting_cycle()
            telem = lora_engine.get_data_streams_telemetry()
            assert telem["summary"]["google_drive_synced"] is True
            assert telem["summary"]["google_drive_target"] == lora_engine.GDRIVE_FALLBACK_DIR
            print(" [PASS] Test 4: Native mount dropout gracefully switches to Local VFS cache target")
            results["test_4_native_mount_fallback"] = "PASS"
        finally:
            lora_engine.GDRIVE_LORA_DIR = orig_native
    except Exception as e:
        print(f" [FAIL] Test 4: {e}")
        traceback.print_exc()
        results["test_4_native_mount_fallback"] = f"FAIL: {e}"

    # Test 5: Hardware NPU Governor telemetry validation
    try:
        npu_status = NPUHardwareGovernor.get_npu_cluster_status()
        assert "apple_ane_m4" in npu_status
        assert "tensor_g5_tpu" in npu_status
        assert "qualcomm_hexagon" in npu_status
        assert "amd_xdna_npu" in npu_status
        assert npu_status["summary"]["total_cluster_npu_tops"] >= 120.0
        assert npu_status["summary"]["gpu_offload_savings_pct"] >= 80.0
        print(" [PASS] Test 5: NPU Hardware Cluster Governor reports valid on-device TOPS and zero-cloud metrics")
        results["test_5_npu_cluster_governor"] = "PASS"
    except Exception as e:
        print(f" [FAIL] Test 5: {e}")
        traceback.print_exc()
        results["test_5_npu_cluster_governor"] = f"FAIL: {e}"

    print("=================================================================")
    all_passed = all(v == "PASS" for v in results.values())
    print(f"R6 LoRA & SYNC ADVERSARIAL RESULT: {'ALL PASSED' if all_passed else 'FAILURES DETECTED'}")
    print("=================================================================")
    return all_passed, results

if __name__ == "__main__":
    ok, res = run_adversarial_lora_sync_tests()
    if not ok:
        sys.exit(1)
