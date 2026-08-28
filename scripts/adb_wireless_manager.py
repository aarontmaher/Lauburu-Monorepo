#!/usr/bin/env python3
"""
adb_wireless_manager.py
WiFi ADB (Wireless ADB) support for LAUBURU
Enables ADB over WiFi without USB cable
Works with Android 11+ native wireless debugging
"""

import subprocess
import json
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import socket
import time
import concurrent.futures

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ADB executable path
ADB_BIN = "/opt/homebrew/bin/adb"


class WiFiADBManager:
    """Manages wireless ADB connections over WiFi."""

    # Default ADB ports
    ADB_PORT = 5555
    ADB_PAIR_PORT = 5037

    @staticmethod
    def get_local_ip() -> str:
        """Get local machine IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception as e:
            logger.error(f"Failed to get local IP: {e}")
            return "127.0.0.1"

    @staticmethod
    def run_adb_command(args: List[str], timeout: int = 10) -> Dict[str, Any]:
        """Execute ADB command."""
        try:
            cmd = [ADB_BIN] + args
            logger.info(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return {
                "command": " ".join(args),
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "timestamp": datetime.utcnow().isoformat()
            }
        except subprocess.TimeoutExpired:
            return {
                "command": " ".join(args),
                "success": False,
                "error": "Command timeout",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "command": " ".join(args),
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    @staticmethod
    def pair_device(device_ip: str, pairing_code: str, port: int = 5555) -> Dict[str, Any]:
        """
        Pair with wireless device using pairing code.
        
        Steps:
        1. On Android device: Enable "Wireless debugging"
        2. Tap "Pair with pairing code"
        3. Get pairing code (6 digits) and device IP:port
        4. Call this function with the credentials
        """
        pair_port = port
        
        result = WiFiADBManager.run_adb_command(
            ["pair", f"{device_ip}:{pair_port}", pairing_code],
            timeout=15
        )
        
        return {
            "operation": "pair_device",
            "device_ip": device_ip,
            "pair_port": pair_port,
            "pairing_code": "***hidden***",
            "status": "paired" if result["success"] else "failed",
            "command_result": result
        }

    @staticmethod
    def connect_device(device_ip: str, port: int = 5555) -> Dict[str, Any]:
        """Connect to wireless device."""
        connection_string = f"{device_ip}:{port}"
        
        result = WiFiADBManager.run_adb_command(["connect", connection_string])
        
        return {
            "operation": "connect",
            "device": connection_string,
            "status": "connected" if result["success"] else "failed",
            "message": result["stdout"],
            "command_result": result
        }

    @staticmethod
    def disconnect_device(device_ip: str, port: int = 5555) -> Dict[str, Any]:
        """Disconnect from wireless device."""
        connection_string = f"{device_ip}:{port}"
        
        result = WiFiADBManager.run_adb_command(["disconnect", connection_string])
        
        return {
            "operation": "disconnect",
            "device": connection_string,
            "status": "disconnected" if result["success"] else "failed",
            "command_result": result
        }

    @staticmethod
    def scan_network_for_devices(network_prefix: str = "192.168.1", start: int = 1, end: int = 254) -> Dict[str, Any]:
        """
        Scan network for devices with ADB enabled using concurrent socket checks.
        """
        devices_found = []
        
        logger.info(f"Scanning network {network_prefix}.* for ADB devices on port {WiFiADBManager.ADB_PORT}...")
        
        def check_host(ip: str) -> Optional[Dict[str, Any]]:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.15)
                res = sock.connect_ex((ip, WiFiADBManager.ADB_PORT))
                sock.close()
                if res == 0:
                    logger.info(f"  ✓ Found ADB on {ip}:{WiFiADBManager.ADB_PORT}")
                    return {
                        "ip": ip,
                        "port": WiFiADBManager.ADB_PORT,
                        "discovered": datetime.utcnow().isoformat()
                    }
            except Exception:
                pass
            return None

        ips = [f"{network_prefix}.{i}" for i in range(start, end + 1)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            results = list(executor.map(check_host, ips))

        for r in results:
            if r is not None:
                devices_found.append(r)
        
        return {
            "operation": "network_scan",
            "network": f"{network_prefix}.*",
            "port": WiFiADBManager.ADB_PORT,
            "devices_found": len(devices_found),
            "devices": devices_found
        }

    @staticmethod
    def get_wireless_devices() -> Dict[str, Any]:
        """Get list of connected wireless devices."""
        result = WiFiADBManager.run_adb_command(["devices", "-l"])
        
        devices = []
        if result["success"] and result["stdout"]:
            lines = result["stdout"].split("\n")[1:]
            for line in lines:
                if line.strip() and "device" in line and ":" in line:  # Wireless devices have IP:port
                    parts = line.split()
                    if len(parts) >= 2:
                        device_id = parts[0]
                        status = parts[1]
                        
                        # Parse IP:port
                        try:
                            ip, port = device_id.rsplit(":", 1)
                            devices.append({
                                "id": device_id,
                                "ip": ip,
                                "port": int(port),
                                "status": status,
                                "type": "wireless"
                            })
                        except ValueError:
                            pass
        
        return {
            "wireless_devices": devices,
            "count": len(devices),
            "command_result": result
        }

    @staticmethod
    def get_device_ip_via_usb(usb_device_id: str) -> Optional[str]:
        """
        Get device IP address via USB connection.
        Then can connect wirelessly.
        """
        # Enable tcpip on USB device
        result = WiFiADBManager.run_adb_command(
            ["-s", usb_device_id, "tcpip", "5555"]
        )
        
        if not result["success"]:
            logger.error(f"Failed to enable tcpip: {result}")
            return None
        
        # Get device IP via getprop
        result = WiFiADBManager.run_adb_command(
            ["-s", usb_device_id, "shell", "getprop", "dhcp.wlan0.ipaddress"]
        )
        
        if result["success"] and result["stdout"]:
            device_ip = result["stdout"].strip()
            logger.info(f"Device IP: {device_ip}")
            return device_ip
        
        return None

    @staticmethod
    def enable_wireless_debugging_from_usb(usb_device_id: str) -> Dict[str, Any]:
        """
        Enable wireless debugging on device connected via USB.
        Returns pairing code and port for wireless connection.
        """
        logger.info(f"Enabling wireless debugging on {usb_device_id}...")
        
        # Enable tcpip
        result1 = WiFiADBManager.run_adb_command(
            ["-s", usb_device_id, "tcpip", "5555"]
        )
        
        if not result1["success"]:
            return {"error": "Failed to enable tcpip", "result": result1}
        
        # Get device IP
        result2 = WiFiADBManager.run_adb_command(
            ["-s", usb_device_id, "shell", "getprop", "dhcp.wlan0.ipaddress"]
        )
        
        device_ip = result2["stdout"].strip() if result2["success"] else None
        
        return {
            "operation": "enable_wireless_debugging",
            "device": usb_device_id,
            "status": "enabled",
            "device_ip": device_ip,
            "port": 5555,
            "next_steps": [
                "On your device: Settings > About phone > Build number (tap 7x)",
                "Settings > System > Developer options > Wireless debugging",
                "Tap 'Pair with pairing code'",
                "Use the pairing code and this IP:port to pair"
            ],
            "command_results": [result1, result2]
        }

    @staticmethod
    def generate_wireless_device_inventory() -> Dict[str, Any]:
        """Generate inventory of wireless ADB devices."""
        inventory = {
            "timestamp": datetime.utcnow().isoformat(),
            "wireless_devices": [],
            "network_scan": {},
            "local_ip": WiFiADBManager.get_local_ip()
        }
        
        # Get connected wireless devices
        wireless = WiFiADBManager.get_wireless_devices()
        inventory["wireless_devices"] = wireless.get("wireless_devices", [])
        inventory["wireless_count"] = wireless.get("count", 0)
        
        # Scan network for potential devices
        local_ip = WiFiADBManager.get_local_ip()
        network_prefix = ".".join(local_ip.split(".")[:3])
        
        logger.info(f"Scanning network {network_prefix}.* for ADB devices...")
        scan_result = WiFiADBManager.scan_network_for_devices(network_prefix)
        inventory["network_scan"] = scan_result
        
        return inventory


def main():
    """Test wireless ADB manager."""
    print("\n" + "="*70)
    print("  WIRELESS ADB MANAGER")
    print("="*70)
    
    # Get local IP
    print("\n[1] Local machine IP:")
    local_ip = WiFiADBManager.get_local_ip()
    print(f"  IP: {local_ip}")
    
    # Get connected wireless devices
    print("\n[2] Connected wireless devices:")
    wireless = WiFiADBManager.get_wireless_devices()
    print(f"  Count: {wireless['count']}")
    for device in wireless["wireless_devices"]:
        print(f"  - {device['id']} ({device['ip']}:{device['port']}) - {device['status']}")
    
    # Scan network
    print("\n[3] Scanning network for ADB devices...")
    network_prefix = ".".join(local_ip.split(".")[:3])
    scan_result = WiFiADBManager.scan_network_for_devices(network_prefix)
    print(f"  Found: {scan_result['devices_found']} devices")
    for device in scan_result["devices"]:
        print(f"  - {device['ip']}:{device['port']}")
    
    # Generate inventory
    print("\n[4] Generating wireless device inventory...")
    inventory = WiFiADBManager.generate_wireless_device_inventory()
    print(json.dumps({
        "timestamp": inventory["timestamp"],
        "local_ip": inventory["local_ip"],
        "wireless_count": inventory["wireless_count"],
        "wireless_devices": inventory["wireless_devices"],
        "network_scan_found": inventory["network_scan"]["devices_found"]
    }, indent=2))
    
    # Usage instructions
    print("\n" + "="*70)
    print("  WIRELESS ADB SETUP INSTRUCTIONS")
    print("="*70)
    print("""
1. Connect Android device via USB cable
2. Run: adb tcpip 5555
3. Get device IP: adb shell getprop dhcp.wlan0.ipaddress
4. Disconnect USB
5. Run: adb connect <device_ip>:5555
6. Now use wireless ADB!

For Android 11+:
1. Settings > Developer Options > Wireless debugging
2. Tap "Pair with pairing code"
3. Use pairing code and IP:port
    """)


if __name__ == "__main__":
    main()
