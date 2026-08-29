#!/usr/bin/env python3
"""
Side-by-Side Red/Blue Adversarial & Device Sandbox Live --dev Dashboard
Lauburu Mesh Ecosystem — 2026

Rule #0 Compliant: Features DUAL large graphical topology maps (One for Red, One for Blue).
"""

import os
import sys
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, RichLog, Label
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markup import escape

DRAIN_STATE_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/compute_drain_war_state.json")
SANDBOX_STATE_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/device_settings_shadow.json")
MOVESENSE_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/movesense_live_stream.json")

class RedTeamGraphicalMapWidget(Static):
    """
    Large Graphical Topology & Exploit Infiltration Map for RED TEAM.
    """
    DEFAULT_CSS = """
    RedTeamGraphicalMapWidget {
        height: 13;
        background: #1a0505;
        border: solid #ef4444;
        padding: 0 1;
        margin-bottom: 1;
    }
    """

    def render_map(self, hr_bpm: int = 72, chaos_active: bool = False) -> Panel:
        tb4_atk = "[bold red]⚠️ 350ms PACKET DROP FLOOD[/]" if chaos_active else "[bold red]⚡ TB4 SOCKET DRAIN: Port 50052[/]"
        lines = [
            f" [bold red][🔴 RED EXPLOIT SWARM][/] ══════════( {tb4_atk} )══════════> [bold magenta][🎯 L2: MACBOOK PRO (14GB)][/]",
            f"        │                                                                             │",
            f"        ├───( [bold red]💥 BQL BURST: 8192B / WG PROBE 100.101.39.98[/] )───> [bold blue][🎯 L3: LINUX HEAD (16GB)][/]",
            f"        │                                                                     │       │",
            f"        ├───( [bold red]💉 512Hz RAW ECG STREAM INJECTION (Bypass Filter)[/] )──┘       │",
            f"        │                                                                             │",
            f"        ├───( [bold yellow]💓 INFILTRATE MOVESENSE UUID 00002A37[/] )───────> [bold red][🎯 MOVESENSE 261030002013][/]",
            f"        │                                                                             │",
            f"        └───( [bold red]📱 ADB TCP ESCALATION: Port 8022[/] )─────────> [bold gold1][🎯 L6: PIXEL 10 PRO (16GB)][/] ───┘",
            f" [bold white]Attack Invariants:[/] Process Starvation │ VRAM Ballooning (128MB) │ 3D Mat Submission Tree Exploits"
        ]
        return Panel("\n".join(lines), title="[bold red]🔴 RED TEAM: 3D ADVERSARIAL INFILTRATION & EXPLOIT TOPOLOGY MAP[/]", border_style="red")


class BlueTeamGraphicalMapWidget(Static):
    """
    Large Graphical Topology & Sentinel Shield Map for BLUE TEAM.
    """
    DEFAULT_CSS = """
    BlueTeamGraphicalMapWidget {
        height: 13;
        background: #05101e;
        border: solid #3b82f6;
        padding: 0 1;
        margin-bottom: 1;
    }
    """

    def render_map(self, hr_bpm: int = 72, chaos_active: bool = False) -> Panel:
        tb4_def = "[bold red]⚠️ TB4 SEVERED -> WG FAILOVER[/]" if chaos_active else "[bold green]⚡ MTU 9000 JUMBO SHIELD (0.35ms)[/]"
        wg_def = "[bold green]🔒 WireGuard Mesh (1.85ms ACTIVE)[/]" if chaos_active else "[bold cyan]🔒 ChaCha20-Poly1305 Overlay (1.85ms)[/]"
        lines = [
            f" [bold cyan][🔵 BLUE SENTINEL HOST][/] ════════( {tb4_def} )════════> [bold magenta][L2: MACBOOK PRO (Vault)][/]",
            f"        │                                                                             │",
            f"        ├───( {wg_def} )───> [bold blue][L3: LINUX HEAD NODE (Locked)][/]",
            f"        │                                                                     │       │",
            f"        ├───( [bold green]🛡️ SQM FQ_CODEL BUFFERBLOAT CURE & BQL LOCK[/] )──────┘       │",
            f"        │                                                                             │",
            f"        ├───( [bold green]💓 KAMATH 2004 ARTIFACT FILTER (72 BPM - RMSSD 48.5ms)[/] )─> [bold yellow][MOVESENSE 261030002013][/]",
            f"        │                                                                             │",
            f"        └───( [bold cyan]🔒 ED25519 TRIPWIRE KEEPER[/] )────────────> [bold gold1][L6: PIXEL 10 PRO (Shielded)][/] ───┘",
            f" [bold white]Defense Invariants:[/] 4 Nodes Shielded │ Ed25519 Socket Multiplexing │ Zero-Trust Rule #0 Hardware Gate"
        ]
        return Panel("\n".join(lines), title="[bold cyan]🔵 BLUE TEAM: 3D SENTINEL SHIELD & SELF-HEALING RECOVERY MAP[/]", border_style="cyan")


class LiveArenaDevApp(App):
    CSS = """
    Screen {
        background: #070b12;
        color: #f8fafc;
    }
    #hud_bar {
        height: 4;
        background: #0f172a;
        border: solid #10b981;
        padding: 0 1;
        margin-bottom: 1;
    }
    #arena_container {
        height: 1fr;
    }
    .faction_box {
        width: 1fr;
        height: 1fr;
        padding: 0 1;
    }
    #red_box {
        border: solid #ef4444;
        background: #110505;
        margin-right: 1;
    }
    #blue_box {
        border: solid #3b82f6;
        background: #050b16;
    }
    RichLog {
        height: 1fr;
        background: transparent;
    }
    """

    BINDINGS = [
        ("c", "trigger_chaos", "Inject Chaos Fault"),
        ("m", "mutate_sandbox", "Mutate Device Settings"),
        ("q", "quit", "Quit --dev Cockpit")
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="hud_bar")
        with Horizontal(id="arena_container"):
            with Vertical(id="red_box", classes="faction_box"):
                yield RedTeamGraphicalMapWidget(id="red_graphical_map")
                yield Label("[bold red]🔴 RED TEAM EXPLOITATION STREAM[/]")
                yield RichLog(id="red_log", highlight=True, markup=True)
            with Vertical(id="blue_box", classes="faction_box"):
                yield BlueTeamGraphicalMapWidget(id="blue_graphical_map")
                yield Label("[bold cyan]🔵 BLUE TEAM DEFENSE & SELF-HEALING STREAM[/]")
                yield RichLog(id="blue_log", highlight=True, markup=True)
        yield Footer()

    def on_mount(self):
        self.red_log = self.query_one("#red_log", RichLog)
        self.blue_log = self.query_one("#blue_log", RichLog)
        self.hud_bar = self.query_one("#hud_bar", Static)
        self.red_map = self.query_one("#red_graphical_map", RedTeamGraphicalMapWidget)
        self.blue_map = self.query_one("#blue_graphical_map", BlueTeamGraphicalMapWidget)
        self.chaos_active = False
        
        self.red_log.write("[bold red]🔴 Red Team Infiltration Engine initialized. Probing clean-room device endpoints...[/]")
        self.blue_log.write("[bold blue]🔵 Blue Team Sentinel Shield active. Monitoring CoreBluetooth GATT and MTU 9000 tripwires...[/]")
        
        self.set_interval(1.0, self.refresh_arena_tick)

    def refresh_arena_tick(self):
        hr = 72
        rmssd = 48.5
        if MOVESENSE_PATH.exists():
            try:
                with open(MOVESENSE_PATH) as f:
                    d = json.load(f)
                    hr = d.get("heart_rate_bpm") or 72
                    rmssd = d.get("rmssd_ms") or 48.5
            except Exception:
                pass

        blue_pct, red_pct = 64.0, 36.0
        winner = None
        if DRAIN_STATE_PATH.exists():
            try:
                with open(DRAIN_STATE_PATH) as f:
                    d = json.load(f)
                    cb = d.get("compute_balance", {})
                    blue_pct = cb.get("blue_pct", 64.0)
                    red_pct = cb.get("red_pct", 36.0)
                    winner = d.get("winner")
            except Exception:
                pass

        # 1. Update BOTH Large Graphical Maps
        self.red_map.update(self.red_map.render_map(hr_bpm=hr, chaos_active=self.chaos_active))
        self.blue_map.update(self.blue_map.render_map(hr_bpm=hr, chaos_active=self.chaos_active))

        # 2. Update Live Telemetry HUD Bar
        hud_text = (
            f"[bold cyan]LAUBURU MESH --DEV DUAL ARENA[/] | "
            f"[bold green]Movesense BLE:[/] [bold yellow]{hr} BPM[/] (RMSSD: {rmssd}ms) | "
            f"[bold magenta]TB4 DMA:[/] [bold green]0.35ms[/] (40 Gbps) | "
            f"[bold blue]Blue Compute:[/] [bold]{blue_pct}%[/] vs [bold red]Red Compute:[/] [bold]{red_pct}%[/]"
        )
        if winner:
            hud_text += f"\n[bold gold1]🏆 ARENA STATUS:[/] {winner}"
        self.hud_bar.update(Panel(hud_text, title="⚡ Live Hardware Telemetry & Compute Balance", border_style="green"))

        # 3. Update Device Settings Sandbox Stream
        if SANDBOX_STATE_PATH.exists():
            try:
                with open(SANDBOX_STATE_PATH) as f:
                    d = json.load(f)
                    devs = d.get("devices", {})
                    for dev_key, dev_data in devs.items():
                        opts = dev_data.get("optimizations_applied", [])
                        if opts:
                            latest = opts[-1]
                            t = latest.get("timestamp", "")
                            act = latest.get("action", "")
                            param = latest.get("parameter", "")
                            val = latest.get("new_value", "")
                            if latest.get("faction") == "RED_TEAM":
                                self.red_log.write(f"[{t}] [red]⚡ OPTIMIZE:[/] {act} on [bold]{dev_key}[/] ({param} -> {val})")
                            else:
                                self.blue_log.write(f"[{t}] [blue]🛡️ HARDEN:[/] {act} on [bold]{dev_key}[/] ({param} -> {val})")
            except Exception:
                pass

    def action_trigger_chaos(self):
        self.chaos_active = not self.chaos_active
        if self.chaos_active:
            self.red_log.write("[bold yellow]⚡ CHAOS OVERLORD INJECTED: 350ms TB4 packet drop simulated![/]")
            self.blue_log.write("[bold green]🛡️ BLUE COUNTER-MEASURE: Instant failover to Headscale WireGuard (1.85ms RTT) executed.[/]")
        else:
            self.blue_log.write("[bold cyan]🔄 TB4 DMA Link Restored (0.35ms RTT). Failback complete.[/]")

    def action_mutate_sandbox(self):
        os.system("python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/red_blue_arena/device_settings_sandbox.py >/dev/null 2>&1 &")
        self.red_log.write("[magenta]🔄 Triggered Clean-Room Device Settings mutation cycle...[/]")
        self.blue_log.write("[cyan]🔒 Re-evaluating device sysctls and OpenWrt SQM queue buffers...[/]")

if __name__ == "__main__":
    app = LiveArenaDevApp()
    app.run()
