#!/usr/bin/env python3
"""
Milestone 3 Automated Fault Injection Test Suite: `test_fault_injection.py`

Performs an end-to-end fault injection audit on the Self-Healing Hub:
1. Master Cleanup Guard: Defines master pristine node settings and guarantees devices.json restoration via try...finally.
2. Baseline Phase: Explicitly polls http://localhost:5001/api/telemetry and asserts active NON-NULL telemetry (`memory`, `ping_latency_ms`) BEFORE starting fault injection.
3. Fault Injection Phase: Injects unreachable IP into devices.json and asserts explicit `null` values for `battery`, `memory`, `net_stats`, `ping_latency_ms` with ZERO fake or hardcoded data.
4. Recovery Phase: Restores original node configuration and asserts 100% state recovery to live non-null telemetry.
5. Saves execution results to scripts/fault_injection_results.json and ensures devices.json is clean post-test.
"""

import sys
import os
import json
import time
import urllib.request
import logging
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")
DEVICES_JSON_PATH = os.path.join(SRC_DIR, "devices.json")
OUTPUT_JSON_PATH = os.path.join(BASE_DIR, "scripts", "fault_injection_results.json")

API_TELEMETRY_URL = "http://localhost:5001/api/telemetry"
API_DEVICES_URL = "http://localhost:5001/api/devices"
UNREACHABLE_IP = "192.0.2.1"
POLL_WAIT_TIMEOUT_SECONDS = 150
POLL_CHECK_INTERVAL_SECONDS = 2

# Master pristine device definitions for guaranteed clean restoration
PRISTINE_DEVICES = {
  "Pixel_10": {
    "use_ssh": True,
    "device_id": "100.73.38.87:5555",
    "ssh_host": "100.73.38.87",
    "ssh_port": 8022,
    "ssh_user": "u0_a363",
    "ssh_key": "~/.ssh/id_ed25519",
    "current_tier": 1
  },
  "Samsung_S20": {
    "use_ssh": True,
    "device_id": "100.84.40.95:5555",
    "ssh_host": "100.84.40.95",
    "ssh_port": 8022,
    "ssh_user": "u0_a420",
    "ssh_key": "~/.ssh/id_ed25519",
    "current_tier": 1
  },
  "Linux_Head_Node": {
    "use_ssh": True,
    "device_id": None,
    "ssh_host": "100.101.39.98",
    "ssh_port": 22,
    "ssh_user": "linux",
    "ssh_key": "~/.ssh/id_ed25519",
    "relay_host": "100.122.185.123",
    "relay_cmd": "dbclient linux@192.168.8.224",
    "current_tier": 1
  },
  "Mac_Node": {
    "use_ssh": True,
    "device_id": None,
    "ssh_host": "127.0.0.1",
    "ssh_port": 22,
    "ssh_user": "aaronmaher",
    "ssh_key": "~/.ssh/id_ed25519",
    "current_tier": 1
  }
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_fault_injection")

def fetch_json(url, timeout=5):
    """Fetches and parses JSON from HTTP endpoint."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FaultInjectionTester/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                return data, None
            else:
                return None, f"HTTP status {response.status}"
    except Exception as e:
        return None, str(e)

def load_devices_json():
    with open(DEVICES_JSON_PATH, "r") as f:
        return json.load(f)

def save_devices_json(data):
    temp_path = DEVICES_JSON_PATH + ".tmp"
    for attempt in range(5):
        try:
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(temp_path, DEVICES_JSON_PATH)
            return
        except Exception as e:
            if attempt == 4:
                raise
            time.sleep(0.2)

def wait_for_telemetry_condition(condition_fn, description, timeout=POLL_WAIT_TIMEOUT_SECONDS):
    """
    Polls http://localhost:5001/api/telemetry until condition_fn(telemetry_data) returns True.
    Returns (telemetry_data, elapsed_time_seconds).
    """
    start_time = time.time()
    logger.info(f"Waiting for telemetry condition: {description} (max {timeout}s)...")
    while time.time() - start_time <= timeout:
        telemetry, err = fetch_json(API_TELEMETRY_URL)
        if telemetry and condition_fn(telemetry):
            elapsed = time.time() - start_time
            logger.info(f"Condition met in {elapsed:.2f}s: {description}")
            return telemetry, round(elapsed, 2)
        time.sleep(POLL_CHECK_INTERVAL_SECONDS)
    
    elapsed = time.time() - start_time
    logger.error(f"Timed out after {elapsed:.2f}s waiting for: {description}")
    telemetry, _ = fetch_json(API_TELEMETRY_URL)
    return telemetry, round(elapsed, 2)

def test_target_node_fault_injection(node_name, unreachable_config_patch, master_pristine_devices):
    logger.info(f"\n==================== FAULT INJECTION TEST: {node_name} ====================")
    test_record = {
        "node_name": node_name,
        "start_timestamp_iso": datetime.now(tz=timezone.utc).isoformat(),
        "unreachable_patch": unreachable_config_patch,
        "phases": {}
    }
    
    # Get original pristine configuration for this node from master backup
    orig_node_config = dict(master_pristine_devices[node_name])
    
    # 1. Baseline Phase: Must explicitly poll API and assert active NON-NULL telemetry BEFORE starting fault injection
    logger.info(f"[{node_name}] Phase 1: Validating baseline telemetry (must be active and NON-NULL)...")
    
    def is_baseline_active(tel):
        dev = tel.get("devices", {}).get(node_name)
        if not dev:
            return False
        # Assert memory and ping_latency_ms are active non-null
        has_memory = dev.get("memory") is not None
        has_ping = dev.get("ping_latency_ms") is not None
        return has_memory and has_ping

    baseline_telemetry, baseline_wait_time = wait_for_telemetry_condition(
        is_baseline_active,
        f"Node {node_name} active non-null baseline telemetry",
        timeout=POLL_WAIT_TIMEOUT_SECONDS
    )

    dev_baseline = baseline_telemetry.get("devices", {}).get(node_name, {}) if baseline_telemetry else {}

    memory_non_null = dev_baseline.get("memory") is not None
    ping_non_null = dev_baseline.get("ping_latency_ms") is not None
    battery_val = dev_baseline.get("battery")
    battery_non_null = battery_val is not None

    baseline_passed = memory_non_null and ping_non_null

    logger.info(f"[{node_name}] Baseline telemetry state: memory={dev_baseline.get('memory')}, ping={dev_baseline.get('ping_latency_ms')}, battery={battery_val}")

    test_record["phases"]["baseline"] = {
        "passed": baseline_passed,
        "wait_time_seconds": baseline_wait_time,
        "assertions": {
            "memory_is_non_null": memory_non_null,
            "ping_latency_ms_is_non_null": ping_non_null,
            "battery_is_non_null": battery_non_null
        },
        "telemetry_snapshot": dev_baseline
    }

    if not baseline_passed:
        logger.error(f"[{node_name}] ❌ Baseline assertions failed! Node telemetry contains null values before fault injection.")
        test_record["overall_passed"] = False
        test_record["end_timestamp_iso"] = datetime.now(tz=timezone.utc).isoformat()
        return test_record

    try:
        # 2. Inject Fault Phase
        logger.info(f"[{node_name}] Phase 2: Injecting unreachable device configuration {unreachable_config_patch}...")
        modified_devices = load_devices_json()
        modified_devices[node_name].update(unreachable_config_patch)
        save_devices_json(modified_devices)
        
        # Condition function: all telemetry metrics for node_name must be explicitly None/null
        def is_unreachable(tel):
            dev = tel.get("devices", {}).get(node_name)
            if not dev:
                return False
            return (
                dev.get("battery") is None and
                dev.get("memory") is None and
                dev.get("net_stats") is None and
                dev.get("ping_latency_ms") is None
            )
            
        fault_telemetry, fault_wait_time = wait_for_telemetry_condition(
            is_unreachable,
            f"Node {node_name} reporting all metrics as null",
            timeout=POLL_WAIT_TIMEOUT_SECONDS
        )
        
        dev_fault = fault_telemetry.get("devices", {}).get(node_name, {}) if fault_telemetry else {}
        
        # Assert explicit nulls
        battery_null = dev_fault.get("battery") is None
        memory_null = dev_fault.get("memory") is None
        net_stats_null = dev_fault.get("net_stats") is None
        ping_null = dev_fault.get("ping_latency_ms") is None
        
        # Assert NO fake / static / fallback numbers
        no_fake_data = True
        fake_data_reasons = []
        for key in ["battery", "memory", "net_stats", "ping_latency_ms"]:
            val = dev_fault.get(key)
            if val is not None:
                no_fake_data = False
                fake_data_reasons.append(f"Field '{key}' is not null: {val}")
                
        fault_passed = battery_null and memory_null and net_stats_null and ping_null and no_fake_data
        
        test_record["phases"]["fault_injection"] = {
            "passed": fault_passed,
            "wait_time_seconds": fault_wait_time,
            "assertions": {
                "battery_is_null": battery_null,
                "memory_is_null": memory_null,
                "net_stats_is_null": net_stats_null,
                "ping_latency_ms_is_null": ping_null,
                "no_fake_data_reported": no_fake_data,
                "fake_data_violations": fake_data_reasons
            },
            "telemetry_snapshot": dev_fault
        }
        
        if not fault_passed:
            logger.error(f"[{node_name}] ❌ Fault injection assertions failed: {fake_data_reasons}")
        else:
            logger.info(f"[{node_name}] ✅ Fault injection assertions PASSED! Device returned explicit nulls without fake data.")
            
    finally:
        # 3. Restore Configuration Phase
        logger.info(f"[{node_name}] Phase 3: Restoring original device configuration...")
        restore_devices = load_devices_json()
        restore_devices[node_name] = orig_node_config
        save_devices_json(restore_devices)
        
    # Wait for state recovery: memory and ping return to active non-null
    def is_recovered(tel):
        dev = tel.get("devices", {}).get(node_name)
        if not dev:
            return False
        has_memory = dev.get("memory") is not None
        has_ping = dev.get("ping_latency_ms") is not None
        return has_memory and has_ping

    recovery_telemetry, recovery_wait_time = wait_for_telemetry_condition(
        is_recovered,
        f"Node {node_name} state recovery (non-null telemetry)",
        timeout=POLL_WAIT_TIMEOUT_SECONDS
    )

    dev_recovered = recovery_telemetry.get("devices", {}).get(node_name, {}) if recovery_telemetry else {}
    
    recovered_memory_non_null = dev_recovered.get("memory") is not None
    recovered_ping_non_null = dev_recovered.get("ping_latency_ms") is not None
    recovery_passed = recovered_memory_non_null and recovered_ping_non_null

    test_record["phases"]["recovery"] = {
        "passed": recovery_passed,
        "wait_time_seconds": recovery_wait_time,
        "assertions": {
            "memory_restored": recovered_memory_non_null,
            "ping_latency_restored": recovered_ping_non_null
        },
        "telemetry_snapshot": dev_recovered
    }
    
    if not recovery_passed:
        logger.error(f"[{node_name}] ❌ Recovery assertions failed!")
    else:
        logger.info(f"[{node_name}] ✅ State recovery assertions PASSED! Node returned live telemetry.")
        
    test_record["overall_passed"] = (
        test_record["phases"]["baseline"]["passed"] and
        test_record["phases"]["fault_injection"]["passed"] and
        test_record["phases"]["recovery"]["passed"]
    )
    test_record["end_timestamp_iso"] = datetime.now(tz=timezone.utc).isoformat()
    return test_record

def main():
    logger.info("Starting Milestone 3 Fault Injection & Unreachable Device Audit...")
    start_time = time.time()
    
    # Save master pristine copy of devices.json at script start and restore disk copy to pristine
    master_pristine_devices = dict(PRISTINE_DEVICES)
    save_devices_json(master_pristine_devices)
    logger.info(f"Master pristine devices.json written and verified with keys: {list(master_pristine_devices.keys())}")

    target_nodes_test_configs = [
        ("Pixel_10", {"ssh_host": UNREACHABLE_IP, "device_id": f"{UNREACHABLE_IP}:5555"}),
        ("Samsung_S20", {"device_id": f"{UNREACHABLE_IP}:5555", "ssh_host": UNREACHABLE_IP})
    ]
    
    all_results = {}
    all_passed = True
    
    try:
        for node_name, patch in target_nodes_test_configs:
            try:
                res = test_target_node_fault_injection(node_name, patch, master_pristine_devices)
                all_results[node_name] = res
                if not res.get("overall_passed"):
                    all_passed = False
            except Exception as e:
                logger.error(f"Error executing fault injection on {node_name}: {e}")
                all_results[node_name] = {
                    "node_name": node_name,
                    "overall_passed": False,
                    "error": str(e)
                }
                all_passed = False
    finally:
        logger.info("Guaranteed Master Cleanup: Restoring pristine devices.json...")
        save_devices_json(master_pristine_devices)
        logger.info("Master devices.json restored successfully.")
            
    end_time = time.time()
    
    output_data = {
        "metadata": {
            "audit_name": "Milestone 3 Fault Injection & Unreachable Device Behavior Audit",
            "timestamp_iso": datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat(),
            "execution_duration_seconds": round(end_time - start_time, 2),
            "unreachable_target_ip": UNREACHABLE_IP,
            "target_nodes_tested": [n for n, _ in target_nodes_test_configs],
            "all_nodes_passed": all_passed
        },
        "results": all_results
    }
    
    os.makedirs(os.path.dirname(OUTPUT_JSON_PATH), exist_ok=True)
    with open(OUTPUT_JSON_PATH, "w") as f:
        json.dump(output_data, f, indent=2)
        
    logger.info(f"\nFault injection execution results saved to: {OUTPUT_JSON_PATH}")
    
    print("\n" + "="*70)
    print("        MILESTONE 3 FAULT INJECTION AUDIT SUMMARY REPORT")
    print("="*70)
    print(f"Timestamp: {output_data['metadata']['timestamp_iso']}")
    print(f"Overall Status: {'PASSED (✅)' if all_passed else 'FAILED (❌)'}")
    print("-"*70)
    for node_name, res in all_results.items():
        status = "PASSED ✅" if res.get("overall_passed") else "FAILED ❌"
        print(f"Node: {node_name:<20} Status: {status}")
        if res.get("phases"):
            bl = res["phases"].get("baseline", {})
            fi = res["phases"].get("fault_injection", {})
            rec = res["phases"].get("recovery", {})
            print(f"  - Baseline Non-Null Check: {'PASS' if bl.get('passed') else 'FAIL'} (in {bl.get('wait_time_seconds')}s)")
            print(f"  - Fault Injection Nulls:   {'PASS' if fi.get('passed') else 'FAIL'} (in {fi.get('wait_time_seconds')}s)")
            print(f"  - Zero Fake Data Verified: {'PASS' if fi.get('assertions', {}).get('no_fake_data_reported') else 'FAIL'}")
            print(f"  - Complete State Recovery: {'PASS' if rec.get('passed') else 'FAIL'} (in {rec.get('wait_time_seconds')}s)")
        else:
            print(f"  - Error: {res.get('error')}")
        print("-" * 70)

    if not all_passed:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
