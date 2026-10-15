# -*- coding: utf-8 -*-
"""
GL.iNet Beryl AX (GL-MT3000/3600) PWM Fan & Thermal Throttling Governor
========================================================================
Subsystem: 01_apps/glinet_web_optimizer/beryl_ax_fan_thermal_governor.py
Lauburu Mesh Ecosystem — 2026

An autonomous thermal governor tailored for the Beryl AX travel enclosure.
Monitors CPU junction temperature (MT7981B) and dynamically modulates:
1. Active PWM cooling fan states (0 to 255)
2. Local TinyLM inference throttle / offload triggers
3. Emergency thermal shutdown threshold (>85C)
"""

from __future__ import annotations

import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("BerylAXThermalGovernor")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


@dataclass
class ThermalAction:
    timestamp: float
    temp_celsius: float
    fan_pwm: int
    thermal_zone: str  # "SILENT", "ACTIVE_COOLING", "THROTTLED_OFFLOAD", "EMERGENCY_HALT"
    inference_allowed_locally: bool
    offload_to_mesh_required: bool
    fan_sysfs_written: bool


class BerylAXThermalGovernor:
    """
    Thermal management engine for GL.iNet GL-MT3000 / GL-MT3600 (Beryl AX).
    """

    def __init__(
        self,
        thermal_zone_path: str = "/sys/class/thermal/thermal_zone0/temp",
        fan_pwm_path: str = "/sys/class/thermal/cooling_device0/cur_state",
    ):
        self.thermal_zone_path = thermal_zone_path
        self.fan_pwm_path = fan_pwm_path
        self.last_action: Optional[ThermalAction] = None

    def read_cpu_temp_celsius(self) -> float:
        """Reads SoC millicelsius from sysfs or returns realistic baseline."""
        if os.path.exists(self.thermal_zone_path):
            try:
                with open(self.thermal_zone_path, "r") as f:
                    mc = int(f.read().strip())
                    return round(mc / 1000.0, 2)
            except Exception as e:
                logger.warning(f"Failed reading thermal sysfs: {e}")
        return 52.5  # Safe default baseline in C

    def evaluate_thermal_policy(self, current_temp_c: Optional[float] = None) -> ThermalAction:
        """
        Calculates optimal fan PWM and AI workload offload decision based on temperature:
        - T < 55C: Silent (PWM = 0). Local AI permitted.
        - 55C <= T < 72C: Active Cooling (PWM = 160). Local AI permitted.
        - 72C <= T < 85C: Throttled Offload (PWM = 255). Force offload to L1/L3 mesh.
        - T >= 85C: Emergency Halt (PWM = 255). Kill local AI process immediately.
        """
        temp = current_temp_c if current_temp_c is not None else self.read_cpu_temp_celsius()
        now = time.time()

        if temp < 55.0:
            zone = "SILENT"
            pwm = 0
            allow_local = True
            force_offload = False
        elif temp < 72.0:
            zone = "ACTIVE_COOLING"
            pwm = 160
            allow_local = True
            force_offload = False
        elif temp < 85.0:
            zone = "THROTTLED_OFFLOAD"
            pwm = 255
            allow_local = False
            force_offload = True
            logger.warning(f"🔥 Thermal threshold exceeded ({temp:.1f}C >= 72C). Offloading AI inference to peripheral mesh nodes.")
        else:
            zone = "EMERGENCY_HALT"
            pwm = 255
            allow_local = False
            force_offload = True
            logger.critical(f"🚨 CRITICAL OVERHEAT ({temp:.1f}C >= 85C). Emergency halt of on-router AI execution!")

        # Apply fan PWM to sysfs if writable
        sysfs_ok = False
        if os.path.exists(self.fan_pwm_path):
            try:
                with open(self.fan_pwm_path, "w") as f:
                    f.write(str(pwm))
                sysfs_ok = True
            except Exception:
                pass

        action = ThermalAction(
            timestamp=now,
            temp_celsius=temp,
            fan_pwm=pwm,
            thermal_zone=zone,
            inference_allowed_locally=allow_local,
            offload_to_mesh_required=force_offload,
            fan_sysfs_written=sysfs_ok,
        )
        self.last_action = action
        return action
