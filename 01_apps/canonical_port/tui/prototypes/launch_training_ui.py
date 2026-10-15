#!/usr/bin/env python3
"""
==============================================================================
Standalone Launcher for Canonical Port TUI — Screen 6: AI Training UI
==============================================================================
Subsystem: 01_apps/canonical_port/tui/prototypes/launch_training_ui.py
Lauburu Mesh Ecosystem — 2026

Direct entrypoint into the AI Training UI, displaying:
1. Red/Blue Adversarial Arena (Zero Trust WAF & <think> streams)
2. 24/7 LoRA SFT & DPO Ingestion Pipeline (Loss trajectory, dataset harvest)
3. The 5 Lauburu AI Gyms (Healing, Stealth, ELO Dev Game, 3D Kinematics)
4. Structural AST PySpark Codebase Crawl Metrics
5. AgentWorld-35B Training Panel
==============================================================================
"""

import os
import sys
from pathlib import Path

# Setup paths
TUI_DIR = Path(__file__).resolve().parent.parent
CANONICAL_PORT_DIR = TUI_DIR.parent
sys.path.insert(0, str(TUI_DIR))
sys.path.insert(0, str(CANONICAL_PORT_DIR))

from textual.app import App, ComposeResult
from views.training_view import TrainingView

class StandaloneTrainingApp(App):
    CSS = """
    Screen {
        background: #070b12;
        color: #e2e8f0;
    }
    """
    TITLE = "⚡ LAUBURU AI TRAINING & GYMS CONSOLE"

    def on_mount(self) -> None:
        self.push_view(TrainingView())

if __name__ == "__main__":
    app = StandaloneTrainingApp()
    app.run()
