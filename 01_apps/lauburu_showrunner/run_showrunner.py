#!/usr/bin/env python3
"""
Lauburu Showrunner Master CLI & Daemon Manager
=============================================
Governed by:
- Rule #0: Zero-Mock & Truth Verification
- Rule #1: Tri-Proof Verification Gate
- Rule #2: Tri-Vault Storage Synchronization
- Rule #3: Host Sanctuary & Dynamic RAM Governance (>= 9.6 GB free)
- Rule #7: Sovereign Local AI Hierarchy (Qwen 3.8 Max Master on 8082)
"""

import sys
import os
import time
import json
import psutil
import socket
import argparse
import subprocess
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR / "backend"
VENV_PYTHON = BACKEND_DIR / "venv" / "bin" / "python3"
PID_FILE = BACKEND_DIR / "showrunner.pid"
LOG_FILE = BACKEND_DIR / "showrunner.log"

def check_preflight():
    """Verifies Tri-Vault storage and host RAM headroom before starting."""
    print("=== Lauburu Showrunner Pre-Flight Check ===")
    
    # Storage
    vault_ok = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/Index.md").exists()
    lora_ok = Path("/Users/aaron/DFS_UNIFIED/lora_datasets").is_dir()
    print(f"[*] Tri-Vault Storage: Obsidian Vault={'OK' if vault_ok else 'MISSING'}, LoRA Lake={'OK' if lora_ok else 'MISSING'}")
    
    # RAM Headroom (Rule #3)
    mem = psutil.virtual_memory()
    free_ram_gb = round(mem.available / (1024 ** 3), 2)
    ram_ok = free_ram_gb >= 9.6
    print(f"[*] Host RAM Headroom: {free_ram_gb} GB Available (Rule #3 Requirement: >= 9.6 GB) -> {'PASSED' if ram_ok else 'THROTTLED'}")
    
    # AI Endpoints
    def check_port(p):
        try:
            with socket.create_connection(("127.0.0.1", p), timeout=0.3):
                return True
        except Exception:
            return False

    qwen_master = check_port(8082)
    qwen_redteam = check_port(8083)
    print(f"[*] Port 8082 (Qwen 3.8 Max Sovereign Master): {'ONLINE' if qwen_master else 'OFFLINE'}")
    print(f"[*] Port 8083 (Qwen 3.8 Max Abliterated Red Team): {'ONLINE' if qwen_redteam else 'OFFLINE'}")
    print(f"[*] Port 8101 (Showrunner Engine): {'ONLINE' if check_port(8101) else 'OFFLINE'}")

def is_running():
    if not PID_FILE.exists():
        return False
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        proc = psutil.Process(pid)
        return proc.is_running() and "python" in proc.name().lower()
    except Exception:
        return False

def start_daemon():
    if is_running():
        print("[!] Showrunner daemon is ALREADY RUNNING.")
        return
    check_preflight()
    print("[*] Starting Lauburu Showrunner Engine daemon on Port 8101...")
    
    cmd = [
        str(VENV_PYTHON),
        "-m", "uvicorn",
        "engine:app",
        "--host", "0.0.0.0",
        "--port", "8101",
        "--log-level", "info"
    ]
    with open(LOG_FILE, "a") as log_out:
        proc = subprocess.Popen(
            cmd,
            cwd=str(BACKEND_DIR),
            stdout=log_out,
            stderr=log_out,
            start_new_session=True
        )
    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))
    
    # Wait for port 8101 to open
    time.sleep(1.5)
    for _ in range(10):
        try:
            with socket.create_connection(("127.0.0.1", 8101), timeout=0.5):
                print(f"[+] Showrunner daemon STARTED successfully (PID: {proc.pid}) on http://127.0.0.1:8101")
                return
        except Exception:
            time.sleep(0.5)
    print(f"[!] Started process {proc.pid}, verifying logs at {LOG_FILE}")

def stop_daemon():
    if not is_running():
        print("[*] Showrunner daemon is NOT running.")
        if PID_FILE.exists():
            PID_FILE.unlink()
        return
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        proc = psutil.Process(pid)
        proc.terminate()
        proc.wait(timeout=5)
        print(f"[+] Showrunner daemon (PID: {pid}) stopped.")
    except Exception as e:
        print(f"[!] Error stopping daemon: {e}")
    finally:
        if PID_FILE.exists():
            PID_FILE.unlink()

def status():
    check_preflight()
    running = is_running()
    print(f"\n[Status] Showrunner Daemon: {'RUNNING' if running else 'STOPPED'}")
    if running:
        with open(PID_FILE) as f:
            print(f"         PID: {f.read().strip()}")
        print(f"         Web Dashboard: http://127.0.0.1:8101")
        print(f"         WebSocket Stream: ws://127.0.0.1:8101/ws/sim_stream")

def main():
    parser = argparse.ArgumentParser(description="Lauburu Showrunner Master CLI")
    parser.add_argument("action", choices=["start", "stop", "restart", "status", "check"], default="status", nargs="?")
    args = parser.parse_args()

    if args.action == "check":
        check_preflight()
    elif args.action == "start":
        start_daemon()
    elif args.action == "stop":
        stop_daemon()
    elif args.action == "restart":
        stop_daemon()
        time.sleep(1)
        start_daemon()
    elif args.action == "status":
        status()

if __name__ == "__main__":
    main()
