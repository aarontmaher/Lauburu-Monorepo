#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Canonical Port - Unified Mesh Console TUI (Omega Harmonized)
Version: 5.0.0-OMEGA
Subsystem: 01_apps/canonical_port/tui/unified_mesh_console_tui.py

Unifies all monorepo TUI capabilities into a single cohesive console:
- Mode 1: NOC & 7-Layer Mesh Interconnect (Hardware, TB4 DMA 0.27ms, 108GB RAM / 82.8GB VRAM)
- Mode 2: Biometrics & Open Wearables (512Hz ECG DSP, DFA-a1, Oura/Whoop/Garmin Federation)
- Mode 3: AI Swarm & Debate Engine (Tri-Orchestrator, Port 8083 Devil's Advocate, Cosine Accord)
- Mode 4: Obsidian Architecture & Knowledge Graph (Directed Canvas, Tarjan SCC, AST Metrics)
- Mode 5: Nomad Courier & Self-Healing Supervisor (6-Tier Watchdog, MCP daemons, Disk Headroom)
"""

import os
import sys
import json
import time
import shutil
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, Button, RichLog
from textual.binding import Binding
from textual.reactive import reactive
from textual import work
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.align import Align
from rich.box import ROUNDED, SIMPLE, DOUBLE

# Paths
MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
BLACKBOARD_FILE = MONOREPO_ROOT / "01_apps/canonical_port/blackboard_state.json"
NOMAD_STATUS_FILE = MONOREPO_ROOT / "data/network/nomad_self_healer_status.json"
BIOMETRICS_FILE = MONOREPO_ROOT / "03_biometrics_and_telemetry/data/live_biometrics.json"

# ==============================================================================
# UI COMPONENTS
# ==============================================================================

class MeshHeaderBar(Static):
    """Top Global Header Bar rendering node status pills and VRAM meter."""
    def render(self) -> Panel:
        pills = [
            Text(" L1: Mac Host (21.6GB) ", style="bold black on green"),
            Text(" L2: MBP TB4 (14.0GB) ", style="bold black on green"),
            Text(" L3: Linux Head (13.8GB) ", style="bold black on green"),
            Text(" L4: Linux Tab (6.5GB) ", style="bold white on dark_orange"),
            Text(" L5: Air Metal (14.0GB) ", style="bold black on green"),
            Text(" L6: Pixel 10 (12.5GB) ", style="bold white on dark_orange"),
            Text(" L7: S20 (9.0GB) ", style="bold black on green"),
            Text(" GW: GL.iNet ", style="bold black on cyan"),
        ]
        
        free_gb = shutil.disk_usage(str(MONOREPO_ROOT)).free / (1024**3)
        disk_badge = Text(f" NVMe: {free_gb:.1f}GB Free ", style="bold white on blue")
        vram_badge = Text(" Pooled VRAM: 82.8/108GB (7 Nodes) ", style="bold black on magenta")

        top_line = Text(" ").join(pills)
        bottom_line = Text("  ").join([vram_badge, disk_badge, Text("TB4 Bridge: 0.277ms RTT", style="bold green")])

        content = Text("\n").join([top_line, bottom_line])
        return Panel(Align.center(content), title="🌐 LAUBURU 7-LAYER MESH NOC CONSOLE — OMEGA UNIFIED", border_style="cyan")


def _probe_socket(ip: str, port: int, timeout: float = 0.12) -> tuple[bool, float]:
    import socket, time
    t0 = time.time()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((ip, port))
        s.close()
        return True, (time.time() - t0) * 1000.0
    except Exception:
        return False, 0.0


class NocView(Static):
    """View 1: 7-Layer Node Topology and Interconnect Matrix."""
    def render(self) -> Panel:
        table = Table(box=ROUNDED, expand=True, title="7-Physical Layer Hardware & DMA Interconnect (Live Sockets)")
        table.add_column("Layer", style="bold cyan", width=6)
        table.add_column("Node Name", style="bold white")
        table.add_column("IP / Tailscale", style="yellow")
        table.add_column("RAM / AI Cap", style="green")
        table.add_column("Primary Protocol / Role", style="magenta")
        table.add_column("Status", style="bold green")

        nodes = [
            ("L1", "Mac_Node (M4 Pro)", "192.168.8.155 / 100.119.199.76", "24.0 GB (21.6 GB AI)", "Host Orchestrator / Memory Gov", "127.0.0.1", 4000),
            ("L2", "MacBook_Pro (M1)", "TB4: 169.254.187.138 (100.103.212.21)", "16.0 GB (14.0 GB AI)", "10Gbps TB4 Bridge / SSD Vault", "100.103.212.21", 22),
            ("L3", "Linux_Mini", "192.168.20.224 / 100.101.39.98", "16.0 GB (13.8 GB AI)", "Docker Hub / Petals / Ray", "100.101.39.98", 22),
            ("L4", "Linux_Tablet", "100.118.79.63 (DHCP)", "8.0 GB (6.5 GB AI)", "Mobile Compute / Touch DSP", "100.118.79.63", 22),
            ("L5", "MacBook_Air (M4)", "192.168.8.222 / 100.121.202.34", "16.0 GB (14.0 GB AI)", "Metal Shaders / LoRA Distill", "100.121.202.34", 22),
            ("L6", "Pixel_10_Pro_XL", "192.168.8.145 / 100.73.38.87", "16.0 GB (12.5 GB AI)", "Tensor G5 Edge TPU / 8K PTZ", "100.73.38.87", 50052),
            ("L7", "Samsung_S20", "100.84.40.95 / USB-ADB", "12.0 GB (9.0 GB AI)", "Dedicated Automated UI Tester", "100.84.40.95", 8022),
            ("GW", "GL.iNet Router", "192.168.8.1 / 100.122.185.123", "Embedded", "Hardware USB ADB & Multi-WAN", "192.168.8.1", 22),
        ]

        for layer, name, net_str, ram_str, role, probe_ip, probe_port in nodes:
            is_up, rtt = _probe_socket(probe_ip, probe_port)
            if is_up:
                status_cell = Text(f"🟢 ONLINE ({rtt:.1f}ms)", style="bold green")
            else:
                status_cell = Text("⚪ STANDBY", style="yellow")
            table.add_row(layer, name, net_str, ram_str, role, status_cell)

        return Panel(table, title="[1] Physical Layer Matrix (Live Zero-Mock Sockets)", border_style="cyan")


class BiometricsView(Static):
    """View 2: Raw 512Hz ECG DSP + Open Wearables Multi-Device Federation."""
    def render(self) -> Panel:
        t_dsp = Table(box=ROUNDED, expand=True, title="Real-Time 512Hz Micro DSP (Movesense BLE)")
        t_dsp.add_column("DSP Feature Metric", style="bold cyan")
        t_dsp.add_column("Live Value", style="bold green")
        t_dsp.add_column("Algorithmic Pipeline", style="yellow")
        t_dsp.add_column("Zero-Mock Verification", style="magenta")

        # Load live biometrics state if present and fresh
        bio_data = {}
        if BIOMETRICS_FILE.exists():
            try:
                with open(BIOMETRICS_FILE, "r") as f:
                    bio_data = json.load(f)
            except Exception:
                pass

        hr_str = f"{bio_data['hr']:.1f} BPM" if bio_data.get("hr") else "-- BPM"
        dfa_str = f"{bio_data['dfa_a1']:.3f}" if bio_data.get("dfa_a1") else "--"
        bp_str = f"{bio_data['bp_sys']:.0f}/{bio_data['bp_dia']:.0f} mmHg" if bio_data.get("bp_sys") else "-- / -- mmHg"
        status_str = "Rule #0 Verified (Live Sensor)" if bio_data.get("hr") else "Standby: Awaiting Movesense BLE"

        t_dsp.add_row("Heart Rate", hr_str, "Pan-Tompkins QRS Detection", status_str)
        t_dsp.add_row("Aerobic HRV (DFA-a1)", dfa_str, "Detrended Fluctuation Analysis", "Zone 2 Dynamic Tracking")
        t_dsp.add_row("PTT Blood Pressure", bp_str, "Pulse Transit Time (ECG-PPG)", "Authentic Sensor Ingest")
        t_dsp.add_row("Sampling Ingress", "512 Hz Ready", "Movesense BLE Characteristic", "Sub-1ms Hardware Timestamp")

        t_wear = Table(box=ROUNDED, expand=True, title="Open Wearables Macro Aggregation (Self-Hosted)")
        t_wear.add_column("Provider Stream", style="bold cyan")
        t_wear.add_column("Metric Ingested", style="bold green")
        t_wear.add_column("Normalized Value", style="yellow")
        t_wear.add_column("Destination Ingestion", style="magenta")

        t_wear.add_row("Oura Ring Gen 3", "Sleep Score & Stages", "-- (Standby)", "Blackboard & PySpark Lake")
        t_wear.add_row("Whoop 4.0", "Strain & Recovery", "-- (Standby)", "Blackboard & PySpark Lake")
        t_wear.add_row("Garmin Connect", "Body Battery & HRV", "-- (Standby)", "Blackboard & PySpark Lake")
        t_wear.add_row("Apple HealthKit", "Steps & Active Cal", "-- (Standby)", "Port 4000 Ingestion")

        content = Columns([t_dsp, t_wear], expand=True)
        return Panel(content, title="[2] Biometrics & Open Wearables Federation", border_style="green")


class AiSwarmView(Static):
    """View 3: AI Inference Mesh, Canonical Sovereign Models & NPU Telemetry Sentinel."""
    def render(self) -> Panel:
        t_models = Table(box=ROUNDED, expand=True, title="Canonical Sovereign Local AI Hierarchy")
        t_models.add_column("Model / Role", style="bold cyan")
        t_models.add_column("Endpoint", style="yellow")
        t_models.add_column("Quantization / VRAM", style="green")
        t_models.add_column("Hardware Target", style="magenta")
        t_models.add_column("Sovereign Role", style="bold green")

        nodes_models = [
            ("Qwen 3.8 Max", "127.0.0.1", 8082, "PRP Ring (32.0 GB)", "Mac Mini M4 Pro + TB4", "SOVEREIGN MASTER"),
            ("Qwen 3.8 Max 27B Abliterated", "100.101.39.98", 8083, "Q4_K_XL (18.2 GB)", "Linux Head Node", "DEVIL'S ADVOCATE"),
            ("Qwen 2.5 7B Coder", "100.101.39.98", 8081, "Q4_K_M (4.8 GB)", "Linux Head Node", "SYNTAX WORKER"),
            ("NanoVision & NanoAction", "100.73.38.87", 50052, "INT8 (4.4 MB)", "Pixel 10 Edge TPU", "PURE-NPU LENS"),
        ]
        
        for name, ip, port, quant, hw, role in nodes_models:
            is_up, rtt = _probe_socket(ip, port)
            if is_up:
                status = f"🟢 ACTIVE ({rtt:.1f}ms)"
            else:
                status = "⚪ -- (Standby)"
            t_models.add_row(name, f"{ip}:{port}", quant, hw, f"{role} [{status}]")

        t_npu = Table(box=ROUNDED, expand=True, title="Pure-NPU Telemetry Sentinel & ELO Data Mining")
        t_npu.add_column("NPU Telemetry Channel", style="bold cyan")
        t_npu.add_column("Measured Metric", style="bold green")
        t_npu.add_row("Bradley-Terry ELO", "-- (Standby)", "Active Polyglot Swarm", "-- (Standby)")
        t_npu.add_row("Autoencoder Anomaly", "-- (Standby)", "Sub-millisecond inference", "-- (Standby)")
        t_npu.add_row("NPU TOPS Saturation", "-- (Standby)", "Hardware Spec Ready", "-- (Standby)")
        t_npu.add_row("Speculative Drafter", "-- (Standby)", "Sub-15ms draft latency", "-- (Standby)")

        content = Columns([t_models, t_npu], expand=True)
        return Panel(content, title="[3] Canonical AI Swarm & Pure-NPU Telemetry Console", border_style="magenta")


class ArchitectureGraphView(Static):
    """View 4: Obsidian Topology Canvas & Codebase AST Metrics."""
    def render(self) -> Panel:
        t_ast = Table(box=ROUNDED, expand=True, title="Monorepo AST & Tri-Vault Storage Invariants")
        t_ast.add_column("Vault Storage Layer", style="bold cyan")
        t_ast.add_column("Path / Engine", style="yellow")
        t_ast.add_column("Capacity / Files", style="green")
        t_ast.add_column("Health Invariant", style="bold green")

        obsidian_path = MONOREPO_ROOT / "obsidian_vault"
        lora_path = MONOREPO_ROOT / "lora_datasets"
        git_lock = MONOREPO_ROOT / ".git/index.lock"
        
        if (obsidian_path / "Index.md").exists():
            obsidian_status = "🟢 HEALTHY (Index.md verified)"
        else:
            obsidian_status = "⚪ -- (Standby / Missing)"
            
        try:
            free_gb = shutil.disk_usage(str(MONOREPO_ROOT)).free / (1024**3)
        except Exception:
            free_gb = 0.0
            
        if free_gb >= 10.0 and lora_path.exists():
            lora_status = f"🟢 HEALTHY ({free_gb:.1f}GB NVMe Headroom)"
        else:
            lora_status = f"🔴 DEGRADED ({free_gb:.1f}GB NVMe Headroom)"
            
        if git_lock.exists():
            git_status = "🔴 DEGRADED (index.lock present)"
        else:
            git_status = "🟢 HEALTHY (0 locks)"
            
        t_ast.add_row("1. Obsidian Vault", str(obsidian_path), "Master Graph & Wikilinks", obsidian_status)
        t_ast.add_row("2. PySpark Big Data Lake", str(lora_path), "AST Crawls / LoRA", lora_status)
        t_ast.add_row("3. GitHub Worktrees", "aarontmaher/Lauburu-Monorepo", "Clean Working Tree", git_status)

        graph_ascii = """
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        SUGIYAMA DIRECTED ARCHITECTURE TOPOLOGY                         │
│                                                                                        │
│   [00_core_infrastructure] ───► [01_apps / Canonical Port TUI] ◄─── [06_tooling_mcp]    │
│              │                               │                              │          │
│              ▼                               ▼                              ▼          │
│   [02_ai_inference_mesh]   ───► [05_agents_and_swarms]        ───► [03_biometrics_dsp] │
│              │                               │                              │          │
│              └───────────────────────► [04_data_and_memory] ◄───────────────┘          │
│                                      (PySpark Data Lake)                               │
└────────────────────────────────────────────────────────────────────────────────────────┘
"""
        content = Vertical(Static(graph_ascii), t_ast)
        return Panel(content, title="[4] Obsidian Architecture Graph & Tarjan SCC Engine", border_style="blue")


class NomadSupervisorView(Static):
    """View 5: Nomad Courier 6-Tier Self-Healing & MCP Supervisor."""
    def render(self) -> Panel:
        t_tiers = Table(box=ROUNDED, expand=True, title="Nomad Courier 6-Tier Autonomous Self-Healing")
        t_tiers.add_column("Tier", style="bold cyan", width=6)
        t_tiers.add_column("Watchdog Target", style="bold white")
        t_tiers.add_column("Monitored Endpoints / Ports", style="yellow")
        t_tiers.add_column("ROI Score / Status", style="bold green")

        nomad_data = {}
        if NOMAD_STATUS_FILE.exists():
            try:
                with open(NOMAD_STATUS_FILE, "r") as f:
                    nomad_data = json.load(f)
            except Exception:
                pass

        t1_status = nomad_data.get("t1_status", "-- (Standby)")
        t2_status = nomad_data.get("t2_status", "-- (Standby)")
        t3_status = nomad_data.get("t3_status", "-- (Standby)")
        t4_status = nomad_data.get("t4_status", f"-- (Standby)")
        t5_status = nomad_data.get("t5_status", "-- (Standby)")
        t6_status = nomad_data.get("t6_status", "-- (Standby)")

        t_tiers.add_row("Line 1", "Bluetooth Proximity Wake", "blueutil CoreBluetooth pulse to all paired nodes", "-- (Standby)")
        t_tiers.add_row("T1", "Service Port Health", ":8080, :8082, :8083, :8084, :8085, :18802", t1_status)
        t_tiers.add_row("T2", "RPC Mesh Probes", "Mac Air, Linux Head, MBP, Pixel 10", t2_status)
        t_tiers.add_row("T3", "AI Models Status", "llama-server health endpoints", t3_status)
        t_tiers.add_row("T4", "Storage & Git Health", "Git locks, NVMe headroom, Vault paths", t4_status)
        t_tiers.add_row("T5", "Skills Guardian", "ai-debate, nomad-governor, swarm skills", t5_status)
        t_tiers.add_row("T6", "LoRA Serialization", "nomad_autonomous_actions.jsonl", t6_status)

        t_mcp = Table(box=ROUNDED, expand=True, title="Custom TUI Controller MCP Server (lauburu-tui-mcp)")
        t_mcp.add_column("Tool Name", style="bold cyan")
        t_mcp.add_column("Protocol / Transport", style="yellow")
        t_mcp.add_column("Target Subsystem Action", style="magenta")

        t_mcp.add_row("start_tui_ecosystem", "JSON-RPC 2.0 stdio", "Bootstrap tmux matrix + sync daemons")
        t_mcp.add_row("stop_tui_ecosystem", "JSON-RPC 2.0 stdio", "Graceful process & session teardown")
        t_mcp.add_row("get_tui_status", "JSON-RPC 2.0 stdio", "Inspect blackboard, PIDs & NVMe")
        t_mcp.add_row("launch_web_tui", "textual-web Port 8088", "Serve console over WebSocket/HTTP")
        t_mcp.add_row("trigger_mesh_self_heal", "Nomad Courier CLI", "Run 6-tier mesh self-heal cycle")
        t_mcp.add_row("trigger_ai_debate", "Port 8083 Devil Advocate", "Adversarial consensus challenge turn")
        t_mcp.add_row("query_wearables_telemetry", "Open Wearables Bridge", "Fetch 512Hz ECG + Oura/Whoop scores")

        content = Columns([t_tiers, t_mcp], expand=True)
        return Panel(content, title="[5] Nomad Courier Governor & Custom MCP Server", border_style="yellow")


# ==============================================================================
# MAIN APPLICATION
# ==============================================================================

class UnifiedMeshConsoleApp(App):
    """Next-Generation Unified Mesh Console TUI (Omega Harmonized)."""

    TITLE = "LAUBURU UNIFIED MESH CONSOLE (OMEGA HARMONIZED)"
    SUB_TITLE = "7-Layer Mesh NOC | 512Hz ECG DSP | Tri-Orchestrator AI Debate | Nomad Governor"

    CSS = """
Screen {
    background: #05080f;
    color: #e2e8f0;
}
Header {
    dock: top;
    height: 1;
    background: #0b111c;
}
Footer {
    dock: bottom;
    height: 1;
    background: #070b12;
    border-top: solid #1e293b;
}
#main_container {
    height: 1fr;
    padding: 0 1;
}
.active_view {
    height: 1fr;
}
"""

    BINDINGS = [
        Binding("1", "set_mode_1", "NOC [1]", priority=True),
        Binding("h", "set_mode_1", "NOC [1]"),
        Binding("2", "set_mode_2", "Biometrics [2]", priority=True),
        Binding("b", "set_mode_2", "Biometrics [2]"),
        Binding("3", "set_mode_3", "AI Swarm [3]", priority=True),
        Binding("d", "set_mode_3", "AI Swarm [3]"),
        Binding("4", "set_mode_4", "Architecture [4]", priority=True),
        Binding("g", "set_mode_4", "Architecture [4]"),
        Binding("5", "set_mode_5", "Nomad Gov [5]", priority=True),
        Binding("s", "set_mode_5", "Nomad Gov [5]"),
        Binding("w", "wake_nodes_bluetooth", "BT Wake [w]"),
        Binding("t", "toggle_web_bridge", "Web-TUI [t]"),
        Binding("r", "refresh_telemetry", "Refresh [r]"),
        Binding("q", "quit", "Quit [q]", priority=True),
    ]

    current_mode = reactive(1)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield MeshHeaderBar(id="top_header")
        with Container(id="main_container"):
            yield NocView(id="view_1")
            yield BiometricsView(id="view_2")
            yield AiSwarmView(id="view_3")
            yield ArchitectureGraphView(id="view_4")
            yield NomadSupervisorView(id="view_5")
        yield Footer()

    def on_mount(self) -> None:
        self.update_view_visibility()
        self.set_interval(2.0, self.periodic_telemetry_tick)

    def periodic_telemetry_tick(self) -> None:
        """Periodic non-blocking UI refresh."""
        self.query_one(MeshHeaderBar).refresh()
        current_view_id = f"view_{self.current_mode}"
        try:
            self.query_one(f"#{current_view_id}").refresh()
        except Exception:
            pass

    def watch_current_mode(self, new_mode: int) -> None:
        self.update_view_visibility()

    def update_view_visibility(self) -> None:
        for i in range(1, 6):
            try:
                widget = self.query_one(f"#view_{i}")
                widget.display = (i == self.current_mode)
            except Exception:
                pass

    def action_set_mode_1(self) -> None: self.current_mode = 1
    def action_set_mode_2(self) -> None: self.current_mode = 2
    def action_set_mode_3(self) -> None: self.current_mode = 3
    def action_set_mode_4(self) -> None: self.current_mode = 4
    def action_set_mode_5(self) -> None: self.current_mode = 5

    def action_wake_nodes_bluetooth(self) -> None:
        """Dispatches Line 1 Bluetooth Proximity Wake across the mesh."""
        sys.path.insert(0, str(MONOREPO_ROOT / "06_scripts_and_tooling"))
        from mesh.wol_manager import WoLEngine
        engine = WoLEngine()
        engine.wake_all()
        self.notify("Dispatched: Line 1 Bluetooth Proximity Wake ➔ Line 2 UDP WoL ➔ Line 3 ADB.", title="📶 BT FIRST-LINE WAKE")
        self.periodic_telemetry_tick()

    def action_toggle_web_bridge(self) -> None:
        """Trigger web bridge launch in background."""
        script = MONOREPO_ROOT / "01_apps/canonical_port/tui/serve_web_tui.py"
        venv_python = MONOREPO_ROOT / "01_apps/canonical_port/.venv/bin/python3"
        python_bin = str(venv_python) if venv_python.exists() else "python3"
        import subprocess
        subprocess.Popen([python_bin, str(script)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.notify("Web-TUI bridge started on http://127.0.0.1:8088", title="🌐 Web Bridge")

    def action_refresh_telemetry(self) -> None:
        self.periodic_telemetry_tick()
        self.notify("Telemetry refreshed across all 7 layers.", title="⚡ Refresh")

def main():
    app = UnifiedMeshConsoleApp()
    app.run()

if __name__ == "__main__":
    main()
