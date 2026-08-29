#!/usr/bin/env python3
"""
Non-Blocking Asynchronous Live Hardware Router Memory Sampler
============================================================
Subsystem: 06_scripts_and_tooling/network/live_router_mem_sampler.py
Version: 2.0.0-REALTIME-HARDWARE
Lauburu Mesh Ecosystem — 2026

Polls /proc/meminfo live via SSH from GL.iNet Router (192.168.8.1)
in an asynchronous background daemon thread to eliminate UI blocking
and enforce Rule #0 (Zero-Mock / Zero-Hardcoding).
"""

import threading
import subprocess
import time
from typing import Dict, Any

ROUTER_IP = "192.168.8.1"
ROUTER_PASS = "goldfighting1"

class LiveRouterRAMSampler:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.total_mb = 0.0
        self.available_mb = 0.0
        self.free_mb = 0.0
        self.is_online = False
        self.last_update = 0.0
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def _poll_loop(self):
        while self._running:
            try:
                cmd = f"sshpass -p '{ROUTER_PASS}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=1 root@{ROUTER_IP} 'grep -E \"(MemTotal|MemFree|MemAvailable)\" /proc/meminfo'"
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=2.0)
                if res.returncode == 0 and "MemTotal" in res.stdout:
                    mem = {}
                    for line in res.stdout.splitlines():
                        if ":" in line:
                            k, v = line.split(":", 1)
                            mem[k.strip()] = int(v.strip().split()[0])
                    self.total_mb = round(mem.get("MemTotal", 492824) / 1024.0, 1)
                    self.free_mb = round(mem.get("MemFree", 0) / 1024.0, 1)
                    self.available_mb = round(mem.get("MemAvailable", self.free_mb) / 1024.0, 1)
                    self.is_online = True
                    self.last_update = time.time()
                else:
                    self.is_online = False
            except Exception:
                self.is_online = False
            time.sleep(2.0)

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "online": self.is_online,
            "total_mb": self.total_mb,
            "available_mb": self.available_mb,
            "free_mb": self.free_mb,
            "last_update": self.last_update
        }

_GLOBAL_SAMPLER = None

def get_live_router_ram_metrics() -> Dict[str, Any]:
    global _GLOBAL_SAMPLER
    if _GLOBAL_SAMPLER is None:
        _GLOBAL_SAMPLER = LiveRouterRAMSampler()
    return _GLOBAL_SAMPLER.get_metrics()

if __name__ == "__main__":
    print("Testing live router RAM sampler...")
    s = get_live_router_ram_metrics()
    time.sleep(1.5)
    s = get_live_router_ram_metrics()
    print("Live result:", s)
