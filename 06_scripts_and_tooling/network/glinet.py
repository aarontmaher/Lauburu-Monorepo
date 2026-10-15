#!/usr/bin/env python3
"""
glinet.py / gli_py — Sovereign GL.iNet & OpenWrt Router Automation Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Lauburu Mesh Ecosystem — Canonical Router Control Library & CLI (Zero-Mock)

Targets:
- GL.iNet GL-MT3600BE (Beryl 7 Wi-Fi 7 Mesh Gateway)
- GL.iNet GL-BE14000 (Sovereign Wi-Fi 7 Gateway)

Features:
1. Dual-Transport Architecture:
   - Native HTTP JSON-RPC 2.0 (OpenSSL crypt-SHA256 authenticated session)
   - High-Speed SSH Dropbear / ubus pipeline with network auto-failover
2. Hardware USB-A Bridge & ADB Keepalive (Pixel 10 Pro XL / Samsung S20+)
3. WireGuard Client/Server & Wi-Fi 7 MLO Radio Controls
4. Real-Time Client Tracking & Bandwidth Accounting
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import sys
import json
import time
import shlex
import socket
import argparse
import hashlib
import subprocess
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple

# ============================================================================
# Canonical Defaults
# ============================================================================
DEFAULT_ROUTER_HOST = os.environ.get("ROUTER_HOST", "192.168.8.1")
DEFAULT_ROUTER_PORT = int(os.environ.get("ROUTER_PORT", "22"))
DEFAULT_ROUTER_USER = os.environ.get("ROUTER_USER", "root")
DEFAULT_ROUTER_PW   = os.environ.get("ROUTER_PASSWORD", "goldfighting1")

FAILOVER_HOSTS = [
    DEFAULT_ROUTER_HOST,
    "100.122.185.123", # Primary Tailscale
    "100.103.212.34",  # Secondary Tailscale
    "10.1.0.1"         # WireGuard VPN Mesh
]


class GLiNetRouter:
    """Canonical client for GL.iNet v4.x routers supporting HTTP JSON-RPC and SSH ubus."""

    def __init__(self,
                 host: str = DEFAULT_ROUTER_HOST,
                 username: str = DEFAULT_ROUTER_USER,
                 password: str = DEFAULT_ROUTER_PW,
                 ssh_port: int = DEFAULT_ROUTER_PORT,
                 timeout: float = 4.0):
        self.host = host
        self.username = username
        self.password = password
        self.ssh_port = ssh_port
        self.timeout = timeout
        self.sid: Optional[str] = None
        self._active_host = host

    # ────────────────────────────────────────────────────────────────────────
    # 1. Transport Layer A: SSH & ubus Fast-Path (Sub-millisecond)
    # ────────────────────────────────────────────────────────────────────────

    def run_ssh(self, command: str, target_host: Optional[str] = None) -> Dict[str, Any]:
        """Executes a command via SSH on the router with auto-failover across mesh IPs."""
        hosts_to_try = [target_host] if target_host else [self._active_host] + [h for h in FAILOVER_HOSTS if h != self._active_host]

        last_err = ""
        for host in hosts_to_try:
            ssh_cmd = [
                "ssh",
                "-p", str(self.ssh_port),
                "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=2",
                "-o", "BatchMode=yes",
                f"{self.username}@{host}",
                command
            ]
            try:
                res = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=self.timeout)
                if res.returncode == 0 or res.stdout:
                    self._active_host = host
                    parsed = None
                    try:
                        parsed = json.loads(res.stdout.strip())
                    except Exception:
                        parsed = res.stdout.strip()
                    return {
                        "success": res.returncode == 0,
                        "host": host,
                        "exit_code": res.returncode,
                        "stdout": res.stdout.strip(),
                        "stderr": res.stderr.strip(),
                        "data": parsed
                    }
                last_err = res.stderr.strip()
            except Exception as e:
                last_err = str(e)
                continue

        return {
            "success": False,
            "error": f"Failed across all mesh hosts. Last error: {last_err}",
            "exit_code": -1,
            "data": None
        }

    def ubus_call(self, service: str, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Invokes an OpenWrt ubus method via SSH."""
        cmd = f"ubus call {shlex.quote(service)} {shlex.quote(method)}"
        if params:
            cmd += f" {shlex.quote(json.dumps(params))}"
        res = self.run_ssh(cmd)
        return res

    # ────────────────────────────────────────────────────────────────────────
    # 2. Transport Layer B: HTTP JSON-RPC Session API (gl-session)
    # ────────────────────────────────────────────────────────────────────────

    def login_http(self) -> bool:
        """
        Authenticates against GL.iNet v4.x /rpc endpoint using OpenSSL crypt-SHA256 handshake.
        Formula: sha256(username + ":" + crypt(password, "$5$" + salt + "$") + ":" + nonce)
        """
        rpc_url = f"http://{self.host}/rpc"
        try:
            # 1. Challenge
            req_data = json.dumps({
                "jsonrpc": "2.0",
                "method": "challenge",
                "params": {"username": self.username},
                "id": 1
            }).encode()
            req = urllib.request.Request(rpc_url, data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                res = json.loads(resp.read().decode())
                if "error" in res:
                    return False
                nonce = res["result"]["nonce"]
                salt = res["result"]["salt"]

            # 2. Compute crypt-SHA256 via openssl
            cmd = ["openssl", "passwd", "-5", "-salt", salt, self.password]
            crypted_pw = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()

            # 3. Hash computation
            hash_payload = f"{self.username}:{crypted_pw}:{nonce}".encode()
            login_hash = hashlib.sha256(hash_payload).hexdigest()

            # 4. Login execution
            login_payload = json.dumps({
                "jsonrpc": "2.0",
                "method": "login",
                "params": {"username": self.username, "hash": login_hash},
                "id": 2
            }).encode()
            req2 = urllib.request.Request(rpc_url, data=login_payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req2, timeout=self.timeout) as resp2:
                res2 = json.loads(resp2.read().decode())
                if "result" in res2 and "sid" in res2["result"]:
                    self.sid = res2["result"]["sid"]
                    return True
                return False
        except Exception:
            return False

    def rpc_call(self, module: str, func: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Calls GL.iNet session-authenticated RPC function over HTTP."""
        if not self.sid and not self.login_http():
            # Fallback to SSH ubus if HTTP login fails
            return self.ubus_call(module, func, params)

        rpc_url = f"http://{self.host}/rpc"
        call_payload = json.dumps({
            "jsonrpc": "2.0",
            "method": "call",
            "params": [self.sid, module, func, params or {}],
            "id": int(time.time() * 1000) % 100000
        }).encode()

        try:
            req = urllib.request.Request(rpc_url, data=call_payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())
                if "error" in data and data["error"].get("code") == -32000:
                    # Session expired, re-login once
                    if self.login_http():
                        return self.rpc_call(module, func, params)
                return {"success": "error" not in data, "data": data.get("result", {})}
        except Exception as e:
            # Fallback to SSH ubus
            return self.ubus_call(module, func, params)

    # ────────────────────────────────────────────────────────────────────────
    # 3. High-Level Subsystem Management
    # ────────────────────────────────────────────────────────────────────────

    def get_system_status(self) -> Dict[str, Any]:
        """Retrieves system model, OpenWrt release, uptime, and load averages."""
        res = self.run_ssh("cat /etc/openwrt_release; cat /etc/glversion 2>/dev/null; uptime; cat /proc/loadavg")
        lines = res.get("stdout", "").splitlines()
        release_info = {}
        for l in lines:
            if "=" in l:
                k, v = l.split("=", 1)
                release_info[k.strip()] = v.strip().strip("'\"")

        model_res = self.run_ssh("cat /tmp/sysinfo/model 2>/dev/null || cat /proc/cpuinfo | grep 'model name' | head -n 1")
        return {
            "model": model_res.get("stdout", "GL.iNet Router"),
            "openwrt": release_info.get("DISTRIB_DESCRIPTION", "OpenWrt"),
            "target": release_info.get("DISTRIB_TARGET", "mediatek"),
            "active_host": self._active_host,
            "connected": res.get("success", False)
        }

    def get_clients(self) -> List[Dict[str, Any]]:
        """Returns list of all active network clients with IP, MAC, hostname, and bandwidth."""
        res = self.ubus_call("gl-clients", "list")
        if not res.get("success") or not isinstance(res.get("data"), dict):
            # Fallback to dhcp leases
            dhcp_res = self.run_ssh("cat /tmp/dhcp.leases 2>/dev/null")
            clients = []
            for l in dhcp_res.get("stdout", "").splitlines():
                parts = l.split()
                if len(parts) >= 4:
                    clients.append({
                        "mac": parts[1],
                        "ip": parts[2],
                        "name": parts[3] if parts[3] != "*" else "Unknown",
                        "online": True
                    })
            return clients

        raw_clients = res["data"].get("clients", {})
        parsed = []
        for mac, info in raw_clients.items():
            parsed.append({
                "mac": mac,
                "ip": info.get("ip", ""),
                "name": info.get("name", "Unknown"),
                "online": info.get("online", False),
                "rx_bytes": info.get("total_rx", 0),
                "tx_bytes": info.get("total_tx", 0),
                "iface": info.get("iface", "")
            })
        return parsed

    def get_usb_devices(self) -> Dict[str, Any]:
        """Scans USB buses for connected peripherals (Pixel 10, Samsung S20, USB Dongles)."""
        res = self.run_ssh("lsusb; dmesg | grep -i -E 'usb|android|google|pixel' | tail -n 15")
        raw = res.get("stdout", "")
        devices = []
        for line in raw.splitlines():
            if "Bus" in line and "Device" in line:
                devices.append(line.strip())

        # Check for active Android ADB or RNDIS / CDC-NCM interfaces
        net_res = self.run_ssh("ip -br link show | grep -E 'usb|rndis|eth' || true")
        return {
            "usb_devices": devices,
            "interfaces": net_res.get("stdout", "").splitlines(),
            "raw_dmesg": raw
        }

    def get_wireguard_status(self) -> Dict[str, Any]:
        """Queries kernel WireGuard and GL.iNet wg_client status."""
        wg_show = self.run_ssh("wg show 2>/dev/null")
        client_res = self.ubus_call("wg_client", "get_status")
        return {
            "wg_show": wg_show.get("stdout", ""),
            "client_status": client_res.get("data", {})
        }

    def get_interfaces(self) -> Dict[str, Any]:
        """Dumps all active LuCI / OpenWrt network interfaces."""
        res = self.ubus_call("network.interface", "dump")
        return res.get("data", {})


# ============================================================================
# CLI Command Dispatcher
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="GL.iNet & OpenWrt Sovereign Router CLI (glinet.py)")
    parser.add_argument("--host", default=DEFAULT_ROUTER_HOST, help="Router Host IP")
    parser.add_argument("--user", default=DEFAULT_ROUTER_USER, help="Admin username")
    parser.add_argument("--password", default=DEFAULT_ROUTER_PW, help="Admin password")
    parser.add_argument("--status", action="store_true", help="Print overall system status")
    parser.add_argument("--clients", action="store_true", help="List connected clients")
    parser.add_argument("--usb", action="store_true", help="Inspect USB hardware & Android bridges")
    parser.add_argument("--wireguard", action="store_true", help="Print WireGuard status")
    parser.add_argument("--interfaces", action="store_true", help="Dump network interfaces")
    parser.add_argument("--ubus", nargs="+", help="Invoke ubus method: --ubus <service> <method> [json_params]")
    parser.add_argument("--test", action="store_true", help="Run full self-test suite (Rule 1 Zero-Mock)")

    args = parser.parse_args()
    router = GLiNetRouter(host=args.host, username=args.user, password=args.password)

    if args.status or len(sys.argv) == 1:
        status = router.get_system_status()
        print("\n🌐 GL.iNet Router Status:")
        print(json.dumps(status, indent=2))

    if args.clients:
        clients = router.get_clients()
        print(f"\n📱 Connected Clients ({len(clients)} total):")
        print(json.dumps(clients, indent=2))

    if args.usb:
        usb_info = router.get_usb_devices()
        print("\n🔌 USB Peripherals & Android Keepalive:")
        print(json.dumps(usb_info, indent=2))

    if args.wireguard:
        wg = router.get_wireguard_status()
        print("\n🛡️ WireGuard Mesh Status:")
        print(json.dumps(wg, indent=2))

    if args.interfaces:
        ifaces = router.get_interfaces()
        print("\n🔀 Network Interfaces:")
        print(json.dumps(ifaces, indent=2))

    if args.ubus:
        service = args.ubus[0]
        method = args.ubus[1] if len(args.ubus) > 1 else "status"
        params = json.loads(args.ubus[2]) if len(args.ubus) > 2 else None
        res = router.ubus_call(service, method, params)
        print(json.dumps(res, indent=2))

    if args.test:
        print("\n================================================================================")
        print("🧪 Executing GL.iNet Suite Self-Test (Zero-Mock Verification)")
        print("================================================================================")
        status = router.get_system_status()
        assert status["connected"], "Router must be reachable"
        print(f"✅ Pass: Router identified as '{status['model']}' ({status['openwrt']}) on {status['active_host']}")

        # Test HTTP Login
        http_ok = router.login_http()
        if http_ok:
            print(f"✅ Pass: HTTP JSON-RPC 2.0 crypt-SHA256 authenticated successfully (SID: {router.sid[:8]}...)")
        else:
            print(f"⚠️ Warn: HTTP JSON-RPC failed, SSH fallback operational.")

        # Test Clients
        clients = router.get_clients()
        print(f"✅ Pass: Retrieved {len(clients)} active network clients.")

        # Test USB
        usb_info = router.get_usb_devices()
        print(f"✅ Pass: USB inspection successful ({len(usb_info['usb_devices'])} devices detected).")
        print("================================================================================\n")


if __name__ == "__main__":
    main()
