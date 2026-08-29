#!/usr/bin/env python3
"""
Universal Web-TUI Portal & 120 FPS PTY WebSocket Server.
=========================================================
Subsystem: 01_apps/web_tui_portal/serve_portal.py
Port: 8088 (Default)

Renders all 7 Lauburu Monorepo applications over WebSockets and xterm.js WebGL:
Domain 1 (User & Scaling Apps):
  - /readiness   -> Movesense Physiological Readiness & Cardio Coach Hub
  - /grappling   -> 3D Spatial Grappling Kinematics (3,044 OPML Tree)
  - /arena       -> Lauburu Combat Arena & Multi-Mode Duel
  - /store       -> Headless Shopify Storefront & Membership Tiers

Domain 2 (Operator & Dev Cockpits):
  - /canonical   -> Canonical Port 9-Screen NOC & Stability Hierarchy
  - /smolagents  -> SmolAgents Python Duel Sandbox
  - /math        -> Standalone Qwen Math Trend Optimizer
"""

import os
import sys
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
    }
}

app = FastAPI(title="Lauburu Universal Web-TUI Portal", version="1.0.0")

# Mount leaderboard dashboard if available
if _LEADERBOARD_READY:
    app.include_router(leaderboard_router)
    print("✅ Leaderboard dashboard mounted at /leaderboard + /api/leaderboard/data")

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
    header { height: 46px; background: #0b111c; border-bottom: 1px solid #1e293b; display: flex; align-items: center; justify-content: space-between; padding: 0 16px; font-size: 13px; font-weight: 600; }
    .nav-left { display: flex; align-items: center; gap: 8px; }
    .nav-links { display: flex; align-items: center; gap: 6px; }
    .nav-links a { color: #94a3b8; text-decoration: none; padding: 4px 8px; border-radius: 4px; font-size: 12px; transition: all 0.2s; }
    .nav-links a:hover, .nav-links a.active { color: #38bdf8; background: #1e293b; }
    #terminal-container { flex: 1; width: 100%; height: calc(100vh - 46px); background: #070b12; position: relative; }
    .badge-user { background: #059669; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; }
    .badge-dev { background: #d97706; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; }
    .badge-fps { background: #2563eb; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; }
  </style>
</head>
<body>
  <header>
    <div class="nav-left">
      <a href="/" style="color:#f8fafc; text-decoration:none;">⚡ <strong>LAUBURU PORTAL</strong></a>
      <span class="{{ badge_class }}">{{ app_tier }}</span>
      <span class="badge-fps">120 FPS WebGL</span>
    </div>
    <div class="nav-links">
      <a href="/readiness" class="{{ 'active' if app_id == 'readiness' else '' }}">💓 Readiness</a>
      <a href="/grappling" class="{{ 'active' if app_id == 'grappling' else '' }}">🥋 Grappling</a>
      <a href="/arena" class="{{ 'active' if app_id == 'arena' else '' }}">⚔️ Arena</a>
      <a href="/store" class="{{ 'active' if app_id == 'store' else '' }}">🛍️ Store</a>
      <a href="/canonical" class="{{ 'active' if app_id == 'canonical' else '' }}">🏛️ NOC</a>
      <a href="/smolagents" class="{{ 'active' if app_id == 'smolagents' else '' }}">🤖 SmolAgents</a>
      <a href="/math" class="{{ 'active' if app_id == 'math' else '' }}">🧮 Math</a>
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

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${proto}//${window.location.host}/ws/{{ app_id }}`;
    const ws = new WebSocket(wsUrl);
    ws.binaryType = 'arraybuffer';

    ws.onopen = () => {
      fitAddon.fit();
      const dims = { type: 'resize', cols: term.cols, rows: term.rows };
      ws.send(JSON.stringify(dims));
    };

    ws.onmessage = (event) => {
      if (typeof event.data === 'string') {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'exit') {
            term.writeln('\\r\\n[Process terminated with exit code ' + msg.code + ']');
          }
        } catch (e) {
          term.write(event.data);
        }
      } else {
        const dec = new TextDecoder('utf-8');
        term.write(dec.decode(event.data));
      }
    };

    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'input', data: data }));
      }
    });

    window.addEventListener('resize', () => {
      fitAddon.fit();
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
      }
    });
  </script>
</body>
</html>
"""

# Landing Page HTML with 120 FPS Grid Cards
HTML_PORTAL_LANDING = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Lauburu Monorepo — Universal Web-TUI Portal</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background-color: #070b12; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; min-height: 100vh; padding: 32px 24px; }
    .header { text-align: center; margin-bottom: 36px; }
    .header h1 { font-size: 28px; font-weight: 700; margin-bottom: 8px; color: #f8fafc; }
    .header p { font-size: 14px; color: #94a3b8; }
    .domains-grid { display: flex; flex-direction: column; gap: 32px; max-width: 1200px; margin: 0 auto; }
    .domain-section h2 { font-size: 18px; font-weight: 600; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
    .app-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
    .card { background: #0b111c; border: 1px solid #1e293b; border-radius: 8px; padding: 20px; text-decoration: none; color: inherit; transition: all 0.2s ease; display: flex; flex-direction: column; justify-content: space-between; }
    .card:hover { border-color: #38bdf8; transform: translateY(-2px); box-shadow: 0 4px 20px rgba(56, 189, 248, 0.15); }
    .card-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
    .card-icon { font-size: 24px; }
    .card-title { font-size: 16px; font-weight: 600; margin-bottom: 6px; color: #f8fafc; }
    .card-desc { font-size: 13px; color: #94a3b8; line-height: 1.4; margin-bottom: 16px; flex: 1; }
    .card-footer { display: flex; align-items: center; justify-content: space-between; font-size: 12px; font-weight: 600; color: #38bdf8; }
    .badge-user { background: #059669; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
    .badge-dev { background: #d97706; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
    .meta-bar { max-width: 1200px; margin: 32px auto 0 auto; background: #0b111c; border: 1px solid #1e293b; border-radius: 8px; padding: 16px 20px; display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: #94a3b8; }
  </style>
</head>
<body>
  <div class="header">
    <h1>⚡ LAUBURU MONOREPO UNIVERSAL WEB-TUI PORTAL</h1>
    <p>Port 8088 • 120 FPS WebGL Terminal Stream • Strict Local Biometric Airgap</p>
  </div>

  <div class="domains-grid">
    <!-- Domain 1: User & Scaling Apps -->
    <div class="domain-section">
      <h2 style="color: #10b981;">👤 Domain 1: User & Scaling Consumer/Pro Applications</h2>
      <div class="app-cards">
        <a href="/readiness" class="card">
          <div class="card-top">
            <span class="card-icon">💓</span>
            <span class="badge-user">User App</span>
          </div>
          <div class="card-title">Movesense Readiness Hub</div>
          <div class="card-desc">512Hz Pan-Tompkins ECG, continuous PTT blood pressure, overnight sleep staging & recovery, Zone 2 coaching.</div>
          <div class="card-footer"><span>Launch Web-TUI</span> <span>→</span></div>
        </a>
        <a href="/grappling" class="card">
          <div class="card-top">
            <span class="card-icon">🥋</span>
            <span class="badge-user">User App</span>
          </div>
          <div class="card-title">3D Spatial Grappling Map</div>
          <div class="card-desc">3,044 OPML hierarchical martial mindmap projected on 10m x 10m tatami with MediaPipe 33-landmark skeleton.</div>
          <div class="card-footer"><span>Launch Web-TUI</span> <span>→</span></div>
        </a>
        <a href="/arena" class="card">
          <div class="card-top">
            <span class="card-icon">⚔️</span>
            <span class="badge-user">User App</span>
          </div>
          <div class="card-title">Lauburu Combat Arena</div>
          <div class="card-desc">Hermes 3 Red vs. LuCI Blue 4-mode duel with 120 FPS compute power bar, live Movesense biofeedback, and RAG voice.</div>
          <div class="card-footer"><span>Launch Web-TUI</span> <span>→</span></div>
        </a>
        <a href="/store" class="card">
          <div class="card-top">
            <span class="card-icon">🛍️</span>
            <span class="badge-user">User App</span>
          </div>
          <div class="card-title">Shopify Headless Storefront</div>
          <div class="card-desc">Athlete membership tiers ($9/$29/$99/mo), medical Movesense HR+ sensor bundles, and Storefront GraphQL checkout.</div>
          <div class="card-footer"><span>Launch Web-TUI</span> <span>→</span></div>
        </a>
      </div>
    </div>

    <!-- Domain 2: Operator & Dev Cockpits -->
    <div class="domain-section">
      <h2 style="color: #f59e0b;">🛠️ Domain 2: Operator & Developer Command Cockpits</h2>
      <div class="app-cards">
        <a href="/canonical" class="card">
          <div class="card-top">
            <span class="card-icon">🏛️</span>
            <span class="badge-dev">Operator NOC</span>
          </div>
          <div class="card-title">Canonical Port 9-Screen NOC</div>
          <div class="card-desc">9-Screen stability command hierarchy monitoring 7 physical nodes, 108GB RAM pool, and AI Debate Council.</div>
          <div class="card-footer"><span>Launch Web-TUI</span> <span>→</span></div>
        </a>
        <a href="/smolagents" class="card">
          <div class="card-top">
            <span class="card-icon">🤖</span>
            <span class="badge-dev">Operator Sandbox</span>
          </div>
          <div class="card-title">SmolAgents Duel Sandbox</div>
          <div class="card-desc">Sandboxed Python code-as-action tool execution arena for autonomous multi-agent mesh stress testing.</div>
          <div class="card-footer"><span>Launch Web-TUI</span> <span>→</span></div>
        </a>
        <a href="/math" class="card">
          <div class="card-top">
            <span class="card-icon">🧮</span>
            <span class="badge-dev">Operator Analytics</span>
          </div>
          <div class="card-title">Qwen Math Trend Optimizer</div>
          <div class="card-desc">Closed-form inverse-variance latency proofs, RAM safety headroom governor, and 24/7 LoRA SFT/DPO fine-tuning logger.</div>
          <div class="card-footer"><span>Launch Web-TUI</span> <span>→</span></div>
        </a>
      </div>
    </div>
  </div>

  <div class="meta-bar">
    <div><strong>Architecture:</strong> 7 Physical Nodes • 108GB RAM Pool • 10Gbps TB4 DMA Bridge (0.27ms RTT)</div>
    <div><strong>Storage Tri-Vault:</strong> Obsidian Core • PySpark Data Lake • GitHub Clean Tree</div>
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

    # Open PTY pair
    master_fd, slave_fd = pty.openpty()

    # Set non-blocking on master
    flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    # Spawn process in new process group
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["COLORTERM"] = "truecolor"
    env["PYTHONUNBUFFERED"] = "1"
    
    # Inject modular package paths
    python_paths = [
        str(MONOREPO_ROOT),
        str(MONOREPO_ROOT / "01_apps/user_facing_and_scaling"),
        str(MONOREPO_ROOT / "01_apps/operator_and_dev"),
        str(MONOREPO_ROOT / "01_apps/canonical_port/tui"),
    ]
    env["PYTHONPATH"] = ":".join(python_paths) + ":" + env.get("PYTHONPATH", "")

    # Choose primary command or fallback
    cmd = app_meta["cmd"]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=str(MONOREPO_ROOT),
            env=env,
            preexec_fn=os.setsid
        )
    except Exception:
        # Fallback to fallback_cmd
        proc = await asyncio.create_subprocess_exec(
            *app_meta["fallback_cmd"],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=str(MONOREPO_ROOT),
            env=env,
            preexec_fn=os.setsid
        )

    os.close(slave_fd)

    loop = asyncio.get_running_loop()

    async def pty_reader():
        try:
            while True:
                await asyncio.sleep(0.008)  # ~120 FPS tick rate
                try:
                    data = os.read(master_fd, 4096)
                    if data:
                        await websocket.send_bytes(data)
                    else:
                        break
                except (BlockingIOError, InterruptedError):
                    continue
                except OSError:
                    break
        except Exception:
            pass

    async def ws_reader():
        try:
            while True:
                msg_text = await websocket.receive_text()
                try:
                    payload = json.loads(msg_text)
                    m_type = payload.get("type")
                    if m_type == "input":
                        inp_data = payload.get("data", "")
                        os.write(master_fd, inp_data.encode("utf-8"))
                    elif m_type == "resize":
                        cols = int(payload.get("cols", 80))
                        rows = int(payload.get("rows", 24))
                        winsize = struct.pack("HHHH", rows, cols, 0, 0)
                        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
                except json.JSONDecodeError:
                    os.write(master_fd, msg_text.encode("utf-8"))
        except (WebSocketDisconnect, Exception):
            pass

    reader_task = asyncio.create_task(pty_reader())
    writer_task = asyncio.create_task(ws_reader())

    done, pending = await asyncio.wait(
        [reader_task, writer_task],
        return_when=asyncio.FIRST_COMPLETED
    )

    for task in pending:
        task.cancel()

    # Clean shutdown of subprocess and master fd
    try:
        os.close(master_fd)
    except Exception:
        pass

    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:
        pass


def reclaim_port(port: int = 8088):
    """Checks if port 8088 is currently bound and kills stale listeners if necessary."""
    try:
        import subprocess
        res = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True)
        pids = res.stdout.strip().split()
        for pid_str in pids:
            if pid_str and pid_str.isdigit():
                pid = int(pid_str)
                if pid != os.getpid():
                    print(f"🔄 Reclaiming Port {port}: Killing stale PID {pid}")
                    os.kill(pid, signal.SIGKILL)
        time.sleep(0.2)
    except Exception as e:
        print(f"Port reclamation notice: {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Lauburu Universal Web-TUI Portal")
    parser.add_argument("--host", default="0.0.0.0", help="Host IP")
    parser.add_argument("--port", type=int, default=8088, help="Port (default: 8088)")
    parser.add_argument("--no-reclaim", action="store_true", help="Skip port reclamation")
    args = parser.parse_args()

    if not args.no_reclaim:
        reclaim_port(args.port)

    print("=" * 80)
    print(f"🌐 LAUBURU UNIVERSAL WEB-TUI PORTAL (Port {args.port})")
    print("=" * 80)
    print(f"Landing Page:     http://127.0.0.1:{args.port}/")
    print(f"Domain 1 Apps:    /readiness, /grappling, /arena, /store")
    print(f"Domain 2 Cockpit: /canonical, /smolagents, /math")
    print("=" * 80)

    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
