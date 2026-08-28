"""
Canonical Port TUI - Harmonized Master Header Bar Widget
Version: 4.0.0-HARMONIZED
Combines Track Alpha's 7-Node Mesh Health Pills, Pooled RAM/VRAM Gauge,
and Track Beta's 8-Engine Selector, live TTFT / tok/s, and WAN Route Badge.
"""

from typing import Dict, List, Optional, Tuple, Any
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, Select
from textual.reactive import reactive
from textual.message import Message
from rich.text import Text
from rich.panel import Panel
from rich.box import ROUNDED, SIMPLE

try:
    from models.blackboard_models import BlackboardTelemetryState, HardwareNodeState
    from services.blackboard_store import blackboard_store
except ImportError:
    from tui.models.blackboard_models import BlackboardTelemetryState, HardwareNodeState
    from tui.services.blackboard_store import blackboard_store


class CanonicalEngineChanged(Message):
    """Event emitted when active inference engine is switched via header dropdown or hotkey."""
    def __init__(
        self,
        engine_name: str,
        display_name: str = "",
        previous_engine: str = "",
        source: str = "ui"
    ):
        super().__init__()
        self.engine_name = engine_name
        self.engine = engine_name  # Compatibility alias
        self.display_name = display_name or engine_name
        self.previous_engine = previous_engine
        self.source = source  # "dropdown", "hotkey", "repl", "api"


# Aliases for backward compatibility
InferenceEngineChanged = CanonicalEngineChanged
BetaEngineChanged = CanonicalEngineChanged


class CanonicalHeaderBar(Vertical):
    """
    Unified Global Top Header Bar:
    - Row 1: 7-Node Physical Mesh Health Pill Matrix (L1..L7 + GW) + Pooled RAM/VRAM Meter + WAN Route Badge
    - Row 2: Dynamic 8-Engine Selector Dropdown ([Ctrl+E] / [F2]) + Real-time TTFT / tok/s metrics
    """

    DEFAULT_CSS = """
    CanonicalHeaderBar {
        height: auto;
        min-height: 3;
        width: 100%;
        background: #080e1a;
        border-bottom: solid #1e293b;
        padding: 0 1;
    }
    #canonical-header-top-row {
        height: auto;
        min-height: 1;
        width: 100%;
        layout: horizontal;
        align: left middle;
    }
    #canonical-pills-and-memory {
        width: 1fr;
        height: auto;
    }
    #canonical-header-bottom-row {
        height: auto;
        min-height: 2;
        width: 100%;
        layout: horizontal;
        align: left middle;
        background: #0b111c;
        padding: 0;
    }
    #canonical-title-badge {
        width: auto;
        min-width: 26;
        color: #00ffcc;
        text-style: bold;
        padding-top: 0;
    }
    #canonical-engine-select-container {
        width: 38;
        height: 1;
        align: left middle;
    }
    #canonical-engine-select {
        width: 36;
        height: 1;
        background: #0f172a;
        color: #38bdf8;
        border: none;
    }
    #canonical-engine-metrics {
        width: 1fr;
        color: #94a3b8;
        text-align: right;
    }
    """

    ENGINES: List[str] = [
        "auto",
        "llama_rpc",
        "exo",
        "accelerate",
        "petals",
        "gemini",
        "cloudflare",
        "julien",
    ]

    ENGINE_OPTIONS: List[Tuple[str, str]] = [
        ("🤖 AUTO (Dynamic TTFT)", "auto"),
        ("🦙 LLAMA.CPP (GGML-RPC)", "llama_rpc"),
        ("🪐 EXO (Ring P2P)", "exo"),
        ("⚡ ACCELERATE (Multi-GPU)", "accelerate"),
        ("🌸 PETALS (DHT Swarm)", "petals"),
        ("♊ GEMINI (Google / CF Gateway)", "gemini"),
        ("☁️ CLOUDFLARE (Workers AI)", "cloudflare"),
        ("👑 JULIEN (Ultra Plan API)", "julien"),
    ]

    ENGINE_NAMES: Dict[str, str] = {
        "auto": "🤖 AUTO (Dynamic TTFT)",
        "llama_rpc": "🦙 LLAMA.CPP (GGML-RPC)",
        "exo": "🪐 EXO (Ring P2P)",
        "accelerate": "⚡ ACCELERATE (Multi-GPU)",
        "petals": "🌸 PETALS (DHT Swarm)",
        "gemini": "♊ GEMINI (Google / CF Gateway)",
        "cloudflare": "☁️ CLOUDFLARE (Workers AI)",
        "julien": "👑 JULIEN (Ultra Plan API)",
    }

    active_engine: reactive[str] = reactive("auto")
    ttft_ms: reactive[float] = reactive(18.5)
    tok_per_sec: reactive[float] = reactive(64.2)
    engine_status: reactive[str] = reactive("ONLINE")

    def __init__(self, active_engine: str = "auto", **kwargs):
        super().__init__(**kwargs)
        self.active_engine = active_engine if active_engine in self.ENGINES else "auto"
        self._last_snapshot: Optional[BlackboardTelemetryState] = None

    def compose(self) -> ComposeResult:
        # Row 1: Node Health Pills, Pooled RAM/VRAM, WAN
        with Horizontal(id="canonical-header-top-row"):
            yield Static(id="canonical-pills-and-memory")

        # Row 2: Title, Engine Selector, Live Latency Metrics
        with Horizontal(id="canonical-header-bottom-row"):
            yield Static("⚡ [bold cyan]LAUBURU MESH[/bold cyan] [dim][7-NODE][/dim]", id="canonical-title-badge")
            with Horizontal(id="canonical-engine-select-container"):
                yield Select(
                    options=self.ENGINE_OPTIONS,
                    value=self.active_engine,
                    allow_blank=False,
                    id="canonical-engine-select"
                )
            yield Static(self._build_metrics_text(), id="canonical-engine-metrics")

    def on_mount(self) -> None:
        """Initial render of hardware pills and memory meters on mount."""
        try:
            snapshot = blackboard_store.get_snapshot(force_refresh=False)
            self.update_view(snapshot)
        except Exception:
            pass

    def _build_pills_and_memory_markup(self, snapshot: Optional[BlackboardTelemetryState]) -> Text:
        if not snapshot:
            return Text.from_markup("[dim]● Loading mesh hardware matrix...[/dim]")

        hw = snapshot.layer_1_hardware
        net = snapshot.layer_0_networking
        nodes = hw.nodes

        # 1. 7-Node Physical Mesh Health Pill Matrix + GW
        node_pills: List[str] = []
        ordered_ids = ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "GW"]
        node_map = {n.node_id: n for n in nodes}

        for nid in ordered_ids:
            if nid in node_map:
                n = node_map[nid]
                st = (n.status or "OFFLINE").upper()
                if st in ("ONLINE", "ACTIVE"):
                    color = "bold green"
                    dot = "●"
                elif st in ("STANDBY", "IDLE"):
                    color = "bold yellow"
                    dot = "◐"
                else:
                    color = "bold red"
                    dot = "○"
                node_name_clean = n.name.split("_")[0] if n.name else nid
                node_pills.append(f"[{color}]{dot} {nid}:{node_name_clean}[/{color}]")
            else:
                if nid == "GW":
                    node_pills.append("[bold cyan]● GW:GL.iNet[/bold cyan]")
                else:
                    node_pills.append(f"[dim]○ {nid}:OFFLINE[/dim]")

        pills_str = " ".join(node_pills)

        # 2. Pooled RAM / VRAM Meter
        total_ram = hw.total_ram_gb or 108.0
        used_ram = hw.pooled_ram_used_gb or 48.2
        ram_pct = (used_ram / total_ram) * 100.0 if total_ram > 0 else 0.0

        total_vram = hw.total_vram_gb or 82.8
        used_vram = hw.pooled_vram_used_gb or 39.0
        vram_pct = (used_vram / total_vram) * 100.0 if total_vram > 0 else 0.0

        ram_bar_filled = max(0, min(8, int(ram_pct / 12.5)))
        ram_bar = "█" * ram_bar_filled + "░" * (8 - ram_bar_filled)

        vram_bar_filled = max(0, min(8, int(vram_pct / 12.5)))
        vram_bar = "█" * vram_bar_filled + "░" * (8 - vram_bar_filled)

        ram_meter = f"[bold cyan]RAM:[/] [green]{ram_bar}[/] {used_ram:.1f}/{total_ram:.1f}G ({ram_pct:.0f}%)"
        vram_meter = f"[bold magenta]VRAM:[/] [magenta]{vram_bar}[/] {used_vram:.1f}/{total_vram:.1f}G ({vram_pct:.0f}%)"

        # 3. Active WAN Route Badge
        active_wan = "en0 (Wi-Fi 7)"
        wan_rtt = "12.4ms"
        wan_color = "bright_green"
        if net and net.wan_routes:
            active_route = next((r for r in net.wan_routes if r.status == "ACTIVE"), net.wan_routes[0])
            active_wan = active_route.interface
            wan_rtt = f"{active_route.rtt_ms:.1f}ms" if active_route.rtt_ms is not None else "--"
            wan_color = "bright_green" if active_route.status == "ACTIVE" else "yellow"

        wan_badge = f"[{wan_color}]🌐 WAN: {active_wan} ({wan_rtt})[/{wan_color}]"

        full_line = f"{pills_str}  │  {ram_meter}  │  {vram_meter}  │  {wan_badge}"
        return Text.from_markup(full_line)

    def _build_metrics_text(self) -> Text:
        t = Text()
        t.append("Active Engine: ", style="dim")
        t.append(f"[{self.active_engine.upper()}] ", style="bold #00ffcc")
        t.append("│ TTFT: ", style="dim")
        t.append(f"{self.ttft_ms:.1f}ms ", style="bold #38bdf8")
        t.append("│ Rate: ", style="dim")
        t.append(f"{self.tok_per_sec:.1f} t/s ", style="bold #a855f7")
        t.append("│ Status: ", style="dim")
        st_style = "bold green" if "ONLINE" in self.engine_status.upper() or "ACTIVE" in self.engine_status.upper() else "bold yellow"
        t.append(f"[{self.engine_status}] ", style=st_style)
        t.append("[Ctrl+E/F2 Cycle]", style="dim italic")
        return t

    def update_view(
        self,
        snapshot: Optional[BlackboardTelemetryState] = None,
        ttft_ms: Optional[float] = None,
        tok_per_sec: Optional[float] = None,
        engine_status: Optional[str] = None
    ) -> None:
        """Update top hardware pills, memory bars, and inference telemetry."""
        if snapshot:
            self._last_snapshot = snapshot
        if ttft_ms is not None:
            self.ttft_ms = ttft_ms
        if tok_per_sec is not None:
            self.tok_per_sec = tok_per_sec
        if engine_status is not None:
            self.engine_status = engine_status

        try:
            pills_widget = self.query_one("#canonical-pills-and-memory", Static)
            if pills_widget:
                pills_widget.update(self._build_pills_and_memory_markup(self._last_snapshot))
        except Exception:
            pass

        try:
            metrics_widget = self.query_one("#canonical-engine-metrics", Static)
            if metrics_widget:
                metrics_widget.update(self._build_metrics_text())
        except Exception:
            pass

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle user changing engine via top dropdown."""
        if event.value != Select.BLANK and str(event.value) != self.active_engine:
            prev = self.active_engine
            self.active_engine = str(event.value)
            disp = self.ENGINE_NAMES.get(self.active_engine, self.active_engine)
            self.post_message(
                CanonicalEngineChanged(
                    engine_name=self.active_engine,
                    display_name=disp,
                    previous_engine=prev,
                    source="dropdown"
                )
            )

    def cycle_engine(self, delta: int = 1) -> str:
        """Cycle through all 8 engines in canonical order."""
        try:
            idx = self.ENGINES.index(self.active_engine)
        except ValueError:
            idx = 0
        next_idx = (idx + delta) % len(self.ENGINES)
        prev = self.active_engine
        self.active_engine = self.ENGINES[next_idx]

        try:
            sel = self.query_one("#canonical-engine-select", Select)
            if sel:
                sel.value = self.active_engine
        except Exception:
            pass

        disp = self.ENGINE_NAMES.get(self.active_engine, self.active_engine)
        self.post_message(
            CanonicalEngineChanged(
                engine_name=self.active_engine,
                display_name=disp,
                previous_engine=prev,
                source="hotkey"
            )
        )
        return self.active_engine

    def set_engine(self, engine_name: str) -> None:
        """Set active engine programmatically and synchronize dropdown."""
        if engine_name in self.ENGINES and engine_name != self.active_engine:
            prev = self.active_engine
            self.active_engine = engine_name
            try:
                sel = self.query_one("#canonical-engine-select", Select)
                if sel and sel.value != self.active_engine:
                    sel.value = self.active_engine
            except Exception:
                pass
            disp = self.ENGINE_NAMES.get(self.active_engine, self.active_engine)
            self.post_message(
                CanonicalEngineChanged(
                    engine_name=self.active_engine,
                    display_name=disp,
                    previous_engine=prev,
                    source="api"
                )
            )
