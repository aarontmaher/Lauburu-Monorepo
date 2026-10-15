# -*- coding: utf-8 -*-
"""
GL.iNet Admin Web Server & LuCI JSON-RPC Simulation Engine
==========================================================
Subsystem: 01_apps/glinet_web_optimizer/glinet_admin_web_server.py
Lauburu Mesh Ecosystem — 2026

Simulates the GL.iNet MT3600BE/MT6000 Web UI (LuCI + GL.iNet Admin Panel),
providing authentic REST and ubus JSON-RPC endpoints for dynamic AI self-tuning
and configuration testing in a safe 500 MB sandboxed container.
"""

from __future__ import annotations

import json
import logging
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict

logger = logging.getLogger("GLiNetAdminWebServer")


class RouterStateStore:
    """Thread-safe state store for simulated OpenWrt router parameters."""

    def __init__(self):
        self.state: Dict[str, Any] = {
            "system": {
                "hostname": "GL-MT3600BE",
                "model": "GL.iNet GL-MT3600BE",
                "firmware": "OpenWrt 23.05.4 / GL.iNet 4.6.2",
                "uptime_seconds": 172800,
                "memory_total_kb": 503808,  # 492 MB usable
                "memory_free_kb": 182400,
                "memory_cached_kb": 89200,
                "memory_available_kb": 224600,
                "cpu_load_1m": 0.42,
                "temperature_c": 54.2,
            },
            "network": {
                "wan_mtu": 1500,
                "tailscale_mtu": 1420,
                "queue_discipline": "cake",
                "queue_depth_packets": 1024,
                "bonding_weights": {"wifi7": 0.60, "eth0": 0.35, "usb0": 0.05},
                "wifi_5g_channel": 36,
                "wifi_5g_bandwidth_mhz": 160,
                "wifi_5g_tx_power_dbm": 23,
                "wifi_airtime_congestion_pct": 24.5,
            },
            "cgroups": {
                "ai_memory_max_bytes": 125829120,  # 120 MB
                "ai_cpu_weight": 100,  # nice +15 equivalent
                "ai_cpu_affinity": "2-3",
            },
            "metrics": {
                "packet_forwarding_jitter_ms": 0.022,
                "packet_drop_rate_pct": 0.000,
                "ai_supervisor_rss_mb": 1.50,
            },
            "history": [],
        }

    def get_state(self) -> Dict[str, Any]:
        return self.state

    def update_network(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        for k, v in updates.items():
            if k in self.state["network"]:
                old_v = self.state["network"][k]
                self.state["network"][k] = v
                self.state["history"].append({
                    "timestamp": time.time(),
                    "category": "network",
                    "param": k,
                    "old_value": old_v,
                    "new_value": v,
                })
        return self.state["network"]

    def update_cgroups(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        for k, v in updates.items():
            if k in self.state["cgroups"]:
                old_v = self.state["cgroups"][k]
                self.state["cgroups"][k] = v
                self.state["history"].append({
                    "timestamp": time.time(),
                    "category": "cgroups",
                    "param": k,
                    "old_value": old_v,
                    "new_value": v,
                })
        return self.state["cgroups"]


ROUTER_STORE = RouterStateStore()


class GLiNetWebHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for GL.iNet Admin Web Interface."""

    def _set_headers(self, status: int = 200, content_type: str = "application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        if self.path == "/" or self.path == "/cgi-bin/luci":
            html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <title>GL.iNet Admin Panel — {ROUTER_STORE.state['system']['hostname']}</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-950 text-white p-6 font-mono">
    <div id="glinet_dashboard" class="max-w-4xl mx-auto space-y-6">
        <header class="border-b border-gray-800 pb-4 flex justify-between items-center">
            <div>
                <h1 class="text-2xl font-bold text-cyan-400">GL.iNet Router Gateway</h1>
                <p class="text-xs text-gray-400">Model: {ROUTER_STORE.state['system']['model']} | RAM: 500MB (492MB Usable)</p>
            </div>
            <span id="ai_optimizer_badge" class="px-3 py-1 bg-emerald-500/20 text-emerald-400 text-xs rounded-full border border-emerald-500/40">
                AI Optimizer Active
            </span>
        </header>
        <div class="grid grid-cols-2 gap-4">
            <div class="p-4 bg-gray-900 rounded-lg border border-gray-800 space-y-2">
                <h3 class="text-sm font-semibold text-gray-300">Live Network Telemetry</h3>
                <p class="text-xs">WAN MTU: <span id="wan_mtu" class="text-cyan-400">{ROUTER_STORE.state['network']['wan_mtu']}</span></p>
                <p class="text-xs">QoS Queue: <span id="qos_queue" class="text-cyan-400">{ROUTER_STORE.state['network']['queue_discipline']}</span></p>
                <p class="text-xs">Wi-Fi 5G Channel: <span id="wifi_chan" class="text-cyan-400">{ROUTER_STORE.state['network']['wifi_5g_channel']} ({ROUTER_STORE.state['network']['wifi_5g_bandwidth_mhz']} MHz)</span></p>
                <p class="text-xs">Forwarding Jitter: <span id="jitter" class="text-emerald-400">{ROUTER_STORE.state['metrics']['packet_forwarding_jitter_ms']} ms</span></p>
            </div>
            <div class="p-4 bg-gray-900 rounded-lg border border-gray-800 space-y-2">
                <h3 class="text-sm font-semibold text-gray-300">Memory & Cgroups v2</h3>
                <p class="text-xs">Available RAM: <span class="text-amber-400">{ROUTER_STORE.state['system']['memory_available_kb'] // 1024} MB</span></p>
                <p class="text-xs">AI Cgroup Limit: <span id="cgroup_max" class="text-cyan-400">{ROUTER_STORE.state['cgroups']['ai_memory_max_bytes'] // (1024*1024)} MB</span></p>
                <p class="text-xs">AI Core Affinity: <span class="text-cyan-400">{ROUTER_STORE.state['cgroups']['ai_cpu_affinity']}</span></p>
                <p class="text-xs">Supervisor RSS: <span class="text-emerald-400">{ROUTER_STORE.state['metrics']['ai_supervisor_rss_mb']} MB</span></p>
            </div>
        </div>
    </div>
</body>
</html>"""
            self._set_headers(200, "text/html")
            self.wfile.write(html.encode("utf-8"))
        elif self.path == "/api/router/status":
            self._set_headers(200)
            self.wfile.write(json.dumps(ROUTER_STORE.get_state()).encode("utf-8"))
        elif self.path == "/api/health":
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "ok", "router": "GL-MT3600BE", "ram_usable_mb": 492}).encode("utf-8"))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode("utf-8"))

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._set_headers(400)
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode("utf-8"))
            return

        if self.path == "/ubus" or self.path == "/cgi-bin/luci/rpc/ubus":
            # Authentic ubus JSON-RPC dispatcher
            method = payload.get("method", "call")
            params = payload.get("params", [])
            
            if len(params) >= 3:
                session_id, ubus_object, ubus_method = params[0], params[1], params[2]
                method_args = params[3] if len(params) > 3 else {}
                
                if ubus_object == "network.interface" and ubus_method == "dump":
                    res = {"interfaces": [{"interface": "wan", "up": True, "mtu": ROUTER_STORE.state["network"]["wan_mtu"]}]}
                elif ubus_object == "gl_optimizer" and ubus_method == "tune_network":
                    res = ROUTER_STORE.update_network(method_args)
                elif ubus_object == "gl_optimizer" and ubus_method == "tune_cgroups":
                    res = ROUTER_STORE.update_cgroups(method_args)
                elif ubus_object == "system" and ubus_method == "info":
                    res = ROUTER_STORE.state["system"]
                else:
                    res = {"result": "ok", "applied": method_args}
                
                self._set_headers(200)
                self.wfile.write(json.dumps({"jsonrpc": "2.0", "id": payload.get("id", 1), "result": [0, res]}).encode("utf-8"))
                return
            else:
                self._set_headers(200)
                self.wfile.write(json.dumps({"jsonrpc": "2.0", "id": payload.get("id", 1), "result": [0, ROUTER_STORE.get_state()]}).encode("utf-8"))
                return

        elif self.path == "/api/network/optimize":
            updated = ROUTER_STORE.update_network(payload)
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "success", "network": updated}).encode("utf-8"))
        elif self.path == "/api/cgroups/optimize":
            updated = ROUTER_STORE.update_cgroups(payload)
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "success", "cgroups": updated}).encode("utf-8"))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode("utf-8"))


def run_glinet_server(host: str = "127.0.0.1", port: int = 8090) -> HTTPServer:
    server = HTTPServer((host, port), GLiNetWebHandler)
    logger.info(f"GL.iNet Admin Web Server listening at http://{host}:{port}")
    return server


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
    srv = run_glinet_server(port=port)
    print(f"🚀 GL.iNet Admin Web Server running on http://127.0.0.1:{port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")
