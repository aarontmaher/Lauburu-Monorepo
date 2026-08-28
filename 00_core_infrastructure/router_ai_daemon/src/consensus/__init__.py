"""
Consensus Subsystem — Dual-Core Genetic Consensus & Micro-Debate Router.

Provides:
- DualCoreRouter: Primary smolagi reasoning engine + secondary Genetic Router coordinator
- GeneticRouter & RoutingChromosome: Evolutionary multi-attribute route optimizer
- MicroDebateEngine & DebateRecord: 3-round micro-debate deliberation and accord synthesis
- Divergence & utility mathematics: compute_divergence, calculate_utility, compute_cosine_accord
"""

from src.consensus.dual_core_router import (
    ConsensusResult,
    DecisionVector,
    DualCoreRouter,
    RoutingContext,
    compute_divergence,
)
from src.consensus.genetic_router import (
    MESH_TOPOLOGY,
    GeneticRouter,
    RoutingChromosome,
)
from src.consensus.micro_debate import (
    CONSENSUS_ACCORD_THRESHOLD,
    DEFAULT_FAILSAFE_ACTION,
    DEFAULT_FAILSAFE_ROUTE,
    DEFAULT_LEDGER_PATH,
    MAX_DEBATE_SLA_MS,
    UTILITY_WEIGHTS,
    CandidateEvaluation,
    DebateRecord,
    DebateTurn,
    MicroDebateEngine,
    calculate_utility,
    compute_cosine_accord,
)

__all__ = [
    # Dual-Core Coordinator
    "DualCoreRouter",
    "RoutingContext",
    "ConsensusResult",
    "DecisionVector",
    "compute_divergence",
    # Genetic Router
    "GeneticRouter",
    "RoutingChromosome",
    "MESH_TOPOLOGY",
    # Micro-Debate Engine
    "MicroDebateEngine",
    "CandidateEvaluation",
    "DebateTurn",
    "DebateRecord",
    "calculate_utility",
    "compute_cosine_accord",
    # Constants
    "CONSENSUS_ACCORD_THRESHOLD",
    "MAX_DEBATE_SLA_MS",
    "DEFAULT_FAILSAFE_ACTION",
    "DEFAULT_FAILSAFE_ROUTE",
    "DEFAULT_LEDGER_PATH",
    "UTILITY_WEIGHTS",
]
