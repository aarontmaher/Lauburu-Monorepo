import sys
import os
import asyncio
import struct
from pathlib import Path
from typing import Optional, List, Dict
import time

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Grid, VerticalScroll, Container, HorizontalScroll, Horizontal
from textual.widgets import Header, Footer, Static, RichLog, Sparkline, Label, Button
from textual.reactive import reactive
from textual import work
from textual.message import Message

try:
    from bleak import BleakScanner, BleakClient
except ImportError:
    pass

sys.path.insert(0, '/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/03_biometrics_and_telemetry')
try:
    from movesense_dsp import TinyMLHealthAnalyzer
except ImportError:
    TinyMLHealthAnalyzer = None

class DeviceTelemetry(Message):
    def __init__(self, device_id: str, device_name: str, msg_type: str, **kwargs):
        self.device_id = device_id
        self.device_name = device_name
        self.msg_type = msg_type
        self.data = kwargs
        super().__init__()

class LogTelemetry(Message):
    def __init__(self, text: str) -> None:
        self.text = text
        super().__init__()

class ReadinessDisplay(Static):
    status_text = reactive("--", layout=True)
    acc_text = reactive("--", layout=True)
    hr_text = reactive("--", layout=True)
    dfa_text = reactive("--", layout=True)

    def compose(self) -> ComposeResult:
        with Container(classes="box"):
            yield Label("=== Metrics ===", classes="title")
            yield Label("--", id="r_status")
            yield Label("--", id="r_hr")
            yield Label("--", id="r_dfa")
            yield Label("--", id="r_acc")

    def watch_status_text(self, new_value: str) -> None:
        try:
            self.query_one("#r_status", Label).update(f"Status: {new_value}")
        except Exception:
            pass

    def watch_acc_text(self, new_value: str) -> None:
        try:
            self.query_one("#r_acc", Label).update(f"IMU (X,Y,Z): {new_value}")
        except Exception:
            pass
            
    def watch_hr_text(self, new_value: str) -> None:
        try:
            self.query_one("#r_hr", Label).update(f"Heart Rate: {new_value} BPM")
        except Exception:
            pass
            
    def watch_dfa_text(self, new_value: str) -> None:
        try:
            self.query_one("#r_dfa", Label).update(f"DFA-alpha1: {new_value}")
        except Exception:
            pass

    def update_data(self, status: str, acc_x: Optional[float], acc_y: Optional[float], acc_z: Optional[float], hr: Optional[int] = None, dfa: Optional[float] = None):
        if status in ["DISCONNECTED", "SCANNING"]:
            self.status_text = f"[dim]{status}[/dim]"
        else:
            self.status_text = f"[bold green]{status}[/bold green]"
            
        if acc_x is not None and acc_y is not None and acc_z is not None:
            self.acc_text = f"{acc_x:.2f}, {acc_y:.2f}, {acc_z:.2f} G"
        else:
            self.acc_text = "--"
            
        self.hr_text = f"[bold red]{hr}[/bold red]" if hr else "--"
        
        if dfa is not None:
            if dfa < 0.5:
                color = "red"
            elif dfa < 0.75:
                color = "yellow"
            else:
                color = "green"
            self.dfa_text = f"[bold {color}]{dfa:.2f}[/bold {color}]"
        else:
            self.dfa_text = "--"

class TrendAnalysisDashboard(Static):
    def compose(self) -> ComposeResult:
        with Container(classes="box"):
            yield Label("=== Live Waveform ===", classes="title")
            yield Sparkline(data=[], summary_function=max)
            yield Label("[dim]WAITING FOR DATA[/dim]", id="trend-status")

    def update_data(self, ecg_data_points: list[float]):
        try:
            sparkline = self.query_one(Sparkline)
            status_label = self.query_one("#trend-status", Label)
            if not ecg_data_points:
                sparkline.data = []
                status_label.update("[dim]DISCONNECTED / WAITING[/dim]")
            else:
                sparkline.data = ecg_data_points[-100:]
                status_label.update("[bold green]STREAMING ECG[/bold green]")
        except Exception:
            pass

class DevicePane(Container):
    def __init__(self, device_id: str, device_name: str, **kwargs):
        self.device_id = device_id
        self.device_name = device_name
        super().__init__(id=f"device-{device_id}", classes="device-pane", **kwargs)

    def compose(self) -> ComposeResult:
        yield Label(f"🖥️ {self.device_name}", classes="title device-title")
        yield ReadinessDisplay(id=f"read-{self.device_id}")
        yield TrendAnalysisDashboard(id=f"trend-{self.device_id}")

class MovesenseTerminal(App):
    CSS_PATH = "movesense.tcss"
    TITLE = "Movesense Terminal Lauburu"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.devices: Dict[str, DevicePane] = {}
        self.ecg_buffers: Dict[str, List[float]] = {}
        self.analyzers: Dict[str, "TinyMLHealthAnalyzer"] = {}
        self.windowed_llm_queue = asyncio.Queue(maxsize=50)
        self.ble_worker_running = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Grid(id="main-grid"):
            with Horizontal(id="controls"):
                yield Button("Connect Bluetooth", id="btn_connect_bt", variant="success")
            
            with HorizontalScroll(id="devices-container"):
                pass

            with VerticalScroll(classes="box", id="log-box"):
                yield Label("=== System & LLM Inference Log ===", classes="title")
                yield RichLog(id="telemetry-log", highlight=True, markup=True, max_lines=1000)
        yield Footer()
        
    def on_mount(self) -> None:
        self.log_event("Application initialized.")
        self.log_event("Architecture ready for TinyML per-packet + Meditron3 windowed LLM processing.")
        
        self.start_windowed_llm_worker()
        self.start_tcp_bridge()
        if 'BleakScanner' in globals() and sys.platform == 'darwin':
            self.ble_worker_running = True
            self.run_ble_worker()
            self.log_event("Direct CoreBluetooth BLE scanner initiated.")

    def log_event(self, message: str) -> None:
        try:
            rlog = self.query_one(RichLog)
            rlog.write(Text.from_markup(f"[[yellow]SYS[/yellow]] {message}", emoji=False))
        except Exception:
            pass

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_connect_bt":
            self.log_event("Connect Bluetooth requested.")
            if 'BleakScanner' in globals() and sys.platform == 'darwin' and not self.ble_worker_running:
                self.ble_worker_running = True
                self.run_ble_worker()
                self.log_event("Direct CoreBluetooth BLE worker started.")
            self.log_event("Triggering remote Shizuku on Pixel to start Kai Morich BLE Terminal...")
            import subprocess
            try:
                subprocess.Popen([
                    "ssh", "-p", "8022", "u0_a363@100.114.215.68", 
                    "/data/data/com.termux/files/home/rish -c 'am start -n de.kai_morich.serial_bluetooth_terminal/.MainActivity' 2>&1"
                ])
                self.log_event("Shizuku command dispatched to Pixel. Awaiting TCP bridged connections on port 19003...")
            except Exception as e:
                self.log_event(f"Error triggering Shizuku: {e}")

    @work
    async def start_windowed_llm_worker(self):
        """Worker to run heavier windowed medical LLMs (MedGemma-4B / Llama 70B) via Pipeline Parallelism."""
        import httpx
        
        while True:
            try:
                device_id, window_data = await self.windowed_llm_queue.get()
                while not self.windowed_llm_queue.empty():
                    device_id, window_data = self.windowed_llm_queue.get_nowait()

                self.post_message(LogTelemetry(f"[blue]Windowed LLM (Llama 70B PP):[/blue] Processing {len(window_data)} samples for {device_id}..."))
                
                prompt = (
                    f"Analyze ECG telemetry window ({len(window_data)} samples, recent: {window_data[-8:]}): "
                    f"Assess rhythm, arrhythmia, and signal quality. Clinical Impression:"
                )
                
                payload = {
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 96,
                    "temperature": 0.2
                }
                
                async with httpx.AsyncClient() as client:
                    resp = await client.post("http://127.0.0.1:8090/v1/chat/completions", json=payload, timeout=30.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        clean = data["choices"][0]["message"]["content"].strip()
                    else:
                        clean = "Error: Invalid response from llama-server."
                    
                    # Post to Screen Lens Telemetry hook
                    try:
                        await client.post("http://127.0.0.1:3037/telemetry", json={"device_id": device_id, "analysis": clean}, timeout=2.0)
                    except Exception:
                        pass
                
                lines = []
                for l in clean.splitlines():
                    ls = l.strip()
                    if ls:
                        lines.append(ls)

                summary = " | ".join(lines[:2]) if lines else "Normal Sinus Rhythm"
                if len(summary) > 160:
                    summary = summary[:157] + "..."

                self.post_message(LogTelemetry(f"[blue]Windowed LLM (Llama 70B PP):[/blue] {device_id}: {summary}"))
            except Exception as e:
                self.post_message(LogTelemetry(f"LLM Worker Error: {e}"))
                await asyncio.sleep(1)

    @work
    async def start_tcp_bridge(self):
        """Listen for raw BLE packets bridged over TCP (for Android Termux)."""
        async def handle_client(reader, writer):
            addr = writer.get_extra_info('peername')
            device_id = f"tcp-{addr[1]}"
            self.post_message(LogTelemetry(f"TCP Bridge connected from {addr}. Registering device {device_id}."))
            self.post_message(DeviceTelemetry(device_id, f"Bridged Device {addr[1]}", "status", status="CONNECTED"))
            
            # Using a buffer to handle fragmentation over TCP
            buffer = bytearray()
            while True:
                try:
                    data = await reader.read(1024)
                    if not data:
                        break
                    buffer.extend(data)
                    
                    # We process full packets via tx_handler_raw heuristic and clear what we processed.
                    # Since tx_handler_raw can handle multiple packets in a bytearray and returns nothing,
                    # we will just feed it, but wait, tx_handler_raw processes whatever it finds.
                    # Instead of buffering here endlessly, we just pass the raw data chunk.
                    # The fragmentation heuristic is implemented within tx_handler_raw.
                    # Actually, if a packet is split across two 'reads', tx_handler_raw won't find the end.
                    # It's better to keep the buffer here, and let tx_handler_raw return the number of bytes consumed.
                    
                    # For simplicity, we just pass buffer and let it consume what it can.
                    bytes_consumed = self.tx_handler_raw(device_id, bytes(buffer))
                    if bytes_consumed > 0:
                        buffer = buffer[bytes_consumed:]
                except Exception as e:
                    self.post_message(LogTelemetry(f"TCP stream error: {e}"))
                    break
                    
            self.post_message(LogTelemetry(f"TCP Bridge {addr} disconnected."))
            self.post_message(DeviceTelemetry(device_id, f"Bridged Device {addr[1]}", "status", status="DISCONNECTED"))
            writer.close()

        try:
            server = await asyncio.start_server(handle_client, '0.0.0.0', 19003)
            self.post_message(LogTelemetry("TCP BLE Bridge listening on 0.0.0.0:19003"))
            async with server:
                await server.serve_forever()
        except Exception as e:
            self.post_message(LogTelemetry(f"TCP Bridge error: {e}"))

    def get_or_create_device_pane(self, device_id: str, device_name: str):
        if device_id not in self.devices:
            pane = DevicePane(device_id, device_name)
            self.devices[device_id] = pane
            self.ecg_buffers[device_id] = []
            if TinyMLHealthAnalyzer:
                self.analyzers[device_id] = TinyMLHealthAnalyzer(window_size=50, threshold_z=3.0)
            
            container = self.query_one("#devices-container", HorizontalScroll)
            container.mount(pane)
        return self.devices[device_id]

    def on_device_telemetry(self, message: DeviceTelemetry):
        pane = self.get_or_create_device_pane(message.device_id, message.device_name)
        
        try:
            if message.msg_type == "status":
                readiness = pane.query_one(f"#read-{message.device_id}", ReadinessDisplay)
                readiness.update_data(
                    status=message.data.get("status", "--"),
                    acc_x=message.data.get("acc_x"),
                    acc_y=message.data.get("acc_y"),
                    acc_z=message.data.get("acc_z"),
                    hr=message.data.get("hr"),
                    dfa=message.data.get("dfa")
                )
            elif message.msg_type == "trend":
                trend = pane.query_one(f"#trend-{message.device_id}", TrendAnalysisDashboard)
                ecg_data = message.data.get("ecg_data_points", [])
                trend.update_data(ecg_data)
                

        except Exception as e:
            self.log_event(f"Error updating device pane: {e}")

    def on_log_telemetry(self, message: LogTelemetry) -> None:
        self.log_event(message.text)

    def tx_handler_raw(self, device_id: str, data: bytes) -> int:
        idx = 0
        while idx < len(data) - 1:
            response_type = data[idx]
            reference = data[idx+1]
            
            if response_type == 2 and reference == 99:
                next_idx = len(data)
                for i in range(idx + 2, len(data) - 1):
                    if data[i] == 2 and data[i+1] in (99, 100):
                        next_idx = i
                        break
                
                # If we didn't find the next packet and this chunk isn't complete
                if next_idx == len(data) and len(data) - idx < 6:
                    return idx # Wait for more data
                
                chunk = data[idx:next_idx]
                if len(chunk) >= 6:
                    samples = []
                    for i in range(6, len(chunk), 4):
                        if i + 4 <= len(chunk):
                            sample = struct.unpack('<i', chunk[i:i+4])[0]
                            samples.append(sample)
                    
                    buf = self.ecg_buffers.get(device_id, [])
                    buf.extend(samples)
                    if len(buf) > 200:
                        buf = buf[-200:]
                    self.ecg_buffers[device_id] = buf
                    
                    self.post_message(DeviceTelemetry(device_id, f"Device {device_id}", "trend", ecg_data_points=buf))
                    
                    if len(samples) > 0 and len(buf) % 50 < len(samples):
                        try:
                            self.windowed_llm_queue.put_nowait((device_id, list(buf)))
                        except asyncio.QueueFull:
                            pass
                        except Exception:
                            pass
                    
                    analyzer = self.analyzers.get(device_id)
                    if analyzer:
                        anomalies = analyzer.process_ecg_packet(samples)
                        for a in anomalies:
                            self.post_message(LogTelemetry(f"[red]ECG ANOMALY ({device_id}):[/red] Val={a['value']} Z={a['z_score']:.2f}"))
                idx = next_idx

            elif response_type == 2 and reference == 100:
                next_idx = len(data)
                for i in range(idx + 2, len(data) - 1):
                    if data[i] == 2 and data[i+1] in (99, 100):
                        next_idx = i
                        break
                        
                if next_idx == len(data) and len(data) - idx < 18:
                    return idx # Wait for more data
                    
                chunk = data[idx:next_idx]
                if len(chunk) >= 18:
                    x, y, z = struct.unpack('<fff', chunk[6:18])
                    self.post_message(DeviceTelemetry(device_id, f"Device {device_id}", "status", status="STREAMING", acc_x=x, acc_y=y, acc_z=z))
                    
                    analyzer = self.analyzers.get(device_id)
                    if analyzer:
                        anomalies = analyzer.process_imu_packet(x, y, z)
                        for a in anomalies:
                            self.post_message(LogTelemetry(f"[orange]IMU ANOMALY ({device_id}):[/orange] Mag={a['value']:.2f} Z={a['z_score']:.2f}"))
                idx = next_idx
            else:
                idx += 1
                
        return idx

    @work
    async def run_ble_worker(self) -> None:
        TARGET_DEVICES = {
            'C1DB5043-8F89-88E8-46A3-BBD4ED83FC88': 'Movesense Chest',
            '74:92:BA:11:36:D6': 'Movesense Chest',
            '74:92:ba:11:36:d6': 'Movesense Chest',
            'D2DB5043-8F89-88E8-46A3-BBD4ED83FC88': 'Movesense Bicep',
            'E3DB5043-8F89-88E8-46A3-BBD4ED83FC88': 'Whoop'
        }
        MOVESENSE_TX = "34800002-7185-4d5d-b431-630e7050e8f0"
        MOVESENSE_RX = "34800001-7185-4d5d-b431-630e7050e8f0"

        while True:
            try:
                self.post_message(LogTelemetry("Scanning for BLE medical devices..."))
                devices = await BleakScanner.discover(timeout=5.0)
                
                found = [d for d in devices if d.address in TARGET_DEVICES or d.address.upper() in TARGET_DEVICES]
                if not found:
                    self.post_message(LogTelemetry("No target devices found. Retrying..."))
                    await asyncio.sleep(5)
                    continue
                    
                for device in found:
                    dev_name = TARGET_DEVICES.get(device.address) or TARGET_DEVICES.get(device.address.upper(), "Unknown BLE")
                    self.post_message(LogTelemetry(f"Found {dev_name} ({device.address}). Connecting..."))
                    
                    async def connect_device(dev, d_name):
                        try:
                            async with BleakClient(dev) as client:
                                self.post_message(LogTelemetry(f"{d_name} Connected! Subscribing..."))
                                self.post_message(DeviceTelemetry(dev.address, d_name, "status", status="CONNECTED"))
                                
                                def cb(sender, data):
                                    self.tx_handler_raw(dev.address, data)
                                    
                                await client.start_notify(MOVESENSE_TX, cb)
                                
                                ecg_cmd = bytearray([1, 99]) + bytearray("/Meas/ECG/512", "utf-8")
                                await client.write_gatt_char(MOVESENSE_RX, ecg_cmd, response=True)
                                
                                acc_cmd = bytearray([1, 100]) + bytearray("/Meas/Acc/104", "utf-8")
                                await client.write_gatt_char(MOVESENSE_RX, acc_cmd, response=True)
                                
                                while client.is_connected:
                                    await asyncio.sleep(1)
                        except Exception as e:
                            self.post_message(LogTelemetry(f"{d_name} Disconnected: {e}"))
                            self.post_message(DeviceTelemetry(dev.address, d_name, "status", status="DISCONNECTED"))
                    
                    asyncio.create_task(connect_device(device, dev_name))
                    
                await asyncio.sleep(20)
            except Exception as e:
                self.post_message(LogTelemetry(f"BLE Scanner Error: {e}"))
                await asyncio.sleep(5)

if __name__ == "__main__":
    app = MovesenseTerminal()
    app.run()
