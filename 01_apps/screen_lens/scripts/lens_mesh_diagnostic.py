#!/usr/bin/env python3
"""
Screen Lens Sovereign: Mesh Topology Diagnostic Tool (Rule 8 Enforcement)
=========================================================================
Actively identifies network disconnections and routing failures that lead
to disorganized swarm execution.
"""
import json, socket, time
from pathlib import Path

MATRIX_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/mesh_ip_matrix.json")

def check_tcp_port(ip, port, timeout=0.5):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False

def run_diagnostic():
    print("================================================================================")
    print("📡 SCREEN LENS MESH TOPOLOGY DIAGNOSTIC (PRE-FLIGHT CHECK)")
    print("================================================================================")
    if not MATRIX_PATH.exists():
        print("[ERROR] mesh_ip_matrix.json not found! Fallback to offline mode.")
        return

    with open(MATRIX_PATH, "r") as f:
        matrix = json.load(f)

    # Key nodes to check
    targets = {
        "Master Orchestrator (prima.cpp)": ("127.0.0.1", 8082),
        "Red Team (prima.cpp)": ("127.0.0.1", 8083),
        "Linux Head Node (Docker/Ray/Voila)": (matrix.get("L3_Linux_Hub", {}).get("tailscale", "100.101.39.98"), 22),
        "MacBook Pro (TB4 Bridge)": (matrix.get("L2_MacBook_Pro", {}).get("tb4_bridge", "169.254.44.77"), 22),
        "Android Pixel 10 (OpenClaw)": (matrix.get("L6_Pixel_10_Edge", {}).get("tailscale", "100.73.38.87"), 8022)
    }

    for name, (ip, port) in targets.items():
        print(f"[*] Probing {name} on {ip}:{port}...", end=" ")
        is_online = check_tcp_port(ip, port)
        if is_online:
            print("[ONLINE] 🟢")
        else:
            print("[OFFLINE / TIMEOUT] 🔴")

    print("\n[Lens Verdict] Diagnostic complete. If local orchestrators (8082/8083) are offline, cloud agents will hallucinate and fail due to lacking local Sovereign guidance.")

if __name__ == "__main__":
    run_diagnostic()
