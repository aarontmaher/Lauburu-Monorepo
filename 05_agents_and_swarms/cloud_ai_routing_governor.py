#!/usr/bin/env python3
"""
================================================================================
Cloud AI Tiered Routing Policy & Dynamic Dispatch Governor
================================================================================
Subsystem: 05_agents_and_swarms/cloud_ai_routing_governor.py
Version: 1.0.0-ROUTING-GOVERNOR
Lauburu Mesh Ecosystem — 2026

Governs "When & Where to Use Cloud AI" with strict cost and latency optimization:
- Local Sovereign First: Qwen MoE (80B A3B) on Apple Silicon Metal + TB4 DMA.
- Tier 1: Gemini 2.0 Flash Thinking / Pro (1,500 free daily reqs) for deep reasoning & distillation.
- Tier 2: Google Jules (Ultra Tier) for async multi-file monorepo PR refactors.
- Tier 3: xAI Grok-2 ($25/mo free tier) for live web facts & adversarial debates.
- Tier 4: Cloudflare Workers AI (10,000 Neurons/day free) for low-latency edge hooks.
================================================================================
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
DATA_DIR = REPO_ROOT / "04_data_and_memory"
OBSIDIAN_DIR = REPO_ROOT / "obsidian_vault" / "07_ARCHITECTURE"

DATA_DIR.mkdir(parents=True, exist_ok=True)
OBSIDIAN_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = DATA_DIR / "cloud_ai_routing_state.json"

# Quota Caps & Free Tiers
CLOUD_AI_TIERS = {
    "local_qwen_moe": {
        "provider": "local_apple_silicon",
        "role": "Default Master Orchestrator, Fast AST, UI Layout, Local MoE Training",
        "daily_quota": 999999,
        "cost_per_req": 0.00,
        "latency_ms": 15.0,
        "best_for": ["ast_validation", "zero_mock_audit", "local_tui", "tb4_training", "code_edits"]
    },
    "gemini_flash_thinking": {
        "provider": "google_ai_studio_free",
        "role": "Deep Multi-Step Reasoning, Mathematical Optimization, Complex Refactors",
        "model_id": "gemini-2.0-flash-thinking-exp-01-21",
        "daily_quota": 1500,
        "cost_per_req": 0.00,
        "latency_ms": 850.0,
        "best_for": ["mathematical_proofs", "complex_architecture", "lora_teacher_distillation", "kinematics_dsp"]
    },
    "gemini_3_1_pro": {
        "provider": "google_ai_studio_free",
        "role": "Lead Cloud Strategic Planning Architect & Macro-System Reasoner (BLOCKED)",
        "model_id": "gemini-3.1-pro-preview",
        "fallback_model_id": "local_qwen_moe",
        "daily_quota": 0,
        "enabled": False,
        "status": "BLOCKED_BY_SOVEREIGN_DIRECTIVE_17PCT_REMAINING",
        "cost_per_req": 0.00,
        "latency_ms": 1100.0,
        "best_for": []
    },
    "gemini_pro_exp": {
        "provider": "google_ai_studio_free",
        "role": "Ultra-Long Context (2M Tokens) (BLOCKED)",
        "model_id": "gemini-2.0-pro-exp-02-05",
        "daily_quota": 0,
        "enabled": False,
        "status": "BLOCKED_BY_SOVEREIGN_DIRECTIVE_17PCT_REMAINING",
        "cost_per_req": 0.00,
        "latency_ms": 1200.0,
        "best_for": []
    },
    "google_jules": {
        "provider": "google_ultra_account",
        "role": "Asynchronous Multi-File GitHub Pull Request Refactoring",
        "model_id": "@google/jules",
        "daily_quota": 500,
        "cost_per_req": 0.00,
        "latency_ms": 60000.0,
        "best_for": ["async_pr_creation", "multi_file_patching", "backlog_resolution"]
    },
    "grok_2_xai": {
        "provider": "xai_free_developer_tier",
        "role": "Live Real-Time Web Facts, Red-Teaming, Devil's Advocate Debate",
        "model_id": "grok-2-1212",
        "daily_quota": 1000,
        "cost_per_req": 0.00,
        "latency_ms": 650.0,
        "best_for": ["live_web_facts", "adversarial_debate", "security_red_team"]
    },
    "nvidia_deepseek_v4_pro": {
        "provider": "nvidia_nim_free_tier",
        "role": "Frontier 1.6T MoE Reasoning, Multi-Node Architecture & Heavy LoRA Teacher Distillation",
        "model_id": "deepseek-ai/deepseek-v4-pro",
        "total_params": "1.6T",
        "active_params": "49B",
        "context_window": "1,000,000 tokens",
        "daily_quota": 2000,
        "cost_per_req": 0.00,
        "latency_ms": 1100.0,
        "best_for": ["frontier_1_6t_reasoning", "heavy_moe_distillation", "macro_system_architecture", "extreme_math"]
    },
    "nvidia_deepseek_v4_flash": {
        "provider": "nvidia_nim_free_tier",
        "role": "High-Speed 284B MoE Coding, 1M Context Codebase Audits & Fast Prototyping",
        "model_id": "deepseek-ai/deepseek-v4-flash",
        "total_params": "284B",
        "active_params": "13B",
        "context_window": "1,000,000 tokens",
        "daily_quota": 5000,
        "cost_per_req": 0.00,
        "latency_ms": 280.0,
        "best_for": ["high_speed_code_gen", "1m_context_repo_audits", "fast_refactoring"]
    },
    "cloudflare_workers_ai": {
        "provider": "cloudflare_free_tier",
        "role": "Edge Webhooks, Durable Objects State Transitions & Micro-Transformers",
        "model_id": "@cf/meta/llama-3.3-70b-instruct",
        "daily_quota": 10000,
        "cost_per_req": 0.00,
        "latency_ms": 120.0,
        "best_for": ["edge_webhooks", "state_machine_transitions", "fast_token_classification"]
    }
}


class CloudAIRoutingGovernor:
    """Intelligent Routing Policy Governor for Local & Cloud AI Model Allocation."""

    def __init__(self):
        self.tiers = CLOUD_AI_TIERS
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        default = {
            "daily_usage": {k: 0 for k in self.tiers.keys()},
            "last_reset": time.strftime("%Y-%m-%d", time.gmtime()),
            "total_cloud_spend_usd": 0.00
        }
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    for k, v in default.items():
                        loaded.setdefault(k, v)
                    return loaded
            except Exception:
                pass
        return default

    def _save_state(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    def route_task(self, domain: str, complexity: str = "medium", estimated_tokens: int = 1000, requires_web: bool = False, is_async_pr: bool = False) -> Dict[str, Any]:
        """
        Calculates the optimal target AI engine based on strict routing policies:
        - Strict $0.00 cost limit
        - Local Qwen MoE for low latency & routine edits
        - DeepSeek V4 Pro (1.6T) on NVIDIA NIM for frontier reasoning & heavy teacher distillation
        - DeepSeek V4 Flash (284B) on NVIDIA NIM for high-speed coding & 1M context audits
        - Gemini Flash Thinking for mathematical/deep reasoning
        - Jules for async GitHub PRs
        - Grok for live web facts / security red-team
        """
        target_model = "local_qwen_moe"
        rationale = "Defaulting to local sovereign Qwen MoE for low latency and zero cost."

        if is_async_pr:
            target_model = "google_jules"
            rationale = "Async multi-file PR refactor routed to Google Jules background agent."
        elif requires_web:
            target_model = "grok_2_xai"
            rationale = "Real-time web retrieval requirement routed to xAI Grok-2."
        elif domain in ["frontier_1_6t_reasoning", "heavy_moe_distillation", "extreme_math"]:
            target_model = "nvidia_deepseek_v4_pro"
            rationale = "Frontier 1.6T MoE reasoning requirement routed to NVIDIA NIM DeepSeek V4 Pro (49B Active)."
        elif domain in ["high_speed_code_gen", "1m_context_repo_audits"] or (estimated_tokens > 100000 and estimated_tokens <= 1000000):
            target_model = "nvidia_deepseek_v4_flash"
            rationale = "1M context high-speed code audit routed to NVIDIA NIM DeepSeek V4 Flash (284B / 13B Active)."
        elif domain in ["system_planning", "macro_architecture", "lens_multimodal_planning"] or "planning" in domain:
            target_model = "local_qwen_moe"
            rationale = "Strategic macro-system planning routed to Local Qwen MoE (Thunderbolt 4) [BLOCKED: Gemini 3.1 Pro preserved at 17% quota]."
        elif domain in ["mathematical_proofs", "kinematics_dsp", "lora_teacher_distillation"] or complexity == "extreme":
            target_model = "local_qwen_moe"
            rationale = f"High complexity task in domain '{domain}' routed to Local Qwen MoE (Thunderbolt 4)."
        elif estimated_tokens > 32000 or domain == "2m_context_repo_indexing":
            target_model = "nvidia_deepseek_v4_flash"
            rationale = "Large context window requirement routed to NVIDIA NIM DeepSeek V4 Flash (Free Tier) [Gemini Pro Exp BLOCKED]."
        elif domain == "edge_webhooks":
            target_model = "cloudflare_workers_ai"
            rationale = "Edge webhook classification routed to Cloudflare Workers AI."

        # Hard Block & Quota Protection Check
        if not self.tiers.get(target_model, {}).get("enabled", True):
            rationale += f" [HARD BLOCK: {target_model} is DISABLED by user directive -> Diverted to local_qwen_moe]"
            target_model = "local_qwen_moe"

        used = self.state["daily_usage"].get(target_model, 0)
        quota = self.tiers[target_model]["daily_quota"]
        if used >= quota and target_model != "local_qwen_moe":
            rationale += f" [FALLBACK: {target_model} daily quota exhausted ({used}/{quota}) -> Falling back to local Qwen MoE]"
            target_model = "local_qwen_moe"

        # Record usage
        self.state["daily_usage"][target_model] = self.state["daily_usage"].get(target_model, 0) + 1
        self._save_state()

        tier_meta = self.tiers[target_model]
        return {
            "chosen_target": target_model,
            "provider": tier_meta["provider"],
            "model_id": tier_meta.get("model_id"),
            "role": tier_meta["role"],
            "expected_latency_ms": tier_meta["latency_ms"],
            "cost_usd": 0.00,
            "rationale": rationale,
            "quota_status": f"{self.state['daily_usage'][target_model]}/{tier_meta['daily_quota']}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }


if __name__ == "__main__":
    gov = CloudAIRoutingGovernor()
    print("=== Cloud AI Tiered Routing Policy Governor ===")
    sample_tasks = [
        {"domain": "ast_validation", "complexity": "low", "estimated_tokens": 500},
        {"domain": "mathematical_proofs", "complexity": "extreme", "estimated_tokens": 4000},
        {"domain": "2m_context_repo_indexing", "complexity": "high", "estimated_tokens": 85000},
        {"domain": "live_web_facts", "complexity": "medium", "requires_web": True},
        {"domain": "async_pr_creation", "complexity": "high", "is_async_pr": True}
    ]

    for t in sample_tasks:
        res = gov.route_task(**t)
        print(f"\nTask Domain: {t['domain']} (Complexity: {t.get('complexity')})")
        print(f"  👉 Routed To: {res['chosen_target']} ({res['provider']})")
        print(f"  ⚡ Latency: {res['expected_latency_ms']}ms | Cost: ${res['cost_usd']:.2f}")
        print(f"  💡 Rationale: {res['rationale']}")
