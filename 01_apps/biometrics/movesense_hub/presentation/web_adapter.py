"""
Web-TUI & PWA Oscilloscope Adapter for Movesense Hub.
Provides:
1. Web-TUI PTY launcher for Port 8088 (/readiness route)
2. Next.js Canvas Oscilloscope PWA connector (LiveEcgMonitor.tsx)
3. Interface Contract JSON REST & WebSocket serializer.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.config import MovesenseHubConfig
from ..core.models import BiometricsStateStore, ReadinessReport


class WebTuiAdapter:
    """
    Adapter for integrating Movesense TUI into the 120 FPS Web-TUI Portal (Port 8088).
    """

    def __init__(self, config: Optional[MovesenseHubConfig] = None):
        self.config = config or MovesenseHubConfig()

    @staticmethod
    def get_pty_command() -> List[str]:
        """Returns the CLI command executed by serve_web_tui.py for the /readiness route."""
        entrypoint = Path(__file__).parent / "tui.py"
        return [sys.executable, str(entrypoint)]


class OscilloscopePwaConnector:
    """
    Connector for Next.js 14 Canvas Oscilloscope (LiveEcgMonitor.tsx)
    Transforms raw ECG microvolt/millivolt samples into circular ring buffer sweep frames.
    """

    def __init__(self, sampling_rate_hz: int = 128, ring_buffer_capacity: int = 640):
        self.sampling_rate_hz = sampling_rate_hz
        self.capacity = ring_buffer_capacity
        self._samples_buffer: List[float] = []

    def format_oscilloscope_payload(
        self,
        ecg_samples: List[float],
        heart_rate: Optional[int] = None,
        is_connected: bool = False,
    ) -> Dict[str, Any]:
        """
        Formats JSON frame conforming to LiveEcgMonitorProps contract.
        """
        clamped_samples = []
        for s in ecg_samples:
            if s is None:
                val = 0.0
            else:
                val = max(-5.0, min(5.0, float(s)))
            clamped_samples.append(val)

        return {
            "type": "ECG_SWEEP_FRAME",
            "leadStatus": "CONNECTED" if is_connected else "DISCONNECTED",
            "samplingRateHz": self.sampling_rate_hz,
            "heartRate": int(heart_rate) if heart_rate is not None else 0,
            "ecgSamples": clamped_samples,
            "timeWindowSeconds": 5.0,
            "rule_0_zero_mock": True,
        }


class ReadinessRestAdapter:
    """
    Serializes readiness snapshots for REST/WebSocket consumption.
    """

    def __init__(self, state_store: BiometricsStateStore):
        self.state_store = state_store

    def get_readiness_json(self) -> str:
        """Returns JSON string conforming to PROJECT.md Interface Contract."""
        return json.dumps(self.state_store.get_interface_contract(), indent=2)

    def get_full_report_json(self) -> str:
        """Returns complete full report JSON payload."""
        return json.dumps(self.state_store.get_report().to_full_dict(), indent=2)
