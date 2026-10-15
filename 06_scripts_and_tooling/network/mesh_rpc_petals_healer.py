#!/usr/bin/env python3
"""
Lauburu Mesh — llama.cpp RPC + Petals + Continuous AI Debate Self-Healing Governor
Runs across all 7 physical nodes.
Periodic self-healer daemon replacement for launchd (100% Python 3.9+ compatible).
"""

import os
import sys
import time
import json
import socket
import subprocess
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

REPO = Path("/Volumes/Lauburu-Monorepo")
LOG_FILE = REPO / "logs/mesh_rpc_petals.log"
LORA_LOG = REPO / "data/lora_datasets/nomad_autonomous_actions.jsonl"

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
LORA_LOG.parent.mkdir(parents=True, exist_ok=True)

def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

def log_lora(action: str, result: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        record = {
            "timestamp_utc": ts,
            "instruction": "Nomad Governor: heal mesh RPC and petals daemon",
            "input": f"Target action: {action}",
            "output": f"Execution result: {result}",
            "action": action,
            "result": result,
            "nomad_agent": "Multi-WAN Nomad Courier v3.0"
        }
        with open(LORA_LOG, "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass

# Node metadata
NODES = {
    "macbook_pro": {
        "user": "aaronmaher",
        "host": "192.168.8.127",
        "port": 22,
        "jump": "root@192.168.8.1",
        "rpc_bin": "/Users/aaronmaher/llama.cpp/build/bin/ggml-rpc-server",
        "petals_model": None
    },
    "linux_head": {
        "user": "linux",
        "host": "10.1.0.12",
        "port": 22,
        "jump": None,
        "rpc_bin": "/home/linux/llama.cpp/build/bin/ggml-rpc-server",
        "petals_model": "Qwen/Qwen2-7B-Instruct"
    },
    "pixel": {
        "user": "u0_a363",
        "host": "10.1.0.13",
        "port": 8022,
        "jump": None,
        "rpc_bin": "/data/data/com.termux/files/home/llama.cpp/build/bin/ggml-rpc-server",
        "petals_model": "Qwen/Qwen2-7B-Instruct"
    }
}

def tcp_probe(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except Exception:
        return False

def http_health(url: str, timeout: float = 2.0) -> bool:
    try:
        r = urllib.request.urlopen(url, timeout=timeout)
        data = json.loads(r.read())
        return data.get("status") == "ok"
    except Exception:
        return False

def ssh_exec(node_key: str, remote_cmd: str) -> str:
    cfg = NODES[node_key]
    ssh_args = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=5",
        "-o", "BatchMode=yes",
        "-p", str(cfg["port"])
    ]
    if cfg["jump"]:
        ssh_args.extend(["-o", f"ProxyJump={cfg['jump']}"])
    ssh_args.extend([f"{cfg['user']}@{cfg['host']}", remote_cmd])
    try:
        res = subprocess.run(ssh_args, capture_output=True, text=True, timeout=15)
        return res.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"

def heal_local_models():
    # 1. Proxy (:8080)
    if http_health("http://127.0.0.1:8080/health"):
        log("✅ Local proxy :8080 HEALTHY")
    else:
        log("⚠️ Local proxy :8080 DOWN — restarting LaunchAgent")
        subprocess.run(["launchctl", "unload", "/Users/aaron/Library/LaunchAgents/ai.lauburu.unified.proxy.plist"], capture_output=True)
        time.sleep(1)
        subprocess.run(["launchctl", "load", "/Users/aaron/Library/LaunchAgents/ai.lauburu.unified.proxy.plist"], capture_output=True)
        log_lora("RESTART_PROXY_8080", "RELOADED")

    # 2. Local Model Heads (:8081)
    if http_health("http://127.0.0.1:8081/health"):
        log("✅ Qwen-Coder-7B Orchestrator :8081 HEALTHY")
    else:
        log("⚪ Qwen-Coder-7B :8081 Standby")

    # Guard RAM Sanctuary: Strictly do NOT auto-spawn 27B/70B models or RPC on Host Mac Mini
    log("🛡️ Sanctuary Invariant: Heavy 27B/70B models & Petals suppressed to preserve 9.6GB Host RAM.")


def heal_bluetooth_terminals():
    log("📶 [Tier 1: Bluetooth Terminal] Probing lowest network connectivity point...")
    blueutil = "/Users/aaron/.local/bin/blueutil"
    if os.path.exists(blueutil):
        # Ensure radio on
        p = subprocess.run([blueutil, "--power"], capture_output=True, text=True)
        if p.stdout.strip() != "1":
            log("⚠️ Bluetooth radio off — powering on")
            subprocess.run([blueutil, "--power", "1"], capture_output=True)
            time.sleep(1)

        devices = {
            "s20": ("5c-cb-99-05-81-41", "Aaron's S20+"),
            "pixel": ("30-e0-44-6d-18-ec", "Pixel 10 Pro XL"),
            "macbook_pro": ("2c-ca-16-08-c0-27", "MacBook Pro L2"),
        }
        for k, (addr, name) in devices.items():
            check = subprocess.run([blueutil, "--is-connected", addr], capture_output=True, text=True)
            if check.stdout.strip() == "1":
                log(f"✅ Bluetooth Terminal: {name} ({addr}) CONNECTED")
            else:
                log(f"⚠️ Bluetooth Terminal: {name} disconnected — attempting reconnect")
                res = subprocess.run([blueutil, "--connect", addr], capture_output=True, text=True)
                log(f"  Result: {res.stdout.strip() or 'Attempted'}")
                log_lora(f"HEAL_BT_TERMINAL_{k.upper()}", "RECONNECTED" if res.returncode == 0 else "STANDBY")
    else:
        log("⚠️ blueutil CLI not installed")

def heal_hardware_bridges():
    log("⚡ [Tier 2: Direct Hardware Bridge] Probing TB4 DMA and USB...")
    tb = subprocess.run(["ifconfig", "bridge0"], capture_output=True, text=True)
    if "status: active" in tb.stdout:
        log("✅ TB4 PCIe DMA bridge0 ACTIVE")
    else:
        log("⚪ TB4 PCIe DMA bridge0 standby")

def heal_local_lan():
    log("🌐 [Tier 3: Local LAN & Gateway] Probing Gateway 192.168.8.1...")
    if tcp_probe("192.168.8.1", 22):
        log("✅ Gateway 192.168.8.1:22 ONLINE")
    else:
        log("⚠️ Gateway unreachable")
    
    if tcp_probe("127.0.0.1", 18802):
        log("✅ WoL Hub API :18802 HEALTHY")

def heal_tailscale():
    log("🔒 [Tier 4: Tailscale WireGuard] Auditing Layer 3 encrypted overlay...")
    ts = subprocess.run(["which", "tailscale"], capture_output=True)
    if ts.returncode == 0:
        stat = subprocess.run(["tailscale", "status"], capture_output=True, text=True)
        active_lines = [l for l in stat.stdout.splitlines() if "active" in l]
        log(f"📡 Tailscale active peers: {len(active_lines)}")

def main():
    log("════════ Bottom-Up Bluetooth Terminal & Network Healer Cycle ════════")
    # 1. Default to Bluetooth terminal lowest connectivity point first
    heal_bluetooth_terminals()
    # 2. Hardware links
    heal_hardware_bridges()
    # 3. Local LAN
    heal_local_lan()
    # 4. Tailscale overlay
    heal_tailscale()
    # 5. Lightweight local proxies (RAM sanctuary strictly protected)
    heal_local_models()
    log("════════ Governor Cycle Complete ════════")

if __name__ == "__main__":
    main()

