#!/usr/bin/env python3
"""
==============================================================================
Standalone Launcher for Screen 5: AI Benchmarking & Distributed Sharding Console
==============================================================================
Subsystem: 01_apps/canonical_port/tui/prototypes/launch_sharding_and_ai_benchmark_ui.py
Lauburu Mesh Ecosystem — 2026

Direct entrypoint into:
1. llama.cpp Distributed GGML-RPC Tensor Sharding Matrix (10Gbps TB4 DMA)
2. prima.cpp PRP Ring & Halda ILP Latency Benchmarks
3. Master AGI Active Inference Model Roster & TTFT/TPOT throughput
4. Canonical AI Arena Overall & Domain Bradley-Terry ELO Leaderboards
5. Petals DHT Swarm (:31337) & Exo P2P (:52415) Dynamic Topologies
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
from views.ai_inference_view import AiInferenceView

class StandaloneShardingAndBenchmarkApp(App):
    CSS = """
    Screen {
        background: #070b12;
        color: #e2e8f0;
    }
    """
    TITLE = "⚡ LAUBURU AI & SHARDING BENCHMARKING CONSOLE"

    def on_mount(self) -> None:
        self.push_view(AiInferenceView())

if __name__ == "__main__":
    app = StandaloneShardingAndBenchmarkApp()
    app.run()
