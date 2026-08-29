"""
Combat Arena State Store.
=========================
Subsystem: 01_apps/user_facing_and_scaling/combat_arena/core/state.py
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from .config import ArenaConfig
from .models import CombatantState, PulseTelemetry, ArenaSnapshot, GameModeType

class ArenaStateStore:
    """Manages persistent live state and telemetry ingestion for Combat Arena."""

    def __init__(self, config: Optional[ArenaConfig] = None):
        self.config = config or ArenaConfig()
        self.step_count = 0
        self.active_mode = self.config.default_game_mode
        self.red = CombatantState(faction="RED", leader_name=self.config.red_leader_name, progress_pct=50.0)
        self.blue = CombatantState(faction="BLUE", leader_name=self.config.blue_leader_name, progress_pct=50.0)
        self.history: List[Dict[str, Any]] = []

    def get_pulse_telemetry(self) -> PulseTelemetry:
        """Reads live physical Movesense telemetry adhering strictly to Rule #0."""
        if self.config.movesense_file.exists():
            try:
                with open(self.config.movesense_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    hr = data.get("heart_rate_bpm")
                    rmssd = data.get("rmssd_ms")
                    connected = data.get("sensor_connected", False)
                    if connected and hr is not None:
                        return PulseTelemetry(
                            heart_rate_bpm=float(hr),
                            rmssd_ms=float(rmssd) if rmssd is not None else None,
                            zone2_aligned=bool(data.get("zone2_aligned", False)),
                            is_connected=True,
                            status_text="CONNECTED_512HZ_STREAM"
                        )
            except Exception:
                pass
        return PulseTelemetry(
            heart_rate_bpm=None,
            rmssd_ms=None,
            zone2_aligned=False,
            is_connected=False,
            status_text="WAITING_FOR_SENSOR"
        )

    def snapshot(self) -> ArenaSnapshot:
        """Produces instantaneous arena state snapshot."""
        diff = (self.blue.progress_pct - self.red.progress_pct) / 100.0
        return ArenaSnapshot(
            step=self.step_count,
            mode=self.active_mode,
            red_combatant=self.red,
            blue_combatant=self.blue,
            pulse=self.get_pulse_telemetry(),
            power_bar_ratio=round(max(min(diff, 1.0), -1.0), 3)
        )
