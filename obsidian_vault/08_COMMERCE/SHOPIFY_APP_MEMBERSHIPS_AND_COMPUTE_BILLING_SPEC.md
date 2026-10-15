---
title: "Shopify App Memberships, Compute Metering & App Store Architecture"
tags: [shopify, commerce, saas, compute_metering, app_memberships, architecture]
date: "2026-09-16"
status: "SANDBOX_VERIFIED"
---

# 🛍️ Shopify App Memberships, Compute Metering & App Architecture

## 1. Executive Summary & Core Paradigm Distinction

There are two fundamentally distinct ways "Apps" interact with Shopify:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                   THE TWO SHOPIFY SOFTWARE MONETIZATION PATHS                    │
├──────────────────────────────────────────────────────────────────────────────────┤
│ PATH A: SHOPIFY APP STORE (B2B SaaS for Other Merchants)                         │
│ • Audience: Other Shopify store owners across the globe.                         │
│ • Delivery: Installed into their Shopify Admin / Storefront via Partner Dashboard│
│ • Tech Stack: Node/Remix, FastAPI, Cloudflare Workers, App Bridge, Shopify CLI   │
│ • Monetization: Shopify Billing API (appSubscriptionCreate, appUsageRecordCreate)│
│ • Take Rate: 0% on first $1,000,000 USD/year, 15% thereafter.                    │
│ • Use Case: Selling Lauburu tools (Inventory Sync, Anti-Scam Shield, 3D Models)  │
│             to thousands of third-party Shopify merchants.                       │
├──────────────────────────────────────────────────────────────────────────────────┤
│ PATH B: DIRECT-TO-ATHLETE SOFTWARE & MEMBERSHIPS (B2C on lauburugrappling.com)   │
│ • Audience: Aaron's end-users (BJJ athletes, gyms, biohackers, developers).       │
│ • Delivery: Direct digital download (.dmg, .apk, .AppImage) & API license keys.  │
│ • Tech Stack: Shopify Subscriptions API, Customer Accounts API, Webhooks.        │
│ • Monetization: Recurring monthly/annual subscription plans + Pay-by-Compute.    │
│ • Backend: 7-Layer Lauburu Mesh (Mac Mini L1 + Linux L3 compute_metering_engine) │
│ • Use Case: Selling Movesense Hub 512Hz SaaS, Spatial Grappling 3D Academy,     │
│             and Qwen 3.8 Max local AI compute credits directly to buyers.        │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Path A: How Shopify "Apps" Work (The Shopify App Store)

If Aaron chooses to sell apps to other e-commerce merchants on the official **Shopify App Store**:
1. **Partner Account & CLI Scaffolding:**
   - Initialize via `shopify app init` using Node/Remix or Python backend.
   - Register the application in the **Shopify Partner Dashboard** (`partners.shopify.com`).
2. **Integration Touchpoints:**
   - **Theme App Extensions:** Injects Liquid/JS widgets directly into the merchant's theme without editing raw code.
   - **Admin UI Extensions:** Renders custom UI pages natively inside the merchant's Shopify Admin dashboard using Polaris.
   - **Shopify Functions:** Custom backend logic executing directly on Shopify's Edge infrastructure (e.g., custom discount calculation, delivery options, payment customization).
3. **App Store Billing:**
   - Charge merchants recurring monthly fees (`appSubscriptionCreate`) or metered usage (`appUsageRecordCreate`).
   - Shopify handles global multi-currency merchant billing; Aaron gets paid out to his bank account.

---

## 3. Path B: Selling Your Actual Apps on `lauburugrappling.com`

To sell Aaron's apps (Movesense Hub, Spatial Grappling 3D, Mesh AI Inference) directly to clients:
1. **Recurring Membership Products:**
   - **Starter Athlete ($29 AUD/mo):** 512Hz ECG streaming, Pan-Tompkins QRS DSP, 250 AI credits, 1 device.
   - **Pro Grappler & Lab ($99 AUD/mo):** Spatial Grappling 3D (955 nodes), Qwen 3.8 Max local model queries, 1,000 compute credits, 15% hardware discount.
   - **Elite Academy ($299 AUD/mo):** Multi-athlete live telemetry, dedicated GPU shard, 5,000 compute credits, video analysis.
2. **Pay-by-Compute Metering (`compute_metering_engine.py`):**
   - Inference rates: $0.20/1M input tokens, $0.80/1M output tokens on Qwen 3.8 Max (L1 Mac Mini).
   - 512Hz ECG DSP: $1.50/hr streaming.
   - Physical Mesh Cost Invariant: 270W draw @ $0.25/kWh calibrated to deliver 70% gross margins.
3. **Automated Webhook Provisioning Flow:**
   ```
   Customer buys plan on lauburugrappling.com
     │
     ▼ (Shopify Webhook: orders/paid)
   Linux Mini L3 Webhook Listener (Port 8000)
     │
     ▼ (compute_metering_engine.py)
   Generate Cryptographic License Key & JWT Token
     │
     ▼
   Provision Compute Credits in compute_billing_db.json
     │
     ▼
   Customer Account Portal reveals .dmg / .apk / .AppImage downloads & API Keys
   ```
4. **Hardware + SaaS Solvency Rule (Rule 0 & Rule 1):**
   - Physical assets (Movesense MD+ $170 AUD, Bicep Band $59 AUD) have hard COGS ($110 + $12) + shipping ($15 + $9.95).
   - Solvency Invariant: Wholesale COGS + courier costs MUST be collected in cash. The SaaS software portion is discounted/offset, guaranteeing Aaron is NEVER out-of-pocket.

---

## 4. Sandboxed Theme Implementation

Staged in:
`/Volumes/Lauburu-Monorepo/01_apps/screen_lens/sandbox_evolution/shopify_theme_sandboxes/theme_unified_hybrid/`

| Component | Path | Function |
| :--- | :--- | :--- |
| **App Memberships** | `snippets/app-memberships.liquid` | Interactive monthly/annual tiered pricing cards with features and cart forms |
| **Compute Calculator**| `snippets/compute-pricing-calculator.liquid` | Live interactive sliders for tokens/ECG hours, physical cost & credit estimation |
| **Digital App Gate** | `snippets/digital-app-gate.liquid` | OS download portal (macOS DMG, Android APK, Linux) and API key manager |
| **Hardware Bundle** | `snippets/hardware-saas-bundle.liquid` | All-in-one Movesense MD+ and 3-month Pro membership bundle |
| **Pages** | `templates/page.memberships.liquid`, `templates/page.compute.liquid` | Full Shopify pages integrating the modular snippets |
| **Adaptive Styling**| `assets/theme-adaptive.css` | 100% responsive dark/light mode styles verified with 0 Shopify CLI offenses |

- [[Index]]
- [[SHOPIFY_SWE_BENCH_REPORT]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
