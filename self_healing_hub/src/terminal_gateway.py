#!/usr/bin/env python3
"""
Termius-Style Unified Terminal PTY Gateway & Whole-Network Swarm REPL
Provides an asynchronous WebSocket bridge for both:
1. Whole-Network Unified Multiplexed Swarm Terminal (Swarm REPL across all nodes)
2. Individual interactive PTY/SSH sessions for local and remote nodes.
"""

import os
import pty
import fcntl
import termios
import struct
import select
import asyncio
import json
import logging
import signal
import sys
import websockets
from swarm_shell_engine import SwarmShellSession

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TerminalGateway")

PORT = 5002
HOST = "0.0.0.0"
ADMIN_BOOTSTRAP_TOKEN = "mGe5qpmFqnVWbnf1v1y72hWOv0JnQBjoTjo_229F400"

HOST_INVENTORY = {
    "whole_network": {
        "id": "whole_network",
        "name": "Whole-Network Swarm REPL (All Nodes)",
        "type": "swarm_repl",
        "os": "Multiplexed Cluster",
        "command": ["swarm_repl"],
        "icon": "🌐",
        "ip": "All 6 Nodes Parallel",
        "port": 0,
        "default_user": "swarm"
    },
    "local_mac": {
        "id": "local_mac",
        "name": "Primary Mac (Local Host)",
        "type": "local",
        "os": "macOS M4",
        "command": ["/bin/zsh", "-l"],
        "icon": "🍎",
        "ip": "127.0.0.1",
        "port": 0,
        "default_user": "aaronmaher"
    },
    "linux_head_node": {
        "id": "linux_head_node",
        "name": "Linux Head Node (Ryzen 7 Hub)",
        "type": "ssh",
        "os": "Linux Ubuntu",
        "command": ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=15", "-o", "ConnectTimeout=5", "linux@192.168.8.224"],
        "fallback_command": ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=15", "-o", "ConnectTimeout=5", "linux@100.101.39.98"],
        "icon": "🐧",
        "ip": "192.168.8.224 (Tailscale: 100.101.39.98)",
        "port": 22,
        "default_user": "linux"
    },
    "gl_router": {
        "id": "gl_router",
        "name": "GL.iNet Wi-Fi 7 Router (OpenWrt)",
        "type": "ssh",
        "os": "OpenWrt Linux",
        "command": ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=15", "-o", "ConnectTimeout=5", "root@192.168.8.1"],
        "icon": "📡",
        "ip": "192.168.8.1",
        "port": 22,
        "default_user": "root"
    },
    "headless_mac": {
        "id": "headless_mac",
        "name": "Headless Mac (Metal GPU & Model Server)",
        "type": "ssh",
        "os": "macOS Intel / Metal",
        "command": ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=15", "-o", "ConnectTimeout=5", "aaronmaher@100.103.212.21"],
        "fallback_command": ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=15", "-o", "ConnectTimeout=5", "aaronmaher@169.254.187.138"],
        "icon": "💻",
        "ip": "100.103.212.21 (10Gbps TB4: 169.254.187.138)",
        "port": 22,
        "default_user": "aaronmaher"
    },
    "pixel_10": {
        "id": "pixel_10",
        "name": "Pixel 10 Pro XL (Termux Node)",
        "type": "ssh",
        "os": "Android Termux",
        "command": ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=15", "-o", "ConnectTimeout=5", "-p", "8022", "100.73.38.87"],
        "icon": "📱",
        "ip": "100.73.38.87:8022",
        "port": 8022,
        "default_user": "u0_a123"
    },
    "samsung_s20": {
        "id": "samsung_s20",
        "name": "Samsung Galaxy S20+ (ADB / Termux)",
        "type": "adb_ssh",
        "os": "Android S20+",
        "command": ["ssh", "-o", "StrictHostKeyChecking=no", "root@192.168.8.1", "adb -s R3CN40CJJ1R shell"],
        "fallback_command": ["ssh", "-o", "StrictHostKeyChecking=no", "-p", "8022", "100.84.40.95"],
        "icon": "📲",
        "ip": "Router USB Bus (R3CN40CJJ1R)",
        "port": 0,
        "default_user": "shell"
    },
    "sandboxed_shell": {
        "id": "sandboxed_shell",
        "name": "Sandboxed Practice Shell (Shadow Coding)",
        "type": "local",
        "os": "macOS Isolated Scratch",
        "command": ["/bin/zsh", "-l"],
        "cwd": "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/scratch/sandbox",
        "icon": "🧪",
        "ip": "127.0.0.1 (Sandbox)",
        "port": 0,
        "default_user": "sandbox"
    }
}

active_sessions = {}

def set_terminal_size(fd, rows, cols):
    """Sets PTY window dimensions."""
    try:
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
    except Exception as e:
        logger.warning(f"Failed to set terminal size: {e}")

async def handle_swarm_repl(websocket, cols, rows):
    """Handles interactive Whole-Network Swarm REPL session."""
    session = SwarmShellSession(websocket, cols, rows)
    await session.print_banner()

    line_buffer = ""
    history_idx = -1

    try:
        async for message in websocket:
            if not isinstance(message, str):
                continue

            # Handle JSON control messages (e.g. resize, broadcast)
            if message.startswith("{") and message.endswith("}"):
                try:
                    msg_obj = json.loads(message)
                    if msg_obj.get("type") == "resize":
                        session.rows = int(msg_obj.get("rows", rows))
                        session.cols = int(msg_obj.get("cols", cols))
                        continue
                    elif msg_obj.get("type") == "ping":
                        await websocket.send(json.dumps({"type": "pong"}))
                        continue
                except Exception:
                    pass

            # Parse keystrokes
            for ch in message:
                # Enter / Return
                if ch in ("\r", "\n"):
                    await websocket.send("\r\n")
                    cmd_to_run = line_buffer
                    line_buffer = ""
                    history_idx = -1
                    await session.handle_command(cmd_to_run)

                # Backspace / Delete
                elif ch in ("\x7f", "\x08"):
                    if len(line_buffer) > 0:
                        line_buffer = line_buffer[:-1]
                        await websocket.send("\b \b")

                # Ctrl + C (Interrupt)
                elif ch == "\x03":
                    await websocket.send("^C\r\n")
                    line_buffer = ""
                    history_idx = -1
                    await session.print_prompt()

                # Ctrl + L (Clear screen)
                elif ch == "\x0c":
                    await websocket.send("\x1b[2J\x1b[H")
                    await session.print_prompt()
                    await websocket.send(line_buffer)

                # Regular printable character
                elif ord(ch) >= 32:
                    line_buffer += ch
                    await websocket.send(ch)

    except websockets.exceptions.ConnectionClosed:
        logger.info("Swarm REPL client disconnected.")
    except Exception as e:
        logger.warning(f"Swarm REPL error: {e}")

async def terminal_handler(websocket):
    """Handles an individual WebSocket terminal connection."""
    client_ip = websocket.remote_address[0] if websocket.remote_address else "unknown"
    path = websocket.request.path if hasattr(websocket, "request") and hasattr(websocket.request, "path") else "/ws/term"
    logger.info(f"🔌 New terminal client connected from {client_ip} on path {path}")

    node_id = "whole_network"
    token = ""
    cols = 120
    rows = 35

    if "?" in path:
        query_part = path.split("?")[1]
        for param in query_part.split("&"):
            if "=" in param:
                k, v = param.split("=", 1)
                if k == "node":
                    node_id = v
                elif k == "token":
                    token = v
                elif k == "cols":
                    cols = int(v) if v.isdigit() else 120
                elif k == "rows":
                    rows = int(v) if v.isdigit() else 35

    # If Whole-Network REPL requested
    if node_id in ("whole_network", "swarm_repl"):
        logger.info("🌟 Initializing Whole-Network Swarm REPL session")
        await handle_swarm_repl(websocket, cols, rows)
        return

    # Individual Node PTY Host lookup
    host_profile = HOST_INVENTORY.get(node_id, HOST_INVENTORY["local_mac"])
    cmd = host_profile["command"]

    logger.info(f"🚀 Spawning PTY session for node '{node_id}' ({host_profile['name']}): {' '.join(cmd)}")

    # Fork PTY
    pid, master_fd = pty.fork()
    if pid == 0:
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["COLORTERM"] = "truecolor"
        env["LANG"] = "en_US.UTF-8"
        if host_profile.get("cwd"):
            try:
                os.makedirs(host_profile["cwd"], exist_ok=True)
                os.chdir(host_profile["cwd"])
            except Exception:
                pass
        try:
            os.execvpe(cmd[0], cmd, env)
        except Exception as e:
            sys.stderr.write(f"Failed to execute {cmd}: {e}\n")
            sys.exit(1)
    
    # Parent process
    set_terminal_size(master_fd, rows, cols)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, os.O_NONBLOCK)

    session_id = f"{node_id}_{int(asyncio.get_event_loop().time() * 1000)}"
    active_sessions[session_id] = {
        "master_fd": master_fd,
        "pid": pid,
        "node_id": node_id,
        "websocket": websocket
    }

    async def pty_to_ws():
        try:
            while True:
                r, _, _ = select.select([master_fd], [], [], 0.05)
                if master_fd in r:
                    try:
                        data = os.read(master_fd, 4096)
                        if not data:
                            break
                        await websocket.send(data.decode("utf-8", errors="replace"))
                    except (BlockingIOError, InterruptedError):
                        await asyncio.sleep(0.01)
                    except OSError:
                        break
                await asyncio.sleep(0.01)
        except Exception as e:
            logger.debug(f"pty_to_ws ended: {e}")

    async def ws_to_pty():
        try:
            async for message in websocket:
                if isinstance(message, str):
                    if message.startswith("{") and message.endswith("}"):
                        try:
                            msg_obj = json.loads(message)
                            if msg_obj.get("type") == "resize":
                                r = int(msg_obj.get("rows", rows))
                                c = int(msg_obj.get("cols", cols))
                                set_terminal_size(master_fd, r, c)
                                continue
                            elif msg_obj.get("type") == "broadcast":
                                cmd_text = msg_obj.get("command", "")
                                for s_id, sess in list(active_sessions.items()):
                                    try:
                                        os.write(sess["master_fd"], cmd_text.encode("utf-8"))
                                    except Exception:
                                        pass
                                continue
                            elif msg_obj.get("type") == "ping":
                                await websocket.send(json.dumps({"type": "pong"}))
                                continue
                        except Exception:
                            pass
                    os.write(master_fd, message.encode("utf-8"))
                elif isinstance(message, bytes):
                    os.write(master_fd, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Terminal client disconnected from session {session_id}")
        except Exception as e:
            logger.warning(f"ws_to_pty error: {e}")

    try:
        await asyncio.gather(pty_to_ws(), ws_to_pty())
    finally:
        logger.info(f"🧹 Cleaning up PTY session {session_id} (PID {pid})")
        if session_id in active_sessions:
            del active_sessions[session_id]
        try:
            os.close(master_fd)
        except Exception:
            pass
        try:
            os.kill(pid, signal.SIGTERM)
            os.waitpid(pid, os.WNOHANG)
        except Exception:
            pass

TERMIUS_WEB_TERMINAL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Termius PTY Terminal Gateway — Lauburu Master Terminal</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/css/xterm.min.css" />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-primary: #070a13;
      --bg-surface: #0f172a;
      --bg-card: #1e293b;
      --accent-cyan: #38bdf8;
      --accent-green: #34d399;
      --text-main: #f8fafc;
      --text-subtle: #94a3b8;
      --border-color: #334155;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg-primary);
      color: var(--text-main);
      font-family: 'Inter', sans-serif;
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    header {
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border-color);
      padding: 10px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 15px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .brand-icon { font-size: 20px; }
    .brand-title { font-weight: 700; font-size: 15px; letter-spacing: 0.5px; }
    .status-badge {
      background: rgba(52, 211, 153, 0.15);
      color: var(--accent-green);
      padding: 3px 10px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 600;
      border: 1px solid rgba(52, 211, 153, 0.3);
    }
    .tabs-bar {
      display: flex;
      gap: 6px;
      overflow-x: auto;
      padding: 4px;
      background: rgba(0,0,0,0.3);
      border-radius: 8px;
      border: 1px solid var(--border-color);
    }
    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-subtle);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
      white-space: nowrap;
    }
    .tab-btn:hover {
      background: rgba(255,255,255,0.06);
      color: var(--text-main);
    }
    .tab-btn.active {
      background: var(--accent-cyan);
      color: #070a13;
    }
    #terminal-container {
      flex: 1;
      padding: 12px;
      background: #020617;
      position: relative;
    }
    .xterm { height: 100%; }
    .xterm-viewport { overflow-y: auto !important; }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <span class="brand-icon">⚡</span>
      <div>
        <div class="brand-title">TERMIUS PTY GATEWAY</div>
        <div style="font-size: 11px; color: var(--text-subtle);">Direct Device Shells • Master Source of Truth</div>
      </div>
    </div>
    
    <div class="tabs-bar" id="tabs-bar">
      <button class="tab-btn active" onclick="switchHost('local_mac')">🍎 Mac Host</button>
      <button class="tab-btn" onclick="switchHost('linux_head_node')">🐧 Linux Node</button>
      <button class="tab-btn" onclick="switchHost('gl_router')">📡 GL.iNet Router</button>
      <button class="tab-btn" onclick="switchHost('headless_mac')">💻 Worker Mac</button>
      <button class="tab-btn" onclick="switchHost('pixel_10')">📱 Pixel 10 Termux</button>
      <button class="tab-btn" onclick="switchHost('samsung_s20')">📲 Samsung S20 ADB</button>
      <button class="tab-btn" onclick="switchHost('sandboxed_shell')">🧪 Sandbox Shell</button>
      <button class="tab-btn" onclick="switchHost('whole_network')">🌐 Swarm REPL</button>
    </div>

    <div style="display: flex; align-items: center; gap: 10px;">
      <span class="status-badge" id="conn-badge">CONNECTING...</span>
    </div>
  </header>

  <div id="terminal-container"></div>

  <script src="https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/lib/xterm.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@xterm/addon-fit@0.8.0/lib/addon-fit.min.js"></script>
  <script>
    let term, fitAddon, ws;
    let currentHost = 'local_mac';
    const container = document.getElementById('terminal-container');
    const badge = document.getElementById('conn-badge');

    function initTerminal() {
      term = new Terminal({
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 13,
        lineHeight: 1.25,
        theme: {
          background: '#020617',
          foreground: '#f8fafc',
          cursor: '#38bdf8',
          selectionBackground: 'rgba(56, 189, 248, 0.3)',
          black: '#0f172a',
          red: '#ef4444',
          green: '#34d399',
          yellow: '#fbbf24',
          blue: '#38bdf8',
          magenta: '#c084fc',
          cyan: '#22d3ee',
          white: '#f8fafc'
        }
      });
      fitAddon = new FitAddon.FitAddon();
      term.loadAddon(fitAddon);
      term.open(container);
      fitAddon.fit();

      window.addEventListener('resize', () => {
        if (fitAddon) {
          fitAddon.fit();
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
          }
        }
      });

      term.onData(data => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(data);
        }
      });

      connectSocket(currentHost);
    }

    function connectSocket(hostId) {
      if (ws) {
        ws.close();
      }
      term.reset();
      badge.innerText = 'CONNECTING...';
      badge.style.color = '#fbbf24';

      const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${proto}//${location.host}/?host=${hostId}&cols=${term.cols}&rows=${term.rows}&token=mGe5qpmFqnVWbnf1v1y72hWOv0JnQBjoTjo_229F400`;
      
      ws = new WebSocket(wsUrl);
      ws.binaryType = 'arraybuffer';

      ws.onopen = () => {
        badge.innerText = `ONLINE: ${hostId.toUpperCase()}`;
        badge.style.color = '#34d399';
        ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
      };

      ws.onmessage = (evt) => {
        if (typeof evt.data === 'string') {
          term.write(evt.data);
        } else {
          term.write(new Uint8Array(evt.data));
        }
      };

      ws.onclose = () => {
        badge.innerText = 'DISCONNECTED';
        badge.style.color = '#ef4444';
      };

      ws.onerror = () => {
        badge.innerText = 'ERROR';
        badge.style.color = '#ef4444';
      };
    }

    function switchHost(hostId) {
      currentHost = hostId;
      document.querySelectorAll('.tab-btn').forEach(b => {
        b.classList.toggle('active', b.getAttribute('onclick').includes(hostId));
      });
      connectSocket(hostId);
    }

    window.addEventListener('DOMContentLoaded', initTerminal);
  </script>
</body>
</html>
"""

from http import HTTPStatus

def process_http_request(connection, request):
    """Intercepts plain HTTP GET requests and serves the full Termius Web Terminal UI."""
    if request.headers.get("Upgrade", "").lower() != "websocket":
        return connection.respond(HTTPStatus.OK, TERMIUS_WEB_TERMINAL_HTML)
    return None

async def main():
    logger.info(f"🌟 Starting Termius-Style Terminal PTY Gateway & Swarm REPL on ws://{HOST}:{PORT}")
    async with websockets.serve(terminal_handler, HOST, PORT, process_request=process_http_request, ping_interval=20, ping_timeout=20):
        await asyncio.Future()

if __name__ == "__main__":
    if "--test" in sys.argv:
        print("✅ Terminal gateway & Swarm REPL syntax verified!")
        print(f"📦 Preconfigured Hosts: {list(HOST_INVENTORY.keys())}")
        sys.exit(0)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Terminal gateway stopped.")

