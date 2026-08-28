# DISPATCH LOG

## 2026-08-28T19:41:28Z
You are Survey Spec Miner 3 for the Lauburu Ecosystem project.
Your Working Directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_3/
Please create your working directory and write all your metadata, progress, and handoff report inside it.

Authoritative source of user intent:
Read /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md

Your Survey Scope:
Investigate and specify all requirements, data structures, and implementation details for:
Requirement 2 (R2) — Shopify Headless Monetization Engine:
1. Target location: `08_business_and_commerce/shopify_headless/` (and check `08_business_commerce` / existing directories in the monorepo).
2. Specify the foundational package architecture:
   - Client module (`client.py` or equivalent) handling Storefront API and Admin/Customer Account API GraphQL endpoints, headers (`X-Shopify-Storefront-Access-Token`, `X-Shopify-Access-Token`), error handling, rate limiting.
   - Configuration via environment variables: `SHOPIFY_STORE_DOMAIN`, `SHOPIFY_STOREFRONT_ACCESS_TOKEN`, `SHOPIFY_ADMIN_ACCESS_TOKEN`, `SHOPIFY_API_VERSION` (e.g., `2024-07` or latest stable). No hardcoded credentials.
3. Precise GraphQL queries and mutations for the 3 required use cases:
   - Use Case 1: Recurring Subscriptions — Purchasing access to the "OpenClaw AI API" (SubscriptionLineItem / subscription contracts / selling plans or storefront cart with sellingPlanId).
   - Use Case 2: Hardware Kit Cart — Buying physical Lauburu Mesh Nodes (GL.iNet routers + Movesense ECGs) via `cartCreate`, `cartLinesAdd`, `cartBuyerIdentityUpdate`.
   - Use Case 3: Token-Gated Authentication — Validating a customer's active subscription via Customer Account API / Storefront customer access token to unlock the 3D Spatial Grappling UI (`01_apps/spatial_grappling/` or Port 4000).
4. Verify exact GraphQL syntax, types, input objects, return payload structures, and response validation logic.

Produce a detailed specification report at `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_3/handoff.md`. Send a message when complete.
