#!/usr/bin/env python3
"""
05_agents_and_swarms/tri_layer_hybrid_bridge.py
================================================
Swarm Bridge & Integration for Tri-Layer Hybrid Orchestration (Milestone M3).
Exposes Cloud Frontier Orchestration, Sovereign Local Kimi Tandem Engine,
and Nomad Courier Autonomous Self-Healing Governor to all swarm agents.
"""

import os
import sys
from pathlib import Path

# Add core infrastructure source paths
CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent
INFRA_SRC = REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src"

for p in [REPO_ROOT, INFRA_SRC]:
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

try:
    from tri_layer_hybrid_orchestrator import (
        TriLayerHybridOrchestrator,
        CloudFrontierOrchestrator,
        SovereignLocalAIEngine,
        AutonomousSelfHealingGovernor,
        TaskSpecification,
        ShadowVerificationResult,
        TriLayerExecutionResult
    )
except ImportError as e:
    # If relative path lookup fails in specialized containers, attempt direct path import
    sys.path.append(str(Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src")))
    from tri_layer_hybrid_orchestrator import (
        TriLayerHybridOrchestrator,
        CloudFrontierOrchestrator,
        SovereignLocalAIEngine,
        AutonomousSelfHealingGovernor,
        TaskSpecification,
        ShadowVerificationResult,
        TriLayerExecutionResult
    )

__all__ = [
    "TriLayerHybridOrchestrator",
    "CloudFrontierOrchestrator",
    "SovereignLocalAIEngine",
    "AutonomousSelfHealingGovernor",
    "TaskSpecification",
    "ShadowVerificationResult",
    "TriLayerExecutionResult",
    "get_tri_layer_orchestrator"
]

_GLOBAL_ORCHESTRATOR = None

def get_tri_layer_orchestrator() -> TriLayerHybridOrchestrator:
    """Returns the singleton instance of the Tri-Layer Hybrid Orchestrator."""
    global _GLOBAL_ORCHESTRATOR
    if _GLOBAL_ORCHESTRATOR is None:
        _GLOBAL_ORCHESTRATOR = TriLayerHybridOrchestrator()
    return _GLOBAL_ORCHESTRATOR
