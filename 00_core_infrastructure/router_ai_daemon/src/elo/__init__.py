"""
ELO Scoring Engine & Economic Realignment Penalty Package.
Features F7 (Shadow Coding), F8 (David vs Goliath ELO Multiplier), F9 (Waste Tax).
"""

from .elo_engine import (
    CodeOffMatch,
    EloEngine,
    EloUpdateResult,
    ResourceUsage,
    DEFAULT_ALPHA,
    DEFAULT_BETA,
    DEFAULT_DELTA,
    DAVID_MAX_MULTIPLIER,
    DAVID_MIN_MULTIPLIER,
    GOLIATH_MAX_MULTIPLIER,
    GOLIATH_MIN_MULTIPLIER,
    MAX_DAVID_ELO_GAIN,
)
from .ledger import (
    DEFAULT_LEDGER_PATH,
    EloLedger,
)
from .waste_tax import (
    DEFAULT_C0,
    DEFAULT_GAMMA,
    DEFAULT_LAMBDA_BASE,
    DEFAULT_T0,
    DEFAULT_THRESHOLD,
    ELO_QUARANTINE_THRESHOLD,
    MAX_TAX_DEDUCTION,
    WEIGHT_CALLS,
    WEIGHT_COST,
    WEIGHT_MESH,
    WEIGHT_TOKENS,
    DisciplinaryVerdict,
    WasteTaxCalculator,
    WasteTaxPenaltyEvent,
    calculate_mesh_drain_index,
    calculate_optimization_score,
    calculate_waste_tax,
    evaluate_disciplinary_action,
)

__all__ = [
    # ELO Engine
    "EloEngine",
    "CodeOffMatch",
    "ResourceUsage",
    "EloUpdateResult",
    "DEFAULT_ALPHA",
    "DEFAULT_BETA",
    "DEFAULT_DELTA",
    "DAVID_MAX_MULTIPLIER",
    "DAVID_MIN_MULTIPLIER",
    "GOLIATH_MAX_MULTIPLIER",
    "GOLIATH_MIN_MULTIPLIER",
    "MAX_DAVID_ELO_GAIN",
    # Waste Tax
    "WasteTaxCalculator",
    "WasteTaxPenaltyEvent",
    "DisciplinaryVerdict",
    "calculate_waste_tax",
    "calculate_mesh_drain_index",
    "calculate_optimization_score",
    "evaluate_disciplinary_action",
    "DEFAULT_LAMBDA_BASE",
    "DEFAULT_C0",
    "DEFAULT_T0",
    "DEFAULT_GAMMA",
    "DEFAULT_THRESHOLD",
    "MAX_TAX_DEDUCTION",
    "ELO_QUARANTINE_THRESHOLD",
    "WEIGHT_COST",
    "WEIGHT_TOKENS",
    "WEIGHT_MESH",
    "WEIGHT_CALLS",
    # Ledger
    "EloLedger",
    "DEFAULT_LEDGER_PATH",
]
