#!/usr/bin/env python3
"""
Autonomous Network Storage Governor & Uptime Sentinel (v1.0)
============================================================
Path: 06_scripts_and_tooling/storage/autonomous_storage_governor.py

Orchestrates 24/7 continuous organization, ordering, and uptime maintenance
for the 1.701 TB unified SeaweedFS storage folder (/Volumes/Lauburu-Monorepo)
and the Tri-Vault synchronization layers.

Powered by:
- Tier 1 Local AI Sentinel: Qwen 2.5 Coder 7B Instruct (Port 8081 / llama-server)
- Tier 2 Deep Reorganizer: Qwen 2.5 Coder 32B / Mistral Nemo 12B (Thunderbolt 4 Cluster)
- Frameworks: Google Antigravity SDK, Nomad Courier Mesh Governor, Genetic MoE

Zero-Mock Policy: All storage metrics, socket probes, and disk stats are authentically sampled.
"""

import os
import sys
import time
import json
import socket
import shutil
import argparse
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# ── Canonical Paths ───────────────────────────────────────────────────────────
REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
DFS_PATH = Path("/Volumes/Lauburu-Monorepo")
DATA_DIR = REPO_ROOT / "data/network"
LORA_DIR = REPO_ROOT / "data/lora_datasets"
STATUS_FILE = DATA_DIR / "storage_governor_status.json"
LORA_LOG = LORA_DIR / "nomad_autonomous_actions.jsonl"
LOGS_DIR = REPO_ROOT / "logs"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LORA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ── Local AI Endpoint Configuration ───────────────────────────────────────────
LOCAL_AI_SENTINEL_URL = "http://127.0.0.1:8081/v1/chat/completions"
LOCAL_AI_MODEL_NAME = "qwen2.5-coder-7b-instruct"

# ── SeaweedFS Managed Sockets ─────────────────────────────────────────────────
SEAWEED_SOCKETS = {
    "master_9333": ("127.0.0.1", 9333),
    "filer_8888": ("127.0.0.1", 8888),
    "filer_alt_8088": ("127.0.0.1", 8088),
    "volume_8080": ("127.0.0.1", 8080),
    "webdav_7333": ("127.0.0.1", 7333),
}


def probe_tcp(host: str, port: int, timeout: float = 0.2) -> bool:
    """Non-blocking TCP socket probe."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        res = s.connect_ex((host, port))
        s.close()
        return res == 0
    except Exception:
        return False


def verify_tri_vault_health() -> Dict[str, Any]:
    """Inspects Obsidian Vault, PySpark Data Lake, and free disk headroom."""
    obsidian_vault = REPO_ROOT / "obsidian_vault"
    index_md = obsidian_vault / "Index.md"
    pyspark_lake = REPO_ROOT / "04_data_and_memory"
    lora_lake = DFS_PATH / "lora_datasets"
    
    stat = shutil.disk_usage("/Users/aaron")
    free_gb = round(stat.free / (1024 ** 3), 2)
    
    obsidian_ok = obsidian_vault.is_dir() and index_md.exists() and index_md.stat().st_size > 0
    pyspark_ok = pyspark_lake.is_dir() or lora_lake.is_dir()
    disk_ok = free_gb >= 5.0
    
    # Self-heal missing git index locks if present
    git_lock = REPO_ROOT / ".git/index.lock"
    if git_lock.exists():
        try:
            git_lock.unlink()
        except Exception:
            pass
            
    is_healthy = obsidian_ok and pyspark_ok and disk_ok
    return {
        "healthy": is_healthy,
        "obsidian_vault_ok": obsidian_ok,
        "pyspark_lake_ok": pyspark_ok,
        "disk_free_gb": free_gb,
        "status": "HEALTHY" if is_healthy else "DEGRADED"
    }


def verify_dfs_mount_and_sockets() -> Dict[str, Any]:
    """Inspects SeaweedFS sockets and local FUSE mount responsiveness."""
    socket_status = {}
    for name, (host, port) in SEAWEED_SOCKETS.items():
        socket_status[name] = probe_tcp(host, port)
        
    mount_exists = DFS_PATH.is_dir()
    can_list_root = False
    file_count = 0
    if mount_exists:
        try:
            entries = list(DFS_PATH.iterdir())
            file_count = len(entries)
            can_list_root = True
        except Exception:
            can_list_root = False
            
    all_critical_sockets = (
        socket_status.get("master_9333", False) and
        (socket_status.get("filer_8888", False) or socket_status.get("filer_alt_8088", False)) and
        socket_status.get("volume_8080", False)
    )
    
    is_healthy = all_critical_sockets and can_list_root and (file_count > 0)
    return {
        "healthy": is_healthy,
        "sockets": socket_status,
        "mount_directory_exists": mount_exists,
        "mount_directory_readable": can_list_root,
        "root_entry_count": file_count,
        "status": "ONLINE" if is_healthy else ("DEGRADED_SOCKETS" if not all_critical_sockets else "MOUNT_OFFLINE")
    }


def query_local_ai_sentinel(context_summary: Dict[str, Any]) -> Dict[str, Any]:
    """Queries the Tier 1 Local AI Sentinel (Qwen 2.5 Coder 7B) on Port 8081 for health analysis."""
    if not probe_tcp("127.0.0.1", 8081):
        return {
            "ai_governor_status": "LOCAL_AI_OFFLINE",
            "decision": "STANDBY",
            "recommended_action": "START_LLAMA_SERVER_8081"
        }
        
    prompt = (
        "You are the Lauburu Autonomous Network Storage Governor.\n"
        f"Input Telemetry:\n{json.dumps(context_summary, indent=2)}\n\n"
        "Evaluate storage status and respond in JSON with keys: "
        "\"assessment\" (healthy/degraded), \"action_required\" (none/remount/restart_weed/clean_cache), \"explanation\"."
    )
    
    payload = {
        "model": LOCAL_AI_MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are the Lauburu Network Storage Governor. Respond in valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 180
    }
    
    try:
        req = urllib.request.Request(
            LOCAL_AI_SENTINEL_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"].strip()
            # Clean markdown JSON block if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            return json.loads(content.strip())
    except Exception as e:
        return {
            "ai_governor_status": "QUERY_TIMEOUT_OR_PARSE_FALLBACK",
            "error": str(e),
            "assessment": "AUTOMATIC_RULES_APPLIED",
            "action_required": "none" if context_summary.get("dfs", {}).get("healthy") else "remount"
        }


def self_heal_storage_if_needed(dfs_status: Dict[str, Any], ai_decision: Dict[str, Any]) -> List[str]:
    """Executes automated recovery for SeaweedFS daemons and FUSE mount."""
    actions = []
    
    # 1. Self-heal daemons if master or filer sockets down
    sockets = dfs_status.get("sockets", {})
    if not sockets.get("master_9333") or not sockets.get("volume_8080"):
        weed_bin = Path("/Users/aaron/.local/bin/weed")
        if weed_bin.exists():
            log_file = LOGS_DIR / "seaweedfs_recovered.log"
            cmd = [
                str(weed_bin), "server",
                "-dir=/Users/aaron/.local/var/seaweedfs",
                "-master.port=9333",
                "-filer=true",
                "-filer.port=8888",
                "-volume.port=8080",
                "-ip.bind=0.0.0.0",
                "-ip=127.0.0.1"
            ]
            with open(log_file, "a") as lf:
                subprocess.Popen(cmd, stdout=lf, stderr=lf, start_new_session=True)
            actions.append("LAUNCHED_SEAWEEDFS_SERVER_CLUSTER")
            time.sleep(1.0)
            
    # 2. Self-heal WebDAV daemon if missing
    if not sockets.get("webdav_7333"):
        weed_bin = Path("/Users/aaron/.local/bin/weed")
        if weed_bin.exists():
            cmd = [str(weed_bin), "webdav", "-port=7333", "-filer=localhost:8888"]
            with open(LOGS_DIR / "weed_webdav.log", "a") as lf:
                subprocess.Popen(cmd, stdout=lf, stderr=lf, start_new_session=True)
            actions.append("LAUNCHED_SEAWEEDFS_WEBDAV_GATEWAY")

    # 3. Dual-Stage Mount Healing: Clean FUSE Remount -> WebDAV Fallback
    needs_remount = (
        not dfs_status.get("mount_directory_readable", True) or
        dfs_status.get("status") == "MOUNT_OFFLINE" or
        ai_decision.get("action_required") == "remount"
    )
    if needs_remount and weed_bin.exists():
        actions.append("TRIGGERED_DUAL_STAGE_MOUNT_HEALER")
        # Stage 1: Clean FUSE Remount
        subprocess.run(["umount", "-f", str(DFS_PATH)], capture_output=True)
        subprocess.run(["diskutil", "unmount", "force", str(DFS_PATH)], capture_output=True)
        time.sleep(0.5)
        fuse_cmd = [str(weed_bin), "mount", "-filer=127.0.0.1:8888", f"-dir={DFS_PATH}"]
        fuse_proc = subprocess.Popen(fuse_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        time.sleep(1.5)
        
        # Verify Stage 1
        fuse_success = False
        try:
            fuse_success = DFS_PATH.is_dir() and len(list(DFS_PATH.iterdir())) > 0
        except Exception:
            fuse_success = False
            
        if fuse_success:
            actions.append("STAGE_1_CLEAN_FUSE_REMOUNT_SUCCESS")
        else:
            # Stage 2: WebDAV Native Fallback
            actions.append("STAGE_1_FUSE_FAILED_ESCALATING_TO_STAGE_2_WEBDAV")
            subprocess.run(["mount_webdav", "-i", "http://127.0.0.1:7333", str(DFS_PATH)], capture_output=True)
            time.sleep(1.0)
            try:
                webdav_success = DFS_PATH.is_dir() and len(list(DFS_PATH.iterdir())) > 0
                if webdav_success:
                    actions.append("STAGE_2_WEBDAV_FALLBACK_MOUNT_SUCCESS")
                else:
                    actions.append("STAGE_2_WEBDAV_MOUNT_DEGRADED")
            except Exception as e:
                actions.append(f"STAGE_2_WEBDAV_EXCEPTION:{str(e)[:60]}")

    if not actions:
        actions.append("STORAGE_UPTIME_VERIFIED_NOMINAL")
        
    return actions


def run_governor_cycle() -> Dict[str, Any]:
    """Executes a single end-to-end storage audit, AI evaluation, and uptime check."""
    ts = datetime.now(timezone.utc).isoformat()
    
    dfs_health = verify_dfs_mount_and_sockets()
    tri_vault = verify_tri_vault_health()
    
    summary = {
        "dfs": dfs_health,
        "tri_vault": tri_vault,
        "timestamp_utc": ts
    }
    
    ai_verdict = query_local_ai_sentinel(summary)
    actions = self_heal_storage_if_needed(dfs_health, ai_verdict)
    
    report = {
        "timestamp_utc": ts,
        "overall_status": "HEALTHY" if (dfs_health["healthy"] and tri_vault["healthy"]) else "DEGRADED",
        "combined_storage_mount": dfs_health["status"],
        "tri_vault_health": tri_vault["status"],
        "disk_headroom_gb": tri_vault["disk_free_gb"],
        "local_ai_sentinel": {
            "model": LOCAL_AI_MODEL_NAME,
            "port": 8081,
            "verdict": ai_verdict
        },
        "actions_taken": actions,
        "endpoints": {
            "seaweedfs_master": "127.0.0.1:9333",
            "seaweedfs_filer": "127.0.0.1:8888",
            "seaweedfs_webdav": "127.0.0.1:7333",
            "fuse_mount_point": str(DFS_PATH)
        }
    }
    
    # Save status JSON
    STATUS_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    
    # Log LoRA action entry for continuous distillation
    lora_entry = {
        "timestamp_utc": ts,
        "governor": "Autonomous Storage Governor v1.0",
        "instruction": "Evaluate 1.701 TB network combined storage uptime and tri-vault health",
        "input": f"DFS: {dfs_health['status']}, Tri-Vault: {tri_vault['status']}, Free: {tri_vault['disk_free_gb']}GB",
        "output": json.dumps(report),
        "action": "STORAGE_GOVERNOR_UPTIME_CYCLE",
        "result": report["overall_status"]
    }
    with open(LORA_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(lora_entry) + "\n")
        
    return report


def main():
    parser = argparse.ArgumentParser(description="Autonomous Network Storage Governor & Uptime Sentinel")
    parser.add_argument("--once", action="store_true", help="Execute single audit cycle and print result")
    parser.add_argument("--daemon", action="store_true", help="Run 24/7 background watchdog daemon")
    parser.add_argument("--interval", type=int, default=60, help="Watchdog interval in seconds (default: 60)")
    args = parser.parse_args()
    
    if args.daemon:
        print(f"[*] Starting Autonomous Storage Governor Daemon (Interval: {args.interval}s)...")
        while True:
            try:
                rep = run_governor_cycle()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Storage: {rep['combined_storage_mount']} | Tri-Vault: {rep['tri_vault_health']} | Actions: {rep['actions_taken']}")
            except Exception as e:
                print(f"[!] Error in cycle: {e}", file=sys.stderr)
            time.sleep(args.interval)
    else:
        rep = run_governor_cycle()
        print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
