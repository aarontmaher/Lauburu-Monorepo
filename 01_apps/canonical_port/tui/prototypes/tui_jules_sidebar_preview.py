#!/usr/bin/env python3
"""
================================================================================
Jules AI SidebarNav TUI — Standalone Preview
================================================================================
Subsystem: 01_apps/canonical_port/tui/prototypes/tui_jules_sidebar_preview.py
Origin: Google Jules AI Remote Session 3252275295042658693

Provides an isolated, non-destructive preview of Jules's left-docked SidebarNav
layout without touching or modifying canonical_tui.py.
================================================================================
"""

from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import List, Tuple, Optional

# Ensure path includes canonical_port and tui directory
TUI_DIR = Path(__file__).resolve().parent.parent
CANONICAL_PORT_DIR = TUI_DIR.parent
sys.path.insert(0, str(TUI_DIR))
sys.path.insert(0, str(CANONICAL_PORT_DIR))

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Label
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual import events

# ─────────────────────────────────────────────────────────────────────────────
# 1. Jules SidebarNav Widget (Extracted verbatim from Session 3252275295042658693)
# ─────────────────────────────────────────────────────────────────────────────

class JulesSidebarNav(Vertical):
    """Left-docked sidebar navigation bar designed by Google Jules AI."""
    
    DEFAULT_CSS = """
    JulesSidebarNav {
        width: 26;
        height: 100%;
        background: #0b111c;
        border-right: solid #1e293b;
        padding-top: 1;
    }
    
    .sidebar-logo {
        text-style: bold;
        color: #00ffff;
        padding: 0 2 1 2;
        border-bottom: solid #1e293b;
        margin-bottom: 1;
    }
    
    .sidebar-title {
        color: #64748b;
        padding: 0 2;
        margin-bottom: 1;
        text-style: bold;
    }
    
    .sidebar-item {
        padding: 1 2;
        color: #94a3b8;
        width: 100%;
    }
    
    .sidebar-item:hover {
        background: #1e293b;
        color: #f8fafc;
    }
    
    .sidebar-item.-active {
        background: #38bdf8;
        color: #0f172a;
        text-style: bold;
    }
    """

    NAV_TABS: List[Tuple[str, str, str, str]] = [
        ("1", "AGI Console", "#00ffcc", "agi_terminal"),
        ("2", "Network NOC", "#00ffff", "network"),
        ("3", "Hardware Hub", "#38bdf8", "hardware"),
        ("4", "Biometrics DSP", "#4ade80", "biometrics"),
        ("5", "AI Inference", "#e879f9", "ai_inference"),
        ("6", "Training Gyms", "#facc15", "training"),
        ("7", "Governance", "#f43f5e", "governance"),
        ("8", "Tooling / Daemons", "#a78bfa", "tooling"),
        ("9", "Optimization", "#fb923c", "optimization"),
        ("0", "All Tabs View", "#cbd5e1", "all_tabs"),
        ("E", "Arch Explorer", "#818cf8", "explorer"),
        ("$", "Commercial Tiers", "#10b981", "commercialization"),
    ]

    def __init__(self, active_view: str = "agi_terminal", **kwargs):
        super().__init__(**kwargs)
        self.active_view = active_view

    def compose(self) -> ComposeResult:
        yield Static("⚡ LAUBURU MESH", id="sidebar-logo", classes="sidebar-logo")
        yield Static("— Navigation —", id="sidebar-title", classes="sidebar-title")
        for key, label, color, sid in self.NAV_TABS:
            item = Static(f"[{key}] {label}", id=f"nav-{sid}", classes="sidebar-item")
            setattr(item, "screen_id", sid)
            if sid == self.active_view:
                item.add_class("-active")
            yield item

    async def on_click(self, event: events.Click) -> None:
        target = event.widget
        if hasattr(target, "screen_id") and target.screen_id:
            app_inst = self.app
            if hasattr(app_inst, "switch_tab"):
                app_inst.switch_tab(target.screen_id)

    def set_active(self, screen_id: str) -> None:
        self.active_view = screen_id
        for key, label, color, sid in self.NAV_TABS:
            try:
                item = self.query_one(f"#nav-{sid}", Static)
                if sid == screen_id:
                    item.add_class("-active")
                else:
                    item.remove_class("-active")
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# 2. Main Standalone Jules Preview App
# ─────────────────────────────────────────────────────────────────────────────

class JulesSidebarPreviewApp(App):
    """Standalone preview application for Jules AI's SidebarNav layout."""

    CSS = """
    Screen {
        background: #070b12;
        color: #e2e8f0;
    }
    
    #main-layout {
        width: 100%;
        height: 100%;
    }
    
    #content-container {
        width: 1fr;
        height: 100%;
        padding: 1 2;
        background: #070b12;
    }
    
    .panel-header {
        text-style: bold;
        color: #38bdf8;
        padding-bottom: 1;
        border-bottom: solid #1e293b;
        margin-bottom: 1;
    }
    
    .metric-card {
        border: round #334155;
        padding: 1;
        margin-bottom: 1;
        background: #0f172a;
    }
    """

    BINDINGS = [
        ("1", "nav('agi_terminal')", "AGI Console"),
        ("2", "nav('network')", "Network"),
        ("3", "nav('hardware')", "Hardware"),
        ("4", "nav('biometrics')", "Biometrics"),
        ("5", "nav('ai_inference')", "Inference"),
        ("6", "nav('training')", "Training"),
        ("7", "nav('governance')", "Governance"),
        ("8", "nav('tooling')", "Tooling"),
        ("9", "nav('optimization')", "Optimization"),
        ("q", "quit", "Quit Preview"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-layout"):
            self.sidebar = JulesSidebarNav(active_view="agi_terminal", id="jules-sidebar")
            yield self.sidebar
            with ScrollableContainer(id="content-container"):
                self.content_title = Label("🤖 Screen 1: Master AGI Coding Console & Swarm Shell", classes="panel-header")
                yield self.content_title
                self.content_body = Static(self._render_view("agi_terminal"), id="active-content")
                yield self.content_body
        yield Footer()

    def action_nav(self, screen_id: str) -> None:
        self.switch_tab(screen_id)

    def switch_tab(self, screen_id: str) -> None:
        self.sidebar.set_active(screen_id)
        titles = {
            "agi_terminal": "🤖 Screen 1: Master AGI Coding Console & Swarm Shell",
            "network": "🌐 Screen 2: Multi-WAN Network Matrix & 10Gbps TB4 DMA",
            "hardware": "⚡ Screen 3: 7-Layer Physical Compute Nodes & Thermals",
            "biometrics": "🫀 Screen 4: Medical 512Hz Movesense ECG & Pan-Tompkins DSP",
            "ai_inference": "🧠 Screen 5: 8-Engine Distributed Sharding Router",
            "training": "🏋️ Screen 6: 6 AI Training Gyms & Continuous LoRA Arena",
            "governance": "🏛️ Screen 7: Tri-Orchestrator Consensus & ELO Leaderboard",
            "tooling": "🛠️ Screen 8: OS Daemon Supervisor & Hardware Watchdog",
            "optimization": "💾 Screen 9: Storage Tri-Vault Health & PySpark Lake",
            "all_tabs": "📑 Screen 0: All Integrated Views",
            "explorer": "🌲 Screen E: Obsidian Sugiyama AST Architecture Explorer",
            "commercialization": "🛍️ Screen $: Headless Shopify Commerce & Subscriptions",
        }
        self.content_title.update(titles.get(screen_id, screen_id.title()))
        self.content_body.update(self._render_view(screen_id))

    def _render_view(self, screen_id: str) -> str:
        if screen_id == "agi_terminal":
            return (
                "╭─ 💻 Single Stream Code Editor [1x1] ────────────────────────────────────────╮\n"
                "│ Line   Source Code Buffer (Active Working Buffer)                            │\n"
                "│ 001    # Jules SidebarNav Layout Active                                      │\n"
                "│ 002    # 108.0 GB Pooled RAM | 82.8 GB VRAM | 7 Compute Nodes               │\n"
                "│ 003    # Left Docked Sidebar (Width: 26) with Direct Mouse/Key Switching     │\n"
                "╰─────────────────────────────────────────────────────────────────────────────╯\n\n"
                "► Inference Engine: [LLAMA_RPC: ACTIVE] (Port 8081 | 18.5ms TTFT)\n"
                "► Jules AI Session: 3252275295042658693 (Sidebar Navigation Standalone Preview)\n"
                "► Status: Clean isolated preview — canonical_tui.py is untouched."
            )
        elif screen_id == "network":
            return (
                "╭─ 🌐 7-Node Physical Health Matrix ─────────────────────────────────────────╮\n"
                "│ • L1 Mac Mini M4 Pro : 192.168.8.230  [ONLINE] ⚡ Memory Governor (Cap 90%)│\n"
                "│ • L2 MacBook Pro TB4 : 169.254.114.190 [ONLINE] ⚡ 10Gbps DMA (0.204ms RTT) │\n"
                "│ • L3 Linux Head Node : 192.168.8.224  [ONLINE] ⚡ Vulkan Petals / Docker Hub│\n"
                "│ • L4 Linux Tablet    : 100.81.92.125  [ONLINE] ⚡ Mobile Compute / Touch DSP │\n"
                "│ • L5 MacBook Air M4  : 192.168.8.222  [ONLINE] ⚡ Metal Performance Shaders │\n"
                "│ • L6 Pixel 10 Pro XL : 100.73.38.87   [ONLINE] ⚡ Tensor G5 Edge TPU        │\n"
                "│ • L7 Samsung S20     : 100.84.40.95   [ONLINE] ⚡ Automated UI ADB Target   │\n"
                "│ • GW GL.iNet Router  : 192.168.8.1    [ONLINE] ⚡ Core USB Bridge & WoL Hub │\n"
                "╰─────────────────────────────────────────────────────────────────────────────╯"
            )
        elif screen_id == "biometrics":
            return (
                "╭─ 🫀 Movesense Medical 512Hz ECG Telemetry ─────────────────────────────────╮\n"
                "│ HR: 134 BPM | RMSSD: 48.2ms | Zone 2 DFA-alpha1: 0.750                      │\n"
                "│ Pan-Tompkins QRS DSP: LOCKED | Optical PPG SpO2: 98.4%                      │\n"
                r"│ Waveform: _/\\__/\\__/\\___/\\__/\\___/\\_/\\_/\\___/\\__/\\___                       │\n"
                "╰─────────────────────────────────────────────────────────────────────────────╯"
            )
        else:
            return f"[{screen_id.upper()}]\n\nRendering telemetry and data widgets for {screen_id}...\n- Layout: Left-docked SidebarNav\n- Status: ACTIVE"

if __name__ == "__main__":
    app = JulesSidebarPreviewApp()
    app.run()
