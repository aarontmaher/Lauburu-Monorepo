# Project: Lauburu External GraphQL Perimeters Integration (Cloudflare Zero Trust & Shopify Headless)

## Architecture
- **Perimeter 1: Cloudflare Zero Trust & WAF Telemetry**:
  - `06_scripts_and_tooling/cloudflare_telemetry.py` queries Cloudflare GraphQL Analytics API (`https://api.cloudflare.com/client/v4/graphql`) for WAF threat blocks (`firewallEventsAdaptive`) and traffic aggregates (`httpRequestsAdaptiveGroups`), plus REST API for Zero Trust Access logs (`/accounts/{account_id}/access/logs/access_requests`).
  - Ingested by `01_apps/canonical_port/backend/training_telemetry_collector.py` and rendered dynamically inside `01_apps/canonical_port/tui/screens/training_screen.py` Tab 1 (Red/Blue Arena) and `01_apps/canonical_port/tui/widgets/lauburu_gyms_widget.py`.
  - Visual correlation between Red Team cognitive reasoning (`<think>` thought stream from Abliterated Llama) and Blue Team WAF intercept events.
- **Perimeter 2: Shopify Headless Monetization Engine**:
  - Located in `08_business_and_commerce/shopify_headless/`.
  - Modular layered architecture: `config.py` (env vars), `client.py` (Async httpx client with rate limit tracking & retry backoff), `errors.py`, `models.py` (Pydantic), `queries/` (`subscriptions.py`, `hardware_kit.py`, `token_gating.py`), and `services/` (`monetization_service.py`, `compute_offset.py`).
  - Three distinct monetization use cases:
    1. Recurring Subscriptions: OpenClaw AI API purchasing via Storefront selling plans and Admin subscription contract tracking.
    2. Hardware Kit Cart: Mesh node bundling (GL.iNet MT3600BE Router + Movesense Medical ECG) with custom device attributes and buyer identity.
    3. Token-Gated Authentication: Customer Account / Storefront API profile verification unlocking the 3D Spatial Grappling UI and Port 4000 Hub.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Cloudflare GraphQL Analytics Collector | Queries `firewallEventsAdaptive` & `httpRequestsAdaptiveGroups` for WAF blocks | M1 | Survey |
| 2 | Cloudflare Zero Trust Access Audit Collector | Queries `/access/logs/access_requests` for user login/service authentications | M1 | Survey |
| 3 | Telemetry Data Models & Zero-Mock Guarantee | Typed dataclasses (`WAFThreatEvent`, `AccessAuthEvent`, `CloudflareTelemetrySnapshot`) with `--` fallback | M1 | Survey |
| 4 | TUI Red/Blue Arena Status Cards & Metrics | Tunnel health, Blue Team Access passes, Red Team threat blocks, RTT | M1 | Survey |
| 5 | TUI Subpixel Braille Sparklines | Real-time traffic & attack frequency visualization | M1 | Survey |
| 6 | TUI Live Combat & Defense Ledger Table | Rich / DataTable listing attacker IP, Geo, target path, action, rule ID | M1 | Survey |
| 7 | TUI Attack Vector & Geo Distribution Panels | Ranked attack vector list and origin country breakdown | M1 | Survey |
| 8 | Red Team Cognitive Telemetry Stream | Real-time `<think>` Chain-of-Thought stream in Tab 1 correlated with WAF blocks | M1 | User Directive |
| 9 | Non-blocking Async TUI Poller | `@work` / `set_interval` loop updating reactive telemetry without UI lag | M1 | Survey |
| 10 | Shopify Headless Configuration Loader | Environment-driven config (`SHOPIFY_STORE_DOMAIN`, tokens, version) with zero hardcoding | M2 | Survey |
| 11 | Resilient Async GraphQL Client | Async httpx client with leaky-bucket rate limiting, 429 backoff, dev token bypass | M2 | Survey |
| 12 | Use Case 1: Subscription Selling Plans Query | Queries `sellingPlanGroups` and `sellingPlans` for OpenClaw AI product | M2 | Survey |
| 13 | Use Case 1: Subscription Cart Mutation | `cartCreate` with `merchandiseId` + `sellingPlanId` for recurring billing | M2 | Survey |
| 14 | Use Case 1: Admin Subscription Contracts Query | Queries `subscriptionContracts` connection for active subscription tracking | M2 | Survey |
| 15 | Use Case 2: Multi-Item Hardware Bundle Cart | `cartCreate` for GL.iNet router + Movesense ECG bundle with custom device attributes | M2 | Survey |
| 16 | Use Case 2: Progressive Hardware Line Updates | `cartLinesAdd` for adding mesh nodes / accessories to existing cart | M2 | Survey |
| 17 | Use Case 2: Buyer Identity & Shipping Preferences | `cartBuyerIdentityUpdate` for country code and delivery rates | M2 | Survey |
| 18 | Use Case 2: Cart Discount Code Application | `cartDiscountCodesUpdate` for bundle promo codes ($0 hardware commitment) | M2 | Survey |
| 19 | Use Case 3: Customer Access Token Creation | `customerAccessTokenCreate` for Storefront login session | M2 | Survey |
| 20 | Use Case 3: Customer Gated Profile Query | `customer(customerAccessToken: ...)` querying membership tags (`tier_pro`) | M2 | Survey |
| 21 | Use Case 3: Customer Account Subscriptions | Direct query against Customer Account API for subscriber status | M2 | Survey |
| 22 | Use Case 3: Spatial Grappling Gatekeeper Service | Verifies subscription status before unlocking 3D Tatami Kinematics | M2 | Survey |
| 23 | Comprehensive E2E Test Suite | 4-tier test harness covering Cloudflare telemetry, TUI rendering, and Shopify engine | M3 | Dual Track |
| 24 | Adversarial Stress & Integrity Audit | White-box vulnerability testing, zero-mock audit, and secret leakage prevention | M3 | Dual Track |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Cloudflare Zero Trust Telemetry & TUI Arena | `06_scripts_and_tooling/cloudflare_telemetry.py`, `01_apps/canonical_port/tui/screens/training_screen.py`, `01_apps/canonical_port/tui/widgets/lauburu_gyms_widget.py`, `01_apps/canonical_port/tui/widgets/red_blue_arena_widget.py` | none | DONE |
| 2 | M2: Shopify Headless Monetization Engine | `08_business_and_commerce/shopify_headless/` (config, client, errors, models, queries, services, tests) | none | DONE |
| 3 | M3: Dual Track E2E Test Suite & Adversarial Audit | Test suite across all 4 tiers (175 tests), adversarial stress testing, Forensic integrity audit | M1, M2 | DONE |


## Interface Contracts
### `cloudflare_telemetry.py` ↔ `training_screen.py`
- Function: `get_cloudflare_zero_trust_snapshot(time_window_minutes: int = 60) -> Dict[str, Any]`
- Dataclass: `CloudflareTelemetrySnapshot` serializable to JSON
- Key fields: `status`, `is_configured`, `summary` (`total_threats_blocked`, `total_challenges_issued`, `top_attacked_host`), `threat_events` (`timestamp`, `action`, `client_ip`, `country`, `path`, `rule_id`, `description`, `ray_id`), `access_events` (`user_email`, `allowed`, `connection_type`, `country`), `red_team_thoughts` (`timestamp`, `model_id`, `thought_summary`, `attack_vector`, `target_endpoint`).
- Rule #0 invariant: When credentials are missing or no live events exist, all numerical fields render `--` and event lists are empty `[]`.

### `shopify_headless` ↔ Consumers (Port 4000 Hub / Spatial Grappling UI)
- High-level Service: `ShopifyMonetizationService`
  - `create_subscription_checkout(handle: str, plan_id: str) -> SubscriptionCheckoutResponse`
  - `create_hardware_kit_cart(items: List[HardwareItemInput], buyer_identity: Optional[BuyerIdentityInput] = None) -> CartResponse`
  - `verify_token_gated_access(customer_token: str, required_tier: str = "tier_pro") -> TokenGatedAccessGrant`
- Error handling: Raises `ShopifyGraphQLError`, `ShopifyRateLimitError`, `ShopifyUserError`.
- Dev token bypass: Tokens matching `tok_dev_*` / `shpat_dev_*` return verified active subscription grants for local offline testing.

## Code Layout
- `06_scripts_and_tooling/cloudflare_telemetry.py`
- `01_apps/canonical_port/tui/screens/training_screen.py`
- `01_apps/canonical_port/tui/widgets/lauburu_gyms_widget.py`
- `01_apps/canonical_port/tui/widgets/red_blue_arena_widget.py` (shared Arena component)
- `08_business_and_commerce/shopify_headless/`
  - `__init__.py`
  - `config.py`
  - `client.py`
  - `errors.py`
  - `models.py`
  - `queries/__init__.py`
  - `queries/subscriptions.py`
  - `queries/hardware_kit.py`
  - `queries/token_gating.py`
  - `services/__init__.py`
  - `services/monetization_service.py`
  - `services/compute_offset.py`
  - `tests/`
- `tests/e2e/test_cloudflare_telemetry_tui_e2e.py`
- `tests/e2e/test_shopify_headless_e2e.py`
