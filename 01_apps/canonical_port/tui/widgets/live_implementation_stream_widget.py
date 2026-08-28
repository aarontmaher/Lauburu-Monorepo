"""
Live Implementation Stream Widget (Milestone 3)
Continuously tails 04_data_and_memory/tui_live_implementation_stream.json in real time.
Broadcasts subagent actions, active agent ELO badge, progress, and worktree isolation events live with zero restarts.
Features thread-safe Multi-Producer Single-Consumer (MPSC) bounded ring buffering and 4x density Unicode Braille sparklines.
"""

import os
import sys
import json
import time
import threading
import collections
from typing import Dict, Any, List, Optional
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, RichLog
from rich.text import Text
from rich.markup import escape


class MPSCRingBuffer:
    """
    Thread-safe Multi-Producer Single-Consumer (MPSC) bounded ring buffer.
    Mitigates UI thread lock contention and prevents render stuttering during burst diff injection.
    """
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self._deque: collections.deque = collections.deque(maxlen=capacity)
        self._lock = threading.Lock()

    def push(self, item: Any) -> None:
        """Thread-safe non-blocking push to the ring buffer."""
        with self._lock:
            self._deque.append(item)

    def push_batch(self, items: List[Any]) -> None:
        """Thread-safe batch push to the ring buffer."""
        with self._lock:
            self._deque.extend(items)

    def pop_all(self) -> List[Any]:
        """Drains all queued items from the ring buffer in a single atomic operation."""
        with self._lock:
            items = list(self._deque)
            self._deque.clear()
            return items

    def peek_latest(self) -> Optional[Any]:
        """Returns the most recent item in the buffer without removing it."""
        with self._lock:
            return self._deque[-1] if self._deque else None

    def __len__(self) -> int:
        with self._lock:
            return len(self._deque)

    def clear(self) -> None:
        with self._lock:
            self._deque.clear()


def render_braille_sparkline(
    values: List[float],
    min_val: Optional[float] = None,
    max_val: Optional[float] = None
) -> str:
    """
    Renders a 1D numerical sequence into a high-density Unicode Braille sparkline (U+2800..U+28FF)
    delivering 4x vertical resolution per character cell. Each Braille character encodes 2 horizontal sample columns (2x4 matrix).
    """
    if not values:
        return "⠂"

    min_v = min_val if min_val is not None else (min(values) if values else 0.0)
    max_v = max_val if max_val is not None else (max(values) if values else 100.0)
    span = max(1e-6, max_v - min_v)

    # Quantize each value to 0..4 dots
    levels = [
        max(0, min(4, int(round(((v - min_v) / span) * 4.0))))
        for v in values
    ]

    # Bitmasks for left column (dots 7, 3, 2, 1) and right column (dots 8, 6, 5, 4)
    col1_dots = [0x00, 0x40, 0x40 | 0x04, 0x40 | 0x04 | 0x02, 0x40 | 0x04 | 0x02 | 0x01]
    col2_dots = [0x00, 0x80, 0x80 | 0x20, 0x80 | 0x20 | 0x10, 0x80 | 0x20 | 0x10 | 0x08]

    chars = []
    for i in range(0, len(levels), 2):
        l1 = levels[i]
        l2 = levels[i + 1] if (i + 1 < len(levels)) else l1
        mask = col1_dots[l1] | col2_dots[l2]
        chars.append(chr(0x2800 + mask) if mask != 0 else "⠀")

    return "".join(chars)


class LiveImplementationStreamWidget(Static):
    """
    Textual Widget for streaming live subagent restructuring events in real-time.
    Tails tui_live_implementation_stream.json and updates UI with zero restarts.
    """
    DEFAULT_CSS = """
    LiveImplementationStreamWidget {
        height: auto;
        min-height: 12;
        border: solid #00ffcc;
        background: #070b12;
        padding: 0 1;
        margin: 0;
    }
    .stream-header {
        text-style: bold;
        color: #00ffcc;
        dock: top;
        height: 1;
        background: #0b1528;
        padding: 0 1;
    }
    #stream-status {
        height: auto;
        color: #38bdf8;
        background: #091424;
        border-bottom: solid #1e293b;
        padding: 0 1;
    }
    #stream-log-view {
        height: 12;
        background: #030712;
        color: #e2e8f0;
        border: solid #1e293b;
    }
    """

    def __init__(
        self,
        stream_path: Optional[str] = None,
        poll_interval: float = 0.1,
        **kwargs
    ):
        super().__init__(**kwargs)
        if stream_path:
            self.stream_path = stream_path
        else:
            candidates = [
                "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/tui_live_implementation_stream.json",
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "04_data_and_memory", "tui_live_implementation_stream.json")),
                "04_data_and_memory/tui_live_implementation_stream.json",
            ]
            self.stream_path = next((p for p in candidates if os.path.exists(os.path.dirname(p))), candidates[0])

        self.poll_interval = poll_interval
        self._last_mtime: float = 0.0
        self._last_size: int = 0
        self._events: List[Dict[str, Any]] = []
        self._ring_buffer: MPSCRingBuffer = MPSCRingBuffer(capacity=1000)
        self.log_widget: Optional[RichLog] = None
        self.status_header: Optional[Static] = None

    def compose(self) -> ComposeResult:
        yield Static("⚡ TUI SPECIALIST LIVE IMPLEMENTATION STREAM", classes="stream-header", id="stream-title")
        self.status_header = Static("Status: IDLE | Agent: -- | Action: --", id="stream-status")
        yield self.status_header
        self.log_widget = RichLog(highlight=True, markup=True, id="stream-log-view", max_lines=1000)
        yield self.log_widget

    def on_mount(self) -> None:
        self.set_interval(self.poll_interval, self.tail_stream_file)
        self.tail_stream_file()

    def tail_stream_file(self) -> None:
        """Polls stream file and ingests newly appended JSON event lines via MPSC ring buffer."""
        if not os.path.isfile(self.stream_path):
            if self.status_header and not self._events:
                self.status_header.update("Status: IDLE | Agent: -- | Action: Awaiting Stream")
            return

        try:
            stat = os.stat(self.stream_path)
            if stat.st_size < self._last_size:
                self._last_size = 0
                self._last_mtime = 0.0

            if stat.st_mtime <= self._last_mtime and stat.st_size <= self._last_size:
                return

            with open(self.stream_path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._last_size if stat.st_size >= self._last_size else 0)
                new_lines = f.readlines()
                self._last_size = f.tell()
                self._last_mtime = stat.st_mtime

            for line in new_lines:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    event = json.loads(line_str)
                    if isinstance(event, dict):
                        self._ring_buffer.push(event)
                        self._events.append(event)
                        self._render_event(event)
                    else:
                        if self.log_widget:
                            self.log_widget.write(f">> {str(event)}")
                except json.JSONDecodeError:
                    if self.log_widget:
                        self.log_widget.write(f">> {line_str}")
        except Exception:
            pass

    def _render_event(self, event: Dict[str, Any]) -> None:
        """Renders parsed event into status header and rich log with Braille density visualization."""
        agent = event.get("active_agent") or event.get("model_assigned") or "--"
        action = event.get("current_action") or event.get("task") or event.get("message") or "--"
        status = event.get("status", "RUNNING")
        progress = event.get("progress", 0)
        event_type = event.get("event", "EVENT")
        worktree = event.get("worktree_path") or event.get("branch") or ""
        elo = event.get("elo")

        # Braille sparkline over recent progress history
        history = [float(e.get("progress", 0)) for e in self._events[-16:]]
        spark = render_braille_sparkline(history, min_val=0.0, max_val=100.0)

        if self.status_header:
            elo_str = f" | ELO: {elo}" if elo else ""
            self.status_header.update(
                f"Status: {status} | {event_type} ({progress}%) [{spark}]{elo_str} | Agent: {agent} | Action: {action}"
            )

        if self.log_widget:
            raw_ts = event.get("timestamp", time.time())
            try:
                ts_str = time.strftime("%H:%M:%S", time.localtime(raw_ts))
            except Exception:
                ts_str = time.strftime("%H:%M:%S")

            wt_str = f" ({worktree})" if worktree else ""
            msg = f"[dim]{ts_str}[/dim] [bold green]{event_type}[/bold green] [yellow]{agent}[/yellow]: {action} [cyan]({progress}%)[/cyan]{wt_str}"
            self.log_widget.write(msg)

    @property
    def event_count(self) -> int:
        return len(self._events)

    @property
    def latest_event(self) -> Optional[Dict[str, Any]]:
        return self._events[-1] if self._events else None

    @property
    def events(self) -> List[Dict[str, Any]]:
        return list(self._events)

    @property
    def ring_buffer(self) -> MPSCRingBuffer:
        return self._ring_buffer

    def clear(self) -> None:
        """Clear recorded events, MPSC buffer, and visual log buffer."""
        self._events.clear()
        self._ring_buffer.clear()
        self._last_size = 0
        self._last_mtime = 0.0
        if self.log_widget:
            self.log_widget.clear()
        if self.status_header:
            self.status_header.update("Status: IDLE | Agent: -- | Action: Awaiting Stream")
