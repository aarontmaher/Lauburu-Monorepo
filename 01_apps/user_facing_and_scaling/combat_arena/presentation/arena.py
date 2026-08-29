"""
Combat Arena Presentation Engine & Textual HUD.
===============================================
Subsystem: 01_apps/user_facing_and_scaling/combat_arena/presentation/arena.py
"""

import sys
import time
from typing import Optional, Dict, Any

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button
from textual.containers import Container, Horizontal, Vertical
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..core.config import ArenaConfig
from ..core.state import ArenaStateStore
from ..core.models import PulseTelemetry
from ..modes import (
    execute_tug_of_war_step,
    execute_battle_step,
    execute_proximity_step,
    execute_defense_step,
    GAME_MODES,
)
from .power_bar import render_power_bar
from .pulse_gauge import render_pulse_gauge
from .rag_voice import RagVoiceCommentator

class CombatArenaEngine:
    """Core logic engine coordinating game modes, biofeedback, and duels."""

    def __init__(self, config: Optional[ArenaConfig] = None):
        self.config = config or ArenaConfig()
        self.state_store = ArenaStateStore(config=self.config)
        self.commentator = RagVoiceCommentator(tts_enabled=False)

    def step(self) -> Dict[str, Any]:
        """Executes a single game tick across the active mode."""
        self.state_store.step_count += 1
        mode = self.state_store.active_mode
        pulse = self.state_store.get_pulse_telemetry()
        hr = pulse.heart_rate_bpm if pulse.heart_rate_bpm is not None else 72.0

        if mode == "TUG_OF_WAR":
            res = execute_tug_of_war_step(self.state_store.red.energy_level, self.state_store.blue.energy_level, pulse_hr=hr)
            self.state_store.red.energy_level = res["red_energy"]
            self.state_store.blue.energy_level = res["blue_energy"]
            red_intent = res["red_intent"]
            blue_intent = res["blue_intent"]
        elif mode == "PROXIMITY":
            res = execute_proximity_step()
            red_intent = res["red_intent"]
            blue_intent = res["blue_intent"]
        elif mode == "DEFENSE":
            res = execute_defense_step()
            red_intent = res["red_intent"]
            blue_intent = res["blue_intent"]
        else:  # BATTLE / SMOLAGENTS_PYTHON_DUEL
            res = execute_battle_step()
            red_intent = res["red_action"]["intent"]
            blue_intent = res["blue_action"]["intent"]

        self.state_store.red.current_objective = red_intent
        self.state_store.blue.current_objective = blue_intent
        narration = self.commentator.generate_narration(mode, red_intent, blue_intent)

        snap = self.state_store.snapshot()
        return {
            "step": self.state_store.step_count,
            "mode": mode,
            "power_bar_ratio": snap.power_bar_ratio,
            "red_intent": red_intent,
            "blue_intent": blue_intent,
            "pulse": pulse,
            "narration": narration
        }

class CombatArenaApp(App):
    """Full-featured interactive Textual TUI for Lauburu Combat Arena."""

    TITLE = "⚔️ LAUBURU COMBAT ARENA — MULTI-MODE DUEL"
    SUB_TITLE = "Hermes 3 Red vs. LuCI Blue • 120 FPS Compute Power • Live Movesense HUD"

    CSS = """
    Screen {
        background: #070b12;
        color: #f8fafc;
    }
    #power-bar-container {
        height: 4;
        margin: 1 1;
        background: #0b111c;
        border: solid #1e293b;
        align: center middle;
    }
    #main-container {
        height: 1fr;
        margin: 0 1;
    }
    .col-box {
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
        ("1", "mode_tug_of_war", "Tug-of-War"),
        ("2", "mode_battle", "Battle Duel"),
        ("3", "mode_proximity", "Proximity"),
        ("4", "mode_defense", "Mesh Defense"),
    ]

    def __init__(self, config: Optional[ArenaConfig] = None):
        super().__init__()
        self.engine = CombatArenaEngine(config=config)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="power-bar-container"):
            yield Static(id="power-bar", classes="power-bar")

        with Horizontal(id="main-container"):
            yield Static(id="red-team-box", classes="col-box")
            yield Static(id="pulse-box", classes="col-box")
            yield Static(id="blue-team-box", classes="col-box")

        with Horizontal(id="footer-bar"):
            yield Static("⚔️ [1] Tug-of-War [2] Battle [3] Proximity [4] Defense • [q] Quit", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self.tick()
        self.set_interval(1.0 / 30.0, self.tick)  # Smooth responsive refresh

    def tick(self) -> None:
        data = self.engine.step()
        
        # 1. Power bar
        pb = render_power_bar(data["power_bar_ratio"], width=40)
        self.query_one("#power-bar", Static).update(pb)

        # 2. Red Faction
        t_red = Text()
        t_red.append("🔴 RED ATTACKERS (HERMES 3)\n", style="bold red")
        t_red.append(f"• Energy: {self.engine.state_store.red.energy_level:.1f}%\n", style="white")
        t_red.append(f"• Objective: {data['red_intent'][:80]}\n", style="yellow")
        t_red.append("• Target: Port 50052 TB4 Buffer", style="dim")
        self.query_one("#red-team-box", Static).update(t_red)

        # 3. Pulse gauge
        pg = render_pulse_gauge(data["pulse"])
        self.query_one("#pulse-box", Static).update(pg)

        # 4. Blue Faction
        t_blue = Text()
        t_blue.append("🔵 BLUE DEFENDERS (LUCI SENTINEL)\n", style="bold blue")
        t_blue.append(f"• Energy: {self.engine.state_store.blue.energy_level:.1f}%\n", style="white")
        t_blue.append(f"• Objective: {data['blue_intent'][:80]}\n", style="cyan")
        t_blue.append("• Shield: OpenWrt SQM fq_codel / Airgap", style="dim")
        self.query_one("#blue-team-box", Static).update(t_blue)

    def action_mode_tug_of_war(self) -> None:
        self.engine.state_store.active_mode = "TUG_OF_WAR"

    def action_mode_battle(self) -> None:
        self.engine.state_store.active_mode = "BATTLE"

    def action_mode_proximity(self) -> None:
        self.engine.state_store.active_mode = "PROXIMITY"

    def action_mode_defense(self) -> None:
        self.engine.state_store.active_mode = "DEFENSE"

def run_arena():
    """Runs the Combat Arena Textual TUI Application."""
    app = CombatArenaApp()
    app.run()

if __name__ == "__main__":
    run_arena()
