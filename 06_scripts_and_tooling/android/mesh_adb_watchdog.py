#!/usr/bin/env python3
"""
mesh_adb_watchdog.py
Autonomous Multi-Transport ADB Watchdog & Reconnection Daemon for Lauburu Mesh.
Governed by Rule 0 (Canonical Hardware Matrix), Rule 1 (Zero-Mock), and Rule 9 (Multi-IP Fallback).
"""

import subprocess
import time
import socket
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mesh_adb_watchdog")

EDGE_NODES = {
    "Pixel_10_Pro_XL": {
        "transports": [
            "192.168.8.114:5555",   # L2 Local Wi-Fi 7 Clean Room MLO
            "100.73.38.87:5555",    # L3 Tailscale WireGuard Overlay
            "100.94.90.84:5555",    # Alt Tailscale Interface
        ],
        "device_hint": "Pixel"
    },
    "Samsung_S20": {
        "transports": [
            "192.168.8.131:5555",   # L2 Local Wi-Fi
            "100.78.206.96:5555",    # L3 Tailscale WireGuard Overlay
            "100.99.123.58:5555",   # Alt Tailscale Interface
        ],
        "device_hint": "SM-G986"
    },
    "Linux_Tablet": {
        "transports": [
            "192.168.42.129:5555",  # L1 USB-C Tethering ADB (RNDIS/CDC-NCM)
            "192.168.8.185:5555",   # L2 Local Wi-Fi LAN
            "192.168.8.173:5555",   # L2 Alt Local Wi-Fi LAN
            "100.81.92.125:5555",   # L3 Tailscale WireGuard Overlay
            "100.99.210.89:5555",     # Alt Tailscale Interface
        ],
        "usb_serials": [
            "R3CN40CJJ1R",          # Physical USB-C attached Samsung device serial
        ],
        "device_hint": "tablet"
    }
}

def get_connected_adb_devices():
    """Queries `adb devices` to identify attached devices and their statuses."""
    try:
        res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        lines = res.stdout.strip().split("\n")[1:]
        devices = {}
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                devices[parts[0]] = parts[1]
        return devices
    except Exception as e:
        logger.error(f"Error querying adb devices: {e}")
        return {}

def probe_socket(host: str, port: int, timeout: float = 1.0) -> bool:
    """Fast TCP handshake check without hanging ADB client."""
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

LAST_TCPIP_REFRESH = {}

def ensure_tcpip_mode(serial: str, port: int = 5555, throttle_secs: int = 300) -> bool:
    """Ensures device adbd is listening on TCP port 5555 for seamless network fallback."""
    now = time.time()
    if serial in LAST_TCPIP_REFRESH and (now - LAST_TCPIP_REFRESH[serial]) < throttle_secs:
        return True
    try:
        res = subprocess.run(["adb", "-s", serial, "tcpip", str(port)], capture_output=True, text=True, timeout=5)
        if "restarting in TCP mode" in res.stdout or res.returncode == 0:
            logger.info(f"[{serial}] adbd confirmed listening in TCP mode on port {port}")
            LAST_TCPIP_REFRESH[serial] = now
            return True
        else:
            logger.warning(f"[{serial}] adb tcpip response: {res.stdout.strip() or res.stderr.strip()}")
            return False
    except Exception as e:
        logger.error(f"Error ensuring tcpip mode on {serial}: {e}")
        return False

def heal_edge_connections():
    connected = get_connected_adb_devices()
    
    for name, config in EDGE_NODES.items():
        is_healthy = False
        
        # 1. Check USB serial attachment first (Rule 0 / Rule 9)
        for usb_serial in config.get("usb_serials", []):
            status = connected.get(usb_serial)
            if status == "device":
                logger.info(f"[{name}] Verified active USB ADB link ({usb_serial}). Ensuring tcpip 5555...")
                ensure_tcpip_mode(usb_serial)
                is_healthy = True
                break
            elif status == "unauthorized":
                logger.warning(f"[{name}] USB device {usb_serial} attached but UNAUTHORIZED (accept prompt on screen).")
            elif status == "offline":
                logger.warning(f"[{name}] USB device {usb_serial} is OFFLINE.")

        if is_healthy:
            continue

        # 2. Check if already connected via network transport with active 'device' status
        for transport in config["transports"]:
            status = connected.get(transport)
            if status == "device":
                is_healthy = True
                break
            elif status == "offline":
                logger.warning(f"[{name}] Transport {transport} is OFFLINE. Pruning...")
                subprocess.run(["adb", "disconnect", transport], capture_output=True, timeout=5)

        if is_healthy:
            continue

        logger.warning(f"[{name}] No active ADB connection. Probing transport matrix...")
        
        # 3. Probe and attempt reconnect down the transport chain
        for transport in config["transports"]:
            ip, port = transport.split(":")
            if probe_socket(ip, int(port), timeout=1.2):
                logger.info(f"[{name}] Socket open on {transport}. Connecting...")
                subprocess.run(["adb", "disconnect", transport], capture_output=True, timeout=5)
                res = subprocess.run(["adb", "connect", transport], capture_output=True, text=True, timeout=8)
                if "connected to" in res.stdout:
                    logger.info(f"[{name}] Successfully connected via {transport}!")
                    is_healthy = True
                    break
                else:
                    logger.warning(f"[{name}] adb connect {transport} response: {res.stdout.strip()}")
        
        if not is_healthy:
            logger.info(f"[{name}] Network transports exhausted. Device may be offline, in deep doze, or using USB.")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Lauburu Autonomous ADB Edge Node Watchdog Daemon")
    parser.add_argument("--once", action="store_true", help="Run a single probe and heal cycle, then exit")
    parser.add_argument("--interval", type=int, default=30, help="Poll interval in seconds (default: 30)")
    args = parser.parse_args()

    if args.once:
        logger.info("Executing single probe and heal cycle for Lauburu ADB Edge Nodes...")
        heal_edge_connections()
        return

    logger.info("Starting Lauburu Autonomous ADB Edge Node Watchdog Daemon...")
    while True:
        try:
            heal_edge_connections()
        except Exception as e:
            logger.error(f"Unexpected watchdog error: {e}")
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
