#!/usr/bin/env python3
"""
================================================================================
LAUBURU-MONOREPO STORAGE MIGRATION E2E TEST RUNNER & SUITE
================================================================================
Automated End-to-End Verification Framework for Native macOS SeaweedFS Deployment
over Thunderbolt 4 Bridge (bridge0).

Methodology (4-Tier Testing):
  - Tier 1: Feature Coverage (Master status, volume allocation, Filer CRUD, S3 API, TB4 bridge0 ingress, launchd autostart)
  - Tier 2: Boundary & Corner Cases (1GB+ large files, 0-byte files, >20 level hierarchies, Unicode/special chars, 50+ concurrent clients)
  - Tier 3: Cross-Feature Combinations (Concurrent Filer R/W during sentinel health probes, TB4 routing isolation avoiding Wi-Fi/Tailscale)
  - Tier 4: Real-World Application Workloads (>2,500 MB/s speed benchmarking, Antigravity swarm workspace stress, SHA256 parity audit)

Usage:
  python3 tests/test_storage_migration_e2e.py [--tier 1,2,3,4] [--json-output report.json]
================================================================================
"""

import os
import sys
import time
import json
import argparse
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Ensure repository root is in sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tests.conftest import (
    DEFAULT_TB4_IP,
    DEFAULT_MASTER_URL,
    DEFAULT_VOLUME_URL,
    DEFAULT_FILER_URL,
    DEFAULT_S3_URL,
    SeaweedFSClient,
    TB4NetworkProbe,
    BenchmarkHelper,
    CryptographicParityAuditor,
)
from tests.test_tier1_features import TestTier1FeatureCoverage
from tests.test_tier2_boundaries import TestTier2BoundaryCases
from tests.test_tier3_combinations import TestTier3Combinations
from tests.test_tier4_workloads import TestTier4RealWorldWorkloads

# Disable pytest double-collection for runner module
__test__ = False

# ANSI Color Codes for Terminal Output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


class MockRequest:
    """Mock pytest Request object for standalone runner invocation."""
    def __init__(self, options: Dict[str, Any]):
        self._options = options

    class Config:
        def __init__(self, opts):
            self._opts = opts
        def getoption(self, name: str, default=None):
            return self._opts.get(name.lstrip("-").replace("-", "_"), default)

    @property
    def config(self):
        return self.Config(self._options)


class StorageMigrationE2ETestRunner:
    """Master Orchestrator and Test Runner for the Storage Migration E2E Suite."""

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.master_url = args.master_url
        self.volume_url = args.volume_url
        self.filer_url = args.filer_url
        self.s3_url = args.s3_url
        self.tb4_ip = args.tb4_ip
        self.json_output = args.json_output
        self.selected_tiers = self._parse_tiers(args.tier)
        
        self.seaweed_client = SeaweedFSClient(
            master_url=self.master_url,
            filer_url=self.filer_url,
            volume_url=self.volume_url,
            s3_url=self.s3_url,
            timeout=15.0
        )
        self.tb4_probe = TB4NetworkProbe()
        self.bench_helper = BenchmarkHelper()
        self.parity_auditor = CryptographicParityAuditor()
        
        self.results: List[Dict[str, Any]] = []

    def _parse_tiers(self, tier_arg: str) -> List[int]:
        if tier_arg.lower() == "all":
            return [1, 2, 3, 4]
        try:
            return [int(t.strip()) for t in tier_arg.split(",") if t.strip()]
        except ValueError:
            print(f"{RED}Invalid tier specification: {tier_arg}. Defaulting to all tiers.{RESET}")
            return [1, 2, 3, 4]

    def log_header(self, title: str):
        print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
        print(f"{BOLD}{CYAN}{title.center(80)}{RESET}")
        print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")

    def run_test_case(self, tier: int, name: str, test_func, *args, **kwargs) -> bool:
        """Executes a single test case with timing, error capture, and structured metrics."""
        print(f"[{CYAN}TIER {tier}{RESET}] Running: {BOLD}{name}{RESET} ...", end=" ", flush=True)
        t0 = time.perf_counter()
        passed = False
        error_msg = None
        tb_str = None

        try:
            test_func(*args, **kwargs)
            passed = True
            duration = time.perf_counter() - t0
            print(f"{GREEN}[PASS]{RESET} ({duration:.3f}s)")
        except Exception as e:
            duration = time.perf_counter() - t0
            passed = False
            error_msg = str(e)
            tb_str = traceback.format_exc()
            print(f"{RED}[FAIL]{RESET} ({duration:.3f}s)")
            print(f"  {RED}Error: {error_msg}{RESET}")
            if self.args.verbose:
                print(f"  {YELLOW}{tb_str}{RESET}")

        self.results.append({
            "tier": tier,
            "name": name,
            "passed": passed,
            "duration_sec": duration,
            "error": error_msg,
            "traceback": tb_str,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        return passed

    def execute(self) -> int:
        """Execute the selected test tiers and generate JSON summary."""
        self.log_header("LAUBURU-MONOREPO STORAGE MIGRATION E2E TEST EXECUTION")
        print(f"{BOLD}Target Configuration:{RESET}")
        print(f"  - SeaweedFS Master URL: {self.master_url}")
        print(f"  - SeaweedFS Filer URL:  {self.filer_url}")
        print(f"  - SeaweedFS Volume URL: {self.volume_url}")
        print(f"  - SeaweedFS S3 URL:     {self.s3_url}")
        print(f"  - TB4 Bridge IP:        {self.tb4_ip}")
        print(f"  - Active Tiers:         {self.selected_tiers}")
        print(f"  - JSON Report Target:   {self.json_output}\n")

        mock_req = MockRequest({
            "source_dir": self.args.source_dir,
            "target_dir": self.args.target_dir,
            "benchmark_size_mb": self.args.benchmark_size_mb,
            "large_file_size": 1024 * 1024 * 1024
        })

        # =========================================================================
        # TIER 1: FEATURE COVERAGE
        # =========================================================================
        if 1 in self.selected_tiers:
            self.log_header("TIER 1: FEATURE COVERAGE")
            t1 = TestTier1FeatureCoverage()
            self.run_test_case(1, "SeaweedFS Master Cluster Status & Topology", t1.test_seaweedfs_master_cluster_status, self.seaweed_client)
            self.run_test_case(1, "SeaweedFS Volume Allocation & FID Generation", t1.test_seaweedfs_volume_allocation, self.seaweed_client)
            self.run_test_case(1, "Filer HTTP API CRUD & Read Parity", t1.test_filer_http_api_crud, self.seaweed_client)
            self.run_test_case(1, "Filer Directory Indexing & JSON Listing", t1.test_filer_directory_indexing_and_json_listing, self.seaweed_client)
            self.run_test_case(1, "S3 Gateway Bucket & Object CRUD", t1.test_s3_api_bucket_and_object_lifecycle, self.seaweed_client)
            self.run_test_case(1, "Thunderbolt 4 (bridge0) Ingress Binding & Ports", t1.test_tb4_bridge0_ingress_binding, self.tb4_probe, self.tb4_ip)
            self.run_test_case(1, "LaunchDaemon Autostart & KeepAlive Plist", t1.test_launchdaemon_autostart_and_keepalive_plist)

        # =========================================================================
        # TIER 2: BOUNDARY & CORNER CASES
        # =========================================================================
        if 2 in self.selected_tiers:
            self.log_header("TIER 2: BOUNDARY & CORNER CASES")
            t2 = TestTier2BoundaryCases()
            self.run_test_case(2, "Large File Streaming Upload & SHA256 Integrity (1GB+)", t2.test_large_file_streaming_upload_and_verification, self.seaweed_client, mock_req)
            self.run_test_case(2, "0-Byte (Empty) File Lifecycle & Metadata", t2.test_zero_byte_file_lifecycle, self.seaweed_client)
            self.run_test_case(2, "Deeply Nested Directory Hierarchy (>20 Levels)", t2.test_deeply_nested_directory_hierarchy, self.seaweed_client)
            self.run_test_case(2, "Unicode, Emojis, and Special Character Filenames", t2.test_unicode_and_special_character_filenames, self.seaweed_client)
            self.run_test_case(2, "High Concurrency Connection Pool Stress (50+ Clients)", t2.test_high_concurrency_connections_stress, self.seaweed_client)

        # =========================================================================
        # TIER 3: CROSS-FEATURE COMBINATIONS
        # =========================================================================
        if 3 in self.selected_tiers:
            self.log_header("TIER 3: CROSS-FEATURE COMBINATIONS")
            t3 = TestTier3Combinations()
            self.run_test_case(3, "Concurrent Filer R/W during Sentinel Probes", t3.test_concurrent_filer_rw_during_sentinel_probes, self.seaweed_client)
            self.run_test_case(3, "Thunderbolt 4 Route Isolation & No Wi-Fi/Tailscale Leakage", t3.test_tb4_route_isolation_and_no_leakage, self.tb4_probe, self.seaweed_client, self.tb4_ip)

        # =========================================================================
        # TIER 4: REAL-WORLD WORKLOADS & PERFORMANCE
        # =========================================================================
        if 4 in self.selected_tiers:
            self.log_header("TIER 4: REAL-WORLD APPLICATION WORKLOADS")
            t4 = TestTier4RealWorldWorkloads()
            self.run_test_case(4, "Monorepo I/O Speed Benchmark (>2,500 MB/s Target)", t4.test_monorepo_io_speed_benchmark, self.bench_helper, mock_req)
            self.run_test_case(4, "Antigravity Agent Swarm Workspace Stress", t4.test_antigravity_agent_workspace_io_stress, self.seaweed_client)
            self.run_test_case(4, "Cryptographic Multi-threaded Data Parity Audit (100%)", t4.test_cryptographic_data_parity_audit, self.parity_auditor, mock_req)

        return self._generate_summary()

    def _generate_summary(self) -> int:
        """Prints formatted summary and writes JSON output report."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        total_duration = sum(r["duration_sec"] for r in self.results)

        self.log_header("TEST EXECUTION SUMMARY")
        print(f"Total Tests Executed: {BOLD}{total}{RESET}")
        print(f"Passed:               {BOLD}{GREEN}{passed}{RESET}")
        print(f"Failed:               {BOLD}{RED}{failed}{RESET}")
        print(f"Total Duration:       {total_duration:.3f}s\n")

        # Per Tier Summary
        tier_counts = {}
        for r in self.results:
            t = r["tier"]
            if t not in tier_counts:
                tier_counts[t] = {"total": 0, "passed": 0, "failed": 0}
            tier_counts[t]["total"] += 1
            if r["passed"]:
                tier_counts[t]["passed"] += 1
            else:
                tier_counts[t]["failed"] += 1

        print(f"{'Tier':<10} | {'Total':<8} | {'Passed':<8} | {'Failed':<8} | {'Status':<10}")
        print(f"{'-'*52}")
        for t in sorted(tier_counts.keys()):
            s = tier_counts[t]
            status_str = f"{GREEN}PASS{RESET}" if s["failed"] == 0 else f"{RED}FAIL{RESET}"
            print(f"Tier {t:<5} | {s['total']:<8} | {s['passed']:<8} | {s['failed']:<8} | {status_str}")
        print()

        # Build JSON report
        report_data = {
            "title": "Lauburu-Monorepo Storage Migration E2E Test Report",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "environment": {
                "tb4_ip": self.tb4_ip,
                "master_url": self.master_url,
                "filer_url": self.filer_url,
                "volume_url": self.volume_url,
                "s3_url": self.s3_url,
                "python_version": sys.version
            },
            "summary": {
                "total_tests": total,
                "passed_tests": passed,
                "failed_tests": failed,
                "total_duration_sec": total_duration,
                "success": (failed == 0)
            },
            "tier_breakdown": tier_counts,
            "test_results": self.results
        }

        try:
            with open(self.json_output, "w") as f:
                json.dump(report_data, f, indent=2)
            print(f"JSON Test Report saved to: {BOLD}{self.json_output}{RESET}")
        except Exception as e:
            print(f"{RED}Failed to write JSON report to {self.json_output}: {e}{RESET}")

        if failed > 0:
            print(f"\n{BOLD}{RED}E2E TEST SUITE COMPLETED WITH FAILURES.{RESET}")
            return 1
        else:
            print(f"\n{BOLD}{GREEN}ALL E2E TESTS COMPLETED SUCCESSFULLY.{RESET}")
            return 0


def main():
    parser = argparse.ArgumentParser(description="Lauburu-Monorepo Storage Migration E2E Test Runner")
    parser.add_argument("--tier", "-t", default="all", help="Comma-separated tiers to run (1,2,3,4 or all)")
    parser.add_argument("--json-output", "-o", default="storage_migration_test_report.json", help="Path for JSON report")
    parser.add_argument("--master-url", default=DEFAULT_MASTER_URL, help="SeaweedFS Master URL")
    parser.add_argument("--volume-url", default=DEFAULT_VOLUME_URL, help="SeaweedFS Volume URL")
    parser.add_argument("--filer-url", default=DEFAULT_FILER_URL, help="SeaweedFS Filer URL")
    parser.add_argument("--s3-url", default=DEFAULT_S3_URL, help="SeaweedFS S3 URL")
    parser.add_argument("--tb4-ip", default=DEFAULT_TB4_IP, help="Thunderbolt 4 Bridge IP")
    parser.add_argument("--source-dir", default="/mnt/dfs_unified", help="Source directory for parity test")
    parser.add_argument("--target-dir", default="/Volumes/Lauburu-Monorepo", help="Target directory for parity test")
    parser.add_argument("--benchmark-size-mb", type=int, default=512, help="Size in MB for I/O benchmark")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose tracebacks")

    args = parser.parse_args()
    runner = StorageMigrationE2ETestRunner(args)
    sys.exit(runner.execute())


if __name__ == "__main__":
    main()
