#!/usr/bin/env python3
"""
================================================================================
Lauburu Universal Device Mesh Runner & Hardware-Tailored Edge Daemon
================================================================================
Subsystem: 06_scripts_and_tooling/automation/universal_device_mesh_runner.py
Version: 1.0.0-UNIVERSAL-DEVICE-RUNNER
Lauburu Mesh Ecosystem — 2026

Runs natively on ANY of the 8 mesh nodes (macOS, Linux, Android/Termux, OpenWrt):
- Automatically fingerprints local device hardware and role (L1-L7, GW).
- Applies tailored profile:
  • L1 (Mac Mini M4 Pro): 16-Core ANE (38 TOPS), Metal GPU, Prima Master (:8082), Coder (:8081).
  • L2 (MacBook Pro 16): Intel x86_64, 285 GB SSD Vault, AMD GPU Metal RPC, TB4 DMA.
  • L3 (Linux Head Node): Ryzen 7 5700U, Docker Hub & Ray Engine.
  • L4 (Linux Tablet): Debian Linux Tablet, lightweight touch compute.
  • L5 (MacBook Air M4): Apple Silicon M4 Metal worker & secondary vault.
  • L6 (Pixel 10 Pro XL): Google Tensor G5 (TSMC 3nm), 18-20 TOPS TPU, 16MB SRAM, SVE2, Android 15.
  • L7 (Samsung S20+): Exynos 990 (12GB RAM), Shizuku Manager, Termux ADB tester.
  • GW (GL.iNet Router): OpenWrt Linux 5.4 aarch64, tmpfs only, Wi-Fi 7 MLO.
- Checks local health before starting daemons (avoids redundant re-installation).
- Writes real-time edge state to /tmp or local Termux directory.
================================================================================
"""

import os
import sys
import time
import json
import socket
import platform
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

HOST_MAC_MINI_IP = "100.119.199.76"
ROUTER_GW_IP = "192.168.8.1"


def detect_device_profile() -> Dict[str, Any]:
    """Inspects kernel syscalls, props, and system identifiers to identify device."""
    sys_name = platform.system().lower()
    machine = platform.machine().lower()
    node_name = platform.node()

    # 1. Android Detection
    is_android = "android" in sys_name or os.path.exists("/system/build.prop") or "termux" in os.environ.get("PREFIX", "")
    if is_android:
        model = ""
        try:
            r = subprocess.run(["getprop", "ro.product.model"], capture_output=True, text=True, timeout=2.0)
            model = r.stdout.strip()
        except Exception:
            pass

        if "pixel" in model.lower() or "tokay" in model.lower() or "tensor" in model.lower():
            return {
                "layer": "L6",
                "device_id": "Pixel_10_Pro_XL",
                "os": "Android 15",
                "hardware": "Google Tensor G5 (TSMC 3nm N3P)",
                "compute_engine": "18-20 TOPS Edge TPU (16MB SRAM) + ARMv8 SVE2",
                "state_dir": str(Path.home() / "pixel_edge_state.json")
            }
        elif "sm-g986" in model.lower() or "s20" in model.lower():
            return {
                "layer": "L7",
                "device_id": "Samsung_S20",
                "os": "Android",
                "hardware": "Samsung Exynos 990 (12GB RAM)",
                "compute_engine": "Exynos NPU + Mali-G77 GPU",
                "state_dir": str(Path.home() / "s20_edge_state.json")
            }
        else:
            return {
                "layer": "L6/L7",
                "device_id": f"Android_Device_{model or 'Unknown'}",
                "os": "Android",
                "hardware": model,
                "compute_engine": "Mobile NPU / SVE",
                "state_dir": str(Path.home() / "android_edge_state.json")
            }

    # 2. OpenWrt Router Detection
    if os.path.exists("/etc/openwrt_release"):
        return {
            "layer": "GW",
            "device_id": "GL_iNet_Router",
            "os": "OpenWrt Linux 5.4",
            "hardware": "GL-MT3600BE Beryl 7 (MediaTek Filogic 820)",
            "compute_engine": "ARMv8 NEON SIMD (tmpfs strictly)",
            "state_dir": "/tmp/router_edge_state.json"
        }

    # 3. macOS Detection
    if sys_name == "darwin":
        hw_model = ""
        try:
            r = subprocess.run(["sysctl", "-n", "hw.model"], capture_output=True, text=True, timeout=2.0)
            hw_model = r.stdout.strip()
        except Exception:
            pass

        if "Mac16,11" in hw_model or ("Macmini" in hw_model and "Mac16" in hw_model):
            return {
                "layer": "L1",
                "device_id": "Mac_Mini_M4_Pro",
                "os": "macOS (Darwin)",
                "hardware": "Apple M4 Pro Mac Mini (24GB RAM, Mac16,11)",
                "compute_engine": "Apple Silicon 16-Core ANE (38 TOPS) + 16-Core Metal GPU",
                "state_dir": "/tmp/lauburu_host_edge_state.json"
            }
        elif "Mac16,12" in hw_model or "MacBookAir" in hw_model:
            return {
                "layer": "L1a",
                "device_id": "MacBook_Air_M4",
                "os": "macOS (Darwin)",
                "hardware": "Apple M4 MacBook Air (16GB RAM, Mac16,12)",
                "compute_engine": "Apple M4 Metal GPU + ANE Distillation Worker",
                "state_dir": "/tmp/mba_edge_state.json"
            }
        elif "Mac14" in hw_model or "Mac14,12" in hw_model:
            return {
                "layer": "L1b",
                "device_id": "Mac_Mini_M2_Pro",
                "os": "macOS (Darwin)",
                "hardware": "Apple M2 Pro Mac Mini (16GB RAM, Mac14,12)",
                "compute_engine": "Apple Silicon Metal GPU + ANE (40 Gb/s TB4 Fabric)",
                "state_dir": "/tmp/m2_edge_state.json"
            }
        elif "MacBookPro" in hw_model:
            return {
                "layer": "L2",
                "device_id": "MacBook_Pro_16",
                "os": "macOS (Darwin)",
                "hardware": "Intel Core i7-9750H, 16GB RAM, AMD GPU (MacBookPro16,1)",
                "compute_engine": "x86_64 AVX2 + AMD Metal GPU + 40G TB4 DMA",
                "state_dir": "/tmp/mbp_edge_state.json"
            }
        else:
            return {
                "layer": "L1/L2/L1a",
                "device_id": f"Mac_{hw_model}",
                "os": "macOS",
                "hardware": hw_model,
                "compute_engine": "Metal GPU",
                "state_dir": "/tmp/mac_generic_edge_state.json"
            }

    # 4. Linux Detection
    if sys_name == "linux":
        if "lauburu" in node_name.lower():
            return {
                "layer": "L8",
                "device_id": "Linux_Mini_Hub",
                "os": "Ubuntu Linux 24.04 (Linux 6.8)",
                "hardware": "Intel Corp x86_64 (12 Cores, 32GB RAM)",
                "compute_engine": "TB4 40Gb/s Bridge + First-Offload Ray Engine",
                "state_dir": "/tmp/lauburu_hub_edge_state.json"
            }
        elif "debian" in node_name.lower():
            return {
                "layer": "L4",
                "device_id": "Debian_AVF_MicroVM",
                "os": "Debian Linux 13 (pKVM)",
                "hardware": "Tensor G5 AVF MicroVM (10.5GB RAM)",
                "compute_engine": "Cortex-X4/A725 ARMv8 SVE2 MicroVM",
                "state_dir": "/tmp/debian_avf_edge_state.json"
            }
        elif "tablet" in node_name.lower():
            return {
                "layer": "L4",
                "device_id": "Linux_Tablet",
                "os": "Debian Linux",
                "hardware": "Linux Tablet (8GB RAM)",
                "compute_engine": "Touch DSP Compute",
                "state_dir": "/tmp/tablet_edge_state.json"
            }
        else:
            return {
                "layer": "L3",
                "device_id": "Linux_Head_Node",
                "os": "Linux x86_64/aarch64",
                "hardware": "AMD Ryzen 7 5700U (16GB RAM)",
                "compute_engine": "Docker Hub & Ray Engine (Xvfb :99)",
                "state_dir": "/tmp/linux_head_edge_state.json"
            }

    return {
        "layer": "UNKNOWN",
        "device_id": node_name,
        "os": sys_name,
        "hardware": machine,
        "compute_engine": "Standard CPU",
        "state_dir": "/tmp/generic_edge_state.json"
    }


def probe_ping(ip: str, timeout_ms: int = 400) -> Tuple[bool, float]:
    """Lightweight ICMP ping."""
    t0 = time.perf_counter()
    try:
        cmd = ["ping", "-c", "1", "-W", str(timeout_ms // 1000 if platform.system().lower() != "darwin" else timeout_ms), ip]
        r = subprocess.run(cmd, capture_output=True, timeout=0.5)
        rtt = (time.perf_counter() - t0) * 1000.0
        return (r.returncode == 0), round(rtt, 2)
    except Exception:
        return False, 999.0


def probe_tcp(host: str, port: int, timeout_sec: float = 0.3) -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout_sec)
        res = s.connect_ex((host, port))
        s.close()
        return res == 0
    except Exception:
        return False


def run_device_tailored_cycle(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Executes the specialized autonomous cycle for the detected device."""
    layer = profile["layer"]
    t0 = time.perf_counter()
    actions_taken = []

    # 1. Android Keepalive & Shizuku (L6 Pixel & L7 S20)
    if "Android" in profile["os"]:
        try:
            subprocess.run(["termux-wake-lock"], capture_output=True)
            actions_taken.append("TERMUX_WAKELOCK_LOCKED")
        except Exception:
            pass

        # Check/start sshd on port 8022
        if not probe_tcp("127.0.0.1", 8022):
            try:
                subprocess.Popen(["sshd"])
                actions_taken.append("SSHD_RESTARTED_8022")
            except Exception:
                pass
        else:
            actions_taken.append("SSHD_HEALTHY_8022")

        # Check/start Movesense Standalone Readiness & TinyML Engine on port 8086
        movesense_main = Path.home() / "movesense-readiness" / "main.py"
        if movesense_main.exists():
            if not probe_tcp("127.0.0.1", 8086):
                try:
                    tmux_bin = shutil.which("tmux")
                    if tmux_bin:
                        subprocess.run(
                            [tmux_bin, "new-session", "-d", "-s", "movesense-hub", f"{sys.executable} {movesense_main}"],
                            check=False
                        )
                    else:
                        subprocess.Popen(
                            [sys.executable, str(movesense_main)],
                            cwd=str(movesense_main.parent),
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                    actions_taken.append("MOVESENSE_STANDALONE_RESTARTED_8086")
                except Exception:
                    pass
            else:
                actions_taken.append("MOVESENSE_STANDALONE_HEALTHY_8086")

        # Shizuku activation check
        shizuku_starter = Path("/storage/emulated/0/Android/data/moe.shizuku.privileged.api/starter")
        if shizuku_starter.exists():
            try:
                subprocess.run(["sh", "/sdcard/Android/data/moe.shizuku.privileged.api/start.sh"], capture_output=True, timeout=3.0)
                actions_taken.append("SHIZUKU_STARTER_TRIGGERED")
            except Exception:
                pass

    # 2. Connectivity to Mesh Host & Gateway
    host_ok, host_rtt = probe_ping(HOST_MAC_MINI_IP)
    gw_ok, gw_rtt = probe_ping(ROUTER_GW_IP)

    # 3. Memory & System Metrics
    mem_free_mb = 0
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if "MemAvailable:" in line:
                    mem_free_mb = int(line.split()[1]) // 1024
                    break
    except Exception:
        pass

    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    # 4. Check for NPU Continuous Training Regulation state
    reg_file = Path("/tmp/neo_npu_training_regulator.json")
    training_reg = {}
    if reg_file.exists():
        try:
            training_reg = json.loads(reg_file.read_text())
        except Exception:
            pass

    state = {
        "status": "OPERATIONAL",
        "timestamp": time.time(),
        "cycle_duration_ms": round(elapsed_ms, 2),
        "device_profile": profile,
        "actions_taken": actions_taken,
        "mesh_connectivity": {
            "mac_mini_host": {"linked": host_ok, "rtt_ms": host_rtt},
            "router_gateway": {"linked": gw_ok, "rtt_ms": gw_rtt}
        },
        "system_headroom": {
            "mem_free_mb": mem_free_mb
        },
        "continuous_training_regulation": {
            "action": training_reg.get("regulation_action", "N/A"),
            "compute_allocation_pct": training_reg.get("compute_allocation_pct", 50.0),
            "target_batch_size": training_reg.get("target_batch_size", 16),
            "user_state": training_reg.get("user_state", "N/A")
        }
    }

    # Save to local state file
    try:
        p = Path(profile["state_dir"])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state, indent=2))
    except Exception:
        pass

    return state


def main():
    profile = detect_device_profile()
    state = run_device_tailored_cycle(profile)
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
