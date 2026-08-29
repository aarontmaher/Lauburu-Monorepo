#!/usr/bin/env python3
"""
Side-by-Side Red/Blue Adversarial & Gamified Live --dev Dashboard
Lauburu Mesh Ecosystem — 2026

Hermes 3 + OpenClaw (Red) vs LuCI OpenWrt + Sentinel (Blue)
Features:
1. Dynamic Animated Tug-of-War Compute Power Bar.
2. Live Movesense Cardiac Pulse Gauge & Autonomic Zone Indicator.
3. Dual Large Graphical Topology Maps.
4. Interactive 1-Key Battle Abilities ([c] Chaos, [h] Heal, [b] BQL Burst, [s] Shield).
5. Interactive RAG Query Input Bar & macOS Voice TTS.
"""

import os
import sys
import json
import time
import random
import asyncio
from pathlib import Path
from typing import Dict, Any, List

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, RichLog, Label, Input
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

sys.path.insert(0, "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/red_blue_arena")
sys.path.insert(0, "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src")
from arena_rag_comm import DualTeamRAGVoiceEngine
from autonomous_game_and_ui_optimizer_loop import AutonomousGameAndUIOptimizerLoop

UI_STATE_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/dynamic_ui_ux_state.json")
MOVESENSE_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/movesense_live_stream.json")

class RedTeamGraphicalMapWidget(Static):
    """Large Graphical Topology & Exploit Infiltration Map for RED TEAM (Hermes 3 & OpenClaw)."""
    DEFAULT_CSS = """
    RedTeamGraphicalMapWidget {
        height: 12;
        background: #180505;
        border: solid #ef4444;
        padding: 0 1;
        margin-bottom: 1;
    }
    """

    def render_map(self, hr_bpm: int = 73, chaos_active: bool = False) -> Panel:
        tb4_atk = "[bold red]⚠️ 350ms PACKET DROP FLOOD[/]" if chaos_active else "[bold red]⚡ TB4 SOCKET DRAIN: Port 50052[/]"
        lines = [
            f" [bold red][🔴 HERMES 3 & OPENCLAW SWARM][/] ═════( {tb4_atk} )═════> [bold magenta][🎯 L2: MACBOOK PRO (14GB)][/]",
            f"        │                                                                             │",
            f"        ├───( [bold red]💥 BQL BURST: 8192B / WG PROBE 100.101.39.98[/] )───> [bold blue][🎯 L3: LINUX HEAD (16GB)][/]",
            f"        │                                                                     │       │",
            f"        ├───( [bold red]💉 512Hz RAW ECG STREAM INJECTION (Bypass Filter)[/] )──┘       │",
            f"        │                                                                             │",
            f"        ├───( [bold yellow]💓 INFILTRATE MOVESENSE UUID 00002A37[/] )───────> [bold red][🎯 MOVESENSE 261030002013][/]",
            f"        │                                                                             │",
            f"        └───( [bold red]📱 ADB TCP ESCALATION: Port 8022[/] )─────────> [bold gold1][🎯 L6: PIXEL 10 PRO (16GB)][/] ───┘"
        ]
        return Panel("\n".join(lines), title="[bold red]🔴 RED TEAM (Hermes 3 & OpenClaw): 3D INFILTRATION MAP[/]", border_style="red")


class BlueTeamGraphicalMapWidget(Static):
    """Large Graphical Topology & Sentinel Shield Map for BLUE TEAM (LuCI OpenWrt & Sentinel)."""
    DEFAULT_CSS = """
    BlueTeamGraphicalMapWidget {
        height: 12;
        background: #05101e;
        border: solid #3b82f6;
        padding: 0 1;
        margin-bottom: 1;
    }
    """

    def render_map(self, hr_bpm: int = 73, chaos_active: bool = False) -> Panel:
        tb4_def = "[bold red]⚠️ TB4 SEVERED -> WG FAILOVER[/]" if chaos_active else "[bold green]⚡ MTU 9000 JUMBO SHIELD (0.35ms)[/]"
        wg_def = "[bold green]🔒 WireGuard Mesh (1.85ms ACTIVE)[/]" if chaos_active else "[bold cyan]🔒 ChaCha20-Poly1305 Overlay (1.85ms)[/]"
        lines = [
            f" [bold cyan][🔵 LUCI OPENWRT & SENTINEL HOST][/] ══( {tb4_def} )══> [bold magenta][L2: MACBOOK PRO (Vault)][/]",
            f"        │                                                                             │",
            f"        ├───( {wg_def} )───> [bold blue][L3: LINUX HEAD NODE (Locked)][/]",
            f"        │                                                                     │       │",
            f"        ├───( [bold green]🛡️ SQM FQ_CODEL BUFFERBLOAT CURE & BQL LOCK[/] )──────┘       │",
            f"        │                                                                             │",
            f"        ├───( [bold green]💓 KAMATH 2004 ARTIFACT FILTER ({hr_bpm} BPM - RMSSD 39.4ms)[/] )─> [bold yellow][MOVESENSE 261030002013][/]",
            f"        │                                                                             │",
            f"        └───( [bold cyan]🔒 ED25519 TRIPWIRE KEEPER[/] )────────────> [bold gold1][L6: PIXEL 10 PRO (Shielded)][/] ───┘"
        ]
        return Panel("\n".join(lines), title="[bold cyan]🔵 BLUE TEAM (LuCI OpenWrt & Sentinel): 3D SHIELD MAP[/]", border_style="cyan")


class LiveArenaDevApp(App):
    CSS = """
    Screen {
        background: #070b12;
        color: #f8fafc;
    }
    #battle_hud_bar {
        height: 6;
        background: #0b111c;
        border: solid #f59e0b;
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
    #rag_input {
        dock: bottom;
        height: 3;
        background: #1e293b;
        border: solid #38bdf8;
        color: #ffffff;
    }
    """

    BINDINGS = [
        ("c", "trigger_chaos", "Inject Chaos Fault"),
        ("h", "trigger_heal", "Self-Heal All"),
        ("b", "trigger_bql_burst", "BQL Queue Burst"),
        ("s", "trigger_jumbo_shield", "Lock MTU 9000 Shield"),
        ("v", "toggle_voice", "Toggle Voice (TTS)"),
        ("q", "quit", "Quit --dev Cockpit")
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="battle_hud_bar")
        with Horizontal(id="arena_container"):
            with Vertical(id="red_box", classes="faction_box"):
                yield RedTeamGraphicalMapWidget(id="red_graphical_map")
                yield Label("[bold red]🔴 HERMES 3 & OPENCLAW COMBAT LOG[/]")
                yield RichLog(id="red_log", highlight=True, markup=True)
            with Vertical(id="blue_box", classes="faction_box"):
                yield BlueTeamGraphicalMapWidget(id="blue_graphical_map")
                yield Label("[bold cyan]🔵 LUCI OPENWRT & SENTINEL DEFENSE LOG[/]")
                yield RichLog(id="blue_log", highlight=True, markup=True)
        yield Input(placeholder="💬 Ask Red [Hermes] or Blue [LuCI]... (e.g., 'red why attack mbp' or 'blue router status')", id="rag_input")
        yield Footer()

    def on_mount(self):
        self.red_log = self.query_one("#red_log", RichLog)
        self.blue_log = self.query_one("#blue_log", RichLog)
        self.battle_hud = self.query_one("#battle_hud_bar", Static)
        self.red_map = self.query_one("#red_graphical_map", RedTeamGraphicalMapWidget)
        self.blue_map = self.query_one("#blue_graphical_map", BlueTeamGraphicalMapWidget)
        self.rag_engine = DualTeamRAGVoiceEngine()
        self.optimizer_loop = AutonomousGameAndUIOptimizerLoop()
        self.chaos_active = False
        
        self.red_log.write("[bold red]🔴 Hermes 3 & OpenClaw active. Target: GL.iNet Router BQL & Movesense GATT.[/]")
        self.blue_log.write("[bold blue]🔵 LuCI OpenWrt & Sentinel Shield active. Target: MTU 9000 & Kamath HRV lock.[/]")
        
        self.set_interval(1.5, self.refresh_game_tick)

    def refresh_game_tick(self):
        state = self.optimizer_loop.run_debate_cycle()
        hud = state.get("gamified_hud", {})
        combat_bar = hud.get("combat_tug_of_war_bar", "")
        pulse_meter = hud.get("cardiac_pulse_meter", "")
        contested = hud.get("contested_node", "")
        hr = hud.get("heart_rate_bpm", 73)

        voice_badge = "[bold green]🔊 VOICE: ON[/]" if self.rag_engine.tts_enabled else "[dim]🔇 VOICE: OFF (Press 'v')[/]"
        hud_content = (
            f"[bold gold1]⚔️ LAUBURU MESH COMPUTATIONAL WAR ARENA[/] | {voice_badge} | [bold yellow]Contested:[/] {contested}\n"
            f"[bold white]Compute Power:[/] {combat_bar}\n"
            f"[bold white]Real Biometrics:[/] {pulse_meter} | [bold cyan]Abilities:[/] [c] Chaos  [h] Heal  [b] BQL Burst  [s] Shield"
        )
        self.battle_hud.update(Panel(hud_content, title=f"⚡ Live Computational Battle & Biofeedback HUD", border_style="gold1"))

        self.red_map.update(self.red_map.render_map(hr_bpm=hr, chaos_active=self.chaos_active))
        self.blue_map.update(self.blue_map.render_map(hr_bpm=hr, chaos_active=self.chaos_active))

        evts = state.get("play_by_play_events", [])
        if evts:
            latest = evts[0]
            if latest["team"] == "red":
                self.red_log.write(f"[{latest['time']}] [bold red]{latest['type']}:[/] {latest['description']}")
            elif latest["team"] == "blue":
                self.blue_log.write(f"[{latest['time']}] [bold cyan]{latest['type']}:[/] {latest['description']}")
            else:
                self.blue_log.write(f"[{latest['time']}] [bold yellow]{latest['type']}:[/] {latest['description']}")

    def on_input_submitted(self, event: Input.Submitted):
        val = event.value.strip()
        if not val:
            return
        event.input.value = ""
        
        if "red" in val.lower() or "hermes" in val.lower() or "openclaw" in val.lower():
            target_team = "RED"
        else:
            target_team = "BLUE"
            
        res = self.rag_engine.query_team(target_team, val)
        if target_team == "RED":
            self.red_log.write(f"[bold yellow]👤 YOU -> RED:[/] {val}")
            self.red_log.write(f"{res['response']}")
        else:
            self.blue_log.write(f"[bold yellow]👤 YOU -> BLUE:[/] {val}")
            self.blue_log.write(f"{res['response']}")

    def action_trigger_chaos(self):
        self.chaos_active = not self.chaos_active
        if self.chaos_active:
            self.red_log.write("[bold yellow]⚡ CHAOS DROP TRIGGERED: 350ms TB4 packet latency fault injected![/]")
            self.blue_log.write("[bold green]🛡️ LUCI RESPONSE: Auto-rerouted to WireGuard ChaCha20 mesh (1.85ms).[/]")
            self.rag_engine.speak_async("Chaos Overlord injected latency drop. LuCI rerouting active.", voice="Fred")
        else:
            self.blue_log.write("[bold cyan]🔄 TB4 DMA Link Restored (0.35ms RTT). Failback complete.[/]")

    def action_trigger_heal(self):
        self.optimizer_loop.blue_compute_pct = min(self.optimizer_loop.blue_compute_pct + 12.0, 95.0)
        self.optimizer_loop.red_compute_pct = 100.0 - self.optimizer_loop.blue_compute_pct
        self.blue_log.write("[bold green]🛡️ HEAL ABILITY ENGAGED: Restored +12% compute power to Blue Sentinel Shield![/]")
        self.rag_engine.speak_async("Self-healing pulse deployed. System compute restored.", voice="Samantha")

    def action_trigger_bql_burst(self):
        self.optimizer_loop.red_compute_pct = min(self.optimizer_loop.red_compute_pct + 10.0, 95.0)
        self.optimizer_loop.blue_compute_pct = 100.0 - self.optimizer_loop.red_compute_pct
        self.red_log.write("[bold red]💥 BQL BURST OVERLOAD: Hermes 3 expanded queue buffers (+10% Red Compute)![/]")
        self.rag_engine.speak_async("BQL buffer expansion executed by Hermes.", voice="Alex")

    def action_trigger_jumbo_shield(self):
        self.blue_log.write("[bold cyan]🔒 MTU 9000 JUMBO SHIELD LOCKED: bridge0 socket buffers hardened against overflows.[/]")
        self.rag_engine.speak_async("MTU 9000 shield verified.", voice="Samantha")

    def action_toggle_voice(self):
        self.rag_engine.tts_enabled = not self.rag_engine.tts_enabled
        status = "ENABLED" if self.rag_engine.tts_enabled else "MUTED"
        self.blue_log.write(f"[bold green]🔊 Voice TTS synthesis {status}.[/]")
        if self.rag_engine.tts_enabled:
            self.rag_engine.speak_async("Voice synthesis active for Hermes and LuCI.", voice="Samantha")

if __name__ == "__main__":
    app = LiveArenaDevApp()
    app.run()
