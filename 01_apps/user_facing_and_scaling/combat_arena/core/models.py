"""
Combat Arena Data Models.
=========================
Subsystem: 01_apps/user_facing_and_scaling/combat_arena/core/models.py
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

class GameModeType(str, Enum):
    TUG_OF_WAR = "TUG_OF_WAR"
    BATTLE = "BATTLE"
    PROXIMITY = "PROXIMITY"
    DEFENSE = "DEFENSE"
    # Aliases matching classic engine
    EDGE_ORCHESTRATOR_CLASSIC = "EDGE_ORCHESTRATOR_CLASSIC"
    SMOLAGENTS_PYTHON_DUEL = "SMOLAGENTS_PYTHON_DUEL"
    MULTI_MODEL_AGI_SWARM = "MULTI_MODEL_AGI_SWARM"
    AIRGAP_MESH_VS_CLOUD_CHAOS = "AIRGAP_MESH_VS_CLOUD_CHAOS"

@dataclass
class CombatantState:
    faction: str  # "RED" or "BLUE"
    leader_name: str
    energy_level: float = 100.0
    progress_pct: float = 50.0
    current_objective: str = ""
    active_code_action: str = ""
    last_action_success: bool = True
    vram_usage_gb: float = 0.0

@dataclass
class DuelRoundResult:
    round_id: int
    game_mode: str
    timestamp_utc: str
    red_action: Dict[str, Any]
    blue_action: Dict[str, Any]
    power_delta: float
    winner: Optional[str] = None

@dataclass
class PulseTelemetry:
    heart_rate_bpm: Optional[float]
    rmssd_ms: Optional[float]
    zone2_aligned: bool
    is_connected: bool
    status_text: str = "WAITING_FOR_SENSOR"

@dataclass
class ArenaSnapshot:
    step: int
    mode: str
    red_combatant: CombatantState
    blue_combatant: CombatantState
    pulse: PulseTelemetry
    power_bar_ratio: float  # -1.0 (all red) to +1.0 (all blue)
    narrative_stream: List[str] = field(default_factory=list)
