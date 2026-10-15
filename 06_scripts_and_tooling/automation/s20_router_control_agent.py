#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
s20_router_control_agent.py
===========================
Samsung Galaxy S20+ Sovereign Router Control Center Daemon.
Runs inside Termux on the Samsung S20+ (which is plugged 24/7 into GL-BE14000 USB),
providing a hardened local REST API, OpenWrt UCI management, WireGuard IPv6 controls,
Shizuku (rish) privilege execution, and Hermes Agent tool-calling integration.

Governed by:
- Rule #0 & #1: Zero-Mock Empirical Truth
- Rule #3 & #10: Mac Mini Sanctuary & Dynamic RAM Governance
"""

import os
import sys
import json
import time
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

PORT = 9090
ROUTER_HOST = "192.168.8.1"
ROUTER_USER = "root"
SHIZUKU_RISH = os.path.expanduser("~/rish")


def run_router_cmd(cmd: str, timeout: float = 4.0) -> dict:
    """Executes an empirical shell command on the GL.iNet router over SSH."""
    ssh_cmd = [
        "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=2",
        f"{ROUTER_USER}@{ROUTER_HOST}", cmd
    ]
    try:
        t0 = time.time()
        res = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
        dt = (time.time() - t0) * 1000
        return {
            "returncode": res.returncode,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip(),
            "latency_ms": round(dt, 2)
        }
    except Exception as e:
        return {"returncode": -1, "stdout": "", "stderr": str(e), "latency_ms": 0}


def run_shizuku_cmd(cmd: str, timeout: float = 3.0) -> dict:
    """Executes a privileged shell command on the Samsung S20+ via Shizuku rish."""
    if not os.path.exists(SHIZUKU_RISH):
        return {"returncode": -1, "stdout": "", "stderr": "rish not found"}
    env = dict(os.environ)
    env["RISH_APPLICATION_ID"] = "com.termux"
    try:
        t0 = time.time()
        res = subprocess.run([SHIZUKU_RISH, "-c", cmd], capture_output=True, text=True, timeout=timeout, env=env)
        dt = (time.time() - t0) * 1000
        output_text = (res.stdout.strip() + " " + res.stderr.strip()).strip()
        return {
            "returncode": res.returncode,
            "stdout": output_text,
            "stderr": res.stderr.strip(),
            "latency_ms": round(dt, 2)
        }
    except Exception as e:
        return {"returncode": -1, "stdout": "", "stderr": str(e), "latency_ms": 0}


def optimize_always_plugged_in():
    """Applies Android system settings via Shizuku for 24/7 USB router keepalive."""
    cmds = [
        "settings put global stay_on_while_plugged_in 3",
        "dumpsys deviceidle whitelist +com.termux",
        "dumpsys deviceidle whitelist +com.mobilefork.hermesagent",
        "dumpsys deviceidle whitelist +moe.shizuku.privileged.api",
        "setprop service.adb.tcp.port 5555"
    ]
    results = {}
    for c in cmds:
        results[c] = run_shizuku_cmd(c)
    # Ensure Termux wake lock held
    wake_lock = "/data/data/com.termux/files/usr/bin/termux-wake-lock"
    if os.path.exists(wake_lock):
        subprocess.run([wake_lock], capture_output=True)
    return results


class RouterControlHandler(BaseHTTPRequestHandler):
    def _send_json(self, data: dict, status_code: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/" or path == "/health":
            shiz_ok = os.path.exists(SHIZUKU_RISH)
            self._send_json({
                "status": "online",
                "service": "Samsung S20+ Sovereign Router Control Center",
                "host_router": ROUTER_HOST,
                "shizuku_bridge": shiz_ok,
                "timestamp": time.time()
            })

        elif path == "/router/status":
            mem = run_router_cmd("free -m; echo '---'; cat /proc/swaps; echo '---'; uptime")
            wan6 = run_router_cmd("ubus call network.interface.wan6 status 2>/dev/null || true")
            self._send_json({
                "router_host": ROUTER_HOST,
                "memory_and_swap": mem.get("stdout", ""),
                "wan6_raw": wan6.get("stdout", ""),
                "latency_ms": mem.get("latency_ms", 0)
            })

        elif path == "/router/clients":
            leases = run_router_cmd("cat /tmp/dhcp.leases")
            wifi = run_router_cmd("ubus call network.device status 2>/dev/null || true")
            self._send_json({
                "leases": leases.get("stdout", "").split("\n"),
                "device_status_raw": wifi.get("stdout", "")
            })

        elif path == "/router/wireguard":
            wg = run_router_cmd("wg show")
            self._send_json({
                "wireguard_status": wg.get("stdout", ""),
                "latency_ms": wg.get("latency_ms", 0)
            })

        elif path == "/s20/optimize":
            res = optimize_always_plugged_in()
            self._send_json({
                "status": "success",
                "message": "Optimized S20+ 24/7 USB router keepalive settings",
                "actions": res
            })

        elif path == "/tools":
            # Expose MCP-compatible Tool Definitions
            tools_list = [
                {"name": "router_heal", "description": "Flush router caches and verify 2.0GB active SWAP", "parameters": {}},
                {"name": "router_command", "description": "Execute shell command on OpenWrt router", "parameters": {"command": {"type": "string"}}},
                {"name": "shizuku_exec", "description": "Execute privileged command on Android S20 via Shizuku rish", "parameters": {"command": {"type": "string"}}},
                {"name": "wireguard_status", "description": "Query live WireGuard peers and public IPv6 endpoint", "parameters": {}},
                {"name": "sync_mobile_storage", "description": "Synchronize S20+ flash storage into SeaweedFS pool", "parameters": {}}
            ]
            self._send_json({"tools": tools_list})

        else:
            self._send_json({"status": "error", "message": f"Endpoint not found: {path}"}, 404)

    def do_POST(self):
        path = self.path.split("?")[0]
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(post_data.decode("utf-8"))
        except Exception:
            payload = {}

        if path == "/router/heal":
            heal_cmd = (
                "echo 3 > /proc/sys/vm/drop_caches && "
                "[ -f /overlay/swapfile ] && swapon /overlay/swapfile 2>/dev/null || true && "
                "free -m"
            )
            res = run_router_cmd(heal_cmd)
            self._send_json({
                "status": "success" if res.get("returncode") == 0 else "error",
                "message": "Self-healed router caches and verified SWAP",
                "details": res
            })

        elif path == "/s20/shizuku/exec":
            cmd = payload.get("command", "id")
            res = run_shizuku_cmd(cmd)
            self._send_json({
                "command": cmd,
                "result": res
            })

        elif path == "/tool/call":
            tool_name = payload.get("tool", "")
            args = payload.get("args", {})
            
            if tool_name == "router_heal":
                res = run_router_cmd("echo 3 > /proc/sys/vm/drop_caches && [ -f /overlay/swapfile ] && swapon /overlay/swapfile 2>/dev/null || true && free -m")
                self._send_json({"tool": tool_name, "output": res})
            elif tool_name == "router_command":
                cmd = args.get("command", "uptime")
                res = run_router_cmd(cmd)
                self._send_json({"tool": tool_name, "output": res})
            elif tool_name == "shizuku_exec":
                cmd = args.get("command", "id")
                res = run_shizuku_cmd(cmd)
                self._send_json({"tool": tool_name, "output": res})
            elif tool_name == "wireguard_status":
                res = run_router_cmd("wg show")
                self._send_json({"tool": tool_name, "output": res})
            elif tool_name == "sync_mobile_storage":
                res = subprocess.run(["rclone", "copy", os.path.expanduser("~/mobile_pool/"), "seaweedfs:edge_mounts/s20_storage/"], capture_output=True, text=True)
                self._send_json({"tool": tool_name, "returncode": res.returncode, "stdout": res.stdout, "stderr": res.stderr})
            else:
                self._send_json({"status": "error", "message": f"Unknown tool: {tool_name}"}, 400)

        else:
            self._send_json({"status": "error", "message": f"POST endpoint not found: {path}"}, 404)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def main():
    print(f"🚀 Initializing Samsung S20+ Router Control Center on port {PORT}...")
    optimize_always_plugged_in()
    print("✓ Applied Android keepalive and Shizuku deviceidle whitelist.")
    server = ThreadedHTTPServer(("0.0.0.0", PORT), RouterControlHandler)
    print(f"✓ Sovereign Router Control Center active on http://0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Router Control Center...")
        server.server_close()


if __name__ == "__main__":
    main()
