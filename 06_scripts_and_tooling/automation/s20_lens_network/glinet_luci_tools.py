#!/usr/bin/env python3
"""
glinet_luci_tools.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Lauburu Mesh - GL.iNet Wi-Fi 7 Sovereign Gateway Tool-Calling API (Zero-Mock)

Translates AI Tool-Calling requests into concrete OpenWrt `ubus`, `wg`, and
LuCI API commands for the GL.iNet Router (GL-MT3600BE / GL-BE14000).

Capabilities:
1. WireGuard Client & Server Management via GL.iNet `ubus call wg_client`.
2. LuCI / OpenWrt active network interface & device inspection.
3. AI Function/Tool-Calling Dispatcher converting structured JSON schemas into actions.
4. Returns cleanly parsed structured JSON (no nested double-encoded strings).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import sys
import json
import shlex
import argparse
import subprocess
from typing import Dict, Any, Optional

ROUTER_HOST_LAN       = os.environ.get("ROUTER_HOST", "192.168.8.1")
ROUTER_HOST_TAILSCALE = os.environ.get("ROUTER_TAILSCALE", "100.103.212.34")
ROUTER_HOST_WG        = "10.1.0.1"
ROUTER_USER           = os.environ.get("ROUTER_USER", "root")
ROUTER_PORT           = int(os.environ.get("ROUTER_PORT", "22"))

def run_router_command(command: str, timeout: int = 3) -> Dict[str, Any]:
    """Executes a command on the GL.iNet router via SSH with network exhaustion and fast failover."""
    hosts = [ROUTER_HOST_LAN, ROUTER_HOST_TAILSCALE, ROUTER_HOST_WG]
    
    last_error = ""
    for host in hosts:
        ssh_cmd = [
            "ssh",
            "-p", str(ROUTER_PORT),
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=2",
            "-o", "BatchMode=yes",
            f"{ROUTER_USER}@{host}",
            command
        ]
        try:
            res = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
            raw_stdout = res.stdout.strip()
            raw_stderr = res.stderr.strip()
            
            # Attempt to parse stdout as JSON if applicable
            parsed_data = None
            if raw_stdout:
                try:
                    parsed_data = json.loads(raw_stdout)
                except json.JSONDecodeError:
                    parsed_data = None

            return {
                "success": res.returncode == 0,
                "host": host,
                "command": command,
                "exit_code": res.returncode,
                "stdout": raw_stdout,
                "stderr": raw_stderr,
                "data": parsed_data if parsed_data is not None else raw_stdout
            }
        except subprocess.TimeoutExpired:
            last_error = f"SSH timeout to {host}"
            continue
        except Exception as e:
            last_error = str(e)
            continue

    # Diagnostic fallback if router is offline
    return {
        "success": False,
        "error": f"Router unreachable across hosts {hosts}. Last error: {last_error}",
        "command": command,
        "exit_code": -1,
        "data": None
    }

# ── WireGuard Client ubus Operations ──────────────────────────────────────────

def wg_client_status() -> Dict[str, Any]:
    """Queries GL.iNet active WireGuard client status."""
    return run_router_command("ubus call wg_client get_status")

def wg_client_profiles() -> Dict[str, Any]:
    """Queries all configured WireGuard client profiles."""
    return run_router_command("ubus call wg_client get_profiles")

def wg_client_start(peer_id: Optional[str] = None) -> Dict[str, Any]:
    """Starts the WireGuard client connection."""
    if peer_id:
        payload_str = json.dumps({"peer_id": peer_id})
        cmd = f"ubus call wg_client start {shlex.quote(payload_str)}"
    else:
        cmd = "ubus call wg_client start"
    return run_router_command(cmd)

def wg_client_stop() -> Dict[str, Any]:
    """Stops the active WireGuard client connection."""
    return run_router_command("ubus call wg_client stop")

def wg_client_switch(peer_id: str) -> Dict[str, Any]:
    """Switches active WireGuard profile to specified peer_id."""
    payload_str = json.dumps({"peer_id": peer_id})
    cmd = f"ubus call wg_client switch {shlex.quote(payload_str)}"
    return run_router_command(cmd)

def wg_server_status() -> Dict[str, Any]:
    """Queries GL.iNet active WireGuard server status."""
    return run_router_command("ubus call wg_server get_status")

# ── LuCI / OpenWrt Network Interface Operations ───────────────────────────────

def luci_interfaces_dump() -> Dict[str, Any]:
    """Dumps all active LuCI/OpenWrt network interfaces."""
    return run_router_command("ubus call network.interface dump")

def luci_interface_status(interface_name: str = "lan") -> Dict[str, Any]:
    """Queries status of a specific interface (lan, wan, wgclient, etc)."""
    safe_name = shlex.quote(interface_name.strip())
    return run_router_command(f"ubus call network.interface.{safe_name} status")

def luci_device_status(device_name: str = "br-lan") -> Dict[str, Any]:
    """Queries status of physical or bridge device (br-lan, eth2, eth1.3)."""
    payload_str = json.dumps({"name": device_name.strip()})
    cmd = f"ubus call network.device status {shlex.quote(payload_str)}"
    return run_router_command(cmd)

def get_wg_show(interface: Optional[str] = None) -> Dict[str, Any]:
    """Runs raw kernel WireGuard status query via `wg show`."""
    if interface:
        safe_iface = shlex.quote(interface.strip())
        cmd = f"wg show {safe_iface}"
    else:
        cmd = "wg show"
    return run_router_command(cmd)

# ── AI Tool-Calling Router & Schema Translator ─────────────────────────────────

TOOL_REGISTRY = {
    "wg_client_status": wg_client_status,
    "wg_client_profiles": wg_client_profiles,
    "wg_client_start": wg_client_start,
    "wg_client_stop": wg_client_stop,
    "wg_client_switch": wg_client_switch,
    "wg_server_status": wg_server_status,
    "luci_interfaces_dump": luci_interfaces_dump,
    "luci_interface_status": luci_interface_status,
    "luci_device_status": luci_device_status,
    "get_wg_show": get_wg_show
}

ACTION_ALIASES = {
    "status": "wg_client_status",
    "profiles": "wg_client_profiles",
    "start": "wg_client_start",
    "stop": "wg_client_stop",
    "switch": "wg_client_switch",
    "interfaces": "luci_interfaces_dump",
    "interface": "luci_interface_status",
    "device": "luci_device_status",
    "show": "get_wg_show",
    "wg_show": "get_wg_show"
}

def dispatch_tool_call(tool_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Translates an AI tool-calling JSON payload into the corresponding router function."""
    func_name = ""
    args: Dict[str, Any] = {}
    
    if "function" in tool_payload and isinstance(tool_payload["function"], dict):
        func_name = tool_payload["function"].get("name", "")
        raw_args = tool_payload["function"].get("arguments", {})
        if isinstance(raw_args, str):
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = {}
        elif isinstance(raw_args, dict):
            args = raw_args
    elif "name" in tool_payload:
        func_name = tool_payload["name"]
        args = tool_payload.get("arguments") or tool_payload.get("args") or tool_payload.get("parameters") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
    elif "tool" in tool_payload:
        func_name = tool_payload["tool"]
        args = tool_payload.get("params", {})
    elif "action" in tool_payload:
        func_name = tool_payload["action"]
        args = {k: v for k, v in tool_payload.items() if k != "action"}

    resolved_name = ACTION_ALIASES.get(func_name, func_name)
    
    if resolved_name not in TOOL_REGISTRY:
        return {
            "success": False,
            "tool": func_name,
            "command": func_name,
            "exit_code": -1,
            "error": f"Unknown tool or action: '{func_name}'. Available tools: {list(TOOL_REGISTRY.keys())}",
            "available_tools": list(TOOL_REGISTRY.keys())
        }

    handler = TOOL_REGISTRY[resolved_name]
    try:
        if args and isinstance(args, dict):
            import inspect
            sig = inspect.signature(handler)
            valid_kwargs = {k: v for k, v in args.items() if k in sig.parameters}
            return handler(**valid_kwargs)
        else:
            return handler()
    except Exception as e:
        return {
            "success": False,
            "tool": resolved_name,
            "command": resolved_name,
            "exit_code": -1,
            "error": f"Execution error in {resolved_name}: {str(e)}"
        }

def execute_luci_tool(action: str, **kwargs) -> Dict[str, Any]:
    """Compatibility API for legacy invocations."""
    payload = {"action": action, **kwargs}
    return dispatch_tool_call(payload)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GL.iNet & LuCI Router Tool-Calling Interface")
    parser.add_argument("--action", choices=list(TOOL_REGISTRY.keys()) + list(ACTION_ALIASES.keys()),
                        help="Action name or alias")
    parser.add_argument("--tool-call", type=str, help="Full JSON AI tool-call payload")
    parser.add_argument("--peer-id", type=str, help="WireGuard peer ID")
    parser.add_argument("--interface", type=str, default="lan", help="Interface name")
    parser.add_argument("--device", type=str, default="br-lan", help="Device name")
    args = parser.parse_args()

    if args.tool_call:
        try:
            payload = json.loads(args.tool_call)
            res = dispatch_tool_call(payload)
        except json.JSONDecodeError:
            res = {"success": False, "error": "Invalid JSON in --tool-call argument"}
    elif args.action:
        extra_args = {}
        if args.peer_id:
            extra_args["peer_id"] = args.peer_id
        if args.interface:
            extra_args["interface_name"] = args.interface
        if args.device:
            extra_args["device_name"] = args.device
        res = execute_luci_tool(args.action, **extra_args)
    else:
        print("Usage: --action <action> OR --tool-call '<json_payload>'")
        print("Available tools:", ", ".join(TOOL_REGISTRY.keys()))
        sys.exit(1)

    print(json.dumps(res, indent=2))
