from textual.widgets import Static
from rich.text import Text
from rich.panel import Panel
from rich.align import Align

class MeshTopologyHeatmap(Static):
    DEFAULT_CSS = """
    MeshTopologyHeatmap {
        height: 100%;
        width: 100%;
        background: #0b111c;
        border: round #38bdf8;
    }
    """
    def render(self) -> Panel:
        heatmap_text = """
[bold cyan]L1 Mac Mini M4[/bold cyan] (21.6G VRAM) ──TB4 (0.2ms)──▶ [bold magenta]L2 Mac Pro Intel[/bold magenta] (14.0G VRAM)
       │                                            │
  Wi-Fi 7 (1.5ms)                               Wi-Fi 5 (12ms)
       │                                            │
       ▼                                            ▼
[bold green]L3 Linux Ryzen[/bold green] (13.8G VRAM) ◀──Tailscale──▶ [bold yellow]L4 Linux Tablet[/bold yellow] (6.5G VRAM)
       │
     Wi-Fi 6
       │
       ▼
[bold orange1]L6 Pixel 10 Pro[/bold orange1] (12.5G VRAM) ◀──ADB USB──▶ [bold red]L7 Galaxy S20[/bold red] (9.0G VRAM)
"""
        return Panel(
            Align.center(Text.from_markup(heatmap_text), vertical="middle"),
            title="[bold white]🌐 7-Layer Mesh Topology Heatmap[/bold white]",
            border_style="cyan"
        )
