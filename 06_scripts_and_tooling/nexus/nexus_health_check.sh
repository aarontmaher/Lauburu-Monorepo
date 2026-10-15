#!/usr/bin/env python3
"""
Nexus Health Check Script for Nexus Terminal & CLI
"""
import socket
import sys
import json
import urllib.request

print("========================================================")
print("⚡ LAUBURU MESH & NEXUS TERMINAL CONNECTIVITY CHECK")
print("========================================================")

def check_target(name, host, port, timeout=0.8):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        print(f"\033[0;32m[ONLINE]\033[0m  {name:32} {host}:{port}")
        return True
    except Exception as e:
        print(f"\033[0;31m[OFFLINE]\033[0m {name:32} {host}:{port} ({e})")
        return False
    finally:
        s.close()

print("--- Core Mesh Inference & Mother Ship ---")
check_target("Single-Chat Nexus Mother Ship", "127.0.0.1", 4050)
check_target("prima.cpp Master Orchestrator", "127.0.0.1", 8082)
check_target("Qwen 3.8 Max Abliterated Red Team", "127.0.0.1", 8083)
check_target("Qwen 2.5 Coder 7B Syntax Worker", "127.0.0.1", 8081)
check_target("Screen Lens MJPEG Stream", "127.0.0.1", 4003)

print("\n--- Physical Mesh Node SSH Listeners ---")
check_target("L1 Mac Mini Host (Local)", "127.0.0.1", 22)
check_target("GW GL.iNet Sovereign Gateway", "192.168.8.1", 22)
check_target("L6 Pixel 10 Pro XL (Termux)", "100.73.38.87", 8022)
check_target("L7 Samsung S20+ (Termux)", "100.78.206.96", 8022)
check_target("L2 MacBook Pro (Metal RPC)", "100.103.212.21", 22)
check_target("L3 Linux Head Node (Ray Cluster)", "100.101.39.98", 22)

print("\n--- Single-Chat Nexus Health API ---")
try:
    req = urllib.request.urlopen("http://127.0.0.1:4050/api/health", timeout=1.5)
    data = json.loads(req.read().decode("utf-8"))
    print(json.dumps(data, indent=2))
except Exception as e:
    print(f"⚠️ Single-Chat Nexus API query error: {e}")

print("========================================================")
