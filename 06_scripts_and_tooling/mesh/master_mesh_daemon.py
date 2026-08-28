#!/usr/bin/env python3
"""
06_scripts_and_tooling/mesh/master_mesh_daemon.py
=================================================
Lauburu Master Mesh Daemon & Service Orchestrator
------------------------------------------------
Supervises and auto-runs all background mesh daemons:
1. WoL REST API (Port 18802 for Localhost 3000 Web UI)
2. Distributed AI Compute Supervisor (llama.cpp RPC & Petals)
3. 10:00 PM Night Scheduler & Auto-Dimming Loop
4. Continuous Telemetry & Device Automation
"""

import os
import sys
import time
import signal
import socket
import logging
import argparse
import threading
import subprocess
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [MasterMeshDaemon]: %(message)s"
)
logger = logging.getLogger("MasterMeshDaemon")

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")

def run_wol_server():
    """Runs the Wake-on-LAN HTTP API server."""
    cmd = [sys.executable, str(REPO_ROOT / "06_scripts_and_tooling/mesh/wol_manager.py"), "--serve-api"]
    subprocess.run(cmd)

def run_ai_supervisor():
    """Runs the AI Compute Supervisor loop."""
    cmd = [sys.executable, str(REPO_ROOT / "06_scripts_and_tooling/mesh/ai_compute_supervisor.py"), "--daemon"]
    subprocess.run(cmd)

def run_night_scheduler():
    """Runs the 10:00 PM Night Scheduler loop."""
    cmd = [sys.executable, str(REPO_ROOT / "06_scripts_and_tooling/dark_mode/night_scheduler_daemon.py"), "--daemon"]
    subprocess.run(cmd)

def run_truth_auditor():
    """Runs the 24/7 Nomad Truth & Consistency Auditor loop."""
    cmd = [sys.executable, str(REPO_ROOT / "06_scripts_and_tooling/automation/nomad_truth_consistency_auditor.py"), "--daemon"]
    subprocess.run(cmd)

def is_port_open(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False

def main():
    parser = argparse.ArgumentParser(description="Lauburu Master Mesh Daemon")
    parser.add_argument("--status", action="store_true", help="Print overall supervisor status")
    args = parser.parse_args()

    if args.status:
        print(f"WoL API (Port 18802): {'ONLINE' if is_port_open(18802) else 'OFFLINE'}")
        print(f"llama.cpp RPC (Port 50052): {'ONLINE' if is_port_open(50052) else 'OFFLINE'}")
        print(f"Dark Fleet PWA (Port 3005): {'ONLINE' if is_port_open(3005) else 'OFFLINE'}")
        print(f"Backend App (Port 3000): {'ONLINE' if is_port_open(3000) else 'PORT_FREE_FOR_BACKEND'}")
        print(f"Hub API (Port 4000): {'ONLINE' if is_port_open(4000) else 'OFFLINE'}")
        return

    logger.info("🚀 Launching Lauburu Master Mesh Supervisor Services...")

    # Spawn threads for background daemons
    t_wol = threading.Thread(target=run_wol_server, daemon=True, name="WoL_Server")
    t_ai = threading.Thread(target=run_ai_supervisor, daemon=True, name="AI_Supervisor")
    t_night = threading.Thread(target=run_night_scheduler, daemon=True, name="Night_Scheduler")
    t_truth = threading.Thread(target=run_truth_auditor, daemon=True, name="Truth_Auditor")

    t_wol.start()
    t_ai.start()
    t_night.start()
    t_truth.start()

    logger.info("✨ All Master Mesh Daemons active: WoL API (Port 18802), AI Supervisor (Port 50052), Night Scheduler (22:00), Nomad Truth Auditor")

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Gracefully terminating Master Mesh Daemon...")

if __name__ == "__main__":
    main()
