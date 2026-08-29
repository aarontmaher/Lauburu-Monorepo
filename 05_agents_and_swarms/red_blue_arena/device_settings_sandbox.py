#!/usr/bin/env python3
"""
Clean-Room Device Settings Sandbox & Autonomous Algorithm Scout Engine
Lauburu Mesh Ecosystem — 2026

Rule #0 Compliant: Provides virtual shadow configuration namespaces for physical hardware:
- GL.iNet Router (OpenWrt SQM / BQL / Wi-Fi 7 MLO)
- Movesense BLE (MDS Whiteboard / 128Hz ECG / 52Hz IMU)
- Mac Mini M4 Pro (Darwin sysctl / Metal GGML)
- Linux Head Node (AMD 5700U / Petals DHT)

Allows Red & Blue teams to scout telemetry, reverse-engineer parameters, and deploy
custom optimization algorithms without impacting physical production hardware.
"""

import os
import sys
import time
import json
import random
import math
from pathlib import Path
from typing import Dict, List, Any, Tuple

SANDBOX_STATE_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/device_settings_shadow.json")
MOVESENSE_LIVE_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/movesense_live_stream.json")
TRANSPORT_STATS_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/benchmarks/live_transport_stats.json")

DEFAULT_DEVICE_SHADOWS = {
    "glinet_router": {
        "device_model": "GL-MT3600BE (OpenWrt 23.05)",
        "ip_address": "192.168.8.1",
        "settings": {
            "sqm_queue_discipline": "cake",
            "sqm_upload_limit_kbps": 250000,
            "sqm_download_limit_kbps": 950000,
            "bql_limit_bytes": 4096,
            "wifi7_mlo_enabled": True,
            "mtu_size": 9000,
            "tcp_congestion_control": "bbr",
            "active_qos_priority_ports": [50052, 8080, 8083, 8086]
        },
        "optimizations_applied": []
    },
    "movesense_sensor": {
        "device_model": "Movesense HR+ 261030002013",
        "ble_address": "C1DB5043-8F89-88E8-46A3-BBD4ED83FC88",
        "settings": {
            "ecg_sample_rate_hz": 128,
            "imu_sample_rate_hz": 52,
            "ble_tx_power_dbm": 4,
            "whiteboard_subscription": "/Meas/ECG/128",
            "kamath_artifact_filter_threshold_pct": 20.0,
            "dfa_alpha1_window_size": 64,
            "battery_save_mode": False
        },
        "optimizations_applied": []
    },
    "mac_mini_host": {
        "device_model": "Apple M4 Pro Mac Mini (24GB RAM)",
        "settings": {
            "sysctl_tcp_win_scale": 7,
            "sysctl_max_socket_buffers_mb": 64,
            "metal_threadgroup_size": 256,
            "rpc_server_threads": 8,
            "bridge0_jumbo_frames": 9000
        },
        "optimizations_applied": []
    },
    "linux_head_node": {
        "device_model": "AMD Ryzen 7 5700U (16GB RAM)",
        "settings": {
            "cpu_governor": "performance",
            "net_core_rmem_max": 16777216,
            "net_core_wmem_max": 16777216,
            "petals_dht_block_allocation": 8,
            "cgroup_memory_limit_gb": 13.8
        },
        "optimizations_applied": []
    }
}

class DeviceSettingsSandbox:
    def __init__(self):
        self.devices = DEFAULT_DEVICE_SHADOWS
        self.turn_count = 1
        self.live_telemetry = {"heart_rate_bpm": 72, "mean_rtt_ms": 0.35}
        self.load_or_init()

    def load_or_init(self):
        if SANDBOX_STATE_PATH.exists():
            try:
                with open(SANDBOX_STATE_PATH) as f:
                    self.devices = json.load(f).get("devices", DEFAULT_DEVICE_SHADOWS)
            except Exception:
                self.devices = DEFAULT_DEVICE_SHADOWS
        else:
            self.save_state()

    def scout_real_telemetry(self) -> Dict[str, Any]:
        """Scouts physical telemetry from Movesense BLE & Network Transports."""
        hr = 72
        rtt = 0.35
        if MOVESENSE_LIVE_PATH.exists():
            try:
                with open(MOVESENSE_LIVE_PATH) as f:
                    d = json.load(f)
                    hr = d.get("heart_rate_bpm") or 72
            except Exception:
                pass
        if TRANSPORT_STATS_PATH.exists():
            try:
                with open(TRANSPORT_STATS_PATH) as f:
                    d = json.load(f)
                    rtt = d.get("transports", {}).get("thunderbolt_4_dma", {}).get("mean_latency_ms") or 0.35
            except Exception:
                pass
        self.live_telemetry = {"heart_rate_bpm": hr, "mean_rtt_ms": rtt}
        return self.live_telemetry

    def red_team_optimize_action(self) -> Dict[str, Any]:
        """Red Team (Abliterated) scouts and mutates parameters for aggressive throughput."""
        scout = self.scout_real_telemetry()
        actions = [
            ("glinet_router", "bql_limit_bytes", 8192, "Aggressive BQL Queue Burst Expansion"),
            ("movesense_sensor", "ecg_sample_rate_hz", 512, "High-Frequency 512Hz Raw ECG Stream Injection"),
            ("mac_mini_host", "sysctl_max_socket_buffers_mb", 128, "TB4 Memory Buffer Overdrive"),
            ("linux_head_node", "petals_dht_block_allocation", 12, "DHT Tensor Layer Pre-Allocation")
        ]
        dev, key, val, desc = random.choice(actions)
        self.devices[dev]["settings"][key] = val
        opt_entry = {
            "timestamp": time.strftime("%H:%M:%S", time.gmtime()),
            "faction": "RED_TEAM",
            "action": desc,
            "device": dev,
            "parameter": key,
            "new_value": val,
            "scouted_hr_bpm": scout["heart_rate_bpm"]
        }
        self.devices[dev]["optimizations_applied"].append(opt_entry)
        if len(self.devices[dev]["optimizations_applied"]) > 10:
            self.devices[dev]["optimizations_applied"].pop(0)
        return opt_entry

    def blue_team_optimize_action(self) -> Dict[str, Any]:
        """Blue Team (Standard) scouts and hardens parameters for self-healing & stability."""
        scout = self.scout_real_telemetry()
        actions = [
            ("glinet_router", "sqm_queue_discipline", "fq_codel", "Self-Healing SQM Bufferbloat Elimination"),
            ("movesense_sensor", "kamath_artifact_filter_threshold_pct", 15.0, "Precision Kamath HRV QRS Stabilization"),
            ("mac_mini_host", "bridge0_jumbo_frames", 9000, "Lock MTU 9000 Jumbo Frame Tripwire"),
            ("linux_head_node", "cpu_governor", "performance", "Dynamic Core Frequency Lock")
        ]
        dev, key, val, desc = random.choice(actions)
        self.devices[dev]["settings"][key] = val
        opt_entry = {
            "timestamp": time.strftime("%H:%M:%S", time.gmtime()),
            "faction": "BLUE_TEAM",
            "action": desc,
            "device": dev,
            "parameter": key,
            "new_value": val,
            "scouted_hr_bpm": scout["heart_rate_bpm"]
        }
        self.devices[dev]["optimizations_applied"].append(opt_entry)
        if len(self.devices[dev]["optimizations_applied"]) > 10:
            self.devices[dev]["optimizations_applied"].pop(0)
        return opt_entry

    def save_state(self):
        SANDBOX_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "turn_count": self.turn_count,
            "live_telemetry": self.live_telemetry,
            "devices": self.devices
        }
        with open(SANDBOX_STATE_PATH, "w") as f:
            json.dump(payload, f, indent=2)

def run_sandbox_daemon():
    print("=" * 75)
    print("🛠️ LAUNCHING CLEAN-ROOM DEVICE SETTINGS SANDBOX & SCOUT DAEMON")
    print("=" * 75)
    sandbox = DeviceSettingsSandbox()
    for _ in range(6):
        red_act = sandbox.red_team_optimize_action()
        print(f"🔴 RED ACTION: {red_act['action']} on {red_act['device']} (Param: {red_act['parameter']} -> {red_act['new_value']})")
        time.sleep(0.2)
        blue_act = sandbox.blue_team_optimize_action()
        print(f"🔵 BLUE ACTION: {blue_act['action']} on {blue_act['device']} (Param: {blue_act['parameter']} -> {blue_act['new_value']})")
        sandbox.turn_count += 1
        sandbox.save_state()
        time.sleep(0.2)
    print(f"\n✅ Clean-Room sandbox state saved to {SANDBOX_STATE_PATH}")

if __name__ == "__main__":
    run_sandbox_daemon()
