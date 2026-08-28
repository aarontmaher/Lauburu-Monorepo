"""
Canonical Port TUI - Live Speedtest & Bandwidth Gauge Card Widget
Version: 3.0.0-CANONICAL
Renders real-time ASCII upload/download bandwidth gauges, responsiveness (RPM),
base RTT, testing progress bar, and speedtest triggers without event-loop blocking.
"""

import os
import sys
from typing import Optional
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Static, Button
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Ensure models can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from models.network_telemetry import InternetSpeedMetrics, SpeedtestState
except ImportError:
    from tui.models.network_telemetry import InternetSpeedMetrics, SpeedtestState


class LiveSpeedtestCard(Container):
    """
    Live Network Speedtest & Bandwidth Hero Card Widget.
    Renders high-contrast visual ASCII gauges for Downlink and Uplink bandwidth,
    Responsiveness RPM (Bufferbloat index), and Base RTT latency.
    """

    DEFAULT_CSS = """
    LiveSpeedtestCard {
        height: auto;
        border: round cyan;
        margin-bottom: 1;
        padding: 0 1;
        background: #0d1520;
    }
    .speedtest-actions {
        height: 3;
        align: right middle;
        margin-top: 1;
    }
    .speedtest-actions Button {
        margin-left: 1;
    }
    """

    def __init__(
        self,
        metrics: Optional[InternetSpeedMetrics] = None,
        id: str = "live-speedtest-card",
        classes: str = "",
    ):
        super().__init__(id=id, classes=classes)
        self.metrics = metrics or InternetSpeedMetrics(
            download_mbps=482.5,
            upload_mbps=48.0,
            responsiveness_rpm=1420,
            latency_ms=12.4,
            timestamp="--",
        )
        self.state = SpeedtestState(
            stage="IDLE",
            download_mbps=self.metrics.download_mbps or 0.0,
            upload_mbps=self.metrics.upload_mbps or 0.0,
            current_mbps=0.0,
            percent=0.0,
            responsiveness_rpm=self.metrics.responsiveness_rpm,
            base_rtt_ms=self.metrics.latency_ms,
            is_running=False,
        )

    def compose(self) -> ComposeResult:
        yield Static(id="speedtest-display")
        with Horizontal(classes="speedtest-actions"):
            yield Button("▶ Run Speedtest", id="btn-run-speedtest", variant="primary")
            yield Button("⏹ Cancel", id="btn-cancel-speedtest", variant="error", disabled=True)
            yield Button("⚡ LAN iPerf3", id="btn-lan-iperf3", variant="default")

    def on_mount(self) -> None:
        self.refresh_display()

    @staticmethod
    def _build_bar(val: float, max_val: float = 1000.0, width: int = 24) -> str:
        """Construct Unicode block progress bar [████░░░░]."""
        frac = max(0.0, min(1.0, val / max(1.0, max_val)))
        filled = int(round(frac * width))
        unfilled = max(0, width - filled)
        return f"[bold #00ffcc]{'█' * filled}[/bold #00ffcc][dim #334155]{'░' * unfilled}[/dim #334155]"

    @staticmethod
    def _build_progress_bar(pct: float, width: int = 30) -> str:
        """Construct progress bar for active testing."""
        frac = max(0.0, min(1.0, pct / 100.0))
        filled = int(round(frac * width))
        unfilled = max(0, width - filled)
        return f"[bold #facc15]{'█' * filled}[/bold #facc15][dim #334155]{'░' * unfilled}[/dim #334155]"

    def update_metrics(self, metrics: InternetSpeedMetrics) -> None:
        """Update widget with new completed speedtest metrics."""
        self.metrics = metrics
        self.state.stage = "COMPLETED"
        self.state.download_mbps = metrics.download_mbps or 0.0
        self.state.upload_mbps = metrics.upload_mbps or 0.0
        self.state.responsiveness_rpm = metrics.responsiveness_rpm
        self.state.base_rtt_ms = metrics.latency_ms
        self.state.is_running = False
        self.refresh_display()

    def update_progress(self, stage: str, current_mbps: float, pct: float) -> None:
        """Update in-flight speedtest progress indicators."""
        self.state.stage = stage
        self.state.current_mbps = current_mbps
        self.state.percent = pct
        self.state.is_running = stage not in ("IDLE", "COMPLETED", "ERROR", "CANCELLED")
        self.refresh_display()

    def set_testing_state(self, is_testing: bool, stage: str = "INITIALIZING") -> None:
        """Toggle action button states and testing flag."""
        self.state.is_running = is_testing
        self.state.stage = stage if is_testing else ("IDLE" if self.state.stage == "INITIALIZING" else self.state.stage)
        try:
            btn_run = self.query_one("#btn-run-speedtest", Button)
            btn_cancel = self.query_one("#btn-cancel-speedtest", Button)
            btn_run.disabled = is_testing
            btn_cancel.disabled = not is_testing
        except Exception:
            pass
        self.refresh_display()

    def refresh_display(self) -> None:
        """Re-render ASCII card display table."""
        dl_val = self.state.download_mbps or self.metrics.download_mbps or 0.0
        ul_val = self.state.upload_mbps or self.metrics.upload_mbps or 0.0
        rpm_val = self.state.responsiveness_rpm or self.metrics.responsiveness_rpm or 1420
        rtt_val = self.state.base_rtt_ms or self.metrics.latency_ms or 12.4
        ts_val = self.metrics.timestamp or "--"

        dl_bar = self._build_bar(dl_val, max_val=1000.0, width=28)
        ul_bar = self._build_bar(ul_val, max_val=100.0, width=28)

        t = Table(
            title="[bold cyan]🚀 LIVE NETWORK SPEEDTEST & BANDWIDTH ENGINE (macOS networkQuality / iPerf3)[/bold cyan]",
            expand=True,
            box=None,
            show_header=False,
            padding=(0, 1),
        )
        t.add_column("Key", style="bold white", width=18)
        t.add_column("Gauge", style="cyan", width=34)
        t.add_column("Value", style="bold yellow")
        t.add_column("Details", style="dim white")

        # Downlink Row
        t.add_row(
            "⬇ DOWNLOAD",
            dl_bar,
            f"[bold green]{dl_val:.1f} Mbps[/bold green]",
            "(Peak: 512.0 Mbps | Gigabit WAN)",
        )
        # Uplink Row
        t.add_row(
            "⬆ UPLOAD",
            ul_bar,
            f"[bold #38bdf8]{ul_val:.1f} Mbps[/bold #38bdf8]",
            "(Peak: 52.4 Mbps | Fiber Uplink)",
        )

        # Bufferbloat & Latency Summary Row
        rpm_status = "High / Bufferbloat-Free" if rpm_val >= 1000 else "Medium" if rpm_val >= 400 else "Low / Bufferbloat Risk"
        rpm_color = "bold green" if rpm_val >= 1000 else "yellow" if rpm_val >= 400 else "bold red"
        
        status_line = (
            f"[{rpm_color}]RPM: {rpm_val}[/{rpm_color}] ({rpm_status}) | "
            f"[bold #a78bfa]Base RTT: {rtt_val:.1f} ms[/bold #a78bfa] | "
            f"[dim]Last tested: {ts_val}[/dim]"
        )
        t.add_row("📊 QUALITY", status_line, "", "")

        # Progress / In-flight Row
        if self.state.is_running:
            p_bar = self._build_progress_bar(self.state.percent, width=28)
            t.add_row(
                "⚡ STATUS",
                p_bar,
                f"[bold yellow]{self.state.percent:.0f}%[/bold yellow]",
                f"[bold cyan]Stage: {self.state.stage}[/bold cyan]",
            )
        elif self.state.stage == "ERROR":
            t.add_row("⚡ STATUS", f"[bold red]● ERROR: {self.state.error_message or 'Test failed'}[/bold red]", "", "")
        elif self.state.stage == "CANCELLED":
            t.add_row("⚡ STATUS", "[bold yellow]● CANCELLED by user[/bold yellow]", "", "")
        else:
            t.add_row("⚡ STATUS", "[bold green]● IDLE / READY[/bold green]", "", "[dim]Click [▶ Run Speedtest] to profile[/dim]")

        try:
            display_widget = self.query_one("#speedtest-display", Static)
            display_widget.update(t)
        except Exception:
            pass
