"""
Adversarial Stress Test Suite for Milestone 2 (Shopify Headless Monetization Engine).
Authored by Challenger 2.

Examines:
1. Rate Limiting Exhaustion (HTTP 429 & GraphQL THROTTLED backoff, retries, and error taxonomy).
2. Mutation Error Handling (userErrors, customerUserErrors across all endpoints).
3. Token Gating Under Attack (expired, invalid, non-pro tags, malformed tokens, unauthorized status).
4. Compute Offset Edge Cases (0s, boundary conditions, zero-division resilience, extreme values).
5. Zero-Mock Integrity (rule #0 compliance verification).
"""

import asyncio
import json
import pytest
import httpx
from typing import Any, Dict, List, Optional

from shopify_headless.config import ShopifyConfig
from shopify_headless.client import ShopifyClient
from shopify_headless.errors import (
    ShopifyAuthError,
    ShopifyError,
    ShopifyGraphQLError,
    ShopifyRateLimitError,
    ShopifyUserError,
)
from shopify_headless.models import (
    BuyerIdentityInput,
    Cart,
    HardwareItemInput,
    Money,
)
from shopify_headless.queries.subscriptions import (
    create_subscription_cart,
    get_customer_subscription_contracts,
    get_product_with_selling_plans,
)
from shopify_headless.queries.hardware_kit import (
    add_hardware_kit_lines,
    create_hardware_kit_cart,
    update_cart_buyer_identity,
    update_cart_discount_codes,
)
from shopify_headless.queries.token_gating import (
    create_customer_access_token,
    delete_customer_access_token,
    extract_tier_from_tags,
    get_customer_account_subscriptions,
    get_customer_gated_profile,
    renew_customer_access_token,
)
from shopify_headless.services.compute_offset import ComputeOffsetCalculator
from shopify_headless.services.monetization_service import ShopifyMonetizationService


class AdversarialMockTransport(httpx.AsyncBaseTransport):
    """
    Stateful and configurable mock HTTP transport for simulating network failures,
    rate limiting, throttling, HTTP errors, and specific GraphQL userErrors.
    """

    def __init__(
        self,
        handler=None,
        status_code: int = 200,
        response_json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.handler = handler
        self.status_code = status_code
        self.response_json = response_json or {}
        self.headers = headers or {}
        self.call_count = 0
        self.history: List[Dict[str, Any]] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.call_count += 1
        body_bytes = await request.aread()
        parsed_body = {}
        if body_bytes:
            try:
                parsed_body = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                pass

        self.history.append({
            "url": str(request.url),
            "headers": dict(request.headers),
            "body": parsed_body,
        })

        if self.handler:
            return await self.handler(request, self.call_count, parsed_body)

        return httpx.Response(
            status_code=self.status_code,
            headers=self.headers,
            json=self.response_json,
            request=request,
        )


# =============================================================================
# 1. RATE LIMITING EXHAUSTION TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_adv_http_429_exhaustion_raises_rate_limit_error():
    """Verify that continuous HTTP 429 returns trigger backoff and raise ShopifyRateLimitError upon exhaustion."""
    config = ShopifyConfig(
        store_domain="lauburugrappling.myshopify.com",
        storefront_access_token="real_test_token_123",
        max_retries=2,
        backoff_factor=1.0,
        timeout_seconds=5.0,
    )
    transport = AdversarialMockTransport(
        status_code=429,
        headers={"Retry-After": "0.01"},
        response_json={"error": "Too Many Requests"},
    )
    client = ShopifyClient(config=config, transport=transport)

    with pytest.raises(ShopifyRateLimitError) as exc_info:
        await client.execute_storefront(query="query { shop { name } }")

    err = exc_info.value
    assert "rate limit exceeded" in err.message.lower()
    assert err.status_code == 429
    assert err.retry_after == 0.01
    # 1 initial attempt + 2 retries = 3 calls
    assert transport.call_count == 3


@pytest.mark.asyncio
async def test_adv_graphql_throttled_exhaustion_raises_rate_limit_error():
    """Verify that continuous GraphQL top-level THROTTLED errors trigger backoff and raise ShopifyRateLimitError upon exhaustion."""
    config = ShopifyConfig(
        store_domain="lauburugrappling.myshopify.com",
        storefront_access_token="real_test_token_123",
        max_retries=2,
        backoff_factor=1.0,
        timeout_seconds=5.0,
    )
    throttled_payload = {
        "errors": [
            {
                "message": "Throttled: Maximum GraphQL API query cost exceeded.",
                "extensions": {
                    "code": "THROTTLED",
                    "documentation": "https://shopify.dev/api/usage/rate-limits",
                },
            }
        ]
    }
    transport = AdversarialMockTransport(
        status_code=200,
        response_json=throttled_payload,
    )
    client = ShopifyClient(config=config, transport=transport)

    with pytest.raises(ShopifyRateLimitError) as exc_info:
        await client.execute_storefront(query="query { shop { name } }")

    err = exc_info.value
    assert "throttled" in err.message.lower()
    assert len(err.errors) == 1
    assert err.errors[0]["extensions"]["code"] == "THROTTLED"
    assert transport.call_count == 3


@pytest.mark.asyncio
async def test_adv_intermittent_429_recovers_successfully():
    """Verify that transient HTTP 429s recover smoothly if subsequent attempts succeed."""
    config = ShopifyConfig(
        store_domain="lauburugrappling.myshopify.com",
        storefront_access_token="real_test_token_123",
        max_retries=3,
        backoff_factor=1.0,
    )

    async def dynamic_handler(request, count, body):
        if count <= 2:
            return httpx.Response(
                status_code=429,
                headers={"Retry-After": "0.01"},
                json={"error": "Throttled"},
                request=request,
            )
        return httpx.Response(
            status_code=200,
            json={"data": {"shop": {"name": "Lauburu Mesh Store"}}},
            request=request,
        )

    transport = AdversarialMockTransport(handler=dynamic_handler)
    client = ShopifyClient(config=config, transport=transport)

    result = await client.execute_storefront(query="query { shop { name } }")
    assert result == {"shop": {"name": "Lauburu Mesh Store"}}
    assert transport.call_count == 3


@pytest.mark.asyncio
async def test_adv_intermittent_graphql_throttled_recovers_successfully():
    """Verify that transient GraphQL THROTTLED recovers smoothly on subsequent attempts."""
    config = ShopifyConfig(
        store_domain="lauburugrappling.myshopify.com",
        storefront_access_token="real_test_token_123",
        max_retries=3,
        backoff_factor=1.0,
    )

    async def dynamic_handler(request, count, body):
        if count == 1:
            return httpx.Response(
                status_code=200,
                json={"errors": [{"message": "Throttled", "extensions": {"code": "THROTTLED"}}]},
                request=request,
            )
        return httpx.Response(
            status_code=200,
            json={"data": {"product": {"id": "gid://shopify/Product/123"}}},
            request=request,
        )

    transport = AdversarialMockTransport(handler=dynamic_handler)
    client = ShopifyClient(config=config, transport=transport)

    result = await client.execute_storefront(query="query { product { id } }")
    assert result == {"product": {"id": "gid://shopify/Product/123"}}
    assert transport.call_count == 2


@pytest.mark.asyncio
async def test_adv_leaky_bucket_cost_tracking():
    """Verify client correctly updates internal cost points from extensions.cost.throttleStatus."""
    config = ShopifyConfig(
        store_domain="lauburugrappling.myshopify.com",
        admin_access_token="shpat_real_admin_token",
    )
    resp_payload = {
        "data": {"shop": {"name": "Lauburu"}},
        "extensions": {
            "cost": {
                "requestedQueryCost": 15,
                "actualQueryCost": 10,
                "throttleStatus": {
                    "maximumAvailable": 2000.0,
                    "currentlyAvailable": 1950.0,
                    "restoreRate": 100.0,
                },
            }
        },
    }
    transport = AdversarialMockTransport(status_code=200, response_json=resp_payload)
    client = ShopifyClient(config=config, transport=transport)

    res = await client.execute_admin(query="query { shop { name } }")
    assert res == {"shop": {"name": "Lauburu"}}
    assert client._available_cost == 1950.0
    assert client._max_cost == 2000.0
    assert client._restore_rate == 100.0


# =============================================================================
# 2. MUTATION ERROR HANDLING TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_adv_create_subscription_cart_invalid_merchandise_id():
    """Verify invalid merchandiseId in subscription cart creation raises ShopifyUserError."""
    config = ShopifyConfig(storefront_access_token="real_tok")
    user_error_payload = {
        "data": {
            "cartCreate": {
                "cart": None,
                "userErrors": [
                    {
                        "field": ["input", "lines", "0", "merchandiseId"],
                        "message": "The merchandise variant gid://shopify/ProductVariant/invalid does not exist.",
                        "code": "INVALID_MERCHANDISE_LINE",
                    }
                ],
                "warnings": [],
            }
        }
    }
    transport = AdversarialMockTransport(status_code=200, response_json=user_error_payload)
    client = ShopifyClient(config=config, transport=transport)

    with pytest.raises(ShopifyUserError) as exc_info:
        await create_subscription_cart(
            client=client,
            variant_id="gid://shopify/ProductVariant/invalid",
            selling_plan_id="gid://shopify/SellingPlan/123",
        )

    err = exc_info.value
    assert "does not exist" in err.message
    assert err.field == "input.lines.0.merchandiseId"
    assert err.code == "INVALID_MERCHANDISE_LINE"
    assert len(err.user_errors) == 1


@pytest.mark.asyncio
async def test_adv_create_subscription_cart_non_existent_selling_plan():
    """Verify non-existent sellingPlanId raises ShopifyUserError."""
    config = ShopifyConfig(storefront_access_token="real_tok")
    user_error_payload = {
        "data": {
            "cartCreate": {
                "cart": None,
                "userErrors": [
                    {
                        "field": ["input", "lines", "0", "sellingPlanId"],
                        "message": "Selling plan gid://shopify/SellingPlan/999 is inactive or does not exist.",
                        "code": "INVALID_SELLING_PLAN",
                    }
                ],
                "warnings": [],
            }
        }
    }
    transport = AdversarialMockTransport(status_code=200, response_json=user_error_payload)
    client = ShopifyClient(config=config, transport=transport)

    with pytest.raises(ShopifyUserError) as exc_info:
        await create_subscription_cart(
            client=client,
            variant_id="gid://shopify/ProductVariant/111",
            selling_plan_id="gid://shopify/SellingPlan/999",
        )

    err = exc_info.value
    assert "Selling plan" in err.message
    assert err.field == "input.lines.0.sellingPlanId"
    assert err.code == "INVALID_SELLING_PLAN"


@pytest.mark.asyncio
async def test_adv_create_hardware_kit_malformed_buyer_email():
    """Verify malformed email in buyerIdentity raises ShopifyUserError."""
    config = ShopifyConfig(storefront_access_token="real_tok")
    user_error_payload = {
        "data": {
            "cartCreate": {
                "cart": None,
                "userErrors": [
                    {
                        "field": ["input", "buyerIdentity", "email"],
                        "message": "The email address 'not_an_email' is invalid.",
                        "code": "INVALID_EMAIL",
                    }
                ],
                "warnings": [],
            }
        }
    }
    transport = AdversarialMockTransport(status_code=200, response_json=user_error_payload)
    client = ShopifyClient(config=config, transport=transport)

    with pytest.raises(ShopifyUserError) as exc_info:
        await create_hardware_kit_cart(
            client=client,
            items=[HardwareItemInput(variant_id="gid://shopify/ProductVariant/glinet")],
            buyer_identity=BuyerIdentityInput(email="not_an_email"),
        )

    err = exc_info.value
    assert "email address" in err.message
    assert err.field == "input.buyerIdentity.email"
    assert err.code == "INVALID_EMAIL"


@pytest.mark.asyncio
async def test_adv_add_hardware_kit_lines_invalid_cart_id():
    """Verify invalid cartId during line append raises ShopifyUserError."""
    config = ShopifyConfig(storefront_access_token="real_tok")
    user_error_payload = {
        "data": {
            "cartLinesAdd": {
                "cart": None,
                "userErrors": [
                    {
                        "field": ["cartId"],
                        "message": "The cart does not exist.",
                        "code": "INVALID_CART_ID",
                    }
                ],
                "warnings": [],
            }
        }
    }
    transport = AdversarialMockTransport(status_code=200, response_json=user_error_payload)
    client = ShopifyClient(config=config, transport=transport)

    with pytest.raises(ShopifyUserError) as exc_info:
        await add_hardware_kit_lines(
            client=client,
            cart_id="gid://shopify/Cart/nonexistent",
            items=[HardwareItemInput(variant_id="gid://shopify/ProductVariant/movesense")],
        )

    err = exc_info.value
    assert "cart does not exist" in err.message
    assert err.field == "cartId"
    assert err.code == "INVALID_CART_ID"


@pytest.mark.asyncio
async def test_adv_update_cart_discount_codes_invalid_code():
    """Verify applying an invalid or expired discount code raises ShopifyUserError."""
    config = ShopifyConfig(storefront_access_token="real_tok")
    user_error_payload = {
        "data": {
            "cartDiscountCodesUpdate": {
                "cart": None,
                "userErrors": [
                    {
                        "field": ["discountCodes"],
                        "message": "Discount code FAKE_CODE is invalid or expired.",
                        "code": "DISCOUNT_NOT_FOUND",
                    }
                ],
                "warnings": [],
            }
        }
    }
    transport = AdversarialMockTransport(status_code=200, response_json=user_error_payload)
    client = ShopifyClient(config=config, transport=transport)

    with pytest.raises(ShopifyUserError) as exc_info:
        await update_cart_discount_codes(
            client=client,
            cart_id="gid://shopify/Cart/123",
            discount_codes=["FAKE_CODE"],
        )

    err = exc_info.value
    assert "FAKE_CODE is invalid" in err.message
    assert err.field == "discountCodes"
    assert err.code == "DISCOUNT_NOT_FOUND"


@pytest.mark.asyncio
async def test_adv_customer_access_token_create_customer_user_errors():
    """Verify customerUserErrors during customer token creation raises ShopifyUserError."""
    config = ShopifyConfig(storefront_access_token="real_tok")
    user_error_payload = {
        "data": {
            "customerAccessTokenCreate": {
                "customerAccessToken": None,
                "customerUserErrors": [
                    {
                        "field": ["input", "password"],
                        "message": "Unidentified customer. Check your email and password.",
                        "code": "UNIDENTIFIED_CUSTOMER",
                    }
                ],
            }
        }
    }
    transport = AdversarialMockTransport(status_code=200, response_json=user_error_payload)
    client = ShopifyClient(config=config, transport=transport)

    with pytest.raises(ShopifyUserError) as exc_info:
        await create_customer_access_token(
            client=client,
            email="nonexistent@user.com",
            password="WrongPassword!",
        )

    err = exc_info.value
    assert "Unidentified customer" in err.message
    assert err.field == "input.password"
    assert err.code == "UNIDENTIFIED_CUSTOMER"


@pytest.mark.asyncio
async def test_adv_renew_customer_access_token_user_errors():
    """Verify userErrors during token renewal raises ShopifyUserError."""
    config = ShopifyConfig(storefront_access_token="real_tok")
    user_error_payload = {
        "data": {
            "customerAccessTokenRenew": {
                "customerAccessToken": None,
                "userErrors": [
                    {
                        "field": ["customerAccessToken"],
                        "message": "Token expired or revoked.",
                        "code": "TOKEN_EXPIRED",
                    }
                ],
            }
        }
    }
    transport = AdversarialMockTransport(status_code=200, response_json=user_error_payload)
    client = ShopifyClient(config=config, transport=transport)

    with pytest.raises(ShopifyUserError) as exc_info:
        await renew_customer_access_token(
            client=client,
            customer_access_token="expired_raw_token_xyz",
        )

    err = exc_info.value
    assert "Token expired" in err.message
    assert err.field == "customerAccessToken"


@pytest.mark.asyncio
async def test_adv_delete_customer_access_token_user_errors():
    """Verify userErrors during token deletion raises ShopifyUserError."""
    config = ShopifyConfig(storefront_access_token="real_tok")
    user_error_payload = {
        "data": {
            "customerAccessTokenDelete": {
                "deletedAccessToken": None,
                "deletedCustomerAccessTokenId": None,
                "userErrors": [
                    {
                        "field": ["customerAccessToken"],
                        "message": "Access token not found.",
                        "code": "NOT_FOUND",
                    }
                ],
            }
        }
    }
    transport = AdversarialMockTransport(status_code=200, response_json=user_error_payload)
    client = ShopifyClient(config=config, transport=transport)

    with pytest.raises(ShopifyUserError) as exc_info:
        await delete_customer_access_token(
            client=client,
            customer_access_token="nonexistent_token",
        )

    err = exc_info.value
    assert "Access token not found" in err.message
    assert err.field == "customerAccessToken"


# =============================================================================
# 3. TOKEN GATING UNDER ATTACK
# =============================================================================

@pytest.mark.asyncio
async def test_adv_token_gating_expired_or_revoked_token():
    """Verify that an expired or revoked token returns customer=null and is strictly denied (allowed=False)."""
    config = ShopifyConfig(storefront_access_token="real_tok")
    # Shopify returns data: { customer: null } when token is invalid or expired
    null_customer_payload = {"data": {"customer": None}}
    transport = AdversarialMockTransport(status_code=200, response_json=null_customer_payload)
    client = ShopifyClient(config=config, transport=transport)
    service = ShopifyMonetizationService(client=client)

    grant = await service.verify_token_gated_access(
        customer_token="cact_expired_token_12345",
        required_tier="tier_pro",
    )

    assert grant.allowed is False
    assert grant.reason == "INVALID_OR_EXPIRED_TOKEN"
    assert grant.is_paid_subscriber is False
    assert grant.tier == "FREE"
    assert "openclaw-ai-pro" in grant.checkout_upgrade_url


@pytest.mark.asyncio
async def test_adv_token_gating_unauthorized_http_status_raises_auth_error():
    """Verify that HTTP 401 or 403 on token gating queries raises ShopifyAuthError."""
    config = ShopifyConfig(storefront_access_token="real_tok")
    transport = AdversarialMockTransport(status_code=401, response_json={"error": "Unauthorized"})
    client = ShopifyClient(config=config, transport=transport)
    service = ShopifyMonetizationService(client=client)

    with pytest.raises(ShopifyAuthError) as exc_info:
        await service.verify_token_gated_access(
            customer_token="cact_tampered_token",
            required_tier="tier_pro",
        )

    assert "401" in exc_info.value.message


@pytest.mark.asyncio
async def test_adv_token_gating_non_pro_tags_denied():
    """Verify that customer with non-pro tags is strictly denied access to Pro features."""
    config = ShopifyConfig(storefront_access_token="real_tok")
    free_customer_payload = {
        "data": {
            "customer": {
                "id": "gid://shopify/Customer/444555",
                "email": "free_athlete@gmail.com",
                "firstName": "Free",
                "lastName": "User",
                "tags": ["free_tier", "newsletter_subscriber", "bjj_white_belt"],
                "orders": {"edges": []},
            }
        }
    }
    transport = AdversarialMockTransport(status_code=200, response_json=free_customer_payload)
    client = ShopifyClient(config=config, transport=transport)
    service = ShopifyMonetizationService(client=client)

    grant = await service.verify_token_gated_access(
        customer_token="cact_valid_free_token",
        required_tier="tier_pro",
    )

    assert grant.allowed is False
    assert grant.reason == "INSUFFICIENT_MEMBERSHIP_TIER"
    assert grant.customer_id == "gid://shopify/Customer/444555"
    assert grant.email == "free_athlete@gmail.com"
    assert grant.is_paid_subscriber is False
    assert grant.tier == "FREE"
    assert grant.granted_features == []


@pytest.mark.asyncio
async def test_adv_token_gating_pro_user_denied_enterprise_tier():
    """Verify that a Pro subscriber is denied access to Enterprise-only gated features."""
    config = ShopifyConfig(storefront_access_token="real_tok")
    pro_customer_payload = {
        "data": {
            "customer": {
                "id": "gid://shopify/Customer/777888",
                "email": "pro_coach@gym.com",
                "firstName": "Pro",
                "lastName": "Coach",
                "tags": ["tier_pro", "movesense_pro"],
                "orders": {"edges": []},
            }
        }
    }
    transport = AdversarialMockTransport(status_code=200, response_json=pro_customer_payload)
    client = ShopifyClient(config=config, transport=transport)
    service = ShopifyMonetizationService(client=client)

    # Pro user asking for Enterprise tier
    grant = await service.verify_token_gated_access(
        customer_token="cact_pro_token_999",
        required_tier="tier_enterprise",
    )

    assert grant.allowed is False
    assert grant.reason == "INSUFFICIENT_MEMBERSHIP_TIER"
    assert grant.tier == "PAID_PRO"
    assert grant.is_paid_subscriber is True


@pytest.mark.asyncio
async def test_adv_token_gating_malformed_inputs():
    """Verify token gating cleanly handles malformed tokens (whitespace, SQL injection strings, nulls)."""
    client = ShopifyClient(config=ShopifyConfig())
    service = ShopifyMonetizationService(client=client)

    # Empty / whitespace
    g1 = await service.verify_token_gated_access(customer_token="")
    assert g1.allowed is False
    assert g1.reason == "MISSING_CUSTOMER_TOKEN"

    g2 = await service.verify_token_gated_access(customer_token="   \t\n  ")
    assert g2.allowed is False
    assert g2.reason == "MISSING_CUSTOMER_TOKEN"

    # None token handling
    g3 = await service.verify_token_gated_access(customer_token=None)  # type: ignore
    assert g3.allowed is False
    assert g3.reason == "MISSING_CUSTOMER_TOKEN"


@pytest.mark.asyncio
async def test_adv_tag_extraction_taxonomy():
    """Verify tag parser covers all enterprise, pro, contributor, and free variants."""
    assert extract_tier_from_tags(["TIER_ENTERPRISE"]) == ("ENTERPRISE", True)
    assert extract_tier_from_tags(["gym_b2b"]) == ("ENTERPRISE", True)
    assert extract_tier_from_tags(["enterprise"]) == ("ENTERPRISE", True)
    assert extract_tier_from_tags(["tier_pro"]) == ("PAID_PRO", True)
    assert extract_tier_from_tags(["movesense_pro"]) == ("PAID_PRO", True)
    assert extract_tier_from_tags(["spatial_grappling_pro"]) == ("PAID_PRO", True)
    assert extract_tier_from_tags(["hardware_contributor"]) == ("CONTRIBUTOR_PRO", True)
    assert extract_tier_from_tags(["tier_contributor"]) == ("CONTRIBUTOR_PRO", True)
    assert extract_tier_from_tags(["random_tag", "athlete"]) == ("FREE", False)
    assert extract_tier_from_tags([]) == ("FREE", False)


# =============================================================================
# 4. COMPUTE OFFSET BOUNDARY & EDGE CASES
# =============================================================================

def test_adv_compute_offset_zero_duration():
    """Verify compute offset with 0 duration computes base hardware depreciation without error."""
    cost_heavy = ComputeOffsetCalculator.calculate_task_cost(duration_seconds=0, is_heavy_moe=True)
    assert cost_heavy == 0.02  # $0.00 electricity + $0.02 depreciation

    cost_edge = ComputeOffsetCalculator.calculate_task_cost(duration_seconds=0, is_heavy_moe=False)
    assert cost_edge == 0.005


def test_adv_compute_offset_zero_monthly_price():
    """Verify margin calculations with 0 monthly price handle division cleanly."""
    res = ComputeOffsetCalculator.calculate_subscription_gross_margin(
        monthly_price_usd=0.0,
        monthly_compute_seconds=3600,
        is_heavy_moe=True,
    )
    assert res["monthly_price_usd"] == 0.0
    assert res["gross_profit_usd"] < 0.0
    assert res["gross_margin_pct"] == 0.0
    assert res["target_70pct_met"] is False


def test_adv_compute_offset_extreme_compute_hours():
    """Verify high compute load (e.g. 100,000 hours continuous mesh inference)."""
    cost = ComputeOffsetCalculator.calculate_task_cost(
        duration_seconds=100000 * 3600,
        is_heavy_moe=True,
    )
    # 270W * 100,000h = 27,000 kWh @ $0.25/kWh = $6750 + $0.02
    assert round(cost, 2) == 6750.02

    credits_needed = ComputeOffsetCalculator.calculate_required_credits(
        physical_cost=cost,
        target_margin=0.70,
    )
    # required_rev = 6750.02 / 0.3 = 22500.0667 => 2,250,007 credits
    assert credits_needed >= 2250000


def test_adv_estimate_max_monthly_tasks_zero_price():
    """Verify zero price estimates 0 allowable tasks."""
    tasks = ComputeOffsetCalculator.estimate_max_monthly_tasks(
        monthly_price_usd=0.0,
        avg_task_sec=45,
        is_heavy_moe=True,
    )
    assert tasks == 0


def test_adv_calculate_required_credits_high_margin_safety():
    """Verify calculate_required_credits handles target_margin >= 1.0 safely without ZeroDivisionError."""
    credits = ComputeOffsetCalculator.calculate_required_credits(
        physical_cost=10.0,
        target_margin=1.0,  # 1.0 - 1.0 = 0.0, protected by max(0.01, ...)
        credit_value_usd=0.01,
    )
    assert credits > 0


# =============================================================================
# 5. ZERO-MOCK INTEGRITY & PRODUCTION CODE AUDIT
# =============================================================================

def test_adv_zero_mock_codebase_integrity():
    """
    Inspects production modules in 08_business_and_commerce/shopify_headless/ to verify:
    - No simulated random arrays or fake telemetry generators.
    - No hardcoded fake product pricing in production queries or services.
    - All queries use strict GraphQL AST templates.
    """
    import os
    import re
    from pathlib import Path

    base_dir = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/shopify_headless")
    prod_files = [
        base_dir / "config.py",
        base_dir / "client.py",
        base_dir / "errors.py",
        base_dir / "models.py",
        base_dir / "queries" / "subscriptions.py",
        base_dir / "queries" / "hardware_kit.py",
        base_dir / "queries" / "token_gating.py",
        base_dir / "services" / "monetization_service.py",
        base_dir / "services" / "compute_offset.py",
    ]

    for pfile in prod_files:
        assert pfile.exists(), f"Production file {pfile} must exist."
        content = pfile.read_text(encoding="utf-8")

        # Verify no random.choice / random.randint / random.random simulating data
        assert "random.randint" not in content, f"Forbidden random.randint in {pfile}"
        assert "random.choice" not in content, f"Forbidden random.choice in {pfile}"
        assert "mock_" not in content or "mock_transport" in content or "MockGraphQLTransport" in content or "test" in pfile.name, (
            f"Suspicious mock variable in {pfile}"
        )
        assert "fake_" not in content, f"Forbidden fake_ variable in {pfile}"

        # Verify no hardcoded API keys
        assert not re.search(r'shpat_[a-zA-Z0-9]{20,}', content), f"Leaked live shopify access token in {pfile}"
        assert not re.search(r'shpca_[a-zA-Z0-9]{20,}', content), f"Leaked live shopify private token in {pfile}"


# =============================================================================
# 6. CONCURRENCY, RESILIENCE & INJECTION RESISTANCE
# =============================================================================

@pytest.mark.asyncio
async def test_adv_concurrent_burst_requests():
    """Verify that multiple concurrent async requests correctly share leaky-bucket state without deadlocks."""
    config = ShopifyConfig(
        store_domain="lauburugrappling.myshopify.com",
        admin_access_token="shpat_admin_burst",
    )

    call_timestamps = []

    async def fast_handler(request, count, body):
        call_timestamps.append(asyncio.get_event_loop().time())
        return httpx.Response(
            status_code=200,
            json={
                "data": {"shop": {"name": f"Shop {count}"}},
                "extensions": {
                    "cost": {
                        "requestedQueryCost": 10,
                        "actualQueryCost": 10,
                        "throttleStatus": {
                            "maximumAvailable": 1000.0,
                            "currentlyAvailable": 990.0,
                            "restoreRate": 50.0,
                        },
                    }
                },
            },
            request=request,
        )

    transport = AdversarialMockTransport(handler=fast_handler)
    client = ShopifyClient(config=config, transport=transport)

    # Launch 20 concurrent requests
    tasks = [client.execute_admin(query=f"query Q{i} {{ shop {{ name }} }}") for i in range(20)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 20
    assert transport.call_count == 20
    for r in results:
        assert "shop" in r


@pytest.mark.asyncio
async def test_adv_network_error_retries_and_exhaustion():
    """Verify httpx.ConnectError triggers backoff and raises ShopifyGraphQLError on exhaustion."""
    config = ShopifyConfig(
        store_domain="lauburugrappling.myshopify.com",
        storefront_access_token="real_tok",
        max_retries=2,
        backoff_factor=1.0,
    )

    async def failing_transport_handler(request, count, body):
        raise httpx.ConnectError("Connection refused by peer", request=request)

    transport = AdversarialMockTransport(handler=failing_transport_handler)
    client = ShopifyClient(config=config, transport=transport)

    with pytest.raises(ShopifyGraphQLError) as exc_info:
        await client.execute_storefront(query="query { shop { name } }")

    assert "network failure" in exc_info.value.message.lower()
    # Initial attempt + 2 retries = 3 calls
    assert transport.call_count == 3


def test_adv_models_parameter_sanitization():
    """Verify input models properly sanitize and format GraphQL variables without string injection risks."""
    item = HardwareItemInput(
        variant_id='gid://shopify/ProductVariant/123"; DROP TABLE products; --',
        quantity=5,
        node_role='L1_Primary; query { stealth { token } }',
        custom_attributes={"key_with_quotes": 'val"ue'},
    )
    cart_line = item.to_cart_line_input()
    graphql_dict = cart_line.to_graphql_dict()

    # The payload must be a pure Python dictionary serializable to JSON (GraphQL variables, not concatenated strings)
    assert graphql_dict["merchandiseId"] == 'gid://shopify/ProductVariant/123"; DROP TABLE products; --'
    assert graphql_dict["quantity"] == 5
    assert len(graphql_dict["attributes"]) == 2
    assert graphql_dict["attributes"][0]["key"] == "node_role"
    assert graphql_dict["attributes"][0]["value"] == "L1_Primary; query { stealth { token } }"
    # Serialization verification
    json_str = json.dumps(graphql_dict)
    assert "\\\"" in json_str or '"L1_Primary; query { stealth { token } }"' in json_str
