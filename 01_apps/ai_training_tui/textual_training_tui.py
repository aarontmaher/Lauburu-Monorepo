#!/usr/bin/env python3
"""
================================================================================
Lauburu Sovereign Mesh: Textual AI Training UI (Multi-Tabbed)
================================================================================
"""
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane, Static, DataTable, Log
from textual.containers import Grid, ScrollableContainer
from rich.text import Text
from rich.table import Table
import random
import time

# Mocking ELO Data for the Leaderboard
MODELS_ELO = [
    ("Qwen 3.8 Max (Master Orchestrator)", 1684.5, "👑 Champion"),
    ("Swarm Delta Apex (Dual-Plane + Gemini High)", 1624.3, "🥈 Challenger"),
    ("Qwen 3.8 Max 27B Abliterated", 1599.0, "🔴 Red Team"),
    ("Qwen 2.5 Coder 32B (Local Metal TB4)", 1530.2, "⚙️ Heavy Worker"),
    ("Qwen 2.5 Coder 7B (Local Syntax)", 1410.8, "⚡ Fast Worker"),
    ("NanoVision UI Encoder (7M)", 1250.0, "👁️ Vision Subagent"),
    ("SmolLM2-135M", 1120.4, "📝 Speculative Drafter")
]

class DashboardPane(Static):
    """Main Training Dashboard Tab"""
    def compose(self) -> ComposeResult:
        # Display the rich content from the original training UI if we wanted,
        # but for now we put a placeholder status screen.
        yield Static(
            "🚀 [b]Training Protocols Active:[/b] GRPO, DPO, Genetic MoE\n\n"
            "⚙️  [b]Hardware:[/b] Mac Mini M4 Pro | [green]Safe 9.6GB Headroom[/green]\n"
            "🌐 [b]Network:[/b] 7-Layer Tailscale Mesh ONLINE\n\n"
            "The training arena is currently distilling knowledge from the\n"
            "architectural debates into the 24/7 continuous_lora_dataset.jsonl",
            classes="dashboard_text"
        )

class LeaderboardPane(Static):
    """ELO Leaderboard Tab"""
    def compose(self) -> ComposeResult:
        yield DataTable(id="elo_table")
        
    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Model / Agent", "Bradley-Terry ELO", "Rank / Role")
        table.cursor_type = "row"
        for name, elo, role in MODELS_ELO:
            table.add_row(name, f"{elo:.1f}", role)

class EntertainmentPane(Static):
    """The 'Entertaining' Tab (Matrix/Speculation feed)"""
    def compose(self) -> ComposeResult:
        yield Log(id="matrix_log", highlight=True)
        
    def on_mount(self) -> None:
        self.update_log()
        self.set_interval(1.5, self.update_log)
        
    def update_log(self) -> None:
        log = self.query_one(Log)
        events = [
            "[green]Speculative Draft (10M -> 7B):[/green] Match! 85% Token overlap. ELO +0.5",
            "[yellow]Genetic MoE:[/yellow] Mutating speculative_depth_chain from 2 -> 3.",
            "[red]Red Team Veto:[/red] Rejected unsafe prompt bypassing Rule 4.",
            "[cyan]Screen Lens:[/cyan] Parsed 45 UI bounding boxes in 8.4ms.",
            "[magenta]Movesense HR+:[/magenta] R-Peak Detected. Pulse stable at 62 BPM.",
            "[white]Qwen 3.8 Max:[/white] Resolving architectural dispute across the mesh...",
        ]
        log.write_line(f"[{time.strftime('%H:%M:%S')}] {random.choice(events)}")

class LauburuTrainingApp(App):
    """The main Textual application."""
    CSS = """
    Screen {
        background: $surface;
    }
    .dashboard_text {
        padding: 2;
        content-align: center middle;
        height: 100%;
    }
    DataTable {
        height: 100%;
        margin: 1;
    }
    Log {
        padding: 1;
        background: #111;
        color: #0f0;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "app.toggle_dark", "Toggle dark mode")
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(initial="dashboard"):
            with TabPane("Monitor Dashboard", id="dashboard"):
                yield DashboardPane()
            with TabPane("🏆 ELO Leaderboard", id="leaderboard"):
                yield LeaderboardPane()
            with TabPane("👁️ Live Neural Matrix", id="entertainment"):
                yield EntertainmentPane()
        yield Footer()

if __name__ == "__main__":
    app = LauburuTrainingApp()
    app.run()
