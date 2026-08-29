"""
Combat Arena Modes Package.
"""

from .tug_of_war import execute_tug_of_war_step
from .battle import execute_battle_step
from .proximity import execute_proximity_step
from .defense import execute_defense_step

GAME_MODES = [
    "TUG_OF_WAR",
    "BATTLE",
    "PROXIMITY",
    "DEFENSE",
    "EDGE_ORCHESTRATOR_CLASSIC",
    "SMOLAGENTS_PYTHON_DUEL",
    "MULTI_MODEL_AGI_SWARM",
    "AIRGAP_MESH_VS_CLOUD_CHAOS"
]

__all__ = [
    "execute_tug_of_war_step",
    "execute_battle_step",
    "execute_proximity_step",
    "execute_defense_step",
    "GAME_MODES",
]
