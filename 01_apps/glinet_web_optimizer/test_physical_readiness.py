# -*- coding: utf-8 -*-
"""
Verification Tests for GL.iNet Beryl AX Physical Hardware Readiness
====================================================================
Subsystem: 01_apps/glinet_web_optimizer/test_physical_readiness.py
Lauburu Mesh Ecosystem — 2026
"""

import importlib.util
import os
import sys
import pytest
from pathlib import Path

_curr_dir = Path(__file__).resolve().parent

def _load_module(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

# Import Thermal Governor & USB Multiplexer
_thermal_mod = _load_module("beryl_ax_fan_thermal_governor", _curr_dir / "beryl_ax_fan_thermal_governor.py")
BerylAXThermalGovernor = _thermal_mod.BerylAXThermalGovernor

_usb_mod = _load_module("usb_port_multiplexer", _curr_dir / "usb_port_multiplexer.py")
USBPortMultiplexer = _usb_mod.USBPortMultiplexer


def test_procd_init_script_structure():
    """Verifies that lauburu_supervisor.init satisfies OpenWrt procd standards."""
    init_path = _curr_dir / "lauburu_supervisor.init"
    assert init_path.exists()
    content = init_path.read_text()

    assert "START=95" in content
    assert "STOP=10" in content
    assert "USE_PROCD=1" in content
    assert "/tmp/run/ai_supervisor" in content  # Zero flash wear tmpfs
    assert "125829120" in content  # 120 MB RAM cgroup cap
    assert "taskset -c 1" in content  # Core 1 AI / Core 0 routing


def test_thermal_governor_curves():
    """Verifies that the Beryl AX thermal governor dynamically scales fan PWM and offloads."""
    gov = BerylAXThermalGovernor()

    # Zone 1: Silent (<55C)
    act_silent = gov.evaluate_thermal_policy(current_temp_c=48.0)
    assert act_silent.thermal_zone == "SILENT"
    assert act_silent.fan_pwm == 0
    assert act_silent.inference_allowed_locally is True
    assert act_silent.offload_to_mesh_required is False

    # Zone 2: Active Cooling (55C - 72C)
    act_cool = gov.evaluate_thermal_policy(current_temp_c=64.0)
    assert act_cool.thermal_zone == "ACTIVE_COOLING"
    assert act_cool.fan_pwm == 160
    assert act_cool.inference_allowed_locally is True
    assert act_cool.offload_to_mesh_required is False

    # Zone 3: Throttled Offload (72C - 85C)
    act_offload = gov.evaluate_thermal_policy(current_temp_c=78.0)
    assert act_offload.thermal_zone == "THROTTLED_OFFLOAD"
    assert act_offload.fan_pwm == 255
    assert act_offload.inference_allowed_locally is False
    assert act_offload.offload_to_mesh_required is True

    # Emergency: Critical Overheat (>=85C)
    act_crit = gov.evaluate_thermal_policy(current_temp_c=88.0)
    assert act_crit.thermal_zone == "EMERGENCY_HALT"
    assert act_crit.inference_allowed_locally is False


def test_usb_multiplexer_devices():
    """Verifies that USBPortMultiplexer identifies Android ADB vs 5G modem vs storage."""
    mux = USBPortMultiplexer()

    # 1. Android Phone attached
    dev_adb = mux.inspect_usb_bus(simulated_devices=[{"vendor_id": "04e8", "product_id": "6860", "description": "Samsung S20+"}])
    assert dev_adb.detected is True
    assert dev_adb.device_type == "ANDROID_ADB"
    assert "Path 4.5" in dev_adb.active_pathway

    # 2. 5G Cellular USB Modem attached
    dev_modem = mux.inspect_usb_bus(simulated_devices=[{"vendor_id": "12d1", "product_id": "1506", "driver": "cdc_ncm", "description": "Huawei 5G Modem"}])
    assert dev_modem.detected is True
    assert dev_modem.device_type == "CELLULAR_5G_MODEM"
    assert dev_modem.interface_name == "usb0"
    assert "lauburu_bond" in dev_modem.active_pathway

    # 3. Disconnected state
    dev_none = mux.inspect_usb_bus(simulated_devices=[])
    assert dev_none.detected is False
    assert dev_none.device_type == "DISCONNECTED"
