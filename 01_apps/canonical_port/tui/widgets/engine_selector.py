"""
Canonical Visual Inference Engine Selector Widget
Version: 2.0.0-CANONICAL

Provides visual top-bar engine dropdown selection and hotkey cycling ([Ctrl+E] / [F2])
across 5 inference modes:
- auto: 🤖 Dynamic TTFT Latency Polling & Auto-Routing
- llama_rpc: LLAMA.CPP GGML-RPC (:50052 & :8081-:8085)
- exo: EXO Decentralized Ring P2P (:52415)
- accelerate: HuggingFace Accelerate Multi-GPU / MPS Metal
- petals: Petals BitTorrent DHT Swarm (:31330/:31337)
"""

from typing import List, Tuple, Optional, Dict
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Select, Static
from textual.message import Message


class InferenceEngineChanged(Message):
    """Event emitted when the active inference engine backend is switched."""

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


class EngineSelectorWidget(Horizontal):
    """
    Visual Engine Selector widget for Canonical Port TUI Header / Top Bar.
    Provides instant switching across inference modes and distributed backends.
    """

    DEFAULT_CSS = """
    EngineSelectorWidget {
        height: 1;
        width: 100%;
        background: #0b111c;
        align: right middle;
        padding: 0 1;
    }
    #engine-selector-label {
        width: auto;
        color: #94a3b8;
        text-style: bold;
    }
    #engine-select {
        width: 36;
        height: 1;
        border: none;
        background: #0f172a;
        color: #00ffcc;
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

    def __init__(
        self,
        active_engine: str = "llama_rpc",
        id: str = "engine-selector-bar",
        classes: str = ""
    ):
        super().__init__(id=id, classes=classes)
        self.active_engine = active_engine if active_engine in self.ENGINES else "llama_rpc"

    def compose(self) -> ComposeResult:
        yield Static("⚙ Inference Engine [Ctrl+E]: ", id="engine-selector-label")
        yield Select(
            options=self.ENGINE_OPTIONS,
            value=self.active_engine,
            allow_blank=False,
            id="engine-select"
        )

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle user selecting an option in the Select dropdown."""
        if event.value != Select.BLANK and str(event.value) != self.active_engine:
            prev = self.active_engine
            self.active_engine = str(event.value)
            disp = self.ENGINE_NAMES.get(self.active_engine, self.active_engine)
            self.post_message(
                InferenceEngineChanged(
                    engine_name=self.active_engine,
                    display_name=disp,
                    previous_engine=prev,
                    source="dropdown"
                )
            )

    def cycle_engine(self, delta: int = 1) -> str:
        """Cycle through inference engines in canonical order."""
        try:
            cur_idx = self.ENGINES.index(self.active_engine)
        except ValueError:
            cur_idx = 0
        next_idx = (cur_idx + delta) % len(self.ENGINES)
        prev = self.active_engine
        self.active_engine = self.ENGINES[next_idx]

        # Update Select dropdown widget value if available
        try:
            sel = self.query_one("#engine-select", Select)
            if sel:
                sel.value = self.active_engine
        except Exception:
            pass

        disp = self.ENGINE_NAMES.get(self.active_engine, self.active_engine)
        self.post_message(
            InferenceEngineChanged(
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
                sel = self.query_one("#engine-select", Select)
                if sel and sel.value != self.active_engine:
                    sel.value = self.active_engine
            except Exception:
                pass
            disp = self.ENGINE_NAMES.get(self.active_engine, self.active_engine)
            self.post_message(
                InferenceEngineChanged(
                    engine_name=self.active_engine,
                    display_name=disp,
                    previous_engine=prev,
                    source="api"
                )
            )
