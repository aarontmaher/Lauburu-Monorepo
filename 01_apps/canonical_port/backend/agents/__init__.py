"""
Canonical Autonomous Agent Ecosystem Package
Version: 3.0.0-CANONICAL
"""

from .quota_governor import QuotaGovernor, get_quota_governor
from .cloud_ai_router import CloudAIRouter, SmolagentAIRouter
from .smolagents_ecosystem import (
    SmolagentTool,
    AgentTool,
    SmolagentAgentWrapper,
    SpecialistAgent,
    SmolagentRunner,
    create_mesh_diagnostics_tool,
    create_obsidian_knowledge_tool,
    create_self_healing_tool,
    create_lora_dataset_tool,
    create_system_metrics_tool,
)
from .cron_scheduler import SmolagentCronScheduler, get_cron_scheduler
from .self_healing_daemon import SelfHealingDaemon, get_self_healing_daemon
from .router import create_agents_router
from .continuous_arena_router import (
    ChampionLeaderboardResolver,
    ContinuousArenaEngine,
    ContinuousArenaInferenceRouter,
    ArenaTrialRequest,
    ArenaTrialResult,
    DEFAULT_CHAMPION_SPEC,
    MODEL_ENGINE_MAPPINGS,
    DEFAULT_CHALLENGER_POOL,
    resolve_model_engine,
)

__all__ = [
    "QuotaGovernor",
    "get_quota_governor",
    "CloudAIRouter",
    "SmolagentAIRouter",
    "SmolagentTool",
    "AgentTool",
    "SmolagentAgentWrapper",
    "SpecialistAgent",
    "SmolagentRunner",
    "create_mesh_diagnostics_tool",
    "create_obsidian_knowledge_tool",
    "create_self_healing_tool",
    "create_lora_dataset_tool",
    "create_system_metrics_tool",
    "SmolagentCronScheduler",
    "get_cron_scheduler",
    "SelfHealingDaemon",
    "get_self_healing_daemon",
    "create_agents_router",
    "ChampionLeaderboardResolver",
    "ContinuousArenaEngine",
    "ContinuousArenaInferenceRouter",
    "ArenaTrialRequest",
    "ArenaTrialResult",
    "DEFAULT_CHAMPION_SPEC",
    "MODEL_ENGINE_MAPPINGS",
    "DEFAULT_CHALLENGER_POOL",
    "resolve_model_engine",
]
