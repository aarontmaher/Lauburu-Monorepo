#!/usr/bin/env python3
"""Dynamic ELO Router for Gemini Free Tier & Alternate APIs.

Ingests public ELO records and attribute metrics to dynamically route
core task domains (deep-research, oss-scout, reverse-engineering, screen-lens)
to the mathematically optimal model under zero-cost free tier constraints.

Governed by:
- Rule 0: Canonical Hardware & Port Truth
- Rule 1: Zero-Mock & Truth Verification Rule
- Rule 6: Multi-Provider Cloud Quota & Graduated Autonomy
- Rule 15: Meritocratic Dynamic ELO Default Model Governance
"""

import os
import json
import math
import logging
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("DynamicELORouter")

# Canonical paths
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_MAPPING_PATH = os.path.join(REPO_ROOT, "gemini_free_tier_mapping.json")
FALLBACK_MAPPING_PATH = os.path.join(os.path.dirname(__file__), "gemini_free_tier_mapping.json")
CANONICAL_LEADERBOARD_PATH = os.path.join(
    REPO_ROOT, "04_data_and_memory", "data", "canonical_elo_leaderboard.json"
)

# Canonical domain aliases and keywords for natural language routing
DOMAIN_KEYWORDS = {
    "deep-research": [
        "deep-research", "deep_research", "research", "literature", "whitepaper",
        "document", "synthesis", "multi-source", "academic", "survey"
    ],
    "oss-scout": [
        "oss-scout", "oss_scout", "oss", "open-source", "open_source", "scout",
        "repository", "github", "ast", "dependency", "license", "audit", "cargo", "pypi"
    ],
    "reverse-engineering": [
        "reverse-engineering", "reverse_engineering", "reverse", "binary", "disassembly",
        "decompil", "hex", "framing", "protocol", "ghidra", "packet", "bytecode"
    ],
    "screen-lens": [
        "screen-lens", "screen_lens", "screen", "lens", "ui", "vision", "ocr",
        "bounding box", "showui", "salience", "actuation", "coregraphics", "desktop"
    ],
}


class DynamicELORouter:
    """Intelligent multi-attribute ELO routing engine."""

    def __init__(
        self,
        mapping_path: Optional[str] = None,
        leaderboard_path: Optional[str] = None
    ) -> None:
        self.mapping_path = self._resolve_mapping_path(mapping_path)
        self.leaderboard_path = leaderboard_path or CANONICAL_LEADERBOARD_PATH
        self.mapping_data: Dict[str, Any] = {}
        self.models_catalog: Dict[str, Any] = {}
        self.domain_routing_config: Dict[str, Any] = {}
        self.alternate_free_apis: Dict[str, Any] = {}
        self.live_elo_overrides: Dict[str, float] = {}

        self.reload_configuration()

    def _resolve_mapping_path(self, custom_path: Optional[str]) -> str:
        if custom_path and os.path.isfile(custom_path):
            return custom_path
        if os.path.isfile(DEFAULT_MAPPING_PATH):
            return DEFAULT_MAPPING_PATH
        if os.path.isfile(FALLBACK_MAPPING_PATH):
            return FALLBACK_MAPPING_PATH
        return DEFAULT_MAPPING_PATH

    def reload_configuration(self) -> None:
        """Loads or reloads mapping JSON and public/canonical ELOs."""
        if not os.path.isfile(self.mapping_path):
            raise FileNotFoundError(
                f"DynamicELORouter configuration not found at {self.mapping_path}"
            )

        with open(self.mapping_path, "r", encoding="utf-8") as f:
            self.mapping_data = json.load(f)

        self.models_catalog = self.mapping_data.get(
            "models_catalog", self.mapping_data.get("models", {})
        )
        self.domain_routing_config = self.mapping_data.get("domain_routing", {})
        self.alternate_free_apis = self.mapping_data.get("alternate_free_apis", {})

        # Load live overrides from canonical leaderboard if accessible
        self._ingest_canonical_leaderboard()

    def _ingest_canonical_leaderboard(self) -> None:
        """Optionally pulls updated ELO scores from canonical leaderboard."""
        if not os.path.isfile(self.leaderboard_path):
            return

        try:
            with open(self.leaderboard_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check models table in SSOT leaderboard
            models = data.get("models", {})
            for m_key, m_val in models.items():
                if isinstance(m_val, dict) and "elo" in m_val:
                    clean_id = m_key.lower().replace(" ", "-")
                    self.live_elo_overrides[clean_id] = float(m_val["elo"])
        except Exception as e:
            logger.debug(f"Non-critical: could not ingest canonical leaderboard: {e}")

    def normalize_domain(self, domain_or_prompt: str) -> str:
        """Resolves raw input to canonical domain key."""
        text = domain_or_prompt.strip().lower()
        # Direct exact match
        for canonical in DOMAIN_KEYWORDS.keys():
            if text == canonical or text == canonical.replace("-", "_"):
                return canonical

        # Keyword substring scanning
        for canonical, keywords in DOMAIN_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    return canonical

        # Default fallback domain if unrecognized
        return "deep-research"

    def get_effective_elo(self, model_id: str) -> float:
        """Returns effective public base ELO, incorporating any registered overrides."""
        if model_id in self.live_elo_overrides:
            return self.live_elo_overrides[model_id]

        if model_id in self.models_catalog:
            return float(self.models_catalog[model_id].get("public_elo_lmsys", 1300.0))

        if model_id in self.alternate_free_apis:
            return float(self.alternate_free_apis[model_id].get("public_elo_lmsys", 1300.0))

        return 1300.0

    def compute_model_utility(self, model_id: str, domain: str) -> float:
        """Calculates multi-attribute utility score: Utility(M, D) = sum(w_{D,k} * S_{M,k})."""
        model_meta = self.models_catalog.get(model_id)
        if not model_meta:
            return 0.0

        domain_meta = self.domain_routing_config.get(domain, {})
        weights = domain_meta.get("domain_attribute_weights", {})
        if not weights:
            return 0.0

        attr_scores = model_meta.get("attribute_scores", {})

        # Compute or fallback attributes
        base_elo = self.get_effective_elo(model_id)
        s_elo = max(0.0, min(1.0, (base_elo - 1200.0) / 300.0))
        s_ctx = attr_scores.get(
            "context_window",
            min(1.0, math.log2(max(1, model_meta.get("context_window_tokens", 1048576))) / 21.0)
        )
        s_reas = attr_scores.get(
            "reasoning",
            float(model_meta.get("arena_hard_score_pct", 50.0)) / 100.0
        )
        s_vis = attr_scores.get("multimodal_vision", 0.5)
        s_code = attr_scores.get("coding", float(model_meta.get("arena_hard_score_pct", 50.0)) / 100.0)
        s_speed = attr_scores.get("latency_speed", 0.5)

        computed = (
            weights.get("elo", 0.0) * s_elo +
            weights.get("context_window", 0.0) * s_ctx +
            weights.get("reasoning", 0.0) * s_reas +
            weights.get("multimodal_vision", 0.0) * s_vis +
            weights.get("coding", 0.0) * s_code +
            weights.get("latency_speed", 0.0) * s_speed
        )
        return round(computed, 4)

    def route(self, domain_or_prompt: str) -> Dict[str, Any]:
        """Routes a given domain or task prompt to optimal model."""
        canonical_domain = self.normalize_domain(domain_or_prompt)
        domain_cfg = self.domain_routing_config.get(canonical_domain, {})

        # Evaluate candidate utility scores across catalog
        candidate_scores: List[Tuple[str, float]] = []
        for model_id in self.models_catalog.keys():
            util = self.compute_model_utility(model_id, canonical_domain)
            candidate_scores.append((model_id, util))

        # Sort descending by computed utility
        candidate_scores.sort(key=lambda x: x[1], reverse=True)

        if candidate_scores and candidate_scores[0][1] > 0.0:
            assigned_model = candidate_scores[0][0]
            best_utility = candidate_scores[0][1]
        else:
            assigned_model = domain_cfg.get("assigned_model", "gemini-2.5-flash")
            best_utility = self.compute_model_utility(assigned_model, canonical_domain)

        base_public_elo = self.get_effective_elo(assigned_model)

        return {
            "domain": canonical_domain,
            "routed_model": assigned_model,
            "base_public_elo": base_public_elo,
            "computed_utility_score": best_utility,
            "fallback_model": domain_cfg.get("fallback_model", "gemini-2.5-flash-lite"),
            "alternate_free_api": domain_cfg.get("alternate_free_api", "groq:llama-3.3-70b-versatile"),
            "local_mesh_fallback": domain_cfg.get("local_mesh_fallback", "qwen_38_max"),
            "rate_limit_policy": domain_cfg.get("rate_limit_policy", {}),
            "mathematical_rationale": domain_cfg.get("mathematical_rationale", ""),
            "all_candidates_evaluated": [
                {"model": m, "utility_score": s, "base_elo": self.get_effective_elo(m)}
                for m, s in candidate_scores
            ]
        }

    def route_domain(self, domain: str) -> Dict[str, Any]:
        """Convenience alias matching RFC spec."""
        return self.route(domain)

    def list_domains(self) -> List[str]:
        return list(self.domain_routing_config.keys())

    def list_models(self) -> List[str]:
        return list(self.models_catalog.keys())


def main():
    import sys
    arg = sys.argv[1] if len(sys.argv) > 1 else "deep-research"
    router = DynamicELORouter()
    decision = router.route(arg)
    print(
        f"[DYNAMIC ELO ROUTER] Domain: {decision['domain']} -> "
        f"Model: {decision['routed_model']} "
        f"(Base Public ELO: {decision['base_public_elo']}, "
        f"Utility: {decision['computed_utility_score']})"
    )


if __name__ == "__main__":
    main()
