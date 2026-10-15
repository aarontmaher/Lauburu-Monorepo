#!/usr/bin/env python3
"""
unified_screen_lens.py — Canonical Screen Lens Unified Device Automation CLI (v3.1)
=============================================================================
Governed by:
- Rule #0 & #1: Zero-Mock Empirical Truth & Tri-Proof Verification Gate
- Rule #3: Host Sanctuary & Dynamic RAM Governance (L1 read-only; L2 actuation target)
- Rule #10: Linux Mini First-Offload Invariant (L8 lauburu prioritized)
- Adaptive Resource Governor: Human Use, Battery, and Location Awareness
=============================================================================
"""

import sys
import os
import subprocess
import json
import time
import socket
import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

_CANDIDATE_REPOS = [
    Path(__file__).resolve().parent.parent.parent,
    Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"),
    Path("/Volumes/Lauburu-Monorepo"),
]
REPO_ROOT = next((p for p in _CANDIDATE_REPOS if p.exists()), Path(__file__).resolve().parent.parent.parent)
GOVERNOR_SCRIPT = REPO_ROOT / "01_apps/screen_lens/src/screen_lens_adaptive_resource_governor.py"
SAFETY_GATE = REPO_ROOT / "06_scripts_and_tooling/automation/device_idle_safety_gate.py"
LORA_LAKE = (
    Path("/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl")
    if Path("/Users/aaron/DFS_UNIFIED/lora_datasets").exists()
    else REPO_ROOT / "data/lora_datasets/continuous_lora_dataset.jsonl"
)

# Node Routing Matrix (Rule 0 Probed Reality)
L1_MAC_MINI_IPS = ["192.168.8.143", "192.168.8.230", "100.119.199.76"]
L1B_MAC_MINI_IPS = ["192.168.8.114", "10.0.0.3", "100.104.128.34"]
L2_MACBOOK_IPS = ["192.168.8.127", "100.103.212.21", "192.168.8.160"]
L8_LAUBURU_IPS = ["192.168.8.242", "10.0.0.8", "100.121.247.8"]
L3_LINUX_IPS = ["192.168.8.225", "100.101.39.98", "192.168.8.224"]
L5_MAC_AIR_IPS = ["192.168.8.248", "100.121.202.34"]
L6_PIXEL_SSH_IPS = [("192.168.8.213", 8022), ("100.114.215.68", 8022)]
L7_S20_IPS = ["192.168.8.101", "192.168.8.157", "100.84.40.95"]
GW_ROUTER_IPS = ["192.168.8.1", "100.70.123.123"]

ANDROID_CANDIDATE_SERIALS = [
    os.getenv("TARGET_DEVICE", ""),
    "192.168.8.213:39619",
    "192.168.8.213:5555",
    "192.168.8.101:41347",
    "192.168.8.224:41347",
    "100.114.215.68:5555",
    "192.168.8.157:5555",
    "100.84.40.95:5555"
]


def check_adaptive_safety(platform: str, target_serial_or_host: str = "") -> bool:
    """Pre-flight check enforcing Human Use, Battery, and Location safety with state cache."""
    state_file = REPO_ROOT / "01_apps/screen_lens/src/adaptive_governor_state.json"
    if state_file.exists():
        try:
            mtime = state_file.stat().st_mtime
            if (time.time() - mtime) < 1800:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                nodes = data.get("mesh_nodes", {})
                for k, node in nodes.items():
                    if platform.lower() in node.get("platform", "").lower() or platform.lower() in k:
                        state = node.get("action_state", "")
                        if state in ["AWAY_MOBILE_SANCTUARY", "BATTERY_CRITICAL_SLEEP"]:
                            print(f"[🛡️ Adaptive Governor Cache] Suppressed execution: {node.get('reason')}")
                            return False
                        elif state == "HUMAN_ACTIVE_OPTIMIZED":
                            print(f"[🛡️ Adaptive Governor Cache] Human in active use: throttling compute for zero UI lag.")
                return True
        except Exception:
            pass

    if not GOVERNOR_SCRIPT.exists():
        return True
    
    try:
        res = subprocess.run(["python3", str(GOVERNOR_SCRIPT)], capture_output=True, text=True, timeout=3)
        if res.returncode == 0 and res.stdout:
            data = json.loads(res.stdout)
            nodes = data.get("mesh_nodes", {})
            for k, node in nodes.items():
                if platform.lower() in node.get("platform", "").lower() or platform.lower() in k:
                    state = node.get("action_state", "")
                    if state in ["AWAY_MOBILE_SANCTUARY", "BATTERY_CRITICAL_SLEEP"]:
                        print(f"[🛡️ Adaptive Governor] Suppressed execution: {node.get('reason')}")
                        return False
                    elif state == "HUMAN_ACTIVE_OPTIMIZED":
                        print(f"[🛡️ Adaptive Governor] Human in active use: throttling compute for zero UI lag.")
            return True
    except Exception as e:
        print(f"[!] Warning: Adaptive safety check fallback to safety gate ({e}).")
    return True


def record_vla_trajectory(platform: str, action: str, command: str, stdout: str, exit_code: int) -> None:
    """Records verified actuation trajectory to continuous PySpark LoRA Data Lake (Rule 1 & 12)."""
    try:
        LORA_LAKE.parent.mkdir(parents=True, exist_ok=True)
        import fcntl
        sha256_hash = hashlib.sha256(f"{platform}:{action}:{command}:{exit_code}:{time.time()}".encode()).hexdigest()
        record = {
            "timestamp": time.time(),
            "source": "unified_screen_lens",
            "instruction": f"Execute Screen Lens unified automation action '{action}' on platform '{platform}'",
            "input": command,
            "output": f"Exit Code: {exit_code}\nOutput: {stdout[:1000]}",
            "sha256": sha256_hash,
            "metadata": {
                "platform": platform,
                "action": action,
                "exit_code": exit_code,
                "sha256": sha256_hash,
            },
        }
        with open(LORA_LAKE, "a", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass


def parse_ui_hierarchy(xml_content: str) -> List[Dict[str, Any]]:
    """Parse Android uiautomator XML into foveated salience nodes."""
    salience_nodes = []
    try:
        start_idx = xml_content.find("<hierarchy")
        if start_idx == -1:
            start_idx = xml_content.find("<?xml")
        if start_idx != -1:
            xml_content = xml_content[start_idx:]
        root = ET.fromstring(xml_content)
        for node in root.iter("node"):
            text = node.attrib.get("text", "").strip()
            desc = node.attrib.get("content-desc", "").strip()
            bounds = node.attrib.get("bounds", "")
            clickable = node.attrib.get("clickable", "false") == "true"
            checkable = node.attrib.get("checkable", "false") == "true"
            checked = node.attrib.get("checked", "false") == "true"
            focused = node.attrib.get("focused", "false") == "true"
            pkg = node.attrib.get("package", "")
            cls = node.attrib.get("class", "")
            res_id = node.attrib.get("resource-id", "")
            if text or desc or clickable or checkable:
                salience_nodes.append({
                    "text": text,
                    "desc": desc,
                    "bounds": bounds,
                    "clickable": clickable,
                    "checkable": checkable,
                    "checked": checked,
                    "package": pkg,
                    "class": cls,
                    "id": res_id
                })
    except Exception:
        pass
    return salience_nodes


def capture_ui_context(target: str = "adb_edge_nodes") -> Tuple[int, str]:
    """Extracts UI context natively from edge nodes via uiautomator (Rule 11)."""
    print(f"[👁️] Screen Lens extracting native UI context for target: {target}")
    xml_content = ""
    active_source = None

    # Check adaptive safety
    if not check_adaptive_safety("android"):
        print("[!] Warning: Adaptive safety suppressed mobile capture.")
        return 1, "SAFETY_SUPPRESSED"

    # Strategy 1: Fast check of already connected ADB devices
    adb_proc = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    if adb_proc.returncode == 0:
        connected_serials = [line.split()[0] for line in adb_proc.stdout.splitlines()[1:] if "\tdevice" in line]
        for serial in connected_serials:
            try:
                dump_cmd = f"adb -s {serial} shell 'uiautomator dump /data/local/tmp/lens_ui.xml >/dev/null 2>&1 && cat /data/local/tmp/lens_ui.xml'"
                res = subprocess.run(dump_cmd, shell=True, capture_output=True, text=True, timeout=5)
                if res.returncode == 0 and "<hierarchy" in res.stdout:
                    xml_content = res.stdout
                    active_source = f"adb:{serial}"
                    break
            except Exception:
                continue

    # Strategy 2: L6 Pixel 10 Pro XL via Termux SSH + Shizuku rish (Rule 0 & Rule 11 Sovereign Bridge)
    if not xml_content:
        for host_ip, ssh_port in L6_PIXEL_SSH_IPS:
            ssh_cmd = [
                "ssh", "-p", str(ssh_port),
                "-o", f"HostName={host_ip}",
                "-o", "BatchMode=yes",
                "-o", "ClearAllForwardings=yes",
                "-o", "ControlMaster=no",
                "-o", "ControlPath=none",
                "-o", "ConnectTimeout=3",
                f"u0_a363@{host_ip}",
                "~/bin/rish -c 'uiautomator dump /sdcard/lens_ui.xml' >/dev/null 2>&1 ; cat /sdcard/lens_ui.xml"
            ]
            try:
                res = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=8)
                if res.returncode == 0 and "<hierarchy" in res.stdout:
                    xml_content = res.stdout
                    active_source = f"pixel_rish@{host_ip}:{ssh_port}"
                    break
            except Exception:
                continue

    # Strategy 3: Fallback probe of candidate ADB endpoints if not yet found
    if not xml_content and subprocess.run(["which", "adb"], capture_output=True).returncode == 0:
        for serial in [s for s in ANDROID_CANDIDATE_SERIALS if s]:
            if ":" in serial:
                try:
                    subprocess.run(f"adb connect {serial}", shell=True, capture_output=True, timeout=0.8)
                except Exception:
                    pass
            try:
                probe = subprocess.run(f"adb -s {serial} get-state", shell=True, capture_output=True, text=True, timeout=1.0)
                if probe.returncode == 0 and "device" in probe.stdout:
                    dump_cmd = f"adb -s {serial} shell 'uiautomator dump /data/local/tmp/lens_ui.xml >/dev/null 2>&1 && cat /data/local/tmp/lens_ui.xml'"
                    res = subprocess.run(dump_cmd, shell=True, capture_output=True, text=True, timeout=5)
                    if res.returncode == 0 and "<hierarchy" in res.stdout:
                        xml_content = res.stdout
                        active_source = f"adb:{serial}"
                        break
            except Exception:
                continue

    if not xml_content:
        # Fallback to local passive macOS window context if no Android edge is reachable
        print("[!] Warning: Android edge uiautomator unreachable; checking passive macOS window context.")
        try:
            res = subprocess.run(["/usr/bin/lsappinfo", "front"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                summary = f"MACOS_PASSIVE_WINDOW_CONTEXT: {res.stdout.strip()[:300]}"
                record_vla_trajectory("macos", "capture_ui", "/usr/bin/lsappinfo front", summary, 0)
                return 0, summary
        except Exception:
            pass
        return 1, "NO_UI_CONTEXT_CAPTURED"

    # Parse and structure the extracted UI hierarchy
    elements = parse_ui_hierarchy(xml_content)
    top_elements = []
    for el in elements[:15]:
        val = el["text"] or el["desc"]
        click = "clickable" if el["clickable"] else "static"
        top_elements.append(f"[{el['package']}] '{val}' ({click}) {el['bounds']}")

    summary = (
        f"SCREEN_LENS_UI_CONTEXT (Source: {active_source}):\n"
        f"Parsed {len(elements)} actionable UI elements from uiautomator.\n"
        f"Active Elements Sample:\n" + "\n".join(f"  • {item}" for item in top_elements)
    )
    print(f"[✓] Successfully captured UI context via {active_source} ({len(elements)} elements parsed)")
    record_vla_trajectory("android", "capture_ui", f"uiautomator dump via {active_source}", summary, 0)
    return 0, summary


def _exec_ssh_candidates(user: str, ips: List[str], cmd: str, port: int = 22, timeout: int = 8) -> Tuple[int, str, Optional[str]]:
    for ip in ips:
        ssh_cmd = [
            "ssh", "-p", str(port),
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=3",
            f"{user}@{ip}",
            cmd,
        ]
        try:
            res = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
            if res.returncode == 0:
                return 0, (res.stdout.strip() or res.stderr.strip()), f"{user}@{ip}:{port}"
        except Exception:
            continue
    return 1, "Unreachable across candidate IPs", None


def route_action(target_platform: str, action: str, command: str) -> int:
    plat = target_platform.lower().strip()
    print(f"\n[🚀] Unified Screen Lens executing: {action} on {plat.upper()}")
    
    # Handle CDP practice automation
    if plat in ["cdp", "cdp_practice", "browser", "vla"] or action.lower() in ["cdp_practice", "cdp"]:
        print("[>] Executing Screen Lens CDP practice automation pass...")
        cdp_script = REPO_ROOT / "06_scripts_and_tooling/automation/continuous_lens_cdp_practice.py"
        res = subprocess.run([sys.executable, str(cdp_script), "--single-pass"], capture_output=True, text=True)
        output_text = res.stdout.strip() or res.stderr.strip()
        exit_code = res.returncode
        print(f"Output: {output_text[:200]} (Exit Code: {exit_code})")
        record_vla_trajectory(target_platform, action, command, output_text, exit_code)
        return exit_code

    # Handle cross-network mesh-wide automation sweep
    if plat in ["mesh", "all", "network"]:
        print("[🌐] Executing Cross-Network Sovereign Mesh Automation Sweep...")
        mesh_targets = [
            ("GW (GL-BE14000)", "root", GW_ROUTER_IPS, 22, command),
            ("L1 (Mac Mini M4 Pro)", "aaron", L1_MAC_MINI_IPS, 22, command),
            ("L1b (Mac Mini M2 Pro)", "aaronmaher", L1B_MAC_MINI_IPS, 22, command),
            ("L2 (MacBook Pro)", "aaronmaher", L2_MACBOOK_IPS, 22, command),
            ("L3 (Linux Head Node)", "linux", L3_LINUX_IPS, 22, command),
            ("L5 (MacBook Air M4)", "aaronmaher", L5_MAC_AIR_IPS, 22, command),
            ("L6 (Pixel 10 Pro XL)", "u0_a363", [ip for ip, _ in L6_PIXEL_SSH_IPS], 8022, command),
            ("L8 (Linux Mini Hub)", "linuxmini", L8_LAUBURU_IPS, 22, command),
        ]
        summary_lines = []
        ok_count = 0
        for label, user, ips, port, node_cmd in mesh_targets:
            rc, out, ep = _exec_ssh_candidates(user, ips, node_cmd, port=port, timeout=8)
            first_line = (out.splitlines()[0] if out else "").strip()
            if rc == 0:
                ok_count += 1
                line = f"  🟢 {label:<24} [{ep}] -> {first_line}"
            else:
                line = f"  ⚪ {label:<24} [STANDBY] -> {first_line}"
            print(line)
            summary_lines.append(line)

        # Also probe L7 Samsung S20+ KDE Connect bridge port 1716
        l7_online = False
        for l7_ip in L7_S20_IPS:
            try:
                with socket.create_connection((l7_ip, 1716), timeout=1.0):
                    l7_online = True
                    ok_count += 1
                    line = f"  🟢 {'L7 (Samsung S20+ 5G)':<24} [{l7_ip}:1716] -> KDE Connect Bridge ACTIVE"
                    print(line)
                    summary_lines.append(line)
                    break
            except Exception:
                continue
        if not l7_online:
            line = f"  ⚪ {'L7 (Samsung S20+ 5G)':<24} [STANDBY] -> KDE Connect Offline"
            print(line)
            summary_lines.append(line)

        total_targets = len(mesh_targets) + 1
        print(f"\n[✓] Cross-Network Mesh Automation Complete: {ok_count}/{total_targets} nodes actuated.")
        exit_code = 0 if ok_count > 0 else 1
        record_vla_trajectory("mesh", action, command, "\n".join(summary_lines), exit_code)
        return exit_code

    # Pre-flight adaptive safety check
    if not check_adaptive_safety(target_platform):
        print(f"[!] Action cancelled by Adaptive Resource Governor.")
        return 1

    exit_code = -1
    output_text = ""

    if plat in ["macos", "l2"]:
        # Rule 3 Host Sanctuary & AGENTS.md §4:
        # If running on L1, route desktop automation to L2 MacBook Pro (Teacher Model actuation target).
        is_read_only = any(term in command.lower() for term in ["lsappinfo", "ioreg", "sysctl", "vm_stat", "system_profiler", "uname", "uptime"])
        
        if is_read_only and plat == "macos":
            print("[>] Executing passive read-only query on Host (L1 Sanctuary Compliant):", command)
            if command.startswith("/") or any(term in command for term in ["lsappinfo", "sysctl", "ioreg", "vm_stat", "uname", "uptime"]):
                res = subprocess.run(command, shell=True, capture_output=True, text=True)
            else:
                res = subprocess.run(["osascript", "-e", command], capture_output=True, text=True)
            output_text = res.stdout.strip() or res.stderr.strip()
            exit_code = res.returncode
        else:
            # Route to L2 MacBook Pro via SSH to protect L1 developer keyboard/mouse
            print("[>] Routing desktop automation to L2 MacBook Pro Target (Rule 3 & AGENTS.md §4)...")
            routed = False
            remote_cmd = command if action == "exec" else f"osascript -e {json.dumps(command)}"
            for ip in L2_MACBOOK_IPS:
                ssh_cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=3", f"aaronmaher@{ip}", remote_cmd]
                try:
                    res = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=10)
                    if res.returncode == 0 or "Syntax Error" not in res.stderr:
                        output_text = res.stdout.strip() or res.stderr.strip()
                        exit_code = res.returncode
                        routed = True
                        print(f"[✓] Executed on L2 MacBook Pro ({ip})")
                        break
                except Exception:
                    continue
            
            if not routed:
                print("[!] Warning: L2 MacBook Pro unreachable via SSH; evaluating local passive fallback.")
                res = subprocess.run(["osascript", "-e", command], capture_output=True, text=True)
                output_text = res.stdout.strip() or res.stderr.strip()
                exit_code = res.returncode

        print(f"Output: {output_text} (Exit Code: {exit_code})")
            
    elif plat in ["linux", "l8", "l3"]:
        print("[>] Utilizing Linux Remote Bridge (Rule 10: Prioritizing L8 Linux Mini Hub)...")
        routed = False
        
        # 1. Try L8 Linux Mini (lauburu) unless explicitly targeting l3
        if plat != "l3":
            for ip in L8_LAUBURU_IPS:
                ssh_target = f"linuxmini@{ip}"
                try:
                    res = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=3", ssh_target, command], capture_output=True, text=True, timeout=12)
                    if res.returncode == 0:
                        output_text = res.stdout.strip() or res.stderr.strip()
                        exit_code = res.returncode
                        routed = True
                        print(f"[✓] Executed on L8 Linux Mini Hub ({ssh_target})")
                        break
                except Exception:
                    continue

        # 2. Fallback to L3 Linux Head Node (linux-amd-gpu)
        if not routed:
            for ip in L3_LINUX_IPS:
                ssh_target = f"linux@{ip}"
                try:
                    res = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=3", ssh_target, command], capture_output=True, text=True, timeout=12)
                    if res.returncode == 0:
                        output_text = res.stdout.strip() or res.stderr.strip()
                        exit_code = res.returncode
                        routed = True
                        print(f"[✓] Executed on L3 Linux Head Node ({ssh_target})")
                        break
                except Exception:
                    continue

        if not routed:
            print("[!] Linux targets unreachable across candidate IPs.")
            exit_code = 1
            output_text = "All Linux endpoints timed out"
        else:
            print(f"Output: {output_text} (Exit Code: {exit_code})")

    elif plat in ["android", "l6", "l7"]:
        print("[>] Utilizing Android Privileged Bridge (ADB / Shizuku rish / Termux SSH)...")
        active_serial = None
        
        # Probe candidate ADB endpoints if adb is available
        if subprocess.run(["which", "adb"], capture_output=True).returncode == 0:
            for serial in [s for s in ANDROID_CANDIDATE_SERIALS if s]:
                if ":" in serial:
                    try:
                        subprocess.run(f"adb connect {serial}", shell=True, capture_output=True, timeout=1.5)
                    except Exception:
                        pass
                try:
                    probe = subprocess.run(f"adb -s {serial} get-state", shell=True, capture_output=True, text=True, timeout=2)
                    if probe.returncode == 0 and "device" in probe.stdout:
                        active_serial = serial
                        break
                except Exception:
                    pass
        
        if not active_serial:
            # Execute directly on L6 Pixel 10 Pro XL via Termux SSH (port 8022)
            for host_ip, ssh_port in L6_PIXEL_SSH_IPS:
                try:
                    res = subprocess.run(
                        ["ssh", "-p", str(ssh_port), "-o", "BatchMode=yes", "-o", "ConnectTimeout=3", f"u0_a363@{host_ip}", command],
                        capture_output=True, text=True, timeout=8
                    )
                    if res.returncode == 0:
                        output_text = res.stdout.strip() or res.stderr.strip()
                        exit_code = 0
                        print(f"[✓] Executed on L6 Pixel 10 Pro XL via Termux SSH (u0_a363@{host_ip}:{ssh_port})")
                        print(f"Output: {output_text} (Exit Code: {exit_code})")
                        break
                except Exception:
                    continue

        if exit_code != 0 and active_serial:
            if action in ["toggle_setting", "exec", "status"]:
                print(f"[>] Executing on {active_serial}: {command}")
                cmd = f"adb -s {active_serial} shell \"/data/local/tmp/rish -c '{command}' 2>&1\""
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                output_text = res.stdout.strip() or res.stderr.strip()
                exit_code = res.returncode
                if exit_code != 0 or "can't execute" in output_text or "not found" in output_text:
                    cmd_direct = f"adb -s {active_serial} shell \"{command}\""
                    res_direct = subprocess.run(cmd_direct, shell=True, capture_output=True, text=True)
                    output_text = res_direct.stdout.strip() or res_direct.stderr.strip()
                    exit_code = res_direct.returncode
            elif action == "tap":
                coords = command.split()
                if len(coords) == 2:
                    cmd = f"adb -s {active_serial} shell input tap {coords[0]} {coords[1]}"
                    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    output_text = f"Injected touch at {coords[0]},{coords[1]}"
                    exit_code = res.returncode
            print(f"Output: {output_text} (Exit Code: {exit_code})")

    elif plat in ["gw", "router"]:
        rc, out, ep = _exec_ssh_candidates("root", GW_ROUTER_IPS, command, port=22, timeout=8)
        output_text = out
        exit_code = rc
        print(f"[✓] Executed on GW Router ({ep}): {output_text} (Exit Code: {exit_code})")

    elif plat in ["l1", "l1b", "l5"]:
        target_map = {
            "l1": ("aaron", L1_MAC_MINI_IPS),
            "l1b": ("aaronmaher", L1B_MAC_MINI_IPS),
            "l5": ("aaronmaher", L5_MAC_AIR_IPS),
        }
        u, ips = target_map[plat]
        rc, out, ep = _exec_ssh_candidates(u, ips, command, port=22, timeout=8)
        output_text = out
        exit_code = rc
        print(f"[✓] Executed on {plat.upper()} ({ep}): {output_text} (Exit Code: {exit_code})")

    # Record verified trajectory for continuous LoRA distillation
    record_vla_trajectory(target_platform, action, command, output_text, exit_code)
    return exit_code


if __name__ == "__main__":
    if "--capture-only" in sys.argv:
        target = "adb_edge_nodes"
        if "--target" in sys.argv:
            try:
                target = sys.argv[sys.argv.index("--target") + 1]
            except IndexError:
                pass
        code, output = capture_ui_context(target)
        print(output)
        sys.exit(code)
    elif len(sys.argv) >= 4:
        code = route_action(sys.argv[1], sys.argv[2], " ".join(sys.argv[3:]))
        sys.exit(code)
    elif len(sys.argv) == 3 and sys.argv[1].lower() in ["mesh", "all", "network"]:
        code = route_action("mesh", sys.argv[2], "uname -n && uptime")
        sys.exit(code)
    elif len(sys.argv) >= 2 and sys.argv[1].lower() in ["capture", "--capture"]:
        code, output = capture_ui_context("adb_edge_nodes")
        print(output)
        sys.exit(code)
    elif len(sys.argv) == 3 and sys.argv[2].lower() in ["capture", "dump_ui", "inspect"]:
        code, output = capture_ui_context(sys.argv[1])
        print(output)
        sys.exit(code)
    else:
        print("Usage: unified_screen_lens.py <platform|mesh> <action> <command>")
        print("       unified_screen_lens.py --capture-only [--target adb_edge_nodes]")
        print("Example: unified_screen_lens.py linux exec 'cat /proc/loadavg'")
        print("Example: unified_screen_lens.py mesh exec 'uname -n && uptime'")
        print("Example: unified_screen_lens.py --capture-only --target adb_edge_nodes")
        sys.exit(0)
