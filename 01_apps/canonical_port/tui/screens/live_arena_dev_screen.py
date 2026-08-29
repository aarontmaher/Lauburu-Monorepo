"""
Canonical Port TUI — Live Side-by-Side Dual Arena & Live AI Narration Screen
Subsystem: 01_apps/canonical_port/tui/screens/live_arena_dev_screen.py
Version: 4.0.0-CANONICAL
Hermes 3 + OpenClaw (Red) vs LuCI OpenWrt + Sentinel (Blue)
"""

import os
import sys
import json
import time
import random
from pathlib import Path
from typing import Optional, Dict, Any, List

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, RichLog, Label, Input
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

_TUI_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _TUI_DIR not in sys.path:
    sys.path.insert(0, _TUI_DIR)

try:
    from widgets.pinned_tab_nav_bar import PinnedTabNavBar
    from widgets.docked_shortcuts_legend import DockedShortcutsLegend
except ImportError:
    PinnedTabNavBar = None
    DockedShortcutsLegend = None

sys.path.insert(0, "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/red_blue_arena")
from arena_rag_comm import DualTeamRAGVoiceEngine

DRAIN_STATE_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/compute_drain_war_state.json")
SANDBOX_STATE_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/device_settings_shadow.json")
MOVESENSE_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/movesense_live_stream.json")
NARRATION_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/live_ai_narration_stream.json")

class RedTeamGraphicalMapWidget(Static):
    """Large Graphical Topology & Exploit Infiltration Map for RED TEAM (Hermes 3 & OpenClaw)."""
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
            f" [bold red][🔴 HERMES 3 & OPENCLAW SWARM][/] ═════( {tb4_atk} )═════> [bold magenta][🎯 L2: MACBOOK PRO (14GB)][/]",
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
        return Panel("\n".join(lines), title="[bold red]🔴 RED TEAM (Hermes 3 & OpenClaw): 3D INFILTRATION & ATTACK MAP[/]", border_style="red")


class BlueTeamGraphicalMapWidget(Static):
    """Large Graphical Topology & Sentinel Shield Map for BLUE TEAM (LuCI OpenWrt & Sentinel)."""
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
            f" [bold cyan][🔵 LUCI OPENWRT & SENTINEL HOST][/] ══( {tb4_def} )══> [bold magenta][L2: MACBOOK PRO (Vault)][/]",
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
        return Panel("\n".join(lines), title="[bold cyan]🔵 BLUE TEAM (LuCI OpenWrt & Sentinel): 3D SHIELD & HEALING MAP[/]", border_style="cyan")


class LiveArenaDevScreen(Screen):
    CSS = """
    LiveArenaDevScreen {
        background: #070b12;
        color: #f8fafc;
    }
    #narration_bar {
        height: 6;
        background: #0f172a;
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
        ("m", "mutate_sandbox", "Mutate Device Settings"),
        ("v", "toggle_voice", "Toggle Voice (TTS)"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        if PinnedTabNavBar:
            yield PinnedTabNavBar()
        yield Static(id="narration_bar")
        with Horizontal(id="arena_container"):
            with Vertical(id="red_box", classes="faction_box"):
                yield RedTeamGraphicalMapWidget(id="red_graphical_map")
                yield Label("[bold red]🔴 HERMES 3 & OPENCLAW ACTION STREAM[/]")
                yield RichLog(id="red_log", highlight=True, markup=True)
            with Vertical(id="blue_box", classes="faction_box"):
                yield BlueTeamGraphicalMapWidget(id="blue_graphical_map")
                yield Label("[bold cyan]🔵 LUCI OPENWRT & SENTINEL ACTION STREAM[/]")
                yield RichLog(id="blue_log", highlight=True, markup=True)
        yield Input(placeholder="💬 Ask Red [Hermes] or Blue [LuCI]... (e.g., 'red why attack mbp' or 'blue router status')", id="rag_input")
        if DockedShortcutsLegend:
            yield DockedShortcutsLegend()
        yield Footer()

    def on_mount(self):
        self.red_log = self.query_one("#red_log", RichLog)
        self.blue_log = self.query_one("#blue_log", RichLog)
        self.narration_bar = self.query_one("#narration_bar", Static)
        self.red_map = self.query_one("#red_graphical_map", RedTeamGraphicalMapWidget)
        self.blue_map = self.query_one("#blue_graphical_map", BlueTeamGraphicalMapWidget)
        self.rag_engine = DualTeamRAGVoiceEngine()
        self.chaos_active = False
        
        self.red_log.write("[bold red]🔴 Hermes 3 & OpenClaw initialized. Reverse-engineering router SQM queues & Movesense GATT...[/]")
        self.blue_log.write("[bold blue]🔵 LuCI OpenWrt & Sentinel Shield active. Locking fq_codel buffers and Kamath HRV filter...[/]")
        
        self.set_interval(1.5, self.refresh_narration_tick)

    def refresh_narration_tick(self):
        hr = 72
        if MOVESENSE_PATH.exists():
            try:
                with open(MOVESENSE_PATH) as f:
                    hr = json.load(f).get("heart_rate_bpm") or 72
            except Exception:
                pass

        tick = self.rag_engine.generate_narration_tick()
        narrator = tick.get("narrator_headline", "")
        red_thought = tick.get("red_lead_thought", "")
        blue_thought = tick.get("blue_lead_thought", "")

        # Render rich live AI thoughts & narration in place of static telemetry
        narration_text = (
            f"[bold gold1]{narrator}[/]\n"
            f"[bold red]🧠 Hermes 3 Thought:[/] [italic]{red_thought}[/]\n"
            f"[bold cyan]🧠 LuCI Thought:[/] [italic]{blue_thought}[/]"
        )
        self.narration_bar.update(Panel(narration_text, title=f"⚡ Live AI Cognitive Thought Stream & Narration (Movesense: {hr} BPM | Voice: {'ON' if self.rag_engine.tts_enabled else 'OFF'})", border_style="gold1"))

        # Update Dual Maps
        self.red_map.update(self.red_map.render_map(hr_bpm=hr, chaos_active=self.chaos_active))
        self.blue_map.update(self.blue_map.render_map(hr_bpm=hr, chaos_active=self.chaos_active))

        # Stream thoughts to logs
        if random.random() > 0.4:
            self.red_log.write(f"[red]⚡ ACTION:[/] {red_thought}")
        if random.random() > 0.4:
            self.blue_log.write(f"[blue]🛡️ DEFENSE:[/] {blue_thought}")

    def on_input_submitted(self, event: Input.Submitted):
        val = event.value.strip()
        if not val:
            return
        event.input.value = ""
        
        # Route to Red or Blue team
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
            self.red_log.write("[bold yellow]⚡ CHAOS OVERLORD INJECTED: 350ms TB4 packet drop simulated![/]")
            self.blue_log.write("[bold green]🛡️ LUCI COUNTER-MEASURE: Instant failover to Headscale WireGuard (1.85ms RTT) executed.[/]")
            self.rag_engine.speak_async("Chaos Overlord injected 350ms latency fault. LuCI failover engaged.", voice="Fred")
        else:
            self.blue_log.write("[bold cyan]🔄 TB4 DMA Link Restored (0.35ms RTT). Failback complete.[/]")

    def action_mutate_sandbox(self):
        os.system("python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/red_blue_arena/device_settings_sandbox.py >/dev/null 2>&1 &")
        self.red_log.write("[magenta]🔄 Triggered Clean-Room Device Settings mutation cycle...[/]")
        self.blue_log.write("[cyan]🔒 Re-evaluating device sysctls and OpenWrt SQM queue buffers...[/]")

    def action_toggle_voice(self):
        self.rag_engine.tts_enabled = not self.rag_engine.tts_enabled
        status = "ENABLED" if self.rag_engine.tts_enabled else "MUTED"
        self.blue_log.write(f"[bold green]🔊 Voice TTS synthesis {status}.[/]")
        if self.rag_engine.tts_enabled:
            self.rag_engine.speak_async("Voice synthesis active for Hermes and LuCI.", voice="Samantha")
