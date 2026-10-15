#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hot-Reloadable Rich Terminal UI for the Pixel AVF Bluetooth Serial Terminal
===========================================================================
Subsystem: 06_scripts_and_tooling/bluetooth_avf_dev_terminal/bt_serial_ui.py

🔥 LIVE DEV MODE UI MODULE:
Modify any panel, color, table column, or sparkline style in this file and save!
The running terminal hot-reloads `bt_serial_ui.py` in real time (<250ms) without
losing serial state or dropping active connections.
"""

from __future__ import annotations

import shutil
import time
from typing import TYPE_CHECKING, Dict, List

from rich.console import Group
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from bt_serial_state import BluetoothSerialState

UI_THEME_VERSION = "2.1.0-AVF-SAFE"
SPARK_CHARS = " ▂▃▄▅▆▇█"


def render_sparkline(values: List[float]) -> str:
    if not values:
        return "─" * 12
    lo = min(values)
    hi = max(values)
    span = (hi - lo) if hi != lo else 1.0
    out = []
    for v in values[-18:]:
        idx = int(((v - lo) / span) * (len(SPARK_CHARS) - 1))
        idx = max(0, min(len(SPARK_CHARS) - 1, idx))
        out.append(SPARK_CHARS[idx])
    return "".join(out)


def build_header_panel(state: "BluetoothSerialState", custom_commands: Dict[str, str]) -> Panel:
    h = state.probe_avf_health(force=False)
    syntax_ok = state.syntax_status == "OK"
    reload_badge_style = "bold black on bright_green" if syntax_ok else "bold white on red"
    reload_badge = (
        f" 🔥 LIVE HOT-RELOAD #{state.reload_count} ({state.last_reload_ms:.1f}ms) | SYNTAX: {state.syntax_status} "
    )

    t = Text()
    t.append("🛰️  LAUBURU PIXEL AVF BLUETOOTH SERIAL TERMINAL ", style="bold bright_cyan")
    t.append(reload_badge, style=reload_badge_style)
    t.append(f" [{UI_THEME_VERSION}]\n", style="dim cyan")

    # Line 2: Serial Transports & Counters
    mesh_str = f"LINKED ({state.mesh_upstream_target})" if state.mesh_connected else "LOCAL-STANDALONE"
    t.append("Transports: ", style="bold white")
    t.append(f"PTY {state.pty_slave_name} (115200 8N1)", style="bold green")
    t.append(" • ", style="dim")
    t.append(f"TCP :{state.tcp_bound_port} ({len(state.tcp_clients)} clients)", style="bold cyan")
    t.append(" • ", style="dim")
    t.append(f"Mesh: {mesh_str}", style="bold yellow" if not state.mesh_connected else "bold green")
    t.append(f" | RX: {state.rx_bytes}B ({state.rx_frames}) TX: {state.tx_bytes}B ({state.tx_frames})\n", style="white")

    # Line 3: AVF Crash Shield & Hot-Reload File Info
    wl_str = "LOCKED" if h.get("wakelock_active") else "STANDBY"
    t.append("AVF Shield: ", style="bold white")
    t.append(
        f"RAM {h.get('mem_avail_gb', 0.0):.1f}/{h.get('mem_total_gb', 0.0):.1f}GB Free • "
        f"Swap {h.get('swap_free_gb', 0.0):.1f}GB • WakeLock: {wl_str} • OOM_Adj: {h.get('oom_score_adj', 0)}",
        style="bold bright_green",
    )
    t.append(
        f" | Last File: {state.last_reload_file} [{state.last_reload_sha256[:8]}]",
        style="dim white",
    )
    if state.last_error:
        t.append(f"\n⚠️  Hot-Reload Compiler Guard Caught Error: {state.last_error}", style="bold red")

    return Panel(t, border_style="bright_cyan" if syntax_ok else "bright_red", padding=(0, 1))


def build_devices_panel(state: "BluetoothSerialState") -> Panel:
    devs = state.probe_bluetooth_devices(force=False)
    tbl = Table(expand=True, box=None, show_header=True, pad_edge=False)
    tbl.add_column("MAC / Endpoint", style="bold cyan", width=18, no_wrap=True)
    tbl.add_column("Profile", style="magenta", width=12, no_wrap=True)
    tbl.add_column("Device Name", style="white", ratio=1, no_wrap=True)
    tbl.add_column("Link", style="bold green", width=10, no_wrap=True)

    for d in devs[:6]:
        link_txt = "[bold green]● ACTIVE[/bold green]" if d.connected else "[yellow]○ PAIRED[/yellow]"
        tbl.add_row(d.mac, d.transport, d.name, link_txt)

    return Panel(
        tbl,
        title="📡 Bluetooth RFCOMM / BLE NUS & Mesh Endpoints",
        border_style="blue",
        padding=(0, 1),
    )


def build_teleplot_and_custom_panel(
    state: "BluetoothSerialState", custom_commands: Dict[str, str]
) -> Panel:
    tbl = Table(expand=True, box=None, show_header=True, pad_edge=False)
    tbl.add_column("Channel / Cmd", style="bold yellow", width=15, no_wrap=True)
    tbl.add_column("Latest", style="bold bright_green", width=10, no_wrap=True)
    tbl.add_column("Teleplot Sparkline / Live Value", style="cyan", ratio=1, no_wrap=True)

    with state.lock:
        series_items = list(state.teleplot_series.items())

    if series_items:
        for chan, vals in series_items[:4]:
            vals_list = list(vals)
            latest = f"{vals_list[-1]:.2f}" if vals_list else "--"
            tbl.add_row(f">{chan}", latest, render_sparkline(vals_list))
    else:
        tbl.add_row(">teleplot", "idle", "[dim]Run 'teleplot demo' or send >var:val[/dim]")

    # Also show live custom commands from bt_serial_commands.py
    for cmd_k, cmd_v in list(custom_commands.items())[:3]:
        tbl.add_row(f"cmd:{cmd_k}", "HOT", str(cmd_v)[:38])

    return Panel(
        tbl,
        title=f"📈 Teleplot Stream & Hot-Reloaded Commands ({len(custom_commands)})",
        border_style="magenta",
        padding=(0, 1),
    )


def build_serial_stream_panel(state: "BluetoothSerialState", max_lines: int = 10) -> Panel:
    dir_styles = {
        "TX": ("bold bright_cyan", "TX ──►"),
        "CMD": ("bold yellow", "CMD ─►"),
        "RELOAD": ("bold black on bright_green", "HOT ⚡"),
        "ERR": ("bold bright_red", "ERR ⚠️"),
        "SYS": ("bold green", "SYS ••"),
    }

    lines_out: List[Text] = []
    with state.lock:
        recent = list(state.logs)[-max_lines:]

    if not recent:
        lines_out.append(Text("Waiting for serial frames... Type 'help', 'status', 'teleplot demo', or 'patch hello world'!", style="dim"))

    for entry in recent:
        row = Text()
        row.append(f"{entry.timestamp} ", style="dim white")
        style, badge = dir_styles.get(
            entry.direction,
            ("bold bright_magenta", f"{entry.direction[:6]:<6}"),
        )
        row.append(f"[{badge}] ", style=style)
        row.append(entry.payload, style="white")
        if entry.hex_preview:
            row.append(f"  ⟪{entry.hex_preview}⟫", style="dim cyan")
        lines_out.append(row)

    # Interactive command prompt line at bottom
    prompt_line = Text("\n")
    prompt_line.append("bt-dev> ", style="bold bright_green")
    prompt_line.append(state.input_buffer, style="bold white")
    prompt_line.append("█", style="blink bold bright_cyan")
    prompt_line.append(
        "   [Type command + ENTER | 'patch <cmd> <text>' live-updates code | Ctrl+C exit]",
        style="dim",
    )
    lines_out.append(prompt_line)

    return Panel(
        Group(*lines_out),
        title="🔌 Live Bidirectional Serial Stream (/tmp/bt_serial_pty & TCP :4005)",
        border_style="green",
        padding=(0, 1),
    )


def render_dashboard(state: "BluetoothSerialState", custom_commands: Dict[str, str]) -> Layout:
    """Builds the responsive Rich layout sized cleanly for the current terminal viewport."""
    cols, rows = shutil.get_terminal_size((100, 28))
    stream_lines = max(4, rows - 16)

    layout = Layout()
    header_size = 5 if not state.last_error else 6
    middle_size = 8

    layout.split(
        Layout(build_header_panel(state, custom_commands), name="header", size=header_size),
        Layout(name="middle", size=middle_size),
        Layout(build_serial_stream_panel(state, max_lines=stream_lines), name="stream", ratio=1),
    )

    if cols >= 90:
        layout["middle"].split_row(
            Layout(build_devices_panel(state), name="devices", ratio=1),
            Layout(build_teleplot_and_custom_panel(state, custom_commands), name="teleplot", ratio=1),
        )
    else:
        # Compact single-column mode for narrow mobile portrait viewports
        layout["middle"].update(build_teleplot_and_custom_panel(state, custom_commands))

    return layout
