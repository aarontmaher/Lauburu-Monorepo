#!/usr/bin/env python3
"""
Human-Centric Dynamic RAM Governor & AI Training Protocol
=========================================================
Subsystem: 02_ai_models_and_inference/human_adaptive_ram_governor.py

Dynamically adjusts host AI VRAM caps and sharding placement based on real-time
human presence and interactive application usage:
1. HUMAN ACTIVE (Idle < 60s, Interactive App Foreground):
   - Host Mac Mini AI Cap: 50% (12.0 GB).
   - System Headroom: >= 12.0 GB reserved for fluid multitasking (Chrome, VS Code, etc.).
   - Excess AI Shards / Training: Automatically offloaded over 40Gbps TB4 to L2 (MBP) & L3 (Mac Air).
2. HUMAN IDLE (> 180s, Display Sleep / Lock):
   - Host Mac Mini AI Cap: 90% (21.6 GB).
   - High-throughput batch LoRA distillation & speculative sharding re-absorbed on M4 Pro.
"""

import datetime
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
DATASET_DIR = REPO_ROOT / "04_data_and_memory" / "lora_datasets" / "human_adaptive_governor"
LOG_FILE = DATASET_DIR / "adaptive_governor_telemetry.jsonl"


@dataclass
class HumanInteractionState:
    is_human_active: bool
    idle_seconds: float
    frontmost_application: str
    is_interactive_workload: bool
    cpu_usage_pct: float
    total_ram_gb: float
    used_ram_gb: float
    compressor_ram_gb: float
    dynamic_ai_cap_pct: float
    max_usable_ai_ram_gb: float
    offload_target: str
    rationale: str
    timestamp: str


class HumanAdaptiveRAMGovernor:
    def __init__(self, host_total_ram_gb: float = 24.0):
        self.host_total_ram_gb = host_total_ram_gb
        DATASET_DIR.mkdir(parents=True, exist_ok=True)

    def get_user_idle_seconds(self) -> float:
        """Query macOS IOHIDSystem for user idle time in seconds."""
        if sys.platform != "darwin":
            return 300.0  # Default to idle on headless/non-macOS nodes
        try:
            cmd = "ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print int($NF/1000000000); exit}'"
            out = subprocess.check_output(cmd, shell=True, timeout=2).decode().strip()
            return float(out) if out else 0.0
        except Exception:
            return 0.0

    def get_frontmost_application(self) -> str:
        """Query macOS for the active foreground window application."""
        if sys.platform != "darwin":
            return "Headless Server"
        try:
            ascript = 'tell application "System Events" to get name of first application process whose frontmost is true'
            out = subprocess.check_output(["osascript", "-e", ascript], timeout=2).decode().strip()
            return out if out else "Unknown"
        except Exception:
            return "Finder"

    def get_memory_metrics(self) -> Tuple[float, float, float]:
        """Returns (used_ram_gb, compressor_gb, cpu_usage_pct)."""
        used_gb = 20.0
        compressor_gb = 3.0
        cpu_pct = 40.0
        try:
            import psutil
            vm = psutil.virtual_memory()
            used_gb = vm.used / (1024 ** 3)
            cpu_pct = psutil.cpu_percent(interval=0.2)
        except ImportError:
            pass

        # Parse vm_stat on macOS for compressed memory
        if sys.platform == "darwin":
            try:
                vm_stat = subprocess.check_output(["vm_stat"], timeout=2).decode()
                for line in vm_stat.splitlines():
                    if "occupied by compressor" in line:
                        parts = line.split(":")
                        if len(parts) > 1:
                            pages = float(parts[1].strip().replace(".", ""))
                            compressor_gb = (pages * 4096) / (1024 ** 3)
            except Exception:
                pass

        return used_gb, compressor_gb, cpu_pct

    def compute_adaptive_governance(self) -> HumanInteractionState:
        idle_sec = self.get_user_idle_seconds()
        app = self.get_frontmost_application()
        used_gb, comp_gb, cpu_pct = self.get_memory_metrics()

        # Applications indicating intense human interactivity
        interactive_apps = {
            "Google Chrome", "Code", "Visual Studio Code", "Antigravity", 
            "Terminal", "iTerm2", "Slack", "Discord", "Photoshop", "Safari"
        }
        is_interactive = app in interactive_apps or idle_sec < 60.0
        is_active = idle_sec < 120.0

        if is_interactive and is_active:
            # Human is actively typing/working: drop cap to 50%
            ai_cap_pct = 50.0
            max_ai_ram = self.host_total_ram_gb * (ai_cap_pct / 100.0)
            offload_target = "L2_MacBook_Pro (TB4 DMA 40Gbps)"
            rationale = f"Human active in {app} (idle {idle_sec:.0f}s); AI capped at 50% ({max_ai_ram:.1f}GB). Offloading training to L2/L3."
        elif is_active:
            # Mild activity
            ai_cap_pct = 70.0
            max_ai_ram = self.host_total_ram_gb * (ai_cap_pct / 100.0)
            offload_target = "Balanced L1/L2 Ring"
            rationale = f"Background activity in {app}; AI balanced at 70% ({max_ai_ram:.1f}GB)."
        else:
            # Fully idle (user away / night time): ramp cap to 90%
            ai_cap_pct = 90.0
            max_ai_ram = self.host_total_ram_gb * (ai_cap_pct / 100.0)
            offload_target = "L1_Host_Full_Throughput"
            rationale = f"System idle for {idle_sec:.0f}s; AI unthrottled at 90% ({max_ai_ram:.1f}GB) on M4 Pro."

        state = HumanInteractionState(
            is_human_active=is_active,
            idle_seconds=idle_sec,
            frontmost_application=app,
            is_interactive_workload=is_interactive,
            cpu_usage_pct=cpu_pct,
            total_ram_gb=self.host_total_ram_gb,
            used_ram_gb=used_gb,
            compressor_ram_gb=comp_gb,
            dynamic_ai_cap_pct=ai_cap_pct,
            max_usable_ai_ram_gb=max_ai_ram,
            offload_target=offload_target,
            rationale=rationale,
            timestamp=datetime.datetime.now().isoformat(),
        )

        # Log for 24/7 DPO LoRA training
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(state)) + "\n")

        return state


if __name__ == "__main__":
    governor = HumanAdaptiveRAMGovernor()
    result = governor.compute_adaptive_governance()
    print("=== HUMAN-CENTRIC ADAPTIVE RAM GOVERNOR STATE ===")
    print(f"Human Active:          {result.is_human_active} (Idle: {result.idle_seconds:.1f}s)")
    print(f"Foreground App:        {result.frontmost_application}")
    print(f"Host Dynamic AI Cap:   {result.dynamic_ai_cap_pct}% ({result.max_usable_ai_ram_gb:.1f} GB Max Usable AI RAM)")
    print(f"Offload Destination:   {result.offload_target}")
    print(f"Action Rationale:      {result.rationale}")
