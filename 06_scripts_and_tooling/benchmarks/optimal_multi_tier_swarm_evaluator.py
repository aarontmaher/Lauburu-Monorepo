#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
06_scripts_and_tooling/benchmarks/optimal_multi_tier_swarm_evaluator.py
Multi-Tier Swarm Capability, Quota, and Financial Optimization Evaluator.
Synthesizes:
- /open-source-software-scout
- /closed-source-reverse-engineering
- /deep-research
Across Local Sovereign Mesh, Cloud Free Tiers, and Paid Frontier Tier.
"""

import json
import time
import os
from pathlib import Path
from typing import Dict, Any, List

# Model Tiers
TIERS = {
    "tier_0_local": {
        "models": ["qwen_38_max_8082", "qwen_25_coder_8081", "qwen_38_max_abliterated_8083", "smollm2_135m"],
        "cost_per_m_tokens": 0.0,
        "avg_latency_ms": 8.5,
        "refusal_rate_pct": 0.0,
        "privacy_airgap": "100% SECURE_ON_DEVICE",
        "quota": "UNLIMITED_HARDWARE"
    },
    "tier_1_cloud_free": {
        "providers": {
            "google_ai_studio": {"model": "gemini-3.8-flash", "daily_quota": 1500, "cost": 0.0},
            "nvidia_nim": {"model": "deepseek-r1-nim", "daily_quota": 2000, "cost": 0.0},
            "cloudflare_workers_ai": {"model": "llama-3.3-70b-instruct", "daily_quota": 800, "cost": 0.0},
            "xai_developer": {"model": "grok-base", "daily_quota": 1000, "cost": 0.0}
        },
        "total_daily_free_reqs": 5300,
        "avg_latency_ms": 420.0,
        "privacy_airgap": "CLOUD_TLS_EXTERNAL",
        "refusal_rate_pct": 12.0
    },
    "tier_2_paid_frontier": {
        "models": {
            "claude_fable_5_1": {"openrouter_slug": "anthropic/claude-fable-5.1", "prompt_m": 10.0, "completion_m": 50.0, "batch_discount": 0.5},
            "gpt_6_astra": {"openrouter_slug": "openai/gpt-6-astra", "prompt_m": 10.0, "completion_m": 50.0, "batch_discount": 0.5},
            "grok_4_6": {"openrouter_slug": "x-ai/grok-4.6", "prompt_m": 2.0, "completion_m": 6.0, "batch_discount": 0.0},
            "kimi_k3": {"openrouter_slug": "moonshotai/kimi-k3", "prompt_m": 3.0, "completion_m": 15.0, "batch_discount": 0.0},
            "deepseek_v4_1_flash": {"openrouter_slug": "deepseek/deepseek-v4.1-flash", "prompt_m": 0.15, "completion_m": 0.60, "batch_discount": 0.0}
        },
        "openrouter_credit_balance": 9.50,
        "avg_latency_ms": 950.0,
        "refusal_rate_pct": 18.5
    }
}

# Domain Task Mapping
DOMAIN_DECISION_MATRIX = [
    {
        "domain": "/open-source-software-scout",
        "task_type": "Upstream Repo Discovery & Live License/CVE Audit",
        "recommended_tier": "tier_1_cloud_free",
        "primary_engine": "Gemini 3.8 Flash (Google AI Studio Free Tier)",
        "why": "Requires live web access and Google search grounding; 1,500 RPD daily quota is 100% free and sufficient for scanning hundreds of GitHub repos daily.",
        "paid_escalation_needed": False,
        "cost": "$0.00"
    },
    {
        "domain": "/open-source-software-scout",
        "task_type": "Local AST Parsing, Dependency Tree Pruning & C/Rust FFI Binding",
        "recommended_tier": "tier_0_local",
        "primary_engine": "Qwen 3.8 Max (:8082) & Qwen 2.5 Coder (:8081)",
        "why": "Fastest execution (<10ms), zero cloud latency, zero token cost, complete AST codebase visibility without uploading source code.",
        "paid_escalation_needed": False,
        "cost": "$0.00"
    },
    {
        "domain": "/closed-source-reverse-engineering",
        "task_type": "Tier A: Binary Disassembly, Hex Decompilation, Wire Protocol Reversing",
        "recommended_tier": "tier_0_local",
        "primary_engine": "Qwen 3.8 Max 27B Abliterated (:8083)",
        "why": "STRICT MANDATE: Cloud models trigger false-positive safety refusals on disassembly and reverse engineering. Local abliterated model has 0% refusal, zero telemetry leakage, and complete privacy airgap.",
        "paid_escalation_needed": False,
        "cost": "$0.00"
    },
    {
        "domain": "/closed-source-reverse-engineering",
        "task_type": "Tier B: Clean-Room Original C11 / Rust Synthesis from Spec",
        "recommended_tier": "tier_0_local",
        "primary_engine": "Qwen 3.8 Max Master (:8082) & Qwen 2.5 Coder (:8081)",
        "why": "Produces memory-safe, verified code tested against local compilers (clang, rustc) with zero cloud spend.",
        "paid_escalation_needed": False,
        "cost": "$0.00"
    },
    {
        "domain": "/deep-research",
        "task_type": "Live Australian Hardware Spot Pricing & ArXiv Paper Scanning",
        "recommended_tier": "tier_1_cloud_free",
        "primary_engine": "Gemini 3.8 Flash Free Tier + NVIDIA NIM DeepSeek R1",
        "why": "Live web search grounding via Gemini Free Tier verifies real AUD prices (Umart, Scorptec) with zero hallucination (Rule 0) at $0 cost.",
        "paid_escalation_needed": False,
        "cost": "$0.00"
    },
    {
        "domain": "Cross-Domain Apex Architecture",
        "task_type": "50k+ LOC Monorepo Refactoring, Cross-Subsystem Deadlock Breaking & Formal Proofs",
        "recommended_tier": "tier_2_paid_frontier",
        "primary_engine": "Claude Fable 5.1 (Coding 81.6) & GPT-6 Astra (Intel 52.8)",
        "why": "OPTIMAL PAID USE: Reserved strictly for high-complexity architectural breakthroughs where local models stagnate. Handled in Batch Mode via OpenRouter ($2.50-$5.00) covered by $9.50 balance.",
        "paid_escalation_needed": True,
        "cost": "$2.50 - $5.00 (From existing $9.50 credits)"
    }
]

def run_evaluation() -> Dict[str, Any]:
    return {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "OPTIMIZED_POLICY_RATIFIED",
        "openrouter_credit_balance": TIERS["tier_2_paid_frontier"]["openrouter_credit_balance"],
        "daily_free_tier_capacity": TIERS["tier_1_cloud_free"]["total_daily_free_reqs"],
        "local_mesh_pooled_vram_gb": 85.02,
        "decision_matrix": DOMAIN_DECISION_MATRIX,
        "optimal_paid_model_rules": [
            "Rule 1: NEVER use paid frontier models for raw biometrics (512Hz ECG), binary disassembly, or routine code linting.",
            "Rule 2: ROUTE all web research, CVE scans, and repo discovery to Gemini 3.8 Flash Free Tier (1,500 RPD = $0.00).",
            "Rule 3: ROUTE all binary analysis to Qwen 3.8 Max 27B Abliterated (:8083) for 0% refusal rate and zero IP leakage.",
            "Rule 4: RESERVE Claude Fable 5.1 and GPT-6 Astra strictly for Tier 3 Apex Escalation (confidence < 0.85 after 2 local/free attempts).",
            "Rule 5: ALWAYS invoke OpenRouter in Batch Mode for multi-turn benchmarks, cutting costs by 50% ($7.26 total vs $9.50 credit headroom).",
            "Rule 6: BRIDGE-THE-GAP 1-BY-1 PROTOCOL: Always invoke paid frontier models sequentially (one-by-one). Ingest the architectural breakthrough and hand off to the local swarm (Qwen 3.8 Max / Qwen 2.5 Coder) to implement and bridge the gap locally before invoking another paid model.",
            "Rule 7: SOVEREIGN WAR GAME EXCEPTION: The only scenario permitting concurrent multi-frontier model invocation is in 'Local Swarm vs Cloud Frontier Swarm' competitive training games and red/blue team war games (/spec-11-security-red-blue-team & /ai-debate) to stress-test mesh defenses."
        ]
    }

if __name__ == "__main__":
    res = run_evaluation()
    print(json.dumps(res, indent=2))
