#!/usr/bin/env python3
"""
Sovereign Cable Speed Tester
============================
Continuously polls the Mac Mini's USB and Thunderbolt buses.
Plug a known high-speed device (SSD or another Mac) into the cable.
This script will instantly reveal the negotiated physical link speed,
allowing you to rapidly bin cables into 480Mbps (Charge Only), 5Gbps, 10Gbps, or 40Gbps (TB).
"""

import subprocess
import time
import sys
import os

def get_usb_devices():
    try:
        out = subprocess.check_output(["system_profiler", "SPUSBDataType"], text=True, stderr=subprocess.DEVNULL)
        devices = []
        current_dev = None
        for line in out.splitlines():
            line = line.strip()
            if line.endswith(":") and "Bus" not in line and "Host Controller" not in line:
                current_dev = {"name": line.replace(":", ""), "speed": "Unknown"}
            elif "Speed:" in line and current_dev:
                current_dev["speed"] = line.split("Speed:")[1].strip()
                devices.append(current_dev)
                current_dev = None
        return devices
    except Exception:
        return []

def get_tb_devices():
    try:
        out = subprocess.check_output(["system_profiler", "SPThunderboltDataType"], text=True, stderr=subprocess.DEVNULL)
        devices = []
        current_dev = None
        for line in out.splitlines():
            line = line.strip()
            if "Device Name:" in line:
                name = line.split("Device Name:")[1].strip()
                if name != "Mac mini":
                    current_dev = {"name": name, "speed": "Unknown"}
            elif "Speed:" in line and current_dev:
                current_dev["speed"] = line.split("Speed:")[1].strip()
                devices.append(current_dev)
                current_dev = None
        return devices
    except Exception:
        return []

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    print("🔌 Starting Sovereign Cable Speed Tester...")
    print("WARNING: You MUST plug a known high-speed device (like an NVMe SSD or Mac) into the cable.")
    print("If you plug in a cheap peripheral, even a 40Gbps cable will show 480 Mbps!")
    time.sleep(3)
    
    last_state = ""
    while True:
        usb = get_usb_devices()
        tb = get_tb_devices()
        
        output = "====================================================\n"
        output += "           ⚡ LIVE CABLE SPEED TESTER ⚡           \n"
        output += "====================================================\n\n"
        
        if not usb and not tb:
            output += "🟡 WAITING: Plug in a device using the mystery cable...\n"
        
        if tb:
            output += "🌩️  THUNDERBOLT BUS:\n"
            for d in tb:
                output += f"   - Device: {d['name']}\n"
                output += f"   - Link Speed: {d['speed']}\n"
                
        if usb:
            output += "\n🔱 USB BUS:\n"
            for d in usb:
                # Filter out internal Mac Mini hubs/devices to reduce noise
                if any(ignore in d['name'] for ignore in ["Apple T2", "Headset", "Bluetooth", "Hub", "Receiver"]):
                    continue
                output += f"   - Device: {d['name']}\n"
                output += f"   - Link Speed: {d['speed']}\n"
                
        output += "\n====================================================\n"
        output += "(Press Ctrl+C to stop testing)\n"
        
        if output != last_state:
            clear_screen()
            print(output)
            last_state = output
            
        time.sleep(1.5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting Cable Tester.")
        sys.exit(0)
