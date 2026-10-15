#!/usr/bin/env python3
"""
Master E2E Test Suite Runner for Lauburu Life Companion
Executes 4-tier opaque-box test suite and generates structured reports.
"""

import sys
import os
import time
import json
import argparse
import traceback
from pathlib import Path
from typing import Dict, List, Any

# Add harness and tests to Python path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Import tests from tiers
import test_tier1_feature_coverage as t1
import test_tier2_boundary_corner as t2
import test_tier3_cross_feature as t3
import test_tier4_real_world_scenarios as t4

# ANSI Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


class TmpPath:
    """Lightweight tmp_path fixture replacement for direct runner execution."""
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def __truediv__(self, other: str) -> Path:
        return self.base_dir / other


def discover_test_cases() -> Dict[str, List[Dict[str, Any]]]:
    """Catalog of all 50 test cases organized by tier and deliverable."""
    return {
        "Tier 1: Feature Coverage": [
            # R1: Silent Boot Persistence
            {"name": "test_macos_launchagent_plist_structure_and_syntax", "func": t1.test_macos_launchagent_plist_structure_and_syntax, "deliverable": "R1: Silent Boot", "needs_tmp": False},
            {"name": "test_macos_launchagent_silent_execution", "func": t1.test_macos_launchagent_silent_execution, "deliverable": "R1: Silent Boot", "needs_tmp": False},
            {"name": "test_macos_daemon_port_responsiveness", "func": t1.test_macos_daemon_port_responsiveness, "deliverable": "R1: Silent Boot", "needs_tmp": False},
            {"name": "test_android_manifest_boot_permission", "func": t1.test_android_manifest_boot_permission, "deliverable": "R1: Silent Boot", "needs_tmp": False},
            {"name": "test_android_boot_receiver_intent_filter", "func": t1.test_android_boot_receiver_intent_filter, "deliverable": "R1: Silent Boot", "needs_tmp": False},
            {"name": "test_android_boot_receiver_silent_contract", "func": t1.test_android_boot_receiver_silent_contract, "deliverable": "R1: Silent Boot", "needs_tmp": False},
            # R2: Shopify Customer Authentication
            {"name": "test_shopify_graphql_login_endpoint_structure", "func": t1.test_shopify_graphql_login_endpoint_structure, "deliverable": "R2: Shopify Auth", "needs_tmp": False},
            {"name": "test_shopify_dev_token_authentication", "func": t1.test_shopify_dev_token_authentication, "deliverable": "R2: Shopify Auth", "needs_tmp": False},
            {"name": "test_shopify_customer_profile_tier_parsing_pro", "func": t1.test_shopify_customer_profile_tier_parsing_pro, "deliverable": "R2: Shopify Auth", "needs_tmp": False},
            {"name": "test_shopify_customer_profile_tier_parsing_elite", "func": t1.test_shopify_customer_profile_tier_parsing_elite, "deliverable": "R2: Shopify Auth", "needs_tmp": False},
            {"name": "test_shopify_customer_profile_tier_parsing_free", "func": t1.test_shopify_customer_profile_tier_parsing_free, "deliverable": "R2: Shopify Auth", "needs_tmp": False},
            {"name": "test_shopify_token_renewal_mutation", "func": t1.test_shopify_token_renewal_mutation, "deliverable": "R2: Shopify Auth", "needs_tmp": False},
            # R3: Cross-Device Sync & Session Persistence
            {"name": "test_session_storage_serialization_and_restore", "func": t1.test_session_storage_serialization_and_restore, "deliverable": "R3: Cross-Device Sync", "needs_tmp": True},
            {"name": "test_cloud_sync_refreshes_local_customer_tags", "func": t1.test_cloud_sync_refreshes_local_customer_tags, "deliverable": "R3: Cross-Device Sync", "needs_tmp": True},
            {"name": "test_session_token_expiration_validation", "func": t1.test_session_token_expiration_validation, "deliverable": "R3: Cross-Device Sync", "needs_tmp": True},
            {"name": "test_session_clear_on_logout", "func": t1.test_session_clear_on_logout, "deliverable": "R3: Cross-Device Sync", "needs_tmp": True},
            {"name": "test_concurrent_device_session_reconciliation", "func": t1.test_concurrent_device_session_reconciliation, "deliverable": "R3: Cross-Device Sync", "needs_tmp": True},
            # R4: Local E-Commerce Models Integration
            {"name": "test_local_ai_dual_port_routing_hierarchy", "func": t1.test_local_ai_dual_port_routing_hierarchy, "deliverable": "R4: E-Commerce AI", "needs_tmp": False},
            {"name": "test_local_ai_live_inference_port_8083", "func": t1.test_local_ai_live_inference_port_8083, "deliverable": "R4: E-Commerce AI", "needs_tmp": False},
            {"name": "test_canonical_catalog_integrity", "func": t1.test_canonical_catalog_integrity, "deliverable": "R4: E-Commerce AI", "needs_tmp": False},
            {"name": "test_ad_copy_generation_prompt_contract", "func": t1.test_ad_copy_generation_prompt_contract, "deliverable": "R4: E-Commerce AI", "needs_tmp": False},
            {"name": "test_strict_timeout_boundaries_enforced", "func": t1.test_strict_timeout_boundaries_enforced, "deliverable": "R4: E-Commerce AI", "needs_tmp": False},
        ],
        "Tier 2: Boundary & Corner Cases": [
            # R1 Boundary
            {"name": "test_plist_file_missing_or_corrupt_handling", "func": t2.test_plist_file_missing_or_corrupt_handling, "deliverable": "R1: Silent Boot", "needs_tmp": True},
            {"name": "test_launchctl_unloaded_state_handling", "func": t2.test_launchctl_unloaded_state_handling, "deliverable": "R1: Silent Boot", "needs_tmp": False},
            {"name": "test_android_manifest_missing_permission_detection", "func": t2.test_android_manifest_missing_permission_detection, "deliverable": "R1: Silent Boot", "needs_tmp": False},
            {"name": "test_daemon_port_conflict_detection", "func": t2.test_daemon_port_conflict_detection, "deliverable": "R1: Silent Boot", "needs_tmp": False},
            {"name": "test_repeated_launchd_load_idempotency", "func": t2.test_repeated_launchd_load_idempotency, "deliverable": "R1: Silent Boot", "needs_tmp": False},
            # R2 Boundary
            {"name": "test_login_invalid_email_format", "func": t2.test_login_invalid_email_format, "deliverable": "R2: Shopify Auth", "needs_tmp": False},
            {"name": "test_login_incorrect_password", "func": t2.test_login_incorrect_password, "deliverable": "R2: Shopify Auth", "needs_tmp": False},
            {"name": "test_login_empty_or_null_credentials", "func": t2.test_login_empty_or_null_credentials, "deliverable": "R2: Shopify Auth", "needs_tmp": False},
            {"name": "test_expired_access_token_renew_failure", "func": t2.test_expired_access_token_renew_failure, "deliverable": "R2: Shopify Auth", "needs_tmp": False},
            {"name": "test_malformed_dev_token_rejected", "func": t2.test_malformed_dev_token_rejected, "deliverable": "R2: Shopify Auth", "needs_tmp": False},
            # R3 Boundary
            {"name": "test_corrupted_session_storage_recovery", "func": t2.test_corrupted_session_storage_recovery, "deliverable": "R3: Cross-Device Sync", "needs_tmp": True},
            {"name": "test_network_offline_during_cloud_sync", "func": t2.test_network_offline_during_cloud_sync, "deliverable": "R3: Cross-Device Sync", "needs_tmp": True},
            {"name": "test_token_revoked_remotely_triggers_logout", "func": t2.test_token_revoked_remotely_triggers_logout, "deliverable": "R3: Cross-Device Sync", "needs_tmp": True},
            {"name": "test_storage_near_expiration_boundary", "func": t2.test_storage_near_expiration_boundary, "deliverable": "R3: Cross-Device Sync", "needs_tmp": True},
            {"name": "test_missing_required_profile_fields", "func": t2.test_missing_required_profile_fields, "deliverable": "R3: Cross-Device Sync", "needs_tmp": False},
            # R4 Boundary
            {"name": "test_both_ai_ports_offline_fallback", "func": t2.test_both_ai_ports_offline_fallback, "deliverable": "R4: E-Commerce AI", "needs_tmp": False},
            {"name": "test_ai_inference_http_503_recovery", "func": t2.test_ai_inference_http_503_recovery, "deliverable": "R4: E-Commerce AI", "needs_tmp": False},
            {"name": "test_ai_inference_empty_prompt_rejection", "func": t2.test_ai_inference_empty_prompt_rejection, "deliverable": "R4: E-Commerce AI", "needs_tmp": False},
            {"name": "test_ai_inference_timeout_cutoff", "func": t2.test_ai_inference_timeout_cutoff, "deliverable": "R4: E-Commerce AI", "needs_tmp": False},
            {"name": "test_canonical_catalog_invalid_item_lookup", "func": t2.test_canonical_catalog_invalid_item_lookup, "deliverable": "R4: E-Commerce AI", "needs_tmp": False},
        ],
        "Tier 3: Cross-Feature Combinations": [
            {"name": "test_boot_persistence_to_auth_session_restore", "func": t3.test_boot_persistence_to_auth_session_restore, "deliverable": "Cross-Feature", "needs_tmp": True},
            {"name": "test_auth_sync_to_ecommerce_tier_entitlement", "func": t3.test_auth_sync_to_ecommerce_tier_entitlement, "deliverable": "Cross-Feature", "needs_tmp": True},
            {"name": "test_session_restore_to_ai_model_query", "func": t3.test_session_restore_to_ai_model_query, "deliverable": "Cross-Feature", "needs_tmp": True},
            {"name": "test_ai_inference_failure_during_active_session", "func": t3.test_ai_inference_failure_during_active_session, "deliverable": "Cross-Feature", "needs_tmp": True},
            {"name": "test_token_revocation_during_ai_catalog_browsing", "func": t3.test_token_revocation_during_ai_catalog_browsing, "deliverable": "Cross-Feature", "needs_tmp": True},
        ],
        "Tier 4: Real-World Scenarios": [
            {"name": "test_user_journey_cold_boot_login_sync_and_ad_generation", "func": t4.test_user_journey_cold_boot_login_sync_and_ad_generation, "deliverable": "E2E User Journey", "needs_tmp": True},
            {"name": "test_user_journey_offline_start_reconnect_and_sync", "func": t4.test_user_journey_offline_start_reconnect_and_sync, "deliverable": "E2E User Journey", "needs_tmp": True},
            {"name": "test_user_journey_cross_device_tier_upgrade", "func": t4.test_user_journey_cross_device_tier_upgrade, "deliverable": "E2E User Journey", "needs_tmp": True},
        ]
    }


def run_tests(selected_tier: str = "all", verbose: bool = False, fail_fast: bool = False, tmp_dir: Path = None) -> Dict[str, Any]:
    catalog = discover_test_cases()
    results = []
    total_passed = 0
    total_failed = 0
    start_total_time = time.time()

    print(f"\n{BOLD}{CYAN}================================================================================{RESET}")
    print(f"{BOLD}{CYAN}         LAUBURU LIFE COMPANION — 4-TIER OPAQUE-BOX E2E TEST RUNNER            {RESET}")
    print(f"{BOLD}{CYAN}================================================================================{RESET}")
    print(f"Working Directory: {PROJECT_ROOT}")
    print(f"Integrity Mode:    BENCHMARK (Cardinal Rule 1: Zero-Mock & Truth Verification)")
    print(f"Timestamp:         {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Selected Scope:    {selected_tier.upper()}\n")

    for tier_name, test_list in catalog.items():
        tier_num = tier_name.split(":")[0].replace("Tier ", "").strip()
        if selected_tier != "all" and selected_tier != tier_num:
            continue

        print(f"{BOLD}--- {tier_name} ({len(test_list)} tests) ---{RESET}")
        for tc in test_list:
            t_start = time.time()
            passed = False
            err_msg = None

            try:
                if tc["needs_tmp"]:
                    tc_tmp = TmpPath(tmp_dir / tc["name"])
                    tc["func"](tc_tmp)
                else:
                    tc["func"]()
                passed = True
                total_passed += 1
            except Exception as e:
                total_failed += 1
                err_msg = str(e) or type(e).__name__
                if verbose:
                    traceback.print_exc()

            duration_ms = (time.time() - t_start) * 1000.0
            status_str = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"

            result_entry = {
                "name": tc["name"],
                "tier": tier_name,
                "deliverable": tc["deliverable"],
                "passed": passed,
                "duration_ms": round(duration_ms, 2),
                "error": err_msg
            }
            results.append(result_entry)

            print(f"  [{status_str}] {tc['deliverable']:<22} {tc['name']:<55} ({duration_ms:6.1f}ms)")
            if not passed and not verbose:
                print(f"         {YELLOW}Error: {err_msg[:100]}{RESET}")

            if not passed and fail_fast:
                print(f"\n{RED}Execution halted due to --fail-fast{RESET}")
                break

    total_duration = time.time() - start_total_time
    total_tests = total_passed + total_failed
    pass_pct = (total_passed / total_tests * 100.0) if total_tests > 0 else 0.0

    print(f"\n{BOLD}{CYAN}================================================================================{RESET}")
    print(f"{BOLD}SUMMARY:{RESET}")
    print(f"  Total Executed: {total_tests}")
    print(f"  {GREEN}Passed:         {total_passed}{RESET}")
    print(f"  {RED if total_failed > 0 else GREEN}Failed:         {total_failed}{RESET}")
    print(f"  Pass Rate:      {pass_pct:.1f}%")
    print(f"  Total Duration: {total_duration:.2f}s")
    print(f"{BOLD}{CYAN}================================================================================{RESET}\n")

    return {
        "total_tests": total_tests,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "pass_pct": round(pass_pct, 2),
        "total_duration_s": round(total_duration, 2),
        "results": results
    }


def main():
    parser = argparse.ArgumentParser(description="Run Lauburu Life Companion Opaque-Box E2E Test Suite")
    parser.add_argument("--tier", choices=["1", "2", "3", "4", "all"], default="all", help="Select tier to run")
    parser.add_argument("--verbose", action="store_true", help="Print detailed tracebacks")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failure")
    parser.add_argument("--report-json", type=str, default=None, help="Path to write JSON test report")
    args = parser.parse_args()

    import tempfile
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str)
        report = run_tests(
            selected_tier=args.tier,
            verbose=args.verbose,
            fail_fast=args.fail_fast,
            tmp_dir=tmp_dir
        )

    if args.report_json:
        report_path = Path(args.report_json)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"JSON report saved to: {report_path}")

    sys.exit(0 if report["total_failed"] == 0 else 1)


if __name__ == "__main__":
    main()
