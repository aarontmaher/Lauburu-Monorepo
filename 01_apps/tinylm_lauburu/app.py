# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "textual",
#     "psutil",
# ]
# ///
import asyncio
import os
import sys
import time
import subprocess
import psutil
from textual import work, on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, Log, Button, Label, TabbedContent, TabPane, Input

sys.path.append("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network")
try:
    import mesh_ping
except ImportError:
    mesh_ping = None

class NodeStatusMessage(Static):
    pass # Replaced by custom message
    
from textual.message import Message
class NodeStatus(Message):
    def __init__(self, node_id: str, status: str, latency: str, transport: str):
        super().__init__()
        self.node_id = node_id
        self.status = status
        self.latency = latency
        self.transport = transport

class MeshTelemetry(Static):
    """Widget to display the status of the 7-layer mesh network."""
    
    NODES = [
        ("L1", "L1_Mac_Host"),
        ("L2", "L2_MacBook_Pro"),
        ("L3", "L3_Linux_Hub"),
        ("L4", "L4_Linux_Tablet"),
        ("L5", "L5_MacBook_Air"),
        ("L6", "L6_Pixel_10_Edge"),
        ("L7", "L7_Samsung_S20"),
        ("GW", "GW_Router"),
    ]

    def compose(self) -> ComposeResult:
        yield Label("🌐 7-Layer Mesh Status", classes="section-title")
        for layer, name in self.NODES:
            yield Horizontal(
                Label(f"[{layer}] {name}", classes="node-name"),
                Label("--", id=f"status-{layer}", classes="node-status"),
                Label("--", id=f"latency-{layer}", classes="node-latency"),
                Label("--", id=f"transport-{layer}", classes="node-transport"),
                classes="node-row"
            )

class AppControlPanel(Static):
    """Panel to control various apps in the ecosystem."""
    
    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Apps & Infra", id="tab-apps"):
                yield VerticalScroll(
                    Label("Sovereign Local AI Topology", classes="subsection-title"),
                    Horizontal(Button("Ping Qwen 3.8 Max (L1:8082)", id="btn-ping-master", variant="primary"),
                               Button("Ping Abliterated (L1:8083)", id="btn-ping-redteam", variant="primary")),
                    Label("Data & Sync", classes="subsection-title"),
                    Horizontal(Button("SeaweedFS Status", id="btn-seaweedfs", variant="primary"),
                               Button("Verify Tri-Vault Storage", id="btn-verify-trivault", variant="warning")),
                    Label("Custom Command", classes="subsection-title"),
                    Input(placeholder="Enter shell command...", id="custom-cmd-input")
                )
            with TabPane("Tablet Resources", id="tab-resources"):
                yield VerticalScroll(
                    Label("L4 Linux Tablet Metrics", classes="subsection-title"),
                    Label("CPU: --%", id="cpu-lbl"),
                    Label("RAM: --%", id="ram-lbl"),
                    Label("Disk: --", id="disk-lbl"),
                    Button("Refresh Metrics", id="btn-refresh-metrics", variant="primary")
                )

class TinyLMLauburu(App):
    """Terminal tinylm for the Lauburu Ecosystem, optimized for Samsung Tablet."""
    
    CSS = """
    Screen {
        layout: grid;
        grid-size: 3 4;
        grid-rows: 100%;
        grid-columns: 1fr 2fr;
    }
    
    #sidebar {
        row-span: 3;
        column-span: 1;
        background: $panel;
        padding: 1;
        border-right: vkey $primary;
    }
    
    #main-panel {
        row-span: 2;
        column-span: 2;
        padding: 1;
    }
    
    #console {
        row-span: 1;
        column-span: 2;
        border-top: vkey $primary;
        height: 100%;
    }
    
    .section-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    
    .subsection-title {
        text-style: bold;
        color: $secondary;
        margin-top: 1;
        margin-bottom: 1;
    }
    
    .node-row {
        height: 1;
        margin-bottom: 1;
    }
    
    .node-name {
        width: 18;
    }
    
    .node-status {
        width: 10;
        color: $warning;
    }
    
    .node-latency {
        width: 10;
        color: $success;
        text-align: right;
    }
    
    .node-transport {
        width: 12;
        color: $primary;
        text-align: right;
    }
    
    Button {
        margin-right: 1;
        margin-bottom: 1;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh_mesh", "Refresh Mesh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="sidebar"):
            yield MeshTelemetry(id="mesh-telemetry")
        with Container(id="main-panel"):
            yield AppControlPanel()
        with Container(id="console"):
            yield Log(id="sys-log", highlight=True)
        yield Footer()

    def on_mount(self) -> None:
        self.sys_log = self.query_one("#sys-log", Log)
        self.sys_log.write_line("[bold green]TinyLM Lauburu[/bold green] initialized on Node L4 (Linux_Tablet).")
        self.sys_log.write_line("Zero-Mock Truth Protocol active. Awaiting commands.")
        self.poll_mesh()
        self.update_metrics()

    @work(thread=True)
    def poll_mesh(self) -> None:
        """Background thread to poll mesh nodes using mesh_ping.py."""
        if not mesh_ping:
            self.app.call_from_thread(self.sys_log.write_line, "[red]Error: mesh_ping module not found.[/red]")
            return
            
        for layer, name in MeshTelemetry.NODES:
            try:
                res = mesh_ping.resolve_node(name, fast_path=True, strict_recovery=False)
                if res["status"] == "CONNECTED":
                    status = "[green]UP[/green]"
                    latency = f"{res['rtt_ms']:.1f}ms"
                    transport = res["transport"]
                else:
                    status = "[red]DOWN[/red]"
                    latency = "--"
                    transport = "--"
            except Exception as e:
                status = "[red]ERR[/red]"
                latency = "--"
                transport = "--"
                
            self.post_message(NodeStatus(layer, status, latency, transport))
            time.sleep(0.1)

    @on(NodeStatus)
    def update_node_status(self, event: NodeStatus) -> None:
        try:
            self.query_one(f"#status-{event.node_id}", Label).update(event.status)
            self.query_one(f"#latency-{event.node_id}", Label).update(event.latency)
            self.query_one(f"#transport-{event.node_id}", Label).update(event.transport)
        except Exception:
            pass

    def action_refresh_mesh(self) -> None:
        self.sys_log.write_line("[cyan]Refreshing 7-Layer Mesh telemetry...[/cyan]")
        for layer, _ in MeshTelemetry.NODES:
            try:
                self.query_one(f"#status-{layer}", Label).update("[yellow]--[/yellow]")
                self.query_one(f"#latency-{layer}", Label).update("--")
                self.query_one(f"#transport-{layer}", Label).update("--")
            except Exception:
                pass
        self.poll_mesh()

    def update_metrics(self) -> None:
        try:
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            self.query_one("#cpu-lbl", Label).update(f"CPU: {cpu}%")
            self.query_one("#ram-lbl", Label).update(f"RAM: {ram.percent}% ({ram.available / (1024**3):.1f}GB free)")
            self.query_one("#disk-lbl", Label).update(f"Disk: {disk.percent}% ({disk.free / (1024**3):.1f}GB free)")
        except Exception as e:
            self.sys_log.write_line(f"Error fetching metrics: {e}")

    @on(Button.Pressed)
    def handle_button(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        self.sys_log.write_line(f"Command dispatched: [bold]{btn_id}[/bold]")
        
        if btn_id == "btn-refresh-metrics":
            self.update_metrics()
            self.sys_log.write_line("Metrics refreshed.")
            return

        # Execute physical actuation via subprocess
        self.execute_command(btn_id)
        
    @on(Input.Submitted, "#custom-cmd-input")
    def handle_custom_command(self, event: Input.Submitted) -> None:
        cmd = event.value
        if not cmd:
            return
        self.sys_log.write_line(f"Executing: [cyan]{cmd}[/cyan]")
        self.query_one("#custom-cmd-input", Input).value = ""
        self.execute_shell_command(cmd)

    @work(thread=True)
    def execute_command(self, btn_id: str) -> None:
        cmd_map = {
            "btn-ping-master": ["python3", "-c", "import sys; sys.path.append('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network'); import mesh_ping; print(mesh_ping.resolve_node('L1_Mac_Host', port=8082))"],
            "btn-ping-redteam": ["python3", "-c", "import sys; sys.path.append('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network'); import mesh_ping; print(mesh_ping.resolve_node('L1_Mac_Host', port=8083))"],
            "btn-seaweedfs": ["df", "-h", "/mnt/seaweedfs"],
            "btn-verify-trivault": ["ls", "-la", "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/Index.md"]
        }
        
        if btn_id in cmd_map:
            try:
                res = subprocess.run(cmd_map[btn_id], capture_output=True, text=True, timeout=10)
                out = res.stdout.strip()
                err = res.stderr.strip()
                if out:
                    self.app.call_from_thread(self.sys_log.write_line, f"Output:\n{out}")
                if err:
                    self.app.call_from_thread(self.sys_log.write_line, f"[red]Error:\n{err}[/red]")
                self.app.call_from_thread(self.sys_log.write_line, f"[{btn_id}] Exit Code {res.returncode}")
            except Exception as e:
                self.app.call_from_thread(self.sys_log.write_line, f"[red]Exception executing {btn_id}: {e}[/red]")
        else:
            self.app.call_from_thread(self.sys_log.write_line, f"[yellow]No handler for {btn_id}[/yellow]")

    @work(thread=True)
    def execute_shell_command(self, cmd: str) -> None:
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            out = res.stdout.strip()
            err = res.stderr.strip()
            if out:
                self.app.call_from_thread(self.sys_log.write_line, f"Output:\n{out}")
            if err:
                self.app.call_from_thread(self.sys_log.write_line, f"[red]Error:\n{err}[/red]")
            self.app.call_from_thread(self.sys_log.write_line, f"Exit Code {res.returncode}")
        except Exception as e:
            self.app.call_from_thread(self.sys_log.write_line, f"[red]Exception: {e}[/red]")

if __name__ == "__main__":
    app = TinyLMLauburu()
    app.run()
