#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Lauburu Sovereign Mesh: Omni Terminal Notebook Plugin — IPython Magics
================================================================================
Subsystem: 01_apps/omniterminal_notebook_plugin/magics.py
Version: 1.0.0-NOTEBOOK-MAGICS
Lauburu Mesh Ecosystem — 2026

Defines custom IPython magics:
- %omni: Command dispatcher (status, snapshot, attach)
- %%omni_polyglot <lang>: Multi-language practice with AST check & GRPO reward
- %%omni_training <protocol>: High-ROI protocol runner & visual stream link
- %omni_telemetry: Real-time 7-layer hardware HUD
- %omni_widget: Embedded HTML5/WebSocket terminal canvas
================================================================================
"""

import sys
from pathlib import Path
from typing import Optional

try:
    from IPython.core.magic import Magics, cell_magic, line_magic, magics_class
    from IPython.display import HTML, display
    IPYTHON_AVAILABLE = True
except ImportError:
    IPYTHON_AVAILABLE = False
    # Mock base class for standalone execution outside Jupyter
    class Magics:
        def __init__(self, shell=None):
            self.shell = shell
    def line_magic(func): return func
    def cell_magic(func): return func
    def magics_class(cls): return cls

try:
    from .hardware_hud import NotebookHardwareAnalyzer
    from .polyglot_runner import NotebookPolyglotRunner
    from .training_bridge import NotebookTrainingBridge
    from .terminal_widget import OmniterminalNotebookWidget
except (ImportError, ValueError):
    from hardware_hud import NotebookHardwareAnalyzer
    from polyglot_runner import NotebookPolyglotRunner
    from training_bridge import NotebookTrainingBridge
    from terminal_widget import OmniterminalNotebookWidget


@magics_class
class OmniterminalMagics(Magics):
    def __init__(self, shell=None):
        super().__init__(shell)
        self.hardware_analyzer = NotebookHardwareAnalyzer()
        self.polyglot_runner = NotebookPolyglotRunner()
        self.training_bridge = NotebookTrainingBridge()
        self.terminal_widget = OmniterminalNotebookWidget()

    @line_magic
    def omni(self, line: str):
        """Line magic: %omni [status|snapshot|telemetry|training|widget]"""
        arg = line.strip().lower()
        if arg in ("status", ""):
            probe = self.terminal_widget.probe_daemon()
            print(f"🛰️  Omniterminal Daemon: {'ONLINE' if probe.get('online') else 'OFFLINE'}")
            print(f"   Transport:  {probe.get('transport')}")
            print(f"   Socket:     {probe.get('socket')}")
            print(f"   Latency:    {probe.get('latency_ms', 0.0):.2f} ms")
        elif arg == "snapshot":
            snap = self.hardware_analyzer.get_snapshot()
            print("================================================================================")
            print("🛰️  LAUBURU OMNITERMINAL NOTEBOOK SNAPSHOT")
            print("================================================================================")
            print(f"Host Model:       {snap.host_model}")
            print(f"RAM Sanctuary:    {snap.ram_sanctuary_headroom_gb:.2f} GB Headroom (Rule 3: {'PASS' if snap.ram_sanctuary_ok else 'FAIL'})")
            print(f"CPU & Power:      {snap.cpu_temp_c:.1f}°C • {snap.power_supply_w:.0f}W Supply")
            print(f"TB4 Ring RTT:     {snap.mesh_latencies_ms.get('L2_MacBook_Pro_TB4', 0.0):.2f} ms")
            print("================================================================================")
        elif arg == "telemetry":
            return self.omni_telemetry("")
        elif arg == "widget":
            return self.omni_widget("")
        else:
            print(f"Unknown %omni subcommand '{arg}'. Options: status, snapshot, telemetry, widget")

    @line_magic
    def omni_telemetry(self, line: str):
        """Renders authentic 7-layer hardware HUD in notebook cell."""
        html = self.hardware_analyzer.render_html_hud()
        if IPYTHON_AVAILABLE and "display" in globals():
            display(HTML(html))
        else:
            print(self.hardware_analyzer.get_snapshot().to_dict())

    @line_magic
    def omni_widget(self, line: str):
        """Renders embedded interactive terminal widget in notebook cell."""
        html = self.terminal_widget.render_html_widget()
        if IPYTHON_AVAILABLE and "display" in globals():
            display(HTML(html))
        else:
            print("[OMNITERMINAL WIDGET] HTML rendered.")

    @cell_magic
    def omni_polyglot(self, line: str, cell: str):
        """
        Cell magic: %%omni_polyglot <language>
        Executes code in isolated sandbox, validates AST, computes GRPO reward,
        and serializes verified code to continuous LoRA dataset.
        """
        lang = line.strip().lower() or "python"
        result = self.polyglot_runner.execute_code(cell, language=lang)
        html = self.polyglot_runner.render_html_result(result)
        if IPYTHON_AVAILABLE and "display" in globals():
            display(HTML(html))
        else:
            print(f"[{lang.upper()} Result] Exit: {result.exit_code} | GRPO Reward: {result.grpo_reward:+.2f}")
            if result.stdout:
                print(f"Stdout:\n{result.stdout.strip()}")
            if result.stderr:
                print(f"Stderr:\n{result.stderr.strip()}")

    @cell_magic
    def omni_training(self, line: str, cell: str):
        """
        Cell magic: %%omni_training <protocol_id>
        Interactive training protocol execution and parameter tuning.
        """
        protocol = line.strip().lower() or "grpo_compiler_reward"
        # If code provided in cell, treat as candidate completion
        candidates = None
        if cell.strip():
            candidates = [{"id": "notebook_cell_cand", "code": cell.strip()}]

        step_res = self.training_bridge.run_training_step(protocol, code_candidates=candidates)
        html = self.training_bridge.render_html_dashboard()
        if IPYTHON_AVAILABLE and "display" in globals():
            display(HTML(html))
        else:
            print(f"[Training Step: {protocol}] Result:", step_res)


if __name__ == "__main__":
    print("=== Testing OmniterminalMagics ===")
    magics = OmniterminalMagics()
    print("\n--- Testing %omni status ---")
    magics.omni("status")
    print("\n--- Testing %omni snapshot ---")
    magics.omni("snapshot")
    print("\n--- Testing %%omni_polyglot python ---")
    magics.omni_polyglot("python", "assert 10 + 20 == 30\nprint('POLYGLOT_CELL_MAGIC_PASS')")
