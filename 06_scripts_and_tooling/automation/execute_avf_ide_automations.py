#!/usr/bin/env python3
"""
================================================================================
AVF Linux Terminal Computer UX Environment & IDE Automations Harness
================================================================================
Executes and verifies automations for:
1. Google Colab notebook workflows
2. Antigravity IDE agent runner
3. PyCharm IDE automation
4. GoLand IDE automation

Probes empirical telemetry from Pixel 10 Pro XL (Tensor G5) & AVF Debian microVM,
executes each automation suite, verifies exit codes, and records structured
results in 04_data_and_memory/test_artifacts/avf_ide_automations.json.
================================================================================
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path("/Users/Shared/aaron/DFS_UNIFIED/Lauburu-Monorepo")
OUTPUT_FILE = REPO_ROOT / "04_data_and_memory" / "test_artifacts" / "avf_ide_automations.json"

def probe_avf_environment():
    """Probe empirical telemetry from L6 Pixel 10 host and L4 AVF Debian microVM."""
    telemetry = {
        "host_device": "Google Pixel 10 Pro XL (Google Tensor G5)",
        "host_ip_tailscale": "100.114.215.68",
        "host_ip_lan": "192.168.8.213",
        "avf_tap_ip": "10.129.74.53",
        "shizuku_uid": 2000,
        "shizuku_status": "OFFLINE",
        "avf_vm_status": "OFFLINE",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # 1. Probe Shizuku / Pixel Host
    try:
        res = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=3", "pixel", "~/bin/rish -c 'id; getprop ro.build.version.release' 2>&1"],
            capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0 and "uid=2000" in res.stdout:
            telemetry["shizuku_status"] = f"OPERATIONAL: {res.stdout.strip().splitlines()[0]}"
            telemetry["android_version"] = f"Android {res.stdout.strip().splitlines()[-1]}"
    except Exception as e:
        telemetry["shizuku_error"] = str(e)

    # 2. Probe Virtualization service / crosvm
    try:
        res = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=3", "pixel", "~/bin/rish -c 'ps -A | grep -E \"(virtualization|crosvm)\"' 2>&1"],
            capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0 and res.stdout.strip():
            telemetry["avf_vm_status"] = f"ACTIVE: {res.stdout.strip().splitlines()[0]}"
    except Exception as e:
        telemetry["avf_error"] = str(e)

    return telemetry

def run_command_capture(cmd, cwd=str(REPO_ROOT), timeout=60):
    """Run a command and capture exit code, stdout, stderr, and execution duration."""
    start_time = time.time()
    try:
        res = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "exit_code": res.returncode,
            "stdout": res.stdout.strip()[-2000:] if len(res.stdout) > 2000 else res.stdout.strip(),
            "stderr": res.stderr.strip()[-1000:] if len(res.stderr) > 1000 else res.stderr.strip(),
            "duration_ms": duration_ms,
            "status": "PASSED" if res.returncode == 0 else "FAILED"
        }
    except subprocess.TimeoutExpired:
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
            "duration_ms": duration_ms,
            "status": "TIMED_OUT"
        }
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
            "duration_ms": duration_ms,
            "status": "ERROR"
        }

def execute_all_automations():
    print("=" * 80)
    print("🚀 EXECUTING AVF LINUX TERMINAL & IDE AUTOMATIONS")
    print("=" * 80)

    env_telemetry = probe_avf_environment()
    print(f"📱 Host Telemetry: {env_telemetry['host_device']} | Shizuku: {env_telemetry['shizuku_status']}")
    print(f"🐧 AVF Status: {env_telemetry['avf_vm_status']}")

    results = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "environment": env_telemetry,
        "automations": {}
    }

    # 1. Google Colab Notebook Workflows Automation
    print("\n[1/4] Running Google Colab Notebook Workflows Automation...")
    colab_res = run_command_capture(
        [sys.executable, "06_scripts_and_tooling/automation/setup_colab_pycharm.py", "--check"]
    )
    results["automations"]["google_colab_notebook_workflows"] = colab_res
    print(f"  └─ Status: {colab_res['status']} | Exit Code: {colab_res['exit_code']} | Duration: {colab_res['duration_ms']}ms")

    # 2. Antigravity IDE Agent Runner Automation
    print("\n[2/4] Running Antigravity IDE Agent Runner Automation...")
    agy_res = run_command_capture(
        [sys.executable, "06_scripts_and_tooling/automation/live_ide_testing_harness.py", "AVF Terminal AGY Agent Execution"]
    )
    results["automations"]["antigravity_ide_agent_runner"] = agy_res
    print(f"  └─ Status: {agy_res['status']} | Exit Code: {agy_res['exit_code']} | Duration: {agy_res['duration_ms']}ms")

    # 3. PyCharm IDE Automation
    print("\n[3/4] Running PyCharm IDE Automation...")
    pycharm_res = run_command_capture(
        [sys.executable, "-m", "pytest", "06_scripts_and_tooling/gemini_lens_integration/tests/test_lens_pycharm_sync.py"]
    )
    results["automations"]["pycharm_ide_automation"] = pycharm_res
    print(f"  └─ Status: {pycharm_res['status']} | Exit Code: {pycharm_res['exit_code']} | Duration: {pycharm_res['duration_ms']}ms")

    # 4. GoLand IDE Automation
    print("\n[4/5] Running GoLand IDE Automation...")
    goland_res = run_command_capture(
        ["./go_browser_automator", "--url", "http://127.0.0.1:8080", "--output", str(REPO_ROOT / "04_data_and_memory" / "data" / "auditor_artifacts" / "goland_ide_telemetry.json")],
        cwd=str(REPO_ROOT / "06_scripts_and_tooling" / "automation" / "go_browser_automator")
    )
    results["automations"]["goland_ide_automation"] = goland_res
    print(f"  └─ Status: {goland_res['status']} | Exit Code: {goland_res['exit_code']} | Duration: {goland_res['duration_ms']}ms")

    # 5. Polyglot Specialist IDE (GoLand/langgo, PyCharm, IntelliJ IDEA) & Runtime (Chromium, Bluetooth Serial :4005) Empirical Suite
    print("\n[5/5] Running Polyglot Specialist IDE & Runtime Empirical Integration Suite...")
    specialists_res = run_command_capture(
        [sys.executable, "06_scripts_and_tooling/lens_cli.py", "specialists", "--target", "all", "--json"]
    )
    results["automations"]["polyglot_specialist_ide_and_runtime_suite"] = specialists_res
    print(f"  └─ Status: {specialists_res['status']} | Exit Code: {specialists_res['exit_code']} | Duration: {specialists_res['duration_ms']}ms")

    # Overall Status Evaluation
    all_passed = all(
        a["exit_code"] == 0 for a in results["automations"].values()
    )
    results["overall_status"] = "PASSED" if all_passed else "FAILED"
    results["total_automations_executed"] = len(results["automations"])
    results["all_exit_codes_zero"] = all_passed

    # Save artifact
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print(f"✅ EXECUTION COMPLETE — Overall Status: {results['overall_status']}")
    print(f"💾 Execution results recorded in: {OUTPUT_FILE}")
    print("=" * 80)

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(execute_all_automations())
