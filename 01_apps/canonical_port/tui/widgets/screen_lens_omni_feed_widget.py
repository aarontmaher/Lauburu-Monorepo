import asyncio
import zmq
import zmq.asyncio
import json
from textual.widgets import RichLog
from textual.app import App
from rich.text import Text

class ScreenLensOmniFeedWidget(RichLog):
    
    DEFAULT_CSS = """
    ScreenLensOmniFeedWidget {
        border: round magenta;
        height: 100%;
        width: 35%;
        background: $surface;
    }
    """
    
    def on_mount(self):
        self.border_title = "Omni-Lens Shadow Feed (ZMQ 5555)"
        self.write("[bold magenta]👁️ Omni-Lens Interceptor Active[/bold magenta]")
        
        # Start ZMQ subscriber
        self.context = zmq.asyncio.Context()
        self.subscriber = self.context.socket(zmq.SUB)
        # Connect to the Unified Broker's PUB port
        self.subscriber.connect("tcp://127.0.0.1:5555")
        
        # Subscribe to Lens-specific topics
        self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "LENS.DRAFT_ACTION")
        self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "LENS.OBS.ACCESSIBILITY")
        self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "LENS.INTENT.VOICE")
        self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "LENS.APPROVED_ACTION")
        self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "LENS.REJECTED_ACTION")
        
        asyncio.create_task(self.zmq_listener())
        
    async def zmq_listener(self):
        self.write("[dim]▶ Listening for Omni-Lens Shadow AI Events...[/dim]\n")
        while True:
            try:
                msg = await self.subscriber.recv_multipart()
                topic = msg[0].decode('utf-8')
                payload = json.loads(msg[1].decode('utf-8'))
                
                if topic == "LENS.INTENT.VOICE":
                    self.write(f"[bold cyan]🎙️ Whisper Intent:[/bold cyan] {payload.get('intent_text')}")
                elif topic == "LENS.OBS.ACCESSIBILITY":
                    self.write(f"[dim]📱 Pixel XML DOM Scraped (Size: {len(payload.get('dom_tree', ''))} bytes)[/dim]")
                elif topic == "LENS.DRAFT_ACTION":
                    action = payload.get("action", "unknown")
                    self.write(f"[yellow]⚡ Draft Action:[/yellow] {action}")
                elif topic == "LENS.APPROVED_ACTION":
                    action = payload.get("action", "unknown")
                    self.write(f"[bold green]✅ Shadow AI Approved:[/bold green] {action}")
                elif topic == "LENS.REJECTED_ACTION":
                    action = payload.get("action", "unknown")
                    reason = payload.get("reason", "Hallucination")
                    self.write(f"[bold red]❌ Shadow AI Veto:[/bold red] {action} (Reason: {reason})")
                    
            except Exception as e:
                self.write(f"[red]ZMQ Error: {e}[/red]")
                await asyncio.sleep(2)
                
    def on_unmount(self):
        self.subscriber.close()
        self.context.term()
