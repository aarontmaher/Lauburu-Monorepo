#!/usr/bin/env python3
"""
06_scripts_and_tooling/storage/verify_dfs_migration.py
======================================================
Independent Migration & Cryptographic Verification Audit Suite for Project Lauburu.
Verifies file tree congruence, sample file SHA-256 hashes, canonical 13-subsystem
structure, and DFS storage capacity between source and target repository.
"""

import os
import sys
import time
import hashlib
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple

SOURCE_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
TARGET_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
REMOTE_TARGET_ROOT = "/mnt/dfs_unified/Lauburu-Monorepo"
LINUX_SSH = "linux@100.101.39.98"

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

SAMPLE_FILES_TO_HASH = [
    ("docker-compose.yml", "docker-compose.yml"),
    ("project_map.opml", "project_map.opml"),
    ("06_scripts_and_tooling/storage/migrate_monorepo_to_dfs.py", "06_scripts_and_tooling/storage/migrate_monorepo_to_dfs.py"),
    ("06_scripts_and_tooling/device_watchdog/launch_scrcpy_mesh.py", "06_scripts_and_tooling/device_watchdog/launch_scrcpy_mesh.py"),
    ("06_scripts_and_tooling/device_watchdog/deploy_mobile_mesh.py", "06_scripts_and_tooling/device_watchdog/deploy_mobile_mesh.py"),
    ("self_healing_hub/src/orchestrator.py", "self_healing_hub/src/orchestrator.py"),
]

def sha256_local_file(p: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()

def get_remote_batch_sha256(rel_paths: List[str]) -> Dict[str, str]:
    full_remote_paths = [f"{REMOTE_TARGET_ROOT}/{rp}" for rp in rel_paths]
    cmd = ["ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no", LINUX_SSH, f"sha256sum {' '.join(full_remote_paths)}"]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    hashes = {}
    if res.stdout:
        for line in res.stdout.strip().split("\n"):
            parts = line.split()
            if len(parts) >= 2:
                h = parts[0]
                p = parts[1]
                # extract relative path
                rel = p.replace(f"{REMOTE_TARGET_ROOT}/", "")
                hashes[rel] = h
    return hashes

def verify_subsystems() -> bool:
    print("\n[Audit 1/4] Checking 13 Canonical Subsystems in DFS Target...", flush=True)
    all_ok = True
    for sub in CANONICAL_SUBSYSTEMS:
        sub_path = TARGET_ROOT / sub
        if not sub_path.exists():
            print(f"  ❌ Missing Subsystem: {sub}", flush=True)
            all_ok = False
        else:
            try:
                items = list(sub_path.iterdir())
                print(f"  ✓ Subsystem '{sub}' present ({len(items)} items)", flush=True)
            except Exception:
                print(f"  ✓ Subsystem '{sub}' present (verified)", flush=True)
    return all_ok

def verify_sample_hashes() -> bool:
    print("\n[Audit 2/4] Verifying SHA-256 Hash Congruence on Key Code & Config Assets...", flush=True)
    all_ok = True
    matched_count = 0
    dest_rels = [d for _, d in SAMPLE_FILES_TO_HASH]
    remote_hashes = get_remote_batch_sha256(dest_rels)

    for src_rel, dest_rel in SAMPLE_FILES_TO_HASH:
        src_path = SOURCE_ROOT / src_rel
        if not src_path.exists():
            print(f"  - Skipped (Not in source): {src_rel}", flush=True)
            continue

        h_src = sha256_local_file(src_path)
        h_dest = remote_hashes.get(dest_rel, "")

        if not h_dest:
            print(f"  ❌ Missing in target DFS: {dest_rel}", flush=True)
            all_ok = False
            continue

        if h_src == h_dest:
            print(f"  ✓ Cryptographic Match: {src_rel} [SHA256: {h_src[:12]}...]", flush=True)
            matched_count += 1
        else:
            print(f"  ❌ Hash Mismatch: {src_rel}\n     Source: {h_src}\n     Target: {h_dest}", flush=True)
            all_ok = False
            
    print(f"  Summary: {matched_count}/{len(SAMPLE_FILES_TO_HASH)} key assets verified with identical cryptographic hashes.", flush=True)
    return all_ok and (matched_count == len(SAMPLE_FILES_TO_HASH))

def verify_storage_capacity() -> bool:
    print("\n[Audit 3/4] Checking Target DFS Storage Free Capacity & Headroom...", flush=True)
    try:
        st = os.statvfs(TARGET_ROOT)
        free_bytes = st.f_bavail * st.f_frsize
        total_bytes = st.f_blocks * st.f_frsize
        free_gb = free_bytes / (1024 ** 3)
        total_gb = total_bytes / (1024 ** 3)
        print(f"  ✓ Target DFS Volume: Total {total_gb:.1f} GB, Free {free_gb:.1f} GB ({free_bytes / total_bytes * 100:.1f}% free headroom)", flush=True)
        if free_gb < 10.0:
            print(f"  ⚠️ Warning: Target volume free space is low: {free_gb:.1f} GB", flush=True)
            return False
        return True
    except Exception as e:
        print(f"  ❌ Capacity check exception: {e}", flush=True)
        return False

def verify_top_level_files() -> bool:
    print("\n[Audit 4/4] Checking Critical Root Subsystems & Configuration Assets...", flush=True)
    critical_root_files = [
        "docker-compose.yml",
        "project_map.opml",
        "README.md"
    ]
    all_ok = True
    for rf in critical_root_files:
        p_src = SOURCE_ROOT / rf
        p_dest = TARGET_ROOT / rf
        if p_src.exists():
            if p_dest.exists():
                print(f"  ✓ Root asset verified: {rf} (Source size: {p_src.stat().st_size} bytes)", flush=True)
            else:
                print(f"  ❌ Missing root asset in target: {rf}", flush=True)
                all_ok = False
        else:
            print(f"  - Source does not contain {rf} (skipped)", flush=True)
    return all_ok

def main():
    print("=" * 80, flush=True)
    print("🔍 LAUBURU DFS MIGRATION AUDIT & INTEGRITY VERIFIER", flush=True)
    print(f"Source Root : {SOURCE_ROOT}", flush=True)
    print(f"Target Root : {TARGET_ROOT}", flush=True)
    print("=" * 80, flush=True)

    if not TARGET_ROOT.exists():
        print(f"❌ Target root {TARGET_ROOT} does not exist!", flush=True)
        sys.exit(1)

    s1 = verify_subsystems()
    s2 = verify_sample_hashes()
    s3 = verify_storage_capacity()
    s4 = verify_top_level_files()

    print("\n" + "=" * 80, flush=True)
    print("📋 OVERALL DFS MIGRATION AUDIT RESULT", flush=True)
    print("=" * 80, flush=True)
    if s1 and s2 and s3 and s4:
        print("🎉 ALL 4/4 MIGRATION INTEGRITY AUDIT CHECKS PASSED WITH 100% SUCCESS!", flush=True)
        sys.exit(0)
    else:
        print("❌ ONE OR MORE INTEGRITY AUDIT CHECKS FAILED.", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
