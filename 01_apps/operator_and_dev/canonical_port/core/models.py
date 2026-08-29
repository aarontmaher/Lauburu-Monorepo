"""
Canonical Port Data Models.
===========================
Subsystem: 01_apps/operator_and_dev/canonical_port/core/models.py
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class MeshNodeInfo:
    layer: str
    node_name: str
    network_role: str
    local_ip: str
    tailscale_ip: str
    physical_ram_gb: float
    usable_ai_vram_gb: float
    dynamic_cap_pct: float
    is_online: bool = True
    active_models: List[str] = field(default_factory=list)

@dataclass
class StabilityScreenInfo:
    screen_id: int
    name: str
    title: str
    hotkey: str
    status: str = "HEALTHY"

@dataclass
class DebateSpeaker:
    name: str
    persona: str
    stance: str
    confidence: float
    last_argument: str

@dataclass
class DebateCouncilState:
    topic: str
    round_number: int
    speakers: List[DebateSpeaker] = field(default_factory=list)
    consensus_reached: bool = True
    consensus_summary: str = ""
