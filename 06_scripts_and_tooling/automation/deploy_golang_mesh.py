#!/usr/bin/env python3
"""
================================================================================
Golang Mesh Deployment & Lens Integration Hook
================================================================================
Subsystem: 06_scripts_and_tooling/automation/deploy_golang_mesh.py
Version: 1.0.0

Deploys Golang 1.23.1 to all headless Linux and Android nodes in the 7-layer mesh
to enable distributed Go compilation and AST analysis for the Screen Lens Sovereign.

Targets:
- L8 (Ubuntu lauburu): amd64
- L3 (Linux head node): amd64
- L4/L6 (Android Edge): arm64 via Termux/AVF
"""

import subprocess
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [GoMeshDeploy] %(levelname)s: %(message)s")
log = logging.getLogger("GoMeshDeploy")

NODES = [
    {"name": "L8 (lauburu)", "user": "linuxmini", "ip": "10.0.0.8", "arch": "linux-amd64"},
    {"name": "L3 (linux-amd)", "user": "linux", "ip": "192.168.8.225", "arch": "linux-amd64"},
    {"name": "L6 (pixel-10)", "user": "root", "ip": "100.114.215.68", "port": "8022", "arch": "termux"},
]

def run_ssh(user, ip, cmd, port="22"):
    log.info(f"Executing on {user}@{ip}:{port} -> {cmd}")
    try:
        res = subprocess.run(["ssh", "-p", port, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5", f"{user}@{ip}", cmd], capture_output=True, text=True)
        if res.returncode == 0:
            log.info(f"Success on {ip}")
        else:
            log.error(f"Failed on {ip}: {res.stderr.strip()}")
    except Exception as e:
        log.error(f"SSH error to {ip}: {e}")

def deploy_go():
    go_version = "1.23.1"
    for node in NODES:
        log.info(f"--- Deploying to {node['name']} ({node['ip']}) ---")
        if node["arch"] == "linux-amd64":
            cmd = f"""
            if ! command -v go &> /dev/null || ! go version | grep -q {go_version}; then
                wget -q https://go.dev/dl/go{go_version}.linux-amd64.tar.gz -O /tmp/go.tar.gz
                sudo rm -rf /usr/local/go
                sudo tar -C /usr/local -xzf /tmp/go.tar.gz
                echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.profile
                rm /tmp/go.tar.gz
                echo "Golang {go_version} installed successfully."
            else
                echo "Golang is already up to date."
            fi
            """
            run_ssh(node["user"], node["ip"], cmd, node.get("port", "22"))
        elif node["arch"] == "termux":
            cmd = "pkg install -y golang"
            run_ssh(node["user"], node["ip"], cmd, node.get("port", "22"))

if __name__ == "__main__":
    deploy_go()
