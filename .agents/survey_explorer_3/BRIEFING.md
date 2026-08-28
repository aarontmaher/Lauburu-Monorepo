# BRIEFING — 2026-08-28T19:47:00Z

## Mission
Discover, probe, and specify all architectural, GraphQL, and integration requirements for Requirement 2 (R2): Shopify Headless Monetization Engine in `08_business_and_commerce/shopify_headless/`.

## 🔒 My Identity
- Archetype: Specification Miner / Teamwork Specialist
- Roles: Survey Spec Miner 3
- Working directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_3/
- Original parent: 9e0d5e24-d9fb-49d8-b62d-be34c78d1690
- Milestone: Survey & Architectural Specification (R2 Shopify Headless)

## 🔒 Key Constraints
- Zero-mock truth enforcement (Rule #0).
- No hardcoded API credentials; strictly use environment variables (`os.environ.get()`).
- All GraphQL operations must be valid against official Shopify GraphQL schemas (Storefront API, Admin API, Customer Account API).
- Write metadata and reports only in `.agents/survey_explorer_3/`.

## Current Parent
- Conversation ID: 9e0d5e24-d9fb-49d8-b62d-be34c78d1690
- Updated: 2026-08-28T19:47:00Z

## Loaded Skills
- **Source**: `/Volumes/aaronmaher/Lauburu-Monorepo/.agents/skills/spec-08-business-commerce/SKILL.md`
  - **Core methodology**: Business & Monetization Specialist AI governing Shopify Storefront GraphQL, membership tiers, subscription billing, CAC/LTV modeling, and merchandise profitability.
- **Source**: `/Users/aaron/.gemini/config/plugins/shopify-plugin/skills/shopify-storefront-graphql/SKILL.md`
  - **Core methodology**: Shopify Storefront GraphQL query and mutation generation and validation.
- **Source**: `/Users/aaron/.gemini/config/plugins/shopify-plugin/skills/shopify-customer/SKILL.md`
  - **Core methodology**: Shopify Customer Account API for customer data, subscriptions, and authentication.
- **Source**: `/Users/aaron/.gemini/config/plugins/shopify-plugin/skills/shopify-admin/SKILL.md`
  - **Core methodology**: Shopify Admin API GraphQL query and mutation operations for subscription contracts.

## Task Summary
- **What to build**: Comprehensive architectural and data specification for R2 (Shopify Headless Monetization Engine) covering package layout, client configuration, rate limiting, error handling, and 3 core use cases: (1) Recurring Subscriptions (OpenClaw AI API), (2) Hardware Kit Cart (GL.iNet + Movesense), (3) Token-Gated Authentication (Spatial Grappling 3D / Port 4000).
- **Success criteria**: Fully verified GraphQL operations, exact input/return types, rate limiting algorithms, fallback logic, test suite design, and handoff report.
- **Interface contracts**: `08_business_and_commerce/shopify_headless/` interface contracts with `01_apps/canonical_port` Port 4000 Hub and `01_apps/spatial_and_3d/spatial_grappling_3d`.

## Key Decisions Made
- Use Shopify API version `2026-01` as default stable version, configurable via `SHOPIFY_API_VERSION`.
- Storefront client uses `X-Shopify-Storefront-Access-Token` and `Shopify-Storefront-Private-Token` for private server-side headless calls.
- Admin client uses `X-Shopify-Access-Token` with leaky-bucket rate limiting based on `extensions.cost.throttleStatus`.
- Support dual token-gating verification: Storefront API customer profile tags (`tier_pro`, `movesense_pro`, `spatial_grappling_pro`) and Customer Account API `subscriptionContracts`.
- Include zero-mock development token fallback pattern (`tok_dev_...`, `shpat_dev_...`) for automated offline test harnesses.

## Artifact Index
- `.agents/survey_explorer_3/DISPATCH.md` — Dispatch log and initial instructions
- `.agents/survey_explorer_3/BRIEFING.md` — Situational awareness and identity
- `.agents/survey_explorer_3/progress.md` — Liveness and milestone progress log
- `.agents/survey_explorer_3/handoff.md` — Final 5-component specification and handoff report
