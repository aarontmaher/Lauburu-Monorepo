#!/usr/bin/env python3
"""
06_scripts_and_tooling/device_watchdog/launch_scrcpy_mesh.py
============================================================
Autonomous Resilient Multi-Device scrcpy 60 FPS Screen Mirroring Daemon.
Orchestrates Google Pixel 10 Pro XL and Samsung Galaxy S20+ with:
- Multi-window macOS geometry layout (Side-by-side positioning: S20 at x=60, y=80; Pixel at x=520, y=80)
- High-performance 60 FPS @ 16M video bitrate
- Autonomous socket watchdog & GL.iNet router USB recovery bounce
- Automatic display wake-up and auto-relaunch upon disconnection
"""

import os
import sys
import time
import signal
import logging
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [scrcpy-mesh]: %(message)s"
)
logger = logging.getLogger("ScrcpyMesh")

ADB_BIN = "/Users/aaron/.local/bin/adb" if os.path.exists("/Users/aaron/.local/bin/adb") else "adb"
SCRCPY_BIN = "/Users/aaron/.local/bin/scrcpy" if os.path.exists("/Users/aaron/.local/bin/scrcpy") else "scrcpy"
ROUTER_SSH = "root@192.168.8.1"

DEVICE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "s20": {
        "name": "Samsung Galaxy S20+ (Layer 7 UI Tester)",
        "ip": "100.84.40.95",
        "port": 5555,
        "alt_ip": "192.168.8.11",
        "router_usb_serial": "R3CN40CJJ1R",
        "window_x": 60,
        "window_y": 80,
        "window_width": 420,
        "bitrate": "16M",
        "max_fps": 60,
        "title": "Lauburu Mesh: Samsung S20+ (Layer 7 UI Tester)"
    },
    "pixel": {
        "name": "Google Pixel 10 Pro XL (Layer 6 Edge AI)",
        "ip": "100.73.38.87",
        "port": 5555,
        "alt_ip": "192.168.8.14",
        "router_usb_serial": "",
        "window_x": 520,
        "window_y": 80,
        "window_width": 420,
        "bitrate": "16M",
        "max_fps": 60,
        "title": "Lauburu Mesh: Pixel 10 Pro XL (Layer 6 Edge AI)"
    }
}

running = True

def handle_signal(sig, frame):
    global running
    logger.info("Received termination signal. Shutting down all scrcpy instances...")
    running = False

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

class DeviceMirrorManager:
    def __init__(self, key: str, cfg: Dict[str, Any], custom_bitrate: Optional[str] = None, custom_fps: Optional[int] = None):
        self.key = key
        self.cfg = cfg
        self.target = f"{cfg['ip']}:{cfg['port']}"
        self.bitrate = custom_bitrate or cfg["bitrate"]
        self.max_fps = custom_fps or cfg["max_fps"]
        self.process: Optional[subprocess.Popen] = None
        self.last_connect_attempt = 0.0

    def is_connected(self) -> bool:
        try:
            res = subprocess.run([ADB_BIN, "devices"], capture_output=True, text=True, timeout=2.5)
            for line in res.stdout.splitlines():
                if self.target in line and "device" in line and "offline" not in line:
                    return True
        except Exception:
            pass
        return False

    def recover_socket(self) -> bool:
        logger.info(f"[{self.key}] Attempting ADB connection to {self.target}...")
        
        # 1. Direct connect
        try:
            subprocess.run([ADB_BIN, "connect", self.target], capture_output=True, timeout=3.0)
            if self.is_connected():
                logger.info(f"[{self.key}] ✓ Connected to {self.target} directly.")
                return True
        except Exception as e:
            logger.warning(f"[{self.key}] Direct connect note: {e}")

        # 2. Router USB TCP/IP bounce if USB serial is available
        if self.cfg.get("router_usb_serial"):
            serial = self.cfg["router_usb_serial"]
            logger.info(f"[{self.key}] Executing router USB ADB TCP/IP bounce on {serial}...")
            try:
                res = subprocess.run(
                    ["ssh", "-o", "ConnectTimeout=2", "-o", "StrictHostKeyChecking=no",
                     ROUTER_SSH, f"adb -s {serial} tcpip 5555"],
                    capture_output=True, text=True, timeout=4.0
                )
                logger.info(f"[{self.key}] Router response: {res.stdout.strip()}")
                time.sleep(1.0)
                subprocess.run([ADB_BIN, "connect", self.target], capture_output=True, timeout=3.0)
                if self.is_connected():
                    logger.info(f"[{self.key}] ✓ Connected to {self.target} via Router USB bounce.")
                    return True
            except Exception as e:
                logger.warning(f"[{self.key}] Router USB bounce note: {e}")

        # 3. Try alternative IP if specified
        if self.cfg.get("alt_ip"):
            alt_target = f"{self.cfg['alt_ip']}:{self.cfg['port']}"
            logger.info(f"[{self.key}] Trying alternative IP {alt_target}...")
            try:
                subprocess.run([ADB_BIN, "connect", alt_target], capture_output=True, timeout=2.0)
                if self.is_connected():
                    return True
            except Exception as e:
                logger.warning(f"[{self.key}] Alt IP note: {e}")

        return False

    def wake_screen(self):
        try:
            logger.info(f"[{self.key}] Sending display wake-up keyevents to {self.target}...")
            subprocess.run([ADB_BIN, "-s", self.target, "shell", "input keyevent KEYCODE_WAKEUP && input keyevent 82"],
                           capture_output=True, timeout=2.5)
        except Exception as e:
            logger.warning(f"[{self.key}] Wake screen note: {e}")

    def build_scrcpy_command(self, extra_args: Optional[List[str]] = None) -> List[str]:
        cmd = [
            SCRCPY_BIN,
            f"--serial={self.target}",
            f"--max-fps={self.max_fps}",
            f"--video-bit-rate={self.bitrate}",
            f"--window-title={self.cfg['title']}",
            f"--window-x={self.cfg['window_x']}",
            f"--window-y={self.cfg['window_y']}",
            f"--window-width={self.cfg['window_width']}",
            "--stay-awake"
        ]
        if extra_args:
            cmd.extend(extra_args)
        return cmd

    def launch_scrcpy(self, extra_args: Optional[List[str]] = None):
        cmd = self.build_scrcpy_command(extra_args)
        logger.info(f"[{self.key}] Spawning scrcpy: {' '.join(cmd)}")
        self.process = subprocess.Popen(cmd)

    def tick(self, extra_args: Optional[List[str]] = None):
        # Check process status
        if self.process is not None:
            ret = self.process.poll()
            if ret is None:
                return
            else:
                logger.warning(f"[{self.key}] scrcpy exited with code {ret}. Preparing restart...")
                self.process = None

        # Process is not running; check socket connection
        if not self.is_connected():
            now = time.time()
            if now - self.last_connect_attempt > 5.0:
                self.last_connect_attempt = now
                if not self.recover_socket():
                    return
            else:
                return

        # Connected, wake screen and launch
        self.wake_screen()
        time.sleep(0.5)
        self.launch_scrcpy(extra_args)

    def terminate(self):
        if self.process is not None and self.process.poll() is None:
            logger.info(f"[{self.key}] Terminating scrcpy process (PID: {self.process.pid})...")
            self.process.terminate()
            try:
                self.process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.process.kill()

def main():
    parser = argparse.ArgumentParser(description="Lauburu Multi-Device scrcpy Mesh Launcher")
    parser.add_argument("--device", choices=["all", "s20", "pixel"], default="all", help="Target device(s)")
    parser.add_argument("--bitrate", type=str, default="16M", help="Video bitrate (default: 16M)")
    parser.add_argument("--fps", type=int, default=60, help="Max frame rate (default: 60)")
    parser.add_argument("--test", action="store_true", help="Run a one-time connection and wake test without spawning continuous daemon")
    args = parser.parse_args()

    print("=" * 80)
    print("🖥️  PROJECT LAUBURU — AUTONOMOUS SCRCPY MESH SCREEN MIRRORING DAEMON")
    print(f"Target Devices : {args.device}")
    print(f"FPS / Bitrate  : {args.fps} FPS @ {args.bitrate}")
    print(f"Mode           : {'One-Time Test' if args.test else 'Continuous Watchdog Daemon'}")
    print("=" * 80)

    targets = ["s20", "pixel"] if args.device == "all" else [args.device]
    managers = [DeviceMirrorManager(k, DEVICE_CONFIGS[k], custom_bitrate=args.bitrate, custom_fps=args.fps) for k in targets]

    if args.test:
        for mgr in managers:
            connected = mgr.is_connected()
            if not connected:
                connected = mgr.recover_socket()
            if connected:
                print(f"✓ Device {mgr.key} ({mgr.cfg['name']}) connected at {mgr.target}!")
                mgr.wake_screen()
                cmd = mgr.build_scrcpy_command()
                print(f"  Command line prepared: {' '.join(cmd)}")
            else:
                print(f"⚠️  Device {mgr.key} ({mgr.target}) not reachable in test mode.")
        print("\nTest completed.")
        return

    try:
        while running:
            for mgr in managers:
                mgr.tick()
            time.sleep(2.0)
    finally:
        for mgr in managers:
            mgr.terminate()
        logger.info("Scrcpy Mesh Daemon cleanly stopped.")

if __name__ == "__main__":
    main()
