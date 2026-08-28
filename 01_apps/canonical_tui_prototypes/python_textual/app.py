#!/usr/bin/env python3
"""Canonical Lauburu Python Textual Cloud API Quota & Telemetry HUD.

Monitors real-time cloud API quota state and mesh telemetry with reactive updates,
safe flock concurrency, and headless verification mode.
"""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Label,
    ProgressBar,
    RichLog,
    Static,
)

DEFAULT_STATE_PATH = Path(
    os.getenv(
        "LAUBURU_QUOTA_STATE_PATH",
        "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/cloud_api_quota_state.json",
    )
)


class QuotaStateReader:
    """Safe reader for cloud API quota state with file locking and retry backoff."""

    def __init__(self, state_path: Path):
        self.state_path = state_path
        self.lock_path = state_path.with_suffix(".lock")
        self.last_valid_state: Optional[Dict[str, Any]] = None

    def read_state(self, retries: int = 3) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Read and validate the quota state file with exponential backoff."""
        if not self.state_path.exists():
            return None, f"State file does not exist: {self.state_path}"

        for attempt in range(retries):
            try:
                # Attempt shared lock on lockfile if present
                lock_fd = None
                if self.lock_path.exists():
                    try:
                        lock_fd = open(self.lock_path, "r")
                        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                    except (IOError, OSError):
                        pass

                with open(self.state_path, "r", encoding="utf-8") as f:
                    content = f.read()

                if lock_fd:
                    try:
                        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                        lock_fd.close()
                    except Exception:
                        pass

                if not content.strip():
                    raise ValueError("State file is empty")

                data = json.loads(content)
                is_valid, err = self.validate_schema(data)
                if not is_valid:
                    raise ValueError(f"Schema validation failed: {err}")

                self.last_valid_state = data
                return data, None

            except Exception as ex:
                if attempt < retries - 1:
                    time.sleep(0.05 * (2**attempt))
                    continue
                if self.last_valid_state is not None:
                    return self.last_valid_state, f"Using cached state (read error: {ex})"
                return None, f"Failed to read state after {retries} attempts: {ex}"

        return self.last_valid_state, "Unknown read failure"

    @staticmethod
    def validate_schema(data: Any) -> Tuple[bool, Optional[str]]:
        """Validate that the state conforms to the canonical Quota State Schema."""
        if not isinstance(data, dict):
            return False, "Root state must be a JSON object"

        for req in ("version", "providers", "metrics"):
            if req not in data:
                return False, f"Missing required root field: '{req}'"

        providers = data.get("providers")
        if not isinstance(providers, dict) or not providers:
            return False, "'providers' must be a non-empty object"

        for p_id, p_info in providers.items():
            if not isinstance(p_info, dict):
                return False, f"Provider '{p_id}' must be an object"
            for p_req in ("daily_limit", "used_today", "remaining_pct", "status"):
                if p_req not in p_info:
                    return False, f"Provider '{p_id}' missing required field: '{p_req}'"

        metrics = data.get("metrics")
        if not isinstance(metrics, dict):
            return False, "'metrics' must be an object"
        for m_req in ("total_tasks_routed", "total_lora_samples_harvested"):
            if m_req not in metrics:
                return False, f"Metrics missing required field: '{m_req}'"

        return True, None


class MetricCard(Static):
    """HUD Metric Card widget with Title and Value."""

    def __init__(self, title: str, value: str, metric_id: str, border_color: str = "#1e293b"):
        super().__init__(id=metric_id)
        self.title_text = title
        self.value_text = value
        self.border_color = border_color

    def compose(self) -> ComposeResult:
        yield Label(self.title_text, classes="metric-title")
        yield Label(self.value_text, id=f"{self.id}-val", classes="metric-val")

    def update_value(self, val: str) -> None:
        try:
            self.query_one(f"#{self.id}-val", Label).update(val)
        except Exception:
            pass


class ProviderGauge(Static):
    """Visual progress gauge for a single provider."""

    def __init__(self, provider_id: str, name: str, used: int, limit: int, remaining_pct: float):
        super().__init__(id=f"gauge-{provider_id}")
        self.provider_id = provider_id
        self.provider_name = name
        self.used = used
        self.limit = limit
        self.remaining_pct = remaining_pct

    def compose(self) -> ComposeResult:
        limit_str = "∞" if self.limit >= 999999 else str(self.limit)
        yield Label(f"[bold cyan]{self.provider_name}[/] ({self.used} / {limit_str})", id=f"lbl-{self.provider_id}")
        yield ProgressBar(total=100, show_eta=False, id=f"pbar-{self.provider_id}")

    def update_progress(self, used: int, limit: int, remaining_pct: float) -> None:
        self.used = used
        self.limit = limit
        self.remaining_pct = remaining_pct
        limit_str = "∞" if self.limit >= 999999 else str(self.limit)
        try:
            self.query_one(f"#lbl-{self.provider_id}", Label).update(
                f"[bold cyan]{self.provider_name}[/] ({self.used} / {limit_str})"
            )
            pct_val = max(0.0, min(100.0, remaining_pct * 100.0))
            self.query_one(f"#pbar-{self.provider_id}", ProgressBar).progress = pct_val
        except Exception:
            pass


class QuotaTuiApp(App):
    """Canonical Lauburu Python Textual Quota & Telemetry TUI."""

    TITLE = "LAUBURU MESH — CLOUD API QUOTA COMMAND"
    SUB_TITLE = "Sovereign Quota Optimizer & LoRA Training Telemetry"

    CSS = """
    Screen {
        background: #070b12;
        color: #e2e8f0;
    }
    Header {
        dock: top;
        height: 1;
        background: #0b111c;
        color: #00ffcc;
    }
    #metrics-row {
        height: 4;
        layout: horizontal;
        margin: 1 1 0 1;
    }
    MetricCard {
        width: 1fr;
        height: 100%;
        border: solid #1e293b;
        background: #0d1526;
        padding: 0 1;
        content-align: center middle;
        text-align: center;
    }
    .metric-title {
        color: #94a3b8;
        text-style: bold;
        text-align: center;
    }
    .metric-val {
        color: #38bdf8;
        text-style: bold;
        text-align: center;
    }
    #main-body {
        height: 1fr;
        margin: 0 1;
    }
    #table-pane {
        width: 62%;
        border: solid #1e293b;
        background: #090e17;
        margin-right: 1;
    }
    #gauge-pane {
        width: 38%;
        border: solid #1e293b;
        background: #090e17;
        padding: 1;
    }
    .section-header {
        color: #38bdf8;
        text-style: bold;
        padding-bottom: 1;
    }
    #gauges-container {
        height: 1fr;
    }
    #system-log {
        height: 5;
        border: solid #1e293b;
        background: #05080e;
        margin: 0 1 1 1;
    }
    Footer {
        dock: bottom;
        height: 1;
        background: #0b111c;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("r", "refresh_data", "Refresh", priority=True),
        Binding("p", "toggle_pause", "Pause/Resume"),
        Binding("v", "verify_and_exit", "Verify & Exit"),
    ]

    quota_data = reactive(dict)
    is_paused = reactive(False)

    def __init__(
        self,
        state_path: Path,
        poll_interval: float = 2.0,
        verify_mode: bool = False,
        timeout: Optional[float] = None,
    ):
        super().__init__()
        self.state_path = state_path
        self.poll_interval = poll_interval
        self.verify_mode = verify_mode
        self.timeout = timeout
        self.reader = QuotaStateReader(state_path)
        self.start_time = time.time()
        self.gauge_widgets: Dict[str, ProviderGauge] = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="metrics-row"):
            yield MetricCard("Total Tasks", "0", "m-tasks")
            yield MetricCard("Cloud Succeeded", "0", "m-cloud")
            yield MetricCard("Mesh Fallbacks", "0", "m-fallback")
            yield MetricCard("LoRA Harvested", "0", "m-lora")
        with Horizontal(id="main-body"):
            with Vertical(id="table-pane"):
                yield Label("  Active Providers Quota Matrix", classes="section-header")
                yield DataTable(id="quota-table")
            with Vertical(id="gauge-pane"):
                yield Label("Provider Quota Remaining", classes="section-header")
                yield VerticalScroll(id="gauges-container")
        yield RichLog(id="system-log", max_lines=50, highlight=True, markup=True)
        yield Footer()

    async def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns(
            "Provider", "Daily Limit", "Used Today", "Rem %", "Avg Latency", "Failures", "Status"
        )

        log = self.query_one(RichLog)
        log.write(f"[dim green]✓ Quota HUD mounted. Reading from {self.state_path}[/]")

        # Perform initial state load
        await self.poll_quota()

        if self.verify_mode:
            log.write("[bold green]✓ Headless Verification Mode: State successfully loaded.[/]")
            self.exit(return_code=0)
            return

        # Start background polling timer
        self.set_interval(self.poll_interval, self.poll_quota)

        if self.timeout and self.timeout > 0:
            self.set_timer(self.timeout, self.action_timeout_exit)

    async def poll_quota(self) -> None:
        if self.is_paused and not self.verify_mode:
            return

        data, err = await asyncio.to_thread(self.reader.read_state)
        log = self.query_one(RichLog)

        if err:
            log.write(f"[yellow]⚠ State notice: {err}[/]")

        if data:
            self.quota_data = data
            self.update_ui(data)

    def update_ui(self, data: Dict[str, Any]) -> None:
        metrics = data.get("metrics", {})
        self.query_one("#m-tasks", MetricCard).update_value(str(metrics.get("total_tasks_routed", 0)))
        self.query_one("#m-cloud", MetricCard).update_value(
            str(metrics.get("cloud_tasks_succeeded", 0))
        )
        self.query_one("#m-fallback", MetricCard).update_value(
            str(metrics.get("local_mesh_fallback_count", 0))
        )
        self.query_one("#m-lora", MetricCard).update_value(
            str(metrics.get("total_lora_samples_harvested", 0))
        )

        table = self.query_one(DataTable)
        table.clear()
        providers = data.get("providers", {})

        gauges_container = self.query_one("#gauges-container", VerticalScroll)

        for p_id, p_info in sorted(providers.items()):
            limit = p_info.get("daily_limit", 0)
            used = p_info.get("used_today", 0)
            rem_pct = p_info.get("remaining_pct", 1.0)
            avg_lat = p_info.get("avg_latency_ms", 0.0)
            fails = p_info.get("consecutive_failures", 0)
            status = str(p_info.get("status", "healthy")).lower()

            limit_str = "∞" if limit >= 999999 else str(limit)
            rem_str = f"{rem_pct * 100.0:.1f}%"
            lat_str = f"{avg_lat:.1f} ms"

            if status == "healthy":
                status_pill = "[bold green]● HEALTHY[/]"
            elif status in ("in_cooldown", "cooldown"):
                status_pill = "[bold yellow]⏱ COOLDOWN[/]"
            elif status == "degraded":
                status_pill = "[bold red]🔻 DEGRADED[/]"
            elif status == "exhausted":
                status_pill = "[dim]⛔ EXHAUSTED[/]"
            else:
                status_pill = f"[bold cyan]● {status.upper()}[/]"

            table.add_row(
                p_id,
                limit_str,
                str(used),
                rem_str,
                lat_str,
                str(fails),
                Text.from_markup(status_pill),
            )

            # Update or create gauge
            if p_id in self.gauge_widgets:
                self.gauge_widgets[p_id].update_progress(used, limit, rem_pct)
            else:
                gauge = ProviderGauge(p_id, p_id, used, limit, rem_pct)
                self.gauge_widgets[p_id] = gauge
                gauges_container.mount(gauge)

    def action_refresh_data(self) -> None:
        asyncio.create_task(self.poll_quota())
        self.query_one(RichLog).write("[cyan]⟳ Manual refresh triggered.[/]")

    def action_toggle_pause(self) -> None:
        self.is_paused = not self.is_paused
        status = "PAUSED" if self.is_paused else "RESUMED"
        self.query_one(RichLog).write(f"[yellow]⏸ Polling {status}.[/]")

    def action_verify_and_exit(self) -> None:
        self.exit(return_code=0)

    def action_timeout_exit(self) -> None:
        self.exit(return_code=0)


def verify_state_headless(state_path: Path) -> int:
    """Validate state file in headless CLI mode and print verification summary."""
    reader = QuotaStateReader(state_path)
    data, err = reader.read_state()
    if not data:
        print(f"❌ Verification FAILED: {err}", file=sys.stderr)
        return 1

    providers = data.get("providers", {})
    metrics = data.get("metrics", {})
    version = data.get("version", "unknown")

    print(f"✓ Python Textual Verification Passed: Version {version}")
    print(f"  Providers ({len(providers)}): {', '.join(providers.keys())}")
    print(
        f"  Metrics: Routed={metrics.get('total_tasks_routed', 0)}, "
        f"LoRA Harvested={metrics.get('total_lora_samples_harvested', 0)}"
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Canonical Lauburu Python Textual Cloud API Quota HUD"
    )
    parser.add_argument(
        "--state-path",
        type=Path,
        default=DEFAULT_STATE_PATH,
        help="Path to cloud_api_quota_state.json",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help="Polling interval in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run headless schema verification and exit 0 on valid state",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Automatic exit timeout in seconds (for smoke tests)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.verify:
        sys.exit(verify_state_headless(args.state_path))

    app = QuotaTuiApp(
        state_path=args.state_path,
        poll_interval=args.poll_interval,
        verify_mode=False,
        timeout=args.timeout,
    )
    app.run()


if __name__ == "__main__":
    main()
