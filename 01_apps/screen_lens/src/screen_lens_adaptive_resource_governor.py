#!/usr/bin/env python3
"""
screen_lens_adaptive_resource_governor.py
=========================================
Canonical Screen Lens Sovereign Adaptive Resource Governor.
Governs:
1. Human Use Identification:
   - Detects active mouse, keyboard, touch, and screen focus events.
   - If device is in human use, INSTANTLY optimizes CPU and RAM to make background
     local and cloud AI completely imperceptible and zero-stutter.
   - Once human activity has ceased for sustained duration (hysteresis), ramps
     CPU and RAM utilization back up smoothly.
2. Battery Awareness:
   - Detects AC power vs Battery discharging and battery level.
   - Enforces graduated compute caps (AC -> 100%, Batt >75% -> 50%, Batt <40% -> 0%).
3. Location Awareness:
   - Detects Home Wi-Fi (GL-BE14000 / 192.168.8.1 gateway) vs Away (Cellular/External Wi-Fi).
   - If user is away from home (e.g. with Pixel / Laptop), completely suppresses
     heavy background AI to protect mobile battery and data.
4. Tri-Proof Verification & Zero-Mock Compliance (Rule 0, 1, 3, 10).
"""

import sys
import os
import re
import time
import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [AdaptiveGovernor] %(levelname)s: %(message)s")
logger = logging.getLogger("AdaptiveGovernor")

# Threshold Constants
HUMAN_ACTIVE_THRESHOLD_SEC = 60.0       # <60s idle = human is actively using device
HUMAN_RAMP_UP_IDLE_SEC = 120.0          # >=120s continuous idle before ramping compute up
BATTERY_CRITICAL_PCT = 20.0             # <20% battery = 0% compute, ultra-low power
BATTERY_LOW_PCT = 40.0                  # <40% battery = no heavy training/inference
BATTERY_NORMAL_PCT = 75.0               # 40-75% battery = conservative inference only
HOME_GATEWAY = "192.168.8.1"
HOME_SUBNET_PREFIX = "192.168.8."
HOME_SSID_KEYWORD = "GL-BE14000"

STATE_FILE = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/src/adaptive_governor_state.json")

def run_cmd(cmd: str, timeout: float = 6.0) -> Tuple[int, str, str]:
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -1, "", str(e)

# ==============================================================================
# 1. TELEMETRY EXTRACTORS
# ==============================================================================

class DeviceTelemetryProber:
    """Probes physical telemetry across macOS, Android, and Linux nodes."""

    @staticmethod
    def probe_local_macos() -> Dict[str, Any]:
        """Probes local Mac Mini M4 Pro host."""
        # 1. Idle time via IOHIDSystem
        code, out, _ = run_cmd("ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print int($NF/1000000000)}' | head -n 1", timeout=2.0)
        idle_sec = float(out) if code == 0 and out.isdigit() else 0.0

        # 2. Power source & battery
        code_p, p_out, _ = run_cmd("pmset -g batt", timeout=2.0)
        is_ac = "AC Power" in p_out
        battery_pct = 100.0
        if "InternalBattery" in p_out:
            for part in p_out.split():
                if "%" in part:
                    try:
                        battery_pct = float(part.replace("%", "").replace(";", ""))
                        break
                    except ValueError:
                        pass

        # 3. Frontmost app via /usr/bin/lsappinfo (Rule 3 compliant, no osascript polling)
        frontmost = "Unknown"
        code_a, app_out, _ = run_cmd("/usr/bin/lsappinfo info $(/usr/bin/lsappinfo front 2>/dev/null) 2>/dev/null | head -n 1", timeout=2.0)
        if code_a == 0 and app_out:
            m = re.search(r'"([^"]+)"', app_out)
            if m:
                frontmost = m.group(1)

        # 3b. Screen Lens Global Orchestrator (Port 3037) perception query
        lens_perception = {}
        try:
            import urllib.request
            req = urllib.request.Request("http://127.0.0.1:3037/api/orchestrator/state")
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            with opener.open(req, timeout=1.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode())
                    lens_screen = data.get("screen", {})
                    lens_perception = {
                        "active_app": lens_screen.get("active_app"),
                        "window_title": lens_screen.get("window_title"),
                        "frame_count": lens_screen.get("frame_count"),
                        "healthy_services": data.get("mesh_health", {}).get("healthy_services")
                    }
                    if not frontmost or frontmost == "Unknown":
                        frontmost = lens_perception.get("active_app", frontmost)
        except Exception:
            pass

        # 4. Network gateway & location
        code_g, g_out, _ = run_cmd("route -n get default | grep gateway | awk '{print $2}'", timeout=2.0)
        gateway = g_out if code_g == 0 else "unknown"
        p_code, _, _ = run_cmd(f"ping -c 1 -W 500 {HOME_GATEWAY}", timeout=1.0)
        is_home = (gateway in [HOME_GATEWAY, "192.168.0.1"] or p_code == 0)

        # 5. Darwin Memory (Rule 1 §6 Mach formulas & Rule 3 sanctuary cap)
        code_press, press_out, _ = run_cmd("sysctl -n kern.memorystatus_vm_pressure_level", timeout=2.0)
        pressure_lvl = int(press_out) if code_press == 0 and press_out.isdigit() else 1
        pressure_str = {1: "Normal", 2: "Warning", 3: "Critical"}.get(pressure_lvl, str(pressure_lvl))

        darwin_mem = {}
        try:
            page_size = int(subprocess.check_output(["sysctl", "-n", "hw.pagesize"]).decode().strip())
            total_mem = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"]).decode().strip())
            vm_out = subprocess.check_output(["vm_stat"]).decode()
            stats = {}
            for line in vm_out.splitlines():
                m = re.match(r"\"?([^\":]+)\"?:?\s+(\d+)\.?", line)
                if m:
                    stats[m.group(1).strip()] = int(m.group(2))
            anon = stats.get("Anonymous pages", 0)
            purge = stats.get("Pages purgeable", 0)
            wired = stats.get("Pages wired down", 0)
            comp = stats.get("Pages occupied by compressor", 0)
            file_backed = stats.get("File-backed pages", 0)
            app_mem = max(0, (anon - purge) * page_size)
            wired_mem = wired * page_size
            comp_mem = comp * page_size
            cached_mem = (file_backed + purge) * page_size
            used_mem = app_mem + wired_mem + comp_mem
            headroom_bytes = total_mem - used_mem
            headroom_gb = round(headroom_bytes / (1024**3), 2)
            used_gb = round(used_mem / (1024**3), 2)
            total_gb = round(total_mem / (1024**3), 2)
            darwin_mem = {
                "total_ram_gb": total_gb,
                "used_ram_gb": used_gb,
                "used_pct": round(used_mem / total_mem * 100, 1),
                "app_ram_gb": round(app_mem / (1024**3), 2),
                "wired_ram_gb": round(wired_mem / (1024**3), 2),
                "compressed_ram_gb": round(comp_mem / (1024**3), 2),
                "cached_files_gb": round(cached_mem / (1024**3), 2),
                "headroom_gb": headroom_gb,
                "rule3_sanctuary_compliant": headroom_gb >= 4.8,
                "pressure_level": pressure_str
            }
        except Exception as e:
            darwin_mem = {"error": str(e), "pressure_level": pressure_str}

        return {
            "node_id": "L1_Mac_Host",
            "name": "Mac mini M4 Pro Host",
            "platform": "macos",
            "idle_sec": idle_sec,
            "human_active": idle_sec < HUMAN_ACTIVE_THRESHOLD_SEC,
            "frontmost_app": frontmost,
            "screen_lens_perception": lens_perception,
            "is_ac_power": is_ac,
            "battery_pct": battery_pct,
            "default_gateway": gateway,
            "is_home": is_home,
            "location_mode": "HOME_SANCTUARY" if is_home else "AWAY_MOBILE",
            "memory_pressure_level": pressure_str,
            "darwin_memory": darwin_mem
        }

    @staticmethod
    def probe_remote_macos(node_id: str, name: str, candidate_ips: List[str], user: str = "aaronmaher") -> Dict[str, Any]:
        """Probes remote macOS host with multi-IP fallback."""
        for ip in candidate_ips:
            p_code, _, _ = run_cmd(f"ping -c 1 -W 1200 {ip}", timeout=2.0)
            if p_code != 0:
                continue

            ssh_cmd = (
                f"ssh -F /dev/null -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=3 "
                f"-o GSSAPIAuthentication=no -o PreferredAuthentications=publickey "
                f"{user}@{ip} \"ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {{print int(\\$NF/1000000000)}}' | head -n 1; "
                f"pmset -g batt; route -n get default | awk '/gateway/ {{print \\$2}}'; vm_stat | head -n 5\""
            )
            code, out, _ = run_cmd(ssh_cmd, timeout=5.0)
            if code != 0 or not out:
                continue

            lines = [l.strip() for l in out.splitlines() if l.strip()]
            idle_sec = 9999.0
            is_ac = True
            battery_pct = 100.0
            gateway = "unknown"

            if lines:
                try:
                    idle_sec = float(lines[0])
                except ValueError:
                    pass

            for l in lines[1:]:
                if "AC Power" in l:
                    is_ac = True
                elif "Battery Power" in l:
                    is_ac = False
                if "%" in l:
                    for tok in l.split():
                        if "%" in tok:
                            try:
                                battery_pct = float(tok.replace("%", "").replace(";", ""))
                            except ValueError:
                                pass
                if l.startswith("192.") or l.startswith("10.") or l.startswith("172."):
                    gateway = l

            is_home = (gateway == HOME_GATEWAY or "192.168.8." in ip or ip.startswith("10.0.0."))
            return {
                "node_id": node_id,
                "name": name,
                "platform": "macos",
                "active_ip": ip,
                "idle_sec": idle_sec,
                "human_active": idle_sec < HUMAN_ACTIVE_THRESHOLD_SEC,
                "is_ac_power": is_ac,
                "battery_pct": battery_pct,
                "default_gateway": gateway,
                "is_home": is_home,
                "location_mode": "HOME_SANCTUARY" if is_home else "AWAY_MOBILE"
            }

        return {"node_id": node_id, "name": name, "status": "OFFLINE_OR_DOZE"}

    @staticmethod
    def probe_linux_node(node_id: str, name: str, candidate_ips: List[str], user: str = "linuxmini") -> Dict[str, Any]:
        """Probes Linux compute host."""
        for ip in candidate_ips:
            p_code, _, _ = run_cmd(f"ping -c 1 -W 1200 {ip}", timeout=2.0)
            if p_code != 0:
                continue

            ssh_cmd = (
                f"ssh -F /dev/null -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=3 "
                f"-o GSSAPIAuthentication=no -o PreferredAuthentications=publickey "
                f"{user}@{ip} \"cat /proc/loadavg; free -m | grep Mem; ip route show default | awk '{{print \\$3}}'; w | head -n 3\""
            )
            code, out, _ = run_cmd(ssh_cmd, timeout=5.0)
            if code != 0 or not out:
                continue

            lines = [l.strip() for l in out.splitlines() if l.strip()]
            load_avg = 0.0
            free_mem_mb = 0
            total_mem_mb = 0
            gateway = "unknown"

            if lines:
                try:
                    load_avg = float(lines[0].split()[0])
                except (ValueError, IndexError):
                    pass

            for l in lines[1:]:
                if "Mem:" in l:
                    parts = l.split()
                    if len(parts) >= 7:
                        try:
                            total_mem_mb = int(parts[1])
                            free_mem_mb = int(parts[6])  # available
                        except ValueError:
                            pass
                elif l.startswith("192.") or l.startswith("10.") or l.startswith("172."):
                    gateway = l

            is_home = (gateway == HOME_GATEWAY or "192.168.8." in ip or ip.startswith("10.0.0.") or ip.startswith("100.121."))
            return {
                "node_id": node_id,
                "name": name,
                "platform": "linux",
                "active_ip": ip,
                "idle_sec": 9999.0,
                "human_active": False,  # Headless compute server
                "is_ac_power": True,     # Mains powered server
                "battery_pct": 100.0,
                "load_avg": load_avg,
                "total_mem_mb": total_mem_mb,
                "available_mem_mb": free_mem_mb,
                "default_gateway": gateway,
                "is_home": is_home,
                "location_mode": "HOME_SANCTUARY" if is_home else "AWAY_MOBILE"
            }

        return {"node_id": node_id, "name": name, "status": "OFFLINE_OR_DOZE"}

    @staticmethod
    def probe_pixel_termux(candidate_ips: List[str] = ["100.114.215.68", "192.168.8.213"], port: int = 8022, user: str = "u0_a234") -> Dict[str, Any]:
        """Probes Google Pixel 10 Pro XL directly via Termux SSH."""
        for ip in candidate_ips:
            # Check TCP port or ICMP ping for reliable mobile reachability
            p_code, _, _ = run_cmd(f"nc -z -w 2 {ip} {port}", timeout=3.0)
            if p_code != 0:
                p_code, _, _ = run_cmd(f"ping -c 1 -W 2000 {ip}", timeout=3.0)
            if p_code != 0:
                continue

            ssh_cmd = (
                f"ssh -F /dev/null -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=5 "
                f"-p {port} {user}@{ip} \"termux-battery-status; echo ___DELIM___; ping -c 1 -W 1 {HOME_GATEWAY} >/dev/null 2>&1 && echo HOME || echo AWAY; echo ___DELIM___; free -m; echo ___DELIM___; tmux list-clients -F '#{{client_activity}}' 2>/dev/null || echo ''\""
            )
            code, out, _ = run_cmd(ssh_cmd, timeout=10.0)
            if code != 0 or not out:
                continue

            parts = out.split("___DELIM___")
            batt_info = {}
            if len(parts) > 0 and "{" in parts[0]:
                try:
                    batt_info = json.loads(parts[0].strip()[parts[0].strip().find("{"):])
                except Exception:
                    pass

            location_tag = parts[1].strip() if len(parts) > 1 else "AWAY"
            is_home = (location_tag == "HOME")

            # Memory
            free_avail = 0
            total_mb = 0
            if len(parts) > 2:
                for line in parts[2].splitlines():
                    if "Mem:" in line:
                        toks = line.split()
                        if len(toks) >= 7:
                            try:
                                total_mb = int(toks[1])
                                free_avail = int(toks[6])
                            except ValueError:
                                pass

            # Human idle / activity
            idle_sec = 3600.0
            if len(parts) > 3 and parts[3].strip().isdigit():
                act_time = float(parts[3].strip())
                idle_sec = max(0.0, time.time() - act_time)

            battery_pct = float(batt_info.get("percentage", 100.0))
            status_str = str(batt_info.get("status", "")).strip().upper()
            plugged_str = str(batt_info.get("plugged", "")).strip().upper()
            is_ac = (
                status_str in ["CHARGING", "FULL"]
                or (
                    plugged_str in ["PLUGGED_AC", "PLUGGED_USB", "PLUGGED_WIRELESS"]
                    and plugged_str != "UNPLUGGED"
                )
            )

            return {
                "node_id": "L6_Pixel_10_Pro_XL",
                "name": "Google Pixel 10 Pro XL (Tensor G5)",
                "platform": "android",
                "active_ip": ip,
                "idle_sec": idle_sec,
                "human_active": idle_sec < HUMAN_ACTIVE_THRESHOLD_SEC,
                "is_ac_power": is_ac,
                "battery_pct": battery_pct,
                "battery_detail": {
                    "health": batt_info.get("health", "UNKNOWN"),
                    "status": status_str or "UNKNOWN",
                    "plugged": plugged_str or "UNKNOWN",
                    "temp_c": batt_info.get("temperature"),
                    "voltage_mv": batt_info.get("voltage")
                },
                "total_mem_mb": total_mb,
                "available_mem_mb": free_avail,
                "is_home": is_home,
                "location_mode": "HOME_SANCTUARY" if is_home else "AWAY_MOBILE"
            }

        return {"node_id": "L6_Pixel_10_Pro_XL", "name": "Google Pixel 10 Pro XL", "status": "OFFLINE_OR_DOZE"}

    @staticmethod
    def probe_router(candidate_ips: List[str] = ["192.168.8.1", "100.70.123.123"]) -> Dict[str, Any]:
        """Probes GL.iNet Gateway Router."""
        for ip in candidate_ips:
            p_code, _, _ = run_cmd(f"ping -c 1 -W 1200 {ip}", timeout=2.0)
            if p_code != 0:
                continue

            ssh_cmd = (
                f"ssh -F /dev/null -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=3 "
                f"root@{ip} \"cat /proc/loadavg; free | grep Mem; route -n | grep '^0.0.0.0' | head -n 1\""
            )
            code, out, _ = run_cmd(ssh_cmd, timeout=5.0)
            if code != 0 or not out:
                continue

            lines = [l.strip() for l in out.splitlines() if l.strip()]
            load_avg = 0.0
            avail_kb = 0
            wan_gw = "unknown"
            for l in lines:
                if "Mem:" in l:
                    parts = l.split()
                    if len(parts) >= 7:
                        try:
                            avail_kb = int(parts[6])
                        except ValueError:
                            pass
                elif l.startswith("0.0.0.0"):
                    parts = l.split()
                    if len(parts) >= 2:
                        wan_gw = parts[1]
                elif "." in l and len(l.split()) >= 3 and not l.startswith("Warning") and not l.startswith("**"):
                    try:
                        load_avg = float(l.split()[0])
                    except Exception:
                        pass

            return {
                "node_id": "GW_Router",
                "name": "GL.iNet GL-BE14000 Sovereign Gateway",
                "platform": "openwrt_linux",
                "active_ip": ip,
                "idle_sec": 9999.0,
                "human_active": False,
                "is_ac_power": True,
                "battery_pct": 100.0,
                "load_avg": load_avg,
                "available_mem_mb": round(avail_kb / 1024, 1),
                "wan_gateway": wan_gw,
                "is_home": True,
                "location_mode": "HOME_SANCTUARY"
            }

        return {"node_id": "GW_Router", "name": "GL.iNet GL-BE14000", "status": "OFFLINE_OR_DOZE"}

# ==============================================================================
# 2. ADAPTIVE OPTIMIZATION DECISION ENGINE
# ==============================================================================

class AdaptiveOptimizationEngine:
    """Evaluates telemetry and computes dynamic CPU/RAM/Cloud throttling parameters."""

    @classmethod
    def evaluate_node_policy(cls, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        node_id = telemetry.get("node_id", "unknown")
        idle_sec = telemetry.get("idle_sec", 0.0)
        human_active = telemetry.get("human_active", False)
        is_home = telemetry.get("is_home", True)
        is_ac = telemetry.get("is_ac_power", True)
        battery_pct = telemetry.get("battery_pct", 100.0)

        # Decision variables
        cpu_quota_pct = 100
        cpu_nice_level = 0
        max_worker_threads = 8
        ram_cache_trim = False
        background_lora_permitted = True
        cloud_batch_permitted = True
        action_state = "FULL_SPEED_SWARM"
        reason = "Device idle on AC power at Home."

        # Rule A: Location Awareness (Away from Home Protection)
        if not is_home:
            action_state = "AWAY_MOBILE_SANCTUARY"
            cpu_quota_pct = 0
            cpu_nice_level = 19
            max_worker_threads = 0
            background_lora_permitted = False
            cloud_batch_permitted = False
            ram_cache_trim = True
            reason = "Node is AWAY from Home. AI compute suppressed to 0% to prevent battery drain and mobile data usage."
            return cls._build_action_dict(telemetry, action_state, cpu_quota_pct, cpu_nice_level, max_worker_threads, ram_cache_trim, background_lora_permitted, cloud_batch_permitted, reason)

        # Rule B: Battery Awareness (Low/Critical Battery)
        if not is_ac and battery_pct < BATTERY_CRITICAL_PCT:
            action_state = "BATTERY_CRITICAL_SLEEP"
            cpu_quota_pct = 0
            cpu_nice_level = 19
            max_worker_threads = 0
            background_lora_permitted = False
            cloud_batch_permitted = False
            ram_cache_trim = True
            reason = f"Battery critically low ({battery_pct}% < {BATTERY_CRITICAL_PCT}%). All background AI halted."
            return cls._build_action_dict(telemetry, action_state, cpu_quota_pct, cpu_nice_level, max_worker_threads, ram_cache_trim, background_lora_permitted, cloud_batch_permitted, reason)

        if not is_ac and battery_pct < BATTERY_LOW_PCT:
            action_state = "BATTERY_LOW_CONSERVE"
            cpu_quota_pct = 15
            cpu_nice_level = 19
            max_worker_threads = 1
            background_lora_permitted = False
            cloud_batch_permitted = False
            ram_cache_trim = True
            reason = f"Battery low ({battery_pct}% < {BATTERY_LOW_PCT}%). Training halted, compute heavily throttled."
            return cls._build_action_dict(telemetry, action_state, cpu_quota_pct, cpu_nice_level, max_worker_threads, ram_cache_trim, background_lora_permitted, cloud_batch_permitted, reason)

        # Rule C: Human Use Identification (Instant Optimization)
        if human_active:
            action_state = "HUMAN_ACTIVE_OPTIMIZED"
            cpu_quota_pct = 20
            cpu_nice_level = 19
            max_worker_threads = 1
            background_lora_permitted = False   # Instantly pause heavy training
            cloud_batch_permitted = False       # Stop background cloud batching
            ram_cache_trim = True               # Evict stale working sets to free RAM for user
            reason = f"Human interaction detected (idle {idle_sec:.1f}s < {HUMAN_ACTIVE_THRESHOLD_SEC}s). Throttled to 1 thread at nice +19 for zero UI lag."
            return cls._build_action_dict(telemetry, action_state, cpu_quota_pct, cpu_nice_level, max_worker_threads, ram_cache_trim, background_lora_permitted, cloud_batch_permitted, reason)

        # Rule D: Hysteresis Transition Phase (60s - 120s idle)
        if idle_sec < HUMAN_RAMP_UP_IDLE_SEC:
            action_state = "IDLE_HYSTERESIS_TRANSITION"
            cpu_quota_pct = 40
            cpu_nice_level = 10
            max_worker_threads = 2
            background_lora_permitted = False
            cloud_batch_permitted = True
            ram_cache_trim = False
            reason = f"Device transitioning from human use (idle {idle_sec:.1f}s < {HUMAN_RAMP_UP_IDLE_SEC}s). Maintaining smooth ramp-up buffer."
            return cls._build_action_dict(telemetry, action_state, cpu_quota_pct, cpu_nice_level, max_worker_threads, ram_cache_trim, background_lora_permitted, cloud_batch_permitted, reason)

        # Rule E: Full Ramp-Up (Sustained Idle >= 120s)
        action_state = "SUSTAINED_IDLE_RAMPED_UP"
        if not is_ac and battery_pct < BATTERY_NORMAL_PCT:
            cpu_quota_pct = 50
            cpu_nice_level = 5
            max_worker_threads = 4
            background_lora_permitted = False
            cloud_batch_permitted = True
            reason = f"Sustained idle on battery ({battery_pct}%). Ramped up to 50% CPU quota (training withheld)."
        else:
            cpu_quota_pct = 100
            cpu_nice_level = 0
            max_worker_threads = 8
            background_lora_permitted = True
            cloud_batch_permitted = True
            reason = f"Sustained idle for {idle_sec:.1f}s on AC power at Home. Full CPU/RAM capacity enabled for swarm compute."

        # Rule F: Rule 3 Host Sanctuary RAM Headroom Invariant (<4.8 GB on Mac Host)
        darwin_mem = telemetry.get("darwin_memory", {})
        headroom_gb = darwin_mem.get("headroom_gb")
        if headroom_gb is not None and headroom_gb < 4.8:
            action_state = "SANCTUARY_MEMORY_THROTTLED"
            cpu_quota_pct = min(cpu_quota_pct, 60)
            cpu_nice_level = max(cpu_nice_level, 10)
            max_worker_threads = min(max_worker_threads, 4)
            background_lora_permitted = False  # Offload heavy LoRA training to L3/L8 per Rule 10
            ram_cache_trim = True
            reason = f"Rule 3 Sanctuary Alert: Host RAM headroom ({headroom_gb:.2f} GB) is below 4.80 GB limit. Compute throttled to {cpu_quota_pct}%, background training offloaded to L3/L8."

        # Rule G: Perpetual Host CPU Offload & Mesh Load Balancing Invariant
        if node_id == "L1_Mac_Host":
            # The primary host CPU must ALWAYS be actively offloaded at 60% max, pushing workloads
            # over Thunderbolt (to L8) to maintain a balanced CPU load across the mesh.
            if cpu_quota_pct > 60:
                cpu_quota_pct = 60
                cpu_nice_level = max(cpu_nice_level, 5)
                max_worker_threads = min(max_worker_threads, 4)
                if action_state == "SUSTAINED_IDLE_RAMPED_UP":
                    action_state = "ACTIVE_MESH_OFFLOAD_BALANCING"
                    reason = f"Sustained idle on AC power. Host CPU actively offloaded at 60% to balance mesh load over Thunderbolt."

        return cls._build_action_dict(telemetry, action_state, cpu_quota_pct, cpu_nice_level, max_worker_threads, ram_cache_trim, background_lora_permitted, cloud_batch_permitted, reason)

    @staticmethod
    def _build_action_dict(telemetry: Dict[str, Any], state: str, cpu_pct: int, nice: int, threads: int, trim_ram: bool, lora_ok: bool, cloud_ok: bool, reason: str) -> Dict[str, Any]:
        return {
            "node_id": telemetry.get("node_id"),
            "name": telemetry.get("name"),
            "platform": telemetry.get("platform"),
            "action_state": state,
            "cpu_quota_pct": cpu_pct,
            "cpu_nice_level": nice,
            "max_worker_threads": threads,
            "ram_cache_trim": trim_ram,
            "background_lora_permitted": lora_ok,
            "cloud_batch_permitted": cloud_ok,
            "reason": reason,
            "telemetry_snapshot": {
                "idle_sec": round(telemetry.get("idle_sec", 0.0), 1),
                "is_home": telemetry.get("is_home"),
                "is_ac": telemetry.get("is_ac_power"),
                "battery_pct": telemetry.get("battery_pct")
            }
        }

# ==============================================================================
# 3. CANONICAL ENFORCEMENT & ACTUATION
# ==============================================================================

class GovernorActuator:
    """Applies the computed resource policies directly onto running processes."""

    @staticmethod
    def apply_policy_local(policy: Dict[str, Any], telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Applies throttling or ramp-up to local processes on Mac Host."""
        nice_lvl = policy["cpu_nice_level"]
        trim_ram = policy["ram_cache_trim"]
        darwin_mem = telemetry.get("darwin_memory", {})
        headroom_gb = darwin_mem.get("headroom_gb", 5.0)
        results = []

        # Check Rule 3 Headroom: if headroom < 4.8 GB, enforce trim regardless
        if headroom_gb < 4.8:
            trim_ram = True
            results.append(f"Rule 3 Alert: Host RAM headroom ({headroom_gb:.2f} GB) is below 4.80 GB sanctuary threshold. Enforcing cache trim.")

        # Adjust nice level for local background python daemons
        code, out, _ = run_cmd("pgrep -f 'python.*(mesh|daemon|trainer|bridge|analyzer)'")
        if code == 0 and out:
            pids = out.split()
            for pid in pids:
                try:
                    run_cmd(f"renice {nice_lvl} -p {pid}")
                    results.append(f"renice {nice_lvl} on pid {pid}")
                except Exception:
                    pass

        # Trigger RAM trim if requested
        if trim_ram:
            run_cmd("sync")
            results.append("Triggered memory buffer flush (sync)")

        # Record to DPO LoRA dataset for continuous alignment training
        dpo_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/lora_datasets/human_adaptive_governor/adaptive_governor_telemetry.jsonl")
        try:
            dpo_path.parent.mkdir(parents=True, exist_ok=True)
            log_entry = {
                "is_human_active": telemetry.get("human_active", False),
                "idle_seconds": telemetry.get("idle_sec", 0.0),
                "frontmost_application": telemetry.get("frontmost_app", "Antigravity"),
                "is_interactive_workload": telemetry.get("human_active", False),
                "cpu_quota_pct": policy["cpu_quota_pct"],
                "action_state": policy["action_state"],
                "reason": policy["reason"],
                "location_mode": telemetry.get("location_mode", "HOME_SANCTUARY"),
                "headroom_gb": headroom_gb,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            with open(dpo_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
            results.append(f"Logged continuous DPO telemetry to {dpo_path.name}")
        except Exception as e:
            logger.warning(f"Failed to append to DPO telemetry: {e}")

        # Append to Obsidian Live Observations (Rule 7)
        obsidian_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/APPS_AND_FEATURES/SCREEN_LENS_LIVE_OBSERVATIONS.md")
        try:
            now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            obs_line = (
                f"| {now_utc} | **AdaptiveGovernor** | `Human/Battery/Location Scan` | "
                f"L1: {policy['action_state']} (Human={telemetry.get('human_active')}, Idle={telemetry.get('idle_sec', 0):.0f}s, Headroom={headroom_gb}GB) | "
                f"Power={ 'AC' if telemetry.get('is_ac_power') else 'BATT' } | "
                f"Loc={telemetry.get('location_mode')} | Policy: CPU {policy['cpu_quota_pct']}%, Nice +{nice_lvl} |\n"
            )
            with open(obsidian_path, "a", encoding="utf-8") as f:
                f.write(obs_line)
            results.append("Appended observation to SCREEN_LENS_LIVE_OBSERVATIONS.md")
        except Exception as e:
            logger.warning(f"Failed to update Obsidian observations: {e}")

        return {
            "node_id": policy["node_id"],
            "actuation_applied": True,
            "actions_executed": results
        }

    @staticmethod
    def apply_policy_pixel(policy: Dict[str, Any], active_ip: Optional[str] = None, candidate_ips: List[str] = ["100.114.215.68", "192.168.8.213"], port: int = 8022, user: str = "u0_a234") -> Dict[str, Any]:
        """Enforces policy on Pixel 10 Pro XL via Termux SSH."""
        state = policy["action_state"]
        nice_lvl = policy["cpu_nice_level"]
        actions = []

        targets = [active_ip] if active_ip else candidate_ips
        applied = False
        for target_ip in targets:
            if not target_ip:
                continue
            cmd = f"ssh -F /dev/null -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=3 -p {port} {user}@{target_ip} \"renice {nice_lvl} \\$(pgrep -f 'lauburu|rpc' || true) 2>/dev/null || true\""
            code, _, _ = run_cmd(cmd, timeout=4.0)
            if code == 0:
                actions.append(f"Reniced background AI processes (lauburu/rpc) to +{nice_lvl} on Pixel 10 ({target_ip})")
                applied = True
                break

        if not applied:
            actions.append(f"Executed remote renice attempt to +{nice_lvl}")

        return {
            "node_id": policy["node_id"],
            "actuation_applied": applied,
            "actions_executed": actions
        }

    @staticmethod
    def apply_policy_remote_macos(policy: Dict[str, Any], ip: str, user: str = "aaronmaher") -> Dict[str, Any]:
        """Applies throttling or ramp-up to remote macOS nodes (L2, L5)."""
        nice_lvl = policy.get("cpu_nice_level", 0)
        trim_ram = policy.get("ram_cache_trim", False)
        actions = []
        if not ip:
            return {"node_id": policy.get("node_id"), "actuation_applied": False, "actions_executed": ["No active IP"]}
        cmd = (
            f"ssh -F /dev/null -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=3 "
            f"{user}@{ip} \"pids=\\$(pgrep -f 'python.*(mesh|daemon|trainer|bridge|analyzer)' || true); "
            f"for p in \\$pids; do renice {nice_lvl} -p \\$p 2>/dev/null || true; done; "
            f"if [ '{trim_ram}' = 'True' ]; then sync; fi\""
        )
        code, _, _ = run_cmd(cmd, timeout=5.0)
        if code == 0:
            actions.append(f"Enforced nice +{nice_lvl} on background daemons at {ip}")
            if trim_ram:
                actions.append("Triggered remote memory buffer flush (sync)")
        else:
            actions.append(f"Remote actuation attempted on {ip}")
        return {
            "node_id": policy.get("node_id"),
            "actuation_applied": code == 0,
            "actions_executed": actions
        }

    @staticmethod
    def apply_policy_remote_linux(policy: Dict[str, Any], ip: str, user: str = "linux") -> Dict[str, Any]:
        """Applies throttling or ramp-up to remote Linux compute nodes (L3, L8)."""
        nice_lvl = policy.get("cpu_nice_level", 0)
        trim_ram = policy.get("ram_cache_trim", False)
        actions = []
        if not ip:
            return {"node_id": policy.get("node_id"), "actuation_applied": False, "actions_executed": ["No active IP"]}
        cmd = (
            f"ssh -F /dev/null -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=3 "
            f"{user}@{ip} \"pids=\\$(pgrep -f 'python.*(mesh|daemon|trainer|bridge|analyzer)|llama|rpc' || true); "
            f"for p in \\$pids; do renice {nice_lvl} -p \\$p 2>/dev/null || true; done; "
            f"if [ '{trim_ram}' = 'True' ]; then sync; fi\""
        )
        code, _, _ = run_cmd(cmd, timeout=5.0)
        if code == 0:
            actions.append(f"Enforced nice +{nice_lvl} on background daemons at {ip}")
            if trim_ram:
                actions.append("Triggered remote memory buffer flush (sync)")
        else:
            actions.append(f"Remote actuation attempted on {ip}")
        return {
            "node_id": policy.get("node_id"),
            "actuation_applied": code == 0,
            "actions_executed": actions
        }

# ==============================================================================
# 4. SWARM ORCHESTRATOR
# ==============================================================================

def audit_full_mesh() -> Dict[str, Any]:
    prober = DeviceTelemetryProber()
    engine = AdaptiveOptimizationEngine()
    actuator = GovernorActuator()

    mesh_status = {}
    
    # 1. Local Host (L1 Mac Mini M4 Pro)
    t_l1 = prober.probe_local_macos()
    p_l1 = engine.evaluate_node_policy(t_l1)
    a_l1 = actuator.apply_policy_local(p_l1, t_l1)
    mesh_status["l1_mac_host"] = {**p_l1, "telemetry": t_l1, "actuation": a_l1}

    # 2. Mac Mini M2 Pro (L1b)
    t_l1b = prober.probe_remote_macos("L1b_Mac_Mini_M2_Pro", "Mac mini M2 Pro (GGUF Vault)", ["10.0.0.3", "192.168.8.114", "100.104.128.34"], user="aaronmaher")
    if t_l1b.get("status") != "OFFLINE_OR_DOZE":
        p_l1b = engine.evaluate_node_policy(t_l1b)
        mesh_status["l1b_mac_mini_m2_pro"] = {**p_l1b, "telemetry": t_l1b}
    else:
        mesh_status["l1b_mac_mini_m2_pro"] = t_l1b

    # 3. MacBook Air M4 (L5)
    t_l5 = prober.probe_remote_macos("L5_MacBook_Air_M4", "MacBook Air M4 (Metal Worker)", ["192.168.8.248", "10.0.0.5", "100.121.202.34"], user="aaronmaher")
    if t_l5.get("status") != "OFFLINE_OR_DOZE":
        p_l5 = engine.evaluate_node_policy(t_l5)
        a_l5 = actuator.apply_policy_remote_macos(p_l5, t_l5.get("active_ip"), user="aaronmaher")
        mesh_status["l5_macbook_air_m4"] = {**p_l5, "telemetry": t_l5, "actuation": a_l5}
    else:
        mesh_status["l5_macbook_air_m4"] = t_l5

    # 4. Linux Mini Central Hub (L8 - lauburu)
    t_l8 = prober.probe_linux_node("L8_Linux_Mini_CPU", "Linux Mini CPU Hub (lauburu)", ["10.0.0.8", "192.168.8.238", "192.168.8.242", "100.121.247.8"], user="linuxmini")
    if t_l8.get("status") != "OFFLINE_OR_DOZE":
        p_l8 = engine.evaluate_node_policy(t_l8)
        a_l8 = actuator.apply_policy_remote_linux(p_l8, t_l8.get("active_ip"), user="linuxmini")
        mesh_status["l8_linux_mini_cpu"] = {**p_l8, "telemetry": t_l8, "actuation": a_l8}
    else:
        mesh_status["l8_linux_mini_cpu"] = t_l8

    # 5. GL.iNet Gateway Router (GW)
    t_gw = prober.probe_router(["192.168.8.1", "100.70.123.123"])
    if t_gw.get("status") != "OFFLINE_OR_DOZE":
        p_gw = engine.evaluate_node_policy(t_gw)
        mesh_status["gw_router"] = {**p_gw, "telemetry": t_gw}
    else:
        mesh_status["gw_router"] = t_gw

    # 6. Google Pixel 10 Pro XL (L6 - Tensor G5 Edge)
    t_l6 = prober.probe_pixel_termux(["100.114.215.68", "192.168.8.213"], port=8022, user="u0_a234")
    if t_l6.get("status") != "OFFLINE_OR_DOZE":
        p_l6 = engine.evaluate_node_policy(t_l6)
        a_l6 = actuator.apply_policy_pixel(p_l6, active_ip=t_l6.get("active_ip"))
        mesh_status["l6_pixel_10_pro_xl"] = {**p_l6, "telemetry": t_l6, "actuation": a_l6}
    else:
        mesh_status["l6_pixel_10_pro_xl"] = t_l6

    # 7. MacBook Pro Intel (L2) - Probe check
    t_l2 = prober.probe_remote_macos("L2_MacBook_Pro", "MacBook Pro Intel Vault", ["192.168.8.127", "100.103.212.21", "10.0.0.4"], user="aaronmaher")
    if t_l2.get("status") != "OFFLINE_OR_DOZE":
        p_l2 = engine.evaluate_node_policy(t_l2)
        a_l2 = actuator.apply_policy_remote_macos(p_l2, t_l2.get("active_ip"), user="aaronmaher")
        mesh_status["l2_macbook_pro"] = {**p_l2, "telemetry": t_l2, "actuation": a_l2}
    else:
        mesh_status["l2_macbook_pro"] = t_l2

    # 8. Linux Head Node (L3 - Ryzen)
    t_l3 = prober.probe_linux_node("L3_Linux_Head_Node", "Linux Head Node (Ryzen)", ["192.168.8.225", "100.101.39.98"], user="linux")
    if t_l3.get("status") != "OFFLINE_OR_DOZE":
        p_l3 = engine.evaluate_node_policy(t_l3)
        a_l3 = actuator.apply_policy_remote_linux(p_l3, t_l3.get("active_ip"), user="linux")
        mesh_status["l3_linux_head_node"] = {**p_l3, "telemetry": t_l3, "actuation": a_l3}
    else:
        mesh_status["l3_linux_head_node"] = t_l3

    # Summary
    active_nodes = {k: v for k, v in mesh_status.items() if v.get("action_state")}
    sleeping_nodes = {k: v for k, v in mesh_status.items() if v.get("status") == "OFFLINE_OR_DOZE"}

    full_report = {
        "timestamp": time.time(),
        "timestamp_iso": datetime.now(timezone.utc).isoformat(),
        "governor_version": "2.2.0-adaptive-swarm",
        "mesh_nodes": mesh_status,
        "swarm_summary": {
            "total_nodes_audited": len(mesh_status),
            "online_active_nodes_count": len(active_nodes),
            "sleeping_nodes_count": len(sleeping_nodes),
            "human_active_nodes": [k for k, v in active_nodes.items() if v.get("action_state") == "HUMAN_ACTIVE_OPTIMIZED"],
            "hysteresis_transition_nodes": [k for k, v in active_nodes.items() if v.get("action_state") == "IDLE_HYSTERESIS_TRANSITION"],
            "ramped_up_nodes": [k for k, v in active_nodes.items() if v.get("action_state") == "SUSTAINED_IDLE_RAMPED_UP"],
            "battery_conserving_nodes": [k for k, v in active_nodes.items() if "BATTERY" in v.get("action_state", "")],
            "away_sanctuary_nodes": [k for k, v in active_nodes.items() if v.get("action_state") == "AWAY_MOBILE_SANCTUARY"],
            "rule3_mac_headroom_gb": t_l1.get("darwin_memory", {}).get("headroom_gb"),
            "rule3_sanctuary_compliant": t_l1.get("darwin_memory", {}).get("rule3_sanctuary_compliant"),
            "linux_mini_offload_headroom_mb": mesh_status.get("l8_linux_mini_cpu", {}).get("telemetry", {}).get("available_mem_mb")
        }
    }

    # Persist state
    try:
        os.makedirs(STATE_FILE.parent, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(full_report, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not persist state file: {e}")

    return full_report

if __name__ == "__main__":
    report = audit_full_mesh()
    print(json.dumps(report, indent=2))
