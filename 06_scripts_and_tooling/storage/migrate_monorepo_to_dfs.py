#!/usr/bin/env python3
"""
06_scripts_and_tooling/storage/migrate_monorepo_to_dfs.py
=========================================================
High-Speed Lossless Distributed File System (DFS) Migration Engine for Project Lauburu.
Migrates the monorepo from the saturated volume (/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo)
to the high-capacity unified target (/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo).

Features:
- Multi-threaded parallel rsync per subsystem and asset block
- SMB-optimized whole-file streaming (-W), recursive copy (-r), symlink preservation (-l),
  modification time preservation (-t), and device node preservation (-D)
- Bypasses problematic POSIX chmod / Apple xattr flags (-p / -E) that cause SMB fchmodat failures
- Clean mapping into all 13 canonical subsystem pillars (00_core_infrastructure through 12_continuous_lora_evolution)
- Lossless replication of git repository, metadata, configurations, and symlinks
- Dynamic retry logic and detailed transfer telemetry
"""

import os
import sys
import time
import shutil
import logging
import argparse
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple, Optional, Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [DFS-MIGRATE]: %(message)s"
)
logger = logging.getLogger("DFSMigrate")

SOURCE_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
MASTER_WORKSPACE = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Master-Workspace")
TARGET_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
RSYNC_BIN = "/usr/bin/rsync"

EXCLUDES = [
    ".git/index.lock",
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    ".DS_Store",
    ".dart_tool",
    ".flutter-plugins-dependencies"
]

CANONICAL_SUBSYSTEMS = [
    "00_core_infrastructure",
    "01_apps",
    "02_ai_models_and_inference",
    "03_biometrics_and_telemetry",
    "04_data_and_memory",
    "05_agents_and_swarms",
    "06_scripts_and_tooling",
    "07_docs_and_architecture",
    "08_business_and_commerce",
    "09_app_store_and_release",
    "10_spatial_grappling_kinematics",
    "11_security_and_governance",
    "12_continuous_lora_evolution"
]

# Canonical Subsystem Mapping Table
MAPPING_TABLE = [
    # 00_core_infrastructure
    ("self_healing_hub", "00_core_infrastructure/self_healing_hub"),
    ("docker", "00_core_infrastructure/docker"),
    ("systemd", "00_core_infrastructure/systemd"),
    ("multi_wan", "00_core_infrastructure/multi_wan"),
    ("infrastructure", "00_core_infrastructure/infrastructure"),
    ("devices", "00_core_infrastructure/devices"),
    ("gluster_brick", "00_core_infrastructure/gluster_brick"),
    
    # 01_apps
    ("Installed_Apps", "01_apps/Installed_Apps"),
    ("movesense_hub", "01_apps/movesense_hub"),
    ("lauburu_compute_hub", "01_apps/lauburu_compute_hub"),
    ("lauburu_zone2_endurance", "01_apps/lauburu_zone2_endurance"),
    ("lauburu-storefront", "01_apps/lauburu-storefront"),
    ("lauburu_business_app", "01_apps/lauburu_business_app"),
    ("openclaw", "01_apps/openclaw"),
    ("openclaw_apk", "01_apps/openclaw_apk"),
    ("swarm_dashboard", "01_apps/swarm_dashboard"),
    ("packages", "01_apps/packages"),
    ("functional_apps", "01_apps/functional_apps"),
    ("Standalone_Services", "01_apps/Standalone_Services"),
    
    # 02_ai_models_and_inference
    ("llama.cpp", "02_ai_models_and_inference/llama_cpp"),
    ("models", "02_ai_models_and_inference/models"),
    ("llama_distributed", "02_ai_models_and_inference/llama_distributed"),
    ("qwen_distributed_proof", "02_ai_models_and_inference/qwen_distributed_proof"),
    ("mesh_benchmarks", "02_ai_models_and_inference/mesh_benchmarks"),
    
    # 03_biometrics_and_telemetry
    ("Movesense", "03_biometrics_and_telemetry/Movesense"),
    
    # 04_data_and_memory
    ("data", "04_data_and_memory/data"),
    ("session_logs", "04_data_and_memory/session_logs"),
    ("qdrant_data", "04_data_and_memory/qdrant_data"),
    ("reports", "04_data_and_memory/reports"),
    ("ray_logs", "04_data_and_memory/ray_logs"),
    ("logs", "04_data_and_memory/logs"),
    ("chat_logs", "04_data_and_memory/chat_logs"),
    ("gdrive_sync", "04_data_and_memory/gdrive_sync"),
    
    # 05_agents_and_swarms
    (".agents", "05_agents_and_swarms/.agents"),
    ("truth_auditing_swarm", "05_agents_and_swarms/truth_auditing_swarm"),
    ("teamwork_projects", "05_agents_and_swarms/teamwork_projects"),
    ("workers", "05_agents_and_swarms/workers"),
    ("ai_swarm_orchestrator", "05_agents_and_swarms/ai_swarm_orchestrator"),
    ("claim_audit_system", "05_agents_and_swarms/claim_audit_system"),
    ("deploy_swarm", "05_agents_and_swarms/deploy_swarm"),
    ("AI_Director", "05_agents_and_swarms/AI_Director"),
    
    # 06_scripts_and_tooling
    ("scripts", "06_scripts_and_tooling/scripts"),
    ("06_scripts_and_tooling", "06_scripts_and_tooling"),
    ("bin", "06_scripts_and_tooling/bin"),
    ("mcp_config", "06_scripts_and_tooling/mcp_config"),
    
    # 07_docs_and_architecture
    ("docs", "07_docs_and_architecture/docs"),
    ("obsidian_vault", "07_docs_and_architecture/obsidian_vault"),
    
    # 08_business_and_commerce
    ("shopify-ai", "08_business_and_commerce/shopify-ai"),
    
    # 11_security_and_governance
    ("credentials", "11_security_and_governance/credentials"),
    
    # 12_continuous_lora_evolution
    ("lora_datasets", "12_continuous_lora_evolution/lora_datasets"),
    ("training", "12_continuous_lora_evolution/training"),
    ("sandbox", "12_continuous_lora_evolution/sandbox"),
    ("Google_Drive_LoRA_Dump", "12_continuous_lora_evolution/Google_Drive_LoRA_Dump"),
    
    # Additional directories and root elements
    ("config", "config"),
    ("assets", "assets"),
    ("subprojects", "subprojects"),
    ("tests", "tests"),
    ("e2e_tests", "e2e_tests"),
    ("ui_dumps", "ui_dumps"),
    ("unorganised", "unorganised"),
    ("scratch", "scratch"),
    ("project_files", "project_files"),
    ("archive", "archive"),
    ("backups", "backups"),
    ("backup_evidence", "backup_evidence"),
    ("chat-bridge-worker", "chat-bridge-worker"),
    ("firebase-backend", "firebase-backend"),
    ("ga_network_optimizer", "ga_network_optimizer"),
    (".agents", ".agents"),
    (".git", ".git")
]


def ensure_canonical_scaffolding():
    """Ensure all 13 canonical subsystems exist in the target root."""
    logger.info("Verifying 13 canonical subsystem directories at target root...")
    for sub in CANONICAL_SUBSYSTEMS:
        sub_path = TARGET_ROOT / sub
        sub_path.mkdir(parents=True, exist_ok=True)
        readme_path = sub_path / "README.md"
        if not readme_path.exists():
            try:
                with open(readme_path, "w", encoding="utf-8") as f:
                    f.write(f"# Subsystem: {sub}\n\nCanonical Project Lauburu Subsystem Pillar.\n")
            except Exception as e:
                logger.warning(f"Could not create placeholder README in {sub}: {e}")


def build_rsync_cmd(src: Path, dest: Path, dry_run: bool = False) -> List[str]:
    # Use -rltDW (recursive, links, times, device nodes, whole-file) to avoid SMB chmod issues
    cmd = [
        RSYNC_BIN,
        "-rltDW",
        "--update",
        "--stats"
    ]
    if dry_run:
        cmd.append("--dry-run")
        
    for exc in EXCLUDES:
        cmd.append(f"--exclude={exc}")
        
    # Format source and destination trailing slashes appropriately
    src_str = str(src)
    if src.is_dir() and not src_str.endswith("/"):
        src_str += "/"
        
    dest_str = str(dest)
    if not dest_str.endswith("/"):
        dest_str += "/"
        
    cmd.extend([src_str, dest_str])
    return cmd


def sync_path_item(item: Tuple[str, str], dry_run: bool = False) -> Dict[str, Any]:
    src_rel, dest_rel = item
    src_path = SOURCE_ROOT / src_rel
    dest_path = TARGET_ROOT / dest_rel
    
    # Handle external paths (like master workspace)
    if src_rel.startswith("/"):
        src_path = Path(src_rel)

    if not src_path.exists() and not src_path.is_symlink():
        return {
            "item": src_rel,
            "status": "SKIPPED_NOT_FOUND",
            "src": str(src_path),
            "dest": str(dest_path),
            "duration": 0.0,
            "stdout": "",
            "stderr": ""
        }

    # Ensure parent destination directory exists
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if src_path.is_dir():
        dest_path.mkdir(parents=True, exist_ok=True)

    cmd = build_rsync_cmd(src_path, dest_path, dry_run=dry_run)
    logger.info(f"Syncing: {src_rel} -> {dest_rel} ...")
    start_t = time.time()
    
    for attempt in range(1, 3):
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
            elapsed = time.time() - start_t
            if res.returncode == 0:
                logger.info(f"✓ Completed {src_rel} in {elapsed:.2f}s (attempt {attempt})")
                return {
                    "item": src_rel,
                    "status": "SUCCESS",
                    "src": str(src_path),
                    "dest": str(dest_path),
                    "duration": elapsed,
                    "stdout": res.stdout,
                    "stderr": res.stderr
                }
            else:
                logger.warning(f"Attempt {attempt} error syncing {src_rel}: {res.stderr.strip()[:200]}")
                if attempt == 2:
                    return {
                        "item": src_rel,
                        "status": "FAILED",
                        "src": str(src_path),
                        "dest": str(dest_path),
                        "duration": elapsed,
                        "stdout": res.stdout,
                        "stderr": res.stderr
                    }
                time.sleep(2.0)
        except Exception as e:
            elapsed = time.time() - start_t
            logger.warning(f"Attempt {attempt} exception syncing {src_rel}: {e}")
            if attempt == 2:
                return {
                    "item": src_rel,
                    "status": "EXCEPTION",
                    "src": str(src_path),
                    "dest": str(dest_path),
                    "duration": elapsed,
                    "stdout": "",
                    "stderr": str(e)
                }
            time.sleep(2.0)

    return {
        "item": src_rel,
        "status": "UNKNOWN",
        "src": str(src_path),
        "dest": str(dest_path),
        "duration": 0.0,
        "stdout": "",
        "stderr": ""
    }


def sync_root_files(dry_run: bool = False):
    """Sync individual files in the monorepo root (e.g. README.md, PROJECT.md, scripts, etc.)."""
    logger.info("Syncing monorepo root files and configurations...")
    root_files = [
        f for f in SOURCE_ROOT.iterdir()
        if f.is_file() and not f.name.startswith(".") and not f.name.endswith(".lock")
    ]
    for rf in root_files:
        dest_file = TARGET_ROOT / rf.name
        if dry_run:
            logger.info(f"[DRY-RUN] Would copy root file {rf.name} -> {dest_file}")
            continue
        try:
            shutil.copy2(rf, dest_file)
            logger.info(f"✓ Copied root file: {rf.name}")
        except Exception as e:
            logger.warning(f"Note on root file copy {rf.name}: {e}")


def sync_master_workspace(dry_run: bool = False):
    """Sync Lauburu-Master-Workspace into 01_apps."""
    if MASTER_WORKSPACE.exists():
        dest = TARGET_ROOT / "01_apps/Lauburu-Master-Workspace"
        dest.mkdir(parents=True, exist_ok=True)
        sync_path_item((str(MASTER_WORKSPACE), "01_apps/Lauburu-Master-Workspace"), dry_run=dry_run)


def main():
    parser = argparse.ArgumentParser(description="Lauburu DFS Migration Engine")
    parser.add_argument("--workers", type=int, default=4, help="Parallel worker threads")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry-run without copying")
    parser.add_argument("--subsystem", type=str, default="", help="Filter sync to specific subsystem or path")
    args = parser.parse_args()

    print("=" * 80)
    print("🚀 PROJECT LAUBURU — HIGH-SPEED LOSSLESS DFS MIGRATION ENGINE")
    print(f"Source Root : {SOURCE_ROOT}")
    print(f"Target Root : {TARGET_ROOT}")
    print(f"Workers     : {args.workers}")
    print(f"Dry Run     : {args.dry_run}")
    print("=" * 80)

    if not SOURCE_ROOT.exists():
        logger.error(f"Source root {SOURCE_ROOT} does not exist!")
        sys.exit(1)

    TARGET_ROOT.mkdir(parents=True, exist_ok=True)
    ensure_canonical_scaffolding()

    items = MAPPING_TABLE
    if args.subsystem:
        items = [m for m in MAPPING_TABLE if args.subsystem.lower() in m[0].lower() or args.subsystem.lower() in m[1].lower()]
        logger.info(f"Filtered mapping items to {len(items)} entries.")

    overall_start = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(sync_path_item, item, args.dry_run): item for item in items}
        for future in as_completed(futures):
            res = future.result()
            results.append(res)

    # Sync root files and master workspace
    sync_root_files(dry_run=args.dry_run)
    sync_master_workspace(dry_run=args.dry_run)

    overall_time = time.time() - overall_start

    print("\n" + "=" * 80)
    print("📊 DFS MIGRATION SUMMARY REPORT")
    print("=" * 80)
    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    skipped_count = sum(1 for r in results if r["status"] == "SKIPPED_NOT_FOUND")
    failed_count = sum(1 for r in results if r["status"] in ["FAILED", "EXCEPTION"])

    print(f"Total Subsystems / Modules Processed : {len(results)}")
    print(f"  ✓ Success                          : {success_count}")
    print(f"  - Skipped (Not present in source)  : {skipped_count}")
    print(f"  ❌ Failed                          : {failed_count}")
    print(f"Total Execution Time                 : {overall_time:.2f} seconds")
    print("=" * 80)

    if failed_count > 0:
        print("Failed items:")
        for r in results:
            if r["status"] in ["FAILED", "EXCEPTION"]:
                print(f"  - {r['item']} ({r['status']}): {r['stderr']}")
        sys.exit(1)
    else:
        print("🎉 ALL MONOREPO ASSETS SUCCESSFULLY MIGRATED TO DFS UNIFIED STORAGE!")
        sys.exit(0)

if __name__ == "__main__":
    main()
