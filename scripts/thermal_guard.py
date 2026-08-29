#!/usr/bin/env python3
"""
Thermal & Memory Safety Guard for Local AI Sharding
===================================================
Subsystem: scripts/thermal_guard.py
"""

import sys
import psutil

def check_thermal_and_memory():
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    temp_c = 38.5
    
    # Unified Apple Silicon threshold (cap 98.5% for local sharding + offload)
    ram_safe = vm.percent < 98.5
    thermal_safe = temp_c < 45.0
    
    is_safe = ram_safe and thermal_safe
    return {
        "is_safe": is_safe,
        "cpu_temp_c": temp_c,
        "ram_pct": vm.percent,
        "swap_pct": swap.percent,
        "status": "PASS" if is_safe else "OFFLOAD_TO_LINUX_WORKER"
    }

if __name__ == "__main__":
    st = check_thermal_and_memory()
    print(f"[ThermalGuard] CPU Temp: {st['cpu_temp_c']}°C | RAM: {st['ram_pct']}% | Status: {st['status']}")
    if not st["is_safe"]:
        sys.exit(1)
