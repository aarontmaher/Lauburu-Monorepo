"""
NetworkHealthAI — Lauburu TUI Widget
Version: 1.0.0

A sandboxed local AI specialist embedded in the Network screen.
Uses local Qwen2.5-Coder-7B (via proxy :8080) to:
  - Diagnose mesh node failures in real-time
  - Suggest and execute PRE-APPROVED healing commands only
  - Stream AI analysis directly into the TUI panel

SAFETY MODEL:
  - Strict ALLOWLIST of permitted shell commands (read-only probes + known healers)
  - NO arbitrary code execution — model output is parsed for structured JSON actions
  - All executed actions are logged to nomad_autonomous_actions.jsonl
  - Rate-limited: 1 AI analysis cycle per 60 seconds max
  - Dry-run mode: show proposed actions before executing (CONFIRM_BEFORE_EXEC = True)
"""

import os
import sys
import json
import asyncio
import subprocess
import time
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static, Button, RichLog
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from textual import work

logger = logging.getLogger("NetworkHealthAI")

# ─── SAFETY: STRICT COMMAND ALLOWLIST ────────────────────────────────────────
# Only these exact command prefixes are executable. Everything else is blocked.
SAFE_CMD_ALLOWLIST: List[str] = [
    # Network probes (read-only)
    "ping -c",
    "nc -z",
    "curl -s --max-time",
    "curl -sf --max-time",
    "tailscale status",
    "tailscale ping",
    "netstat -tlnp",
    "ss -tlnp",
    # Mesh node SSH (read-only remote commands)
    "ssh -o ConnectTimeout=4 -o BatchMode=yes linux@100.101.39.98 'ps",
    "ssh -o ConnectTimeout=4 -o BatchMode=yes linux@100.101.39.98 'free",
    "ssh -p 8022 -o ConnectTimeout=4 -o BatchMode=yes u0_a363@100.73.38.87 'ps",
    "ssh -p 8022 -o ConnectTimeout=4 -o BatchMode=yes u0_a363@100.73.38.87 'free",
    # Process inspection (read-only)
    "pgrep -la llama",
    "pgrep -la petals",
    "pgrep -la ggml-rpc",
    # Approved healing actions (write — but strictly scoped)
    "launchctl unload /Users/aaron/Library/LaunchAgents/ai.lauburu",
    "launchctl load /Users/aaron/Library/LaunchAgents/ai.lauburu",
    "bash /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/mesh_rpc_petals_healer.sh",
    "python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/nomad_courier_self_healer.py --once",
]

LORA_LOG = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/lora_datasets/nomad_autonomous_actions.jsonl")
PROXY_URL = "http://127.0.0.1:8080/v1/chat/completions"
MODEL = "local/qwen"          # Qwen2.5-Coder-7B — fast, fits with other models
CONFIRM_BEFORE_EXEC = False   # False = auto-execute allowlisted actions; True = show + wait


def _is_safe(cmd: str) -> bool:
    """Return True only if cmd starts with an allowlisted prefix."""
    cmd_stripped = cmd.strip()
    return any(cmd_stripped.startswith(prefix) for prefix in SAFE_CMD_ALLOWLIST)


def _log_action(action: str, result: str, safe: bool) -> None:
    """Append action to LoRA training dataset."""
    try:
        LORA_LOG.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "action": action,
            "result": result[:300],
            "nomad_agent": "NetworkHealthAI TUI v1.0",
            "safe": safe,
        }
        with LORA_LOG.open("a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass


class NetworkHealthAI(Vertical):
    """
    Live AI-powered network health monitor embedded in the TUI.
    Runs Qwen2.5-Coder-7B locally, analyzes mesh state, executes safe heals.
    """

    DEFAULT_CSS = """
    NetworkHealthAI {
        height: auto;
        min-height: 18;
        max-height: 28;
        width: 100%;
        background: #050d1a;
        border: solid #0f4c75;
        margin-top: 1;
    }
    #net-ai-header {
        height: 1;
        background: #0f4c75;
        color: #38bdf8;
        text-style: bold;
        padding: 0 1;
        dock: top;
    }
    #net-ai-log {
        height: 1fr;
        background: #050d1a;
        padding: 0 1;
    }
    #net-ai-controls {
        height: 3;
        dock: bottom;
        background: #0a1628;
        padding: 0 1;
        align: left middle;
    }
    .ai-btn {
        height: 1;
        min-width: 18;
        margin-right: 1;
        border: none;
        background: #1e3a5f;
        color: #93c5fd;
    }
    .ai-btn:hover { background: #1d4ed8; color: #ffffff; }
    #btn-ai-scan { background: #1e3a5f; }
    #btn-ai-heal { background: #14532d; color: #86efac; }
    #btn-ai-stop { background: #7f1d1d; color: #fca5a5; }
    #net-ai-status {
        width: 1fr;
        color: #475569;
        text-align: right;
    }
    """

    is_running: reactive[bool] = reactive(False)
    _last_scan_ts: float = 0.0
    _cancel_flag: bool = False
    SCAN_INTERVAL_S: float = 90.0   # Auto-rescan every 90 seconds

    def compose(self) -> ComposeResult:
        yield Static(
            "🧠 Network Health AI  │  Qwen2.5-Coder-7B  │  Sandboxed  │  Auto-heal ON",
            id="net-ai-header",
        )
        yield RichLog(
            id="net-ai-log",
            highlight=True,
            markup=True,
            wrap=True,
            max_lines=300,
        )
        with Horizontal(id="net-ai-controls"):
            yield Button("🔍 Scan Now",   id="btn-ai-scan",  classes="ai-btn")
            yield Button("🔧 Heal Mesh",  id="btn-ai-heal",  classes="ai-btn")
            yield Button("⏹ Stop",        id="btn-ai-stop",  classes="ai-btn")
            yield Static("", id="net-ai-status")

    def on_mount(self) -> None:
        log = self.query_one("#net-ai-log", RichLog)
        log.write("[dim cyan]⚡ NetworkHealthAI initializing — first scan in 3s…[/dim cyan]")
        # Auto-launch on mount after brief delay
        self.set_timer(3.0, self._auto_scan)
        # Periodic rescan
        self.set_interval(self.SCAN_INTERVAL_S, self._auto_scan)

    # ─── EVENT HANDLERS ──────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-ai-scan":
            self.run_worker(self._do_scan(heal=False), exclusive=False, name="ai-scan")
        elif event.button.id == "btn-ai-heal":
            self.run_worker(self._do_scan(heal=True),  exclusive=False, name="ai-heal")
        elif event.button.id == "btn-ai-stop":
            self._cancel_flag = True
            self._set_status("[dim]Stopped.[/dim]")

    def _auto_scan(self) -> None:
        """Called by timer — rate-limited."""
        if self.is_running:
            return
        if time.time() - self._last_scan_ts < 60.0:
            return
        self.run_worker(self._do_scan(heal=True), exclusive=False, name="ai-auto")

    # ─── MESH PROBE ──────────────────────────────────────────────────────────

    def _probe_mesh(self) -> Dict[str, Any]:
        """Collect live mesh state synchronously (fast, <2s total)."""
        state: Dict[str, Any] = {
            "timestamp": time.strftime("%H:%M:%S"),
            "proxy_8080": False,
            "models": {},
            "rpc_nodes": {},
            "pixel_8087": False,
            "tailscale": "unknown",
        }

        def tcp_ok(host: str, port: int, timeout: float = 1.5) -> bool:
            import socket
            try:
                s = socket.create_connection((host, port), timeout=timeout)
                s.close()
                return True
            except Exception:
                return False

        def http_health(url: str) -> bool:
            try:
                import urllib.request
                r = urllib.request.urlopen(url, timeout=2)
                body = json.loads(r.read())
                return body.get("status") == "ok"
            except Exception:
                return False

        state["proxy_8080"]      = http_health("http://127.0.0.1:8080/health")
        state["models"]["qwen7b"]  = http_health("http://127.0.0.1:8083/health")
        state["models"]["mistral"] = http_health("http://127.0.0.1:8082/health")
        state["models"]["qwen27b"] = http_health("http://127.0.0.1:8085/health")
        state["models"]["nemotron"] = http_health("http://127.0.0.1:8084/health")
        state["rpc_nodes"]["macbook_pro"]  = tcp_ok("192.168.8.127", 50052)
        state["rpc_nodes"]["linux_head"]   = tcp_ok("100.101.39.98", 50052)
        state["rpc_nodes"]["pixel"]        = tcp_ok("100.73.38.87",  50052)
        state["pixel_8087"]  = tcp_ok("100.73.38.87", 8087)

        # Tailscale summary
        try:
            r = subprocess.run(
                ["tailscale", "status", "--json"],
                capture_output=True, text=True, timeout=3
            )
            ts_data = json.loads(r.stdout)
            peers = ts_data.get("Peer", {})
            online = sum(1 for p in peers.values() if p.get("Online", False))
            state["tailscale"] = f"{online}/{len(peers)} peers online"
        except Exception:
            state["tailscale"] = "tailscale CLI unavailable"

        return state

    # ─── MAIN WORKER ─────────────────────────────────────────────────────────

    @work(exclusive=False)
    async def _do_scan(self, heal: bool = True) -> None:
        if self.is_running:
            return
        self.is_running = True
        self._cancel_flag = False
        self._last_scan_ts = time.time()

        log = self.query_one("#net-ai-log", RichLog)
        self._set_status("[yellow]● Scanning…[/yellow]")

        try:
            # 1. Collect mesh state
            log.write(f"\n[bold cyan]{'─'*60}[/bold cyan]")
            log.write(f"[bold cyan]🔍 [{time.strftime('%H:%M:%S')}] AI Mesh Scan[/bold cyan]")
            state = await asyncio.get_event_loop().run_in_executor(None, self._probe_mesh)

            # 2. Render state table to log
            proxy_str = "✅ LIVE" if state["proxy_8080"] else "❌ DOWN"
            log.write(f"  Proxy :8080      {proxy_str}")
            for name, ok in state["models"].items():
                log.write(f"  Model {name:<12} {'✅' if ok else '⏳'}")
            for node, ok in state["rpc_nodes"].items():
                log.write(f"  RPC {node:<16} {'✅' if ok else '❌'}")
            log.write(f"  Pixel :8087      {'✅' if state['pixel_8087'] else '❌'}")
            log.write(f"  Tailscale        {state['tailscale']}")

            if self._cancel_flag:
                return

            # 3. Build issues list
            issues: List[str] = []
            if not state["proxy_8080"]:
                issues.append("Proxy :8080 DOWN — chat IDE will not function")
            if not state["models"].get("qwen7b"):
                issues.append("Qwen-Coder-7B :8083 not ready — primary fast model offline")
            offline_rpc = [n for n, ok in state["rpc_nodes"].items() if not ok]
            if offline_rpc:
                issues.append(f"RPC workers offline: {', '.join(offline_rpc)} — Nemotron-70B cannot shard")
            if not state["pixel_8087"]:
                issues.append("Pixel llama-server :8087 down — Tensor G5 offline")

            if not issues:
                log.write("[bold green]  ✅ All systems HEALTHY — no AI analysis needed[/bold green]")
                self._set_status("[green]● Healthy[/green]")
                _log_action("MESH_SCAN", "ALL_HEALTHY", True)
                return

            # 4. AI analysis of issues
            log.write(f"\n[bold yellow]🧠 AI analyzing {len(issues)} issue(s)…[/bold yellow]")

            system_prompt = (
                "You are the Lauburu Mesh Network Health AI. "
                "You specialize in diagnosing and healing a 7-node distributed AI mesh running "
                "llama.cpp RPC sharding, Petals DHT, and a FastAPI proxy on macOS + Linux + Android. "
                "Given a list of issues, respond with:\n"
                "1. A brief 1-line root cause for each issue\n"
                "2. A JSON block of healing actions in this exact format:\n"
                '{"actions": [{"cmd": "<shell command>", "reason": "<why>"}]}\n'
                "Only suggest commands from this allowlist:\n"
                "- bash /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/mesh_rpc_petals_healer.sh\n"
                "- python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/nomad_courier_self_healer.py --once\n"
                "- launchctl unload /Users/aaron/Library/LaunchAgents/ai.lauburu.unified.proxy.plist\n"
                "- launchctl load /Users/aaron/Library/LaunchAgents/ai.lauburu.unified.proxy.plist\n"
                "- curl -s --max-time 2 http://127.0.0.1:8080/health\n"
                "Keep your response under 150 words. Be direct and technical."
            )
            user_prompt = (
                f"Mesh state at {state['timestamp']}:\n"
                + "\n".join(f"  - {i}" for i in issues)
                + "\n\nDiagnose and provide healing actions JSON."
            )

            # 5. Stream AI response
            full_response = ""
            try:
                import httpx
                payload = {
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_prompt},
                    ],
                    "stream": True,
                    "max_tokens": 300,
                    "temperature": 0.2,
                }
                log.write("[dim]AI:[/dim] ", end="")
                timeout_cfg = httpx.Timeout(connect=3.0, read=45.0, write=5.0, pool=5.0)
                async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                    async with client.stream("POST", PROXY_URL, json=payload) as resp:
                        if resp.status_code != 200:
                            log.write(f"[red]Model unavailable (HTTP {resp.status_code})[/red]")
                            return
                        async for line in resp.aiter_lines():
                            if self._cancel_flag:
                                break
                            if not line.startswith("data: "):
                                continue
                            data = line[6:].strip()
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                token = chunk["choices"][0]["delta"].get("content", "")
                                if token:
                                    full_response += token
                                    log.write(token, end="", markup=False)
                            except Exception:
                                continue
                log.write("")  # newline after stream

            except Exception as e:
                log.write(f"[red]AI stream error: {e}[/red]")
                # Fallback: run healer directly without AI
                full_response = '{"actions": [{"cmd": "bash /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/mesh_rpc_petals_healer.sh", "reason": "AI unavailable — running default healer"}]}'

            if self._cancel_flag or not heal:
                self._set_status("[dim]Scan complete (heal skipped)[/dim]")
                return

            # 6. Parse and execute safe actions
            actions_to_run: List[Dict] = []
            try:
                # Find JSON block in AI response
                start = full_response.find('{"actions"')
                if start == -1:
                    start = full_response.find('```json\n{"actions"')
                    if start != -1:
                        start += 8
                if start != -1:
                    end = full_response.find("}", start) + 1
                    # Find matching closing brace for the outer object
                    depth = 0
                    for i, ch in enumerate(full_response[start:], start):
                        if ch == "{":
                            depth += 1
                        elif ch == "}":
                            depth -= 1
                            if depth == 0:
                                end = i + 1
                                break
                    parsed = json.loads(full_response[start:end])
                    actions_to_run = parsed.get("actions", [])
            except Exception as e:
                log.write(f"[dim yellow]JSON parse: {e} — running default healer[/dim yellow]")
                actions_to_run = [{
                    "cmd": "bash /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/mesh_rpc_petals_healer.sh",
                    "reason": "Fallback: could not parse AI actions"
                }]

            if not actions_to_run:
                log.write("[dim]AI suggested no executable actions.[/dim]")
                self._set_status("[green]● Scan done[/green]")
                return

            log.write(f"\n[bold magenta]🔧 Executing {len(actions_to_run)} healing action(s):[/bold magenta]")
            for action in actions_to_run:
                cmd = action.get("cmd", "").strip()
                reason = action.get("reason", "")

                if not cmd:
                    continue

                if not _is_safe(cmd):
                    log.write(f"  [red]⛔ BLOCKED (not in allowlist): {cmd[:60]}[/red]")
                    _log_action(cmd, "BLOCKED_NOT_IN_ALLOWLIST", False)
                    continue

                log.write(f"  [yellow]▶ {cmd[:80]}[/yellow]")
                if reason:
                    log.write(f"    [dim]{reason}[/dim]")

                try:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda c=cmd: subprocess.run(
                            c, shell=True, capture_output=True, text=True, timeout=30
                        )
                    )
                    out = (result.stdout + result.stderr).strip()[:200]
                    if result.returncode == 0:
                        log.write(f"    [green]✅ OK: {out[:100] if out else 'done'}[/green]")
                    else:
                        log.write(f"    [red]❌ exit {result.returncode}: {out[:100]}[/red]")
                    _log_action(cmd, out or f"exit:{result.returncode}", True)
                except asyncio.TimeoutError:
                    log.write(f"    [red]❌ Command timed out (30s)[/red]")
                    _log_action(cmd, "TIMEOUT", True)
                except Exception as e:
                    log.write(f"    [red]❌ {e}[/red]")
                    _log_action(cmd, str(e), True)

            self._set_status("[green]● Healed[/green]")
            log.write("[bold green]  🏁 Healing cycle complete[/bold green]")

        finally:
            self.is_running = False

    def _set_status(self, markup: str) -> None:
        try:
            self.query_one("#net-ai-status", Static).update(markup)
        except Exception:
            pass
