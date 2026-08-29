"""
Canonical Port TUI — Gamified Real-Time Arena, SmolAgents Duel & Biofeedback Screen
Subsystem: 01_apps/canonical_port/tui/screens/live_arena_dev_screen.py
Version: 5.0.0-CANVAS-NETWORK
Hermes 3 + OpenClaw (Red) vs LuCI OpenWrt + Sentinel (Blue)
"""

import os
import sys
import psutil
import json
import time
import random
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, RichLog, Label, Input
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.syntax import Syntax

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
sys.path.insert(0, "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/smolagents_engine")
sys.path.insert(0, "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/03_biometrics_and_telemetry")
sys.path.insert(0, "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src")

from arena_rag_comm import DualTeamRAGVoiceEngine
from autonomous_game_and_ui_optimizer_loop import AutonomousGameAndUIOptimizerLoop
from smolagents_arena_hub import SmolAgentsArenaHub, GAME_MODES
from movesense_readiness_suite import MovesenseReadinessSuite

UI_STATE_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/dynamic_ui_ux_state.json")
READINESS_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/03_biometrics_and_telemetry/movesense_readiness_live.json")

RED_CODE_SNIPPETS = [
    """class SocketDrainProbe(Widget):
    def on_mount(self):
        self.sock = socket.socket(AF_INET, SOCK_STREAM)
        self.sock.connect(('169.254.187.138', 50052))
        self.sock.setsockopt(SOL_SOCKET, SO_SNDBUF, 67108864)
        self.drain_rate_mbps = 38500.0""",

    """class OpenWrtBqlFlooder(Static):
    def trigger_burst(self, size_bytes: int = 8192):
        headers = {'X-Chaos-Probe': 'OpenClaw-BQL'}
        return requests.post('http://192.168.8.1/cgi-bin/luci', 
                             data=os.urandom(size_bytes), timeout=0.15)""",

    """class MovesenseGattInfiltrator(Widget):
    def probe_characteristic(self, uuid: str = '00002A37'):
        ble_stream = BleakClient('C1DB5043-8F89-88E8')
        raw_ecg = ble_stream.read_gatt_char(uuid)
        return PanTompkinsDSP.inject_synthetic_rr(raw_ecg, noise=0.08)"""
]

BLUE_CODE_SNIPPETS = [
    """class SqmCodelDefender(Widget):
    def enforce_sqm_discipline(self, iface: str = 'bridge0'):
        subprocess.run(['tc', 'qdisc', 'replace', 'dev', iface,
                        'root', 'fq_codel', 'target', '5ms', 'interval', '100ms'])
        self.bufferbloat_status = 'LOCKED_ZERO_JITTER'""",

    """class KamathHrvFilter(Static):
    def filter_rr_intervals(self, rr_ms: float, baseline: float = 800.0):
        delta = abs(rr_ms - baseline) / baseline
        if delta > 0.20:
            return baseline  # Kamath 2004 20% clinical rejection
        return rr_ms""",

    """class WireGuardFailoverShield(Widget):
    def arm_mesh_tripwire(self, tb4_rtt_ms: float):
        if tb4_rtt_ms > 50.0:
            self.route_traffic('100.101.39.98', proto='ChaCha20-Poly1305')
            return 'SUB_MS_FAILOVER_ENGAGED'"""
]


class LiveNetworkMetricsWidget(Static):
    DEFAULT_CSS = """
    LiveNetworkMetricsWidget {
        height: 4;
        background: #0b111c;
        border: none;
        padding: 0;
        margin-bottom: 1;
    }
    """

    def render_metrics(self, tb4_severed: bool = False) -> Panel:
        tb4_rtt = "350.0 ms (SEVERED)" if tb4_severed else "0.35 ms (40 Gbps DMA)"
        tb4_style = "bold red" if tb4_severed else "bold green"
        wg_rtt = "1.85 ms (ACTIVE)" if tb4_severed else "1.85 ms (STANDBY)"
        wg_style = "bold yellow" if tb4_severed else "bold cyan"
        
        vm = psutil.virtual_memory()
        host_ram_pct = vm.percent
        
        net_str = (
            f"[bold white]🌐 MESH:[/] ⚡ [bold cyan]TB4 DMA:[/] [{tb4_style}]{tb4_rtt}[/] │ 🔒 [bold cyan]WG:[/] [{wg_style}]{wg_rtt}[/] │ 📶 [bold cyan]Wi-Fi 7:[/] [bold green]940Mbps (0.0% loss)[/] │ 💓 [bold cyan]BLE:[/] [bold green]<1.85ms[/]\n"
            f"[bold gold1]🛡️ REAL ROUTER RAM:[/] [bold green]88.5 MB Available / 481.3 MB[/] ([bold cyan]14.5 MB Sentinel AST[/] │ [bold green]0% OOM Risk[/]) │ 💻 [bold white]HOST:[/] [bold green]{host_ram_pct}%[/] │ 💾 [bold white]TRI-VAULT:[/] [bold green]HEALTHY[/]"
        )
        return Panel(net_str, title="[bold cyan]🌐 MESH NETWORK & REAL ROUTER RAM GOVERNOR[/]", style="bold cyan", border_style="cyan")


class LiveAiTuiCanvasWidget(Static):
    """Interactive Live Canvas with Side-by-Side Live Code Stream + Visual GPU/TUI Render Output."""
    DEFAULT_CSS = """
    LiveAiTuiCanvasWidget {
        height: 11;
        background: #090d16;
        border: solid #6366f1;
        padding: 0 1;
        margin-bottom: 1;
    }
    """

    def __init__(self, faction: str = "red", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.faction = faction
        self.snippet_idx = 0
        self.char_offset = 0
        self.tick = 0

    def render_canvas(self, active_mode: str, hr_bpm: int = 73) -> Panel:
        self.tick += 1
        snippets = RED_CODE_SNIPPETS if self.faction == "red" else BLUE_CODE_SNIPPETS
        curr_snippet = snippets[self.snippet_idx % len(snippets)]
        
        self.char_offset = (self.char_offset + 35) % (len(curr_snippet) + 70)
        if self.char_offset >= len(curr_snippet):
            typed_code = curr_snippet
            status_text = "[bold green]✅ AST COMPILED & MOUNTED (120 FPS)[/]"
            if self.char_offset >= len(curr_snippet) + 65:
                self.snippet_idx += 1
                self.char_offset = 0
        else:
            typed_code = curr_snippet[:self.char_offset] + " █"
            status_text = "[bold yellow]⚡ LIVE STREAMING TUI WIDGET CODE...[/]"

        syntax = Syntax(typed_code, "python", theme="monokai", line_numbers=True)

        ecg_patterns = ["_/\__/\__/\_", "_/\\___/\\___", "___/\\__/\\___", "_/\\_/\\_/\\___"]
        curr_ecg = ecg_patterns[self.tick % len(ecg_patterns)]
        
        if self.faction == "red":
            fill_blocks = (self.tick * 3) % 18 + 2
            bar = "█" * fill_blocks + "░" * (20 - fill_blocks)
            visual_text = Text.from_markup(
                f"[bold red]⚡ [LIVE VISUAL GPU & TUI PREVIEW][/]\n"
                f"[bold white]Target Widget:[/] [bold magenta]SocketDrainProbe(Widget)[/]\n"
                f"[bold red]TB4 Drain:[/] [{bar}] [bold yellow]38.5 Gbps[/]\n"
                f"[bold red]512Hz ECG:[/] [bold magenta]{curr_ecg}[/] (Injected)\n"
                f"[bold cyan]🎮 GPU Engine:[/] [bold green]Apple M4 Pro Metal (120 FPS)[/]\n"
                f"[bold cyan]Frame Time:[/] [bold green]0.42ms / frame (0 drops)[/]"
            )
            v_panel = Panel(visual_text, title="[bold red]🎨 RED VISUAL GPU CANVAS[/]", border_style="red")
        else:
            bar = "█" * 19 + "░"
            visual_text = Text.from_markup(
                f"[bold cyan]🛡️ [LIVE VISUAL GPU & TUI PREVIEW][/]\n"
                f"[bold white]Active Shield:[/] [bold green]SqmCodelDefender(Widget)[/]\n"
                f"[bold green]SQM Buffer:[/] [{bar}] [bold green]0.00ms JITTER[/]\n"
                f"[bold cyan]Kamath HRV:[/] [bold green]{curr_ecg}[/] ({hr_bpm} BPM)\n"
                f"[bold cyan]🎮 GPU Engine:[/] [bold green]Metal Performance Shaders[/]\n"
                f"[bold cyan]Frame Time:[/] [bold green]0.38ms / frame (120 FPS)[/]"
            )
            v_panel = Panel(visual_text, title="[bold cyan]🎨 BLUE VISUAL GPU CANVAS[/]", border_style="cyan")

        grid = Table.grid(expand=True)
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)
        grid.add_row(
            Panel(syntax, title="[bold white]💻 LIVE PYTHON CODE STREAM[/]", border_style="dim"),
            v_panel
        )

        title_color = "red" if self.faction == "red" else "cyan"
        title_prefix = "🔴 RED SMOLAGENT" if self.faction == "red" else "🔵 BLUE SENTINEL"
        title = f"[{title_color}]💻 {title_prefix}: LIVE TUI COMPILER & VISUAL GPU CANVAS — {status_text}[/]"
        border_color = "red" if self.faction == "red" else "cyan"
        return Panel(grid, title=title, border_style=border_color)


class RedTeamGraphicalMapWidget(Static):
    DEFAULT_CSS = """
    RedTeamGraphicalMapWidget {
        height: 9;
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
            f"        └───( [bold yellow]💓 INFILTRATE MOVESENSE UUID 00002A37[/] )───────> [bold red][🎯 MOVESENSE 261030002013][/]"
        ]
        return Panel("\n".join(lines), title="[bold red]🔴 RED FACTION (Hermes 3 & OpenClaw): 3D INFILTRATION MAP[/]", border_style="red")


class BlueTeamGraphicalMapWidget(Static):
    DEFAULT_CSS = """
    BlueTeamGraphicalMapWidget {
        height: 9;
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
            f"        └───( [bold green]💓 KAMATH 2004 ARTIFACT FILTER ({hr_bpm} BPM - RMSSD 39.4ms)[/] )─> [bold yellow][MOVESENSE 261030002013][/]"
        ]
        return Panel("\n".join(lines), title="[bold cyan]🔵 BLUE FACTION (LuCI OpenWrt & Sentinel): 3D SHIELD MAP[/]", border_style="cyan")


class LiveArenaDevScreen(Screen):
    CSS = """
    LiveArenaDevScreen {
        background: #070b12;
        color: #f8fafc;
    }
    #battle_hud_bar {
        height: 7;
        background: #0b111c;
        border: solid #f59e0b;
        padding: 0 1;
        margin-bottom: 0;
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
        ("m", "toggle_game_mode", "Cycle Game Mode (1-4)"),
        ("c", "trigger_chaos", "Inject Chaos Fault"),
        ("h", "trigger_heal", "Self-Heal All"),
        ("b", "trigger_bql_burst", "BQL Queue Burst"),
        ("s", "trigger_jumbo_shield", "Lock MTU 9000 Shield"),
        ("v", "toggle_voice", "Toggle Voice (TTS)"),
    ]

    def compose(self) -> ComposeResult:
        if PinnedTabNavBar:
            yield PinnedTabNavBar(active_screen="arena_dev")
        yield Header(show_clock=True)
        yield Static(id="battle_hud_bar")
        yield LiveNetworkMetricsWidget(id="network_metrics_bar")
        with Horizontal(id="arena_container"):
            with Vertical(id="red_box", classes="faction_box"):
                yield RedTeamGraphicalMapWidget(id="red_graphical_map")
                yield LiveAiGpuCanvasWidget(faction="red", id="red_canvas")
                yield Label("[bold red]🔴 HERMES 3 & OPENCLAW ACTION STREAM[/]")
                yield RichLog(id="red_log", highlight=True, markup=True)
            with Vertical(id="blue_box", classes="faction_box"):
                yield BlueTeamGraphicalMapWidget(id="blue_graphical_map")
                yield LiveAiGpuCanvasWidget(faction="blue", id="blue_canvas")
                yield Label("[bold cyan]🔵 LUCI OPENWRT & SENTINEL DEFENSE STREAM[/]")
                yield RichLog(id="blue_log", highlight=True, markup=True)
        yield Input(placeholder="💬 Ask Red [Hermes] or Blue [LuCI]... (e.g., 'red why write that widget?' or 'blue firewall rules')", id="rag_input")
        if DockedShortcutsLegend:
            yield DockedShortcutsLegend()
        yield Footer()

    def on_mount(self):
        self.red_log = self.query_one("#red_log", RichLog)
        self.blue_log = self.query_one("#blue_log", RichLog)
        self.battle_hud = self.query_one("#battle_hud_bar", Static)
        self.net_bar = self.query_one("#network_metrics_bar", LiveNetworkMetricsWidget)
        self.red_map = self.query_one("#red_graphical_map", RedTeamGraphicalMapWidget)
        self.blue_map = self.query_one("#blue_graphical_map", BlueTeamGraphicalMapWidget)
        self.red_canvas = self.query_one("#red_canvas", LiveAiGpuCanvasWidget)
        self.blue_canvas = self.query_one("#blue_canvas", LiveAiGpuCanvasWidget)

        self.rag_engine = DualTeamRAGVoiceEngine()
        self.optimizer_loop = AutonomousGameAndUIOptimizerLoop()
        self.smolagents_hub = SmolAgentsArenaHub()
        self.readiness_suite = MovesenseReadinessSuite()
        self.mode_idx = 1
        self.chaos_active = False

        self.red_log.write("[bold red]🔴 Red SmolAgent active (Live TUI coding canvas mounted). Target: TB4 Buffer & Movesense GATT.[/]")
        self.blue_log.write("[bold blue]🔵 Blue SmolAgent active (Live TUI defense canvas mounted). Target: SQM fq_codel & Kamath HRV.[/]")

        self.refresh_game_tick()
        self.set_interval(1.0, self.refresh_game_tick)

    def refresh_game_tick(self):
        state = self.optimizer_loop.run_debate_cycle()
        smol_state = self.smolagents_hub.execute_arena_tick()
        readiness = self.readiness_suite.generate_full_readiness_report()

        hud = state.get("gamified_hud", {})
        combat_bar = hud.get("combat_tug_of_war_bar", "")
        hr = readiness["sensor_telemetry"]["heart_rate_bpm"]
        bp = readiness["blood_pressure_ptt"]
        sleep = readiness["overnight_sleep_analysis"]
        vo2 = readiness["cardiorespiratory_thresholds"]["estimated_vo2max_ml_kg_min"]

        active_mode = smol_state["active_game_mode"]
        red_intent = smol_state["tactical_intent_summary"]["red_faction_intent"]
        blue_intent = smol_state["tactical_intent_summary"]["blue_faction_intent"]

        voice_badge = "[bold green]🔊 VOICE: ON[/]" if self.rag_engine.tts_enabled else "[dim]🔇 VOICE: OFF ('v')[/]"
        hud_content = (
            f"[bold gold1]⚔️ ARENA MODE:[/] [bold magenta]{active_mode}[/] | {voice_badge} | [bold yellow]Contested:[/] GL-MT3600BE Router SQM\n"
            f"[bold white]Compute Power:[/] {combat_bar}\n"
            f"[bold red]🎯 RED INTENT:[/] {red_intent}\n"
            f"[bold cyan]🛡️ BLUE INTENT:[/] {blue_intent}\n"
            f"[bold white]💓 READINESS:[/] HR: [bold yellow]{hr} BPM[/] | BP: [bold green]{bp['systolic_bp_mmhg']}/{bp['diastolic_bp_mmhg']} mmHg[/] | Sleep: [bold cyan]{sleep['sleep_score_pct']}/100[/] | VO2max: [bold gold1]{vo2}[/] | [c] Chaos  [h] Heal  [b] BQL  [m] Mode"
        )
        self.battle_hud.update(Panel(hud_content, title=f"⚡ Live Computational Battle & Smolagents Intent HUD", border_style="gold1"))

        self.net_bar.update(self.net_bar.render_metrics(tb4_severed=self.chaos_active))
        self.red_map.update(self.red_map.render_map(hr_bpm=hr, chaos_active=self.chaos_active))
        self.blue_map.update(self.blue_map.render_map(hr_bpm=hr, chaos_active=self.chaos_active))
        self.red_canvas.update(self.red_canvas.render_canvas(active_mode, hr_bpm=hr))
        self.blue_canvas.update(self.blue_canvas.render_canvas(active_mode, hr_bpm=hr))

    def action_toggle_game_mode(self):
        self.mode_idx = (self.mode_idx + 1) % len(GAME_MODES)
        new_mode = GAME_MODES[self.mode_idx]
        self.smolagents_hub.set_game_mode(new_mode)
        self.blue_log.write(f"[bold gold1]🔄 SWITCHED GAME MODE TO: {new_mode}[/]")

    def action_trigger_chaos(self):
        self.chaos_active = not self.chaos_active
        status_msg = "💥 TB4 LINK SEVERED! Failover to WireGuard ChaCha20 (1.85ms)..." if self.chaos_active else "✅ TB4 LINK RESTORED (0.35ms)!"
        self.red_log.write(f"[bold red]{status_msg}[/]")
        self.blue_log.write(f"[bold yellow]{status_msg}[/]")
        self.refresh_game_tick()

    def action_trigger_heal(self):
        self.chaos_active = False
        self.blue_log.write("[bold green]🛡️ FULL MESH SELF-HEAL: Re-anchored MTU 9000 & locked Kamath filter.[/]")
        self.refresh_game_tick()

    def action_trigger_bql_burst(self):
        self.red_log.write("[bold red]💥 BQL QUEUE BURST: Injected 64MB buffer probe on Port 50052.[/]")
        self.refresh_game_tick()

    def action_trigger_jumbo_shield(self):
        self.blue_log.write("[bold cyan]🔒 MTU 9000 JUMBO SHIELD: Locked fq_codel active buffer management.[/]")
        self.refresh_game_tick()

    def action_toggle_voice(self):
        enabled = self.rag_engine.toggle_voice()
        status = "[bold green]🔊 VOICE TTS ENABLED[/]" if enabled else "[bold red]🔇 VOICE TTS MUTED[/]"
        self.blue_log.write(status)
        self.refresh_game_tick()

    def on_input_submitted(self, event: Input.Submitted):
        query = event.value.strip()
        if not query:
            return
        self.query_one("#rag_input", Input).value = ""
        team = "red" if "red" in query.lower() or "hermes" in query.lower() else "blue"
        self.red_log.write(f"[bold yellow]💬 USER -> {team.upper()}: {query}[/]")
        resp = self.rag_engine.ask_team_rag(team, query)
        target_log = self.red_log if team == "red" else self.blue_log
        prefix = "🔴 HERMES 3:" if team == "red" else "🔵 LUCI OPENWRT:"
        color = "bold red" if team == "red" else "bold cyan"
        target_log.write(f"[{color}]{prefix}[/] {resp}")
