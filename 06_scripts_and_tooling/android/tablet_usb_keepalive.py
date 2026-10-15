#!/usr/bin/env python3
"""
tablet_usb_keepalive.py
Autonomous USB Keepalive, ADB Reverse Forwarding & Tether Monitor Daemon
for Samsung Galaxy Tablet (Node L4 / Linux_Tablet) in the Lauburu 7-Layer Mesh.

Governed by:
- Rule 0 (Canonical Hardware Matrix)
- Rule 1 (Zero-Mock Empirical Truth)
- Rule 9 (Multi-IP Fallback & Bluetooth PAN Exhaustion)
- Rule 20 (AI Manual Execution & App Test Nodes)

Target Device:
- Hardware: Samsung Galaxy Tablet (Vendor ID: 0x04e8 / 1256, Product ID: 0x6860 / 26720)
- Serial: R3CN40CJJ1R
- Physical Port: Mac Mini M4 Pro front USB-C Port 1 (locationID: 0x03110000 / 51445760)
- Subnets: 192.168.42.0/24 (USB Tethering, Host: 192.168.42.1, Tablet: 192.168.42.129)
"""

import sys
import os
import time
import socket
import subprocess
import argparse
import json
import logging
import signal
import re
from typing import Dict, Any, List, Optional

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [tablet_keepalive] %(message)s"
)
logger = logging.getLogger("tablet_keepalive")

# Target Constants
TARGET_SERIAL = "R3CN40CJJ1R"
SAMSUNG_VENDOR_ID = 1256  # 0x04e8
TARGET_LOCATION_ID = 51445760  # 0x03110000 (front Port 1)
TETHER_PEER_IP = "192.168.42.129"
REVERSE_PORTS = [
    (8082, 8082),  # Sovereign Master Qwen 3.8 Max / Prima.cpp PRP
    (4000, 4000),  # Lauburu Hub & Web Services
]

# State tracking
LAST_TCPIP_HEAL: float = 0.0
LAST_REVERSE_CHECK: float = 0.0
RUNNING = True


def signal_handler(signum, frame):
    """Graceful shutdown handler for daemon mode."""
    global RUNNING
    logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
    RUNNING = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def probe_physical_usb() -> Dict[str, Any]:
    """
    Empirically inspects macOS IORegistry (IOUSB plane) for physical attachment
    of the Samsung Galaxy device on the front USB-C port.
    """
    res = {
        "attached": False,
        "product_name": None,
        "vendor_id": None,
        "product_id": None,
        "serial": None,
        "location_id": None,
        "speed": None,
        "interfaces": []
    }
    try:
        proc = subprocess.run(
            ["ioreg", "-p", "IOUSB", "-l", "-w0"],
            capture_output=True,
            text=True,
            timeout=4
        )
        if proc.returncode != 0:
            logger.warning(f"ioreg command returned exit code {proc.returncode}")
            return res

        output = proc.stdout
        lines = output.splitlines()

        # Search for SAMSUNG device entry
        for i, line in enumerate(lines):
            if "SAMSUNG_Android" in line or TARGET_SERIAL in line or '"idVendor" = 1256' in line:
                res["attached"] = True
                
                # Scan surrounding lines for attributes
                chunk_start = max(0, i - 15)
                chunk_end = min(len(lines), i + 25)
                chunk = "\n".join(lines[chunk_start:chunk_end])

                # Extract properties
                vendor_match = re.search(r'"idVendor"\s*=\s*(\d+)', chunk)
                if vendor_match:
                    res["vendor_id"] = int(vendor_match.group(1))

                product_match = re.search(r'"idProduct"\s*=\s*(\d+)', chunk)
                if product_match:
                    res["product_id"] = int(product_match.group(1))

                serial_match = re.search(r'"kUSBSerialNumberString"\s*=\s*"([^"]+)"', chunk)
                if serial_match:
                    res["serial"] = serial_match.group(1)

                loc_match = re.search(r'"locationID"\s*=\s*(\d+)', chunk)
                if loc_match:
                    res["location_id"] = int(loc_match.group(1))

                name_match = re.search(r'"USB Product Name"\s*=\s*"([^"]+)"', chunk)
                if name_match:
                    res["product_name"] = name_match.group(1)

                speed_match = re.search(r'"USBSpeed"\s*=\s*(\d+)', chunk)
                if speed_match:
                    res["speed"] = int(speed_match.group(1))

                # Identify interfaces
                for sub_line in lines[i:chunk_end]:
                    if "class IOUSBHostInterface" in sub_line or "ADB Interface" in sub_line or "CDC" in sub_line or "MTP" in sub_line:
                        res["interfaces"].append(sub_line.strip())

                break

    except subprocess.TimeoutExpired:
        logger.warning("ioreg probe timed out after 4 seconds")
    except Exception as e:
        logger.error(f"Error probing IOUSB registry: {e}")

    return res


def probe_adb_status(target_serial: str = TARGET_SERIAL) -> Dict[str, Any]:
    """
    Queries `adb devices -l` to verify ADB transport connectivity and authorization.
    """
    res = {
        "found": False,
        "status": "disconnected",
        "transport_type": None,
        "details": {}
    }
    try:
        proc = subprocess.run(
            ["adb", "devices", "-l"],
            capture_output=True,
            text=True,
            timeout=4
        )
        if proc.returncode != 0:
            logger.warning(f"adb devices returned code {proc.returncode}")
            return res

        for line in proc.stdout.strip().splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2:
                dev_id, status = parts[0], parts[1]
                if dev_id == target_serial or (target_serial in line):
                    res["found"] = True
                    res["status"] = status
                    res["transport_type"] = "usb"
                    for item in parts[2:]:
                        if ":" in item:
                            k, v = item.split(":", 1)
                            res["details"][k] = v
                    break
                elif dev_id == f"{TETHER_PEER_IP}:5555":
                    res["found"] = True
                    res["status"] = status
                    res["transport_type"] = "tether_ip"
                    for item in parts[2:]:
                        if ":" in item:
                            k, v = item.split(":", 1)
                            res["details"][k] = v
                    break

    except subprocess.TimeoutExpired:
        logger.warning("adb devices probe timed out after 4 seconds")
    except Exception as e:
        logger.error(f"Error querying adb devices: {e}")

    return res


def probe_usb_network_tether() -> Dict[str, Any]:
    """
    Probes macOS network interfaces for active USB Ethernet / RNDIS / CDC-NCM interfaces.
    """
    res = {
        "interface": None,
        "ip": None,
        "active": False,
        "peer_reachable": False,
        "hardware_port": None
    }
    try:
        # Check ifconfig for tethering subnet or active USB interfaces
        proc = subprocess.run(["ifconfig"], capture_output=True, text=True, timeout=4)
        if proc.returncode == 0:
            current_iface = None
            for line in proc.stdout.splitlines():
                iface_match = re.match(r"^([a-z0-9]+):", line)
                if iface_match:
                    current_iface = iface_match.group(1)

                if "inet 192.168.42." in line and current_iface:
                    ip_match = re.search(r"inet (192\.168\.42\.\d+)", line)
                    if ip_match:
                        res["interface"] = current_iface
                        res["ip"] = ip_match.group(1)
                        res["active"] = True
                        break

        # Check networksetup hardware ports if not found
        if not res["active"]:
            hw_proc = subprocess.run(
                ["networksetup", "-listallhardwareports"],
                capture_output=True,
                text=True,
                timeout=4
            )
            if hw_proc.returncode == 0:
                entries = hw_proc.stdout.split("Hardware Port: ")
                for entry in entries:
                    if any(k in entry for k in ["SAMSUNG", "Android", "CDC", "RNDIS", "USB Ethernet"]):
                        dev_match = re.search(r"Device:\s*([a-z0-9]+)", entry)
                        if dev_match:
                            res["interface"] = dev_match.group(1)
                            res["hardware_port"] = entry.splitlines()[0].strip()
                            break

        # Probe ping to tablet peer IP if interface is active
        if res["active"]:
            ping_proc = subprocess.run(
                ["ping", "-c", "1", "-W", "500", TETHER_PEER_IP],
                capture_output=True,
                timeout=2
            )
            res["peer_reachable"] = (ping_proc.returncode == 0)

    except subprocess.TimeoutExpired:
        logger.warning("network tether probe timed out")
    except Exception as e:
        logger.error(f"Error querying network interfaces: {e}")

    return res


def setup_adb_reverse_tunnels(serial: str) -> Dict[str, Any]:
    """
    Sets up reverse port forwards from tablet to Mac Mini host services
    (Port 8082 for Prima.cpp Qwen 3.8 Max, Port 4000 for Lauburu Hub).
    """
    results = {}
    try:
        # Check existing reverses
        list_proc = subprocess.run(
            ["adb", "-s", serial, "reverse", "--list"],
            capture_output=True,
            text=True,
            timeout=4
        )
        existing = list_proc.stdout if list_proc.returncode == 0 else ""

        for local_port, remote_port in REVERSE_PORTS:
            target_str = f"tcp:{remote_port} tcp:{local_port}"
            if target_str in existing:
                results[f"{remote_port}->{local_port}"] = "already_active"
                continue

            rev_proc = subprocess.run(
                ["adb", "-s", serial, "reverse", f"tcp:{remote_port}", f"tcp:{local_port}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if rev_proc.returncode == 0:
                logger.info(f"[{serial}] Established ADB reverse tunnel: tcp:{remote_port} -> tcp:{local_port}")
                results[f"{remote_port}->{local_port}"] = "established"
            else:
                logger.warning(f"[{serial}] Failed to set up reverse tunnel tcp:{remote_port}: {rev_proc.stderr.strip()}")
                results[f"{remote_port}->{local_port}"] = f"failed: {rev_proc.stderr.strip()}"

    except Exception as e:
        logger.error(f"Error establishing ADB reverse tunnels on {serial}: {e}")
        results["error"] = str(e)

    return results


def ensure_tcpip_listening(serial: str, throttle_seconds: int = 300) -> bool:
    """
    Ensures the device's adbd listens on TCP port 5555 so network ADB
    can connect when USB is unplugged or for wireless mesh fallback.
    """
    global LAST_TCPIP_HEAL
    now = time.time()
    if (now - LAST_TCPIP_HEAL) < throttle_seconds:
        return True

    try:
        proc = subprocess.run(
            ["adb", "-s", serial, "tcpip", "5555"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if proc.returncode == 0 or "restarting in TCP mode" in proc.stdout:
            logger.info(f"[{serial}] Confirmed adbd listening on TCP port 5555")
            LAST_TCPIP_HEAL = now
            return True
        else:
            logger.warning(f"[{serial}] adb tcpip 5555 returned: {proc.stdout.strip() or proc.stderr.strip()}")
            return False
    except Exception as e:
        logger.error(f"Error invoking adb tcpip on {serial}: {e}")
        return False


def evaluate_health_cycle() -> Dict[str, Any]:
    """
    Executes a single end-to-end evaluation and self-healing cycle for Node L4.
    """
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_serial": TARGET_SERIAL,
        "physical_usb": probe_physical_usb(),
        "adb_status": probe_adb_status(TARGET_SERIAL),
        "network_tether": probe_usb_network_tether(),
        "reverses": {},
        "tcpip_5555_active": False,
        "overall_state": "DISCONNECTED",
        "action_log": []
    }

    is_usb_attached = report["physical_usb"]["attached"]
    adb_status = report["adb_status"]["status"]
    tether_active = report["network_tether"]["active"]

    if adb_status == "device":
        serial_to_use = report["adb_status"]["details"].get("serial", TARGET_SERIAL)
        report["action_log"].append(f"Detected ADB active on {serial_to_use}")
        
        # Configure reverse tunnels
        report["reverses"] = setup_adb_reverse_tunnels(serial_to_use)
        report["action_log"].append("Configured reverse tunnels (8082, 4000)")
        
        # Ensure TCP/IP mode is maintained
        if ensure_tcpip_listening(serial_to_use):
            report["tcpip_5555_active"] = True
            report["action_log"].append("Verified adbd listening on TCP 5555")

        if tether_active:
            report["overall_state"] = "ONLINE_USB_ADB_AND_TETHER"
        else:
            report["overall_state"] = "ONLINE_USB_ADB"

    elif adb_status == "unauthorized":
        report["overall_state"] = "UNAUTHORIZED"
        report["action_log"].append("Device attached via USB but unauthorized. Accept RSA prompt on tablet.")
        logger.warning(f"[{TARGET_SERIAL}] Device attached via USB but unauthorized. User must tap 'Allow' on tablet screen.")

    elif is_usb_attached:
        if tether_active:
            report["overall_state"] = "ONLINE_TETHER_ONLY"
            report["action_log"].append("USB tether interface active, but ADB not enabled.")
        else:
            report["overall_state"] = "ONLINE_USB_RAW_ONLY"
            report["action_log"].append("Physical USB connected, but ADB and Tethering are disabled in tablet OS.")
            logger.info(f"[{TARGET_SERIAL}] Samsung tablet detected on USB (0x03110000), but ADB and RNDIS are unconfigured.")

    else:
        report["overall_state"] = "DISCONNECTED"
        report["action_log"].append("Physical USB not detected at front port 0x03110000.")
        logger.info(f"[{TARGET_SERIAL}] Tablet not detected on USB. Check cable or run resurrection sequence.")

    return report


def print_human_report(report: Dict[str, Any]):
    """Prints a clear, structured status summary."""
    print("=" * 65)
    print(f"Lauburu Node L4 (Linux_Tablet) USB Keepalive Report — {report['timestamp']}")
    print("=" * 65)
    print(f"Target Serial:      {report['target_serial']}")
    print(f"Overall State:      {report['overall_state']}")
    
    usb = report["physical_usb"]
    print(f"Physical USB:       {'ATTACHED' if usb['attached'] else 'DISCONNECTED'}")
    if usb["attached"]:
        print(f"  - Product Name:   {usb['product_name'] or 'SAMSUNG_Android'}")
        print(f"  - Vendor / Prod:  {usb['vendor_id']} / {usb['product_id']}")
        print(f"  - Location ID:    {usb['location_id']} (Front Port 1)")
    
    adb = report["adb_status"]
    print(f"ADB Transport:      {adb['status'].upper()}")
    if adb["found"]:
        print(f"  - Type:           {adb['transport_type']}")
        print(f"  - Details:        {adb['details']}")
    
    tether = report["network_tether"]
    print(f"USB Tethering:      {'ACTIVE' if tether['active'] else 'INACTIVE'}")
    if tether["active"]:
        print(f"  - Interface:      {tether['interface']}")
        print(f"  - IP Address:     {tether['ip']}")
        print(f"  - Peer Reachable: {tether['peer_reachable']}")

    if report["reverses"]:
        print(f"Reverse Tunnels:    {report['reverses']}")
    print(f"TCP/IP 5555:        {'ACTIVE' if report['tcpip_5555_active'] else 'INACTIVE'}")
    
    if report["action_log"]:
        print("-" * 65)
        print("Actions & Diagnostics:")
        for action in report["action_log"]:
            print(f"  • {action}")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous USB Keepalive Daemon for Node L4 (Linux_Tablet)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Execute a single diagnostic and keepalive cycle, then exit"
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run continuously as a persistent background keepalive daemon"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=15,
        help="Polling interval in seconds for daemon mode (default: 15)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose debug logging"
    )
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if args.once or not args.daemon:
        # Run single evaluation cycle
        report = evaluate_health_cycle()
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print_human_report(report)
        sys.exit(0)

    # Daemon mode
    logger.info(f"Starting Node L4 USB Keepalive Daemon (polling every {args.interval}s)...")
    while RUNNING:
        try:
            report = evaluate_health_cycle()
            if args.verbose:
                logger.debug(f"Cycle result: {report['overall_state']}")
        except Exception as e:
            logger.error(f"Unexpected error during keepalive cycle: {e}")
        
        # Sleep in short increments for responsive signal handling
        for _ in range(args.interval):
            if not RUNNING:
                break
            time.sleep(1)

    logger.info("Node L4 USB Keepalive Daemon stopped.")


if __name__ == "__main__":
    main()
