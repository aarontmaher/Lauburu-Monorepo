---
title: "Combat Storefront Lauburu — UI/UX Specification & Frontier Review"
tags: [combat_storefront, b2b_wholesale, rashguards, movesense, shopify_graphql, zero_mock, frontier_review, lora]
date: 2026-10-03
status: PRODUCTION_ACTIVE
---

# 🥋 Combat Storefront Lauburu — UI/UX Specification & Review

## 1. System Overview
**Combat Storefront Lauburu** (`08_business_and_commerce/frontend/index.html`) is the sovereign combat sports e-commerce storefront, B2B wholesale academy portal, and hardware liquidation desk of the Lauburu Ecosystem.

- **Product Catalog Lines:**
  - **Stealth Black Rashguard (Absolute MMA Cut):** 250 GSM poly-spandex athletic weave, 25mm non-slip silicone waistband, tone-on-tone stealth flatlock stitching.
    - D2C Retail: $89.00 AUD.
    - B2B Wholesale Tier 1 (20–49 units): $48.00 AUD/unit.
    - B2B Wholesale Tier 2 (50+ units): $42.00 AUD/unit.
    - **Physical Sample Gate Status:** `LOCKED_UNTIL_PHYSICAL_SAMPLE_APPROVAL` (Sample parcel `EJ350397089AU` in transit from Shaoxing).
  - **Movesense Combat Biometrics Kit ($249 AUD):** Movesense Medical MD+ sensor strap bundle with 512Hz Pan-Tompkins QRS peak detection and 9-axis IMU kinematic impact profiling.
  - **Marketplace Liquidation Desk (iPhone 16 Pro, $790 AUD Cash):** Altona Gate Shopping Centre daytime pickup, $750 AUD cash floor, full Australian Consumer Law §54 compliance with macro-photographic OLED bezel dead pixel disclosure.
- **Rule 0 Zero-Mock Conformance:** Awaiting checkout displays explicit token states (`-- (AWAITING CHECKOUT)`), and storefront API dispatches show unauthenticated waiting states (`[Awaiting Shopify Storefront Token]`).

---

## 2. Practical Backend Development Path & Full Functionality Roadmap

### Architecture & Endpoints
- **Shopify Storefront GraphQL:** `08_business_and_commerce/shopify_headless/client.py` executing cart and checkout mutations against `https://lauburugrappling.com/api/2026-10/graphql.json`.
- **Subliminator Manufacturing Webhook:** Ingestion daemon in `ai_debate_hicham_subliminator_response.py` capturing sample manufacturing status and wholesale packing manifests.
- **Business Ledger Sync:** Real-time updates committed to `08_business_and_commerce/business_ledger.json`.

### Requirements for 100% Launch
1. **Storefront Credentials:** Export `SHOPIFY_STOREFRONT_ACCESS_TOKEN` in sovereign local `.env`.
2. **Physical Sample Gate Approval:** Aaron receives, inspects, and rolls in the Black Belt sample set (`EJ350397089AU`).
3. **DNS & Payments:** Complete Cloudflare SSL routing for `lauburugrappling.com` and connect Stripe/Shopify Payments for AUD bank payouts.

---

## 3. Frontier Model Review Summary (Gemini 2.5 Flash Lite)
- **Zero-Mock Truth Enforcement:** **90/100** — Explicit waiting states (`-- (AWAITING CHECKOUT)`), clear physical sample gate locking.
- **E-Commerce UX & Catalog Architecture:** **85/100** — Structured spec badges, transparent ACL §54 flaw disclosures, dual D2C and B2B wholesale pricing.
- **Backend Development Path Clarity:** **85/100** — Logical GraphQL integration, unit economics margin defense, and Launch requirements.
- **WCAG AAA Compliance:** **80/100** — High-contrast dark mode readability with accessible keyboard focus rings (`focus:ring-amber-300`).

---

## 4. Tri-Vault Synchronization
- **Frontend Code:** [`08_business_and_commerce/frontend/index.html`](file:///Volumes/Lauburu-Monorepo/08_business_and_commerce/frontend/index.html)
- **Ecosystem Prototype:** [`08_business_and_commerce/prototypes/ecosystem/combat_storefront_preview.html`](file:///Volumes/Lauburu-Monorepo/08_business_and_commerce/prototypes/ecosystem/combat_storefront_preview.html)
- **LoRA Lake:** Triplet appended to `/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl`.
