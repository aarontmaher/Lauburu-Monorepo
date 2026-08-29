#!/usr/bin/env python3
"""
Lauburu Canonical Web-TUI Server (textual-web & WebSocket PTY Engine)
====================================================================
Subsystem: 01_apps/canonical_port/tui/serve_web_tui.py
Version: 5.0.0-SEPARATION

Separates apps into two clear domains:
1. USER & SCALING APPS: Movesense Readiness, 3D Spatial Grappling, Consumer Arena, Storefront.
2. OPERATOR & DEV APPS: Canonical Port 9-Screen NOC, SmolAgents Python Sandbox, Qwen Math Optimizer.

Serves 100% authentic Textual apps over WebSockets & xterm.js at 120 FPS on http://0.0.0.0:8088.
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
from pathlib import Path
from aiohttp import web, WSMsgType

MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
TUI_DIR = MONOREPO_ROOT / "01_apps/canonical_port/tui"

APP_ROUTER = {
    # 👤 User & Scaled Athlete Apps
    "readiness": {
        "name": "💓 Movesense Readiness & Cardio Coach",
        "cmd": ["python3", str(MONOREPO_ROOT / "01_apps/biometrics/movesense_readiness_tui.py")],
        "tier": "user"
    },
    "grappling": {
        "name": "🥋 3D Spatial Grappling (3,044 OPML Tree)",
        "cmd": ["python3", str(MONOREPO_ROOT / "00_core_infrastructure/self_healing_hub/src/spatial_grappling_map_engine.py")],
        "tier": "user"
    },
    "arena": {
        "name": "⚔️ Lauburu Combat Arena & Swarm Game",
        "cmd": ["python3", str(TUI_DIR / "tui_live_arena_dev.py")],
        "tier": "user"
    },
    "store": {
        "name": "🛍️ Headless Storefront & Membership Tiers",
        "cmd": ["python3", str(MONOREPO_ROOT / "01_apps/commerce_and_business/storefront_membership_tui.py")],
        "tier": "user"
    },
    # 🛠️ Developer & Operator Command Cockpits
    "canonical": {
        "name": "🏛️ Canonical Port 9-Screen Command Center",
        "cmd": ["python3", str(TUI_DIR / "canonical_tui.py")],
        "tier": "operator"
    },
    "smolagents": {
        "name": "🤖 SmolAgents Python Duel Sandbox",
        "cmd": ["python3", str(MONOREPO_ROOT / "05_agents_and_swarms/red_blue_arena/smolagents_arena_engine.py")],
        "tier": "operator"
    },
    "math": {
        "name": "🧮 Standalone Qwen Math Trend Optimizer",
        "cmd": ["python3", str(MONOREPO_ROOT / "02_ai_models_and_inference/quantum/autonomous_math_trend_optimizer.py")],
        "tier": "operator"
    }
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Lauburu — __APP_NAME__</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css" />
  <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/xterm-addon-webgl@0.16.0/lib/xterm-addon-webgl.js"></script>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background-color: #070b12; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; overflow: hidden; height: 100vh; display: flex; flex-direction: column; }
    header { height: 44px; background: #0b111c; border-bottom: 1px solid #1e293b; display: flex; align-items: center; justify-content: space-between; padding: 0 16px; font-size: 13px; font-weight: 600; }
    .nav-links a { color: #94a3b8; text-decoration: none; margin-left: 10px; padding: 4px 8px; border-radius: 4px; font-size: 12px; transition: all 0.2s; }
    .nav-links a:hover, .nav-links a.active { color: #38bdf8; background: #1e293b; }
    #terminal-container { flex: 1; width: 100%; height: calc(100vh - 44px); background: #070b12; position: relative; }
    .badge-user { background: #059669; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; margin-left: 6px; }
    .badge-dev { background: #d97706; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; margin-left: 6px; }
  </style>
</head>
<body>
  <header>
    <div>
      <a href="/" style="color:#f8fafc; text-decoration:none;">⚡ <strong>LAUBURU APPS</strong></a>
      __TIER_BADGE__
    </div>
    <div class="nav-links">
      <a href="/readiness" class="__ACTIVE_READINESS__">💓 Readiness</a>
      <a href="/grappling" class="__ACTIVE_GRAPPLING__">🥋 3D Grappling</a>
      <a href="/arena" class="__ACTIVE_ARENA__">⚔️ Arena</a>
      <a href="/store" class="__ACTIVE_STORE__">🛍️ Store</a>
      <span style="color:#334155; margin:0 4px;">|</span>
      <a href="/canonical" class="__ACTIVE_CANONICAL__">🏛️ Command Center</a>
      <a href="/smolagents" class="__ACTIVE_SMOLAGENTS__">🤖 SmolAgents</a>
    </div>
  </header>
  <div id="terminal-container"></div>

  <script>
    const term = new Terminal({
      cursorBlink: true,
      theme: {
        background: '#070b12',
        foreground: '#f8fafc',
        cursor: '#38bdf8',
        selectionBackground: '#1e3a8a'
      },
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      fontSize: window.innerWidth < 768 ? 11 : 13,
      allowTransparency: true
    });

    const fitAddon = new FitAddon.FitAddon();
    term.loadAddon(fitAddon);
    term.open(document.getElementById('terminal-container'));
    fitAddon.fit();

    try {
      const webglAddon = new WebglAddon.WebglAddon();
      term.loadAddon(webglAddon);
    } catch(e) {}

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ws/__APP_SLUG__`;
    const socket = new WebSocket(wsUrl);

    socket.binaryType = 'arraybuffer';

    socket.onopen = () => {
      term.focus();
      sendResize();
    };

    socket.onmessage = (event) => {
      if (typeof event.data === 'string') {
        term.write(event.data);
      } else {
        const text = new TextDecoder().decode(event.data);
        term.write(text);
      }
    };

    socket.onclose = () => {
      term.write('\\r\\n\\x1b[31m[Session Disconnected. Refresh to Reconnect]\\x1b[0m\\r\\n');
    };

    term.onData((data) => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'input', data: data }));
      }
    });

    function sendResize() {
      fitAddon.fit();
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
      }
    }

    window.addEventListener('resize', sendResize);
    window.setInterval(sendResize, 1500);
  </script>
</body>
</html>
"""

INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Lauburu Unified Application Portal</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #070b12; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 40px 20px; min-height: 100vh; display: flex; justify-content: center; }
    .portal-container { max-width: 1000px; width: 100%; }
    .portal-header { text-align: center; margin-bottom: 36px; }
    .portal-header h1 { color: #38bdf8; font-size: 28px; font-weight: 800; margin-bottom: 8px; }
    .portal-header p { color: #94a3b8; font-size: 15px; }
    .grid-container { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
    @media (max-width: 768px) { .grid-container { grid-template-columns: 1fr; } }
    .section-card { background: #0b111c; border: 1px solid #1e293b; border-radius: 12px; padding: 24px; }
    .section-title { font-size: 17px; font-weight: 700; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; }
    .user-title { color: #34d399; }
    .dev-title { color: #f59e0b; }
    .badge { font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 600; }
    .badge-green { background: #065f46; color: #a7f3d0; }
    .badge-amber { background: #78350f; color: #fde68a; }
    .app-link { display: block; background: #131d2e; border: 1px solid #1e293b; color: #f8fafc; text-decoration: none; padding: 14px 16px; border-radius: 8px; margin-bottom: 12px; transition: all 0.2s; }
    .app-link:hover { background: #1e293b; border-color: #38bdf8; transform: translateY(-1px); }
    .app-name { font-weight: 600; font-size: 14px; display: flex; justify-content: space-between; margin-bottom: 4px; }
    .app-desc { font-size: 12px; color: #94a3b8; line-height: 1.4; }
    .status-dot { height: 8px; width: 8px; background-color: #10b981; border-radius: 50%; display: inline-block; margin-right: 6px; }
  </style>
</head>
<body>
  <div class="portal-container">
    <div class="portal-header">
      <h1>⚡ LAUBURU APPLICATION PORTAL</h1>
      <p>Clean architectural separation between User-Facing Consumer Apps and Operator/Dev Command Cockpits</p>
    </div>

    <div class="grid-container">
      <!-- 👤 User-Facing & Scaling Apps -->
      <div class="section-card">
        <div class="section-title user-title">
          <span>👤 USER & ATHLETE APPS</span>
          <span class="badge badge-green">SCALED CONSUMER</span>
        </div>
        <p style="color:#64748b; font-size:12px; margin-bottom:16px;">Zero-clutter, polished consumer interfaces for athletes, gyms, and subscription members.</p>

        <a href="/readiness" class="app-link">
          <div class="app-name"><span><span class="status-dot"></span>💓 Movesense Physiological Readiness</span> <span style="color:#34d399; font-size:12px;">512Hz ECG</span></div>
          <div class="app-desc">Bicep ECG, continuous PTT blood pressure, overnight sleep score (88/100), and Zone 2 coach.</div>
        </a>

        <a href="/grappling" class="app-link">
          <div class="app-name"><span><span class="status-dot"></span>🥋 3D Spatial Grappling Kinematics</span> <span style="color:#38bdf8; font-size:12px;">3,044 OPML</span></div>
          <div class="app-desc">Interactive 3D tatami world model, Brazilian Jiu-Jitsu mindmap & MediaPipe 33-landmark skeleton.</div>
        </a>

        <a href="/arena" class="app-link">
          <div class="app-name"><span><span class="status-dot"></span>⚔️ Gamified Combat Arena</span> <span style="color:#fbbf24; font-size:12px;">120 FPS</span></div>
          <div class="app-desc">Interactive compute tug-of-war, 4 game modes, live telemetry HUD & spoken TTS coaching.</div>
        </a>

        <a href="/store" class="app-link">
          <div class="app-name"><span><span class="status-dot"></span>🛍️ Storefront & Membership Tiers</span> <span style="color:#c084fc; font-size:12px;">GraphQL</span></div>
          <div class="app-desc">Shopify headless commerce, Athlete ($9), Pro ($29), and Gym Team ($99/mo) subscriptions.</div>
        </a>
      </div>

      <!-- 🛠️ Operator & Developer Cockpits -->
      <div class="section-card">
        <div class="section-title dev-title">
          <span>🛠️ OPERATOR & DEV COCKPITS</span>
          <span class="badge badge-amber">INTERNAL ADMIN</span>
        </div>
        <p style="color:#64748b; font-size:12px; margin-bottom:16px;">Mission-control cockpits for monorepo development, mesh sharding, AI debates, and hardware tuning.</p>

        <a href="/canonical" class="app-link">
          <div class="app-name"><span><span class="status-dot"></span>🏛️ Canonical Port 9-Screen Command Center</span> <span style="color:#f59e0b; font-size:12px;">7 NODES</span></div>
          <div class="app-desc">Master NOC, AGI Terminal, 108GB RAM pool governor, llama.cpp RPC sharding & Big Data Lake.</div>
        </a>

        <a href="/smolagents" class="app-link">
          <div class="app-name"><span><span class="status-dot"></span>🤖 SmolAgents Python Duel Sandbox</span> <span style="color:#f87171; font-size:12px;">CODE EXEC</span></div>
          <div class="app-desc">Faction leaders (Hermes 3 vs LuCI OpenWrt) generating & executing native Python countermeasures.</div>
        </a>

        <a href="/math" class="app-link">
          <div class="app-name"><span><span class="status-dot"></span>🧮 Standalone Qwen Math Trend Optimizer</span> <span style="color:#60a5fa; font-size:12px;">QUANTUM</span></div>
          <div class="app-desc">Autonomous 24/7 background optimizer analyzing mesh latency trends and QAOA routing weights.</div>
        </a>
      </div>
    </div>
  </div>
</body>
</html>
"""

def render_page(app_slug: str) -> str:
    app_info = APP_ROUTER.get(app_slug, {"name": app_slug, "tier": "user"})
    app_name = app_info["name"]
    tier_badge = '<span class="badge-user">USER APP</span>' if app_info["tier"] == "user" else '<span class="badge-dev">OPERATOR COCKPIT</span>'
    
    html = HTML_TEMPLATE.replace("__APP_NAME__", app_name).replace("__APP_SLUG__", app_slug).replace("__TIER_BADGE__", tier_badge)
    for slug in ["readiness", "grappling", "arena", "store", "canonical", "smolagents"]:
        html = html.replace(f"__ACTIVE_{slug.upper()}__", "active" if app_slug == slug else "")
    return html

async def handle_index(request):
    return web.Response(text=INDEX_TEMPLATE, content_type="text/html")

async def handle_app_page(request):
    app_slug = request.match_info.get("app_slug", "readiness")
    if app_slug not in APP_ROUTER:
        raise web.HTTPNotFound()
    return web.Response(text=render_page(app_slug), content_type="text/html")

async def handle_websocket(request):
    app_slug = request.match_info.get("app_slug", "readiness")
    app_info = APP_ROUTER.get(app_slug, APP_ROUTER["readiness"])
    
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    cmd = app_info["cmd"]
    master_fd, slave_fd = pty.openpty()

    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONPATH"] = f"{TUI_DIR}:{MONOREPO_ROOT / '01_apps/canonical_port'}:{MONOREPO_ROOT / '01_apps/biometrics'}:{MONOREPO_ROOT / '01_apps/commerce_and_business'}:{MONOREPO_ROOT / '05_agents_and_swarms/red_blue_arena'}:{MONOREPO_ROOT / '00_core_infrastructure/self_healing_hub/src'}:{env.get('PYTHONPATH', '')}"

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        cwd=str(MONOREPO_ROOT),
        env=env,
        close_fds=True
    )
    os.close(slave_fd)

    flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    loop = asyncio.get_event_loop()

    async def read_from_pty():
        try:
            while proc.returncode is None and not ws.closed:
                data = await loop.run_in_executor(None, lambda: os.read(master_fd, 4096) if master_fd else b"")
                if not data:
                    break
                await ws.send_str(data.decode("utf-8", errors="replace"))
        except Exception:
            pass

    async def read_from_ws():
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        payload = json.loads(msg.data)
                        msg_type = payload.get("type")
                        if msg_type == "input":
                            input_data = payload.get("data", "").encode("utf-8")
                            os.write(master_fd, input_data)
                        elif msg_type == "resize":
                            cols = int(payload.get("cols", 120))
                            rows = int(payload.get("rows", 40))
                            winsize = struct.pack("HHHH", rows, cols, 0, 0)
                            fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
                    except Exception:
                        pass
        except Exception:
            pass

    task_pty = asyncio.create_task(read_from_pty())
    task_ws = asyncio.create_task(read_from_ws())

    done, pending = await asyncio.wait([task_pty, task_ws], return_when=asyncio.FIRST_COMPLETED)
    for p in pending:
        p.cancel()

    try:
        proc.terminate()
        os.close(master_fd)
    except Exception:
        pass

    return ws

def create_app():
    app = web.Application()
    app.router.add_get("/", handle_index)
    for slug in APP_ROUTER.keys():
        app.router.add_get(f"/{slug}", handle_app_page)
    app.router.add_get("/ws/{app_slug}", handle_websocket)
    return app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8088"))
    
    # Auto-reclaim port from stale processes
    try:
        import subprocess
        pids = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True).stdout.strip().split()
        my_pid = str(os.getpid())
        for pid in pids:
            if pid and pid != my_pid:
                try:
                    os.kill(int(pid), 9)
                except Exception:
                    pass
        time.sleep(0.3)
    except Exception:
        pass

    print("=" * 80)
    print(f"🌐 LAUBURU WEB-TUI SERVER RUNNING ON http://0.0.0.0:{port}")
    print(f"   • User & Scaling Apps: http://localhost:{port}/readiness | /grappling | /arena | /store")
    print(f"   • Operator Cockpits:   http://localhost:{port}/canonical | /smolagents | /math")
    print("=" * 80)
    web.run_app(create_app(), host="0.0.0.0", port=port, reuse_address=True, reuse_port=True)
