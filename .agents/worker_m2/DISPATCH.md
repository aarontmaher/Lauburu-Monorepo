## 2026-08-28T19:51:00Z
You are Worker 2 for Milestone 2 (M2: Shopify Headless Monetization Engine) of the Lauburu Ecosystem project.
Your Working Directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/worker_m2/
Please create your working directory and write all your metadata, progress, and handoff.md report inside it.

Mandatory Context & Specifications to Read:
1. /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md
2. /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/PROJECT.md
3. /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_3/handoff.md
4. Domain Skill: /Volumes/aaronmaher/Lauburu-Monorepo/.agents/skills/spec-08-business-commerce/SKILL.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope & Assigned Files:
You have exclusive write ownership of `08_business_and_commerce/shopify_headless/`:
- `08_business_and_commerce/shopify_headless/__init__.py`
- `08_business_and_commerce/shopify_headless/config.py`
- `08_business_and_commerce/shopify_headless/client.py`
- `08_business_and_commerce/shopify_headless/errors.py`
- `08_business_and_commerce/shopify_headless/models.py`
- `08_business_and_commerce/shopify_headless/queries/__init__.py`
- `08_business_and_commerce/shopify_headless/queries/subscriptions.py`
- `08_business_and_commerce/shopify_headless/queries/hardware_kit.py`
- `08_business_and_commerce/shopify_headless/queries/token_gating.py`
- `08_business_and_commerce/shopify_headless/services/__init__.py`
- `08_business_and_commerce/shopify_headless/services/monetization_service.py`
- `08_business_and_commerce/shopify_headless/services/compute_offset.py`
- `08_business_and_commerce/shopify_headless/tests/` (unit and integration tests)

Implementation Requirements:
1. `config.py`: Environment-driven config loading (`SHOPIFY_STORE_DOMAIN`, `SHOPIFY_STOREFRONT_ACCESS_TOKEN`, `SHOPIFY_STOREFRONT_PRIVATE_TOKEN`, `SHOPIFY_ADMIN_ACCESS_TOKEN`, `SHOPIFY_API_VERSION="2026-01"`, `SHOPIFY_TIMEOUT_SECONDS=8.0`). Zero hardcoding.
2. `client.py`: Async httpx client with leaky-bucket rate limiting (`extensions.cost.throttleStatus`), exponential backoff retries on 429 / THROTTLED, and dev token offline fallback (`tok_dev_*`, `shpat_dev_*`).
3. `errors.py` & `models.py`: Exception taxonomy and typed Pydantic models for carts, lines, selling plans, subscriptions, and access grants.
4. `queries/subscriptions.py` (Use Case 1): Storefront `getProductWithSellingPlans`, `createSubscriptionCart` (using `merchandiseId` + `sellingPlanId`), Admin `getCustomerSubscriptionContracts`.
5. `queries/hardware_kit.py` (Use Case 2): Storefront `createHardwareKitCart` (multi-item GL.iNet + Movesense bundle), `addHardwareKitLines`, `updateCartBuyerIdentity`, `updateCartDiscountCodes`.
6. `queries/token_gating.py` (Use Case 3): Storefront `customerAccessTokenCreate`, `getCustomerGatedProfile` (membership tags `tier_pro`), Customer Account `getCustomerAccountSubscription`.
7. `services/monetization_service.py`: High-level domain workflows connecting the 3 use cases.
8. `services/compute_offset.py`: 70% gross margin compute offset calculator.
9. `tests/`: Comprehensive unit tests verifying query formatting, client execution, retry handling, and monetization services.
10. Run pytest on your tests and ensure 100% pass rate.
