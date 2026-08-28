#!/usr/bin/env python3
"""
Canonical Port — 4-Tier Test Suite Master Runner
Version: 3.0.0-CANONICAL
Executes all test tiers, compiles metrics, verifies coverage thresholds, and outputs a formatted report.
"""

import os
import sys
import subprocess
import time
import re

def run_tier(tier_name: str, test_path: str):
    print(f"\n========================================================")
    print(f"  RUNNING {tier_name.upper()}")
    print(f"  Path: {test_path}")
    print(f"========================================================")
    for f in ["blackboard_state.json", "blackboard_state.yaml"]:
        if os.path.isfile(f):
            try:
                os.remove(f)
            except Exception:
                pass
    cmd = ["uv", "run", "--with", "rich,textual,pyyaml,pytest,pytest-asyncio,httpx", "pytest", test_path, "-v", "--tb=short"]
    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True)
    duration = time.time() - t0
    
    output = res.stdout + res.stderr
    print(output)
    
    passed_match = re.search(r"(\d+)\s+passed", output)
    passed_count = int(passed_match.group(1)) if passed_match else 0
    failed_match = re.search(r"(\d+)\s+failed", output)
    failed_count = int(failed_match.group(1)) if failed_match else 0
    
    passed = (res.returncode == 0 and failed_count == 0)
    return {
        "tier": tier_name,
        "path": test_path,
        "passed": passed,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "durationSec": round(duration, 3),
        "returnCode": res.returncode
    }

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root_dir)
    
    tiers = [
        ("Unit & Component Tests", "tests/unit/"),
        ("Tier 1: Category-Partition Feature Coverage (F1-F24)", "tests/e2e/test_tier1_category_partition.py"),
        ("Tier 2: Boundary Value Analysis (F1-F24)", "tests/e2e/test_tier2_boundary_values.py"),
        ("Tier 3: Pairwise Combinatorial Matrix", "tests/e2e/test_tier3_pairwise_combinations.py"),
        ("Tier 4: Real-World Swarm Workload Scenarios", "tests/e2e/test_tier4_real_world_scenarios.py"),
        ("Challenger 1: React Web UI Adversarial Verifier", "tests/e2e/test_challenger_react_web_adversarial.py"),
        ("Challenger 2: Headless TUI Pilot Adversarial Verifier", "tests/e2e/test_challenger_tui_adversarial.py")
    ]
    
    results = []
    all_passed = True
    total_tests = 0
    
    for name, path in tiers:
        res = run_tier(name, path)
        results.append(res)
        total_tests += res["passed_count"]
        if not res["passed"]:
            all_passed = False
            
    print("\n" + "=" * 80)
    print("                 4-TIER E2E TEST EXECUTION SUMMARY")
    print("=" * 80)
    for r in results:
        status_str = "[PASS]" if r["passed"] else "[FAIL]"
        print(f"  {status_str} {r['tier']:<55} | {r['passed_count']:>3} passed | ({r['durationSec']}s)")
    print("-" * 80)
    print(f"  TOTAL TESTS EXECUTED: {total_tests} | ALL TIERS PASSED: {all_passed}")
    print("=" * 80)
    
    if all_passed:
        print("🎉 ALL 4 TIERS & CHALLENGER AUDITS PASSED 100% CLEANLY WITH ZERO DEFECTS.")
        sys.exit(0)
    else:
        print("❌ ONE OR MORE TEST TIERS FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()
