"""
SmolAgents Duel Sandbox Data Models.
====================================
Subsystem: 01_apps/operator_and_dev/smolagents_duel_sandbox/core/models.py
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class AgentAction:
    agent_id: str
    faction: str  # "RED" or "BLUE"
    intent: str
    python_code: str
    execution_time_ms: float = 0.0
    status: str = "PENDING"
    output: Any = None
    error: Optional[str] = None

@dataclass
class ToolResult:
    tool_name: str
    parameters: Dict[str, Any]
    result: Any
    is_success: bool
    latency_ms: float

@dataclass
class DuelExecutionRecord:
    step_id: int
    timestamp_utc: str
    red_action: AgentAction
    blue_action: AgentAction
    evaluation_score_delta: float
    tactical_summary: str
