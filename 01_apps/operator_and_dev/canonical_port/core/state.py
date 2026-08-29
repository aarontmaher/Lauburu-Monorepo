"""
Canonical Port State Store.
===========================
Subsystem: 01_apps/operator_and_dev/canonical_port/core/state.py
"""

from typing import Dict, List, Any
from .models import MeshNodeInfo, StabilityScreenInfo, DebateCouncilState, DebateSpeaker

class CanonicalStateStore:
    """Central state governor tracking 7 physical nodes and stability hierarchy."""

    def __init__(self):
        self.active_screen_id = 1
        self.debate_state = DebateCouncilState(
            topic="Dynamic VRAM Sharding across 10Gbps TB4 & Tailscale Mesh",
            round_number=4,
            speakers=[
                DebateSpeaker(name="Hermes 3 Red", persona="Aggressive Throughput", stance="Shard 32B across Mac + MacBook Pro", confidence=0.92, last_argument="TB4 latency is 0.27ms, zero tensor pipeline stalls."),
                DebateSpeaker(name="LuCI Blue", persona="Security & Stability", stance="Enforce 90% Host RAM safety ceiling", confidence=0.95, last_argument="Must guarantee 2.50 GB free host RAM for Pan-Tompkins 512Hz ECG."),
                DebateSpeaker(name="Devil's Advocate", persona="Adversarial Critic", stance="Test Wi-Fi 7 fallback latency", confidence=0.88, last_argument="If TB4 cable unplugs, system must failover to WireGuard in <10ms."),
                DebateSpeaker(name="Synthesis Arbiter", persona="Consensus Leader", stance="Approved Hybrid Policy", confidence=0.97, last_argument="Enforce TB4 primary + 90% dynamic RAM governor with automatic hot-swap.")
            ],
            consensus_reached=True,
            consensus_summary="All 7 nodes operating under dynamic RAM governance with 82.8 GB usable AI VRAM."
        )
