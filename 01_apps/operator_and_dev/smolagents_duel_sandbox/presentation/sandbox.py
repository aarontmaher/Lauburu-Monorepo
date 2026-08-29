"""
SmolAgents Python Duel Sandbox Presentation & TUI.
==================================================
Subsystem: 01_apps/operator_and_dev/smolagents_duel_sandbox/presentation/sandbox.py
"""

import sys
import time
from typing import Optional, Dict, Any, List

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button
from textual.containers import Container, Horizontal, Vertical
from rich.panel import Panel
from rich.text import Text

from ..core.config import SandboxConfig
from ..core.models import AgentAction, DuelExecutionRecord
from ..tools.registry import SmolagentsToolRegistry
from ..tools.sandbox import PythonCodeSandbox

class SmolAgentsArenaHub:
    """Coordinating hub for agentic duelists executing sandboxed Python code."""

    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self.sandbox = PythonCodeSandbox(config=self.config)
        self.step_count = 0

    def step(self) -> DuelExecutionRecord:
        """Executes a duel tick between Hermes 3 Red and LuCI Blue."""
        self.step_count += 1
        
        red_code = """
def red_action():
    # Probe TB4 DMA buffer & check latency
    lat = tools.get_mesh_latency('Mac_Node', 'MacBook_Pro')
    return {'action': 'TB4_PROBE', 'latency_ms': lat, 'status': 'OPTIMAL'}
result = red_action()
"""
        blue_code = """
def blue_action():
    # Run Kamath 20% filter on biometric pulse
    kamath = tools.apply_kamath_filter(hr_bpm=72.0, threshold=0.20)
    vram = tools.inspect_vram_load()
    return {'action': 'FILTER_GUARD', 'kamath': kamath, 'vram': vram}
result = blue_action()
"""
        act_red = self.sandbox.execute_action(AgentAction(
            agent_id="hermes_3_red",
            faction="RED",
            intent="Probe TB4 DMA latency & buffer capacity",
            python_code=red_code
        ))
        act_blue = self.sandbox.execute_action(AgentAction(
            agent_id="luci_blue",
            faction="BLUE",
            intent="Validate Kamath 20% filter & monitor VRAM load",
            python_code=blue_code
        ))

        return DuelExecutionRecord(
            step_id=self.step_count,
            timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            red_action=act_red,
            blue_action=act_blue,
            evaluation_score_delta=1.2,
            tactical_summary=f"Round {self.step_count}: Red executed TB4 probe in {act_red.execution_time_ms}ms; Blue verified Kamath filter in {act_blue.execution_time_ms}ms."
        )

class SmolAgentsDuelApp(App):
    """Textual TUI for SmolAgents Python Duel Sandbox."""

    TITLE = "🤖 SMOLAGENTS PYTHON DUEL SANDBOX"
    SUB_TITLE = "Code-as-Action Agentic Duelists • Hermes 3 Red vs. LuCI Blue"

    CSS = """
    Screen {
        background: #070b12;
        color: #f8fafc;
    }
    #top-bar {
        height: 3;
        background: #0b111c;
        border-bottom: solid #1e293b;
        align: center middle;
    }
    #main-container {
        height: 1fr;
        margin: 1 1;
    }
    .duel-box {
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
        ("s", "step_duel", "Step Duel"),
    ]

    def __init__(self):
        super().__init__()
        self.hub = SmolAgentsArenaHub()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="top-bar"):
            yield Static("🤖 SmolAgents Code-as-Action Tool Sandbox • Sandboxed Python Execution Engine", id="header-text")

        with Horizontal(id="main-container"):
            yield Static(id="red-duel-box", classes="duel-box")
            yield Static(id="blue-duel-box", classes="duel-box")

        with Horizontal(id="footer-bar"):
            yield Static("⚡ Press [s] Step Duel • [q] Quit", id="status-text")
        yield Footer()

    def on_mount(self) -> None:
        self.tick()
        self.set_interval(1.0, self.tick)

    def tick(self) -> None:
        record = self.hub.step()

        # Red Box
        tr = Text()
        tr.append(f"🔴 RED DUELIST: {record.red_action.agent_id.upper()}\n", style="bold red")
        tr.append(f"• Intent: {record.red_action.intent}\n", style="yellow")
        tr.append(f"• Exec Time: {record.red_action.execution_time_ms} ms\n", style="white")
        tr.append(f"• Status: {record.red_action.status}\n\n", style="bold green")
        tr.append("Python Code-as-Action:\n", style="bold cyan")
        tr.append(record.red_action.python_code.strip()[:180] + "...", style="dim")
        self.query_one("#red-duel-box", Static).update(tr)

        # Blue Box
        tb = Text()
        tb.append(f"🔵 BLUE DUELIST: {record.blue_action.agent_id.upper()}\n", style="bold blue")
        tb.append(f"• Intent: {record.blue_action.intent}\n", style="cyan")
        tb.append(f"• Exec Time: {record.blue_action.execution_time_ms} ms\n", style="white")
        tb.append(f"• Status: {record.blue_action.status}\n\n", style="bold green")
        tb.append("Python Code-as-Action:\n", style="bold cyan")
        tb.append(record.blue_action.python_code.strip()[:180] + "...", style="dim")
        self.query_one("#blue-duel-box", Static).update(tb)

    def action_step_duel(self) -> None:
        self.tick()

def run_sandbox():
    """Runs the SmolAgents Duel Sandbox Textual TUI Application."""
    app = SmolAgentsDuelApp()
    app.run()

if __name__ == "__main__":
    run_sandbox()
