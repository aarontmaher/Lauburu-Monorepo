#!/usr/bin/env python3
"""
High-Fidelity Mock Shizuku Device & Privileged IPC Simulator
============================================================
Simulates Android Shizuku Binder IPC / rish privileged shell execution,
providing deterministic state machines for Tailscale service restart,
atomic Wi-Fi toggling, Doze mode whitelist manipulation, TCP 5555 persistence,
and phantom process monitor disablement.
"""

import re
import shlex
import time
from typing import Dict, Any, List, Optional, Tuple


class MockShizukuDevice:
    """
    Stateful Android device simulator with Shizuku Binder IPC privileges.
    """

    def __init__(self, device_id: str = "pixel_10", is_root: bool = True):
        self.device_id = device_id
        self.is_root = is_root
        self.is_online = True
        self.shizuku_running = True
        self.wifi_enabled = True
        self.tailscale_installed = True
        self.tailscale_running = True
        self.adb_tcp_port = 5555
        self.doze_whitelist = {"com.termux", "com.tailscale.ipn"}
        self.phantom_procs_monitor_enabled = False
        self.battery_level = 85
        self.is_thermal_emergency = False
        self.running_pids: Dict[int, str] = {
            101: "com.tailscale.ipn",
            202: "com.termux",
            303: "uiautomator",
        }
        self.command_history: List[str] = []

    def execute_command(self, cmd: str, as_root: bool = False, timeout: float = 10.0) -> Tuple[int, str, str]:
        """
        Executes a shell command on the simulated Android device.
        Supports compound commands (&&, ;).
        Returns (exit_code, stdout, stderr).
        """
        self.command_history.append(cmd)

        if not self.is_online:
            return 1, "", "error: device offline (connection refused)"

        if not self.shizuku_running and as_root:
            return 127, "", "sh: rish: command not found (Shizuku service not running)"

        # Handle compound commands with &&
        if "&&" in cmd:
            subcmds = [c.strip() for c in cmd.split("&&")]
            full_out = []
            for sc in subcmds:
                code, out, err = self._execute_single_cmd(sc, as_root=as_root)
                if out:
                    full_out.append(out)
                if code != 0:
                    return code, "".join(full_out), err
            return 0, "".join(full_out), ""

        # Handle compound commands with ;
        if ";" in cmd and not ("'" in cmd or '"' in cmd):
            subcmds = [c.strip() for c in cmd.split(";")]
            full_out = []
            last_code = 0
            for sc in subcmds:
                if not sc:
                    continue
                code, out, err = self._execute_single_cmd(sc, as_root=as_root)
                last_code = code
                if out:
                    full_out.append(out)
            return last_code, "".join(full_out), ""

        return self._execute_single_cmd(cmd, as_root=as_root)

    def _execute_single_cmd(self, cmd: str, as_root: bool = False) -> Tuple[int, str, str]:
        clean_cmd = cmd.strip()

        # 1. Root / ID checks
        if clean_cmd in ["id", "whoami", "id -u"]:
            if as_root or self.is_root:
                return 0, "uid=0(root) gid=0(root) groups=0(root) context=u:r:su:s0\n", ""
            return 0, "uid=2000(shell) gid=2000(shell) groups=2000(shell)\n", ""

        # 2. Package Manager
        if "pm list packages" in clean_cmd:
            if "com.tailscale.ipn" in clean_cmd:
                if self.tailscale_installed:
                    return 0, "package:com.tailscale.ipn\n", ""
                return 0, "", ""
            return 0, "package:com.termux\npackage:com.tailscale.ipn\n", ""

        # 3. Activity Manager (am)
        if clean_cmd.startswith("am force-stop"):
            pkg = clean_cmd.split()[-1].strip("'\"")
            if "com.tailscale.ipn" in pkg:
                self.tailscale_running = False
                self.running_pids = {pid: name for pid, name in self.running_pids.items() if name != "com.tailscale.ipn"}
            return 0, "", ""

        if clean_cmd.startswith("am start"):
            if "com.tailscale.ipn" in clean_cmd:
                self.tailscale_running = True
                self.running_pids[105] = "com.tailscale.ipn"
                return 0, "Starting: Intent { act=android.intent.action.MAIN cmp=com.tailscale.ipn/.ui.MainActivity }\n", ""
            return 0, "Starting: Intent { act=android.intent.action.MAIN }\n", ""

        # 4. Service Wifi (svc wifi)
        if clean_cmd == "svc wifi enable":
            self.wifi_enabled = True
            return 0, "", ""
        if clean_cmd == "svc wifi disable":
            self.wifi_enabled = False
            return 0, "", ""

        # 5. Dumpsys Wifi
        if "dumpsys wifi" in clean_cmd:
            state_str = "Wi-Fi is enabled" if self.wifi_enabled else "Wi-Fi is disabled"
            return 0, f"Wi-Fi is currently running\n  {state_str}\n  IP: 192.168.8.150\n", ""

        # 6. Dumpsys DeviceIdle (Doze)
        if "dumpsys deviceidle whitelist" in clean_cmd:
            if "+" in clean_cmd:
                # Add to whitelist
                parts = clean_cmd.split("+")
                for p in parts[1:]:
                    pkg = p.strip().split()[0]
                    self.doze_whitelist.add(pkg)
                return 0, "Added to whitelist\n", ""
            if "-" in clean_cmd:
                # Remove from whitelist
                parts = clean_cmd.split("-")
                for p in parts[1:]:
                    pkg = p.strip().split()[0]
                    self.doze_whitelist.discard(pkg)
                return 0, "Removed from whitelist\n", ""
            # Query whitelist
            whitelist_out = "System whitelist:\n" + "\n".join([f"  {pkg}" for pkg in self.doze_whitelist]) + "\n"
            return 0, whitelist_out, ""

        # 7. Setprop ADB TCP
        if "setprop service.adb.tcp.port" in clean_cmd:
            port_match = re.search(r"setprop service\.adb\.tcp\.port\s+(\d+)", clean_cmd)
            if port_match:
                self.adb_tcp_port = int(port_match.group(1))
            return 0, "", ""

        # 8. Settings Put Global (Phantom processes)
        if "settings put global settings_enable_monitor_phantom_procs" in clean_cmd:
            if "false" in clean_cmd or "0" in clean_cmd:
                self.phantom_procs_monitor_enabled = False
            else:
                self.phantom_procs_monitor_enabled = True
            return 0, "", ""

        # 9. Termux Wake Lock
        if "termux-wake-lock" in clean_cmd:
            return 0, "CPU wake-lock acquired.\n", ""

        # 10. Process Management (pgrep, kill)
        if "pgrep" in clean_cmd:
            target = clean_cmd.split()[-1]
            matched_pids = [str(pid) for pid, name in self.running_pids.items() if target in name]
            if matched_pids:
                return 0, "\n".join(matched_pids) + "\n", ""
            return 1, "", ""

        if clean_cmd.startswith("kill"):
            pids_to_kill = [int(p) for p in clean_cmd.split() if p.isdigit()]
            for p in pids_to_kill:
                self.running_pids.pop(p, None)
            return 0, "", ""

        # Default echo / safe fallback
        if clean_cmd.startswith("echo"):
            msg = clean_cmd[5:].strip().strip("'\"")
            return 0, f"{msg}\n", ""

        return 0, f"Executed: {clean_cmd}\n", ""

    def simulate_disconnect(self):
        """Simulates device going offline or losing connection."""
        self.is_online = False

    def simulate_reconnect(self):
        """Restores device online state."""
        self.is_online = True
