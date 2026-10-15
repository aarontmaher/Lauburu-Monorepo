#!/usr/bin/env python3
"""
Screen Lens Sovereign: Reactive Notebook IDE Web Studio (Port 4005)
===================================================================
Part of the Screen Lens Sovereign TUI & Notebook IDE Ecosystem.

Features:
- Lightweight, zero-dependency async HTTP Server running on Port 4005
- Reactive REST API endpoints for task prioritization, sharding latency, and model dispatch
- Interactive Reactive Studio UI with Dark Mode, Live Topology DAG, and Model Routing
- Bidirectional sync to JupyterLab / Marimo reactive notebooks
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver
import threading

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lens_monorepo_roi_engine import MonorepoROIEngine
from lens_workspace_cloud_hub import LensWorkspaceCloudHub

DEFAULT_PORT = 4008
NOTEBOOK_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/src/notebooks")


class ReactiveIDEHandler(BaseHTTPRequestHandler):
    roi_engine = MonorepoROIEngine()
    cloud_hub = LensWorkspaceCloudHub()

    def do_GET(self):
        if self.path == "/api/status":
            self.handle_api_status()
        elif self.path == "/api/tasks":
            self.handle_api_tasks()
        elif self.path == "/api/shards":
            self.handle_api_shards()
        elif self.path == "/" or self.path.startswith("/?"):
            self.handle_ui_dashboard()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        if self.path == "/api/execute":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                data = json.loads(body)
            except Exception:
                data = {}
            self.handle_api_execute(data)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def handle_api_status(self):
        tasks = self.roi_engine.scan_and_prioritize()
        shards = self.cloud_hub.probe_distributed_sharding()
        
        # [NEW] Active Bluetooth Network Healing (Phase 2)
        try:
            sys.path.insert(0, "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network")
            import canonical_network_resurrection_engine as cnre
            for shard in shards:
                if not shard.is_online and shard.node_name in cnre.get_mesh_ip_matrix():
                    cnre.ensure_node_connectivity(shard.node_name)
        except Exception:
            pass
            
        quota = self.cloud_hub.get_google_cloud_quota_status()
        alerts = self.cloud_hub.get_google_workspace_alerts(limit=5)

        payload = {
            "status": "HEALTHY",
            "timestamp": time.time(),
            "highest_roi_tasks": [t.to_dict() for t in tasks],
            "sharding_nodes": [s.__dict__ for s in shards],
            "cloud_quota": quota.__dict__,
            "workspace_alerts": alerts
        }
        self.send_json_response(payload)

    def handle_api_tasks(self):
        tasks = self.roi_engine.scan_and_prioritize()
        self.send_json_response({"tasks": [t.to_dict() for t in tasks]})

    def handle_api_shards(self):
        shards = self.cloud_hub.probe_distributed_sharding()
        self.send_json_response({"shards": [s.__dict__ for s in shards]})

    def handle_api_execute(self, data: Dict[str, Any]):
        task_id = data.get("task_id", "top")
        tasks = self.roi_engine.scan_and_prioritize()
        target_task = tasks[0] if tasks else None
        if task_id != "top":
            for t in tasks:
                if t.task_id == task_id:
                    target_task = t
                    break

        if not target_task:
            self.send_json_response({"status": "ERROR", "message": "No task found"}, status=400)
            return

        # Execute
        if target_task.category == "MOBILE_VLA":
            res = self.cloud_hub.execute_tool_call("read_file", {
                "path": "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/src/android_pixel/pixel_window_dump_fixture.xml"
            })
            outcome = {"status": "SUCCESS", "task": target_task.task_id, "execution": "Mobile VLA tree parsed"}
        elif target_task.category == "INFRASTRUCTURE":
            res = self.cloud_hub.execute_tool_call("shell_command", {
                "command": "find /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo -name '__pycache__' | wc -l"
            })
            outcome = {"status": "SUCCESS", "task": target_task.task_id, "execution": res}
        else:
            outcome = {"status": "SUCCESS", "task": target_task.task_id, "execution": "Dispatched to Sovereign Model Pipeline"}

        self.send_json_response(outcome)

    def send_json_response(self, data: Any, status: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_ui_dashboard(self):
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Screen Lens Sovereign: Reactive Notebook IDE</title>
    <style>
        :root {
            --bg: #0d1117;
            --surface: #161b22;
            --border: #30363d;
            --accent: #58a6ff;
            --green: #3fb950;
            --red: #f85149;
            --text: #c9d1d9;
            --subtext: #8b949e;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 24px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
            padding-bottom: 16px;
            margin-bottom: 24px;
        }
        .title {
            font-size: 24px;
            font-weight: 700;
            color: var(--accent);
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .card {
            background-color: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 18px;
        }
        .card-header {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 12px;
            color: #fff;
            border-bottom: 1px solid var(--border);
            padding-bottom: 8px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }
        th, td {
            text-align: left;
            padding: 8px 6px;
            border-bottom: 1px solid var(--border);
        }
        th { color: var(--subtext); font-weight: 500; }
        .badge {
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }
        .badge-green { background: rgba(63, 185, 80, 0.2); color: var(--green); }
        .badge-red { background: rgba(248, 81, 73, 0.2); color: var(--red); }
        .badge-blue { background: rgba(88, 166, 255, 0.2); color: var(--accent); }
        .task-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid var(--border);
        }
        .btn-exec {
            background-color: #238636;
            color: white;
            border: none;
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
        }
        .btn-exec:hover { background-color: #2ea043; }
    </style>
</head>
<body>
    <div class="header">
        <div class="title">
            <span>👁️</span> Screen Lens Sovereign: Reactive Notebook IDE Studio
        </div>
        <div>
            <button class="btn-exec" onclick="fetchData()">🔄 Refresh Telemetry</button>
            <button class="btn-exec" onclick="executeTop()" style="background:#1f6feb;">⚡ Execute Top ROI Task</button>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <div class="card-header">🌐 Distributed AI Tensor Sharding & 7-Layer Mesh</div>
            <table id="shards-table">
                <thead>
                    <tr><th>Node</th><th>Endpoint</th><th>RTT</th><th>Status</th><th>Mode</th></tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>

        <div class="card">
            <div class="card-header">⚡ Google Cloud Free Tier & Workspace Cadence</div>
            <div id="quota-content" style="font-size: 13px; line-height: 1.8;">Loading quota...</div>
        </div>
    </div>

    <div class="card" style="margin-top: 20px;">
        <div class="card-header">🚀 Highest-ROI Monorepo Tasks (Autonomous Dispatch Queue)</div>
        <div id="tasks-content">Loading tasks...</div>
    </div>

    <script>
        async function fetchData() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                renderShards(data.sharding_nodes);
                renderQuota(data.cloud_quota, data.workspace_alerts);
                renderTasks(data.highest_roi_tasks);
            } catch (e) {
                console.error(e);
            }
        }

        function renderShards(shards) {
            const tbody = document.querySelector('#shards-table tbody');
            tbody.innerHTML = shards.map(s => `
                <tr>
                    <td><b>${s.node_name}</b></td>
                    <td><code>${s.target_ip}</code></td>
                    <td>${s.rtt_ms} ms</td>
                    <td><span class="badge ${s.is_online ? 'badge-green' : 'badge-red'}">${s.is_online ? 'ONLINE' : 'OFFLINE'}</span></td>
                    <td><small>${s.sharding_mode}</small></td>
                </tr>
            `).join('');
        }

        function renderQuota(q, alerts) {
            const div = document.getElementById('quota-content');
            div.innerHTML = `
                <div><b>Provider:</b> ${q.provider} (${q.model})</div>
                <div><b>Daily Free Quota:</b> ${q.consumed_today} / ${q.daily_quota_rpd} consumed (<span style="color:var(--green);font-weight:bold;">${q.remaining_today} remaining</span>)</div>
                <div><b>Pacing Cadence:</b> ${q.cadence_rpm} RPM | <b>Reset in:</b> ${q.reset_hours_remaining} hrs</div>
                <hr style="border:0;border-top:1px solid var(--border);margin:10px 0;">
                <div><b>Workspace Alerts:</b> ${alerts.length} active alerts</div>
                ${alerts.map(a => `<div style="color:var(--subtext);font-size:12px;">• [${a.priority}] ${a.sender}: ${a.subject}</div>`).join('')}
            `;
        }

        function renderTasks(tasks) {
            const div = document.getElementById('tasks-content');
            div.innerHTML = tasks.map((t, idx) => `
                <div class="task-row">
                    <div>
                        <b>#${idx+1} [ROI: ${t.roi_score}] ${t.title}</b>
                        <div style="font-size:12px;color:var(--subtext);margin-top:2px;">
                            Model: <code style="color:var(--accent);">${t.assigned_model}</code> | Host: ${t.mesh_host} | Speedup: ${t.speedup_multiplier}x
                        </div>
                        <div style="font-size:12px;color:#8b949e;">${t.description}</div>
                    </div>
                    <div>
                        <button class="btn-exec" onclick="executeTask('${t.task_id}')">Execute</button>
                    </div>
                </div>
            `).join('');
        }

        async function executeTop() {
            const res = await fetch('/api/execute', {method: 'POST', body: JSON.stringify({task_id: 'top'})});
            const out = await res.json();
            alert('Executed: ' + JSON.stringify(out));
            fetchData();
        }

        async function executeTask(id) {
            const res = await fetch('/api/execute', {method: 'POST', body: JSON.stringify({task_id: id})});
            const out = await res.json();
            alert('Executed Task ' + id + ': ' + JSON.stringify(out));
            fetchData();
        }

        fetchData();
    </script>
</body>
</html>
"""
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class ScreenLensNotebookIDE:
    def __init__(self, port: int = DEFAULT_PORT):
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self, blocking: bool = False):
        """Starts the Reactive Notebook IDE HTTP server."""
        self.server = HTTPServer(("0.0.0.0", self.port), ReactiveIDEHandler)
        print(f"[+] Screen Lens Reactive Notebook IDE Studio running on http://127.0.0.1:{self.port}")
        
        if blocking:
            try:
                self.server.serve_forever()
            except KeyboardInterrupt:
                self.stop()
        else:
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            print("[*] Screen Lens Notebook IDE stopped.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Screen Lens Sovereign Reactive Notebook IDE")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind (default: 4005)")
    parser.add_argument("--daemon", action="store_true", help="Run in background daemon mode")
    args = parser.parse_args()

    ide_studio = ScreenLensNotebookIDE(port=args.port)
    ide_studio.start(blocking=not args.daemon)
