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
import fcntl
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
DATA_DIR = REPO_ROOT / "04_data_and_memory"
OBSIDIAN_DIR = REPO_ROOT / "obsidian_vault" / "07_ARCHITECTURE"

DATA_DIR.mkdir(parents=True, exist_ok=True)
OBSIDIAN_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = DATA_DIR / "cloud_ai_routing_state.json"
STATE_LOCK_FILE = DATA_DIR / "cloud_ai_routing_state.json.lock"

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
        "role": "Asynchronous Multi-File GitHub Pull Request Refactoring & Repository Architecture",
        "model_id": "@google/jules",
        "daily_quota": 300,
        "cost_per_req": 0.00,
        "latency_ms": 60000.0,
        "best_for": ["async_pr_creation", "multi_file_patching", "backlog_resolution", "codebase_refactor"]
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
    },
    "gemini_4_argon_high": {
        "provider": "antigravity_g1_flash_parity",
        "role": "Primary Frontier Swarm Engine (1.0x Flash Token Parity) for P0 Sellable Apps & Architecture",
        "model_id": "gemini-4-argon-high",
        "token_cost_multiplier_vs_flash": 1.0,
        "use_g1_credits": True,
        "daily_quota": 5000,
        "cost_per_req": 0.00,
        "latency_ms": 420.0,
        "best_for": ["sellable_apps_p0", "argon_same_model_swarm", "production_packaging", "e2e_checkout_audit"]
    },
    "gemini_4_argon_medium": {
        "provider": "antigravity_g1_flash_parity",
        "role": "Balanced High-Throughput Argon Worker (1.0x Flash Token Parity)",
        "model_id": "gemini-4-argon-medium",
        "token_cost_multiplier_vs_flash": 1.0,
        "use_g1_credits": True,
        "daily_quota": 5000,
        "cost_per_req": 0.00,
        "latency_ms": 310.0,
        "best_for": ["ui_component_polish", "test_generation", "parallel_code_review"]
    },
    "gemini_4_argon_low": {
        "provider": "antigravity_g1_flash_parity",
        "role": "Ultra-Fast Argon Micro-Swarm Worker (1.0x Flash Token Parity)",
        "model_id": "gemini-4-argon-low",
        "token_cost_multiplier_vs_flash": 1.0,
        "use_g1_credits": True,
        "daily_quota": 10000,
        "cost_per_req": 0.00,
        "latency_ms": 190.0,
        "best_for": ["lint_triage", "telemetry_verification", "fast_doc_sync"]
    },
    "gemini_3_8_flash_high": {
        "provider": "google_ai_studio_free",
        "role": "Baseline High-Speed Flash Reference Engine (1.0x Token Parity Baseline)",
        "model_id": "gemini-3.8-flash-high",
        "token_cost_multiplier_vs_flash": 1.0,
        "use_g1_credits": True,
        "daily_quota": 1500,
        "cost_per_req": 0.00,
        "latency_ms": 380.0,
        "best_for": ["flash_baseline_audit", "fast_solver_swarm", "dataset_distillation"]
    },
    "gemini_2_5_flash_free": {
        "provider": "google_ai_studio_free",
        "role": "Zero-Cost High-Speed Test & E2E Verification Swarm Worker",
        "model_id": "gemini-2.5-flash",
        "token_cost_multiplier_vs_flash": 0.0,
        "use_g1_credits": False,
        "daily_quota": 1500,
        "cost_per_req": 0.00,
        "latency_ms": 260.0,
        "best_for": ["sellable_e2e_verification", "regression_testing", "doc_generation"]
    },
    "local_tiny_edge_argon_companion": {
        "provider": "local_tiny_edge_metal",
        "role": "Tiny/Edge Local Argon Companion (0.5B Qwen2.5, 397MB RAM) — Zero Device Overload",
        "model_id": "lauburu-lens-argon:latest",
        "params_b": 0.50,
        "ram_gb": 0.40,
        "daily_quota": 999999,
        "cost_per_req": 0.00,
        "latency_ms": 8.0,
        "best_for": ["tiny_edge_local", "screen_lens_ocr_parse", "low_ram_local_syntax"]
    },
    "local_tiny_smollm2": {
        "provider": "local_tiny_edge_metal",
        "role": "Ultra-Light Local Classifier & Telemetry Watcher (SmolLM2-135M, 350MB RAM)",
        "model_id": "SmolLM2-135M-Instruct",
        "params_b": 0.135,
        "ram_gb": 0.35,
        "daily_quota": 999999,
        "cost_per_req": 0.00,
        "latency_ms": 4.5,
        "best_for": ["telemetry_anomaly_filter", "heartbeat_classification", "micro_routing"]
    }
}

# Large-Scale Same-Model Swarm Rule: Homogeneous N-way parallel swarms of the SAME model
# mapped to the highest-ROI project tasks (Sellable Apps P0 first).
LARGE_SCALE_SAME_MODEL_SWARM_RULES: List[Dict[str, Any]] = [
    {
        "swarm_id": "SWARM_SAME_MODEL_01_ARGON_HIGH_16X",
        "priority_rank": "P0_HIGHEST_ROI",
        "homogeneous_model": "gemini-4-argon-high",
        "tier_key": "gemini_4_argon_high",
        "parallel_replicas": 16,
        "token_cost_vs_flash": 1.0,
        "host_ram_impact_gb": 0.0,
        "roi_score": 99.4,
        "target_task": "Finish & Verify All P0 Sellable Apps (Combat Lab, OpenVitals, Screen Lens, Cable Analyzer, Showrunner, Port 4000 Console)",
        "why_same_model_rule": (
            "16x homogeneous Gemini 4 Argon (High) workers share identical AST/checkout prompt cache prefixes, "
            "eliminate cross-model schema drift across all sellable apps, and run at 1.0x Flash token parity with 0 GB local RAM."
        )
    },
    {
        "swarm_id": "SWARM_SAME_MODEL_02_ARGON_MEDIUM_16X",
        "priority_rank": "P0_SELLABLE_UI_UX",
        "homogeneous_model": "gemini-4-argon-medium",
        "tier_key": "gemini_4_argon_medium",
        "parallel_replicas": 16,
        "token_cost_vs_flash": 1.0,
        "host_ram_impact_gb": 0.0,
        "roi_score": 96.8,
        "target_task": "Parallel Shopify Storefront Cart/Webhook Verification & Multi-Platform App Packaging (DMG, APK, PWA)",
        "why_same_model_rule": (
            "16x homogeneous Gemini 4 Argon (Medium) workers validate every pricing tier, SKU bundle, and checkout permalink "
            "in lockstep at 1.0x Flash token cost."
        )
    },
    {
        "swarm_id": "SWARM_SAME_MODEL_06_GOOGLE_FLASH_FREE_16X",
        "priority_rank": "P0_SELLABLE_E2E_VERIFICATION",
        "homogeneous_model": "gemini-2.5-flash",
        "tier_key": "gemini_2_5_flash_free",
        "parallel_replicas": 16,
        "token_cost_vs_flash": 0.0,
        "host_ram_impact_gb": 0.0,
        "roi_score": 95.6,
        "target_task": "16x Parallel E2E Test & Regression Verification Across All 5 Sellable Apps (125+ Test Cases)",
        "why_same_model_rule": (
            "16x homogeneous Gemini Flash Free-Tier workers execute deterministic test assertions in parallel "
            "with zero host RAM consumption and $0.00 API cost."
        )
    },
    {
        "swarm_id": "SWARM_SAME_MODEL_03_DEEPSEEK_V4_FLASH_12X",
        "priority_rank": "P1_FREE_CLOUD_CODE_AUDIT",
        "homogeneous_model": "deepseek-ai/deepseek-v4-flash",
        "tier_key": "nvidia_deepseek_v4_flash",
        "parallel_replicas": 12,
        "token_cost_vs_flash": 0.0,
        "host_ram_impact_gb": 0.0,
        "roi_score": 94.2,
        "target_task": "Full-Monorepo Zero-Mock & Security Audit Across All 5 Commercial Apps + Port 4000 Console",
        "why_same_model_rule": (
            "12x homogeneous DeepSeek V4 Flash free-tier NIM workers partition the repository by subsystem with uniform "
            "AST security rules and zero local VRAM footprint."
        )
    },
    {
        "swarm_id": "SWARM_SAME_MODEL_04_CF_LLAMA33_70B_24X",
        "priority_rank": "P1_EDGE_WEBHOOK_STRESS",
        "homogeneous_model": "@cf/meta/llama-3.3-70b-instruct",
        "tier_key": "cloudflare_workers_ai",
        "parallel_replicas": 24,
        "token_cost_vs_flash": 0.0,
        "host_ram_impact_gb": 0.0,
        "roi_score": 91.5,
        "target_task": "Synthetic Customer Onboarding, License Activation & Entitlement Webhook Stress Testing",
        "why_same_model_rule": (
            "24x homogeneous Cloudflare Workers AI replicas execute sub-120ms edge entitlement checks using free daily Neurons."
        )
    },
    {
        "swarm_id": "SWARM_SAME_MODEL_05_LOCAL_TINY_ARGON_COMPANION_8X",
        "priority_rank": "P1_LOCAL_TINY_EDGE_GUARD",
        "homogeneous_model": "lauburu-lens-argon:latest",
        "tier_key": "local_tiny_edge_argon_companion",
        "parallel_replicas": 8,
        "token_cost_vs_flash": 0.0,
        "host_ram_impact_gb": 0.40,
        "roi_score": 90.1,
        "target_task": "Offline-First Local Edge Telemetry & Screen Lens UI Verification (Strictly <= 0.5B Params)",
        "why_same_model_rule": (
            "8x sequential/batched micro-workers share a single 397MB weight buffer in unified memory, preventing device overload."
        )
    },
    {
        "swarm_id": "SWARM_SAME_MODEL_07_SMOLLM2_135M_TELEMETRY_16X",
        "priority_rank": "P1_LOCAL_MICRO_WATCHDOG",
        "homogeneous_model": "SmolLM2-135M-Instruct",
        "tier_key": "local_tiny_smollm2",
        "parallel_replicas": 16,
        "token_cost_vs_flash": 0.0,
        "host_ram_impact_gb": 0.35,
        "roi_score": 89.4,
        "target_task": "Continuous Live Device Telemetry, RAM Sanctuary Guard & Token Parity Anomaly Detection",
        "why_same_model_rule": (
            "16x batched micro-requests on a single 135M parameter model (350MB RAM) classify telemetry at <5ms latency."
        )
    }
]


class CloudAIRoutingGovernor:
    """Intelligent Routing Policy Governor for Local & Cloud AI Model Allocation."""

    def __init__(self):
        self.tiers = CLOUD_AI_TIERS
        self.same_model_swarm_rules = LARGE_SCALE_SAME_MODEL_SWARM_RULES
        self.state = self._load_state()

    def _default_state(self) -> Dict[str, Any]:
        return {
            "daily_usage": {k: 0 for k in self.tiers.keys()},
            "last_reset": time.strftime("%Y-%m-%d", time.gmtime()),
            "total_cloud_spend_usd": 0.00
        }

    def _load_state_unlocked(self) -> Dict[str, Any]:
        default = self._default_state()
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    for k, v in default.items():
                        loaded.setdefault(k, v)
                    for tier_k in self.tiers.keys():
                        loaded["daily_usage"].setdefault(tier_k, 0)
                    return loaded
            except Exception:
                pass
        return default

    def _load_state(self) -> Dict[str, Any]:
        STATE_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_LOCK_FILE, "a+", encoding="utf-8") as lock_f:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_SH)
            try:
                return self._load_state_unlocked()
            finally:
                fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)

    def _save_state_unlocked(self) -> None:
        fd, tmp_path = tempfile.mkstemp(dir=str(DATA_DIR), prefix=".cloud_routing_", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_f:
                json.dump(self.state, tmp_f, indent=2)
                tmp_f.flush()
                os.fsync(tmp_f.fileno())
            os.replace(tmp_path, STATE_FILE)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    def _save_state(self) -> None:
        STATE_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_LOCK_FILE, "a+", encoding="utf-8") as lock_f:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
            try:
                self._save_state_unlocked()
            finally:
                fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)

    def get_high_roi_same_model_swarms(self) -> List[Dict[str, Any]]:
        """Returns the ranked Large-Scale Same-Model Swarm configurations ordered by ROI."""
        return sorted(self.same_model_swarm_rules, key=lambda r: r["roi_score"], reverse=True)

    def route_task(self, domain: str, complexity: str = "medium", estimated_tokens: int = 1000, requires_web: bool = False, is_async_pr: bool = False) -> Dict[str, Any]:
        """
        Calculates the optimal target AI engine based on strict routing policies:
        - Strict $0.00 cost limit / 1.0x Argon-Flash token parity
        - Gemini 4 Argon (High/Medium/Low) for P0 Sellable Apps & Same-Model Swarms (0 GB local RAM)
        - Local Tiny/Edge models (<=8B, <=0.5B under pressure) when tiny_edge_local is requested
        - Local Qwen MoE for legacy default / system_planning fallback
        - DeepSeek V4 Pro (1.6T) on NVIDIA NIM for frontier reasoning & heavy teacher distillation
        - DeepSeek V4 Flash (284B) on NVIDIA NIM for high-speed coding & 1M context audits
        - Gemini Flash Thinking for mathematical/deep reasoning
        - Jules for async GitHub PRs
        - Grok for live web facts / security red-team
        """
        target_model = "local_qwen_moe"
        rationale = "Defaulting to local sovereign Qwen MoE for low latency and zero cost."

        if domain in ["sellable_apps_p0", "argon_same_model_swarm", "production_packaging", "e2e_checkout_audit"]:
            target_model = "gemini_4_argon_high"
            rationale = "P0 Sellable App / High-ROI task routed to Gemini 4 Argon High (1.0x Flash token parity, 0 GB local RAM load)."
        elif domain in ["ui_component_polish", "test_generation", "parallel_code_review"]:
            target_model = "gemini_4_argon_medium"
            rationale = "Parallel UI/test verification routed to Gemini 4 Argon Medium (1.0x Flash token parity)."
        elif domain in ["lint_triage", "telemetry_verification", "fast_doc_sync"]:
            target_model = "gemini_4_argon_low"
            rationale = "High-frequency telemetry/lint task routed to Gemini 4 Argon Low (1.0x Flash token parity)."
        elif domain in ["sellable_e2e_verification", "regression_testing", "doc_generation"]:
            target_model = "gemini_2_5_flash_free"
            rationale = "Parallel E2E test verification routed to Gemini 2.5 Flash Free Tier (0 GB local RAM)."
        elif domain in ["tiny_edge_local", "screen_lens_ocr_parse", "low_ram_local_syntax"]:
            target_model = "local_tiny_edge_argon_companion"
            rationale = "Local execution restricted to Tiny/Edge Argon Companion (0.5B, 397MB RAM) to prevent device overload."
        elif domain in ["telemetry_anomaly_filter", "heartbeat_classification", "micro_routing"]:
            target_model = "local_tiny_smollm2"
            rationale = "Ultra-light local telemetry filter routed to SmolLM2-135M (0.135B, 350MB RAM)."
        elif is_async_pr or domain in ["async_pr_creation", "multi_file_patching", "backlog_resolution"]:
            target_model = "google_jules"
            rationale = "Strategic asynchronous PR creation routed to Google Jules Ultra Plan (300 daily sessions @ $0.00 cost)."
        elif requires_web:
            target_model = "grok_2_xai"
            rationale = "Real-time web retrieval requirement routed to xAI Grok-2."
        elif domain in ["frontier_1_6t_reasoning", "heavy_moe_distillation", "extreme_math"]:
            target_model = "nvidia_deepseek_v4_pro"
            rationale = "Frontier 1.6T MoE reasoning requirement routed to NVIDIA NIM DeepSeek V4 Pro (49B Active)."
        elif domain in ["high_speed_code_gen", "1m_context_repo_audits"] or (estimated_tokens > 100000 and estimated_tokens <= 1000000):
            target_model = "nvidia_deepseek_v4_flash"
            rationale = "1M context high-speed code audit routed to NVIDIA NIM DeepSeek V4 Flash (284B / 13B Active)."
        elif domain in ["mathematical_proofs", "kinematics_dsp", "lora_teacher_distillation"]:
            target_model = "gemini_flash_thinking"
            rationale = f"Deep reasoning / mathematical proof in domain '{domain}' routed to Gemini Flash Thinking Exp (Free Tier, 1,500 RPD)."
        elif estimated_tokens > 32000 or domain == "2m_context_repo_indexing":
            target_model = "nvidia_deepseek_v4_flash"
            rationale = "Large context window requirement routed to NVIDIA NIM DeepSeek V4 Flash (Free Tier) [Gemini Pro Exp BLOCKED]."
        elif domain == "edge_webhooks":
            target_model = "cloudflare_workers_ai"
            rationale = "Edge webhook classification routed to Cloudflare Workers AI."

        STATE_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_LOCK_FILE, "a+", encoding="utf-8") as lock_f:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
            try:
                self.state = self._load_state_unlocked()

                # Hard Block & Quota Protection Check
                if not self.tiers.get(target_model, {}).get("enabled", True):
                    rationale += f" [HARD BLOCK: {target_model} is DISABLED by user directive -> Diverted to local_qwen_moe]"
                    target_model = "local_qwen_moe"

                used = self.state["daily_usage"].get(target_model, 0)
                quota = self.tiers[target_model]["daily_quota"]
                if used >= quota and target_model != "local_qwen_moe":
                    rationale += f" [FALLBACK: {target_model} daily quota exhausted ({used}/{quota}) -> Falling back to local Qwen MoE]"
                    target_model = "local_qwen_moe"

                # Record usage atomically under exclusive lock
                self.state["daily_usage"][target_model] = self.state["daily_usage"].get(target_model, 0) + 1
                self._save_state_unlocked()
                current_usage = self.state["daily_usage"][target_model]
            finally:
                fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)

        tier_meta = self.tiers[target_model]
        return {
            "chosen_target": target_model,
            "provider": tier_meta["provider"],
            "model_id": tier_meta.get("model_id"),
            "role": tier_meta["role"],
            "expected_latency_ms": tier_meta["latency_ms"],
            "cost_usd": 0.00,
            "token_cost_multiplier_vs_flash": tier_meta.get("token_cost_multiplier_vs_flash", 1.0),
            "rationale": rationale,
            "quota_status": f"{current_usage}/{tier_meta['daily_quota']}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }


if __name__ == "__main__":
    gov = CloudAIRoutingGovernor()
    print("=== Cloud AI Tiered Routing Policy Governor (Argon Parity + Free Cloud + Tiny/Edge Local) ===")
    sample_tasks = [
        {"domain": "sellable_apps_p0", "complexity": "high", "estimated_tokens": 4000},
        {"domain": "tiny_edge_local", "complexity": "low", "estimated_tokens": 500},
        {"domain": "ast_validation", "complexity": "low", "estimated_tokens": 500},
        {"domain": "mathematical_proofs", "complexity": "extreme", "estimated_tokens": 4000},
        {"domain": "2m_context_repo_indexing", "complexity": "high", "estimated_tokens": 85000},
        {"domain": "live_web_facts", "complexity": "medium", "requires_web": True},
        {"domain": "async_pr_creation", "complexity": "high", "is_async_pr": True}
    ]

    for t in sample_tasks:
        res = gov.route_task(**t)
        print(f"\nTask Domain: {t['domain']} (Complexity: {t.get('complexity')})")
        print(f"  👉 Routed To: {res['chosen_target']} ({res['provider']}) | Model: {res.get('model_id')}")
        print(f"  ⚡ Latency: {res['expected_latency_ms']}ms | Cost: ${res['cost_usd']:.2f}")
        print(f"  💡 Rationale: {res['rationale']}")

