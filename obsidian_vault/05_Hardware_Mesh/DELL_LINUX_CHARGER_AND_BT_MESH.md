---
title: "Dell Inspiron 15 3525 Power Subsystem, ACPI, BD PROCHOT & Bluetooth BNEP Mesh Architecture"
tags: [dell, ryzen, amd_pstate, bd_prochot, acpi, power_supply, bluetooth, bnep, rfcomm, hardware_mesh, head_node]
author: "Antigravity Mesh Orchestrator & Specification Miner"
status: "CANONICAL"
date: "2026-09-04"
nodes: ["[[Linux_Head_Node]]", "[[Mac_Node]]", "[[MacBook_Pro]]"]
vault_root: "[[Index]]"
canonical_rule: "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]"
---

# 📘 Dell Inspiron 15 3525 Power Subsystem, ACPI & Bluetooth BNEP Mesh Architecture

## 1. Executive Summary & 7-Layer Mesh Role
The Dell Inspiron 15 3525 operates as **Layer 3 ([[Linux_Head_Node]])** (`192.168.8.224` / `100.101.39.98`) within the Lauburu 7-layer mesh ecosystem, contributing 16.0 GB RAM (13.8 GB AI VRAM dynamic allocation) to the pooled 82.8 GB VRAM cluster alongside **Layer 1 ([[Mac_Node]])** and **Layer 2 ([[MacBook_Pro]])**.

Canonical Vault references: [[Index]], [[CANONICAL_PROJECT_AND_STORAGE_RULE]], [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]].

## 2. Hardware Specifications & Subsystem Anatomy
- **Processor:** AMD Ryzen 7 5700U (Zen 2, Lucienne, 8 cores / 16 threads, base clock $f_{\min} = 1.8\text{ GHz}$, boost clock 4.3 GHz).
- **Bluetooth Adapters:**
  - Internal: Realtek RTL8821CE (`0bda:c829` / `hci2`, BT 4.2).
  - External USB Dongle: Realtek RTL8761BU (`2357:0604` / `0bda:b009` / `hci1`, BT 5.3).
- **Power Delivery:** 65W AC Adapter (19.5V, 3.34A) with 1-Wire Dallas DS2501 ID chip on center barrel pin.
- **Hardware Identifiers:** `bluetooth_hardware`, `power_supply`, `cpu_frequencies`.

## 3. Linux Power Subsystem (`/sys/class/power_supply/`)
Audit sysfs nodes under `/sys/class/power_supply/{ACAD,BAT0}`:
- `ACAD/online`: 1 (Mains connected), 0 (Mains disconnected).
- `BAT0/status`: Charging, Discharging, Full, Not charging.
- `BAT0/power_now`: Micro-watts ($P = V \times I$ or scaled as $P = (V \times I)/10^{12}$).

## 4. Dell ACPI Drivers & Kernel SMM Configuration
```bash
sudo modprobe dell-laptop
sudo modprobe dell-wmi
sudo modprobe dell-smm-hwmon force=1 restricted=0 ignore_dmi=1
sudo modprobe msr
```

## 5. The 400 MHz BD PROCHOT Anomaly & Root Cause Analysis
When an unrecognized or degraded charger is attached, the Dell Embedded Controller (EC) fails 1-Wire center-pin authentication and asserts hardware `BD_PROCHOT#`, clamping the AMD Ryzen CPU to 399.2 MHz ($P_{\min} = 400\text{ MHz}$) despite cold silicon ($T < 45^\circ\text{C}$), well below thermal trip thresholds ($T \ge 95^\circ\text{C}$).

## 6. Frequency Governor Enforcement & AMD P-State Optimization
To restore frequencies from throttled clamp ($P_{\min} = 400\text{ MHz}$) back to normal operation ($f_{\min} = 1.8\text{ GHz}$) and performance scaling:
```bash
if [ -f /sys/devices/system/cpu/amd_pstate/status ]; then
    echo "active" | sudo tee /sys/devices/system/cpu/amd_pstate/status
fi
for gov in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo "performance" | sudo tee "$gov"
done
```

## 7. Bluetooth BNEP PAN Mesh & Out-of-Band RFCOMM Console
- Subnet: `192.168.44.0/24` (Gateway: `192.168.44.1`).
- RFCOMM: Channel 1 (`/dev/rfcomm0`), 115200 baud emergency root console.
- Zero-network emergency root console resilient against network stack failures.

## 8. Real-Time Diagnostic Telemetry Bridge (`/tmp/linux_mesh_status.json`)
Atomic sub-50ms JSON snapshot publisher streaming link state, wattage, and CPU clock speeds.
Schema fields: `timestamp`, `node`, `status`, `bluetooth_hardware`, `power_supply`, `cpu_frequencies`, `mesh_role`.

## 9. Comprehensive Troubleshooting Runbook
Step-by-step resolution for BD PROCHOT throttle and Bluetooth HCI enumeration reset:
1. Check AC adapter online state: `cat /sys/class/power_supply/ACAD/online`
2. Check CPU core clock speeds: `grep "cpu MHz" /proc/cpuinfo`
3. Execute automated unthrottling daemon: `sudo /usr/local/bin/dell_unthrottle.sh`
4. Reset Bluetooth HCI controller: `sudo hciconfig hci1 reset && sudo hciconfig hci1 piscan`
5. Connect out-of-band console from Mac Mini: `screen /dev/cu.Bluetooth-Incoming-Port 115200`
