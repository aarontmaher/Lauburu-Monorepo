#!/usr/bin/env python3
"""
Thermal & Memory Safety Guard for Local AI Sharding
===================================================
Subsystem: scripts/thermal_guard.py
Rule #0 Enforced: Zero-mock, authentic Darwin kernel thermal telemetry.
"""

import os
import subprocess
import sys
import psutil


def check_thermal_and_memory():
    """Authentically evaluates Darwin memory headroom and kernel thermal pressure."""
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()

    # 1. Read authentic macOS kernel thermal pressure level (0 = Normal, 1 = Moderate, 2 = Heavy, 3 = Trapping)
    thermal_pressure = 0
    try:
        res = subprocess.run(
            ["sysctl", "-n", "kern.sched_thermal_pressure_level"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res.returncode == 0 and res.stdout.strip().isdigit():
            thermal_pressure = int(res.stdout.strip())
    except Exception:
        pass

    # 2. Check pmset thermal throttles
    pmset_warning = False
    cpu_limit = 100
    try:
        res = subprocess.run(["pmset", "-g", "therm"], capture_output=True, text=True, timeout=2)
        out = res.stdout.lower()
        if "warning level has been recorded" in out and "no thermal warning" not in out and "no performance warning" not in out:
            pmset_warning = True
        for line in res.stdout.splitlines():
            if "cpu_scheduler_limit" in line.lower() or "cpu_speed_limit" in line.lower():
                parts = line.split("=")
                if len(parts) == 2 and parts[1].strip().isdigit():
                    cpu_limit = min(cpu_limit, int(parts[1].strip()))
    except Exception:
        pass

    # Dynamic RAM Governance (Rule 3 & Rule 7.1: Host RAM <= 90%, free >= 2.5 GB)
    free_gb = vm.available / (1024**3)
    ram_safe = (vm.percent <= 90.0) and (free_gb >= 2.5)
    thermal_safe = (thermal_pressure == 0) and (not pmset_warning) and (cpu_limit >= 100)

    is_safe = ram_safe and thermal_safe

    return {
        "is_safe": is_safe,
        "thermal_pressure_level": thermal_pressure,
        "thermal_pressure_desc": ["NORMAL", "MODERATE", "HEAVY", "TRAPPING"][min(thermal_pressure, 3)],
        "cpu_scheduler_limit_pct": cpu_limit,
        "pmset_warning": pmset_warning,
        "ram_pct": vm.percent,
        "ram_available_gb": round(free_gb, 2),
        "swap_pct": swap.percent,
        "status": "PASS" if is_safe else "OFFLOAD_TO_LINUX_WORKER",
    }


if __name__ == "__main__":
    st = check_thermal_and_memory()
    print(
        f"[ThermalGuard] Pressure: {st['thermal_pressure_desc']} (L{st['thermal_pressure_level']}) | "
        f"CPU Limit: {st['cpu_scheduler_limit_pct']}% | "
        f"RAM: {st['ram_pct']}% ({st['ram_available_gb']} GB avail) | "
        f"Status: {st['status']}"
    )
    if not st["is_safe"]:
        sys.exit(1)

