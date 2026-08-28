import re
import logging
import json
from adb_helper import AdbHelper

logger = logging.getLogger(__name__)

class MetricPollers:
    def __init__(self, adb_helper: AdbHelper):
        self.adb = adb_helper
        self.os_type = self._detect_os_type()

    def _detect_os_type(self):
        """Helper to identify device platform to optimize metric extraction."""
        if not self.adb.use_ssh:
            return "android_adb"
        if self.adb.relay_host or (self.adb.ssh_handler and self.adb.ssh_handler.username == "linux"):
            return "linux"
        if self.adb.ssh_handler and (self.adb.ssh_handler.host == "127.0.0.1" or self.adb.ssh_handler.username == "aaronmaher"):
            return "macos"
        if self.adb.ssh_port == 8022 or (self.adb.ssh_handler and "u0_a" in self.adb.ssh_handler.username):
            return "android_termux"
        return "generic"

    def get_battery_stats(self, timeout=30):
        """
        Get battery level and status across Android, macOS, and Linux.
        Returns dict: {'level': int/None, 'status': str, 'ac_powered': bool, 'usb_powered': bool} or None on failure.
        """
        os_type = self.os_type

        # macOS platform
        if os_type == "macos":
            result = self.adb.run_shell("pmset -g batt", timeout=timeout)
            if result and result.returncode == 0 and ("InternalBattery" in result.stdout or "AC Power" in result.stdout):
                output = result.stdout
                stats = {'level': None, 'status': 'unknown', 'ac_powered': False, 'usb_powered': False}
                if "AC Power" in output or "AC attached" in output:
                    stats['ac_powered'] = True
                level_match = re.search(r'(\d+)%', output)
                if level_match:
                    stats['level'] = int(level_match.group(1))
                if "charging" in output:
                    stats['status'] = 'charging'
                elif "discharging" in output:
                    stats['status'] = 'discharging'
                elif "charged" in output or "full" in output:
                    stats['status'] = 'full'
                elif stats['ac_powered']:
                    stats['status'] = 'not_charging'
                return stats
            return None

        # Termux Android SSH platform
        if os_type == "android_termux":
            result = self.adb.run_shell("termux-battery-status", timeout=timeout)
            if result and result.returncode == 0 and "percentage" in result.stdout:
                try:
                    b_data = json.loads(result.stdout)
                    level = b_data.get("percentage") if b_data.get("percentage") is not None else b_data.get("level")
                    status_raw = str(b_data.get("status", "unknown")).lower()
                    plugged_raw = str(b_data.get("plugged", "")).upper()
                    return {
                        'level': int(level) if level is not None else None,
                        'status': status_raw,
                        'ac_powered': plugged_raw in ['PLUGGED', 'AC'],
                        'usb_powered': plugged_raw == 'USB'
                    }
                except Exception:
                    pass
                    
            # Fallback: Read directly from Linux/Android sysfs power_supply in a single SSH call
            combined_res = self.adb.run_shell("cat /sys/class/power_supply/battery/capacity /sys/class/power_supply/battery/status 2>/dev/null || cat /sys/class/power_supply/bms/capacity /sys/class/power_supply/bms/status 2>/dev/null", timeout=timeout)
            
            if combined_res and combined_res.returncode == 0 and combined_res.stdout.strip():
                lines = [l.strip() for l in combined_res.stdout.strip().split("\n") if l.strip()]
                if len(lines) >= 1 and lines[0].isdigit():
                    level = int(lines[0])
                    status_raw = lines[1].lower() if len(lines) > 1 else "discharging"
                    is_charging = "charging" in status_raw or "full" in status_raw
                    return {
                        'level': level,
                        'status': status_raw if status_raw else ("charging" if is_charging else "discharging"),
                        'ac_powered': is_charging,
                        'usb_powered': False
                    }
            return None

        # Standard Android ADB platform with Multi-Transport Self-Healing Fallback
        if os_type == "android_adb":
            result = self.adb.run_shell("dumpsys battery", timeout=timeout)
            if result and result.returncode == 0 and "level:" in result.stdout:
                output = result.stdout
                stats = {}
                level_match = re.search(r'level: (\d+)', output)
                if level_match:
                    stats['level'] = int(level_match.group(1))
                status_match = re.search(r'status: (\d+)', output)
                if status_match:
                    status_map = {1: 'unknown', 2: 'charging', 3: 'discharging', 4: 'not_charging', 5: 'full'}
                    stats['status'] = status_map.get(int(status_match.group(1)), 'unknown')
                ac_match = re.search(r'AC powered: (true|false)', output)
                if ac_match:
                    stats['ac_powered'] = (ac_match.group(1) == 'true')
                usb_match = re.search(r'USB powered: (true|false)', output)
                if usb_match:
                    stats['usb_powered'] = (usb_match.group(1) == 'true')
                return stats

            # Pathway 2: Fallback to Termux SSH on port 8022
            host_ip = self.adb.device_id.split(':')[0] if ':' in self.adb.device_id else self.adb.device_id
            try:
                import subprocess
                termux_cmd = f"ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no -p 8022 {host_ip} 'termux-battery-status' 2>/dev/null"
                res = subprocess.run(termux_cmd, shell=True, capture_output=True, text=True, timeout=3)
                if res.returncode == 0 and "percentage" in res.stdout:
                    b_data = json.loads(res.stdout)
                    level = b_data.get("percentage") if b_data.get("percentage") is not None else b_data.get("level")
                    status_raw = str(b_data.get("status", "unknown")).lower()
                    plugged_raw = str(b_data.get("plugged", "")).upper()
                    return {
                        'level': int(level) if level is not None else None,
                        'status': status_raw,
                        'ac_powered': plugged_raw in ['PLUGGED', 'AC', 'PLUGGED_AC'],
                        'usb_powered': plugged_raw == 'USB'
                    }
            except Exception:
                pass

            # Pathway 3: Fallback to Router USB ADB for USB-connected devices (e.g. S20+)
            try:
                import subprocess
                router_adb_cmd = "ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no root@192.168.8.1 'adb shell dumpsys battery' 2>/dev/null"
                res = subprocess.run(router_adb_cmd, shell=True, capture_output=True, text=True, timeout=3)
                if res.returncode == 0 and "level:" in res.stdout:
                    output = res.stdout
                    stats = {}
                    level_match = re.search(r'level: (\d+)', output)
                    if level_match:
                        stats['level'] = int(level_match.group(1))
                    status_match = re.search(r'status: (\d+)', output)
                    if status_match:
                        status_map = {1: 'unknown', 2: 'charging', 3: 'discharging', 4: 'not_charging', 5: 'full'}
                        stats['status'] = status_map.get(int(status_match.group(1)), 'unknown')
                    ac_match = re.search(r'AC powered: (true|false)', output)
                    if ac_match:
                        stats['ac_powered'] = (ac_match.group(1) == 'true')
                    usb_match = re.search(r'USB powered: (true|false)', output)
                    if usb_match:
                        stats['usb_powered'] = (usb_match.group(1) == 'true')
                    return stats
            except Exception:
                pass

            return None

        # Linux platform
        if os_type == "linux":
            result = self.adb.run_shell("cat /sys/class/power_supply/BAT0/capacity 2>/dev/null; cat /sys/class/power_supply/BAT0/status 2>/dev/null", timeout=timeout)
            if result and result.returncode == 0 and result.stdout.strip():
                lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
                if len(lines) >= 1 and lines[0].isdigit():
                    level = int(lines[0])
                    status = lines[1].lower() if len(lines) > 1 else 'unknown'
                    return {
                        'level': level,
                        'status': status,
                        'ac_powered': status in ['charging', 'full'],
                        'usb_powered': False
                    }
            return None

        # Generic fallback
        return None

    def get_hardware_specs(self, timeout=30):
        """
        Get static hardware specifications: CPU, NPU, RAM.
        Returns dict: {'cpu': str, 'npu': str, 'ram': str} or None on failure.
        """
        os_type = self.os_type
        specs = {'cpu': 'Unknown', 'npu': 'None', 'ram': 'Unknown', 'device_type': 'Unknown'}
        
        if os_type == "macos":
            specs['device_type'] = 'Apple Mac'
            mem_res = self.adb.run_shell("sysctl -n hw.memsize", timeout=timeout)
            if mem_res and mem_res.returncode == 0:
                try:
                    gb = round(float(mem_res.stdout.strip()) / (1024**3), 1)
                    specs['ram'] = f"{gb} GB"
                except Exception:
                    pass
            cpu_res = self.adb.run_shell("sysctl -n machdep.cpu.brand_string", timeout=timeout)
            if cpu_res and cpu_res.returncode == 0:
                specs['cpu'] = cpu_res.stdout.strip()
                if "Apple M" in specs['cpu']:
                    specs['npu'] = "Apple Neural Engine (ANE)"
            return specs
            
        if os_type in ["linux", "android_adb", "android_termux"]:
            if os_type == "linux":
                specs['device_type'] = "Linux Device"
            else:
                specs['device_type'] = "Android Device"
                
            mem_res = self.adb.run_shell("cat /proc/meminfo", timeout=timeout)
            if mem_res and mem_res.returncode == 0:
                total_match = re.search(r'MemTotal:\s+(\d+)\s+kB', mem_res.stdout)
                if total_match:
                    gb = round(float(total_match.group(1)) / (1024**2), 1)
                    specs['ram'] = f"{gb} GB"
                    
            if os_type in ["android_adb", "android_termux"]:
                soc_res = self.adb.run_shell("getprop ro.soc.model", timeout=timeout)
                board_res = self.adb.run_shell("getprop ro.board.platform", timeout=timeout)
                soc = soc_res.stdout.strip() if soc_res and soc_res.returncode == 0 else ""
                board = board_res.stdout.strip() if board_res and board_res.returncode == 0 else ""
                cpu_name = soc or board or "Unknown Android SoC"
                specs['cpu'] = cpu_name
                
                board_lower = board.lower()
                if "gs201" in board_lower or "tensor" in cpu_name.lower() or "zuma" in board_lower or "laguna" in board_lower:
                    specs['npu'] = "Google Edge TPU"
                elif "exynos" in board_lower or "exynos" in cpu_name.lower():
                    specs['npu'] = "Samsung NPU"
                elif "kona" in board_lower or "snapdragon" in cpu_name.lower():
                    specs['npu'] = "Qualcomm Hexagon NPU"
            else:
                cpu_res = self.adb.run_shell("grep 'model name' /proc/cpuinfo | head -n 1", timeout=timeout)
                if cpu_res and cpu_res.returncode == 0 and ":" in cpu_res.stdout:
                    specs['cpu'] = cpu_res.stdout.split(":")[1].strip()
                    
            return specs

        return None

    def get_cpu_usage(self, timeout=5):
        """
        Get dynamic CPU utilization percentage.
        Returns float (e.g. 45.2) or None on failure.
        """
        os_type = self.os_type
        
        if os_type == "macos":
            res = self.adb.run_shell("top -l 1 -n 0 | awk '/CPU usage/'", timeout=timeout)
            if res and res.returncode == 0:
                match = re.search(r'CPU usage:\s*([\d\.]+)%\s*user,\s*([\d\.]+)%\s*sys', res.stdout)
                if match:
                    return round(float(match.group(1)) + float(match.group(2)), 2)
            return None
            
        if os_type in ["linux", "android_adb", "android_termux"]:
            if os_type == "android_adb":
                res = self.adb.run_shell("dumpsys cpuinfo | head -n 5", timeout=timeout)
                if res and res.returncode == 0:
                    match = re.search(r'([\d\.]+)%\s+TOTAL', res.stdout)
                    if match:
                        return float(match.group(1))
            
            res = self.adb.run_shell("top -b -n 1 | head -n 10", timeout=timeout)
            if res and res.returncode == 0:
                # 1. Standard Linux format (Cpu(s): 12.5 us, 4.2 sy)
                cpu_match = re.search(r'(?:Cpu\(s\):|CPU:)\s*([\d\.]+)\D*(?:us|user|%usr)?,\s*([\d\.]+)\D*(?:sy|sys|%sys)?', res.stdout, re.IGNORECASE)
                if cpu_match:
                    try:
                        return round(float(cpu_match.group(1)) + float(cpu_match.group(2)), 2)
                    except:
                        pass
                # 2. Android top format (800%cpu 12%user 0%nice 5%sys 783%idle)
                android_match = re.search(r'(\d+)%cpu\s+(\d+)%user.*?(\d+)%sys.*?(\d+)%idle', res.stdout)
                if android_match:
                    try:
                        total_cap = float(android_match.group(1))
                        idle_cap = float(android_match.group(4))
                        if total_cap > 0:
                            usage_pct = round(((total_cap - idle_cap) / total_cap) * 100.0, 2)
                            return max(0.0, usage_pct)
                    except:
                        pass
        return None

    def get_memory_stats(self, timeout=30):
        """
        Get system memory usage statistics across Linux/Android (/proc/meminfo) and macOS (vm_stat, sysctl).
        Returns dict: {'total_mb': float, 'available_mb': float, 'used_mb': float, 'used_percent': float} or None on failure.
        """
        os_type = self.os_type

        if os_type == "macos":
            sysctl_res = self.adb.run_shell("sysctl hw.memsize", timeout=timeout)
            vm_res = self.adb.run_shell("vm_stat", timeout=timeout)
            if sysctl_res and sysctl_res.returncode == 0 and vm_res and vm_res.returncode == 0:
                total_match = re.search(r'hw.memsize:\s*(\d+)', sysctl_res.stdout)
                if total_match:
                    total_bytes = float(total_match.group(1))
                    total_mb = round(total_bytes / (1024.0 * 1024.0), 2)
                    page_size_match = re.search(r'page size of (\d+) bytes', vm_res.stdout)
                    page_size = float(page_size_match.group(1)) if page_size_match else 4096.0

                    free_match = re.search(r'Pages free:\s+(\d+)\.', vm_res.stdout)
                    spec_match = re.search(r'Pages speculative:\s+(\d+)\.', vm_res.stdout)
                    inact_match = re.search(r'Pages inactive:\s+(\d+)\.', vm_res.stdout)

                    free_pages = float(free_match.group(1)) if free_match else 0.0
                    spec_pages = float(spec_match.group(1)) if spec_match else 0.0
                    inact_pages = float(inact_match.group(1)) if inact_match else 0.0

                    avail_bytes = (free_pages + spec_pages + inact_pages) * page_size
                    avail_mb = round(avail_bytes / (1024.0 * 1024.0), 2)
                    used_mb = round(total_mb - avail_mb, 2)
                    used_percent = round((used_mb / total_mb) * 100.0, 2) if total_mb > 0 else 0.0

                    return {
                        'total_mb': total_mb,
                        'available_mb': avail_mb,
                        'used_mb': used_mb,
                        'used_percent': used_percent
                    }
            return None

        # Linux / Android
        result = self.adb.run_shell("cat /proc/meminfo", timeout=timeout)
        if result and result.returncode == 0 and "MemTotal:" in result.stdout:
            output = result.stdout
            total_match = re.search(r'MemTotal:\s+(\d+)\s+kB', output)
            avail_match = re.search(r'MemAvailable:\s+(\d+)\s+kB', output)
            free_match = re.search(r'MemFree:\s+(\d+)\s+kB', output)
            buffers_match = re.search(r'Buffers:\s+(\d+)\s+kB', output)
            cached_match = re.search(r'Cached:\s+(\d+)\s+kB', output)

            if total_match:
                total_kb = float(total_match.group(1))
                if avail_match:
                    avail_kb = float(avail_match.group(1))
                elif free_match:
                    free_kb = float(free_match.group(1))
                    buf_kb = float(buffers_match.group(1)) if buffers_match else 0.0
                    cache_kb = float(cached_match.group(1)) if cached_match else 0.0
                    avail_kb = free_kb + buf_kb + cache_kb
                else:
                    return None

                total_mb = round(total_kb / 1024.0, 2)
                avail_mb = round(avail_kb / 1024.0, 2)
                used_mb = round(total_mb - avail_mb, 2)
                used_percent = round((used_mb / total_mb) * 100.0, 2) if total_mb > 0 else 0.0

                return {
                    'total_mb': total_mb,
                    'available_mb': avail_mb,
                    'used_mb': used_mb,
                    'used_percent': used_percent
                }

        return None

    def get_network_interfaces(self, timeout=30):
        """
        Get active network interfaces and their Rx/Tx bytes across Linux/Android (/proc/net/dev) and macOS (netstat -ib).
        Returns a dict: {'wlan0': {'rx_bytes': int, 'tx_bytes': int}, ...} or None on failure.
        """
        os_type = self.os_type

        if os_type == "macos":
            result = self.adb.run_shell("netstat -ib", timeout=timeout)
            if result and result.returncode == 0 and "Name" in result.stdout:
                interfaces = {}
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:
                    parts = line.split()
                    if len(parts) >= 10:
                        iface_name = parts[0].rstrip('*')
                        if "<Link#" in parts[2] or (len(parts) > 3 and "<Link#" in parts[3]):
                            try:
                                rx_bytes = int(parts[6])
                                tx_bytes = int(parts[9])
                                if iface_name not in interfaces or rx_bytes > interfaces[iface_name]['rx_bytes']:
                                    interfaces[iface_name] = {
                                        'rx_bytes': rx_bytes,
                                        'tx_bytes': tx_bytes
                                    }
                            except (ValueError, IndexError):
                                continue
                if interfaces:
                    return interfaces
            return None

        # Linux / Android
        if os_type == "android_termux":
            result = self.adb.run_shell("cat /proc/net/dev 2>/dev/null", as_root=False, timeout=timeout)
        else:
            result = self.adb.run_shell("cat /proc/net/dev", as_root=False, timeout=timeout)
        if result and result.returncode == 0 and "Inter-|" in result.stdout:
            interfaces = {}
            lines = result.stdout.strip().split('\n')
            for line in lines[2:]:
                parts = line.split(':')
                if len(parts) == 2:
                    iface_name = parts[0].strip()
                    data_parts = parts[1].split()
                    if len(data_parts) >= 9:
                        try:
                            rx_bytes = int(data_parts[0])
                            tx_bytes = int(data_parts[8])
                            interfaces[iface_name] = {
                                'rx_bytes': rx_bytes,
                                'tx_bytes': tx_bytes
                            }
                        except ValueError:
                            continue
            if interfaces:
                return interfaces

        return None

    def ping_test(self, target="8.8.8.8", count=1, timeout=30):
        """
        Run a simple ping test from the device to check latency.
        Returns average latency in ms, or None if failed.
        """
        result = self.adb.run_shell(f"ping -c {count} -W 2 {target}", timeout=timeout)
        if not result or result.returncode != 0 or not result.stdout:
            return None

        match = re.search(r'(?:rtt|round-trip) min/avg/max/(?:mdev|stddev) = [\d\.]+/(.*?)/[\d\.]+', result.stdout)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

        time_match = re.search(r'time=([\d\.]+)\s*ms', result.stdout)
        if time_match:
            try:
                return float(time_match.group(1))
            except ValueError:
                pass

        return None
