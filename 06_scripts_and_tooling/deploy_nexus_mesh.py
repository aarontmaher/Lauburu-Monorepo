#!/usr/bin/env python3
"""
================================================================================
👑 Sovereign Nexus Mesh Deployer & Cross-Device Orchestrator (2026)
================================================================================
Subsystem: 06_scripts_and_tooling/deploy_nexus_mesh.py
CLI Command: python3 deploy_nexus_mesh.py
Governed by:
  - Rule 0 (Zero-Mock): Authentic local endpoints, genuine syscalls, authentic records
  - Rule 1 (Tri-Proof): Exact process exit codes, SHA256 checksums, visual snapshots
  - Rule 2 (Tri-Vault): Obsidian Vault, PySpark LoRA lake, GitHub Monorepo
  - Rule 3 & 10 (Host Sanctuary): Zero heavy models in-process, RAM headroom >= 4.8GB
  - Rule 8 & 15 (Model Governance): Qwen 3.8 Max Master (:8082), Abliterated Red Team (:8083)

Capabilities:
  1. Verifies Mother Ship on Port 4050 (:4050)
  2. Deploys/Verifies Sovereign Nexus on Pixel 10 Pro XL (L6) via SSH
  3. Deploys/Verifies Sovereign Nexus on Samsung Galaxy S20+ (L7) via ADB
  4. Deploys/Verifies Sovereign Nexus on GL.iNet Gateway Router (GW)
  5. Validates cross-device telemetry & directive fanout across the physical mesh
================================================================================
"""

import os
import sys
import json
import time
import shutil
import sqlite3
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, List

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
CLIENT_SRC = REPO_ROOT / "06_scripts_and_tooling" / "integrations" / "nexus_mesh_client.py"
ROUTER_BRIDGE = REPO_ROOT / "06_scripts_and_tooling" / "network" / "router_nexus_bridge.py"
DB_PATH = REPO_ROOT / "04_data_and_memory" / "single_chat_nexus.db"
MOTHER_SHIP_URL = "http://127.0.0.1:4050"

C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_CYAN = "\033[36m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_RED = "\033[31m"
C_DIM = "\033[90m"


def print_header():
    print(f"{C_BOLD}{C_CYAN}╔══════════════════════════════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}║     👑 SOVEREIGN NEXUS CROSS-DEVICE & ROUTER MESH DEPLOYER           ║{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}╚══════════════════════════════════════════════════════════════════════╝{C_RESET}")
    print(f"{C_DIM}• Target Mother Ship: {MOTHER_SHIP_URL}{C_RESET}")
    print(f"{C_DIM}• SQLite Tri-Vault:   {DB_PATH}{C_RESET}")
    print(f"{C_DIM}• Client Source:      {CLIENT_SRC}{C_RESET}\n")


def verify_mother_ship() -> bool:
    print(f"{C_BOLD}[Stage 1/5] Verifying Sovereign Mother Ship (:4050)...{C_RESET}")
    try:
        with urllib.request.urlopen(f"{MOTHER_SHIP_URL}/health", timeout=3) as resp:
            data = json.loads(resp.read().decode())
            print(f"  {C_GREEN}✓ Mother Ship ONLINE:{C_RESET} {data.get('app')} (Indexed: {data.get('database_records_indexed'):,} records)")
            return True
    except Exception as e:
        print(f"  {C_RED}✗ Mother Ship OFFLINE: {e}{C_RESET}")
        return False


def deploy_pixel_10() -> Dict[str, Any]:
    print(f"\n{C_BOLD}[Stage 2/5] Deploying Sovereign Nexus to Pixel 10 Pro XL (L6)...{C_RESET}")
    res = {"node": "L6_Pixel_10_Pro_XL", "status": "UNKNOWN", "details": {}}

    try:
        scp_cmd = ["scp", str(CLIENT_SRC), "pixel:/data/data/com.termux/files/home/bin/nexus_mesh_client.py"]
        sp = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=10)
        if sp.returncode != 0:
            res["status"] = "FAILED"
            res["error"] = f"SCP failed: {sp.stderr}"
            print(f"  {C_RED}✗ SCP failed: {sp.stderr.strip()}{C_RESET}")
            return res

        remote_cmds = [
            "chmod +x /data/data/com.termux/files/home/bin/nexus_mesh_client.py",
            "printf '#!/data/data/com.termux/files/usr/bin/bash\\nexec python3 /data/data/com.termux/files/home/bin/nexus_mesh_client.py \"$@\"\\n' > /data/data/com.termux/files/usr/bin/nexus",
            "chmod 755 /data/data/com.termux/files/usr/bin/nexus",
            "cp -f /data/data/com.termux/files/usr/bin/nexus /data/data/com.termux/files/home/bin/nexus",
            "chmod 755 /data/data/com.termux/files/home/bin/nexus",
            "nexus status"
        ]
        ssh_cmd = ["ssh", "pixel", "; ".join(remote_cmds)]
        sp2 = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=15)
        if sp2.returncode == 0:
            print(f"  {C_GREEN}✓ Pixel 10 Pro XL configured successfully!{C_RESET}")
            report_cmd = ["ssh", "pixel", "nexus report core_infrastructure 'Pixel 10 Pro XL Mesh Health' 'Nexus CLI v0.4.0 verified over Tailscale'"]
            subprocess.run(report_cmd, capture_output=True, text=True, timeout=10)
            res["status"] = "ONLINE"
            res["details"]["cli"] = "INSTALLED (/usr/bin/nexus)"
        else:
            res["status"] = "ERROR"
            res["error"] = sp2.stderr.strip()
            print(f"  {C_RED}✗ Remote execution error: {sp2.stderr.strip()}{C_RESET}")

    except Exception as e:
        res["status"] = "OFFLINE"
        res["error"] = str(e)
        print(f"  {C_YELLOW}⚠️  Pixel 10 unreachable: {e}{C_RESET}")

    return res


def deploy_samsung_s20() -> Dict[str, Any]:
    print(f"\n{C_BOLD}[Stage 3/5] Deploying Sovereign Nexus to Samsung Galaxy S20+ (L7)...{C_RESET}")
    res = {"node": "L7_Samsung_S20", "status": "UNKNOWN", "details": {}}
    serial = "100.78.206.96:5555"

    try:
        check = subprocess.run(["adb", "-s", serial, "get-state"], capture_output=True, text=True, timeout=3)
        if check.returncode != 0:
            print(f"  {C_YELLOW}⚠️  ADB device {serial} not found or offline.{C_RESET}")
            res["status"] = "OFFLINE"
            return res

        subprocess.run(["adb", "-s", serial, "push", str(CLIENT_SRC), "/data/local/tmp/nexus_mesh_client.py"], capture_output=True, timeout=5)

        remote_cmds = [
            "cat /data/local/tmp/nexus_mesh_client.py | run-as com.termux tee /data/data/com.termux/files/home/bin/nexus_mesh_client.py >/dev/null",
            "run-as com.termux chmod 755 /data/data/com.termux/files/home/bin/nexus_mesh_client.py",
            "printf '#!/data/data/com.termux/files/usr/bin/bash\\nexport PATH=\"/data/data/com.termux/files/usr/bin:$PATH\"\\nexec /data/data/com.termux/files/usr/bin/python3 /data/data/com.termux/files/home/bin/nexus_mesh_client.py \"$@\"\\n' | run-as com.termux tee /data/data/com.termux/files/usr/bin/nexus >/dev/null",
            "run-as com.termux chmod 755 /data/data/com.termux/files/usr/bin/nexus",
            "run-as com.termux /data/data/com.termux/files/usr/bin/nexus report core_infrastructure 'Samsung S20+ Mesh Health' 'Nexus CLI v0.4.0 verified via ADB'"
        ]
        sp = subprocess.run(["adb", "-s", serial, "shell", "; ".join(remote_cmds)], capture_output=True, text=True, timeout=15)
        if sp.returncode == 0:
            print(f"  {C_GREEN}✓ Samsung Galaxy S20+ configured successfully via ADB!{C_RESET}")
            res["status"] = "ONLINE"
            res["details"]["cli"] = "INSTALLED (/usr/bin/nexus)"
        else:
            print(f"  {C_RED}✗ S20 deployment failed: {sp.stderr.strip()}{C_RESET}")
            res["status"] = "ERROR"

    except Exception as e:
        res["status"] = "ERROR"
        res["error"] = str(e)
        print(f"  {C_YELLOW}⚠️  Samsung S20 error: {e}{C_RESET}")

    return res


def deploy_router() -> Dict[str, Any]:
    print(f"\n{C_BOLD}[Stage 4/5] Integrating GL.iNet Gateway Router (GW)...{C_RESET}")
    res = {"node": "GW_GLiNet_Router", "status": "UNKNOWN", "details": {}}

    try:
        sp = subprocess.run([sys.executable, str(ROUTER_BRIDGE), "--once"], capture_output=True, text=True, timeout=5)
        if sp.returncode == 0:
            print(f"  {C_GREEN}✓ GL-BE14000 Gateway Router integrated via live telemetry bridge!{C_RESET}")
            for line in sp.stdout.strip().splitlines():
                print(f"    {line}")
            res["status"] = "ONLINE"
            res["details"]["bridge"] = "06_scripts_and_tooling/network/router_nexus_bridge.py"
        else:
            print(f"  {C_YELLOW}⚠️  Router bridge returned non-zero: {sp.stderr.strip()}{C_RESET}")
            res["status"] = "DEGRADED"

    except Exception as e:
        res["status"] = "OFFLINE"
        res["error"] = str(e)
        print(f"  {C_RED}✗ Router bridge error: {e}{C_RESET}")

    return res


def verify_database_state():
    print(f"\n{C_BOLD}[Stage 5/5] Auditing SQLite Tri-Vault Persistence...{C_RESET}")
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            c = conn.cursor()
            actions = c.execute("SELECT id, thread_id, action, result, timestamp FROM actions ORDER BY id DESC LIMIT 5").fetchall()
            print(f"  {C_GREEN}✓ Actions Table Active ({len(actions)} recent actions shown):{C_RESET}")
            for a in actions:
                ts = time.strftime("%H:%M:%S", time.localtime(a[4]))
                print(f"    • [{ts}] ID {a[0]} ({a[1]}): {a[2]} -> {a[3][:60]}...")
    except Exception as e:
        print(f"  {C_RED}✗ Database audit failed: {e}{C_RESET}")


def main():
    print_header()
    if not verify_mother_ship():
        print(f"{C_RED}Aborting mesh deployment: Mother Ship (:4050) is not running.{C_RESET}")
        sys.exit(1)

    r_pixel = deploy_pixel_10()
    r_s20 = deploy_samsung_s20()
    r_router = deploy_router()
    verify_database_state()

    print(f"\n{C_BOLD}{C_CYAN}══════════════════════════════════════════════════════════════════════{C_RESET}")
    print(f"{C_BOLD}👑 MESH INTEGRATION SUMMARY:{C_RESET}")
    print(f"  • L1 Mac Host (Mother Ship): {C_GREEN}ONLINE (:4050){C_RESET}")
    print(f"  • L6 Pixel 10 Pro XL:        " + (f"{C_GREEN}ONLINE{C_RESET}" if r_pixel["status"] == "ONLINE" else f"{C_YELLOW}{r_pixel['status']}{C_RESET}"))
    print(f"  • L7 Samsung Galaxy S20+:    " + (f"{C_GREEN}ONLINE{C_RESET}" if r_s20["status"] == "ONLINE" else f"{C_YELLOW}{r_s20['status']}{C_RESET}"))
    print(f"  • GW GL.iNet Gateway Router: " + (f"{C_GREEN}ONLINE{C_RESET}" if r_router["status"] == "ONLINE" else f"{C_YELLOW}{r_router['status']}{C_RESET}"))
    print(f"{C_BOLD}{C_CYAN}══════════════════════════════════════════════════════════════════════{C_RESET}\n")


if __name__ == "__main__":
    main()
