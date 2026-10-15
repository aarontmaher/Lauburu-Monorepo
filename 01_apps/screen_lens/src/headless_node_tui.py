#!/usr/bin/env python3
import os, sys, socket, curses, subprocess, time
from typing import Dict, Any, List

def run_cmd(cmd: List[str], timeout=1.0) -> str:
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if res.returncode == 0: return res.stdout.strip()
    except: pass
    return ""

def is_termux() -> bool: return "com.termux" in os.environ.get("PREFIX", "") or os.path.exists("/data/data/com.termux")

def get_device_specs() -> Dict[str, Any]:
    specs = {"hostname": socket.gethostname(), "kernel": os.uname().release, "arch": os.uname().machine, "cpu_model": "Unknown CPU", "cpu_cores": os.cpu_count() or 1, "ram_total_gb": 0.0, "ram_free_gb": 0.0, "ram_used_pct": 0.0, "thermal_c": "--", "gpu_npu": "Standard Framebuffer"}
    if is_termux():
        specs["cpu_model"] = run_cmd(["getprop", "ro.soc.model"]) or "Android Edge SoC"
        specs["gpu_npu"] = "Android Hardware / Edge TPU"
    elif sys.platform == "darwin":
        specs["cpu_model"] = run_cmd(["sysctl", "-n", "machdep.cpu.brand_string"]) or "Apple Silicon"
        specs["gpu_npu"] = "Apple Metal Performance Shaders"
        total_b_str = run_cmd(["sysctl", "-n", "hw.memsize"])
        if total_b_str.isdigit():
            specs["ram_total_gb"] = round(int(total_b_str) / (1024**3), 2)
            vm = run_cmd(["vm_stat"])
            pages = {k.strip(): int(v.strip().rstrip(".")) for line in vm.splitlines() if ":" in line for k, v in [line.split(":", 1)] if v.strip().rstrip(".").isdigit()}
            free_p = pages.get("Pages free", 0) + pages.get("Pages speculative", 0) + pages.get("Pages inactive", 0)
            specs["ram_free_gb"] = round((free_p * (16384 if "arm64" in specs["arch"] else 4096)) / (1024**3), 2)
            if specs["ram_total_gb"] > 0: specs["ram_used_pct"] = round(((specs["ram_total_gb"] - specs["ram_free_gb"]) / specs["ram_total_gb"]) * 100, 1)
    elif sys.platform == "linux" and not is_termux():
        # Standard Linux parsing
        cpuinfo = run_cmd(["cat", "/proc/cpuinfo"])
        for line in cpuinfo.splitlines():
            if "model name" in line:
                specs["cpu_model"] = line.split(":", 1)[1].strip()
                break
        meminfo = run_cmd(["cat", "/proc/meminfo"])
        mem_total = 0
        mem_free = 0
        mem_avail = 0
        for line in meminfo.splitlines():
            if line.startswith("MemTotal:"): mem_total = int(line.split()[1]) * 1024
            elif line.startswith("MemFree:"): mem_free = int(line.split()[1]) * 1024
            elif line.startswith("MemAvailable:"): mem_avail = int(line.split()[1]) * 1024
        
        specs["ram_total_gb"] = round(mem_total / (1024**3), 2)
        actual_free = mem_avail if mem_avail > 0 else mem_free
        specs["ram_free_gb"] = round(actual_free / (1024**3), 2)
        if specs["ram_total_gb"] > 0:
            specs["ram_used_pct"] = round(((specs["ram_total_gb"] - specs["ram_free_gb"]) / specs["ram_total_gb"]) * 100, 1)
        
        try:
            temp = run_cmd(["cat", "/sys/class/thermal/thermal_zone0/temp"])
            if temp.isdigit(): specs["thermal_c"] = str(round(int(temp) / 1000, 1))
        except: pass
    return specs

def get_cable_connectivity() -> List[Dict[str, Any]]:
    links = []
    if sys.platform in ["darwin", "linux"] or is_termux():
        out = run_cmd(["ip", "link", "show"]) if sys.platform == "linux" and not is_termux() else run_cmd(["ifconfig"])
        current_iface = ""
        for line in out.splitlines():
            if line and not line.startswith("\t") and not line.startswith(" "): 
                # Linux ip link format: "1: lo: <LOOPBACK,UP,LOWER_UP>..."
                if "linux" in sys.platform and not is_termux():
                    parts = line.split(":")
                    if len(parts) >= 2: current_iface = parts[1].strip()
                else:
                    current_iface = line.split(":")[0]
            
            if "status: active" in line or "UP" in line:
                if current_iface == "lo" or "rmnet" in current_iface: continue
                ltype = "TB Bridge" if "bridge" in current_iface else "Ethernet" if "en" in current_iface else "Tailscale" if "tun" in current_iface else "Wi-Fi" if "wlan" in current_iface else "Network"
                # Prevent duplicates
                if not any(l["interface"] == current_iface for l in links):
                    links.append({"interface": current_iface, "type": ltype, "state": "UP", "speed": "Auto"})
    return links

def get_daemon_activity() -> List[Dict[str, Any]]:
    daemons = ["tailscaled", "docker", "ssh", "python3", "sshd", "launchd"]
    results = []
    out = run_cmd(["ps", "aux"])
    lines = out.splitlines()
    for d in daemons:
        status, pid, cpu = "STOPPED", "--", "--"
        for line in lines:
            if d in line and "grep" not in line:
                parts = line.split()
                if len(parts) > 2: pid, cpu, status = parts[1], parts[2], "ACTIVE"; break
        results.append({"name": d[:10], "status": status, "pid": pid, "cpu": f"{cpu}%" if cpu != "--" else "--"})
    return results

def draw_tui(stdscr):
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    stdscr.nodelay(True)
    
    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        try:
            specs = get_device_specs()
            links = get_cable_connectivity()
            daemons = get_daemon_activity()
            
            stdscr.addstr(0, 0, "=" * (w-1))
            stdscr.addstr(1, 0, "🏛️  LAUBURU SOVEREIGN MESH — HEADLESS NOC REPORT", curses.color_pair(1) | curses.A_BOLD)
            stdscr.addstr(2, 0, "=" * (w-1))
            
            stdscr.addstr(3, 0, f"Hostname: {specs['hostname']} | OS: {specs['kernel']} | Arch: {specs['arch']}")
            stdscr.addstr(4, 0, f"CPU: {specs['cpu_model']} ({specs['cpu_cores']} Cores) | Temp: {specs['thermal_c']}°C")
            stdscr.addstr(5, 0, f"RAM: {specs['ram_free_gb']} GB Free / {specs['ram_total_gb']} GB Total ({specs['ram_used_pct']}% Used)", curses.color_pair(3))
            stdscr.addstr(6, 0, f"GPU/NPU: {specs['gpu_npu']}")
            
            stdscr.addstr(8, 0, "[CABLE & CONNECTIVITY SPECS]", curses.color_pair(1))
            y = 9
            for l in links:
                if y < h - 2:
                    stdscr.addstr(y, 0, f"  • {l['interface']:<14} {l['type']:<14} {l['state']:<8} Link: {l['speed']}", curses.color_pair(2))
                    y += 1
                    
            y += 1
            stdscr.addstr(y, 0, "[DAEMON SUPERVISOR]", curses.color_pair(1))
            y += 1
            for d in daemons:
                if y < h - 2:
                    stdscr.addstr(y, 0, f"  • {d['name']:<12} {d['status']:<8} PID:{d['pid']:<6} CPU:{d['cpu']}")
                    y += 1
            
        except Exception: pass
        
        stdscr.refresh()
        c = stdscr.getch()
        if c == ord('q'): break
        time.sleep(1.5)

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        print("🏛️ LAUBURU SOVEREIGN MESH NOC REPORT")
        print(get_device_specs())
        return
    curses.wrapper(draw_tui)

if __name__ == "__main__": main()
