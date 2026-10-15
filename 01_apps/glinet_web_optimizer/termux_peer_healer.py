# -*- coding: utf-8 -*-
"""
Termux Standalone Peer Self-Healing Client & Daemon
===================================================
Subsystem: 01_apps/glinet_web_optimizer/termux_peer_healer.py
Lauburu Mesh Ecosystem — 2026

Runs natively inside Termux on Android (L6 Pixel 10 Pro XL / L7 Samsung S20+).
Zero external dependencies (pure Python 3 standard library).
"""

import json
import os
import sys
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

MAC_HOST_TAILSCALE_IP = "100.119.199.76"
MAC_HOST_LAN_IP = "192.168.8.230"
ROUTER_IP = "192.168.8.1"
ROUTER_TAILSCALE_IP = "100.122.185.123"

def find_active_mac_host() -> str:
    for ip in [MAC_HOST_TAILSCALE_IP, MAC_HOST_LAN_IP]:
        try:
            req = urllib.request.Request(f"http://{ip}:8082/health", headers={"User-Agent": "Termux-Peer"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    return ip
        except Exception:
            pass
    return MAC_HOST_TAILSCALE_IP

class TermuxHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/health", "/"):
            active_host = find_active_mac_host()
            data = {
                "node": "Android Termux Peer (L6/L7)",
                "status": "ONLINE",
                "mac_host_connected": active_host,
                "timestamp": time.time()
            }
            body = json.dumps(data, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8082
    print(f"📱 Termux Peer Self-Healing Daemon starting on port {port}...")
    server = HTTPServer(("", port), TermuxHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping Termux peer.")
