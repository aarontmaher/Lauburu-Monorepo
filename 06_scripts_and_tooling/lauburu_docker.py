#!/usr/bin/env python3
"""
Lauburu Mesh - Docker & Containerized Microservices Orchestrator CLI
Manages Colima/Docker lifecycle, master compose stack, and self-healing.
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
from pathlib import Path

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
COMPOSE_MASTER = REPO_ROOT / "00_core_infrastructure" / "docker-compose.master.yml"

def get_docker_env():
    env = os.environ.copy()
    colima_sock = Path.home() / ".colima" / "default" / "docker.sock"
    if colima_sock.exists() and "DOCKER_HOST" not in env:
        env["DOCKER_HOST"] = f"unix://{colima_sock}"
    return env

def cmd_status():
    print("=== 🐳 LAUBURU DOCKER ORCHESTRATION STATUS ===")
    has_docker = shutil.which("docker") is not None
    has_colima = shutil.which("colima") is not None
    print(f"• Docker CLI: {'Installed' if has_docker else 'Missing'}")
    print(f"• Colima Runtime: {'Installed' if has_colima else 'Missing'}")
    print(f"• Master Compose Manifest: {'Exists' if COMPOSE_MASTER.exists() else 'Missing'}")

    env = get_docker_env()
    try:
        res = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True, timeout=3, env=env)
        if res.returncode == 0:
            print(f"• Daemon State: RUNNING (Docker Engine v{res.stdout.strip()})")
            # List containers
            res_ps = subprocess.run(["docker", "ps", "--format", "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"], capture_output=True, text=True, timeout=4, env=env)
            print("\n📦 Active Containers:")
            print(res_ps.stdout if res_ps.stdout.strip() else "  (No containers currently running)")
        else:
            print("• Daemon State: STANDBY (Colima/Docker daemon is not running)")
    except Exception:
        print("• Daemon State: STANDBY")

def cmd_start_daemon(cpu: int = 4, memory: int = 8):
    print(f"==> Launching Colima container runtime ({cpu} CPUs, {memory}GB RAM)...")
    cmd = ["colima", "start", "--cpu", str(cpu), "--memory", str(memory), "--arch", "aarch64"]
    subprocess.run(cmd)

def cmd_up():
    print("==> Starting Lauburu Master Microservices Stack...")
    env = get_docker_env()
    cmd = ["docker", "compose", "-f", str(COMPOSE_MASTER), "up", "-d"]
    subprocess.run(cmd, env=env)

def cmd_down():
    print("==> Stopping Lauburu Master Microservices Stack...")
    env = get_docker_env()
    cmd = ["docker", "compose", "-f", str(COMPOSE_MASTER), "down"]
    subprocess.run(cmd, env=env)

def main():
    parser = argparse.ArgumentParser(description="Lauburu Docker Microservices CLI")
    parser.add_argument("action", choices=["status", "start-daemon", "up", "down", "ps"], default="status", nargs="?")
    args = parser.parse_args()

    if args.action == "status" or args.action == "ps":
        cmd_status()
    elif args.action == "start-daemon":
        cmd_start_daemon()
    elif args.action == "up":
        cmd_up()
    elif args.action == "down":
        cmd_down()

if __name__ == "__main__":
    main()
