import os
import sys
import time
import json
import asyncio
from pathlib import Path
from typing import Optional, Any, Union

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, RichLog, Input, Label, Button
from textual import work
from bleak import BleakScanner, BleakClient

# Connect to chat_dispatcher if available
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from chat_dispatcher import default_chat_dispatcher
except Exception:
    default_chat_dispatcher = None

from mesh_healer import HealerState, MeshHealer

# Nordic UART Service (NUS)
NUS_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
NUS_RX_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
NUS_TX_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

class BluetoothTerminalApp(App):
    """Bluetooth Serial Terminal TUI for Lauburu Mesh."""
    
    CSS_PATH = "ui/app.tcss"
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "scan", "Scan Devices"),
        ("d", "disconnect", "Disconnect"),
    ]

    def __init__(self, mesh_healer: Optional[MeshHealer] = None):
        super().__init__()
        self.client: Optional[BleakClient] = None
        self.target_address: Optional[str] = None
        self._connected = False
        self.mesh_healer = mesh_healer or MeshHealer(app=self)
        self.mesh_healer.app = self

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="main_container"):
            with Horizontal(id="status_bar"):
                yield Label("Status: DISCONNECTED", id="status_label")
                yield Label("[Stage 1: Raw Serial]", id="stage_label")
                yield Button("Scan & Connect", id="btn_scan", variant="primary")
                yield Button("Disconnect", id="btn_disconnect", variant="error")
            
            yield RichLog(id="terminal_log", highlight=True, markup=True)
            yield Input(placeholder="Send UART Command...", id="terminal_input")
        yield Footer()

    def on_mount(self) -> None:
        self.log_widget = self.query_one("#terminal_log", RichLog)
        self.status_label = self.query_one("#status_label", Label)
        self.stage_label = self.query_one("#stage_label", Label)
        self.log_widget.write("[bold cyan]=== LAUBURU BLUETOOTH SERIAL TERMINAL ===[/]")
        self.log_widget.write("[bold green]Movesense 512Hz BLE Stream & Sovereign Medical AI Active.[/]")
        self.log_widget.write("[dim]Ready. Press 's' to scan for Movesense / NUS devices.[/]")
        self.watch_stream_pipe()
        self._start_mesh_healer()

    @work
    async def _start_mesh_healer(self):
        await self.mesh_healer.start_monitoring()

    async def on_unmount(self) -> None:
        if self.mesh_healer:
            await self.mesh_healer.stop_monitoring()

    @work(thread=True)
    def watch_stream_pipe(self):
        pipe_path = "/tmp/bluetooth_terminal_stream.ansi"
        last_pos = 0
        while self.is_running:
            if os.path.exists(pipe_path):
                try:
                    with open(pipe_path, "r", encoding="utf-8", errors="replace") as f:
                        f.seek(last_pos)
                        lines = f.readlines()
                        last_pos = f.tell()
                        for line in lines:
                            clean = line.strip()
                            if clean and self.is_running:
                                self.call_from_thread(self.log_widget.write, clean)
                except Exception:
                    pass
            for _ in range(5):
                if not self.is_running:
                    break
                time.sleep(0.1)

    @work(exclusive=True)
    async def action_scan(self):
        self._update_status("SCANNING...")
        self.log_widget.write("[yellow]Scanning for BLE devices...[/]")
        
        try:
            devices = await BleakScanner.discover(timeout=5.0)
            target = None
            for d in devices:
                self.log_widget.write(f"Found: {d.name} ({d.address})")
                if d.name and ("Movesense" in d.name or "Nordic" in d.name or "Lauburu" in d.name):
                    target = d
                    break
            
            if target:
                self.log_widget.write(f"[green]Target found: {target.name} ({target.address})[/]")
                self.target_address = target.address
                await self.connect_to_device()
            else:
                self.log_widget.write("[red]No matching device found.[/]")
                self._update_status("DISCONNECTED")
        except Exception as e:
            self.log_widget.write(f"[red]Scan error: {e}[/]")
            self._update_status("ERROR")

    async def connect_to_device(self):
        self._update_status("CONNECTING...")
        self.log_widget.write(f"Connecting to {self.target_address}...")
        
        try:
            self.client = BleakClient(self.target_address, disconnected_callback=self._on_disconnect)
            await self.client.connect()
            self._connected = True
            if self.mesh_healer and self.mesh_healer.nus_transport:
                self.mesh_healer.nus_transport.client = self.client
                self.mesh_healer.nus_transport.is_connected = True
            self._update_status(f"CONNECTED: {self.target_address}")
            self.log_widget.write(f"[bold green]Successfully connected to {self.target_address}[/]")
            
            await self.client.start_notify(NUS_TX_UUID, self._rx_handler)
            self.log_widget.write("[cyan]Streaming UART data (RX)...[/]")
            
            # Keep connection alive while running
            while self.is_running and self._connected:
                await asyncio.sleep(1.0)
                
        except Exception as e:
            self.log_widget.write(f"[bold red]Connection error: {e}[/]")
            self._update_status("ERROR")
        finally:
            if self.client:
                try:
                    await self.client.disconnect()
                except Exception:
                    pass
            if self.mesh_healer and self.mesh_healer.nus_transport:
                self.mesh_healer.nus_transport.is_connected = False

    def _rx_handler(self, sender: int, data: bytearray):
        if self.mesh_healer and self.mesh_healer.nus_transport:
            self.mesh_healer.nus_transport._on_gatt_notification(sender, data)
        try:
            decoded = data.decode("utf-8")
            self.log_widget.write(f"[green]RX>[/]\t{decoded}")
        except UnicodeDecodeError:
            self.log_widget.write(f"[yellow]RX (Hex)>[/]\t{data.hex()}")

    def _on_disconnect(self, client):
        self._connected = False
        if self.mesh_healer and self.mesh_healer.nus_transport:
            self.mesh_healer.nus_transport.is_connected = False
        self._update_status("DISCONNECTED")
        self.log_widget.write("[bold red]Device disconnected.[/]")

    @work
    async def action_disconnect(self):
        self._connected = False
        if self.mesh_healer and self.mesh_healer.nus_transport:
            self.mesh_healer.nus_transport.is_connected = False
        if self.client:
            self.log_widget.write("Disconnecting...")
            try:
                await self.client.disconnect()
            except Exception:
                pass
        else:
            self.log_widget.write("Not connected.")
        self._update_status("DISCONNECTED")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_scan":
            self.action_scan()
        elif event.button.id == "btn_disconnect":
            self.action_disconnect()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        cmd = event.value
        if not cmd:
            return
        self.query_one("#terminal_input", Input).value = ""
        self.log_widget.write(f"[blue]TX>[/]\t{cmd}")

        clean_cmd = cmd.strip()
        # Intercept /nexus ENABLE_PAN for Stage 2 escalation
        if clean_cmd in ["/nexus ENABLE_PAN", "ENABLE_PAN", "/dispatch ENABLE_PAN"] or clean_cmd.startswith("/nexus ENABLE_PAN"):
            self._handle_enable_pan()
            return

        if clean_cmd.startswith("/nexus ") or clean_cmd.startswith("/dispatch "):
            directive = clean_cmd.split(" ", 1)[1].strip()
            self._handle_nexus_dispatch(directive)
            return
        elif clean_cmd in ["/threads", "/chats"]:
            self._handle_nexus_threads()
            return
        elif clean_cmd in ["/next", "/nextsteps"]:
            self._handle_nexus_next_steps()
            return
        elif clean_cmd in ["/help", "help"]:
            self.log_widget.write("[bold yellow]=== BLUETOOTH TERMINAL IDE COMMANDS ===[/]")
            self.log_widget.write("  /nexus ENABLE_PAN   - Escalate to Stage 2 Bluetooth PAN (Shizuku BNEP)")
            self.log_widget.write("  /nexus <directive>  - Dispatch directive through Sovereign Single-Chat Nexus")
            self.log_widget.write("  /threads            - List active satellite chats & agents")
            self.log_widget.write("  /next               - View latest proactive Next-Step Discussion")
            self.log_widget.write("  [s]                 - Scan & connect to Movesense / BLE NUS")
            self.log_widget.write("  [d]                 - Disconnect BLE")
            self.log_widget.write("  [q]                 - Quit")
            return
        
        if self._connected and self.client:
            @work
            async def send_data():
                data = (cmd + "\r\n").encode("utf-8")
                try:
                    if self.mesh_healer and self.mesh_healer.nus_transport:
                        await self.mesh_healer.nus_transport.write_raw_data(data, response=False)
                    else:
                        await self.client.write_gatt_char(NUS_RX_UUID, data, response=False)
                except Exception as e:
                    self.log_widget.write(f"[red]Send error: {e}[/]")
            send_data()
        else:
            self.log_widget.write("[yellow]Note: BLE not connected. Type /nexus <directive> or /help for IDE commands.[/]")

    @work
    async def _handle_enable_pan(self):
        self.log_widget.write("[bold yellow]👑 SINGLE CHAT NEXUS:[/] Intercepted /nexus ENABLE_PAN")
        res = await self.mesh_healer.handle_command("/nexus ENABLE_PAN")
        if res:
            self.log_widget.write(res)

    def update_healer_stage(self, stage: Any) -> None:
        stage_val = getattr(stage, "value", str(stage))
        badge_map = {
            "STAGE_0_NORMAL": "[Stage 0: Normal]",
            "STAGE_1_RAW_SERIAL": "[Stage 1: Raw Serial]",
            "STAGE_2_PAN_ESCALATING": "[Stage 2: BT PAN Escalating]",
            "STAGE_2_PAN_CONNECTED": "[Stage 2: BT PAN]",
            "STAGE_3_SSH_MOSH": "[Stage 3: SSH/Mosh]",
        }
        badge = badge_map.get(stage_val, f"[{stage_val}]")
        try:
            self.stage_label.update(badge)
        except Exception:
            try:
                self.query_one("#stage_label", Label).update(badge)
            except Exception:
                pass

    @work(thread=True)
    def _handle_nexus_dispatch(self, directive: str):
        self.call_from_thread(self.log_widget.write, f"[bold yellow]👑 SINGLE CHAT NEXUS:[/] Fanning out directive: \"{directive}\"...")
        if default_chat_dispatcher:
            try:
                res = default_chat_dispatcher.dispatch(directive)
                fan_str = ", ".join([f["thread_title"] for f in res.get("fanouts", [])])
                self.call_from_thread(self.log_widget.write, f"[cyan]Fanned out to {len(res.get('fanouts', []))} satellite chats:[/] {fan_str}")
                for a in res.get("actions_completed", []):
                    self.call_from_thread(self.log_widget.write, f"[green]⚡ [{a.get('thread_title')}] Completed:[/] {a['action']} (Exit: {a['exit_code']})")
                self.call_from_thread(self.log_widget.write, f"[bold yellow]💡 NEXT STEP DISCUSSION:[/] {res.get('next_step_discussion')}")
                opts = res.get("suggested_options", [])
                if opts:
                    self.call_from_thread(self.log_widget.write, "[bold cyan]Recommended Actions:[/]")
                    for i, opt in enumerate(opts):
                        self.call_from_thread(self.log_widget.write, f"  [{i+1}] {opt}")
            except Exception as e:
                self.call_from_thread(self.log_widget.write, f"[red]Nexus dispatch error: {e}[/]")
        else:
            self.call_from_thread(self.log_widget.write, "[red]Chat dispatcher unavailable.[/]")

    @work(thread=True)
    def _handle_nexus_threads(self):
        if default_chat_dispatcher:
            threads = default_chat_dispatcher.list_threads()
            self.call_from_thread(self.log_widget.write, f"[bold cyan]=== ACTIVE SATELLITE CHATS ({len(threads)}) ===[/]")
            for t in threads:
                self.call_from_thread(self.log_widget.write, f"• [{t['category'].upper()}] {t['title']} ({t['id']}) - {t.get('message_count',0)} msgs, {t.get('action_count',0)} actions")
        else:
            self.call_from_thread(self.log_widget.write, "[red]Chat dispatcher unavailable.[/]")

    @work(thread=True)
    def _handle_nexus_next_steps(self):
        if default_chat_dispatcher:
            ns = default_chat_dispatcher.get_latest_next_steps()
            self.call_from_thread(self.log_widget.write, "[bold yellow]=== LATEST NEXT STEP DISCUSSION ===[/]")
            self.call_from_thread(self.log_widget.write, ns.get("discussion", "No discussion cached yet."))
            opts = ns.get("options", [])
            if opts:
                self.call_from_thread(self.log_widget.write, "[bold cyan]Recommended Actions:[/]")
                for i, opt in enumerate(opts):
                    self.call_from_thread(self.log_widget.write, f"  [{i+1}] {opt}")
        else:
            self.call_from_thread(self.log_widget.write, "[red]Chat dispatcher unavailable.[/]")

    def _update_status(self, text: str):
        self.status_label.update(f"Status: {text}")

if __name__ == "__main__":
    app = BluetoothTerminalApp()
    app.run()
