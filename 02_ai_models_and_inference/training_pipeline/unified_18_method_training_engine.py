#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Lauburu Distributed AI Mesh: Unified AI Training & Distillation Framework
================================================================================
Subsystem: 02_ai_models_and_inference/training_pipeline/unified_18_method_training_engine.py
Version: 2.0.0-COMPATIBILITY-SHIM
Lauburu Mesh Ecosystem — 2026

CANONICAL ARCHITECTURAL DIRECTIVE (AI Debate Consensus 0.996):
This module is a frozen backward-compatible re-export shim for the canonical
Single Source of Truth (SSOT):
  `02_ai_models_and_inference/training_pipeline/unified_22_method_frontier_training_engine.py`

Preserves 100% backward compatibility for all existing callers, test suites,
and daemons while channeling all underlying mathematical execution through
the 22-Method Frontier Framework (adding SimPO, RLVR, TTC MCTS, and FastV).
================================================================================
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Import everything directly from canonical 22-method SSOT engine
try:
    from .unified_22_method_frontier_training_engine import (
        PretrainingFamily,
        PEFTFamily,
        PreferenceAlignmentFamily,
        VerifiableRewardsAndTTCFamily,
        DistillationFamily,
        MultimodalAndMergingFamily,
        MultimodalAndMergingFamily as ModelMergingFamily,  # Backward-compatible alias
        dot_product,
        vector_norm,
        matrix_mult,
        matrix_transpose,
        softmax,
        sigmoid,
        export_manifest as export_22_manifest,
        OUTPUT_DIR,
    )
except ImportError:
    from unified_22_method_frontier_training_engine import (
        PretrainingFamily,
        PEFTFamily,
        PreferenceAlignmentFamily,
        VerifiableRewardsAndTTCFamily,
        DistillationFamily,
        MultimodalAndMergingFamily,
        MultimodalAndMergingFamily as ModelMergingFamily,  # Backward-compatible alias
        dot_product,
        vector_norm,
        matrix_mult,
        matrix_transpose,
        softmax,
        sigmoid,
        export_manifest as export_22_manifest,
        OUTPUT_DIR,
    )

__all__ = [
    "PretrainingFamily",
    "PEFTFamily",
    "PreferenceAlignmentFamily",
    "VerifiableRewardsAndTTCFamily",
    "DistillationFamily",
    "ModelMergingFamily",
    "MultimodalAndMergingFamily",
    "dot_product",
    "vector_norm",
    "matrix_mult",
    "matrix_transpose",
    "softmax",
    "sigmoid",
    "export_manifest",
]


def export_manifest() -> Dict[str, Any]:
    """Exports both backward-compatible 18-method manifest and 22-method frontier manifest."""
    manifest_18 = {
        "framework": "Lauburu Unified 18-Method AI Training Framework (SSOT Linked to 22-Method Frontier)",
        "engine_type": "Zero-Dependency Universal Python Engine",
        "ssot_source": "unified_22_method_frontier_training_engine.py",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_methods": 18,
        "frontier_extended_methods": 22,
        "consensus_decree": "AI Debate Consensus 0.996 (SSOT Invariant)",
        "families": {
            "Family 1: Pretraining": ["1. CLM", "2. MLM", "3. FIM"],
            "Family 2: SFT & PEFT": ["4. Full SFT", "5. LoRA", "6. QLoRA", "7. DoRA", "8. LongLoRA / LoRA-FA"],
            "Family 3: Preference Alignment": [
                "9. RLHF/PPO",
                "10. DPO",
                "11. IPO",
                "12. KTO",
                "13. ORPO",
                "14. GRPO (DeepSeek-R1)",
                "15. SimPO (NeurIPS 2024 Reference-Free)",
            ],
            "Family 4: Rule-Based Verifiable & TTC": [
                "16. RLVR Oracles",
                "17. TTC-Search MCTS",
            ],
            "Family 5: Distillation & Self-Play": [
                "18. CoT Reasoning Distillation",
                "19. SPIN",
                "20. STaR / ReST",
            ],
            "Family 6: Multimodal VLA & Merging": [
                "21. FastV Token Pruning",
                "22. SLERP / TIES Model Merging",
            ],
        },
    }
    json_path = os.path.join(OUTPUT_DIR, "unified_18_training_methods_manifest.json")
    with open(json_path, "w") as f:
        json.dump(manifest_18, f, indent=2)
    print(f"✅ Master 18-Method Manifest saved to {json_path}")
    export_22_manifest()
    return manifest_18


if __name__ == "__main__":
    export_manifest()
