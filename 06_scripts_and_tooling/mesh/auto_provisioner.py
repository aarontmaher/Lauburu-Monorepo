#!/usr/bin/env python3
"""
Zero-Friction Mesh Auto-Provisioner
Lauburu Immortal Swarm — Generation 74
Discovers devices on the mesh, checks llama.cpp RPC server status, and prints
provisioning commands for human review. NEVER auto-pushes binaries.
"""

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MESH_DATA_DIR = REPO_ROOT / "data" / "mesh"
LORA_DIR = REPO_ROOT / "data" / "lora_datasets"
KNOWN_NODES_FILE = MESH_DATA_DIR / "known_nodes.json"
LORA_FILE = LORA_DIR / "mesh_provisioning.jsonl"

MESH_DATA_DIR.mkdir(parents=True, exist_ok=True)
LORA_DIR.mkdir(parents=True, exist_ok=True)

KNOWN_USERS = ["aaron", "root", "pi", "ubuntu", "lauburu"]
TARGET_SUBNET = "192.168.8.0/24"

DEFAULT_KNOWN_NODES = {
    "nodes": [
        {"name": "Mac_Node",        "ip": "192.168.8.230",   "type": "mac",     "tailscale_ip": "100.101.39.98", "rpc_port": 50052, "status": "known"},
        {"name": "MacBook_Pro",     "ip": "169.254.187.138", "type": "mac",     "tailscale_ip": "100.101.39.98", "rpc_port": 50052, "status": "known"},
        {"name": "Linux_Head_Node", "ip": "100.101.39.98",   "type": "linux",   "tailscale_ip": "100.101.39.98", "rpc_port": 50052, "status": "known"},
        {"name": "Linux_Tablet",    "ip": "100.81.92.125",   "type": "linux",   "tailscale_ip": "100.81.92.125", "rpc_port": 50052, "status": "known"},
        {"name": "MacBook_Air",     "ip": "100.93.158.96",   "type": "mac",     "tailscale_ip": "100.93.158.96", "rpc_port": 50052, "status": "known"},
        {"name": "Pixel",           "ip": "100.73.38.87",    "type": "android", "tailscale_ip": "100.73.38.87",  "rpc_port": 50052, "status": "known"},
        {"name": "Samsung_S20",     "ip": "100.84.40.95",    "type": "android", "tailscale_ip": "100.84.40.95",  "rpc_port": 50052, "status": "known"},
    ],
    "last_updated_utc": None,
    "mesh_subnet": TARGET_SUBNET,
}


def load_known_nodes() -> dict:
    if not KNOWN_NODES_FILE.exists():
        print(f"[INFO] {KNOWN_NODES_FILE} not found -- creating default registry.")
        save_known_nodes(DEFAULT_KNOWN_NODES)
        return DEFAULT_KNOWN_NODES.copy()
    with open(KNOWN_NODES_FILE) as f:
        return json.load(f)


def save_known_nodes(data: dict) -> None:
    data["last_updated_utc"] = datetime.now(timezone.utc).isoformat()
    with open(KNOWN_NODES_FILE, "w") as f:
        json.dump(data, f, indent=2)


def known_ips(nodes_data: dict) -> set:
    return {n["ip"] for n in nodes_data.get("nodes", [])}


def run_arp_scan() -> list:
    """Run arp -a and parse IPs on 192.168.8.x subnet."""
    try:
        result = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=10)
        ips = re.findall(r"\((\d+\.\d+\.\d+\.\d+)\)", result.stdout)
        return list(set(ip for ip in ips if ip.startswith("192.168.8.")))
    except Exception as e:
        print(f"[WARN] arp -a failed: {e}")
        return []


def try_adb_connect(ip: str) -> bool:
    """Try adb connect. Returns True if Android device detected."""
    try:
        result = subprocess.run(
            ["adb", "connect", f"{ip}:5555"],
            capture_output=True, text=True, timeout=8
        )
        output = result.stdout + result.stderr
        return "connected" in output.lower() and "unable" not in output.lower()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def try_ssh_uname(ip: str, user: str):
    """Try SSH uname. Returns (success, os_name)."""
    try:
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=3", "-o", "StrictHostKeyChecking=no",
             "-o", "BatchMode=yes", f"{user}@{ip}", "uname"],
            capture_output=True, text=True, timeout=8
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return False, ""


def check_android_rpc(ip: str) -> bool:
    """Check if llama.cpp RPC server is running on Android via adb."""
    try:
        result = subprocess.run(
            ["adb", "-s", f"{ip}:5555", "shell", "netstat -tlnp 2>/dev/null | grep 50052"],
            capture_output=True, text=True, timeout=10
        )
        return "50052" in result.stdout
    except Exception:
        return False


def check_linux_rpc(ip: str, user: str) -> bool:
    """Check if llama-rpc-server is running via SSH."""
    try:
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=3", "-o", "StrictHostKeyChecking=no",
             "-o", "BatchMode=yes", f"{user}@{ip}", "pgrep -f rpc-server"],
            capture_output=True, text=True, timeout=8
        )
        return result.returncode == 0 and result.stdout.strip() != ""
    except Exception:
        return False


def probe_unknown_ip(ip: str) -> dict:
    """
    Probe an unknown IP. NEVER auto-executes push commands.
    All binary push commands are marked PENDING_APPROVAL.
    """
    report = {
        "ip": ip,
        "device_type": "unknown",
        "rpc_running": False,
        "status": "UNKNOWN",
        "pending_actions": [],
        "approval_required": [],
    }

    if try_adb_connect(ip):
        report["device_type"] = "android"
        rpc_running = check_android_rpc(ip)
        report["rpc_running"] = rpc_running
        if rpc_running:
            report["status"] = "IN_MESH"
            print(f"  [{ip}] Android -- llama.cpp RPC already running on port 50052")
        else:
            report["status"] = "DISCOVERED_NEEDS_PROVISIONING"
            start_cmd = f"adb -s {ip}:5555 shell 'nohup /data/local/tmp/llama-rpc-server --host 0.0.0.0 --port 50052 &'"
            push_cmd = (
                f"adb -s {ip}:5555 push /path/to/ggml-rpc-server /data/local/tmp/ggml-rpc-server && "
                f"adb -s {ip}:5555 shell 'chmod +x /data/local/tmp/ggml-rpc-server'"
            )
            print(f"  [{ip}] Android -- RPC NOT running.")
            print(f"         [PENDING_APPROVAL] Push binary: {push_cmd}")
            print(f"         [PENDING_APPROVAL] Start RPC:   {start_cmd}")
            report["pending_actions"].append({"action": "start_rpc", "command": start_cmd})
            report["approval_required"].append({"action": "push_binary", "command": push_cmd, "status": "PENDING_APPROVAL"})
        return report

    for user in KNOWN_USERS:
        success, os_name = try_ssh_uname(ip, user)
        if success:
            dev_type = "mac" if "Darwin" in os_name else "linux"
            report["device_type"] = dev_type
            report["ssh_user"] = user
            rpc_running = check_linux_rpc(ip, user)
            report["rpc_running"] = rpc_running
            if rpc_running:
                report["status"] = "IN_MESH"
                print(f"  [{ip}] {dev_type} ({user}) -- llama-rpc-server running")
            else:
                report["status"] = "DISCOVERED_NEEDS_PROVISIONING"
                start_cmd = f"ssh {user}@{ip} 'nohup /usr/local/bin/llama-rpc-server --host 0.0.0.0 --port 50052 > /tmp/rpc.log 2>&1 &'"
                push_cmd = f"scp /path/to/llama-rpc-server {user}@{ip}:/usr/local/bin/llama-rpc-server && ssh {user}@{ip} 'chmod +x /usr/local/bin/llama-rpc-server'"
                print(f"  [{ip}] {dev_type} ({user}) -- RPC NOT running.")
                print(f"         [PENDING_APPROVAL] Push: {push_cmd}")
                print(f"         [PENDING_APPROVAL] Start: {start_cmd}")
                report["pending_actions"].append({"action": "start_rpc", "command": start_cmd})
                report["approval_required"].append({"action": "push_binary", "command": push_cmd, "status": "PENDING_APPROVAL"})
            return report

    print(f"  [{ip}] No ADB or SSH response -- PENDING_HARDWARE_VERIFICATION")
    report["status"] = "PENDING_HARDWARE_VERIFICATION"
    return report


def serialize_lora(event: dict) -> None:
    entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "instruction": "Discover mesh nodes on the local network and determine which require llama.cpp RPC server provisioning.",
        "input": f"IP={event['ip']}, type={event['device_type']}, rpc_running={event['rpc_running']}",
        "output": f"status={event['status']}, pending_actions={len(event.get('pending_actions', []))}, approval_required={len(event.get('approval_required', []))}",
    }
    with open(LORA_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def run_scan(verbose: bool = True) -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    if verbose:
        print(f"\n[auto_provisioner] Mesh scan -- {ts}")
        print("-" * 70)

    nodes_data = load_known_nodes()
    existing_ips = known_ips(nodes_data)

    if verbose:
        print(f"[INFO] Known nodes: {len(nodes_data['nodes'])}")
        print(f"[INFO] Running: arp -a (scanning {TARGET_SUBNET})")

    discovered_ips = run_arp_scan()
    if verbose:
        print(f"[INFO] ARP discovered {len(discovered_ips)} IPs: {discovered_ips}")

    new_ips = [ip for ip in discovered_ips if ip not in existing_ips]
    known_in_subnet = [ip for ip in discovered_ips if ip in existing_ips]

    report = {
        "timestamp_utc": ts,
        "known_in_mesh": [],
        "new_discovered": [],
        "needs_provisioning": [],
        "pending_hardware": [],
    }

    if verbose:
        print(f"\n[Known nodes on subnet: {len(known_in_subnet)}]")
    for ip in known_in_subnet:
        node = next((n for n in nodes_data["nodes"] if n["ip"] == ip), {"name": ip, "ip": ip})
        report["known_in_mesh"].append(ip)
        if verbose:
            print(f"  [OK] {node.get('name', ip)} ({ip}) -- in registry")

    if verbose:
        print(f"\n[New IPs to probe: {len(new_ips)}]")
    for ip in new_ips:
        result = probe_unknown_ip(ip)
        serialize_lora(result)
        if result["status"] == "IN_MESH":
            report["known_in_mesh"].append(ip)
        elif result["status"] == "DISCOVERED_NEEDS_PROVISIONING":
            report["new_discovered"].append(ip)
            report["needs_provisioning"].append(result)
            nodes_data["nodes"].append({
                "name": f"AutoDiscovered_{ip.replace('.', '_')}",
                "ip": ip,
                "type": result["device_type"],
                "rpc_port": 50052,
                "status": "PENDING_PROVISIONING",
            })
        else:
            report["pending_hardware"].append(ip)

    save_known_nodes(nodes_data)

    if verbose:
        print(f"\n{'='*70}")
        print(f"PROVISIONING REPORT -- {ts}")
        print(f"  Already in mesh:     {len(report['known_in_mesh'])} device(s)")
        print(f"  Newly discovered:    {len(report['new_discovered'])} device(s)")
        print(f"  Needs provisioning:  {len(report['needs_provisioning'])} device(s)")
        print(f"  Pending HW verify:   {len(report['pending_hardware'])} IP(s)")
        if report["needs_provisioning"]:
            print(f"\n  WARNING: Commands below require HUMAN APPROVAL before execution:")
            for entry in report["needs_provisioning"]:
                for action in entry.get("approval_required", []):
                    print(f"     [{action['status']}] {action['command']}")
        print(f"\n[OK] Written -> {KNOWN_NODES_FILE}")
        print(f"[OK] LoRA entries appended -> {LORA_FILE}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Mesh Auto-Provisioner -- Lauburu Swarm Gen 74")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scan-once", action="store_true", help="Single discovery scan")
    group.add_argument("--daemon", action="store_true", help="Continuous daemon mode (120s interval)")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    args = parser.parse_args()
    verbose = not args.quiet

    if args.scan_once:
        run_scan(verbose=verbose)
    elif args.daemon:
        print("[auto_provisioner] Daemon mode (120s) -- Ctrl+C to stop")
        cycle = 0
        while True:
            cycle += 1
            if verbose:
                print(f"\n{'='*70}\n  DAEMON CYCLE #{cycle}")
            try:
                run_scan(verbose=verbose)
            except Exception as e:
                print(f"[ERROR] Cycle {cycle}: {e}", file=sys.stderr)
            time.sleep(120)


if __name__ == "__main__":
    main()
