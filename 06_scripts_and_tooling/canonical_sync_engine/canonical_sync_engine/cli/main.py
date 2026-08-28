"""
canonical_sync_engine.cli.main
Command-line interface for storage verification, pre-flight self-healing,
quad-vault synchronization, and mesh status reporting.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from canonical_sync_engine import __version__
from canonical_sync_engine.config import SyncConfig
from canonical_sync_engine.engine.coordinator import CanonicalSyncEngine
from canonical_sync_engine.models.artifact import ArtifactType, TruthArtifact
from canonical_sync_engine.models.health import StorageHealthReport
from canonical_sync_engine.models.sync_result import QuadVaultSyncResult
from canonical_sync_engine.verification import StorageVerifier

logger = logging.getLogger("canonical_sync_engine.cli")


def _setup_logging(verbose: bool = False) -> None:
    """Configures console logging formatting and verbosity."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _load_payload(payload_arg: str) -> Dict[str, Any]:
    """
    Parses payload from either:
    1. A file reference starting with '@' (e.g. '@data/payload.json')
    2. An existing file path on disk
    3. An inline JSON string (e.g. '{"key": "value"}')
    """
    payload_str = payload_arg.strip()
    if payload_str.startswith("@"):
        filepath = Path(payload_str[1:]).expanduser().resolve()
        if not filepath.exists():
            raise FileNotFoundError(f"Payload file not found: {filepath}")
        content = filepath.read_text(encoding="utf-8")
        return json.loads(content)

    # Check if it points to an existing file path directly
    potential_file = Path(payload_str).expanduser()
    if potential_file.is_file():
        content = potential_file.read_text(encoding="utf-8")
        return json.loads(content)

    # Otherwise parse as raw JSON string
    return json.loads(payload_str)


# -----------------------------------------------------------------------------
# CLI Subcommand Handlers
# -----------------------------------------------------------------------------

def handle_verify(args: argparse.Namespace, config: SyncConfig) -> int:
    """Handles the 'verify' subcommand."""
    verifier = StorageVerifier(
        obsidian_vault_path=config.obsidian_vault_path,
        pyspark_dataset_path=config.pyspark_dataset_path,
        pyspark_memory_path=config.pyspark_memory_path,
        git_working_tree_path=config.git_repo_path,
        gdrive_mount_path=config.gdrive_mount_path,
        gdrive_fallback_cache_path=config.gdrive_fallback_cache_path,
        min_headroom_gb=config.min_disk_headroom_gb,
    )

    auto_heal = not getattr(args, "no_heal", False)
    scan_remote = getattr(args, "full", False)

    report: StorageHealthReport = verifier.full_verification(
        scan_remote_nodes=scan_remote,
        auto_heal=auto_heal,
    )

    if getattr(args, "json", False):
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(report.summary())

    return 0 if report.is_healthy else 1


def handle_heal(args: argparse.Namespace, config: SyncConfig) -> int:
    """Handles the 'heal' subcommand."""
    verifier = StorageVerifier(
        obsidian_vault_path=config.obsidian_vault_path,
        pyspark_dataset_path=config.pyspark_dataset_path,
        pyspark_memory_path=config.pyspark_memory_path,
        git_working_tree_path=config.git_repo_path,
        gdrive_mount_path=config.gdrive_mount_path,
        gdrive_fallback_cache_path=config.gdrive_fallback_cache_path,
        min_headroom_gb=config.min_disk_headroom_gb,
    )

    actions = verifier.pre_flight_self_heal()

    if getattr(args, "json", False):
        output = {
            "healed_actions": actions,
            "count": len(actions),
            "status": "success",
        }
        print(json.dumps(output, indent=2, sort_keys=True))
    else:
        print("=== Pre-Flight Self-Healing (Rule 6.2) ===")
        if actions:
            print(f"Executed {len(actions)} self-healing action(s):")
            for action in actions:
                print(f"  ✓ {action}")
        else:
            print("Storage is healthy. No self-healing actions were necessary.")

    return 0


def handle_sync(args: argparse.Namespace, config: SyncConfig) -> int:
    """Handles the 'sync' subcommand."""
    # 1. Parse artifact type
    try:
        art_type = ArtifactType.from_string(args.type)
    except ValueError as e:
        print(f"Error: Invalid artifact type: {e}", file=sys.stderr)
        return 1

    # 2. Parse payload
    try:
        payload = _load_payload(args.payload)
    except Exception as e:
        print(f"Error: Failed to parse payload: {e}", file=sys.stderr)
        return 1

    # 3. Parse tags
    tags: List[str] = []
    if getattr(args, "tags", None):
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    # 4. Determine artifact ID
    art_id = getattr(args, "id", None)
    if not art_id:
        art_id = f"art-{art_type.value[:4]}-{uuid.uuid4().hex[:8]}"

    # 5. Construct TruthArtifact
    try:
        artifact = TruthArtifact(
            artifact_id=art_id,
            artifact_type=art_type,
            title=args.title,
            payload=payload,
            source_node=getattr(args, "source", "Mac_Node") or "Mac_Node",
            tags=tags,
        )
    except Exception as e:
        print(f"Error: Invalid artifact parameters: {e}", file=sys.stderr)
        return 1

    # 6. Execute synchronization via CanonicalSyncEngine
    engine = CanonicalSyncEngine(config=config)
    verify_first = not getattr(args, "no_verify", False)
    parallel = not getattr(args, "sequential", False)
    rollback = getattr(args, "rollback", False)

    result: QuadVaultSyncResult = engine.sync_truth_artifact(
        artifact=artifact,
        verify_first=verify_first,
        parallel=parallel,
        rollback_on_failure=rollback,
    )

    # 7. Render output
    if getattr(args, "json", False):
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        status_label = "SUCCESS" if result.success else "FAILED"
        print("=== Quad-Vault Synchronization Result ===")
        print(f"Artifact ID:              {result.artifact_id}")
        print(f"Artifact Type:            {artifact.artifact_type.value}")
        print(f"Title:                    {artifact.title}")
        print(f"Source Node:              {artifact.source_node}")
        print(f"Canonical SHA-256 Hash:   {result.sha256_hash}")
        print(f"Overall Status:           {status_label}")
        print(f"All 4 Vaults Succeeded:   {result.all_vaults_succeeded}")
        print(f"Total Bytes Written:      {result.total_bytes_written}")
        print(f"Total Duration:           {result.total_duration_ms:.2f} ms")
        print("\nVault Targets:")
        for v_name, v_res in result.vault_results.items():
            v_status = "SUCCESS" if v_res.success else "FAILED"
            details = f"({v_res.bytes_written} bytes, {v_res.latency_ms:.1f} ms)"
            if v_res.success:
                print(f"  ✓ [{v_name:8s}] {v_status} {details} -> {v_res.target_path}")
            else:
                print(f"  ✗ [{v_name:8s}] {v_status} -> {v_res.error}")

        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for err in result.errors:
                print(f"  ! {err}")

    return 0 if result.success else 1


def handle_status(args: argparse.Namespace, config: SyncConfig) -> int:
    """Handles the 'status' subcommand."""
    engine = CanonicalSyncEngine(config=config)
    vault_status = engine.get_vault_status()
    fast_path_ok = engine.fast_path_check()
    headroom_ok, free_gb, headroom_violations = engine.verifier.validate_headroom()

    status_data: Dict[str, Any] = {
        "fast_path_healthy": fast_path_ok,
        "disk_free_gb": round(free_gb, 2),
        "headroom_satisfied": headroom_ok,
        "min_headroom_gb": config.min_disk_headroom_gb,
        "vaults": vault_status,
        "violations": headroom_violations,
    }

    if getattr(args, "json", False):
        print(json.dumps(status_data, indent=2, sort_keys=True))
    else:
        print("=== Canonical Storage Status ===")
        print(f"Fast-Path Status (<3ms):  {'HEALTHY' if fast_path_ok else 'DEGRADED'}")
        print(f"Host Free Disk Space:     {free_gb:.2f} GB (Required: {config.min_disk_headroom_gb:.1f} GB)")
        print(f"Headroom Satisfied:       {headroom_ok}")
        print("\nQuad-Vault Status:")
        for v_name, v_info in vault_status.items():
            exists_str = "EXISTS" if v_info.get("exists") else "MISSING"
            writable_str = "WRITABLE" if v_info.get("writable") else "READ-ONLY"
            extra = ""
            if v_name == "gdrive":
                extra = f" [Tier: {v_info.get('active_tier', 'unknown')}]"
            print(f"  - [{v_name:8s}] {exists_str}, {writable_str}{extra}")
            path_key = [k for k in v_info if "path" in k or "dir" in k]
            if path_key:
                print(f"             Path: {v_info[path_key[0]]}")

        if headroom_violations:
            print("\nWarnings / Violations:")
            for v in headroom_violations:
                print(f"  ! {v}")

    return 0


def handle_info(args: argparse.Namespace, config: SyncConfig) -> int:
    """Handles the 'info' subcommand."""
    config_dict = config.to_dict()

    if getattr(args, "json", False):
        print(json.dumps(config_dict, indent=2, sort_keys=True))
    else:
        print(f"=== Canonical Sync Engine Configuration (v{__version__}) ===")
        print(f"Environment:             {config.env}")
        print(f"Auto-Heal Enabled:       {config.auto_heal}")
        print(f"Min Disk Headroom:       {config.min_disk_headroom_gb:.1f} GB")
        print(f"Network Timeout:         {config.network_timeout_sec:.1f} s")
        print("\nVault Paths:")
        print(f"  • Obsidian Vault:      {config.obsidian_vault_path}")
        print(f"  • PySpark Datasets:    {config.pyspark_dataset_path}")
        print(f"  • PySpark Memory:      {config.pyspark_memory_path}")
        print(f"  • Git Working Tree:    {config.git_repo_path}")
        print(f"  • Google Drive Mount:  {config.gdrive_mount_path}")
        print(f"  • Google Drive Cache:  {config.gdrive_fallback_cache_path}")
        print(f"\nMesh Nodes Configured:   {len(config.mesh_nodes)} nodes (L1-L7, GW)")
        for node_id, node in config.mesh_nodes.items():
            print(f"  - [{node_id}] {node.name:18s} (Layer: {node.layer}, IP: {node.local_ip})")

    return 0


# -----------------------------------------------------------------------------
# Parser Construction
# -----------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Constructs the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="canonical-sync",
        description="Canonical Quad-Vault Storage Verification and Synchronization Engine CLI",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose / debug output",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="subcommands",
        description="Valid operations for canonical storage and synchronization",
    )

    # 1. verify
    verify_parser = subparsers.add_parser(
        "verify",
        help="Scans mesh and validates storage health across local and remote vaults",
    )
    verify_parser.add_argument(
        "--full",
        action="store_true",
        help="Perform comprehensive multi-layer remote mesh scan (L1-L7)",
    )
    verify_parser.add_argument(
        "--no-heal",
        action="store_true",
        help="Disable automatic pre-flight self-healing prior to verification",
    )
    verify_parser.add_argument(
        "--json",
        action="store_true",
        help="Output verification report in structured JSON format",
    )

    # 2. heal
    heal_parser = subparsers.add_parser(
        "heal",
        help="Executes pre-flight self-healing routines per Rule 6.2",
    )
    heal_parser.add_argument(
        "--json",
        action="store_true",
        help="Output self-healing results in structured JSON format",
    )

    # 3. sync
    sync_parser = subparsers.add_parser(
        "sync",
        help="Ingests and synchronizes a TruthArtifact across the Quad-Vault ecosystem",
    )
    sync_parser.add_argument(
        "--type",
        required=True,
        help="Artifact type (e.g. truth_audit, ai_debate_consensus, architectural_decision, telemetry_record, lora_pair, benchmark_result)",
    )
    sync_parser.add_argument(
        "--title",
        required=True,
        help="Descriptive title of the truth artifact",
    )
    sync_parser.add_argument(
        "--payload",
        required=True,
        help="JSON payload string, or file path prefixed with '@' (e.g. @data.json)",
    )
    sync_parser.add_argument(
        "--source",
        default="Mac_Node",
        help="Source node identity (default: Mac_Node)",
    )
    sync_parser.add_argument(
        "--id",
        dest="id",
        default=None,
        help="Custom unique artifact ID (auto-generated if omitted)",
    )
    sync_parser.add_argument(
        "--tags",
        default="",
        help="Comma-separated list of tags (e.g. 'audit,consensus,lora')",
    )
    sync_parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip pre-flight storage verification and self-healing",
    )
    sync_parser.add_argument(
        "--sequential",
        action="store_true",
        help="Execute vault synchronization sequentially instead of in parallel",
    )
    sync_parser.add_argument(
        "--rollback",
        action="store_true",
        help="Attempt atomic rollback of written files if any target vault fails",
    )
    sync_parser.add_argument(
        "--json",
        action="store_true",
        help="Output synchronization result in structured JSON format",
    )

    # 4. status
    status_parser = subparsers.add_parser(
        "status",
        help="Shows vault health, disk headroom, and mesh node reachability",
    )
    status_parser.add_argument(
        "--json",
        action="store_true",
        help="Output status overview in structured JSON format",
    )

    # 5. info
    info_parser = subparsers.add_parser(
        "info",
        help="Displays configuration paths, thresholds, and mesh topology",
    )
    info_parser.add_argument(
        "--json",
        action="store_true",
        help="Output configuration details in structured JSON format",
    )

    return parser


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------

def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Main entry point for the canonical-sync CLI.

    Parameters:
        argv: Optional sequence of command-line arguments (uses sys.argv[1:] if None).

    Returns:
        Integer exit status code (0 for success, non-zero for failure).
    """
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    _setup_logging(verbose=getattr(args, "verbose", False))

    if not args.command:
        parser.print_help()
        return 0

    config = SyncConfig.from_env()

    if args.command == "verify":
        return handle_verify(args, config)
    elif args.command == "heal":
        return handle_heal(args, config)
    elif args.command == "sync":
        return handle_sync(args, config)
    elif args.command == "status":
        return handle_status(args, config)
    elif args.command == "info":
        return handle_info(args, config)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
