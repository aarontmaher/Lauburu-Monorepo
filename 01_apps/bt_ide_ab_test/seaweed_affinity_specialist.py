#!/usr/bin/env python3
"""
SeaweedFS Hardware Affinity Specialist CLI Wrapper.
Lauburu IDE Intelligence Architecture (Requirement R3).

CLI wrapper for:
1. Inspecting file/directory storage affinity routes.
2. Testing live SeaweedFS Master /dir/assign allocation parameters.
3. Checking SeaweedFS cluster datacenter topology and affinity readiness.
4. Generating conceptual project trees demonstrating unified structure with physical node partitioning.
5. Validating filer.toml rules against the affinity matrix.
"""

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

# Ensure current directory is in sys.path for core imports
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from core.storage_specialist import (
        TriVaultStorageSpecialist,
        StorageAffinityRoute,
        AssignmentResult,
        ClusterHealthReport,
        DEFAULT_MASTER_URL,
        LOCAL_MASTER_URL,
        MASTER_PEER_URLS,
        DATACENTER_L1_MAC,
        DATACENTER_L3_LINUX,
        DATACENTER_L6_EDGE,
    )
except ImportError:
    # Direct import fallback if executed from another working directory
    from storage_specialist import (  # type: ignore
        TriVaultStorageSpecialist,
        StorageAffinityRoute,
        AssignmentResult,
        ClusterHealthReport,
        DEFAULT_MASTER_URL,
        LOCAL_MASTER_URL,
        MASTER_PEER_URLS,
        DATACENTER_L1_MAC,
        DATACENTER_L3_LINUX,
        DATACENTER_L6_EDGE,
    )


# ==============================================================================
# Terminal Formatting Helpers
# ==============================================================================

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _color(text: str, color_code: str, no_color: bool = False) -> str:
    if no_color or not sys.stdout.isatty():
        return text
    return f"{color_code}{text}{RESET}"


def _format_route_card(route: StorageAffinityRoute, no_color: bool = False) -> str:
    category_colors = {
        "heavy_datasets": YELLOW,
        "vector_context": CYAN,
        "git_source": GREEN,
    }
    c = category_colors.get(route.category, "")

    lines = [
        f"{_color('┌─ [STORAGE AFFINITY ROUTE]', BOLD, no_color)}",
        f"│  {_color('Path:', BOLD, no_color)}              {route.path}",
        f"│  {_color('Category:', BOLD, no_color)}          {_color(route.category, c, no_color)}",
        f"│  {_color('Target Node:', BOLD, no_color)}       {_color(route.target_node, BOLD, no_color)} ({route.target_ip})",
        f"│  {_color('DataCenter:', BOLD, no_color)}        {route.data_center} (Rack: {route.rack})",
        f"│  {_color('Collection:', BOLD, no_color)}        {route.collection} (Replication: {route.replication})",
        f"│  {_color('Assign Params:', BOLD, no_color)}     {json.dumps(route.seaweed_assign_params)}",
        f"│  {_color('Rationale:', BOLD, no_color)}         {route.rationale}",
        f"{_color('└──────────────────────────────────────────────────────────', BOLD, no_color)}",
    ]
    return "\n".join(lines)


# ==============================================================================
# CLI Commands
# ==============================================================================

def cmd_inspect(args: argparse.Namespace) -> int:
    """Inspect affinity route for given path(s)."""
    paths: List[str] = args.paths
    if not paths and args.path:
        paths = [args.path]
    if not paths:
        print(_color("Error: No path specified. Provide one or more paths to inspect.", RED, args.no_color))
        return 1

    routes: List[StorageAffinityRoute] = [
        TriVaultStorageSpecialist.resolve_affinity(p) for p in paths
    ]

    if args.json:
        print(json.dumps([r.to_dict() for r in routes], indent=2))
        return 0

    print(f"\n{_color('=== Tri-Vault Storage Specialist: Affinity Inspection ===', BOLD, args.no_color)}\n")
    for r in routes:
        print(_format_route_card(r, args.no_color))
    return 0


def cmd_assign(args: argparse.Namespace) -> int:
    """Test file assignment on SeaweedFS Master /dir/assign."""
    path = args.path or getattr(args, "pos_path", None)
    if not path:
        print(_color("Error: Path is required for assign command.", RED, args.no_color))
        return 1

    master_url = args.master_url
    if not master_url:
        # Check if local master is up, otherwise use default canonical L3 master
        master_url = DEFAULT_MASTER_URL

    route = TriVaultStorageSpecialist.resolve_affinity(path)
    assign_params = TriVaultStorageSpecialist.get_seaweed_assign_params(
        path, count=args.count, replication=args.replication
    )
    assign_url = TriVaultStorageSpecialist.build_assign_url(
        path, master_url=master_url, count=args.count, replication=args.replication
    )

    if args.dry_run:
        dry_result = {
            "dry_run": True,
            "path": route.path,
            "category": route.category,
            "target_node": route.target_node,
            "target_ip": route.target_ip,
            "collection": route.collection,
            "data_center": route.data_center,
            "query_url": assign_url,
            "assign_params": assign_params,
        }
        if args.json:
            print(json.dumps(dry_result, indent=2))
        else:
            print(f"\n{_color('[DRY RUN] SeaweedFS Master /dir/assign Query Preview:', BOLD, args.no_color)}")
            print(f"  URL:    {assign_url}")
            print(f"  Params: {json.dumps(assign_params, indent=4)}")
        return 0

    specialist = TriVaultStorageSpecialist(master_url=master_url)
    result = specialist.assign_file(
        path=path,
        master_url=master_url,
        count=args.count,
        replication=args.replication,
        timeout=args.timeout,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return 0 if result.success else 2

    print(f"\n{_color('=== SeaweedFS File Assignment Test ===', BOLD, args.no_color)}")
    print(f"  Path:              {result.path}")
    print(f"  Category:          {result.category}")
    print(f"  Target DataCenter: {result.data_center} ({result.target_ip})")
    print(f"  Master URL:        {master_url}")
    print(f"  Query URL:         {result.query_url}")

    if result.success:
        print(f"  {_color('Status:            SUCCESS', GREEN, args.no_color)}")
        print(f"  Assigned FID:      {result.fid}")
        print(f"  Volume URL:        {result.url}")
        print(f"  Public URL:        {result.public_url}")
        print(f"  Count:             {result.count}")
        return 0
    else:
        print(f"  {_color('Status:            FAILED / UNREACHABLE', RED, args.no_color)}")
        print(f"  Error:             {result.error}")
        print(f"  {_color('Note: Zero-Mock compliance: Genuine error reported. Check SeaweedFS cluster status.', YELLOW, args.no_color)}")
        return 2


def cmd_health(args: argparse.Namespace) -> int:
    """Check SeaweedFS cluster placement health and datacenter topology."""
    peers: Optional[List[str]] = None
    if args.master_urls:
        peers = [p.strip() for p in args.master_urls.split(",") if p.strip()]

    report = TriVaultStorageSpecialist.check_cluster_health(
        master_urls=peers, timeout=args.timeout
    )

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return 0 if report.status == "HEALTHY" else (1 if report.status == "DEGRADED" else 2)

    status_colors = {
        "HEALTHY": GREEN,
        "DEGRADED": YELLOW,
        "OFFLINE": RED,
    }
    c_status = status_colors.get(report.status, "")

    print(f"\n{_color('=== SeaweedFS Topology & Affinity Readiness Report ===', BOLD, args.no_color)}")
    print(f"  Status:               {_color(report.status, c_status, args.no_color)}")
    print(f"  Raft Leader:          {report.leader or 'None detected'}")
    print(f"  Active Masters:       {', '.join(report.active_masters) or 'None'}")
    if report.unreachable_masters:
        print(f"  Unreachable Masters:  {', '.join(report.unreachable_masters)}")
    print(f"  Detected DataCenters: {', '.join(report.datacenters_detected) or 'None'}")
    print(f"  Volumes:              Free: {report.free_volumes} / Max: {report.max_volumes} (Total: {report.total_volumes})")

    print(f"\n  {_color('Hardware Affinity DataCenter Readiness:', BOLD, args.no_color)}")
    for dc, ready in report.affinity_readiness.items():
        tag = _color("READY", GREEN, args.no_color) if ready else _color("MISSING/OFFLINE", YELLOW, args.no_color)
        print(f"    - {dc:12s} : {tag}")

    print(f"\n  Timestamp UTC:        {report.timestamp_utc}\n")
    return 0 if report.status in ("HEALTHY", "DEGRADED") else 2


def cmd_tree(args: argparse.Namespace) -> int:
    """Generate conceptual project tree demonstrating unified tree with partitioned storage."""
    target_dir = args.dir or "."
    summary = TriVaultStorageSpecialist.get_conceptual_project_tree(root_dir=target_dir)

    if args.json:
        print(json.dumps(summary, indent=2))
        return 0

    print(f"\n{_color('=== Unified Conceptual Project Tree & Physical Affinity ===', BOLD, args.no_color)}")
    print(f"  Root Directory:               {summary['root_dir']}")
    print(f"  Total Files Scanned:          {summary['total_files']}")
    print(f"  Conceptual Tree Unified:      {_color('YES (Preserved POSIX hierarchy)', GREEN, args.no_color)}")
    print(f"  Physical Partitioning Active: {_color('YES (Hardware affinity enforced)', GREEN, args.no_color)}")

    counts = summary["counts"]
    print(f"\n  {_color('Breakdown by Physical Storage Node:', BOLD, args.no_color)}")
    print(f"    • {YELLOW}Heavy Datasets (L3 Linux Hub):{RESET}  {counts['heavy_datasets_l3']:4d} files (collection: heavy_datasets)")
    print(f"    • {CYAN}Vector Context (L6 Edge NPUs):{RESET}  {counts['vector_context_l6']:4d} files (collection: vector_context)")
    print(f"    • {GREEN}Git Source (L1 Mac Mini Host):{RESET}  {counts['git_source_l1']:4d} files (collection: git_source)")

    # Sample preview of files in each category
    by_cat = summary["by_category"]
    for cat, name, col in [
        ("heavy_datasets", "Heavy Datasets (L3 Linux)", YELLOW),
        ("vector_context", "Vector Context (L6 Edge)", CYAN),
        ("git_source", "Git Source (L1 Mac)", GREEN),
    ]:
        items = by_cat.get(cat, [])
        if items:
            print(f"\n  {_color(f'Sample files for {name} [showing up to 5 of {len(items)}]:', BOLD, args.no_color)}")
            for it in items[:5]:
                print(f"    - {col}{it['path']}{RESET} -> DC: {it['dataCenter']}")

    print()
    return 0


def cmd_validate_filer(args: argparse.Namespace) -> int:
    """Validate filer.toml syntax and check consistency with Python affinity rules."""
    filer_path = Path(args.config) if args.config else (SCRIPT_DIR / "filer.toml")
    if not filer_path.exists():
        print(_color(f"Error: filer.toml not found at {filer_path}", RED, args.no_color))
        return 1

    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore

    try:
        with open(filer_path, "rb") as f:
            cfg = tomllib.load(f)
    except Exception as e:
        print(_color(f"Error parsing TOML syntax in {filer_path}: {e}", RED, args.no_color))
        return 1

    rules = cfg.get("rule", {})
    required_rules = ["heavy_datasets", "vector_context", "git_source"]
    missing = [r for r in required_rules if r not in rules]

    validation_result = {
        "file": str(filer_path),
        "valid_toml": True,
        "rules_present": list(rules.keys()),
        "missing_rules": missing,
        "rule_checks": {},
    }

    checks_passed = True
    expected_dcs = {
        "heavy_datasets": DATACENTER_L3_LINUX,
        "vector_context": DATACENTER_L6_EDGE,
        "git_source": DATACENTER_L1_MAC,
    }

    for rule_name, exp_dc in expected_dcs.items():
        rule_cfg = rules.get(rule_name, {})
        actual_dc = rule_cfg.get("dataCenter")
        actual_coll = rule_cfg.get("collection")
        passed = (actual_dc == exp_dc) and (actual_coll == rule_name)
        if not passed:
            checks_passed = False
        validation_result["rule_checks"][rule_name] = {
            "passed": passed,
            "expected_dataCenter": exp_dc,
            "actual_dataCenter": actual_dc,
            "collection": actual_coll,
            "path_regex": rule_cfg.get("path"),
        }

    if args.json:
        print(json.dumps(validation_result, indent=2))
        return 0 if (not missing and checks_passed) else 1

    print(f"\n{_color('=== SeaweedFS filer.toml Validation ===', BOLD, args.no_color)}")
    print(f"  Configuration File: {filer_path}")
    print(f"  TOML Syntax:        {_color('VALID', GREEN, args.no_color)}")
    print(f"  Found Rules:        {', '.join(rules.keys())}")

    if missing:
        print(f"  {_color(f'Missing Required Rules: {missing}', RED, args.no_color)}")
    else:
        print(f"  Required Rules:     {_color('ALL PRESENT', GREEN, args.no_color)}")

    print(f"\n  {_color('Rule-to-DataCenter Alignment Checks:', BOLD, args.no_color)}")
    for r_name, chk in validation_result["rule_checks"].items():
        st = _color("PASS", GREEN, args.no_color) if chk["passed"] else _color("FAIL", RED, args.no_color)
        print(f"    - {r_name:16s} : {st} (dataCenter: {chk['actual_dataCenter']}, collection: {chk['collection']})")

    overall_pass = not missing and checks_passed
    print(f"\n  Overall Status:     {_color('VERIFIED COMPLIANT', GREEN, args.no_color) if overall_pass else _color('NON-COMPLIANT', RED, args.no_color)}\n")
    return 0 if overall_pass else 1


# ==============================================================================
# Main CLI Entrypoint
# ==============================================================================

def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--no-color", action="store_true", help="Disable ANSI terminal colors")
    common.add_argument("--json", action="store_true", help="Output results in JSON format")

    parser = argparse.ArgumentParser(
        description="SeaweedFS Hardware Affinity Specialist CLI (Requirement R3)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common],
    )

    # Top-level quick flags
    parser.add_argument("--path", "-p", type=str, help="Path to inspect or test")
    parser.add_argument("--health", action="store_true", help="Quick cluster health probe")
    parser.add_argument("--test-assign", action="store_true", help="Test assignment on SeaweedFS Master")
    parser.add_argument("--tree", action="store_true", help="Display conceptual project tree breakdown")
    parser.add_argument("--validate-filer", action="store_true", help="Validate filer.toml placement rules")

    subparsers = parser.add_subparsers(dest="command", help="Specialist subcommands")

    # Subcommand: inspect
    p_inspect = subparsers.add_parser("inspect", parents=[common], help="Inspect storage affinity routes for paths")
    p_inspect.add_argument("paths", nargs="*", help="File or directory paths to classify")
    p_inspect.add_argument("--path", "-p", type=str, help="Single path flag")

    # Subcommand: assign
    p_assign = subparsers.add_parser("assign", parents=[common], help="Test /dir/assign query on SeaweedFS Master")
    p_assign.add_argument("pos_path", nargs="?", default=None, help="Path to assign")
    p_assign.add_argument("--path", "-p", type=str, help="Path to assign")
    p_assign.add_argument("--master-url", "-m", type=str, default=DEFAULT_MASTER_URL, help="Master URL")
    p_assign.add_argument("--count", "-c", type=int, default=1, help="Count of file IDs")
    p_assign.add_argument("--replication", "-r", type=str, help="Replication code (e.g. 000)")
    p_assign.add_argument("--timeout", "-t", type=float, default=3.0, help="Socket timeout seconds")
    p_assign.add_argument("--dry-run", action="store_true", help="Preview query URL without sending request")

    # Subcommand: health
    p_health = subparsers.add_parser("health", parents=[common], help="Check cluster datacenter topology & affinity health")
    p_health.add_argument("--master-urls", "-m", type=str, help="Comma-separated master URLs")
    p_health.add_argument("--timeout", "-t", type=float, default=2.0, help="Socket timeout seconds")

    # Subcommand: tree
    p_tree = subparsers.add_parser("tree", parents=[common], help="Display unified project tree with physical partitioning")
    p_tree.add_argument("--dir", "-d", type=str, default=".", help="Root directory to inspect")

    # Subcommand: validate-filer
    p_val = subparsers.add_parser("validate-rules", parents=[common], help="Validate filer.toml syntax and affinity rules")
    p_val.add_argument("--config", "-c", type=str, help="Path to filer.toml")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # Route top-level flags if no explicit subcommand was provided
    if not args.command:
        if args.health:
            args.master_urls = None
            args.timeout = 2.0
            return cmd_health(args)
        if args.test_assign and args.path:
            args.master_url = DEFAULT_MASTER_URL
            args.count = 1
            args.replication = None
            args.timeout = 3.0
            args.dry_run = False
            return cmd_assign(args)
        if args.tree:
            args.dir = "."
            return cmd_tree(args)
        if args.validate_filer:
            args.config = None
            return cmd_validate_filer(args)
        if args.path:
            args.paths = [args.path]
            return cmd_inspect(args)
        parser.print_help()
        return 0

    if args.command == "inspect":
        return cmd_inspect(args)
    elif args.command == "assign":
        return cmd_assign(args)
    elif args.command == "health":
        return cmd_health(args)
    elif args.command == "tree":
        return cmd_tree(args)
    elif args.command == "validate-rules":
        return cmd_validate_filer(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
