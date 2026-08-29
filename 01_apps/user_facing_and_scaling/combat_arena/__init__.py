"""
Lauburu Combat Arena Suite.
===========================
Subsystem: 01_apps/user_facing_and_scaling/combat_arena
Version: 1.0.0-CANONICAL

Multi-mode adversarial game arena between Hermes 3 (Red Attackers)
and LuCI OpenWrt (Blue Defenders) with 120 FPS compute power gauge,
live Movesense biofeedback, and RAG narrative voice.

Subpackages:
- core: Data models, configs, and state stores
- modes: Tug-of-War, Battle, Proximity, Defense
- presentation: Power bar renderer, pulse gauge, RAG voice, Textual TUI
"""

from .core import (
    ArenaConfig,
    GameModeType,
    CombatantState,
    DuelRoundResult,
    PulseTelemetry,
    ArenaSnapshot,
    ArenaStateStore,
)
from .modes import (
    execute_tug_of_war_step,
    execute_battle_step,
    execute_proximity_step,
    execute_defense_step,
    GAME_MODES,
)
from .presentation import (
    render_power_bar,
    render_pulse_gauge,
    RagVoiceCommentator,
    CombatArenaEngine,
    CombatArenaApp,
    run_arena,
)

__version__ = "1.0.0"

__all__ = [
    "__version__",
    "ArenaConfig",
    "GameModeType",
    "CombatantState",
    "DuelRoundResult",
    "PulseTelemetry",
    "ArenaSnapshot",
    "ArenaStateStore",
    "execute_tug_of_war_step",
    "execute_battle_step",
    "execute_proximity_step",
    "execute_defense_step",
    "GAME_MODES",
    "render_power_bar",
    "render_pulse_gauge",
    "RagVoiceCommentator",
    "CombatArenaEngine",
    "CombatArenaApp",
    "run_arena",
]
