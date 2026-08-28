#!/usr/bin/env python3
"""
Lauburu Self-Healing Hub - Privileged ADB & Shizuku Device Controller
====================================================================
Provides an untethered, privileged execution layer across Android nodes
(Pixel 10 Pro XL, Samsung Galaxy S20+) supporting:
1. Shizuku Binder IPC (rish) for untethered on-device execution
2. Local ADB daemon commands & TCP 5555 auto-reconnect
3. SSH Relay Bridge for remote orchestrators
4. Deterministic Synthetic Mock Testbed with real state tracking for CI/E2E
"""

import subprocess
import logging
import os
import re
import shutil
import time
from typing import Optional, List, Dict, Any, Union

try:
    from ssh_handler import SSHHandler
except ImportError:
    SSHHandler = None

logger = logging.getLogger(__name__)


class SyntheticAndroidState:
    """Maintains mutable state for synthetic mock testbeds."""
    def __init__(self):
        self.adb_tcp_port = 5555
        self.wifi_enabled = True
        self.cellular_enabled = True
        self.doze_whitelist = {"com.termux", "com.tailscale.ipn", "com.termux.boot", "com.openclaw.agent"}
        self.phantom_monitor_enabled = False
        self.max_phantom_processes = 2147483647
        self.installed_packages = {"com.termux", "com.tailscale.ipn", "com.termux.boot", "moe.shizuku.privileged.api"}
        self.running_services = {"com.tailscale.ipn": True, "com.termux": True, "moe.shizuku.privileged.api": True}
        self.appops = {
            "com.termux": {"RUN_IN_BACKGROUND": "allow", "RUN_ANY_IN_BACKGROUND": "allow"},
            "com.tailscale.ipn": {"RUN_IN_BACKGROUND": "allow", "RUN_ANY_IN_BACKGROUND": "allow"}
        }
        self.battery_level = 88
        self.battery_temp = 29.5
        self.command_log: List[str] = []


class AdbHelper:
    def __init__(
        self,
        device_id: Optional[str] = None,
        use_ssh: bool = False,
        ssh_host: Optional[str] = None,
        ssh_user: str = "root",
        ssh_port: int = 22,
        ssh_key: Optional[str] = None,
        relay_host: Optional[str] = None,
        relay_cmd: Optional[str] = None,
        mock_mode: bool = False
    ):
        """
        Initialize the privileged device executor.
        :param device_id: Optional specific device ID or host:port (for ADB).
        :param use_ssh: If True, executes commands over SSH.
        :param mock_mode: If True, uses the synthetic mock device state engine.
        """
        self.device_id = device_id
        self.use_ssh = use_ssh
        self.ssh_port = ssh_port
        self.ssh_key = ssh_key
        self.relay_host = relay_host
        self.relay_cmd = relay_cmd
        self.mock_mode = mock_mode

        if self.mock_mode:
            self.state = SyntheticAndroidState()
        else:
            self.state = None

        if self.use_ssh and SSHHandler is not None:
            self.ssh_handler = SSHHandler(
                host=ssh_host,
                username=ssh_user,
                port=ssh_port,
                key_file=ssh_key,
                relay_host=relay_host,
                relay_cmd=relay_cmd
            )
        else:
            self.ssh_handler = None

        # Resolve ADB binary
        self.adb_bin = shutil.which("adb") or "/Users/aaron/.local/bin/adb" or "adb"
        self.base_adb_cmd = [self.adb_bin]
        if self.device_id and not self.use_ssh:
            self.base_adb_cmd.extend(["-s", self.device_id])

        # Rish path resolution
        self.rish_bin = shutil.which("rish") or f"{os.environ.get('PREFIX', '')}/bin/rish"
        if not os.path.exists(self.rish_bin):
            for candidate in ["/data/local/tmp/bin/rish", "/data/local/tmp/rish", "/system/bin/rish"]:
                if os.path.exists(candidate):
                    self.rish_bin = candidate
                    break

    def _ensure_adb_connected(self):
        """Connect to device over TCP if device_id specifies host:port."""
        if self.mock_mode or not self.device_id or ":" not in self.device_id:
            return
        try:
            subprocess.run(
                [self.adb_bin, "connect", self.device_id],
                capture_output=True,
                text=True,
                timeout=5
            )
        except Exception as e:
            logger.warning(f"Failed to connect ADB device {self.device_id}: {e}")

    def is_shizuku_available(self) -> bool:
        """Checks if Shizuku binder CLI (rish) is installed and operational."""
        if self.mock_mode:
            return True
        if self.rish_bin and os.path.exists(self.rish_bin) and os.access(self.rish_bin, os.X_OK):
            res = self.run_rish("id")
            if res and res.returncode == 0 and ("uid=2000" in res.stdout or "uid=0" in res.stdout):
                return True
        return False

    def run_cmd(self, cmd_args: List[str], timeout: int = 10) -> Optional[subprocess.CompletedProcess]:
        """Run a standard local ADB command."""
        if self.mock_mode:
            self.state.command_log.append(f"adb {' '.join(cmd_args)}")
            return subprocess.CompletedProcess(
                args=[self.adb_bin] + cmd_args,
                returncode=0,
                stdout="Mock ADB command succeeded\n",
                stderr=""
            )

        if self.use_ssh:
            logger.error("Cannot run base ADB commands (like push/pull) over direct SSH.")
            return None

        if self.device_id and ":" in self.device_id:
            self._ensure_adb_connected()

        full_cmd = self.base_adb_cmd + cmd_args
        try:
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            if result.returncode != 0:
                logger.warning(f"ADB command failed: {' '.join(full_cmd)}\nError: {result.stderr.strip()}")
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"ADB command timed out after {timeout}s: {' '.join(full_cmd)}")
            return None
        except Exception as e:
            logger.error(f"Error running ADB command: {e}")
            return None

    def run_rish(self, cmd_string: str, timeout: int = 10) -> Optional[subprocess.CompletedProcess]:
        """Executes a command directly through Shizuku's rish Binder IPC client."""
        if self.mock_mode:
            return self._handle_mock_command(f"rish -c '{cmd_string}'", cmd_string)

        try:
            result = subprocess.run(
                [self.rish_bin, "-c", cmd_string],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result
        except Exception as e:
            logger.debug(f"Direct rish invocation failed: {e}")
            return None

    def run_shell(self, shell_cmd: str, as_root: bool = False, timeout: int = 10) -> Optional[subprocess.CompletedProcess]:
        """Run a shell command on the device via SSH, ADB, or Mock Engine."""
        if self.mock_mode:
            return self._handle_mock_command(shell_cmd, shell_cmd)

        if self.use_ssh and self.ssh_handler:
            if self.ssh_handler.host in ["127.0.0.1", "localhost"]:
                try:
                    res = subprocess.run(["zsh", "-c", shell_cmd], capture_output=True, text=True, timeout=timeout)
                    return res
                except Exception as e:
                    logger.error(f"Localhost command error: {e}")
                    return None

            if as_root:
                safe_cmd = shell_cmd.replace("'", "'\\''")
                cmd_string = f"su -c '{safe_cmd}'"
            else:
                cmd_string = shell_cmd
            return self.ssh_handler.run_cmd(cmd_string, timeout=timeout)
        else:
            if as_root:
                safe_cmd = shell_cmd.replace("'", "'\\''")
                cmd_args = ["shell", "su", "-c", f"'{safe_cmd}'"]
            else:
                cmd_args = ["shell", shell_cmd]
            return self.run_cmd(cmd_args, timeout=timeout)

    def run_privileged(self, shell_cmd: str, timeout: int = 10) -> Optional[subprocess.CompletedProcess]:
        """
        Executes a command with elevated privileges using the optimal available channel:
        1. Shizuku (rish) Binder IPC
        2. Direct ADB shell
        3. Superuser (su)
        4. Mock testbed handler
        """
        if self.mock_mode:
            return self._handle_mock_command(f"privileged: {shell_cmd}", shell_cmd)

        # 1. Try Shizuku rish
        if self.is_shizuku_available():
            res = self.run_rish(shell_cmd, timeout=timeout)
            if res and res.returncode == 0:
                return res

        # 2. Try standard ADB shell
        res = self.run_shell(shell_cmd, as_root=False, timeout=timeout)
        if res and res.returncode == 0:
            return res

        # 3. Fallback to su
        return self.run_shell(shell_cmd, as_root=True, timeout=timeout)

    def _handle_mock_command(self, logged_cmd: str, raw_cmd: str) -> subprocess.CompletedProcess:
        """Processes synthetic commands and updates mock device state."""
        self.state.command_log.append(logged_cmd)
        stdout = ""
        stderr = ""
        returncode = 0

        cmd_clean = raw_cmd.strip()

        if cmd_clean == "id" or re.search(r'\bid\b', cmd_clean) and not ("dumpsys" in cmd_clean or "settings" in cmd_clean):
            stdout = "uid=2000(shell) gid=2000(shell) groups=2000(shell),1004(input),1007(log),1011(adb),3003(inet)"
        elif "getprop service.adb.tcp.port" in cmd_clean:
            stdout = f"{self.state.adb_tcp_port}\n"
        elif "setprop service.adb.tcp.port" in cmd_clean:
            parts = cmd_clean.split()
            port_val = parts[-1] if len(parts) > 2 else "5555"
            self.state.adb_tcp_port = int(port_val) if port_val.isdigit() else 5555
            stdout = ""
        elif "svc wifi enable" in cmd_clean:
            self.state.wifi_enabled = True
            stdout = ""
        elif "svc wifi disable" in cmd_clean:
            self.state.wifi_enabled = False
            stdout = ""
        elif "dumpsys wifi" in cmd_clean:
            state_str = "enabled" if self.state.wifi_enabled else "disabled"
            stdout = f"Wi-Fi is {state_str}\nmNetworkInfo [type: WIFI[], state: CONNECTED/CONNECTED]\n"
        elif "svc data enable" in cmd_clean:
            self.state.cellular_enabled = True
            stdout = ""
        elif "svc data disable" in cmd_clean:
            self.state.cellular_enabled = False
            stdout = ""
        elif "dumpsys deviceidle whitelist" in cmd_clean:
            if "+" in cmd_clean:
                for token in cmd_clean.split():
                    if token.startswith("+"):
                        self.state.doze_whitelist.add(token[1:])
                stdout = "Added to whitelist\n"
            else:
                stdout = "Whitelist system apps:\n" + "\n".join([f"  {p}" for p in sorted(self.state.doze_whitelist)]) + "\n"
        elif "settings put global settings_enable_monitor_phantom_procs" in cmd_clean:
            if "false" in cmd_clean:
                self.state.phantom_monitor_enabled = False
            elif "true" in cmd_clean:
                self.state.phantom_monitor_enabled = True
            stdout = ""
        elif "settings get global settings_enable_monitor_phantom_procs" in cmd_clean:
            stdout = "false\n" if not self.state.phantom_monitor_enabled else "true\n"
        elif "settings put global max_phantom_processes" in cmd_clean:
            self.state.max_phantom_processes = 2147483647
            stdout = ""
        elif "am force-stop" in cmd_clean:
            pkg = cmd_clean.split()[-1]
            self.state.running_services[pkg] = False
            stdout = ""
        elif "am start" in cmd_clean or "am start-service" in cmd_clean:
            for pkg in self.state.installed_packages:
                if pkg in cmd_clean:
                    self.state.running_services[pkg] = True
            stdout = "Starting: Intent { act=android.intent.action.MAIN }\n"
        elif "pm list packages" in cmd_clean:
            stdout = "\n".join([f"package:{p}" for p in sorted(self.state.installed_packages)]) + "\n"
        elif "cmd appops set" in cmd_clean:
            parts = cmd_clean.split()
            if len(parts) >= 6:
                pkg, op, val = parts[3], parts[4], parts[5]
                if pkg not in self.state.appops:
                    self.state.appops[pkg] = {}
                self.state.appops[pkg][op] = val
            stdout = ""
        elif "dumpsys battery" in cmd_clean:
            stdout = (
                f"Current Battery Service state:\n"
                f"  AC powered: true\n"
                f"  USB powered: false\n"
                f"  Wireless powered: false\n"
                f"  level: {self.state.battery_level}\n"
                f"  temperature: {int(self.state.battery_temp * 10)}\n"
            )
        else:
            stdout = f"Executed mock: {raw_cmd}\n"

        return subprocess.CompletedProcess(
            args=["mock", raw_cmd],
            returncode=returncode,
            stdout=stdout,
            stderr=stderr
        )

    def check_root_access(self) -> bool:
        """Check if the device grants root access."""
        result = self.run_shell("id", as_root=True)
        return bool(result and result.returncode == 0 and "uid=0" in result.stdout)

    def set_adb_tcp_port(self, port: int = 5555) -> bool:
        """Enforces persistent wireless ADB TCP port and restarts adbd."""
        res1 = self.run_privileged(f"setprop service.adb.tcp.port {port}")
        self.run_privileged("stop adbd && start adbd")
        return bool(res1 and res1.returncode == 0)

    def whitelist_doze(self, packages: Union[str, List[str]]) -> bool:
        """Whitelists packages from Android Doze Mode battery optimization."""
        if isinstance(packages, str):
            packages = [packages]
        plus_args = " ".join([f"+{p}" for p in packages])
        cmd = f"dumpsys deviceidle whitelist {plus_args}"
        res = self.run_privileged(cmd)

        # Grant appops background privileges
        for pkg in packages:
            self.run_privileged(f"cmd appops set {pkg} RUN_IN_BACKGROUND allow")
            self.run_privileged(f"cmd appops set {pkg} RUN_ANY_IN_BACKGROUND allow")

        return bool(res and res.returncode == 0)

    def is_doze_whitelisted(self, package_name: str) -> bool:
        """Checks if a given package is on the Doze Mode whitelist."""
        res = self.run_privileged("dumpsys deviceidle whitelist")
        if res and res.returncode == 0:
            return package_name in res.stdout
        return False

    def set_phantom_process_monitor(self, enabled: bool = False, max_processes: int = 2147483647) -> bool:
        """Disables or enables Android 12+ Phantom Process Killer."""
        val = "true" if enabled else "false"
        res1 = self.run_privileged(f"settings put global settings_enable_monitor_phantom_procs {val}")
        res2 = self.run_privileged(f"settings put global max_phantom_processes {max_processes}")
        return bool(res1 and res1.returncode == 0 and res2 and res2.returncode == 0)

    def get_phantom_process_monitor_state(self) -> bool:
        """Returns True if phantom monitor is enabled, False if disabled."""
        res = self.run_privileged("settings get global settings_enable_monitor_phantom_procs")
        if res and res.returncode == 0:
            return "true" in res.stdout.lower()
        return True

    def bounce_wifi(self, delay_sec: float = 2.0) -> bool:
        """Atomic Wi-Fi radio bounce."""
        res_off = self.run_privileged("svc wifi disable")
        if not self.mock_mode and delay_sec > 0:
            time.sleep(delay_sec)
        res_on = self.run_privileged("svc wifi enable")
        return bool(res_off and res_off.returncode == 0 and res_on and res_on.returncode == 0)

    def bounce_cellular(self, delay_sec: float = 1.0) -> bool:
        """Atomic Cellular data radio bounce."""
        res_off = self.run_privileged("svc data disable")
        if not self.mock_mode and delay_sec > 0:
            time.sleep(delay_sec)
        res_on = self.run_privileged("svc data enable")
        return bool(res_off and res_off.returncode == 0 and res_on and res_on.returncode == 0)

    def get_battery_telemetry(self) -> Dict[str, Any]:
        """Queries hardware battery percentage, temperature, and charging status."""
        res = self.run_privileged("dumpsys battery")
        telemetry = {"level": None, "temperature_c": None, "ac_powered": False}
        if res and res.returncode == 0:
            for line in res.stdout.splitlines():
                line = line.strip()
                if line.startswith("level:"):
                    try:
                        telemetry["level"] = int(line.split(":")[1].strip())
                    except ValueError:
                        pass
                elif line.startswith("temperature:"):
                    try:
                        telemetry["temperature_c"] = float(line.split(":")[1].strip()) / 10.0
                    except ValueError:
                        pass
                elif line.startswith("AC powered: true"):
                    telemetry["ac_powered"] = True
        return telemetry
