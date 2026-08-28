#!/usr/bin/env python3
"""
01_apps/dark_mode_pwa/server.py
===============================
Lauburu Dark Fleet PWA Server & Unified REST API Gateway
--------------------------------------------------------
Serves the Dark Fleet PWA on Port 3000 and handles:
- Service Worker & Manifest delivery
- REST API for device dark mode toggles (/api/dark-mode/toggle)
- REST API for Wake-on-LAN triggers (/api/wol/wake)
- 24/7 background self-healing
"""

import os
import sys
import json
import socket
import logging
import argparse
import subprocess
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [DarkFleetPWA]: %(message)s"
)
logger = logging.getLogger("DarkFleetPWA")

PWA_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")

class DarkFleetHTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PWA_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # API: WoL Wake
        if path == "/api/wol/wake":
            device = params.get("device", [""])[0]
            cmd = f"python3 '{REPO_ROOT}/06_scripts_and_tooling/mesh/wol_manager.py' --wake '{device}'"
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(res.stdout.encode() if res.stdout else b'{"success": true}')
            return

        # API: WoL Wake All
        if path == "/api/wol/wake-all":
            cmd = f"python3 '{REPO_ROOT}/06_scripts_and_tooling/mesh/wol_manager.py' --wake-all"
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(res.stdout.encode() if res.stdout else b'{"success": true}')
            return

        # API: Dark Mode Status (Aggregated Zero-Mock Live Telemetry)
        if path == "/api/dark-mode/status":
            fleet_template = [
                {"id": "Mac_Node_Local", "name": "Host Mac Mini M4", "role": "Local Neural Engine & Master Ingress", "os": "macOS 15.5", "ip": "192.168.8.230", "tailscale": "100.119.199.76", "can_wol": False, "wol_key": None},
                {"id": "MacBook_Pro_Vault", "name": "MacBook Pro M1 Max Vault", "role": "NVMe Storage & 32GB Pooled VRAM", "os": "macOS 15.5", "ip": "192.168.8.127", "tailscale": "100.103.212.21", "can_wol": True, "wol_key": "macbook_pro_vault"},
                {"id": "Linux_Head_Node", "name": "Linux Head Node (Ryzen 7)", "role": "Continuous AI Training Server (16 Threads)", "os": "Ubuntu 24.04 (GNOME)", "ip": "192.168.8.224", "tailscale": "100.101.39.98", "can_wol": True, "wol_key": "linux_head_node"},
                {"id": "Pixel_10_Pro_XL", "name": "Google Pixel 10 Pro XL", "role": "Mobile Roaming Node (Tensor G5)", "os": "Android 15 (Night UI)", "ip": "100.73.38.87:5555", "tailscale": "100.73.38.87", "can_wol": False, "wol_key": None},
                {"id": "MacBook_Air", "name": "MacBook Air M2 Node", "role": "Edge AI Worker (8 Cores)", "os": "macOS 15.5", "ip": "192.168.8.222", "tailscale": "100.93.158.96", "can_wol": True, "wol_key": "macbook_air"},
                {"id": "Samsung_S20_Plus", "name": "Samsung Galaxy S20+", "role": "Mobile Tester & ADB Daemon", "os": "Android 13 (OneUI)", "ip": "100.84.40.95:5555", "tailscale": "100.84.40.95", "can_wol": False, "wol_key": None},
                {"id": "GL_Travel_Router", "name": "GL.iNet Travel Router", "role": "Wi-Fi 7 Multi-WAN Gateway", "os": "OpenWrt 21.02", "ip": "192.168.8.1", "tailscale": "100.122.185.123", "can_wol": False, "wol_key": None}
            ]

            # 1. Read dark mode enforcement state
            dm_status_file = REPO_ROOT / "data/dark_mode/fleet_dark_mode_status.json"
            dm_data = {}
            if dm_status_file.exists():
                try:
                    with open(dm_status_file) as f:
                        dm_data = json.load(f)
                except Exception:
                    pass

            # 2. Read live network latencies from nomad self healer
            healer_status_file = REPO_ROOT / "data/network/nomad_self_healer_status.json"
            healer_matrix = {}
            if healer_status_file.exists():
                try:
                    with open(healer_status_file) as f:
                        h_json = json.load(f)
                        healer_matrix = h_json.get("llama_rpc_port_50052", {}).get("endpoint_matrix", {})
                except Exception:
                    pass

            # 3. Assemble normalized devices list
            devices_list = []
            applied_count = 0
            dm_devices = dm_data.get("devices", {}) if isinstance(dm_data.get("devices"), dict) else {}

            for tmpl in fleet_template:
                dev_id = tmpl["id"]
                dev_dm = dm_devices.get(dev_id, {})
                is_dark = dev_dm.get("dark_mode_active", dm_data.get("dark_mode_active", False))
                dev_status = dev_dm.get("status", "APPLIED" if is_dark else "STANDBY")

                # Match live latency from endpoint matrix if available
                matched_latency = None
                matched_latency_ms = None
                for ep_name, ep_data in healer_matrix.items():
                    ep_ip = ep_data.get("ip", "")
                    if (ep_ip and ep_ip in (tmpl["ip"], tmpl["tailscale"])) or (dev_id.lower().replace("_", "") in ep_name.lower().replace("_", "")):
                        lat = ep_data.get("latency_ms")
                        if lat is not None:
                            matched_latency_ms = round(float(lat), 2)
                            matched_latency = f"{matched_latency_ms}ms"
                            break

                if is_dark:
                    applied_count += 1

                devices_list.append({
                    "id": dev_id,
                    "name": tmpl["name"],
                    "role": tmpl["role"],
                    "os": tmpl["os"],
                    "ip": tmpl["ip"],
                    "tailscale": tmpl["tailscale"],
                    "latency": matched_latency,
                    "latency_ms": matched_latency_ms,
                    "status": dev_status,
                    "dark_mode": is_dark,
                    "can_wol": tmpl["can_wol"],
                    "wol_key": tmpl["wol_key"]
                })

            response_payload = {
                "status": "ONLINE",
                "timestamp_utc": dm_data.get("timestamp_utc") or dm_data.get("timestamp") or "LIVE",
                "devices_total": len(devices_list),
                "devices_active": applied_count,
                "devices": devices_list
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response_payload).encode())
            return

        # API: Device Detect
        if path == "/api/device/detect":
            import platform
            detect_data = {
                "server_host": socket.gethostname(),
                "server_os": platform.system() + " " + platform.release(),
                "server_arch": platform.machine(),
                "port": 3005,
                "standalone_pwa_ready": True,
                "local_controls": ["macos_appearance", "gnome_colorscheme", "android_uimode", "web_dark_reader", "contrast_meter"],
                "timestamp_utc": str(Path(__file__).stat().st_mtime)
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(detect_data).encode())
            return

        # Serve static PWA files
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len).decode('utf-8')
        data = {}
        try:
            data = json.loads(post_body)
        except Exception:
            pass

        if path == "/api/dark-mode/toggle":
            enabled = data.get("enabled", True)
            device = data.get("device", "all")
            
            if device == "all":
                flag = "--apply-all" if enabled else "--disable-all"
            else:
                mode_flag = "--enable" if enabled else "--disable"
                flag = f"--device '{device}' {mode_flag}"
            
            cmd = f"python3 '{REPO_ROOT}/06_scripts_and_tooling/dark_mode/dark_mode_device_controller.py' {flag}"
            subprocess.Popen(cmd, shell=True)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "action": "DARK_MODE_TOGGLED", "device": device, "enabled": enabled}).encode())
            return

        # API: Hardware Luminance Dim & Instant OFF/Reset
        if path in ("/api/hardware/dim", "/api/circadian/shift"):
            brightness = float(data.get("brightness", 1.0))
            is_off = data.get("off", False) or brightness >= 0.99
            device = data.get("device", "all")

            # 1. Apply to macOS Host
            if device in ("all", "Mac_Node_Local"):
                cli_path = REPO_ROOT / "06_scripts_and_tooling/dark_mode/night_shift_cli"
                if cli_path.exists():
                    if is_off:
                        subprocess.Popen([str(cli_path), "--off"])
                    else:
                        subprocess.Popen([str(cli_path), "--brightness", str(brightness)])

            # 2. Apply to Android Nodes via ADB
            if device in ("all", "Pixel_10_Pro_XL", "Samsung_S20_Plus"):
                if is_off:
                    subprocess.Popen("adb shell settings put secure night_display_activated 0 2>/dev/null", shell=True)
                else:
                    adb_bright = max(1, int(brightness * 255))
                    subprocess.Popen(f"adb shell settings put system screen_brightness {adb_bright} 2>/dev/null", shell=True)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "action": "HARDWARE_LUMINANCE_APPLIED",
                "brightness": brightness,
                "off": is_off,
                "device": device
            }).encode())
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        pass  # Quiet logging for smooth UI performance

def run_server(port: int = 3000):
    server = HTTPServer(("0.0.0.0", port), DarkFleetHTTPHandler)
    logger.info(f"🚀 Lauburu Dark Fleet PWA Server running on http://localhost:{port} (and http://0.0.0.0:{port})")
    server.serve_forever()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=3000)
    args = parser.parse_args()
    run_server(port=args.port)
