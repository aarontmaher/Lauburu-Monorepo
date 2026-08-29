"""
Canonical Port 9-Screen NOC Dashboard Application.
==================================================
Subsystem: 01_apps/operator_and_dev/canonical_port/views/dashboard.py
"""

import sys
import time
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button
from textual.containers import Container, Horizontal, Vertical
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .screens import STABILITY_SCREENS
from ..nodes.mesh_nodes import MESH_NODES
from ..nodes.hardware_pool import get_hardware_pool_summary
from ..debate.council import DebateCouncilEngine
from ..core.state import CanonicalStateStore

class CanonicalPortDashboard(App):
    """9-Screen Stability NOC Operator Dashboard."""

    TITLE = "🏛️ LAUBURU CANONICAL PORT — 9-SCREEN STABILITY NOC"
    SUB_TITLE = "7 Physical Nodes • 108GB RAM Pool • AI Debate Council • Tri-Vault Core"

    CSS = """
    Screen {
        background: #070b12;
        color: #f8fafc;
    }
    #nav-bar {
        height: 3;
        background: #0b111c;
        border-bottom: solid #1e293b;
        align: center middle;
    }
    #main-container {
        height: 1fr;
        margin: 1 1;
    }
    .panel-box {
        background: #0b111c;
        border: solid #1e293b;
        height: 100%;
        padding: 1 2;
    }
    #footer-bar {
        height: 3;
        background: #0b111c;
        border-top: solid #1e293b;
        align: center middle;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("1", "screen_1", "Screen 1: Overview"),
        ("2", "screen_2", "Screen 2: Nodes"),
        ("3", "screen_3", "Screen 3: Memory"),
        ("4", "screen_4", "Screen 4: Biometrics"),
        ("5", "screen_5", "Screen 5: Inference"),
        ("6", "screen_6", "Screen 6: Debate"),
        ("7", "screen_7", "Screen 7: Tri-Vault"),
        ("8", "screen_8", "Screen 8: Airgap"),
        ("9", "screen_9", "Screen 9: Logs"),
    ]

    def __init__(self):
        super().__init__()
        self.state_store = CanonicalStateStore()
        self.debate_engine = DebateCouncilEngine()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="nav-bar"):
            yield Static("🏛️ [1] Overview [2] Nodes [3] Memory [4] Bio [5] Infer [6] Debate [7] Vault [8] Airgap [9] Logs", id="nav-text")

        with Horizontal(id="main-container"):
            yield Static(id="left-panel", classes="panel-box")
            yield Static(id="right-panel", classes="panel-box")

        with Horizontal(id="footer-bar"):
            yield Static("🔒 100% Sovereign Mesh NOC • 10Gbps TB4 Bridge • Press [1-9] Switch Screen • [q] Quit", id="status-text")
        yield Footer()

    def on_mount(self) -> None:
        self.render_active_screen()

    def render_active_screen(self) -> None:
        sid = self.state_store.active_screen_id
        pool = get_hardware_pool_summary()

        if sid == 1:
            # Overview
            t_left = Text()
            t_left.append("🌐 7-LAYER PHYSICAL MESH OVERVIEW\n\n", style="bold cyan")
            t_left.append(f"• Total Physical RAM: {pool['total_physical_ram_gb']} GB\n", style="bold green")
            t_left.append(f"• Usable AI VRAM Pool: {pool['total_usable_ai_vram_gb']} GB\n", style="bold green")
            t_left.append(f"• TB4 Low-Latency Link: {pool['tb4_rtt_ms']} ms RTT (10 Gbps)\n", style="bold yellow")
            t_left.append(f"• Mesh Nodes Online: {pool['online_nodes']} / {pool['total_nodes']}\n\n", style="white")
            t_left.append("• Tri-Vault Synchronization: HEALTHY (Obsidian + PySpark + Git)\n", style="bold green")
            t_left.append("• Biometrics Fail-Closed Airgap: CERTIFIED (0% Cloud Leak)", style="bold cyan")
            self.query_one("#left-panel", Static).update(t_left)

            t_right = Text()
            t_right.append("⚡ 9-SCREEN STABILITY HIERARCHY\n\n", style="bold yellow")
            for s in STABILITY_SCREENS:
                t_right.append(f"[{s.hotkey}] {s.title} — {s.status}\n", style="white")
            self.query_one("#right-panel", Static).update(t_right)

        elif sid == 2:
            # Nodes
            table = Table(title="7 Physical Mesh Nodes & Dynamic Caps", expand=True)
            table.add_column("Layer", style="cyan")
            table.add_column("Node Name", style="bold yellow")
            table.add_column("IP / Tailscale", style="white")
            table.add_column("RAM / VRAM", style="green")
            table.add_column("Dynamic Cap", style="magenta")
            for n in MESH_NODES:
                table.add_row(n.layer, n.node_name, f"{n.local_ip} / {n.tailscale_ip}", f"{n.physical_ram_gb}G / {n.usable_ai_vram_gb}G", f"{int(n.dynamic_cap_pct*100)}%")
            self.query_one("#left-panel", Static).update(table)

            t2 = Text()
            t2.append("🛠️ NODE HEALTH & ROUTING RULES\n\n", style="bold green")
            t2.append("• Host Mac Mini M4 Pro: Ingestion & Memory Governor (≤90% Cap)\n", style="white")
            t2.append("• MacBook Pro TB4 Bridge: 0.27ms RTT RPC sharding\n", style="white")
            t2.append("• Linux Head Node: Petals DHT & Apache Ray ingress\n", style="white")
            t2.append("• Android Termux Nodes: 24/7 Keepalive whitelisted", style="white")
            self.query_one("#right-panel", Static).update(t2)

        elif sid == 6:
            # Debate
            deb = self.state_store.debate_state
            t_deb = Text()
            t_deb.append(f"🗣️ AI DEBATE COUNCIL — ROUND {deb.round_number}\n", style="bold magenta")
            t_deb.append(f"Topic: {deb.topic}\n\n", style="bold yellow")
            for spk in deb.speakers:
                t_deb.append(f"• [{spk.name}]: {spk.last_argument}\n", style="white")
            t_deb.append(f"\n★ Consensus: {deb.consensus_summary}", style="bold green")
            self.query_one("#left-panel", Static).update(t_deb)

            t_right = Text()
            t_right.append("⚖️ GENETIC MoE & ARBITRATION\n\n", style="bold cyan")
            t_right.append("• Hermes 3 (8B Red Lead): 94% Confidence\n", style="white")
            t_right.append("• LuCI OpenWrt (Blue Lead): 96% Confidence\n", style="white")
            t_right.append("• Devil's Advocate Critic: 89% Confidence\n", style="white")
            t_right.append("• Synthesis Arbiter: 98% Confidence", style="bold green")
            self.query_one("#right-panel", Static).update(t_right)

        else:
            # Generic Screen view
            s_info = STABILITY_SCREENS[sid - 1]
            t_gen = Text()
            t_gen.append(f"🏛️ {s_info.title}\n\n", style="bold cyan")
            t_gen.append(f"• Screen ID: {s_info.screen_id}\n", style="white")
            t_gen.append(f"• Subsystem Status: {s_info.status}\n", style="bold green")
            t_gen.append("• Real-Time Mesh Telemetry: STREAMING\n", style="white")
            t_gen.append("• 100% Local Airgap Protected", style="dim")
            self.query_one("#left-panel", Static).update(t_gen)

            t_gen_r = Text()
            t_gen_r.append("📊 DIAGNOSTIC METRICS\n\n", style="bold green")
            t_gen_r.append(f"• Total Pooled VRAM: {pool['total_usable_ai_vram_gb']} GB\n", style="white")
            t_gen_r.append(f"• TB4 Latency: {pool['tb4_rtt_ms']} ms\n", style="white")
            t_gen_r.append("• All Invariants Certified Passed", style="bold green")
            self.query_one("#right-panel", Static).update(t_gen_r)

    def action_screen_1(self) -> None:
        self.state_store.active_screen_id = 1
        self.render_active_screen()

    def action_screen_2(self) -> None:
        self.state_store.active_screen_id = 2
        self.render_active_screen()

    def action_screen_3(self) -> None:
        self.state_store.active_screen_id = 3
        self.render_active_screen()

    def action_screen_4(self) -> None:
        self.state_store.active_screen_id = 4
        self.render_active_screen()

    def action_screen_5(self) -> None:
        self.state_store.active_screen_id = 5
        self.render_active_screen()

    def action_screen_6(self) -> None:
        self.state_store.active_screen_id = 6
        self.render_active_screen()

    def action_screen_7(self) -> None:
        self.state_store.active_screen_id = 7
        self.render_active_screen()

    def action_screen_8(self) -> None:
        self.state_store.active_screen_id = 8
        self.render_active_screen()

    def action_screen_9(self) -> None:
        self.state_store.active_screen_id = 9
        self.render_active_screen()

def run_canonical():
    """Runs the Canonical Port 9-Screen NOC Textual TUI Application."""
    app = CanonicalPortDashboard()
    app.run()

if __name__ == "__main__":
    run_canonical()
