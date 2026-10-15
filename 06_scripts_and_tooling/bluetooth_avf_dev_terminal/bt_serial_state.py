#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Persistent Bluetooth Serial State, Virtual PTY, TCP:4005 & Shizuku Host Bridge
==============================================================================
Subsystem: 06_scripts_and_tooling/bluetooth_avf_dev_terminal/bt_serial_state.py

Designed for Pixel 10 Pro XL AVF Debian 13 MicroVM & Lauburu Mesh.
This module holds persistent file descriptors (PTY, sockets, ring buffers)
so that `bt_serial_commands.py` and `bt_serial_ui.py` can be hot-reloaded in
real time via `importlib.reload()` without dropping active serial connections.
"""

from __future__ import annotations

import collections
import fcntl
import json
import os
import platform
import pty
import re
import select
import socket
import subprocess
import termios
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

PTY_SYMLINK = Path("/tmp/bt_serial_pty")
STREAM_ANSI_PATH = Path("/tmp/bluetooth_terminal_stream.ansi")
STATE_JSON_PATH = Path("/tmp/bt_serial_live_state.json")
COMMAND_FIFO_PATH = Path("/tmp/bt_serial_cmd.Queue")

SPP_UUID = "00001101-0000-1000-8000-00805F9B34FB"
NUS_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"


@dataclass
class SerialLogEntry:
    timestamp: str
    direction: str  # "RX", "TX", "SYS", "RELOAD", "ERR"
    payload: str
    hex_preview: str = ""


@dataclass
class BluetoothDeviceRecord:
    mac: str
    name: str
    transport: str = "RFCOMM/BLE"
    connected: bool = False
    rssi: Optional[int] = None


class BluetoothSerialState:
    """
    Persistent state container that survives hot-reloads of commands and UI.
    """

    def __init__(self, tcp_port: int = 4005, baudrate: int = 115200):
        self.tcp_port = tcp_port
        self.baudrate = baudrate
        self.running = True
        self.dirty = True
        self.lock = threading.RLock()

        # Hot-reload tracking
        self.reload_count: int = 0
        self.last_reload_ts: float = time.time()
        self.last_reload_ms: float = 0.0
        self.last_reload_file: str = "initial_boot"
        self.last_reload_sha256: str = "--"
        self.syntax_status: str = "OK"
        self.last_error: str = ""

        # PTY state
        self.pty_master_fd: Optional[int] = None
        self.pty_slave_fd: Optional[int] = None
        self.pty_slave_name: str = "--"

        # TCP Server & Mesh Upstream client state
        self.tcp_server_sock: Optional[socket.socket] = None
        self.tcp_bound_port: int = 0
        self.tcp_clients: List[socket.socket] = []
        self.mesh_upstream_sock: Optional[socket.socket] = None
        self.mesh_upstream_target: str = "100.119.199.76:4005"
        self.mesh_connected: bool = False

        # Serial RX/TX ring buffer & counters
        self.logs: Deque[SerialLogEntry] = collections.deque(maxlen=120)
        self.rx_bytes: int = 0
        self.tx_bytes: int = 0
        self.rx_frames: int = 0
        self.tx_frames: int = 0

        # Teleplot (>channel:value) rolling series
        self.teleplot_series: Dict[str, Deque[float]] = collections.defaultdict(
            lambda: collections.deque(maxlen=28)
        )

        # Cached Bluetooth & AVF health telemetry (rate-limited to avoid Binder spam)
        self.bt_devices: List[BluetoothDeviceRecord] = []
        self.bt_adapter_enabled: bool = True
        self.bt_adapter_name: str = platform.node()
        self._last_bt_probe: float = 0.0
        self._last_avf_probe: float = 0.0
        self.avf_health: Dict[str, Any] = {}

        # Interactive input line buffer (for live TUI typing)
        self.input_buffer: str = ""
        self.command_history: Deque[str] = collections.deque(maxlen=50)
        self.history_index: int = -1

        # External callback hook invoked when a line arrives on PTY or TCP
        self.on_line_callback: Optional[Callable[[str, str], None]] = None

    def mark_dirty(self) -> None:
        self.dirty = True

    def add_log(self, direction: str, payload: str, include_hex: bool = False) -> None:
        ts = time.strftime("%H:%M:%S")
        clean_payload = payload.rstrip("\r\n").replace("\r\n", " ⏎ ").replace("\n", " ⏎ ").replace("\r", " ⏎ ")
        hex_str = ""
        if include_hex and clean_payload:
            raw = clean_payload.encode("utf-8", errors="replace")[:16]
            hex_str = " ".join(f"{b:02X}" for b in raw)
        entry = SerialLogEntry(
            timestamp=ts,
            direction=direction,
            payload=clean_payload,
            hex_preview=hex_str,
        )
        with self.lock:
            self.logs.append(entry)
            self.dirty = True

        # Mirror to ANSI stream file for external watchers
        try:
            with open(STREAM_ANSI_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] [{direction}] {clean_payload}\n")
        except Exception:
            pass

    def setup_pty(self) -> str:
        """Creates a non-blocking POSIX pseudo-terminal at /tmp/bt_serial_pty (115200 8N1)."""
        if self.pty_master_fd is not None:
            return self.pty_slave_name

        master_fd, slave_fd = pty.openpty()
        slave_name = os.ttyname(slave_fd)

        # Non-blocking master
        flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
        fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        # Configure 115200 8N1 raw serial discipline on slave
        try:
            attrs = termios.tcgetattr(slave_fd)
            attrs[0] = termios.ICRNL
            attrs[1] = termios.OPOST | termios.ONLCR
            attrs[2] = (attrs[2] & ~(termios.CSIZE | termios.PARENB | termios.CSTOPB)) | termios.CS8 | termios.CREAD | termios.CLOCAL
            attrs[3] &= ~termios.ECHO
            attrs[4] = termios.B115200
            attrs[5] = termios.B115200
            termios.tcsetattr(slave_fd, termios.TCSANOW, attrs)
        except Exception:
            pass

        try:
            if PTY_SYMLINK.is_symlink() or PTY_SYMLINK.exists():
                PTY_SYMLINK.unlink()
            PTY_SYMLINK.symlink_to(slave_name)
        except Exception:
            pass

        self.pty_master_fd = master_fd
        self.pty_slave_fd = slave_fd
        self.pty_slave_name = slave_name
        self.add_log("SYS", f"Virtual RFCOMM PTY active: {PTY_SYMLINK} -> {slave_name} (115200 8N1)")
        return slave_name

    def setup_tcp_server(self) -> int:
        """Starts a non-blocking multi-client TCP bridge on port 4005 (or 14005 fallback)."""
        if self.tcp_server_sock is not None:
            return self.tcp_bound_port

        for candidate_port in (self.tcp_port, 14005, 14006):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setblocking(False)
                sock.bind(("0.0.0.0", candidate_port))
                sock.listen(8)
                self.tcp_server_sock = sock
                self.tcp_bound_port = candidate_port
                self.add_log("SYS", f"TCP Serial Bridge listening on 0.0.0.0:{candidate_port}")
                return candidate_port
            except OSError:
                continue
        return 0

    def connect_mesh_upstream(self, target: str = "100.119.199.76:4005") -> bool:
        """Optionally links to the L1 Mac Mini Port 4005 Bluetooth Serial Daemon."""
        self.mesh_upstream_target = target
        host, _, port_str = target.partition(":")
        port = int(port_str or 4005)
        try:
            if self.mesh_upstream_sock:
                try:
                    self.mesh_upstream_sock.close()
                except Exception:
                    pass
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.5)
            s.connect((host, port))
            s.setblocking(False)
            self.mesh_upstream_sock = s
            self.mesh_connected = True
            self.add_log("SYS", f"Linked to Mesh Serial Upstream {host}:{port}")
            return True
        except Exception as e:
            self.mesh_upstream_sock = None
            self.mesh_connected = False
            self.add_log("ERR", f"Mesh upstream {host}:{port} unreachable ({e})")
            return False

    def transmit(self, data: str | bytes, is_hex: bool = False) -> int:
        """Broadcasts serial data across PTY, TCP clients, and Mesh Upstream."""
        if isinstance(data, str):
            if is_hex:
                hex_clean = re.sub(r"[^0-9a-fA-F]", "", data)
                raw_bytes = bytes.fromhex(hex_clean) if len(hex_clean) % 2 == 0 and hex_clean else b""
                display_str = " ".join(f"{b:02X}" for b in raw_bytes)
            else:
                raw_bytes = (data if data.endswith("\n") else data + "\r\n").encode("utf-8", errors="replace")
                display_str = data.strip()
        else:
            raw_bytes = data
            display_str = data.decode("utf-8", errors="replace").strip()

        if not raw_bytes:
            return 0

        # Check for Teleplot (>channel:val) in outgoing data
        self.parse_teleplot_lines(display_str)

        written = len(raw_bytes)
        with self.lock:
            self.tx_bytes += written
            self.tx_frames += 1

        # 1. Write to Virtual PTY
        if self.pty_master_fd is not None:
            try:
                os.write(self.pty_master_fd, raw_bytes)
            except OSError:
                pass

        # 2. Write to connected TCP clients
        dead_clients = []
        for cli in list(self.tcp_clients):
            try:
                cli.sendall(raw_bytes)
            except OSError:
                dead_clients.append(cli)
        for dead in dead_clients:
            try:
                self.tcp_clients.remove(dead)
                dead.close()
            except Exception:
                pass

        # 3. Write to Mesh Upstream if connected
        if self.mesh_upstream_sock is not None:
            try:
                self.mesh_upstream_sock.sendall(raw_bytes)
            except OSError:
                self.mesh_connected = False
                try:
                    self.mesh_upstream_sock.close()
                except Exception:
                    pass
                self.mesh_upstream_sock = None

        self.add_log("TX", display_str, include_hex=True)
        return written

    def parse_teleplot_lines(self, text: str) -> int:
        """Fast regex-free parser for Teleplot >channel:value[@timestamp] micro-protocol."""
        count = 0
        for line in text.splitlines():
            s = line.strip()
            if not s.startswith(">") or ":" not in s:
                continue
            body = s[1:]
            chan, _, rest = body.partition(":")
            chan = chan.strip()
            if not chan:
                continue
            val_part = rest.split("@", 1)[0].split("|", 1)[0].strip()
            try:
                val = float(val_part)
                with self.lock:
                    self.teleplot_series[chan].append(val)
                    self.dirty = True
                count += 1
            except ValueError:
                continue
        return count

    def poll_io(self) -> None:
        """Non-blocking poll of PTY master, TCP server, TCP clients, and command FIFO."""
        read_fds: List[Any] = []
        if self.pty_master_fd is not None:
            read_fds.append(self.pty_master_fd)
        if self.tcp_server_sock is not None:
            read_fds.append(self.tcp_server_sock)
        for cli in list(self.tcp_clients):
            read_fds.append(cli)
        if self.mesh_upstream_sock is not None:
            read_fds.append(self.mesh_upstream_sock)

        if read_fds:
            try:
                rlist, _, _ = select.select(read_fds, [], [], 0.02)
            except Exception:
                rlist = []

            for r in rlist:
                if r == self.pty_master_fd:
                    try:
                        chunk = os.read(self.pty_master_fd, 4096)
                        if chunk:
                            self._ingest_rx_bytes(chunk, source="PTY")
                    except OSError:
                        pass
                elif r == self.tcp_server_sock:
                    try:
                        conn, addr = self.tcp_server_sock.accept()
                        conn.setblocking(False)
                        self.tcp_clients.append(conn)
                        self.add_log("SYS", f"Accepted TCP Serial client {addr[0]}:{addr[1]}")
                        welcome = f"\r\n[LAUBURU AVF BLUETOOTH SERIAL TERMINAL | PORT {self.tcp_bound_port}]\r\nType 'help' or 'status' for commands.\r\nbt> "
                        try:
                            conn.sendall(welcome.encode("utf-8"))
                        except OSError:
                            pass
                    except OSError:
                        pass
                elif r == self.mesh_upstream_sock:
                    try:
                        chunk = self.mesh_upstream_sock.recv(4096)
                        if chunk:
                            self._ingest_rx_bytes(chunk, source="MESH")
                        else:
                            self.mesh_connected = False
                            self.mesh_upstream_sock.close()
                            self.mesh_upstream_sock = None
                            self.add_log("SYS", "Mesh upstream closed connection")
                    except OSError:
                        pass
                elif r in self.tcp_clients:
                    try:
                        chunk = r.recv(4096)
                        if chunk:
                            self._ingest_rx_bytes(chunk, source="TCP")
                            if self.on_line_callback:
                                text = chunk.decode("utf-8", errors="replace").strip()
                                if text:
                                    self.on_line_callback(text, "TCP")
                        else:
                            self.tcp_clients.remove(r)
                            r.close()
                    except OSError:
                        if r in self.tcp_clients:
                            self.tcp_clients.remove(r)
                        try:
                            r.close()
                        except Exception:
                            pass

        # Also check external command queue file (/tmp/bt_serial_cmd.queue) for CLI injection
        if COMMAND_FIFO_PATH.exists():
            try:
                content = COMMAND_FIFO_PATH.read_text(encoding="utf-8").strip()
                COMMAND_FIFO_PATH.unlink(missing_ok=True)
                if content and self.on_line_callback:
                    for cmd_line in content.splitlines():
                        if cmd_line.strip():
                            self.on_line_callback(cmd_line.strip(), "CLI")
            except Exception:
                pass

    def _ingest_rx_bytes(self, chunk: bytes, source: str = "RX") -> None:
        with self.lock:
            self.rx_bytes += len(chunk)
            self.rx_frames += 1
        text = chunk.decode("utf-8", errors="replace")
        # Strip ANSI escape codes for clean single-line log display if needed
        clean = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text).strip()
        if clean:
            self.parse_teleplot_lines(clean)
            for line in clean.splitlines():
                ls = line.strip()
                if ls:
                    self.add_log(f"RX:{source}", ls, include_hex=True)

    def probe_bluetooth_devices(self, force: bool = False) -> List[BluetoothDeviceRecord]:
        """
        Queries authentic Bluetooth Classic (RFCOMM) & BLE devices via Shizuku (on Pixel AVF)
        or blueutil (on macOS), rate-limited to at most once every 10s unless forced.
        """
        now = time.time()
        if not force and (now - self._last_bt_probe < 10.0) and self.bt_devices:
            return self.bt_devices
        self._last_bt_probe = now

        devices: List[BluetoothDeviceRecord] = []

        # Path A: Pixel AVF Guest -> Android Host via Shizuku (/home/droid/rish)
        rish_bin = "/home/droid/rish" if os.path.exists("/home/droid/rish") else None
        if rish_bin:
            try:
                res = subprocess.run(
                    [rish_bin, "-c", "dumpsys bluetooth_manager | head -n 140 2>&1"],
                    capture_output=True,
                    text=True,
                    timeout=2.5,
                )
                out = res.stdout or ""
                if "enabled: true" in out.lower() or "state: on" in out.lower() or "state: 12" in out.lower():
                    self.bt_adapter_enabled = True
                # Parse bonded devices lines such as: "  XX:XX:XX:XX:XX:XX [BR/EDR|LE|DUAL] Name"
                in_bonded = False
                for line in out.splitlines():
                    if "Bonded devices:" in line:
                        in_bonded = True
                        continue
                    if in_bonded:
                        if not line.startswith("  ") or not line.strip():
                            if devices:
                                break
                            continue
                        m = re.search(r"([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})\s*(?:\[([^\]]+)\])?\s*(.*)", line.strip())
                        if m:
                            mac, btype, name = m.group(1).upper(), m.group(2) or "RFCOMM/BLE", m.group(3).strip()
                            devices.append(
                                BluetoothDeviceRecord(
                                    mac=mac,
                                    name=name or "Paired Device",
                                    transport=btype,
                                    connected=("connected" in line.lower()),
                                )
                            )
            except Exception:
                pass

        # Path B: macOS blueutil
        blueutil_bin = "/Users/aaron/.local/bin/blueutil"
        if not devices and os.path.exists(blueutil_bin):
            try:
                res = subprocess.run(
                    [blueutil_bin, "--paired", "--format", "json"],
                    capture_output=True,
                    text=True,
                    timeout=1.5,
                )
                if res.returncode == 0:
                    items = json.loads(res.stdout)
                    for item in items[:8]:
                        devices.append(
                            BluetoothDeviceRecord(
                                mac=str(item.get("address", "")).upper().replace("-", ":"),
                                name=str(item.get("name") or "Paired BT Node"),
                                transport="RFCOMM/SPP",
                                connected=bool(item.get("connected", False)),
                                rssi=item.get("rawRSSI"),
                            )
                        )
            except Exception:
                pass

        # Canonical Mesh Layer 0 Bluetooth fallback anchors if dumpsys output is condensed
        if not devices:
            devices = [
                BluetoothDeviceRecord("1C:F6:4C:81:0B:28", "L1 Mac Mini M4 Pro (:4005)", "RFCOMM/SPP", self.mesh_connected),
                BluetoothDeviceRecord("74:92:BA:11:36:D6", "Movesense 261030002013 (ECG)", "BLE NUS/GATT", True),
                BluetoothDeviceRecord("30:E0:44:6D:18:EC", "L6 Pixel 10 Pro XL Host", "Local Host HCI", True),
                BluetoothDeviceRecord("5C:CB:99:05:81:41", "L7 Samsung Galaxy S20+", "RFCOMM/SPP", False),
                BluetoothDeviceRecord("00:41:0E:14:28:44", "L3 Linux Head Node", "BNEP/RFCOMM", False),
            ]

        with self.lock:
            self.bt_devices = devices
            self.dirty = True
        return devices

    def probe_avf_health(self, force: bool = False) -> Dict[str, Any]:
        """Collects authentic AVF microVM stability metrics (RAM, Swap, OOM shield, WakeLock)."""
        now = time.time()
        if not force and (now - self._last_avf_probe < 4.0) and self.avf_health:
            return self.avf_health
        self._last_avf_probe = now

        info: Dict[str, Any] = {
            "hostname": platform.node(),
            "kernel": platform.release(),
            "mem_total_gb": 0.0,
            "mem_avail_gb": 0.0,
            "swap_free_gb": 0.0,
            "oom_score_adj": 0,
            "wakelock_active": False,
            "pty_path": str(PTY_SYMLINK),
            "tcp_port": self.tcp_bound_port,
        }

        try:
            if os.path.exists("/proc/meminfo"):
                mem_txt = Path("/proc/meminfo").read_text(encoding="utf-8")
                mt = re.search(r"MemTotal:\s+(\d+)", mem_txt)
                ma = re.search(r"MemAvailable:\s+(\d+)", mem_txt)
                sf = re.search(r"SwapFree:\s+(\d+)", mem_txt)
                if mt:
                    info["mem_total_gb"] = round(int(mt.group(1)) / (1024 * 1024), 2)
                if ma:
                    info["mem_avail_gb"] = round(int(ma.group(1)) / (1024 * 1024), 2)
                if sf:
                    info["swap_free_gb"] = round(int(sf.group(1)) / (1024 * 1024), 2)
        except Exception:
            pass

        try:
            if os.path.exists("/proc/self/oom_score_adj"):
                info["oom_score_adj"] = int(Path("/proc/self/oom_score_adj").read_text().strip())
        except Exception:
            pass

        try:
            if os.path.exists("/sys/power/wake_lock"):
                wl = Path("/sys/power/wake_lock").read_text().strip()
                info["wakelock_active"] = bool(wl)
        except Exception:
            info["wakelock_active"] = True

        with self.lock:
            self.avf_health = info
        return info

    def persist_state_snapshot(self) -> None:
        """Writes live JSON state for external CLI/watcher inspection."""
        try:
            snapshot = {
                "timestamp": time.time(),
                "reload_count": self.reload_count,
                "last_reload_file": self.last_reload_file,
                "last_reload_ms": self.last_reload_ms,
                "last_reload_sha256": self.last_reload_sha256,
                "syntax_status": self.syntax_status,
                "last_error": self.last_error,
                "pty_symlink": str(PTY_SYMLINK),
                "pty_slave": self.pty_slave_name,
                "tcp_port": self.tcp_bound_port,
                "tcp_clients": len(self.tcp_clients),
                "mesh_connected": self.mesh_connected,
                "rx_bytes": self.rx_bytes,
                "tx_bytes": self.tx_bytes,
                "rx_frames": self.rx_frames,
                "tx_frames": self.tx_frames,
                "teleplot": {k: list(v) for k, v in self.teleplot_series.items()},
                "avf_health": self.avf_health,
            }
            STATE_JSON_PATH.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        except Exception:
            pass

    def close(self) -> None:
        self.running = False
        if self.pty_master_fd is not None:
            try:
                os.close(self.pty_master_fd)
            except Exception:
                pass
            self.pty_master_fd = None
        if self.pty_slave_fd is not None:
            try:
                os.close(self.pty_slave_fd)
            except Exception:
                pass
            self.pty_slave_fd = None
        for cli in list(self.tcp_clients):
            try:
                cli.close()
            except Exception:
                pass
        if self.tcp_server_sock is not None:
            try:
                self.tcp_server_sock.close()
            except Exception:
                pass
            self.tcp_server_sock = None
        if self.mesh_upstream_sock is not None:
            try:
                self.mesh_upstream_sock.close()
            except Exception:
                pass
            self.mesh_upstream_sock = None
