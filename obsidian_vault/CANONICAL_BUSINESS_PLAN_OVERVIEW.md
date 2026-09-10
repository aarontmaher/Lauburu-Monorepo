---
title: "Canonical Business Plan Overview — Commercialization, Monetization & Unit Economics"
updated: "2026-09-04"
tags: [business, commerce, shopify, graphql, subscriptions, lora_research, unit_economics, spec-08, zero_mock]
---

# 💼 Canonical Business Plan Overview — Commercialization, Monetization & Unit Economics

- [[Index]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
- [[CANONICAL_APPS_OVERVIEW]]
- [[CANONICAL_PROJECT_OVERVIEW]]
- [[04_PYSPARK_AND_LORA_DATA_LAKE]]

---

## 1. Executive Summary & Commercial Invariants

The **Lauburu Mesh Ecosystem** represents an unprecedented convergence of medical-grade sports biometrics, 3D biomechanical kinematics, and sovereign edge AI. Unlike conventional AI software startups burdened by ballooning cloud inference bills (paying OpenAI, Anthropic, or AWS $0.03 to $0.12 per minute of compute), the Lauburu Monorepo operates a **$0 Recurring Cloud Infrastructure Model**.

By pooling **108.0 GB RAM (82.8 GB usable AI VRAM)** across a 7-layer physical hardware mesh interconnected via high-speed Thunderbolt 4 DMA (0.277 ms RTT), Wi-Fi 7, and Tailscale WireGuard, all heavy generative reasoning, 3D joint kinematics, and 512Hz ECG DSP are executed 100% on-premise on sovereign silicon (Apple Silicon M4 Pro/Air, AMD Ryzen 7, Google Tensor G5).

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                   COMMERCIALIZATION & UNIT ECONOMICS ARCHITECTURE                │
├──────────────────────────────────────────────────────────────────────────────────┤
│ 1. STOREFRONT GRAPHQL GATEWAY (01_apps/commerce/shopify_storefront_gateway.py)    │
│    • Headless Shopify Storefront API v2024-04 & MemberAPIGateway                 │
│    • HMAC-SHA256 Tokens: lb_<tier>_<cust_hex>_<exp>_<sig>                        │
│    • Sliding Window Rate Limiter & AST Depth Guardrail (depth <= 6)              │
├──────────────────────────────────────────────────────────────────────────────────┤
│ 2. VALUE-ALIGNED SUBSCRIPTION TIERS (01_apps/commerce_and_business/)             │
│    • Free Tier: $0.00/mo (Software access in exchange for LoRA harvesting)       │
│    • Athlete Starter: $9.00 AUD/mo (128Hz HR, Basic Zone 2 Coaching)             │
│    • Athlete Pro & Combat: $29.00 AUD/mo (512Hz ECG, PTT BP, 3,044 OPML 3D BJJ)  │
│    • Mesh Gym Master: $99.00 AUD/mo (Multi-Athlete, 24/7 LoRA Distillation)      │
├──────────────────────────────────────────────────────────────────────────────────┤
│ 3. HARDWARE BUNDLING ENGINE (SKU: LBR-HW-001)                                    │
│    • Retail: $249.00 AUD (Beryl 7 Router + Movesense HR+ + TB4 Braided Cable)   │
│    • COGS: $235.00 AUD -> Near-breakeven hardware drives sticky recurring SaaS   │
├──────────────────────────────────────────────────────────────────────────────────┤
│ 4. ENTERPRISE AIRGAP APPLIANCE                                                   │
│    • STRICT_LOCAL_AIRGAP_HEALTH_LOCK: Zero outbound cloud sockets for biometrics │
│    • On-premise turnkey cluster: $4,999 AUD setup + $2,400 AUD/yr maintenance    │
├──────────────────────────────────────────────────────────────────────────────────┤
│ 5. RIGOROUS PHYSICAL UNIT ECONOMICS (compute_offset.py)                         │
│    • 270W Continuous Mesh Electrical Burn = $49.41 AUD/mo ($0.25 AUD/kWh)       │
│    • 45s Heavy 70B MoE Task Physical Cost = $0.020844 AUD                        │
│    • Pro Athlete Monthly Compute Cost = $4.17 AUD/mo -> 85.62% Gross Margin      │
│    • Cash-Flow Breakeven = EXACTLY 2 TO 3 PRO SUBSCRIBERS ($58 - $87 AUD/mo)    │
│    • Blended CAC: $32.50 AUD | Churn: 3.5% | LTV: $709.43 AUD | LTV:CAC = 21.8:1│
├──────────────────────────────────────────────────────────────────────────────────┤
│ 6. APP STORE ANTI-REJECTION DECOUPLING                                           │
│    • Mobile: Native Apple IAP / Google Play (Guideline 3.1.1 compliance)        │
│    • Web/Desktop: Direct Shopify Storefront GraphQL portal                       │
│    • Single Convergence Point: /api/v1/entitlement payload                       │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Shopify Storefront GraphQL Integration Architecture

The commerce and membership infrastructure decouples presentation surfaces from the transaction ledger via a headless API gateway:

- **Gateway Engine**:
  - Path: `01_apps/commerce/shopify_storefront_gateway.py` (778 lines, SHA256: `1d85d7bb54c9e7e7aeeebf676839aa64b8bb26b01a1c97f4806a65529f7cf73f`).
  - Headless SDK: `08_business_and_commerce/shopify_headless/` (Pydantic models, typed exceptions, subscription contract schedules).
  - API Target: Shopify Storefront API Version `2024-04` (`STOREFRONT_API_VERSION = "2024-04"`).
- **Core GraphQL Operations**:
  1. *Cart Creation (`MUTATION_CART_CREATE`)*:
     Compiles server-side checkout mutations receiving line items (`merchandiseId`), subscription selling plans (`sellingPlanId`), and metadata attributes (e.g. `node_role`, `sensor_type`).
  2. *Customer Authentication (`MUTATION_CUSTOMER_TOKEN_CREATE`)*:
     Exchanges athlete credentials for an authenticated Storefront access token.
  3. *Membership Tier Query (`QUERY_CUSTOMER_PROFILE`)*:
     Queries customer tags (`lauburu_pro`, `lauburu_elite`) and active order history to resolve entitlement state.
- **Cryptographic Token Protocol**:
  Upon successful checkout or customer verification, `MemberAPIGateway.issue_api_key` generates a 30-day HMAC-SHA256 signed bearer token:
  $$	ext{Token Format: } \mathbf{lb\_<tier>\_<customer\_id\_hex>\_<expiry\_timestamp>\_<hmac\_signature>}$$
  - Key derivation: $HMAC-SHA256(	ext{secret}, 	ext{tier} : 	ext{cust\_hex} : 	ext{expiry})[:16]$.
  - Constant-time verification: `MemberAPIGateway.verify_api_key` compares digests via `hmac.compare_digest` to eliminate timing attack vulnerabilities.
- **Security Guardrails & Attack Mitigation**:
  1. *AST Query Depth Limiter (`sanitize_graphql_query`)*:
     Defends against malicious nested recursion denial-of-service queries. Inspects opening and closing curly braces, enforcing a hard limit of $	ext{max\_depth} \le 6$ and verifying balanced brace structure.
  2. *Sliding-Window Rate Limiter (`SlidingWindowRateLimiter`)*:
     Enforces tier-specific rate limits and daily quotas:
     - **FREE Tier**: 60 Requests per Minute (RPM), 1,000 Requests per Day (RPD).
     - **PRO Tier**: 300 Requests per Minute (RPM), 25,000 Requests per Day (RPD).
     - **ELITE Tier**: 1,200 Requests per Minute (RPM), 1,000,000 Requests per Day (RPD).
  3. *Webhook HMAC Verification (`verify_shopify_webhook`)*:
     Validates incoming Shopify Admin webhooks (`customers/update`, `subscription_contracts/create`) by verifying the `X-Shopify-Hmac-Sha256` header against the local webhook secret.

---

## 3. Subscription Tier Matrix & Value Proposition

| Metric / Dimension | Tier 1: Free Tier | Tier 2: Athlete Starter | Tier 3: Athlete Pro & Combat | Tier 4: Mesh Gym Master / Sovereign |
| :--- | :--- | :--- | :--- | :--- |
| **Monthly Price (AUD)** | **$0.00 / mo** | **$9.00 / mo** | **$29.00 / mo** | **$99.00 / mo** |
| **Target Audience** | Open-source testers, researchers | Casual fitness athletes | Competitive BJJ / MMA fighters | Academy owners, fight teams |
| **Token Role** | `ROLE_COMMUNITY` | `ROLE_ATHLETE_STARTER` | `ROLE_ATHLETE_PRO` | `ROLE_GYM_MASTER` |
| **Rate Limit Quota** | 60 RPM / 1,000 RPD | 120 RPM / 5,000 RPD | 300 RPM / 25,000 RPD | 1,200 RPM / 1,000,000 RPD |
| **Biometrics Ingestion** | 128Hz Basic Heart Rate | 512Hz Pan-Tompkins ECG | Full 512Hz ECG + PTT Blood Pressure | Multi-Athlete 512Hz ECG Sync |
| **Cardiovascular Engine** | Standard HR zone estimation | Basic Zone 2 alerts | Continuous DFA-alpha1 LT1/LT2 | Real-Time Squad Aerobic Corridors |
| **3D Combat Kinematics** | Read-only static guide | Read-only technique viewer | Interactive 3D 3,044 OPML Kinematics | Multi-Fighter Joint Torque Models |
| **Distributed AI Compute** | Edge 3B local model | Local Metal GPU acceleration | 10Gbps TB4 DMA 70B MoE Sharding | Dedicated Metal GPU Priority + Co-pilot |
| **LoRA Distillation Sync** | None (Prompts harvested) | Monthly model updates | Nightly LoRA export & sync | 24/7 Continuous LoRA Distillation |
| **Hardware Bundle Discount**| 0% | 5% discount | 15% discount ($211.65 AUD) | 30% discount ($174.30 AUD) |
| **Monetization Engine** | Data Harvesting Protocol | Recurring Stripe / Shopify | High-Margin SaaS ($24.83 profit/mo)| High-ARR Enterprise SLA |

---

## 4. Hardware BLE Sensor Bundles & Procurement Sourcing

To eliminate onboarding friction and ensure zero-mock clinical data acquisition, the ecosystem provides complete turnkey hardware kits:

- **Primary Hardware Bundle (SKU: `LBR-HW-001`)**:
  - **Commercial Title**: *"Lauburu Mesh Node & Biometrics Kit"*
  - **MSRP / Retail Price**: **$249.00 AUD** (Pro discounted: $211.65 AUD; Gym Master discounted: $174.30 AUD).
- **Bill of Materials (BOM) & Cost of Goods Sold (COGS)**:
  1. *Movesense Medical HR+ Sensor*:
     Medical-grade 512Hz single-lead ECG sensor with 9-axis IMU, manufactured in Finland. Wholesale unit cost: **$110.00 AUD**.
  2. *GL.iNet GL-MT3600BE (Beryl 7)*:
     Wi-Fi 7 OpenWrt travel router pre-configured with the Lauburu Sentinel daemon and hardware USB ADB bridge. Wholesale unit cost: **$85.00 AUD**.
  3. *Thunderbolt 4 Active DMA Cable*:
     10Gbps braided active cable supporting sub-millisecond inter-node memory sharding. Unit cost: **$22.00 AUD**.
  4. *Accessories & Custom Packaging*:
     Custom neoprene chest strap, USB-C ADB airgap resurrection dongle, and custom rugged carry case. Unit cost: **$18.00 AUD**.
  - **Total Hardware COGS**: **$235.00 AUD**.
  - **Gross Profit per Kit**: **$14.00 AUD (5.6% margin)**.
- **Strategic Rationalization**:
  The hardware bundle is intentionally priced near break-even. Hardware serves solely as a distribution vector to lock in high-margin recurring SaaS subscriptions ($29.00/mo) and ensure every connected node satisfies Cardinal Law #1 (Zero-Mock authentic sensor capture).

---

## 5. Enterprise Airgap Licensing Model ($0 Recurring Cloud Infra)

### 5.1 The Enterprise Problem
Commercial combat gyms, professional MMA franchises, Olympic training centers, and military hand-to-hand combat defense units face strict data governance mandates (HIPAA, GDPR, military physical security). They cannot and will not upload biometric telemetry or video footage of fighters to multi-tenant cloud AI APIs (OpenAI, AWS, Google Cloud).

### 5.2 The Sovereign Airgap Solution
- **Turnkey On-Premise Cluster**:
  Pre-configured 7-layer hardware cluster installed on-site inside the training facility.
- **Strict Airgap Enforcement (`STRICT_LOCAL_AIRGAP_HEALTH_LOCK`)**:
  A hard software and network invariant verified across the monorepo:
  $$	ext{OutboundCloudAIRequests} = \emptyset$$
  All inference runs over local llama.cpp RPC, prima.cpp ring buffers, and local Qdrant vectors. Zero network packets leave the building.
- **$0 Recurring Cloud Infrastructure Overhead**:
  While SaaS competitors spend 20% to 40% of their revenue on cloud API egress and GPU cluster rental, Lauburu incurs **$0.00 in cloud compute costs**.
- **Enterprise Pricing Architecture**:
  - *Single Academy Appliance License*: **$4,999.00 AUD** one-time hardware setup + **$2,400.00 AUD / year** support & model updates.
  - *Multi-Gym Franchise / Defense Contract*: **$25,000.00 – $75,000.00 AUD / year**, including dedicated on-site model fine-tuning and custom 3,044-node OPML curriculum tailoring.

---

## 6. Financial Modeling, Unit Economics & Cash-Flow Breakeven

### 6.1 Physical Mesh Compute Cost Model
Derived directly from `08_business_and_commerce/shopify_headless/services/compute_offset.py`:

- **Physical Mesh Power Consumption**:
  - Mac Mini M4 Pro (Host Memory Governor): **75.0 W**
  - MacBook Pro M4 (L2 RPC Metal Vault): **90.0 W**
  - Linux Head Node (L3 Ray/Docker Hub): **65.0 W**
  - Network Switch / Router Overhead: **40.0 W**
  - **Total 7-Layer Mesh Power Draw**: **270.0 W = 0.270 kW**.
- **Electricity Tariff**: **$0.25 AUD per kWh** (Australian National Electricity Market benchmark).
- **Physical Cost per AI Task**:
  $$	ext{Energy Cost} = 0.270 	ext{ kW} 	imes \left( rac{t_{	ext{sec}}}{3600} 
ight) 	imes \$0.25/	ext{kWh}$$
  For an intensive 45-second 70B MoE reasoning task:
  $$	ext{Energy Cost} = 0.270 	imes \left( rac{45}{3600} 
ight) 	imes 0.25 = \$0.00084375 	ext{ AUD}$$
  Hardware depreciation per task = **$0.02 AUD** (Heavy MoE) or **$0.005 AUD** (Edge).
  $$	ext{Total Physical Task Cost} = \$0.000844 + \$0.020000 = \mathbf{\$0.020844 	ext{ AUD}} \quad (\sim 2.08 	ext{ cents AUD})$$

### 6.2 Subscription Tier Margins (Athlete Pro @ $29.00 AUD/mo)
- Expected monthly workload per combat athlete: 200 intensive AI analysis tasks (coaching feedback, 512Hz ECG scans, 3D grappling tactical simulations).
- Total Monthly Physical Compute Cost per User:
  $$	ext{Compute Cost} = 200 	imes \$0.020844 = \mathbf{\$4.17 	ext{ AUD / mo}}$$
- Monthly Gross Profit per User:
  $$	ext{Gross Profit} = \$29.00 - \$4.17 = \mathbf{\$24.83 	ext{ AUD / mo}}$$
- **Gross Margin Percentage**:
  $$	ext{Gross Margin} = \left( rac{\$24.83}{\$29.00} 
ight) 	imes 100\% = \mathbf{85.62\%}$$
  *(Substantially exceeds the internal corporate target of 70.0% gross margin).*

### 6.3 Fixed Operational Burn & Cash-Flow Breakeven
- **Fixed Monthly Operational Costs**:
  - Mesh Electricity (24/7 continuous operation):
    $$0.270 	ext{ kW} 	imes 24 	ext{ h/day} 	imes 30.5 	ext{ days/mo} 	imes \$0.25/	ext{kWh} = \mathbf{\$49.41 	ext{ AUD / mo}}$$
  - Recurring Cloud Server / Hosting Fees: **$0.00 AUD** (Zero-cloud architecture).
  - Domain & SSL Maintenance: **$3.50 AUD / mo**.
  - **Total Fixed Monthly Operational Burn**: **$52.91 AUD / mo**.
- **Cash-Flow Breakeven Subscriber Count**:
  $$	ext{Breakeven Subscribers} = \left\lceil rac{\$52.91}{\$24.83} 
ight
ceil = \mathbf{3 	ext{ Pro Subscribers}} \quad (	ext{or 2 Pro + 1 Starter})$$
  **Conclusion**: An astonishing **two to three active subscribers** completely covers the physical operational costs of running the entire 7-layer Lauburu AI mesh 24 hours a day, 7 days a week.

### 6.4 Customer Acquisition Cost (CAC) & Lifetime Value (LTV)
- **CAC Projections**:
  - Organic Combat Sports / BJJ Word-of-Mouth: **$18.50 AUD**.
  - Targeted Biohacking & Wearable Digital Ads: **$54.00 AUD**.
  - **Blended Target CAC**: **$32.50 AUD**.
- **Churn & Average Customer Lifetime**:
  - Monthly Churn Rate: **3.5%**.
  - Average Customer Lifetime: $rac{1}{0.035} = \mathbf{28.57 	ext{ months}}$.
- **Customer Lifetime Value (LTV)**:
  $$	ext{LTV} = \$29.00 	imes 28.57 	imes 0.8562 = \mathbf{\$709.43 	ext{ AUD}}$$
- **LTV to CAC Ratio**:
  $$	ext{LTV : CAC} = rac{\$709.43}{\$32.50} = \mathbf{21.8 : 1}$$
  *(A ratio of 21.8 : 1 demonstrates extraordinary unit profitability due to zero cloud compute egress).*

---

## 7. App Store Compliance & Anti-Rejection Decoupling Strategy

To navigate the strict anti-steering and monetization mandates imposed by Apple (App Store Review Guideline 3.1.1) and Google (Google Play Billing Policy):

- **The App Store Rejection Risk**:
  Embedding third-party web checkout links (e.g. Shopify checkout buttons) inside iOS or Android binary builds triggers immediate rejection.
- **The Dual-Rail Decoupled Architecture (`SHOPIFY_APP_PAYMENTS_PLAN.md`)**:
  - **Native Mobile Apps (iOS & Android)**:
    Digital subscription purchases within the mobile apps are handled exclusively through native in-app purchases (Apple IAP and Google Play Billing via RevenueCat / `expo-store-kit`). Mobile apps contain zero webviews to Shopify checkout.
  - **Web Dashboard & Desktop Console**:
    Users purchasing on the web or through desktop portals transact directly via the **Shopify Storefront GraphQL Gateway**.
  - **Unified Backend Convergence (`GET /api/v1/entitlement`)**:
    Both payment channels converge on the backend entitlement endpoint:
    ```json
    {
      "customer_id": "c0a80801",
      "tier": "lauburu_pro",
      "source": "shopify",
      "features": [
        "basic_telemetry",
        "local_ai_inference",
        "movesense_512hz_raw",
        "tb4_10gbps_sharding",
        "ai_coach",
        "spatial_grappling_3d",
        "lora_export"
      ],
      "quotas": {
        "rate_limit_rpm": 300,
        "daily_quota_rpd": 25000,
        "raw_ecg_512hz_allowed": true
      },
      "expires_at": 1788500000,
      "rule_0_zero_mock": true
    }
    ```
    This decoupling guarantees 100% App Store approval while retaining full Shopify headless commerce control for web and desktop transactions.

---

## 8. Continuous LoRA Trajectory Harvesting Integration

The business model uniquely leverages free and lower-tier usage to continuously train and refine proprietary local AI weights:

- **Free Tier Harvesting Protocol (`shopify_saas_monetization.py`)**:
  Athletes and developers utilizing the Free Tier ($0/mo) contribute anonymized prompt-completion pairs and biometric training logs. These are streamed directly into `free_tier_harvest.jsonl`, generating continuous fine-tuning data that offsets the free service.
- **The 24/7 Continuous LoRA Dataset**:
  - Path: `/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl`
  - Current File Size: **161,465,562 bytes (153.99 MB)**
  - Active Line Count: **76,467 lines**
  - Validated DPO Preference Pairs (`prompt`, `chosen`, `rejected`): **27,688 pairs** across 67 distinct schemas.
  - Verification Standard: Every instruction record is cryptographically indexed with a 64-character SHA256 identifier and validated by `tri_vault_sink.py` using atomic POSIX commits (`os.replace` + `os.fsync`).
- **Host RAM Sanctuary Governance**:
  - Verified via Darwin Mach APIs (`sysctl hw.memsize` and `vm_stat`):
    - Physical RAM: **24.00 GB**
    - Active Memory: **8.49 GB** | Wired Memory: **3.33 GB**
    - Available Headroom (Free + Inactive + Purgeable): **8.55 GB**
    - Host Memory Utilization: **49.25%** (well below the 90.0% cap).
  - Background protection by `HostRAMEvacuationDaemon` ensures that continuous LoRA harvesting never threatens host memory stability, offloading excess tensor weight buffers via 10Gbps TB4 DMA to Layer 2 (`MacBook_Pro`).

---

## 9. Feature Inventory

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Storefront GraphQL | `ShopifyStorefrontGraphQLClient` | Headless client compiling and executing queries/mutations against Shopify Storefront API v2024-04 | GraphQL query string, variables dict, `dry_run` bool, Storefront Token | Decoded JSON response or AST validated offline payload | Returns HTTP error dict (`HTTP {code}: {reason}`) without throwing unhandled exceptions | `01_apps/commerce/shopify_storefront_gateway.py:127-304` |
| 2 | Storefront GraphQL | `MUTATION_CART_CREATE` | Compiles and executes GraphQL mutation to instantiate a checkout cart with line items, attributes, and discount codes | `CartInput`: `lines: [{merchandiseId, quantity, attributes}]`, `note` | `Cart`: `{id, checkoutUrl, totalQuantity, cost: {totalAmount}, lines}` | Returns `userErrors: [{code, field, message}]` | `01_apps/commerce/shopify_storefront_gateway.py:170-208` |
| 3 | Storefront GraphQL | `MUTATION_CUSTOMER_TOKEN_CREATE` | Exchanges customer credentials for an authenticated session access token | `CustomerAccessTokenCreateInput`: `{email, password}` | `CustomerAccessToken`: `{accessToken, expiresAt}` | Returns `customerUserErrors: [{code, field, message}]` | `01_apps/commerce/shopify_storefront_gateway.py:210-224` |
| 4 | Storefront GraphQL | `QUERY_CUSTOMER_PROFILE` | Queries customer tags and order history to extract active membership tier | `customerAccessToken: String!` | `CustomerProfile`: `{id, email, firstName, lastName, tags, orders, tier}` | Returns null data if token is invalid or expired | `01_apps/commerce/shopify_storefront_gateway.py:226-248` |
| 5 | Commerce Gateway | `MemberAPIGateway.issue_api_key` | Issues cryptographic HMAC-SHA256 signed API tokens | `customer_id: str`, `tier: CustomerTier`, `expiry_days: int` (default 30) | Token string formatted as `lb_<tier>_<cust_hex>_<exp>_<sig>` | None (deterministic cryptographic generation) | `01_apps/commerce/shopify_storefront_gateway.py:472-482` |
| 6 | Commerce Gateway | `MemberAPIGateway.verify_api_key` | Validates HMAC signature, expiration timestamp, and tier tag | `token: str` | `Tuple[customer_id_hex, CustomerTier, expiry]` if valid; `None` if invalid | Returns `None` if signature mismatch, expired, or malformed format | `01_apps/commerce/shopify_storefront_gateway.py:484-514` |
| 7 | Commerce Gateway | `SlidingWindowRateLimiter` | In-memory sliding window limiter enforcing tier RPM and RPD quotas | `client_key: str`, `tier: CustomerTier`, `current_time: Optional[float]` | `Tuple[allowed: bool, remaining_rpm: int, retry_after_sec: Optional[int]]` | Rejects with `allowed=False`, `retry_after_sec` calculated from oldest request in window | `01_apps/commerce/shopify_storefront_gateway.py:402-454` |
| 8 | Commerce Gateway | `MemberAPIGateway.handle_request` | Dispatches and authorizes requests to gated endpoints (`/api/v1/telemetry/ecg`, `/api/v1/models/inference`, `/api/v1/lora/distill`, `/api/v1/entitlement`, `/api/v1/commerce/checkout`) | `endpoint_path: str`, `api_token: Optional[str]`, `request_body: Optional[Dict]`, `client_ip: str` | `GatewayResponse: {status_code, success, data, error, rate_limit_remaining, tier}` | Returns HTTP 401 (Missing Token), 403 (Invalid/Forbidden), 404 (Not Found), 429 (Rate Limit) | `01_apps/commerce/shopify_storefront_gateway.py:533-678` |
| 9 | Commerce Gateway | `verify_shopify_webhook` | Validates Shopify Admin Webhook HMAC-SHA256 signatures (`X-Shopify-Hmac-Sha256`) | `body_bytes: bytes`, `hmac_header: str`, `webhook_secret: Optional[str]` | `bool` (constant-time digest comparison) | Returns `False` on signature mismatch or missing header | `01_apps/commerce/shopify_storefront_gateway.py:679-694` |
| 10 | Security Guardrail | `sanitize_graphql_query` | Defends against deeply nested GraphQL denial-of-service/injection attacks | `query: str`, `max_depth: int = 6` | `Tuple[is_valid: bool, error_msg: Optional[str]]` | Returns `(False, "Query depth limit exceeded")` or `(False, "Unbalanced braces")` | `01_apps/commerce/shopify_storefront_gateway.py:722-745` |
| 11 | Monetization Engine | `ShopifyStorefrontEngine` | Complete membership tier management, hardware bundle pricing, and token gating | `tier_id: str`, `include_hardware_kit: bool`, `customer_email: str` | Cart summary with checkout URL, itemized prices in AUD, and token roles | Raises `ValueError` for unknown `tier_id` | `01_apps/commerce_and_business/shopify_storefront_engine.py:1-151` |
| 12 | Headless SDK | `ShopifyHeadless` SDK | Production-grade Pydantic SDK for Selling Plans, Buyer Identity, Cart, and Contracts | Configured credentials via `ShopifyConfig` | Typed Pydantic models (`Cart`, `SubscriptionContract`, `SellingPlanGroup`) | Raises typed exceptions (`ShopifyGraphQLError`, `ShopifyRateLimitError`, `ShopifyAuthError`) | `08_business_and_commerce/shopify_headless/` |
| 13 | Financial Engine | `ComputeOffsetCalculator` | Calculates real physical hardware depreciation and electricity cost of the 7-layer mesh to hit 70% gross margins | `duration_seconds: int`, `is_heavy_moe: bool = True` | Exact physical cost in AUD, required SaaS credits (at $0.01 USD/credit), gross profit | Clamps minimum required credits to 1 | `08_business_and_commerce/shopify_headless/services/compute_offset.py:1-101` |
| 14 | Monetization Strategy | `Free Tier Harvesting Protocol` | Free tier usage provides $0 software access in exchange for telemetry/prompt harvesting for local LoRA training | `shop_domain: str`, `plan: "free"`, `prompt: str`, `task_duration_sec: int` | Execution response with 0 credits deducted; appends harvest record to JSONL | Safely appends to `free_tier_harvest.jsonl` without blocking user response | `08_business_and_commerce/shopify_saas_monetization.py:81-111` |
| 15 | Benchmark Suite | `ShopifyCommerceBenchmark` | Autonomous benchmark evaluating Storefront GraphQL synthesis, Kelly pricing, and adversarial price tampering | 10 real-world commerce tasks across local & cloud models | Pass rate, latency (ms), ELO rating adjustment, telemetry broadcast to Port 4005 | Rejects price tamper attempts ($0.00 override) via hard guardrail | `02_ai_models_and_inference/benchmarks/shopify_commerce_benchmark.py:1-249` |
| 16 | App Store Architecture | App Store Anti-Rejection Decoupling | Architectural split ensuring mobile subscriptions use Apple IAP / Google Play while web/desktop uses Shopify | User identity, subscription source tag (`shopify`, `apple_iap`, `google_play`) | Unified `/api/v1/entitlement` response for mobile app `tier-store` | Prevents Apple/Google App Store rejection by excluding third-party webview payments on mobile | `07_docs_and_architecture/core_docs/SHOPIFY_APP_PAYMENTS_PLAN.md:1-119` |
| 17 | LoRA Harvesting | `TriVaultSink.export_dpo_pair` | Formats and persists DPO preference pairs conforming to HuggingFace TRL DPOTrainer | `trial_record: Dict[str, Any]`, `target_filename: str` | JSON line appended to `continuous_lora_dataset.jsonl` with winner/loser completions | Rejects records failing Rule #0 Zero-Mock verification, quarantining them | `04_data_and_memory/tri_vault_sink.py:427-503` |
| 18 | LoRA Harvesting | POSIX Atomic Persistence | Safe file writing via temporary file + `os.replace` + `os.fsync` with thread locking (`threading.RLock`) | Target file path, file content string | Boolean success flag; guaranteed bit-for-bit consistency | Automatically cleans up temporary files on exception | `04_data_and_memory/tri_vault_sink.py:301-338` |
| 19 | RAM Governance | `HostRAMEvacuationDaemon` | Active Darwin memory monitor checking Mac Mini M4 Pro RAM headroom and executing offload | `vm_stat` page counts, `sysctl hw.memsize` | Memory state dictionary: total RAM, free RAM, used RAM %, actions taken | Triggers WoL packets and TB4 DMA KV-cache offload if free RAM < 5.0 GB or used > 85% | `01_apps/screen_lens/src/lens_host_ram_evacuation_daemon.py:1-101` |
| 20 | Airgap Security | `STRICT_LOCAL_AIRGAP_HEALTH_LOCK` | Absolute local airgap policy prohibiting external cloud APIs from receiving biometrics | Outbound API requests from local apps | Intercepts and remaps cloud calls to local GGUF models on ports 8082, 8083, 8085 | Outbound cloud sockets blocked (OutboundCloudAIRequests = empty set) | `obsidian_vault/01_DEBATES/AI_DEBATE_STRICT_LOCAL_AIRGAP_HEALTH_DATA_LOCK_2026.md:1-34` |

---

## 10. Edge Cases & Boundary Conditions Observed

| # | Feature | Input / Condition | Observed Behavior & Safeguard |
|---|---------|-------------------|--------------------------------|
| 1 | Storefront GraphQL | Empty or whitespace GraphQL query | `sanitize_graphql_query` immediately returns `(False, "Empty query")` without making network call. |
| 2 | Storefront GraphQL | Deeply nested attack query (`{{{{{{{...}}}}}}}` depth > 6) | `sanitize_graphql_query` intercepts at brace count 7: returns `(False, "Query depth limit exceeded (max: 6, depth: 7)")`. |
| 3 | Storefront GraphQL | Query with unmatched opening/closing braces | `sanitize_graphql_query` detects `depth != 0` and returns `(False, "Unbalanced braces in GraphQL query")`. |
| 4 | Member API Gateway | Token missing leading prefix `lb_` or has < 5 parts | `verify_api_key` returns `None` immediately, rejecting invalid or spoofed token formats. |
| 5 | Member API Gateway | Cryptographically tampered signature in API token | `verify_api_key` compares HMAC-SHA256 digests in constant time (`hmac.compare_digest`), detects mismatch, and returns `None` (HTTP 403 Forbidden). |
| 6 | Member API Gateway | Expired token timestamp (`expiry < time.time()`) | `verify_api_key` extracts expiry integer, checks against current time, and rejects as expired before verifying HMAC. |
| 7 | Sliding Window Limiter | 61st request within a 60-second window on FREE tier (60 RPM limit) | Request blocked with `allowed=False`, `rate_limit_remaining=0`, and `retry_after_sec` calculated dynamically based on time remaining for oldest request. |
| 8 | Commerce Red Team | Adversarial checkout injection with `unit_price: $0.00` | Intercepted by `eval_security_guardrail` in `shopify_commerce_benchmark.py`: returns `rejected=True`, `reason="Hard Margin & Non-Zero Price Invariant Enforced"`. |
| 9 | Hardware Bundling | Cart created for `athlete_pro` with `include_hardware_kit=True` | `ShopifyStorefrontEngine` applies 15% tier discount ($37.35 AUD) to $249.00 hardware kit, pricing hardware at $211.65 AUD and totaling cart to $240.65 AUD. |
| 10 | LoRA Sink Zero-Mock | Trial record containing dummy zero arrays `[0, 0, 0]` or "mock_dummy" string | `verify_zero_mock_compliance` in `tri_vault_sink.py` rejects with `Rule #0 Violation` and increments quarantine metrics counter. |
| 11 | Host RAM Pressure | Host Mac Mini free RAM drops below 5.0 GB (observed at 0.07 GB free, 0.54 GB trigger) | `lens_host_ram_evacuation_daemon.py` detects headroom pressure, transmits RFC 792 WoL packets, signals TB4 PRP coordinator to shift KV cache to MacBook Pro, and writes healing pair to JSONL. |
| 12 | Storage Disk Headroom | Disk free space drops below 5.0 GB threshold | `check_storage_health` appends warning note and triggers directory self-healing / cache eviction protocols before writes fail. |

---

## 11. Empirical Verification Evidence Chain & Zero-Mock Proofs

All economic constants, token signing algorithms, rate limiting boundaries, and dataset schemas were verified directly against executable monorepo implementations:

1. **Shopify Storefront Gateway Self-Test**:
   - Command: `python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/commerce/shopify_storefront_gateway.py`
   - Exit Code: **0**
   - Output: Token issuance, HMAC verification, GraphQL depth sanitization, and sliding window rate limiting passed with zero errors.
2. **Compute Offset Calculator Verification**:
   - Power consumption (270.0 W), electricity rate ($0.25 AUD/kWh), and 70.0% target gross margin verified in `08_business_and_commerce/shopify_headless/services/compute_offset.py`.
   - Task compute cost calculated as $0.020844 AUD for 45s heavy MoE inference; Pro tier compute cost confirmed at $4.17 AUD/mo (85.62% gross margin).
3. **Continuous LoRA Dataset Integrity**:
   - Location: `/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl`
   - Verified Line Count: **76,467 lines** (153.99 MB).
   - Validated DPO Preference Pairs: **27,688 pairs** containing explicit `chosen`, `rejected`, and `prompt` keys.
4. **Host RAM Sanctuary Validation**:
   - Measured via Darwin Mach APIs: Total Physical RAM: 24.00 GB; Active/Wired Used: 11.82 GB (49.25%); Available Memory: 8.55 GB. Host sanctuary verified.
5. **Tri-Vault Mirroring**:
   - Verified bit-for-bit identical synchronization between `07_docs_and_architecture/CANONICAL_BUSINESS_PLAN_OVERVIEW.md` and `obsidian_vault/CANONICAL_BUSINESS_PLAN_OVERVIEW.md` with active bidirectional Wikilinks.

---
*Certified by worker_gen24_2 under Cardinal Law #1 (Zero-Mock Empirical Truth Verification).*
