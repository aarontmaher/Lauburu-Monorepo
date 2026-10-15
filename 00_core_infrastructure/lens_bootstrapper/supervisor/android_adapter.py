"""
00_core_infrastructure/lens_bootstrapper/supervisor/android_adapter.py
======================================================================
Android Edge TinyLM Adapter (Feature F8).

Adapts the Local Autonomous Healing Supervisor for Android AVF (Android
Virtualization Framework) Debian 13 microVMs and Termux environments on
Google Pixel 10 Pro XL (Tensor G5) and Samsung Galaxy S20 (Exynos 990).

Governed by Rule 9:
- AVF microVM memory residency capped at <= 3.5 GB ceiling.
- Static ARM64 NEON / TFLite C++ runner target < 110 MB RAM.
- Shizuku 2>&1 stderr redirection invariant on all non-interactive `rish` calls.
"""

from __future__ import annotations

import logging
import os
import platform
import re
import shlex
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("AndroidEdgeAdapter")


class AndroidEnvironment:
    """
    Detects and inspects the Android runtime environment:
    - Native Linux AVF Debian microVM under pKVM/crosvm (Google Tensor G5)
    - User-space Termux PRoot
    - Host memory limits enforcing AVF <= 3.5 GB ceiling (Rule 9 §3).
    """

    AVF_MAX_CEILING_BYTES: int = int(3.5 * 1024 * 1024 * 1024)  # 3.5 GB
    EDGE_RUNNER_MAX_RSS_BYTES: int = 110 * 1024 * 1024          # 110 MB

    def __init__(self, override_env: Optional[Dict[str, Any]] = None) -> None:
        self._override = override_env or {}

    def is_android(self) -> bool:
        """Determines if the current execution context is Android-based."""
        if "is_android" in self._override:
            return bool(self._override["is_android"])

        # Check Android indicators
        if os.environ.get("ANDROID_ROOT") or os.environ.get("TERMUX_VERSION"):
            return True
        if os.path.exists("/mnt/shared") or os.path.exists("/system/build.prop"):
            return True

        # Check kernel release string
        release = platform.release().lower()
        if "android" in release or "crosvm" in release:
            return True

        return False

    def is_avf_microvm(self) -> bool:
        """Determines if running inside an Android AVF pKVM microVM."""
        if "is_avf_microvm" in self._override:
            return bool(self._override["is_avf_microvm"])

        # AVF microVM mounts VirtioFS shared drive at /mnt/shared
        has_shared = os.path.exists("/mnt/shared")
        release = platform.release().lower()
        return has_shared or ("android" in release and os.path.exists("/etc/debian_version"))

    def is_termux(self) -> bool:
        """Determines if running inside Termux."""
        if "is_termux" in self._override:
            return bool(self._override["is_termux"])
        return bool(os.environ.get("TERMUX_VERSION") or "/data/data/com.termux" in os.environ.get("PREFIX", ""))

    def get_avf_memory_headroom(self) -> Dict[str, Any]:
        """
        Calculates memory stats inside the VM and enforces the 3.5 GB AVF ceiling.
        """
        total_mem = 0
        available_mem = 0

        # Read /proc/meminfo
        if os.path.exists("/proc/meminfo"):
            try:
                with open("/proc/meminfo", "r", encoding="utf-8") as f:
                    meminfo = {}
                    for line in f:
                        parts = line.split(":")
                        if len(parts) == 2:
                            k = parts[0].strip()
                            v = parts[1].strip().split()[0]
                            meminfo[k] = int(v) * 1024
                    total_mem = meminfo.get("MemTotal", 0)
                    available_mem = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
            except Exception as e:
                logger.debug(f"Failed to read /proc/meminfo: {e}")

        if total_mem == 0:
            # Baseline guest allocation for testing / simulation
            total_mem = int(3.5 * 1024 * 1024 * 1024)
            available_mem = int(2.2 * 1024 * 1024 * 1024)

        used_mem = max(0, total_mem - available_mem)
        within_avf_ceiling = used_mem <= self.AVF_MAX_CEILING_BYTES

        return {
            "total_bytes": total_mem,
            "used_bytes": used_mem,
            "available_bytes": available_mem,
            "avf_ceiling_bytes": self.AVF_MAX_CEILING_BYTES,
            "within_avf_ceiling": within_avf_ceiling,
            "used_gb": round(used_mem / (1024**3), 3),
            "available_gb": round(available_mem / (1024**3), 3),
            "ceiling_gb": round(self.AVF_MAX_CEILING_BYTES / (1024**3), 3),
        }


class AndroidEdgeTinyLMAdapter:
    """
    Edge adapter orchestrating TFLite C++ and static ARM64 NEON runners
    on Android Edge devices (L6 Pixel 10 Pro XL, L7 Galaxy S20).
    """

    def __init__(
        self,
        runner_type: str = "tflite_neon",
        model_path: Optional[str] = None,
        env: Optional[AndroidEnvironment] = None,
    ) -> None:
        self.runner_type = runner_type
        self.model_path = model_path or "/mnt/shared/models/smollm2_135m_q4.gguf"
        self.env = env or AndroidEnvironment()

    def build_shizuku_command(self, raw_command: str) -> str:
        """
        Rule 9 §2 Invariant:
        When executing non-interactive commands via Shizuku (`rish`), scripts
        MUST redirect stderr to stdout (`2>&1`). Never pipe `2>/dev/null`.
        Uses shlex.quote to prevent inner single quotes from breaking `rish -c`.
        """
        sanitized = raw_command.strip()
        # Disallow 2>/dev/null with any spacing variation
        sanitized = re.sub(r"2\s*>\s*/dev/null", "2>&1", sanitized)

        # Ensure 2>&1 is present
        if not re.search(r"2>&1\s*$", sanitized):
            sanitized = f"{sanitized} 2>&1"

        # Wrap in rish if not already
        if not sanitized.startswith("rish"):
            return f"rish -c {shlex.quote(sanitized)}"
        return sanitized

    def build_neon_runner_command(
        self,
        prompt: str,
        max_tokens: int = 64,
        threads: int = 4,
    ) -> List[str]:
        """
        Constructs the execution command for the static ARM64 NEON runner.
        Optimized for Google Tensor G5 CPU cores without AVF MMIO TPU passthrough.
        """
        cmd = [
            "llama-cli-neon",
            "-m", self.model_path,
            "-p", prompt,
            "-n", str(max_tokens),
            "-t", str(threads),
            "--temp", "0.7",
            "--top-p", "0.9",
            "--no-mmap",  # Enforce direct resident buffer for memory control
        ]
        return cmd

    def check_runner_memory_headroom(self, current_rss_bytes: int) -> Tuple[bool, str]:
        """
        Validates that the edge model runner satisfies the < 110 MB RSS target
        and respects the guest VM 3.5 GB ceiling.
        """
        if current_rss_bytes > self.env.EDGE_RUNNER_MAX_RSS_BYTES:
            rss_mb = current_rss_bytes / (1024 * 1024)
            limit_mb = self.env.EDGE_RUNNER_MAX_RSS_BYTES / (1024 * 1024)
            return False, f"Edge runner RSS {rss_mb:.1f} MB exceeds target {limit_mb:.1f} MB."

        mem_stats = self.env.get_avf_memory_headroom()
        if not mem_stats["within_avf_ceiling"]:
            return False, f"AVF VM memory {mem_stats['used_gb']} GB exceeds {mem_stats['ceiling_gb']} GB ceiling."

        return True, "Runner memory within safe edge thresholds."

    def diagnose_edge_anomaly(self, anomaly_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Produces edge diagnosis and local healing instructions for Android nodes.
        """
        start = time.perf_counter()
        down_ifaces = anomaly_data.get("down_interfaces", [])
        down_ports = anomaly_data.get("down_ports", [])

        # Shizuku/Termux specific recovery actions for all 5 canonical interfaces
        actions = []
        for iface in down_ifaces:
            if iface in ("wifi", "wlan0"):
                # Non-interactive command with 2>&1
                actions.append({
                    "target": iface,
                    "command": self.build_shizuku_command("svc wifi disable && sleep 1 && svc wifi enable"),
                })
            elif iface == "tailscale":
                actions.append({
                    "target": iface,
                    "command": self.build_shizuku_command("tailscale up --accept-routes 2>&1"),
                })
            elif iface == "nebula":
                actions.append({
                    "target": iface,
                    "command": self.build_shizuku_command("pkill -HUP nebula || nebula -config /mnt/shared/nebula/config.yml 2>&1"),
                })
            elif iface in ("tb4", "thunderbolt0", "bridge0"):
                actions.append({
                    "target": iface,
                    "command": self.build_shizuku_command("ip link set dev rndis0 up 2>&1 || ifconfig eth0 up 2>&1"),
                })
            elif iface in ("bluetooth_pan", "bnep0", "pan"):
                actions.append({
                    "target": iface,
                    "command": self.build_shizuku_command("svc bluetooth disable && sleep 1 && svc bluetooth enable 2>&1"),
                })
            else:
                actions.append({
                    "target": iface,
                    "command": self.build_shizuku_command(f"ifconfig {iface} up 2>&1"),
                })

        for port in down_ports:
            actions.append({
                "target": port,
                "command": f"pkill -f ':{port}' || true",
            })

        elapsed = max(0.001, time.perf_counter() - start)
        mem_info = self.env.get_avf_memory_headroom()

        return {
            "platform": "android_edge",
            "is_avf": self.env.is_avf_microvm(),
            "is_termux": self.env.is_termux(),
            "runner_type": self.runner_type,
            "actions": actions,
            "memory": mem_info,
            "latency_ms": round(elapsed * 1000.0, 2),
            "status": "DIAGNOSIS_COMPLETE",
        }
