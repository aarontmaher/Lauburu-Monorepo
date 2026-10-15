#!/usr/bin/env python3
"""
s20_shizuku_network.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Lauburu Mesh - L7 Samsung S20 Network Toolkit via Shizuku/Sui (Zero-Mock)

Utilizes the Android Shizuku/Sui Binder API (via `rish` or Termux wrapper)
to execute privileged network diagnostics without traditional root access.

Multi-Transport Execution Matrix (Rule 9 Multi-IP Fallback Compliant):
1. Local S20 Execution: Direct `rish -c '<command>'` within Termux.
2. Remote ADB Transport: Tailscale TCP (100.78.206.96:5555), LAN (192.168.8.131:5555), or USB (R3CN40CJJ1R).
3. Remote SSH Transport: u0_a420@100.78.206.96:8022 or u0_a420@192.168.8.131:8022.
4. Host Local Diagnostic: Transparent local socket/diagnostic fallback when remote edge is offline.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import sys
import json
import shlex
import shutil
import argparse
import subprocess

# ── S20 Node Network Matrix Configuration ─────────────────────────────────────
S20_TAILSCALE_IP = os.environ.get("S20_TAILSCALE_IP", "100.78.206.96")
S20_LAN_IP       = os.environ.get("S20_LAN_IP", "192.168.8.131")
S20_SSH_PORT     = int(os.environ.get("S20_SSH_PORT", "8022"))
S20_SSH_USER     = os.environ.get("S20_SSH_USER", "u0_a420")
S20_ADB_SERIAL   = os.environ.get("S20_ADB_SERIAL", "R3CN40CJJ1R")
S20_ADB_TCP      = f"{S20_TAILSCALE_IP}:5555"

# Candidate paths for rish on Android / Termux
RISH_CANDIDATE_PATHS = [
    os.path.expanduser("~/bin/rish"),
    "/data/data/com.termux/files/usr/bin/rish",
    "/data/data/com.termux/files/home/bin/rish",
    "/system/bin/rish",
    "/system/xbin/rish",
    shutil.which("rish")
]

def is_running_on_s20() -> bool:
    """Detects if script is currently executing locally on Android/Termux."""
    return os.path.exists("/data/data/com.termux") or "com.termux" in os.environ.get("PREFIX", "")

def find_local_rish() -> str:
    """Finds path to rish binary on local Android system."""
    for path in RISH_CANDIDATE_PATHS:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return "rish"

def run_local_rish_command(command: str, timeout: int = 5) -> dict:
    """Executes command locally on S20 using Shizuku/rish."""
    rish_bin = find_local_rish()
    full_cmd = [rish_bin, "-c", command]
    env = os.environ.copy()
    env["RISH_APPLICATION_ID"] = "com.termux"
    
    try:
        res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout, env=env)
        return {
            "success": res.returncode == 0,
            "transport": "local_rish",
            "command": command,
            "exit_code": res.returncode,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip()
        }
    except FileNotFoundError:
        # Fallback to standard sh if rish is missing locally
        res = subprocess.run(["sh", "-c", command], capture_output=True, text=True, timeout=timeout)
        return {
            "success": res.returncode == 0,
            "transport": "local_fallback_sh",
            "command": command,
            "exit_code": res.returncode,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip()
        }
    except Exception as e:
        return {
            "success": False,
            "transport": "local_rish",
            "command": command,
            "error": str(e),
            "exit_code": -1
        }

def run_remote_adb_command(command: str, timeout: int = 3) -> dict:
    """Executes command on S20 via ADB over TCP or USB with fast failover (Rule 9)."""
    adb_bin = shutil.which("adb") or "/Users/aaron/.local/bin/adb"
    if not shutil.which(adb_bin) and not os.path.exists(adb_bin):
        return {"success": False, "transport": "adb", "error": "adb binary not found", "exit_code": 127}
    
    # Check currently visible ADB devices first to avoid stalling on dead endpoints
    connected_devices = []
    try:
        dev_res = subprocess.run([adb_bin, "devices"], capture_output=True, text=True, timeout=2)
        connected_devices = [line.split()[0] for line in dev_res.stdout.splitlines()[1:] if "\tdevice" in line]
    except Exception:
        pass

    targets = [S20_ADB_TCP, S20_ADB_SERIAL, f"{S20_LAN_IP}:5555"]
    for target in targets:
        # If not already connected and it's a network target, attempt fast connect
        if target not in connected_devices and ":" in target:
            try:
                subprocess.run([adb_bin, "connect", target], capture_output=True, timeout=1.5)
            except Exception:
                continue
                
        try:
            escaped_cmd = shlex.quote(command)
            remote_cmd = f"if command -v rish >/dev/null 2>&1; then rish -c {escaped_cmd}; else eval {escaped_cmd}; fi"
            res = subprocess.run(
                [adb_bin, "-s", target, "shell", remote_cmd],
                capture_output=True, text=True, timeout=timeout
            )
            if res.returncode == 0 or res.stdout:
                return {
                    "success": res.returncode == 0,
                    "transport": f"adb_{target}",
                    "command": command,
                    "exit_code": res.returncode,
                    "stdout": res.stdout.strip(),
                    "stderr": res.stderr.strip()
                }
        except Exception:
            continue
            
    return {"success": False, "transport": "adb", "command": command, "error": "All ADB endpoints exhausted", "exit_code": 1}

def run_remote_ssh_command(command: str, timeout: int = 3) -> dict:
    """Executes command on S20 via SSH into Termux with fast connect timeout."""
    hosts = [S20_TAILSCALE_IP, S20_LAN_IP]
    escaped_cmd = shlex.quote(command)
    remote_cmd = f"export PATH=$PATH:/data/data/com.termux/files/usr/bin:~/bin; if command -v rish >/dev/null 2>&1; then rish -c {escaped_cmd}; else eval {escaped_cmd}; fi"
    
    for host in hosts:
        ssh_cmd = [
            "ssh",
            "-p", str(S20_SSH_PORT),
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=2",
            "-o", "BatchMode=yes",
            f"{S20_SSH_USER}@{host}",
            remote_cmd
        ]
        try:
            res = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
            if res.returncode == 0 or res.stdout:
                return {
                    "success": res.returncode == 0,
                    "transport": f"ssh_{host}",
                    "command": command,
                    "exit_code": res.returncode,
                    "stdout": res.stdout.strip(),
                    "stderr": res.stderr.strip()
                }
        except Exception:
            continue
            
    return {"success": False, "transport": "ssh", "command": command, "error": "All SSH endpoints exhausted", "exit_code": 1}

def run_shizuku_command(command: str, transport: str = "auto", timeout: int = 5) -> dict:
    """Unified entrypoint to execute privileged commands with fast multi-tier fallback."""
    if transport == "local" or (transport == "auto" and is_running_on_s20()):
        return run_local_rish_command(command, timeout=timeout)
    
    # If remote, try ADB first with short timeout
    if transport in ("auto", "adb"):
        adb_res = run_remote_adb_command(command, timeout=2.5)
        if adb_res.get("success"):
            return adb_res
            
    # Try SSH next
    if transport in ("auto", "ssh"):
        ssh_res = run_remote_ssh_command(command, timeout=2.5)
        if ssh_res.get("success"):
            return ssh_res

    # Host local diagnostic fallback if on host machine and edge node offline
    if transport == "auto":
        try:
            if any(op in command for op in ["|", "&&", "||", ">", "<"]):
                res = subprocess.run(["sh", "-c", command], capture_output=True, text=True, timeout=timeout)
            else:
                cmd_args = shlex.split(command)
                res = subprocess.run(cmd_args, capture_output=True, text=True, timeout=timeout)
            return {
                "success": res.returncode == 0,
                "transport": "host_local_direct",
                "command": command,
                "exit_code": res.returncode,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
                "note": "Executed on local host environment (S20 edge node unreachable)"
            }
        except Exception as e:
            return {
                "success": False,
                "transport": "none",
                "command": command,
                "error": str(e),
                "exit_code": -1
            }

    return {"success": False, "transport": transport, "error": "Command failed across specified transport", "exit_code": 1}

def get_network_interfaces(transport: str = "auto") -> dict:
    """Retrieves physical & virtual network interfaces via ip link."""
    return run_shizuku_command("ip link", transport=transport)

def get_routing_table(transport: str = "auto") -> dict:
    """Retrieves kernel routing table via ip route."""
    return run_shizuku_command("ip route", transport=transport)

def get_socket_statistics(transport: str = "auto") -> dict:
    """Retrieves active listening sockets and ports via ss or netstat."""
    return run_shizuku_command("ss -tuln 2>/dev/null || netstat -tuln", transport=transport)

def ping_host(host: str, count: int = 3, transport: str = "auto") -> dict:
    """Executes ICMP ping diagnostic with count and timeout limits."""
    safe_host = shlex.quote(host.strip())
    if sys.platform == "darwin":
        ping_cmd = f"ping -c {count} -W 1000 {safe_host}"
    else:
        ping_cmd = f"ping -c {count} -W 1 -w {max(count, 2)} {safe_host}"
    return run_shizuku_command(ping_cmd, transport=transport)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Samsung S20 Shizuku/Sui Elevated Network Toolkit")
    parser.add_argument("--action", choices=["interfaces", "route", "netstat", "ping", "raw"], required=True)
    parser.add_argument("--host", type=str, default="1.1.1.1", help="Target host for ping")
    parser.add_argument("--count", type=int, default=3, help="Ping count")
    parser.add_argument("--cmd", type=str, help="Raw command to execute with --action raw")
    parser.add_argument("--transport", choices=["auto", "local", "adb", "ssh"], default="auto")
    args = parser.parse_args()
    
    if args.action == "interfaces":
        result = get_network_interfaces(transport=args.transport)
    elif args.action == "route":
        result = get_routing_table(transport=args.transport)
    elif args.action == "netstat":
        result = get_socket_statistics(transport=args.transport)
    elif args.action == "ping":
        result = ping_host(args.host, count=args.count, transport=args.transport)
    elif args.action == "raw":
        if not args.cmd:
            result = {"success": False, "error": "--cmd is required when --action raw is specified"}
        else:
            result = run_shizuku_command(args.cmd, transport=args.transport)
            
    print(json.dumps(result, indent=2))
