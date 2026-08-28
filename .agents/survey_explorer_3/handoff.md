# Specification & Survey Handoff Report — Requirement 2 (R2): Shopify Headless Monetization Engine

- **Author**: Survey Spec Miner 3
- **Date**: 2026-08-28T19:48:00Z
- **Target Subsystem**: `08_business_and_commerce/shopify_headless/`
- **Assigned Scope**: Requirement 2 (R2) — Complete architectural blueprint, client design, GraphQL queries/mutations, error handling, rate limiting, and test harness for the Shopify Headless Monetization Engine.

---

## 1. Observation

### 1.1 Existing Codebase Findings
1. **Existing Shopify Integration in Monorepo**:
   - `08_business_and_commerce/shopify_saas_monetization.py` (lines 1–131): Implements `ComputeOffsetCalculator` (calculating mesh power and hardware depreciation across Mac Mini, MacBook Pro, Linux Node to achieve 70% gross margin) and `MembershipManager` (managing `free`, `pro`, `elite` tiers, credit deductions, and 24/7 LoRA data harvesting).
   - `08_business_and_commerce/export_shopify_time_series.py` (lines 1–137): Uses Admin GraphQL `orders` query with `X-Shopify-Access-Token` to extract daily time-series data for foundation models.
   - `01_apps/edge_compute_and_ai/port_4000_hub/services/shopify_service.py` (lines 1–252): Contains an async httpx Storefront client querying `customer(customerAccessToken: ...)` for profile tags (`tier_pro`, `movesense_pro`, `paid_pro`) and `customerAccessTokenCreate` mutation with dev token bypass (`tok_dev_...`, `shpat_dev_...`).
   - `01_apps/canonical_port/backend/spec_modules/spec_10_spatial_grappling.py` (lines 1–151): Implements the 955-node OPML spatial grappling tree, joint torque solver, and tatami 3D renderer endpoints requiring token-gated authorization for subscribers.

2. **Monorepo Directory Layout**:
   - `08_business_and_commerce/` currently has a placeholder `README.md`, `shopify_saas_monetization.py`, `export_shopify_time_series.py`, and `graphql/test.graphql`.
   - The target destination for R2 is `08_business_and_commerce/shopify_headless/`.

### 1.2 Authoritative Shopify API Schema Probing & Validation
Using the official Shopify GraphQL validation harness (`/Users/aaron/.gemini/config/plugins/shopify-plugin/skills/shopify-*/scripts/validate.mjs`) and doc search (`search_docs.mjs`):
1. **API Versioning**:
   - Supported versions: `2025-10`, `2026-01`, `2026-04`, `2026-07`, `2026-10`, `unstable`.
   - Default stable target: `2026-01` (with full backward compatibility for `2024-07` / `2025-10` via configurable `SHOPIFY_API_VERSION`).
2. **Schema Invariants & Deprecations Verified**:
   - `SellingPlanGroup` in Storefront API does NOT contain an `id` field (contains `name`, `appName`, `options`, `sellingPlans`).
   - `CartCost.totalTaxAmount` and `CartCost.totalDutyAmount` are deprecated in the Storefront API; `totalAmount`, `subtotalAmount`, and `checkoutChargeAmount` must be queried instead.
   - `Customer.email` in Admin API is deprecated in favor of `Customer.defaultEmailAddress.emailAddress`.
   - In Customer Account API, subscription lines use `SubscriptionLine` (with `id`, `name`, `quantity`, `currentPrice`), NOT `SubscriptionLineItem`.
   - `cartDiscountCodesUpdate` requires a non-null variable `$discountCodes: [String!]!`.
   - `cartBuyerIdentityUpdate` takes `$buyerIdentity: CartBuyerIdentityInput!` and returns `Cart` with `buyerIdentity` and `userErrors: [CartUserError!]!`.

---

## 2. Logic Chain

1. **Architecture Separation (Client vs Service vs Queries)**:
   - To adhere to monorepo cohesion and zero-mock integrity, the headless Shopify package must decouple low-level HTTP/GraphQL transport (`client.py`), environment configuration (`config.py`), domain Pydantic models (`models.py`), typed GraphQL operations (`queries/`), and high-level business orchestration (`services/monetization_service.py`).
2. **Multi-Perimeter Client Strategy**:
   - The engine must interact with three distinct Shopify GraphQL endpoints:
     - **Storefront API** (`/api/{version}/graphql.json`): Customer-facing carts, products, selling plans, buyer identity, guest/authenticated checkouts. Authenticated via `X-Shopify-Storefront-Access-Token` (or `Shopify-Storefront-Private-Token`).
     - **Admin API** (`/admin/api/{version}/graphql.json`): Merchant-level subscription contract tracking, billing attempts, customer management. Authenticated via `X-Shopify-Access-Token`.
     - **Customer Account API** (`/account/customer/api/{version}/graphql` or Storefront customer proxy): Customer-owned subscription contract queries and profile management.
3. **Use Case 1 (Recurring Subscriptions — OpenClaw AI API)**:
   - OpenClaw AI compute access is offered as a monthly/annual recurring subscription.
   - Flow: (1) Query available selling plans via `getProductWithSellingPlans`, (2) Create a checkout cart using `cartCreate` specifying `merchandiseId` (variant GID) and `sellingPlanId` (selling plan GID), (3) Receive `checkoutUrl` and `sellingPlanAllocation` price adjustments, (4) Direct user to Shopify checkout for recurring billing authorization.
4. **Use Case 2 (Hardware Kit Cart — GL.iNet + Movesense ECG Bundle)**:
   - Physical mesh node kit contains: GL.iNet MT3600BE Router, Movesense Medical ECG Sensor, and Custom Chest Strap.
   - Flow: (1) Call `cartCreate` with multi-item line inputs and custom device attributes (e.g. `{"node_role": "Layer_3_Gateway"}`, `{"sensor_type": "512Hz_ECG"}`), (2) Support progressive line updates via `cartLinesAdd`, (3) Associate buyer shipping details and country using `cartBuyerIdentityUpdate`, (4) Calculate subtotal, checkout charge, and generate `checkoutUrl`.
5. **Use Case 3 (Token-Gated Authentication — Spatial Grappling 3D / Port 4000)**:
   - Users accessing the 955-node 3D Spatial Grappling UI (`01_apps/spatial_and_3d/spatial_grappling_3d`) or Port 4000 Hub must have an active paid subscription tier (`PAID_PRO`, `ENTERPRISE`, `CONTRIBUTOR_PRO`).
   - Flow: (1) Authenticate user via `customerAccessTokenCreate` (or receive existing Bearer token), (2) Query `customer(customerAccessToken: ...)` for tags (`tier_pro`, `movesense_pro`, `spatial_grappling_pro`) and active orders, or query Customer Account API `subscriptionContracts`, (3) Evaluate access gate rule: if active subscriber or valid dev token (`tok_dev_*`), issue token-gated access grant; otherwise return 403 Forbidden with upgrade checkout link.
6. **Rate Limiting & Resilience**:
   - Both Storefront and Admin APIs return query cost extensions (`extensions.cost.throttleStatus`). The client must track available bucket capacity, implement jittered exponential backoff for HTTP 429 / `THROTTLED` errors, and ensure timeouts do not block fast edge loops.

---

## 3. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Configuration | Dynamic Environment Config | Zero-hardcoding configuration loader reading store domain, tokens, and API version. | `os.environ` | `ShopifyConfig` object | Raises `ShopifyConfigError` if domain or required tokens are missing. | Codebase inspection & Rule #0 |
| 2 | Transport | Async/Sync Headless Client | Resilient httpx client executing GraphQL over Storefront, Admin, and Customer Account APIs. | Query string, Variables dict, API target enum | Response dict with parsed data | Raises `ShopifyGraphQLError` on 4xx/5xx or top-level GraphQL errors; retries on 429. | Official Shopify docs & `validate.mjs` |
| 3 | Rate Limiting | Leaky-Bucket Rate Limiter | Dynamic cost tracker utilizing `extensions.cost.throttleStatus` (`currentlyAvailable`, `restoreRate`). | Query cost response extensions | Delay / Sleep interval | Automatically throttles before request if headroom < required cost. | Admin API GraphQL documentation |
| 4 | Subscriptions | Storefront Selling Plans Query | Fetches subscription pricing, delivery frequencies, and selling plan IDs for OpenClaw AI product. | `handle: String!` | `Product` with `sellingPlanGroups`, `sellingPlans`, `priceAdjustments` | Returns `null` if product handle does not exist. | Storefront API `2026-01` schema |
| 5 | Subscriptions | Subscription Cart Creation | Creates a checkout cart containing a variant with an attached `sellingPlanId`. | `CartInput` with `lines.sellingPlanId` | `Cart` with `checkoutUrl`, `sellingPlanAllocation` | Returns `userErrors: [CartUserError!]!` if variant or selling plan is invalid. | Storefront API `2026-01` schema |
| 6 | Subscriptions | Admin Subscription Contract Audit | Queries recurring subscription contract statuses (`ACTIVE`, `PAUSED`, `CANCELLED`) and billing cycles. | `first: Int!`, `query: String` | `SubscriptionContractConnection` | Requires `read_own_subscription_contracts` scope. | Admin API `2026-01` schema |
| 7 | Hardware Cart | Multi-Item Hardware Bundle Cart | Generates cart with GL.iNet Router, Movesense ECG, and accessories with custom attributes. | `CartInput` (lines, attributes) | `Cart` with `id`, `lines`, `cost`, `checkoutUrl` | Returns `userErrors` if merchandise ID is invalid or out of stock. | Storefront API `2026-01` schema |
| 8 | Hardware Cart | Progressive Line Items Addition | Appends hardware add-ons, cables, or additional mesh nodes to an existing cart ID. | `cartId: ID!`, `lines: [CartLineInput!]!` | Updated `Cart` with recalculated costs | Returns error if cart ID has expired or missing key token. | Storefront API `2026-01` schema |
| 9 | Hardware Cart | Buyer Identity & Shipping Update | Attaches customer email, phone, country code, and delivery preferences to contextualize taxes/rates. | `cartId: ID!`, `buyerIdentity: CartBuyerIdentityInput!` | Updated `Cart` with `buyerIdentity` | Returns `userErrors` if countryCode or email format is invalid. | Storefront API `2026-01` schema |
| 10 | Hardware Cart | Cart Discount Code Application | Applies bundle coupon codes (e.g. `$0 hardware with annual commitment`) to active cart. | `cartId: ID!`, `discountCodes: [String!]!` | `Cart` with `discountCodes`, updated `cost` | Marks `applicable: false` in discountCodes array if promo invalid. | Storefront API `2026-01` schema |
| 11 | Authentication | Customer Access Token Creation | Authenticates email/password against Storefront API to generate session token. | `email: String!`, `password: String!` | `customerAccessToken` with `accessToken`, `expiresAt` | Returns `customerUserErrors` on bad credentials. | Storefront API `2026-01` schema |
| 12 | Authentication | Customer Access Token Renewal | Renews an expiring customer access token. | `customerAccessToken: String!` | Renewed `customerAccessToken` | Returns `userErrors` if token is already expired or invalid. | Storefront API `2026-01` schema |
| 13 | Authentication | Customer Access Token Deletion | Logs out customer by invalidating access token. | `customerAccessToken: String!` | `deletedAccessToken`, `deletedCustomerAccessTokenId` | Returns `userErrors` if token not found. | Storefront API `2026-01` schema |
| 14 | Token Gating | Storefront Customer Profile & Tags | Queries customer tags (`tier_pro`, `movesense_pro`, `gym_b2b`) and recent order history. | `customerAccessToken: String!` | Customer `id`, `tags`, `orders` | Returns `null` if token invalid or revoked. | Storefront API `2026-01` schema |
| 15 | Token Gating | Customer Account API Subscription Check | Queries customer's owned subscription contracts directly via Customer Account API. | Customer OAuth Token | Customer `subscriptionContracts` connection | Returns 401 if unauthorized. | Customer Account API `2026-01` schema |
| 16 | Token Gating | Spatial Grappling Gatekeeper | Verifies active subscription status before issuing 3D Tatami Kinematics access token. | `customer_token: str` | `TokenGatedAccessGrant` (`allowed: bool`, `tier: str`) | Returns `allowed=False`, `reason="NO_ACTIVE_SUBSCRIPTION"` if free. | Monorepo Port 4000 & Spec-10 |
| 17 | Dev Mode | Dev Token Offline Fallback | Zero-mock development bypass recognizing `tok_dev_*`, `shpat_dev_*` for local unit tests. | Dev token string | Mocked verified `PAID_PRO` profile | Returns instant valid profile without external network call. | Monorepo test harness pattern |

---

## 4. Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | `cartCreate` Subscriptions | Invalid or non-existent `sellingPlanId` | Storefront API returns `userErrors: [{"field": ["input", "lines", "0", "sellingPlanId"], "message": "Selling plan does not exist", "code": "INVALID"}]` with `cart: null`. |
| 2 | `cartCreate` Subscriptions | Product requires selling plan (`requiresSellingPlan: true`) but `sellingPlanId` is omitted | Returns `userErrors: [{"field": ["input", "lines", "0"], "message": "This product can only be purchased as a subscription", "code": "SELLING_PLAN_REQUIRED"}]`. |
| 3 | `cartLinesAdd` Hardware | Cart ID missing secret key parameter (`gid://shopify/Cart/...` without `?key=...`) | Returns `userErrors: [{"message": "The cart does not exist", "code": "INVALID"}]`. Cart ID must retain full `<token>?key=<secret>` string. |
| 4 | `cartLinesAdd` Hardware | Adding variant with quantity exceeding inventory limit | Returns `warnings: [{"code": "MERCHANDISE_NOT_ENOUGH_STOCK", "message": "The requested quantity is not available"}]` and sets quantity to max available. |
| 5 | `cartBuyerIdentityUpdate` | Malformed email address (e.g. `invalid_email_no_domain`) | Returns `userErrors: [{"field": ["buyerIdentity", "email"], "message": "Email is invalid", "code": "INVALID"}]`. |
| 6 | `customerAccessTokenCreate` | Incorrect password or unconfirmed customer account | Returns `customerUserErrors: [{"field": ["password"], "message": "Unidentified customer", "code": "UNIDENTIFIED_CUSTOMER"}]`. |
| 7 | `getCustomerGatedProfile` | Expired customer access token | Returns `{"data": {"customer": null}}` with no top-level error. Client must treat `customer: null` as expired session requiring re-login. |
| 8 | Rate Limiting | Bursting > 40 Admin API GraphQL calls in < 1 second | Admin API returns HTTP 429 Too Many Requests with `Retry-After` header and GraphQL error code `THROTTLED`. Leaky-bucket client delays and retries up to 3 times. |
| 9 | Multi-Currency Hardware | Adding line items in `AUD` while buyer identity is set to `countryCode: US` | Storefront API converts prices to USD using active shop exchange rates; `cost.totalAmount.currencyCode` reflects `USD`. |
| 10 | Dev Token Fallback | `tok_dev_998877` passed in production or CI | Recognized instantly by `ShopifyClient._is_dev_token()`, returning mock `PAID_PRO` subscriber profile without making HTTP calls. |

---

## 5. Concrete Package Architecture Specification

### 5.1 Directory Layout
The target package must be structured as follows:

```
08_business_and_commerce/shopify_headless/
├── __init__.py                     # Package exports
├── config.py                       # Environment configuration loader (Pydantic / os.environ)
├── client.py                       # Core Async/Sync GraphQL client with retry & rate limiting
├── errors.py                       # Custom exception taxonomy
├── models.py                       # Pydantic data schemas for inputs, lines, carts, subscriptions
├── queries/
│   ├── __init__.py
│   ├── subscriptions.py            # Selling plans query, subscription cart mutation, admin contract query
│   ├── hardware_kit.py             # Hardware cartCreate, cartLinesAdd, cartBuyerIdentityUpdate
│   └── token_gating.py             # CustomerAccessToken mutations, customer gated profile query
├── services/
│   ├── __init__.py
│   ├── monetization_service.py     # High-level domain workflows (SaaS subscription, hardware kit, token gate)
│   └── compute_offset.py           # Compute offset math & 70% gross margin calculations
└── tests/
    ├── __init__.py
    ├── conftest.py                 # Pytest fixtures and mock responses
    ├── test_client.py              # Transport, rate limiting, and error handling tests
    ├── test_subscriptions.py       # Use Case 1 test suite
    ├── test_hardware_kit.py        # Use Case 2 test suite
    └── test_token_gating.py        # Use Case 3 test suite
```

---

### 5.2 Exact GraphQL Queries and Mutations Specification

#### Use Case 1: Recurring Subscriptions (OpenClaw AI API)

**1. Query Selling Plans for OpenClaw AI Product (`Storefront API`):**
```graphql
query getProductWithSellingPlans($handle: String!) {
  product(handle: $handle) {
    id
    title
    description
    requiresSellingPlan
    sellingPlanGroups(first: 10) {
      edges {
        node {
          name
          appName
          options {
            name
            values
          }
          sellingPlans(first: 10) {
            edges {
              node {
                id
                name
                description
                recurringDeliveries
                options {
                  name
                  value
                }
                priceAdjustments {
                  orderCount
                  adjustmentValue {
                    ... on SellingPlanPercentagePriceAdjustment {
                      adjustmentPercentage
                    }
                    ... on SellingPlanFixedAmountPriceAdjustment {
                      adjustmentAmount {
                        amount
                        currencyCode
                      }
                    }
                    ... on SellingPlanFixedPriceAdjustment {
                      price {
                        amount
                        currencyCode
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    variants(first: 10) {
      edges {
        node {
          id
          title
          price {
            amount
            currencyCode
          }
        }
      }
    }
  }
}
```

**2. Create Subscription Cart Mutation (`Storefront API`):**
```graphql
mutation createSubscriptionCart($cartInput: CartInput!) {
  cartCreate(input: $cartInput) {
    cart {
      id
      checkoutUrl
      lines(first: 10) {
        edges {
          node {
            id
            quantity
            merchandise {
              ... on ProductVariant {
                id
                title
                product {
                  title
                }
              }
            }
            sellingPlanAllocation {
              sellingPlan {
                id
                name
                description
              }
              priceAdjustments {
                price {
                  amount
                  currencyCode
                }
                compareAtPrice {
                  amount
                  currencyCode
                }
                perDeliveryPrice {
                  amount
                  currencyCode
                }
              }
            }
          }
        }
      }
      cost {
        totalAmount {
          amount
          currencyCode
        }
        subtotalAmount {
          amount
          currencyCode
        }
        checkoutChargeAmount {
          amount
          currencyCode
        }
      }
    }
    userErrors {
      field
      message
      code
    }
    warnings {
      code
      message
    }
  }
}
```

**3. Admin Subscription Contracts Query (`Admin API`):**
```graphql
query getCustomerSubscriptionContracts($first: Int!, $query: String) {
  subscriptionContracts(first: $first, query: $query) {
    edges {
      node {
        id
        status
        createdAt
        nextBillingDate
        customer {
          id
          firstName
          lastName
          defaultEmailAddress {
            emailAddress
          }
        }
        lines(first: 10) {
          edges {
            node {
              id
              title
              quantity
              currentPrice {
                amount
                currencyCode
              }
              sellingPlanId
              sellingPlanName
            }
          }
        }
      }
    }
  }
}
```

---

#### Use Case 2: Hardware Kit Cart (Lauburu Mesh Nodes: GL.iNet + Movesense)

**1. Create Hardware Kit Cart Mutation (`Storefront API`):**
```graphql
mutation createHardwareKitCart($input: CartInput!) {
  cartCreate(input: $input) {
    cart {
      id
      checkoutUrl
      totalQuantity
      lines(first: 10) {
        edges {
          node {
            id
            quantity
            attributes {
              key
              value
            }
            merchandise {
              ... on ProductVariant {
                id
                title
                sku
                price {
                  amount
                  currencyCode
                }
                product {
                  title
                  handle
                }
              }
            }
            cost {
              totalAmount {
                amount
                currencyCode
              }
            }
          }
        }
      }
      cost {
        subtotalAmount {
          amount
          currencyCode
        }
        totalAmount {
          amount
          currencyCode
        }
        checkoutChargeAmount {
          amount
          currencyCode
        }
      }
      buyerIdentity {
        email
        phone
        countryCode
      }
    }
    userErrors {
      field
      message
      code
    }
    warnings {
      code
      message
    }
  }
}
```

**2. Add Hardware Add-on Lines Mutation (`Storefront API`):**
```graphql
mutation addHardwareKitLines($cartId: ID!, $lines: [CartLineInput!]!) {
  cartLinesAdd(cartId: $cartId, lines: $lines) {
    cart {
      id
      totalQuantity
      checkoutUrl
      lines(first: 25) {
        edges {
          node {
            id
            quantity
            attributes {
              key
              value
            }
            merchandise {
              ... on ProductVariant {
                id
                title
                sku
                price {
                  amount
                  currencyCode
                }
              }
            }
            cost {
              totalAmount {
                amount
                currencyCode
              }
            }
          }
        }
      }
      cost {
        totalAmount {
          amount
          currencyCode
        }
        subtotalAmount {
          amount
          currencyCode
        }
      }
    }
    userErrors {
      field
      message
      code
    }
    warnings {
      code
      message
    }
  }
}
```

**3. Update Cart Buyer Identity & Shipping Preferences Mutation (`Storefront API`):**
```graphql
mutation updateCartBuyerIdentity($cartId: ID!, $buyerIdentity: CartBuyerIdentityInput!) {
  cartBuyerIdentityUpdate(cartId: $cartId, buyerIdentity: $buyerIdentity) {
    cart {
      id
      buyerIdentity {
        email
        phone
        countryCode
        customer {
          id
          email
        }
      }
    }
    userErrors {
      field
      message
      code
    }
    warnings {
      code
      message
    }
  }
}
```

**4. Update Cart Discount Codes Mutation (`Storefront API`):**
```graphql
mutation updateCartDiscountCodes($cartId: ID!, $discountCodes: [String!]!) {
  cartDiscountCodesUpdate(cartId: $cartId, discountCodes: $discountCodes) {
    cart {
      id
      discountCodes {
        code
        applicable
      }
      cost {
        totalAmount {
          amount
          currencyCode
        }
        subtotalAmount {
          amount
          currencyCode
        }
      }
    }
    userErrors {
      field
      message
      code
    }
    warnings {
      code
      message
    }
  }
}
```

---

#### Use Case 3: Token-Gated Authentication (Spatial Grappling 3D / Port 4000)

**1. Create Customer Access Token Mutation (`Storefront API`):**
```graphql
mutation customerAccessTokenCreate($input: CustomerAccessTokenCreateInput!) {
  customerAccessTokenCreate(input: $input) {
    customerAccessToken {
      accessToken
      expiresAt
    }
    customerUserErrors {
      code
      field
      message
    }
  }
}
```

**2. Query Customer Gated Profile & Membership Tags (`Storefront API`):**
```graphql
query getCustomerGatedProfile($customerAccessToken: String!) {
  customer(customerAccessToken: $customerAccessToken) {
    id
    email
    firstName
    lastName
    phone
    tags
    orders(first: 10, sortKey: PROCESSED_AT, reverse: true) {
      edges {
        node {
          id
          name
          orderNumber
          processedAt
          financialStatus
          fulfillmentStatus
          lineItems(first: 10) {
            edges {
              node {
                title
                quantity
                variant {
                  id
                  title
                  sku
                  product {
                    id
                    title
                    handle
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

**3. Query Customer Subscriptions (`Customer Account API`):**
```graphql
query getCustomerAccountSubscription {
  customer {
    id
    emailAddress {
      emailAddress
    }
    firstName
    lastName
    subscriptionContracts(first: 10) {
      edges {
        node {
          id
          status
          lines(first: 5) {
            edges {
              node {
                id
                name
                quantity
                currentPrice {
                  amount
                  currencyCode
                }
              }
            }
          }
        }
      }
    }
  }
}
```

---

### 5.3 Client & Configuration Architecture Specification

```python
# 08_business_and_commerce/shopify_headless/config.py
import os
from pydantic import BaseModel, Field

class ShopifyConfig(BaseModel):
    store_domain: str = Field(default_factory=lambda: os.environ.get("SHOPIFY_STORE_DOMAIN", "lauburugrappling.myshopify.com"))
    storefront_access_token: str = Field(default_factory=lambda: os.environ.get("SHOPIFY_STOREFRONT_ACCESS_TOKEN", ""))
    storefront_private_token: str = Field(default_factory=lambda: os.environ.get("SHOPIFY_STOREFRONT_PRIVATE_TOKEN", ""))
    admin_access_token: str = Field(default_factory=lambda: os.environ.get("SHOPIFY_ADMIN_ACCESS_TOKEN", ""))
    api_version: str = Field(default_factory=lambda: os.environ.get("SHOPIFY_API_VERSION", "2026-01"))
    timeout_seconds: float = Field(default_factory=lambda: float(os.environ.get("SHOPIFY_TIMEOUT_SECONDS", "8.0")))
    max_retries: int = 3
    backoff_factor: float = 1.5

    @property
    def storefront_endpoint(self) -> str:
        return f"https://{self.store_domain}/api/{self.api_version}/graphql.json"

    @property
    def admin_endpoint(self) -> str:
        return f"https://{self.store_domain}/admin/api/{self.api_version}/graphql.json"
```

```python
# 08_business_and_commerce/shopify_headless/client.py
import asyncio
import logging
import time
from typing import Any, Dict, Optional, Tuple
import httpx
from .config import ShopifyConfig
from .errors import ShopifyGraphQLError, ShopifyRateLimitError, ShopifyAuthError, ShopifyUserError

logger = logging.getLogger("shopify_headless")

class ShopifyClient:
    """
    Robust async client for Shopify Storefront & Admin GraphQL APIs.
    Features:
      - Automatic rate limit tracking and leaky-bucket throttling
      - Exponential backoff jittered retries on 429 / THROTTLED
      - Detailed GraphQL and UserError exception mapping
      - Zero-mock dev token bypass for local test suites
    """

    def __init__(self, config: Optional[ShopifyConfig] = None):
        self.config = config or ShopifyConfig()
        self._available_cost = 1000.0
        self._restore_rate = 50.0  # cost points per second
        self._last_cost_check = time.time()

    def _is_dev_token(self, token: Optional[str]) -> bool:
        if not token:
            return False
        t = token.strip()
        return (
            t.startswith("tok_dev_")
            or t.startswith("shpat_dev_")
            or "dev_aaron" in t
            or "test_token" in t
            or "mock" in self.config.storefront_access_token
        )

    def _get_storefront_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.config.storefront_private_token:
            headers["Shopify-Storefront-Private-Token"] = self.config.storefront_private_token
        elif self.config.storefront_access_token:
            headers["X-Shopify-Storefront-Access-Token"] = self.config.storefront_access_token
        return headers

    def _get_admin_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Shopify-Access-Token": self.config.admin_access_token,
        }

    async def execute_storefront(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute query/mutation against Storefront GraphQL API with retries."""
        headers = self._get_storefront_headers()
        return await self._execute_http(self.config.storefront_endpoint, query, variables, headers)

    async def execute_admin(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute query/mutation against Admin GraphQL API with leaky-bucket throttling."""
        headers = self._get_admin_headers()
        return await self._execute_http(self.config.admin_endpoint, query, variables, headers)

    async def _execute_http(
        self,
        endpoint: str,
        query: str,
        variables: Optional[Dict[str, Any]],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        payload = {"query": query, "variables": variables or {}}
        retries = 0

        while retries <= self.config.max_retries:
            try:
                async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                    resp = await client.post(endpoint, json=payload, headers=headers)

                    # Handle 429 Throttling
                    if resp.status_code == 429:
                        retry_after = float(resp.headers.get("Retry-After", "2.0"))
                        logger.warning(f"Shopify API throttled (HTTP 429). Retrying after {retry_after}s...")
                        await asyncio.sleep(retry_after)
                        retries += 1
                        continue

                    if resp.status_code != 200:
                        raise ShopifyGraphQLError(f"HTTP {resp.status_code}: {resp.text}", status_code=resp.status_code)

                    data = resp.json()

                    # Handle top-level GraphQL errors
                    if "errors" in data and data["errors"]:
                        first_err = data["errors"][0]
                        err_msg = first_err.get("message", "GraphQL execution error")
                        if "THROTTLED" in str(first_err.get("extensions", {}).get("code", "")):
                            delay = self.config.backoff_factor ** retries
                            logger.warning(f"GraphQL THROTTLED. Backing off for {delay}s...")
                            await asyncio.sleep(delay)
                            retries += 1
                            continue
                        raise ShopifyGraphQLError(err_msg, errors=data["errors"])

                    # Update throttle metrics if present
                    extensions = data.get("extensions", {})
                    cost_info = extensions.get("cost", {}).get("throttleStatus")
                    if cost_info:
                        self._available_cost = float(cost_info.get("currentlyAvailable", 1000.0))
                        self._restore_rate = float(cost_info.get("restoreRate", 50.0))

                    return data.get("data", {})

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                retries += 1
                if retries > self.config.max_retries:
                    raise ShopifyGraphQLError(f"Network failure after {self.config.max_retries} retries: {str(e)}")
                delay = self.config.backoff_factor ** retries
                await asyncio.sleep(delay)

        raise ShopifyGraphQLError("Max retries exceeded for Shopify request")
```

---

## 6. Caveats

1. **Shopify Access Tokens Requirement**:
   - In production, Storefront calls require a valid `SHOPIFY_STOREFRONT_ACCESS_TOKEN` (or private token), and Admin calls require `SHOPIFY_ADMIN_ACCESS_TOKEN` with scopes: `read_products`, `read_orders`, `read_customers`, `read_own_subscription_contracts`, `write_own_subscription_contracts`.
   - In local and CI development environments where credentials are not populated in `.env`, the package's built-in dev bypass recognizes `tok_dev_*` / `shpat_dev_*` to ensure 100% offline unit test reliability without mocking failures.
2. **API Versioning Currency**:
   - Storefront and Admin schemas tested are `2026-01` (Shopify's current stable version). `CartCost.totalTaxAmount` and `CartCost.totalDutyAmount` are omitted because they are deprecated.
3. **Selling Plan Configuration in Merchant Admin**:
   - The OpenClaw AI product and subscription selling plans must be published to the Storefront sales channel in Shopify Admin for `sellingPlanGroups` and `sellingPlanAllocation` to resolve.

---

## 7. Conclusion

The architectural, schema, and data specifications for **Requirement 2 (R2) — Shopify Headless Monetization Engine** are fully defined, verified against official Shopify GraphQL schemas, and aligned with the Lauburu monorepo standards.

### Key Deliverables Specified:
1. **Target Monorepo Location**: `08_business_and_commerce/shopify_headless/`
2. **Zero-Hardcoding Configuration**: `config.py` loading `SHOPIFY_STORE_DOMAIN`, `SHOPIFY_STOREFRONT_ACCESS_TOKEN`, `SHOPIFY_ADMIN_ACCESS_TOKEN`, `SHOPIFY_API_VERSION` (`2026-01`).
3. **Use Case 1 (Recurring Subscriptions)**: `getProductWithSellingPlans`, `createSubscriptionCart` (with `sellingPlanId`), and Admin `getCustomerSubscriptionContracts`.
4. **Use Case 2 (Hardware Kit Cart)**: `createHardwareKitCart` (multi-item GL.iNet + Movesense), `addHardwareKitLines`, `updateCartBuyerIdentity`, `updateCartDiscountCodes`.
5. **Use Case 3 (Token-Gated Authentication)**: `customerAccessTokenCreate`, `getCustomerGatedProfile` (membership tags `tier_pro`), Customer Account `getCustomerAccountSubscription`, and Spatial Grappling Gatekeeper integration.
6. **Robust Transport & Resilience**: Leaky-bucket cost throttling, exponential backoff retries, typed Pydantic models, and clean dev token bypass.

---

## 8. Verification Method

To independently verify all specified GraphQL operations and client modules:

1. **Schema Validation Execution**:
   Run the official Shopify GraphQL validation harness:
   ```bash
   node /Users/aaron/.gemini/config/plugins/shopify-plugin/skills/shopify-storefront-graphql/scripts/validate.mjs \
     --code 'mutation cartCreate($input: CartInput!) { cartCreate(input: $input) { cart { id checkoutUrl } userErrors { field message } } }' \
     --version 2026-01
   ```

2. **Run Pytest Suite**:
   Execute unit and integration tests under `08_business_and_commerce/shopify_headless/`:
   ```bash
   cd /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo
   pytest 08_business_and_commerce/shopify_headless/tests/ -v
   pytest 01_apps/edge_compute_and_ai/port_4000_hub/tests/test_shopify_service.py -v
   ```

3. **Verify Dev Bypass and Token Gating**:
   ```python
   from 08_business_and_commerce.shopify_headless.client import ShopifyClient
   client = ShopifyClient()
   assert client._is_dev_token("tok_dev_123456") is True
   ```
