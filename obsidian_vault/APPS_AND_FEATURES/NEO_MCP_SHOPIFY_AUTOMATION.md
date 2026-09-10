---
title: "Neo MCP Autonomous Shopify & E-Commerce Automation Engine"
tags: [shopify, neo_mcp, ecommerce, combat_apparel, rashguard, shorts, bjj, ads, social_media, lora, spec11]
updated: "2026-09-05"
---

# 🥋 Neo MCP: Sovereign Shopify Account Automation & Continuous E-Commerce Benchmarking
- Related: [[Index]] | [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]] | [[CANONICAL_PROJECT_AND_STORAGE_RULE]] | [[AI_DEBATE_NEO_INTEGRATION]]

## 📋 Architectural Overview
The **Neo MCP Server** (`neo-mcp`) transforms local open-source LLMs (Mistral-Nemo & Qwen on `:8081` and `:8082`) into an autonomous e-commerce operator capable of:
1. **Fully Automating Shopify Operations:** Direct GraphQL 2026-04 cart creation, product queries, and athlete discount checkout generation.
2. **Ordering Custom Combat Apparel:** Specification of the **Lauburu Exact Ghost Rashguard** and **Ghost Fight Shorts** bundle, custom back sublimation, and sizing with verified 25% Champion discounts.
3. **Generating Direct-Response Ads:** Multi-hook copy generation, BJJ pain-point targeting (waistband silicone grip, anti-ride up, flatlock anti-chafing), and high-detail diffusion image prompts for SDXL/Flux.
4. **Autonomous Social Media Management:** 7-day multi-channel content calendars across Instagram, TikTok, Reels, and X/Twitter timed to peak martial arts training windows.
5. **Spec-11 Red/Blue Team Security:** Constant-time HMAC SHA256 signature verification for incoming Shopify webhooks and anti-price tampering gates.
6. **Continuous Overnight Benchmarking:** Background trainer daemon harvesting validated LoRA instruction and DPO pairs into `lora_datasets/neo_ecommerce_continuous_lora.jsonl` with real-time TUI telemetry.

---

## 🛠️ Neo MCP Tool Catalog

| Tool Name | Parameters | Capabilities | Local AI Shard |
| :--- | :--- | :--- | :--- |
| `order_custom_combat_gear` | `item_type`, `size`, `quantity`, `custom_name`, `member_tier` | Headless Shopify CartCreate mutation, line-item pricing, custom sublimation attributes, and instant checkout URL. | Deterministic / `:8081` |
| `develop_combat_sports_ad_creative` | `product`, `target_audience`, `platform` | 3 scroll-stopping hooks, 100-word body copy, discount CTA (`ROLL20`), and cinematic 8K diffusion visual prompt. | Local Metal GPU (`:8081`) |
| `schedule_social_media_campaign` | `campaign_theme`, `days` | Multi-day posting schedule, video hook concepts, fighter-optimized post times (AEST), and 10 targeted hashtags. | Local Metal GPU (`:8081`) |
| `run_ecommerce_benchmark` | `iterations` | Benchmarks local model throughput (tokens/sec), JSON adherence, and latency on e-commerce tasks. | Local Metal GPU (`:8081`) |
| `verify_webhook_signature` | `raw_payload`, `hmac_header`, `secret` | Spec-11 constant-time cryptographic verification (`hmac.compare_digest`) preventing webhook spoofing. | Local Python Ctypes |

---

## 🛍️ Custom Combat Gear Product Specifications

```json
{
  "rashguard": {
    "title": "Lauburu Exact Ghost Rashguard",
    "price_aud": 75.00,
    "variant_id": "gid://shopify/ProductVariant/4819201",
    "features": "4-way compression, silicone inner grip, flatlock seams, sublimated Lauburu cross"
  },
  "shorts": {
    "title": "Lauburu Exact Ghost Fight Shorts",
    "price_aud": 65.00,
    "variant_id": "gid://shopify/ProductVariant/4819202",
    "features": "Micro-ripstop polyester, elastic + velcro closure, high-slit guard mobility"
  },
  "bundle": {
    "title": "Lauburu Combat Set Bundle (Ghost Rashguard + Fight Shorts)",
    "price_aud": 120.00,
    "variant_id": "gid://shopify/ProductVariant/4819203",
    "champion_discount_price": 90.00
  }
}
```

---

## 🛡️ Spec-11 Security & Red/Blue Team Gate
- **Zero Cloud Leakage:** All ad generation, social copy, and product logic runs 100% locally on `:8081` / `:8082`.
- **Anti-Tamper Validation:** Server-side price comparison prevents client-modified cart subtotals.
- **Cryptographic Signatures:** Incoming Shopify webhook payloads are authenticated via `X-Shopify-Hmac-Sha256` using constant-time comparison (`hmac.compare_digest`) to thwart timing attacks.
- **Spec-11 Automated Suite (`tests/test_spec11_security.py`):**
  - `test_blue_team_valid_webhook_hmac`: PASSED
  - `test_blue_team_constant_time_comparison`: PASSED (< 0.001s variance)
  - `test_blue_team_custom_gear_pricing_integrity`: PASSED ($90.00 AUD bundle)
  - `test_red_team_bit_flip_tampering`: PASSED (Rejected)
  - `test_red_team_forged_signature`: PASSED (Rejected)
  - `test_red_team_wrong_secret_key`: PASSED (Rejected)
  - `test_red_team_unauthorized_tier_discount_fallback`: PASSED (Fallback to standard tier)

---

## 📸 Generated Combat Sports Visual Ad Asset
- **Image File:** `01_apps/commerce_and_business/shopify_ai/assets/ad_ghost_rashguard_mockup.jpg`
- **File Size:** 719,894 bytes | **SHA256:** `0bf97e231d3b13d4154092a66673cb9c5abe64716bde476e40ccf3df182168b8`
- **Prompt:** Direct-response studio photography of Lauburu Ghost Rashguard and Fight Shorts on matte slate background.

---

## 🔄 Continuous Overnight Trainer Telemetry
- **Daemon Plist:** `~/Library/LaunchAgents/ai.lauburu.ecommerce_trainer.plist`
- **LoRA Dataset:** `/Users/aaron/DFS_UNIFIED/lora_datasets/neo_ecommerce_continuous_lora.jsonl`
- **Live Stream:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/tui_training_stream.json`
- **Logs:** `/tmp/ecommerce_trainer.log`
- **Current Performance:** Epoch 172 at 100% pass rate across all 5 benchmark categories; loss reduction 0.4463 $\to$ 0.0296; 889+ LoRA instruction & DPO pairs harvested.
- **Model Orchestration Plane:** Local AI Orchestrator (Port 8081) locked to **Qwen 3.8 Max** (Standard Non-Abliterated); Devil's Advocate (Port 8083) locked to **Qwen 3.8 Max Abliterated** (`Huihui-Qwen3.8-27B`).
- **Supplier Integration:** Subliminator & Tapstitch native web 3D Product Creators integrated for direct panel mapping and one-click Shopify catalog sync.

