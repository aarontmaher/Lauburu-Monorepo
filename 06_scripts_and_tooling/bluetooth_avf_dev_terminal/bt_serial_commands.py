#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hot-Reloadable Bluetooth Serial Terminal Command & Protocol Engine
==================================================================
Subsystem: 06_scripts_and_tooling/bluetooth_avf_dev_terminal/bt_serial_commands.py

🔥 LIVE DEV MODE MODULE:
Edit and save this file at any time while `tmux --dev` or `zellij --dev` is running!
`bt_serial_terminal.py` automatically validates AST syntax and hot-reloads this
module in <50ms without dropping your active PTY (/tmp/bt_serial_pty) or TCP (:4005)
serial connections.
"""

from __future__ import annotations

import json
import math
import os
import re
import socket
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from bt_serial_state import BluetoothSerialState

PLUGIN_VERSION = "2.1.0-LIVE-DEV"

# ==============================================================================
# ⚡ LIVE-EDITABLE CUSTOM COMMAND REGISTRY
# Add or modify entries below (or run `patch <cmd> <text>` in the terminal)
# and save the file to see instant zero-downtime hot-reload in action!
# ==============================================================================
# BEGIN_CUSTOM_COMMANDS
CUSTOM_COMMANDS: Dict[str, str] = {
    "ping": "PONG (115200 8N1 RFCOMM/PTY Zero-Latency Loopback)",
    "version": "Lauburu AVF Bluetooth Serial Terminal v2.1.0-LIVE-DEV",
    "whoami": "Pixel 10 Pro XL (Tensor G5 AVF Debian 13 MicroVM + Shizuku UID 2000)",
}
# END_CUSTOM_COMMANDS


def on_hot_reload(state: "BluetoothSerialState") -> None:
    """Hook automatically invoked whenever this module is hot-reloaded."""
    state.add_log(
        "RELOAD",
        f"Hot-reloaded bt_serial_commands.py ({PLUGIN_VERSION}, {len(CUSTOM_COMMANDS)} custom cmds)",
    )


def execute_command(state: "BluetoothSerialState", raw_line: str, source: str = "TUI") -> str:
    """
    Executes an interactive command from the TUI, TCP client, or CLI queue.
    Returns the formatted response string and logs it into the serial stream.
    """
    line = raw_line.strip()
    if not line:
        return ""

    state.add_log("CMD", f"({source}) > {line}")
    parts = line.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    # 1. Check live-editable CUSTOM_COMMANDS first
    if cmd in CUSTOM_COMMANDS:
        resp = CUSTOM_COMMANDS[cmd]
        state.add_log("SYS", f"[{cmd}] {resp}")
        return resp

    # 2. Built-in commands
    if cmd in ("help", "?"):
        custom_keys = ", ".join(sorted(CUSTOM_COMMANDS.keys())) or "none"
        msg = (
            "Commands: status | scan | connect [host:port|mac] | send <ascii> | tx <hex> | "
            "teleplot [chan:val|demo] | movesense | shizuku <cmd> | avf | mesh | "
            f"patch <cmd> <reply> | reload | clear | Custom: [{custom_keys}]"
        )
        state.add_log("SYS", msg)
        return msg

    if cmd in ("clear", "cls"):
        with state.lock:
            state.logs.clear()
        state.add_log("SYS", "Serial stream buffer cleared.")
        return "Cleared."

    if cmd in ("status", "bt", "devices"):
        devs = state.probe_bluetooth_devices(force=True)
        summary = f"BT Adapter: {'ON' if state.bt_adapter_enabled else 'OFF'} | {len(devs)} Bonded Devices | PTY: {state.pty_slave_name} | TCP: :{state.tcp_bound_port}"
        state.add_log("SYS", summary)
        for d in devs[:6]:
            state.add_log("SYS", f"  • {d.mac} [{d.transport}] {d.name} ({'CONNECTED' if d.connected else 'PAIRED'})")
        return summary

    if cmd == "scan":
        state.add_log("SYS", "Triggering Bluetooth discovery & refreshing bonded devices...")
        if os.path.exists("/home/droid/rish"):
            try:
                subprocess.run(
                    ["/home/droid/rish", "-c", "cmd bluetooth_manager enable 2>&1"],
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                )
            except Exception:
                pass
        devs = state.probe_bluetooth_devices(force=True)
        msg = f"Scan complete: {len(devs)} Bluetooth serial/BLE endpoints indexed."
        state.add_log("SYS", msg)
        return msg

    if cmd == "connect":
        target = arg or "100.119.199.76:4005"
        if ":" in target and target.count(":") == 1:
            ok = state.connect_mesh_upstream(target)
            return f"Connected to {target}" if ok else f"Failed to connect to {target}"
        else:
            # Bluetooth MAC connection via Shizuku intent
            state.add_log("SYS", f"Requesting Android RFCOMM/BLE link to {target}...")
            if os.path.exists("/home/droid/rish"):
                try:
                    subprocess.run(
                        [
                            "/home/droid/rish",
                            "-c",
                            "am start -n de.kai_morich.serial_bluetooth_terminal/.MainActivity 2>&1",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=2.5,
                    )
                except Exception:
                    pass
            return f"Dispatched RFCOMM/BLE bridge intent for {target}"

    if cmd in ("send", "write", "echo"):
        if not arg:
            state.add_log("ERR", "Usage: send <ascii_payload>")
            return "Usage: send <ascii_payload>"
        n = state.transmit(arg, is_hex=False)
        return f"Transmitted {n} bytes (ASCII)"

    if cmd in ("tx", "hex"):
        if not arg:
            state.add_log("ERR", "Usage: tx <hex_bytes> (e.g. tx 01 02 AA FF)")
            return "Usage: tx <hex_bytes>"
        n = state.transmit(arg, is_hex=True)
        return f"Transmitted {n} bytes (HEX)"

    if cmd in ("teleplot", "tp"):
        if not arg or arg.lower() == "demo":
            base_t = time.time()
            for step in range(12):
                t = base_t + step * 0.45
                hr = round(68.0 + 5.5 * math.sin(t), 1)
                rmssd = round(54.0 + 7.0 * math.cos(t * 0.7), 1)
                rssi = round(-48.0 + 4.0 * math.sin(t * 1.1), 1)
                state.parse_teleplot_lines(f">hr_bpm:{hr}\n>rmssd_ms:{rmssd}\n>bt_rssi_dbm:{rssi}")
            sample = f">hr_bpm:{hr}\n>rmssd_ms:{rmssd}\n>bt_rssi_dbm:{rssi}"
            state.transmit(sample, is_hex=False)
            return f"Injected Teleplot burst: HR={hr} BPM, RMSSD={rmssd} ms, RSSI={rssi} dBm"
        else:
            formatted = arg if arg.startswith(">") else f">{arg}"
            state.transmit(formatted, is_hex=False)
            return f"Emitted Teleplot frame: {formatted}"

    if cmd == "movesense":
        # Probe local AVF movesense.service (:8086) or state file
        for url in ("http://127.0.0.1:8086/api/status", "http://127.0.0.1:8086/health"):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "BTSerialDev/2.1"})
                with urllib.request.urlopen(req, timeout=1.2) as r:
                    data = r.read().decode("utf-8", errors="replace")[:200]
                    msg = f"Movesense (:8086) ONLINE -> {data}"
                    state.add_log("SYS", msg)
                    return msg
            except Exception:
                continue
        msg = "Movesense 261030002013 (74:92:BA:11:36:D6) | Sole BLE Owner: Pixel 10 (L6) | Waiting for chest strap wake"
        state.add_log("SYS", msg)
        return msg

    if cmd == "shizuku":
        sub_cmd = arg or "id && getprop ro.product.model"
        rish_bin = "/home/droid/rish" if os.path.exists("/home/droid/rish") else "rish"
        try:
            res = subprocess.run(
                [rish_bin, "-c", f"{sub_cmd} 2>&1"],
                capture_output=True,
                text=True,
                timeout=3.0,
            )
            out = (res.stdout or res.stderr or "").strip().replace("\n", " | ")[:220]
            msg = f"Shizuku (rc={res.returncode}): {out}"
            state.add_log("SYS", msg)
            return msg
        except Exception as e:
            msg = f"Shizuku error: {e}"
            state.add_log("ERR", msg)
            return msg

    if cmd in ("avf", "shield", "health"):
        h = state.probe_avf_health(force=True)
        msg = (
            f"AVF Shield: Host={h.get('hostname')} | Kernel={h.get('kernel')} | "
            f"RAM Avail={h.get('mem_avail_gb')}/{h.get('mem_total_gb')} GB | "
            f"Swap Free={h.get('swap_free_gb')} GB | OOM_Adj={h.get('oom_score_adj')} | "
            f"WakeLock={'ACTIVE' if h.get('wakelock_active') else 'STANDBY'}"
        )
        state.add_log("SYS", msg)
        return msg

    if cmd in ("mesh", "nodes"):
        targets = [
            ("L1 Mac Mini", "100.119.199.76", 4005),
            ("L3 Linux Head", "100.101.39.98", 22),
            ("L5 MacBook Air", "100.121.202.34", 22),
            ("L8 Linux Hub", "100.121.247.8", 22),
        ]
        results = []
        for name, ip, port in targets:
            t0 = time.perf_counter()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.35)
            ok = s.connect_ex((ip, port)) == 0
            s.close()
            rtt = round((time.perf_counter() - t0) * 1000, 1)
            results.append(f"{name}: {'ONLINE (' + str(rtt) + 'ms)' if ok else 'STANDBY'}")
        msg = " | ".join(results)
        state.add_log("SYS", msg)
        return msg

    if cmd == "patch":
        # Live self-patching command: `patch <new_cmd> <response_text>`
        # Writes directly to bt_serial_commands.py on disk, triggering the real-time hot-reload watcher!
        sub_parts = arg.split(maxsplit=1)
        if len(sub_parts) < 2:
            msg = "Usage: patch <command_name> <response_text>"
            state.add_log("ERR", msg)
            return msg
        new_cmd, new_resp = sub_parts[0].lower().strip(), sub_parts[1].strip()
        ok, err = patch_custom_command_on_disk(new_cmd, new_resp)
        if ok:
            msg = f"Patched '{new_cmd}' into bt_serial_commands.py on disk -> Hot-reloading now!"
            state.add_log("RELOAD", msg)
            return msg
        else:
            msg = f"Patch failed: {err}"
            state.add_log("ERR", msg)
            return msg

    # Default: transmit unknown command as raw serial frame over PTY & TCP:4005
    n = state.transmit(line, is_hex=False)
    return f"Sent raw serial frame ({n}B): {line}"


def patch_custom_command_on_disk(cmd_name: str, response_text: str) -> tuple[bool, str]:
    """
    Updates CUSTOM_COMMANDS in bt_serial_commands.py on disk so the live watcher
    hot-reloads the module in real time.
    """
    try:
        file_path = Path(__file__).resolve()
        source = file_path.read_text(encoding="utf-8")
        updated_dict = dict(CUSTOM_COMMANDS)
        updated_dict[cmd_name] = response_text

        dict_lines = [
            "# BEGIN_CUSTOM_COMMANDS",
            "CUSTOM_COMMANDS: Dict[str, str] = {",
        ]
        for k, v in updated_dict.items():
            dict_lines.append(f"    {json.dumps(k)}: {json.dumps(v)},")
        dict_lines.append("}")
        dict_lines.append("# END_CUSTOM_COMMANDS")
        replacement = "\n".join(dict_lines)

        pattern = r"# BEGIN_CUSTOM_COMMANDS.*?# END_CUSTOM_COMMANDS"
        new_source, count = re.subn(
            pattern,
            replacement,
            source,
            count=1,
            flags=re.DOTALL,
        )
        if count == 0:
            return False, "CUSTOM_COMMANDS markers not found"
        file_path.write_text(new_source, encoding="utf-8")
        return True, ""
    except Exception as e:
        return False, str(e)
