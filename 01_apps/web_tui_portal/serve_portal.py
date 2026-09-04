#!/usr/bin/env python3
"""
================================================================================
Lauburu Universal Web-TUI Portal & Command Center (Port 8088)
================================================================================
Subsystem: 01_apps/web_tui_portal/serve_portal.py
Version: 3.0.0-UNIFIED-PORTAL-ECOSYSTEM
Lauburu Mesh Ecosystem — 2026

Comprehensive Navigation & 120 FPS WebGL Terminal Stream:
- 🏆 Master AI Leaderboard & Swarm Radar (/leaderboard)
- 👤 Domain 1: User & Scaling Consumer/Pro Applications
- 🛠️ Domain 2: Operator & Developer Command Cockpits
- 🧠 Domain 3: World Models, Autonomous Simulation & Swarms
- 🏛️ Domain 4: Tri-Vault Storage, MCP Hub & Mesh Infrastructure
================================================================================
"""

import os
import sys
import subprocess
import pty
import fcntl
import termios
import struct
import asyncio
import json
import time
import socket
import signal
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

# ── Leaderboard & Project MCP dashboard router ────────────────────────────────
try:
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).parent))
    from leaderboard_dashboard import router as leaderboard_router
    _LEADERBOARD_READY = True
except Exception as _e:
    _LEADERBOARD_READY = False
    print(f"⚠️  Leaderboard router not loaded: {_e}")

MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")

# Canonical Application Registry
REGISTERED_APPS: Dict[str, Dict[str, Any]] = {
    # 👤 User & Scaling Apps
    "readiness": {
        "id": "readiness",
        "name": "💓 Movesense Readiness & Cardio Coach",
        "title": "Movesense Hub",
        "cmd": ["python3", "-m", "movesense_readiness_hub.presentation.tui"],
        "fallback_cmd": ["python3", str(MONOREPO_ROOT / "01_apps/biometrics/movesense_readiness_tui.py")],
        "tier": "User & Scaling",
        "badge_class": "badge-user",
        "description": "512Hz Bicep ECG (Pan-Tompkins DSP), PTT continuous blood pressure, overnight sleep staging, Zone 2 coaching.",
        "icon": "💓"
    },
    "grappling": {
        "id": "grappling",
        "name": "🥋 3D Spatial Grappling Kinematics",
        "title": "3D Grappling Map",
        "cmd": ["python3", "-m", "spatial_grappling_3d.presentation.tui"],
        "fallback_cmd": ["python3", str(MONOREPO_ROOT / "00_core_infrastructure/self_healing_hub/src/spatial_grappling_map_engine.py")],
        "tier": "User & Scaling",
        "badge_class": "badge-user",
        "description": "3,044 OPML martial mindmap tree mapped to 10m x 10m tatami grid with MediaPipe 33-skeleton & joint torque.",
        "icon": "🥋"
    },
    "arena": {
        "id": "arena",
        "name": "⚔️ Lauburu Combat Arena",
        "title": "Combat Arena",
        "cmd": ["python3", "-m", "combat_arena.presentation.arena"],
        "fallback_cmd": ["python3", str(MONOREPO_ROOT / "01_apps/canonical_port/tui/tui_live_arena_dev.py")],
        "tier": "User & Scaling",
        "badge_class": "badge-user",
        "description": "Hermes 3 Red vs. LuCI Blue multi-mode duel with 120 FPS compute power bar, live Movesense pulse, and RAG voice.",
        "icon": "⚔️"
    },
    "store": {
        "id": "store",
        "name": "🛍️ Headless Storefront & Memberships",
        "title": "Shopify Storefront",
        "cmd": ["python3", "-m", "shopify_storefront.presentation.store"],
        "fallback_cmd": ["python3", str(MONOREPO_ROOT / "01_apps/commerce_and_business/storefront_membership_tui.py")],
        "tier": "User & Scaling",
        "badge_class": "badge-user",
        "description": "Athlete membership subscriptions ($9/$29/$99/mo), Movesense HR+ medical sensor bundles, and Storefront GraphQL.",
        "icon": "🛍️"
    },
    # 🛠️ Operator & Dev Cockpits
    "canonical": {
        "id": "canonical",
        "name": "🏛️ Canonical Port 9-Screen NOC",
        "title": "Canonical NOC",
        "cmd": ["python3", "-m", "canonical_port.views.dashboard"],
        "fallback_cmd": ["python3", str(MONOREPO_ROOT / "01_apps/canonical_port/tui/canonical_tui.py")],
        "tier": "Operator & Dev",
        "badge_class": "badge-dev",
        "description": "9-Screen stability command hierarchy monitoring 7 physical nodes, 108GB RAM pool, AI debate, and Tri-Vault core.",
        "icon": "🏛️"
    },
    "smolagents": {
        "id": "smolagents",
        "name": "🤖 SmolAgents Python Duel Sandbox",
        "title": "SmolAgents Sandbox",
        "cmd": ["python3", "-m", "smolagents_duel_sandbox.presentation.sandbox"],
        "fallback_cmd": ["python3", str(MONOREPO_ROOT / "05_agents_and_swarms/red_blue_arena/smolagents_arena_engine.py")],
        "tier": "Operator & Dev",
        "badge_class": "badge-dev",
        "description": "Autonomous Python code-as-action tool registry and execution arena for Red & Blue dueling AI agents.",
        "icon": "🤖"
    },
    "math": {
        "id": "math",
        "name": "🧮 Qwen Math Trend Optimizer",
        "title": "Math Optimizer",
        "cmd": ["python3", "-m", "qwen_math_trend_optimizer.presentation.optimizer"],
        "fallback_cmd": ["python3", str(MONOREPO_ROOT / "02_ai_models_and_inference/quantum/autonomous_math_trend_optimizer.py")],
        "tier": "Operator & Dev",
        "badge_class": "badge-dev",
        "description": "Decoupled mathematical governor calculating closed-form latency proofs, RAM safety headroom, and 24/7 LoRA SFT/DPO logging.",
        "icon": "🧮"
    },
    "training": {
        "id": "training",
        "name": "🦀 Rust Swarm Live Training TUI (--dev)",
        "title": "Rust Training TUI",
        "cmd": [str(MONOREPO_ROOT / "01_apps/rust_swarm_training_tui/target/debug/rust_swarm_training_tui"), "--dev"],
        "fallback_cmd": [str(MONOREPO_ROOT / "01_apps/rust_swarm_training_tui/target/debug/rust_swarm_training_tui"), "--dev"],
        "tier": "Operator & Dev",
        "badge_class": "badge-dev",
        "description": "Sub-millisecond Rust Ratatui 120 FPS live dashboard streaming real-time SWE-bench diffs, MCTS lookaheads, and LoRA pairs.",
        "icon": "🦀"
    }
}

app = FastAPI(title="Lauburu Universal Web-TUI Portal", version="3.0.0")

if _LEADERBOARD_READY:
    app.include_router(leaderboard_router)

# HTML Template with xterm.js WebGL & 120 FPS Rendering
HTML_TERMINAL_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Lauburu — {{ app_name }}</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css" />
  <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/xterm-addon-webgl@0.16.0/lib/xterm-addon-webgl.js"></script>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background-color: #070b12; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; overflow: hidden; height: 100vh; display: flex; flex-direction: column; }
    header { height: 48px; background: #0b111c; border-bottom: 1px solid #1e293b; display: flex; align-items: center; justify-content: space-between; padding: 0 16px; font-size: 13px; font-weight: 600; }
    .nav-left { display: flex; align-items: center; gap: 10px; }
    .nav-links { display: flex; align-items: center; gap: 6px; }
    .nav-links a { color: #94a3b8; text-decoration: none; padding: 5px 10px; border-radius: 4px; font-size: 12px; transition: all 0.2s; font-weight: 600; }
    .nav-links a:hover, .nav-links a.active { color: #38bdf8; background: #1e293b; }
    #terminal-container { flex: 1; width: 100%; height: calc(100vh - 48px); background: #070b12; position: relative; }
    .badge-user { background: #059669; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; }
    .badge-dev { background: #d97706; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; }
    .badge-fps { background: #2563eb; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; }
  </style>
</head>
<body>
  <header>
    <div class="nav-left">
      <a href="/" style="color:#f8fafc; text-decoration:none;">⚡ <strong>LAUBURU HUB</strong></a>
      <span class="{{ badge_class }}">{{ app_tier }}</span>
      <span class="badge-fps">120 FPS WebGL</span>
    </div>
    <div class="nav-links">
      <a href="/leaderboard" style="color:#f59e0b; background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3);">🏆 Leaderboard</a>
      <a href="/readiness" class="{{ 'active' if app_id == 'readiness' else '' }}">💓 Readiness</a>
      <a href="/grappling" class="{{ 'active' if app_id == 'grappling' else '' }}">🥋 Grappling</a>
      <a href="/arena" class="{{ 'active' if app_id == 'arena' else '' }}">⚔️ Arena</a>
      <a href="/store" class="{{ 'active' if app_id == 'store' else '' }}">🛍️ Store</a>
      <a href="/canonical" class="{{ 'active' if app_id == 'canonical' else '' }}">🏛️ NOC</a>
      <a href="/smolagents" class="{{ 'active' if app_id == 'smolagents' else '' }}">🤖 SmolAgents</a>
      <a href="/math" class="{{ 'active' if app_id == 'math' else '' }}">🧮 Math</a>
      <a href="http://100.93.158.96:8889/lab" target="_blank" style="color:#38bdf8; font-weight:bold;">📓 Notebook</a>
    </div>
  </header>
  <div id="terminal-container"></div>
  <script>
    const term = new Terminal({
      cursorBlink: true,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      fontSize: 14,
      lineHeight: 1.15,
      letterSpacing: 0,
      theme: {
        background: '#070b12',
        foreground: '#f8fafc',
        cursor: '#38bdf8',
        selectionBackground: 'rgba(56, 189, 248, 0.3)',
        black: '#0f172a',
        red: '#ef4444',
        green: '#10b981',
        yellow: '#f59e0b',
        blue: '#3b82f6',
        magenta: '#d946ef',
        cyan: '#06b6d4',
        white: '#f8fafc',
      }
    });

    const fitAddon = new FitAddon.FitAddon();
    term.loadAddon(fitAddon);

    const termContainer = document.getElementById('terminal-container');
    term.open(termContainer);

    try {
      const webglAddon = new WebglAddon.WebglAddon();
      term.loadAddon(webglAddon);
    } catch (e) {
      console.warn("WebGL renderer fallback to canvas", e);
    }

    fitAddon.fit();
    window.addEventListener('resize', () => fitAddon.fit());

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/{{ app_id }}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      term.write("\\r\\n\\x1b[32m⚡ Connected to {{ app_name }} (120 FPS PTY Stream)\\x1b[0m\\r\\n\\r\\n");
      const dims = { cols: term.cols, rows: term.rows };
      ws.send(JSON.stringify({ type: 'resize', ...dims }));
    };

    ws.onmessage = (event) => term.write(event.data);
    term.onData((data) => ws.readyState === WebSocket.OPEN && ws.send(JSON.stringify({ type: 'input', data })));
    ws.onclose = () => term.write("\\r\\n\\x1b[31m⚠️ Connection closed.\\x1b[0m\\r\\n");
  </script>
</body>
</html>
"""

HTML_PORTAL_LANDING = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Lauburu Monorepo — Universal Web-TUI Portal & Ecosystem Directory</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background-color: #070b12; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; min-height: 100vh; padding: 28px 20px; }
    .header { text-align: center; margin-bottom: 28px; }
    .header h1 { font-size: 26px; font-weight: 700; margin-bottom: 6px; color: #f8fafc; letter-spacing: -0.5px; }
    .header p { font-size: 13px; color: #94a3b8; }
    
    .domains-grid { display: flex; flex-direction: column; gap: 28px; max-width: 1280px; margin: 0 auto; }
    .domain-section h2 { font-size: 16px; font-weight: 700; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
    
    .app-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 16px; }
    .card { background: #0b111c; border: 1px solid #1e293b; border-radius: 10px; padding: 18px; text-decoration: none; color: inherit; transition: all 0.2s ease; display: flex; flex-direction: column; justify-content: space-between; }
    .card:hover { border-color: #38bdf8; transform: translateY(-2px); box-shadow: 0 6px 24px rgba(56, 189, 248, 0.15); }
    .card-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
    .card-icon { font-size: 22px; }
    .card-title { font-size: 15px; font-weight: 700; margin-bottom: 6px; color: #f8fafc; }
    .card-desc { font-size: 12.5px; color: #94a3b8; line-height: 1.45; margin-bottom: 14px; flex: 1; }
    .card-footer { display: flex; align-items: center; justify-content: space-between; font-size: 11.5px; font-weight: 700; color: #38bdf8; }
    
    /* Custom Badges */
    .badge-hero { background: #f59e0b; color: #000; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; }
    .badge-user { background: #059669; color: white; padding: 2px 7px; border-radius: 4px; font-size: 10.5px; font-weight: 600; }
    .badge-dev { background: #d97706; color: white; padding: 2px 7px; border-radius: 4px; font-size: 10.5px; font-weight: 600; }
    .badge-sim { background: #7c3aed; color: white; padding: 2px 7px; border-radius: 4px; font-size: 10.5px; font-weight: 600; }
    .badge-infra { background: #2563eb; color: white; padding: 2px 7px; border-radius: 4px; font-size: 10.5px; font-weight: 600; }

    .hero-banner { background: linear-gradient(135deg, rgba(245, 158, 11, 0.18), rgba(56, 189, 248, 0.12)); border: 1px solid rgba(245, 158, 11, 0.5); border-radius: 12px; padding: 22px; display: flex; align-items: center; justify-content: space-between; gap: 20px; }
    .hero-btn { background: #f59e0b; color: #000; font-weight: 700; font-size: 13.5px; padding: 12px 22px; border-radius: 6px; text-decoration: none; white-space: nowrap; display: inline-flex; align-items: center; gap: 8px; transition: transform 0.2s; }
    .hero-btn:hover { transform: scale(1.03); }

    .meta-bar { max-width: 1280px; margin: 32px auto 0 auto; background: #0b111c; border: 1px solid #1e293b; border-radius: 8px; padding: 14px 18px; display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: #94a3b8; }
  </style>
</head>
<body>
  <div class="header">
    <h1>⚡ LAUBURU MONOREPO UNIVERSAL WEB-TUI PORTAL</h1>
    <p>Port 8088 • 120 FPS WebGL Terminal Stream • 7-Layer Mesh Topology • 82.8 GB Pooled VRAM</p>
  </div>

  <div class="domains-grid">
    <!-- 🏆 HERO: Master AI Leaderboard & Radar -->
    <div class="hero-banner">
      <div>
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
          <span style="font-size: 22px;">🏆</span>
          <span class="badge-hero">CANONICAL SWE-BENCH & ELO RADAR</span>
          <span style="color: #38bdf8; font-size: 12px; font-weight: 600;">27 Quantized Models • 82.8 GB Pooled VRAM</span>
        </div>
        <h2 style="font-size: 19px; font-weight: 700; color: #f8fafc; margin-bottom: 4px;">Lauburu AI Model Leaderboard & Adaptive Swarm Radar</h2>
        <p style="font-size: 12.5px; color: #94a3b8;">Real-time ELO rankings, Empirical ROI scores ($/token), dynamic RAM sharding across 10Gbps TB4 DMA, and HuggingFace GGUF model procurement.</p>
      </div>
      <a href="/leaderboard" class="hero-btn">Open AI Leaderboard →</a>
    </div>

    <!-- Domain 1: 👤 User & Scaling Apps -->
    <div class="domain-section">
      <h2 style="color: #10b981;">👤 Domain 1: User & Scaling Consumer / Athlete Applications</h2>
      <div class="app-cards">
        <a href="/readiness" class="card">
          <div class="card-top"><span class="card-icon">💓</span><span class="badge-user">User App</span></div>
          <div class="card-title">Movesense Readiness Hub</div>
          <div class="card-desc">512Hz Pan-Tompkins ECG, continuous PTT blood pressure, overnight sleep staging & recovery, Zone 2 coaching.</div>
          <div class="card-footer"><span>Launch Web-TUI</span> <span>→</span></div>
        </a>
        <a href="/grappling" class="card">
          <div class="card-top"><span class="card-icon">🥋</span><span class="badge-user">User App</span></div>
          <div class="card-title">3D Spatial Grappling Map</div>
          <div class="card-desc">3,044 OPML hierarchical martial mindmap projected on 10m x 10m tatami with MediaPipe 33-landmark skeleton.</div>
          <div class="card-footer"><span>Launch Web-TUI</span> <span>→</span></div>
        </a>
        <a href="/arena" class="card">
          <div class="card-top"><span class="card-icon">⚔️</span><span class="badge-user">User App</span></div>
          <div class="card-title">Lauburu Combat Arena</div>
          <div class="card-desc">Hermes 3 Red vs. LuCI Blue 4-mode duel with 120 FPS compute power bar, live Movesense biofeedback, and RAG voice.</div>
          <div class="card-footer"><span>Launch Web-TUI</span> <span>→</span></div>
        </a>
        <a href="/store" class="card">
          <div class="card-top"><span class="card-icon">🛍️</span><span class="badge-user">User App</span></div>
          <div class="card-title">Shopify Headless Storefront</div>
          <div class="card-desc">Athlete membership tiers ($9/$29/$99/mo), medical Movesense HR+ sensor bundles, and Storefront GraphQL checkout.</div>
          <div class="card-footer"><span>Launch Web-TUI</span> <span>→</span></div>
        </a>
      </div>
    </div>

    <!-- Domain 2: 🛠️ Operator & Dev Cockpits -->
    <div class="domain-section">
      <h2 style="color: #f59e0b;">🛠️ Domain 2: Operator & Developer Command Cockpits</h2>
      <div class="app-cards">
        <a href="/canonical" class="card">
          <div class="card-top"><span class="card-icon">🏛️</span><span class="badge-dev">Operator NOC</span></div>
          <div class="card-title">Canonical Port 9-Screen NOC</div>
          <div class="card-desc">9-Screen stability command hierarchy monitoring 7 physical nodes, 108GB RAM pool, and AI Debate Council.</div>
          <div class="card-footer"><span>Launch Web-TUI</span> <span>→</span></div>
        </a>
        <a href="/smolagents" class="card">
          <div class="card-top"><span class="card-icon">🤖</span><span class="badge-dev">Operator Sandbox</span></div>
          <div class="card-title">SmolAgents Duel Sandbox</div>
          <div class="card-desc">Sandboxed Python code-as-action tool execution arena for autonomous multi-agent mesh stress testing.</div>
          <div class="card-footer"><span>Launch Web-TUI</span> <span>→</span></div>
        </a>
        <a href="/math" class="card">
          <div class="card-top"><span class="card-icon">🧮</span><span class="badge-dev">Operator Analytics</span></div>
          <div class="card-title">Qwen Math Trend Optimizer</div>
          <div class="card-desc">Closed-form inverse-variance latency proofs, RAM safety headroom governor, and 24/7 LoRA SFT/DPO fine-tuning logger.</div>
          <div class="card-footer"><span>Launch Web-TUI</span> <span>→</span></div>
        </a>
        <a href="/training" class="card" style="border-color: rgba(245,158,11,0.4); background: linear-gradient(180deg, rgba(245,158,11,0.06), rgba(16,23,38,0.8));">
          <div class="card-top"><span class="card-icon">🦀</span><span class="badge-dev" style="background: rgba(245,158,11,0.2); color:#f59e0b; border-color:#f59e0b;">Live 120 FPS TUI</span></div>
          <div class="card-title" style="color: #f59e0b;">Rust Swarm Live Training TUI</div>
          <div class="card-desc">Sub-millisecond Rust Ratatui 120 FPS dashboard streaming SWE-bench diffs, MCTS lookaheads, and continuous LoRA pairs live.</div>
          <div class="card-footer"><span style="color:#f59e0b;">Launch Live TUI</span> <span style="color:#f59e0b;">→</span></div>
        </a>
      </div>
    </div>

    <!-- Domain 3: 🧠 World Models, Autonomous Simulation & Swarms -->
    <div class="domain-section">
      <h2 style="color: #a855f7;">🧠 Domain 3: World Models, Autonomous Simulation & Swarms</h2>
      <div class="app-cards">
        <div class="card" style="border-color: #a855f7;">
          <div class="card-top"><span class="card-icon">🌐</span><span class="badge-sim">World Model</span></div>
          <div class="card-title">Qwen-AgentWorld-35B OS Simulator</div>
          <div class="card-desc">7-Domain in-memory simulation (Terminal, MCP tools, SWE diffs, Android ADB, OS syscalls) with 30-step MCTS lookahead at 0ms latency.</div>
          <div class="card-footer"><span style="color: #a855f7;">Port 8086 Active</span> <span>● ONLINE</span></div>
        </div>
        <div class="card" style="border-color: #a855f7;">
          <div class="card-top"><span class="card-icon">✈️</span><span class="badge-sim">World Model</span></div>
          <div class="card-title">WebWorld-32B / 8B Flight Simulator</div>
          <div class="card-desc">Deep browser flight simulator evaluating DOM accessibility trees, CSS bounding boxes, and Shopify storefronts without external network lag.</div>
          <div class="card-footer"><span style="color: #a855f7;">Port 8092 Active</span> <span>● ONLINE</span></div>
        </div>
        <div class="card" style="border-color: #a855f7;">
          <div class="card-top"><span class="card-icon">⚔️</span><span class="badge-sim">Consensus Swarm</span></div>
          <div class="card-title">Tri-Orchestrator AI Debate Arena</div>
          <div class="card-desc">Structured 3-way consensus engine (Local Orchestrator, Devil's Advocate, Cloud Oracle) locking code changes to >0.98 agreement.</div>
          <div class="card-footer"><span style="color: #a855f7;">Swarm Protocol</span> <span>● VERIFIED</span></div>
        </div>
      </div>
    </div>

    <!-- Domain 4: 🛡️ Infrastructure, Sentinel & Tri-Vault Storage -->
    <div class="domain-section">
      <h2 style="color: #3b82f6;">🛡️ Domain 4: Infrastructure, Sentinel & Tri-Vault Storage</h2>
      <div class="app-cards">
        <div class="card" style="border-color: #3b82f6;">
          <div class="card-top"><span class="card-icon">🛡️</span><span class="badge-infra">Network Guard</span></div>
          <div class="card-title">Router 512MB Network Sentinel</div>
          <div class="card-desc">Autonomous network health governor keeping memory under 28MB RAM on OpenWrt routers with automatic ARP cache healing.</div>
          <div class="card-footer"><span style="color: #3b82f6;">28 MB RAM Safe</span> <span>● HEALTHY</span></div>
        </div>
        <div class="card" style="border-color: #3b82f6;">
          <div class="card-top"><span class="card-icon">🔌</span><span class="badge-infra">MCP Gateway</span></div>
          <div class="card-title">Master MCP Server & Gemini Spark Bridge</div>
          <div class="card-desc">Live Model Context Protocol SSE server on Port 9999 exposing 6 local tools and 82.8 GB pooled VRAM to external AI clients.</div>
          <div class="card-footer"><span style="color: #3b82f6;">Port 9999 / HTTPS</span> <span>● CONNECTED</span></div>
        </div>
        <div class="card" style="border-color: #3b82f6;">
          <div class="card-top"><span class="card-icon">☁️</span><span class="badge-infra">Credit Governor</span></div>
          <div class="card-title">Google Cloud Credit Governor ($1,400 Pool)</div>
          <div class="card-desc">Dynamic FLOPs gating with strict $10.00 AUD micro-spend tranches, 50% Vertex AI batch discounts, and self-destructing Spot GPUs.</div>
          <div class="card-footer"><span style="color: #3b82f6;">$1,400 AUD Reserve</span> <span>● 100% INTACT</span></div>
        </div>
      </div>
    </div>
  </div>

  <div class="meta-bar">
    <div><strong>7-Layer Physical Mesh:</strong> Mac Mini M4 Pro • MacBook Pro (TB4 DMA 0.204ms) • Linux Head Node • Debian Tablet • MacBook Air M4 • Pixel TPU • Samsung S20+ • GL.iNet Router</div>
    <div><strong>Storage Tri-Vault:</strong> Obsidian Core • PySpark Data Lake (435K+ LOC) • GitHub Clean Tree</div>
  </div>
</body>
</html>
"""

def render_app_page(app_id: str) -> str:
    app_info = REGISTERED_APPS.get(app_id)
    if not app_info:
        return HTML_PORTAL_LANDING
    return HTML_TERMINAL_PAGE \
        .replace("{{ app_name }}", app_info["name"]) \
        .replace("{{ app_id }}", app_id) \
        .replace("{{ app_tier }}", app_info["tier"]) \
        .replace("{{ badge_class }}", app_info["badge_class"])

@app.get("/", response_class=HTMLResponse)
async def get_index():
    return HTMLResponse(content=HTML_PORTAL_LANDING)

@app.get("/readiness", response_class=HTMLResponse)
async def get_readiness():
    return HTMLResponse(content=render_app_page("readiness"))

@app.get("/grappling", response_class=HTMLResponse)
async def get_grappling():
    return HTMLResponse(content=render_app_page("grappling"))

@app.get("/arena", response_class=HTMLResponse)
async def get_arena():
    return HTMLResponse(content=render_app_page("arena"))

@app.get("/store", response_class=HTMLResponse)
async def get_store():
    return HTMLResponse(content=render_app_page("store"))

@app.get("/canonical", response_class=HTMLResponse)
async def get_canonical():
    return HTMLResponse(content=render_app_page("canonical"))

@app.get("/smolagents", response_class=HTMLResponse)
async def get_smolagents():
    return HTMLResponse(content=render_app_page("smolagents"))

@app.get("/math", response_class=HTMLResponse)
async def get_math():
    return HTMLResponse(content=render_app_page("math"))

@app.get("/training", response_class=HTMLResponse)
async def get_training():
    return HTMLResponse(content=render_app_page("training"))

@app.get("/api/status")
@app.get("/api/apps")
async def get_api_status():
    return {
        "status": "HEALTHY",
        "port": 8088,
        "fps": 120,
        "total_apps": len(REGISTERED_APPS),
        "apps": REGISTERED_APPS,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "airgap_certified": True
    }

@app.websocket("/ws/{app_id}")
async def websocket_terminal(websocket: WebSocket, app_id: str):
    if app_id not in REGISTERED_APPS:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    app_meta = REGISTERED_APPS[app_id]

    master_fd, slave_fd = pty.openpty()
    flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    # Set default 120x35 terminal size for Ratatui
    winsize = struct.pack("HHHH", 35, 120, 0, 0)
    try:
        fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
    except Exception:
        pass

    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["COLORTERM"] = "truecolor"

    cmd = app_meta.get("fallback_cmd") or app_meta.get("cmd")
    proc = subprocess.Popen(
        cmd,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
        cwd=str(MONOREPO_ROOT),
        env=env
    )
    os.close(slave_fd)

    async def pty_reader():
        loop = asyncio.get_event_loop()
        while proc.poll() is None:
            try:
                data = await loop.run_in_executor(None, lambda: os.read(master_fd, 4096))
                if data:
                    await websocket.send_text(data.decode("utf-8", errors="replace"))
                else:
                    await asyncio.sleep(0.01)
            except (BlockingIOError, OSError):
                await asyncio.sleep(0.01)

    async def ws_reader():
        try:
            while proc.poll() is None:
                msg = await websocket.receive_text()
                try:
                    payload = json.loads(msg)
                    if payload.get("type") == "input":
                        os.write(master_fd, payload.get("data", "").encode("utf-8"))
                    elif payload.get("type") == "resize":
                        cols = int(payload.get("cols", 80))
                        rows = int(payload.get("rows", 24))
                        winsize = struct.pack("HHHH", rows, cols, 0, 0)
                        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
                except json.JSONDecodeError:
                    os.write(master_fd, msg.encode("utf-8"))
        except WebSocketDisconnect:
            pass

    reader_task = asyncio.create_task(pty_reader())
    writer_task = asyncio.create_task(ws_reader())
    done, pending = await asyncio.wait([reader_task, writer_task], return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()

    try:
        proc.terminate()
        os.close(master_fd)
    except Exception:
        pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8088, log_level="info")
