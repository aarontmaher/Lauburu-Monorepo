#!/usr/bin/env python3
"""
================================================================================
Lauburu Sovereign Mesh: Dynamic API Provider Registry
================================================================================
Subsystem: 05_agents_and_swarms/dynamic_api_provider_registry.py
Version: 1.0.0-SOVEREIGN-PROVIDER-REGISTRY

Role:
  Scans .env for any API keys (Anthropic/Claude, OpenAI/ChatGPT, Mistral,
  Together, Groq, etc.) and dynamically registers them into the quota pool
  with correct daily caps. Reports NOT_CONFIGURED cleanly for absent keys.

  Enables the ROI cron to adapt automatically when new API keys are added.
  Rule #0: No key values are printed — sovereign masking enforced.
================================================================================
"""
import os
import re
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional, Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [APIProviderRegistry] %(message)s"
)
log = logging.getLogger("APIProviderRegistry")

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
ENV_FILE = REPO_ROOT / ".env"
REGISTRY_OUT = REPO_ROOT / "04_data_and_memory/dynamic_provider_registry.json"

# ── Provider definitions: env var -> provider metadata ────────────────────────
# Each entry maps one or more env var names to provider config.
PROVIDER_CATALOG: Dict[str, Dict[str, Any]] = {
    # ── Already integrated (free-tier) ────────────────────────────────────────
    "GEMINI_API_KEY": {
        "name": "Google AI Studio (Gemini)",
        "alias": "google_gemini",
        "daily_cap_free": 1500,
        "daily_cap_paid": 999999,
        "cost_per_1k_tokens": 0.0,
        "recommended_task": "Long-context code review, LoRA instruction generation",
        "payload_tier": "LONG_CONTEXT_AST",
        "reset_time_aest": "10:00",
        "status": "FREE_TIER",
    },
    "NVIDIA_NIM_API_KEY": {
        "name": "NVIDIA NIM (DeepSeek V4 Pro)",
        "alias": "nvidia_nim",
        "daily_cap_free": 2000,
        "daily_cap_paid": 999999,
        "cost_per_1k_tokens": 0.0,
        "recommended_task": "Kernel synthesis, SIMD vectorization, heavy refactoring",
        "payload_tier": "HEAVY_ALGORITHMIC_CODING",
        "reset_time_aest": "10:00",
        "status": "FREE_TIER",
    },
    "XAI_API_KEY": {
        "name": "xAI (Grok-2)",
        "alias": "xai_grok",
        "daily_cap_free": 1000,
        "daily_cap_paid": 999999,
        "cost_per_1k_tokens": 0.0,
        "recommended_task": "Adversarial red-team, edge-case testing, vulnerability audit",
        "payload_tier": "ADVERSARIAL_RED_TEAM",
        "reset_time_aest": "10:00",
        "status": "FREE_TIER",
    },
    "CLOUDFLARE_API_TOKEN": {
        "name": "Cloudflare Workers AI (Llama 3.3 70B)",
        "alias": "cloudflare_ai",
        "daily_cap_free": 800,
        "daily_cap_paid": 999999,
        "cost_per_1k_tokens": 0.0,
        "recommended_task": "Edge triage, JSON schema validation, telemetry classification",
        "payload_tier": "EDGE_TRIAGE_AND_JSON",
        "reset_time_aest": "10:00",
        "status": "FREE_TIER",
    },
    # ── Dynamically registered if key appears ─────────────────────────────────
    "ANTHROPIC_API_KEY": {
        "name": "Anthropic Claude (claude-3-5-haiku / claude-3-7-sonnet)",
        "alias": "anthropic_claude",
        "daily_cap_free": 0,          # No free tier; usage capped by $ budget
        "daily_cap_paid": 5000,       # Conservative default — override via ANTHROPIC_DAILY_CAP
        "cost_per_1k_tokens": 0.80,   # claude-3-5-haiku input price (USD/MTok = $0.80)
        "recommended_task": "High-fidelity architecture synthesis, long-context diff review",
        "payload_tier": "PREMIUM_ARCHITECTURE",
        "reset_time_aest": "Never (monthly quota)",
        "status": "NOT_CONFIGURED",
    },
    "OPENAI_API_KEY": {
        "name": "OpenAI (gpt-4o-mini / gpt-4.1-nano)",
        "alias": "openai_chatgpt",
        "daily_cap_free": 0,
        "daily_cap_paid": 3000,       # Conservative default
        "cost_per_1k_tokens": 0.15,   # gpt-4o-mini input (USD/MTok = $0.15)
        "recommended_task": "Structured JSON output, function-calling, embeddings",
        "payload_tier": "STRUCTURED_JSON_FUNCTION_CALLING",
        "reset_time_aest": "Never (monthly quota)",
        "status": "NOT_CONFIGURED",
    },
    "MISTRAL_API_KEY": {
        "name": "Mistral AI (mistral-small / codestral)",
        "alias": "mistral_ai",
        "daily_cap_free": 0,
        "daily_cap_paid": 2000,
        "cost_per_1k_tokens": 0.10,
        "recommended_task": "Code completion, fill-in-middle, fast syntax tasks",
        "payload_tier": "FAST_CODE_COMPLETION",
        "reset_time_aest": "Never (monthly quota)",
        "status": "NOT_CONFIGURED",
    },
    "TOGETHER_API_KEY": {
        "name": "Together AI (Llama 3.3 70B / DeepSeek-R1)",
        "alias": "together_ai",
        "daily_cap_free": 1000,       # $25 free credit on signup
        "daily_cap_paid": 5000,
        "cost_per_1k_tokens": 0.18,
        "recommended_task": "Bulk inference, speculative drafts, auxiliary verification",
        "payload_tier": "BULK_SPECULATIVE_DRAFTS",
        "reset_time_aest": "Never (credit-based)",
        "status": "NOT_CONFIGURED",
    },
    "GROQ_API_KEY": {
        "name": "Groq (llama-3.3-70b-versatile)",
        "alias": "groq_ai",
        "daily_cap_free": 14400,      # 14,400 RPD on free tier (10 RPM limit)
        "daily_cap_paid": 999999,
        "cost_per_1k_tokens": 0.0,
        "recommended_task": "Ultra-low-latency inference, real-time streaming, sub-100ms TTFT",
        "payload_tier": "ULTRA_LOW_LATENCY",
        "reset_time_aest": "10:00",
        "status": "NOT_CONFIGURED",
    },
    "DEEPSEEK_API_KEY": {
        "name": "DeepSeek API (deepseek-coder-v3 / deepseek-r1)",
        "alias": "deepseek_api",
        "daily_cap_free": 0,
        "daily_cap_paid": 3000,
        "cost_per_1k_tokens": 0.014,  # Extremely cheap ($0.014/MTok input)
        "recommended_task": "Deep algorithmic reasoning, formal proofs, math olympiad solving",
        "payload_tier": "DEEP_REASONING",
        "reset_time_aest": "Never (monthly quota)",
        "status": "NOT_CONFIGURED",
    },
}

# Alternative env var aliases
ENV_ALIASES = {
    "CLAUDE_API_KEY": "ANTHROPIC_API_KEY",
    "CHATGPT_API_KEY": "OPENAI_API_KEY",
    "OPENAI_SECRET_KEY": "OPENAI_API_KEY",
    "ANTHROPIC_KEY": "ANTHROPIC_API_KEY",
    "CF_API_TOKEN": "CLOUDFLARE_API_TOKEN",
    "CLOUDFLARE_TOKEN": "CLOUDFLARE_API_TOKEN",
}


def _load_env_vars() -> Dict[str, str]:
    """Loads all env vars from .env without exposing values."""
    env_vars = {}
    if not ENV_FILE.exists():
        return env_vars
    try:
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env_vars[k.strip()] = v.strip().strip('"').strip("'")
    except Exception as e:
        log.warning(f"Failed to read .env: {e}")
    # Also check process environment
    for k, v in os.environ.items():
        if k not in env_vars and v:
            env_vars[k] = v
    return env_vars


def _resolve_alias(key: str) -> str:
    """Resolves an env var alias to its canonical key."""
    return ENV_ALIASES.get(key, key)


def scan_and_build_registry() -> Dict[str, Any]:
    """
    Scans .env and os.environ for known API keys.
    Returns the full provider registry with CONFIGURED/NOT_CONFIGURED status.
    Never logs actual key values.
    """
    env_vars = _load_env_vars()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    registered: Dict[str, Any] = {}
    configured_count = 0
    free_tier_count = 0
    paid_tier_count = 0

    for canonical_key, config in PROVIDER_CATALOG.items():
        # Check aliases too
        found_key = None
        for env_k in env_vars:
            resolved = _resolve_alias(env_k)
            if resolved == canonical_key:
                found_key = env_k
                break

        alias = config["alias"]
        entry = dict(config)  # copy

        if found_key:
            key_val = env_vars[found_key]
            # Validate: must be non-empty and reasonably long (not a placeholder)
            is_valid = (
                len(key_val) > 20
                and key_val.lower() not in ("your_key_here", "xxx", "placeholder", "none", "null", "")
            )
            if is_valid:
                entry["status"] = "CONFIGURED"
                entry["env_var"] = found_key
                entry["key_prefix"] = key_val[:8] + "...[SOVEREIGN_MASKED]"
                # Override daily_cap if a custom override exists
                cap_override_key = f"{canonical_key.replace('_KEY','').replace('_TOKEN','')}_DAILY_CAP"
                if cap_override_key in env_vars:
                    try:
                        entry["daily_cap_paid"] = int(env_vars[cap_override_key])
                    except ValueError:
                        pass
                configured_count += 1
                if entry["cost_per_1k_tokens"] == 0.0:
                    free_tier_count += 1
                else:
                    paid_tier_count += 1
                log.info(f"✅ {config['name']}: CONFIGURED ({entry['key_prefix']})")
            else:
                entry["status"] = "PLACEHOLDER_DETECTED"
                entry["env_var"] = found_key
                log.warning(f"⚠️ {config['name']}: key found but looks like a placeholder")
        else:
            entry["status"] = "NOT_CONFIGURED"
            entry["env_var"] = canonical_key
            log.info(f"— {config['name']}: NOT_CONFIGURED")

        registered[alias] = entry

    # Build effective quota pool (only CONFIGURED providers)
    effective_pool = {
        alias: {
            "name": cfg["name"],
            "daily_cap": cfg["daily_cap_free"] if cfg["cost_per_1k_tokens"] == 0.0 else cfg["daily_cap_paid"],
            "is_free": cfg["cost_per_1k_tokens"] == 0.0,
            "payload_tier": cfg["payload_tier"],
            "recommended_task": cfg["recommended_task"],
        }
        for alias, cfg in registered.items()
        if cfg["status"] == "CONFIGURED"
    }

    total_pooled_cap = sum(p["daily_cap"] for p in effective_pool.values())

    registry = {
        "timestamp_utc": ts,
        "scanner_version": "1.0.0",
        "env_file": str(ENV_FILE),
        "total_providers_scanned": len(PROVIDER_CATALOG),
        "configured_count": configured_count,
        "free_tier_count": free_tier_count,
        "paid_tier_count": paid_tier_count,
        "total_effective_daily_cap": total_pooled_cap,
        "effective_quota_pool": effective_pool,
        "all_providers": registered,
    }

    REGISTRY_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_OUT, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

    log.info(
        f"Registry written: {configured_count} configured, "
        f"{len(PROVIDER_CATALOG) - configured_count} not configured. "
        f"Total daily cap: {total_pooled_cap:,} req/day"
    )
    return registry


def get_provider_status(alias: str) -> str:
    """Quick lookup: returns CONFIGURED / NOT_CONFIGURED / PLACEHOLDER_DETECTED."""
    if REGISTRY_OUT.exists():
        try:
            data = json.loads(REGISTRY_OUT.read_text())
            provider = data.get("all_providers", {}).get(alias, {})
            return provider.get("status", "UNKNOWN")
        except Exception:
            pass
    # Fallback: live scan
    registry = scan_and_build_registry()
    return registry["all_providers"].get(alias, {}).get("status", "UNKNOWN")


def get_effective_pool() -> Dict:
    """Returns only the active (CONFIGURED) providers."""
    if REGISTRY_OUT.exists():
        try:
            data = json.loads(REGISTRY_OUT.read_text())
            return data.get("effective_quota_pool", {})
        except Exception:
            pass
    return scan_and_build_registry().get("effective_quota_pool", {})


if __name__ == "__main__":
    print("=" * 70)
    print("⚡ DYNAMIC API PROVIDER REGISTRY — Lauburu Sovereign Mesh")
    print("=" * 70)
    reg = scan_and_build_registry()
    print(f"\n📊 Summary: {reg['configured_count']} / {reg['total_providers_scanned']} providers configured")
    print(f"   Free tier: {reg['free_tier_count']} | Paid: {reg['paid_tier_count']}")
    print(f"   Total effective daily cap: {reg['total_effective_daily_cap']:,} req/day\n")
    print("Provider Status:")
    for alias, cfg in reg["all_providers"].items():
        icon = "✅" if cfg["status"] == "CONFIGURED" else ("⚠️" if "PLACEHOLDER" in cfg["status"] else "—")
        print(f"  {icon} {cfg['name']}: {cfg['status']}")
    print(f"\n📁 Registry written → {REGISTRY_OUT}")
