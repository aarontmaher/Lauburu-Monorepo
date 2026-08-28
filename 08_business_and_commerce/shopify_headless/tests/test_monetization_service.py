"""
Unit tests for ShopifyMonetizationService high-level domain workflows across all 3 use cases.
"""

import httpx
import pytest

from shopify_headless.client import ShopifyClient
from shopify_headless.models import BuyerIdentityInput, HardwareItemInput
from shopify_headless.services.monetization_service import ShopifyMonetizationService
from .conftest import MockGraphQLTransport


@pytest.mark.asyncio
async def test_create_subscription_checkout_flow(mock_config, mock_product_with_selling_plans_payload, mock_cart_payload):
    transport = MockGraphQLTransport(responses=[
        httpx.Response(200, json={"data": mock_product_with_selling_plans_payload}),
        httpx.Response(200, json={"data": {"cartCreate": {"cart": mock_cart_payload, "userErrors": []}}}),
    ])
    client = ShopifyClient(config=mock_config, transport=transport)
    service = ShopifyMonetizationService(client=client)

    cart = await service.create_subscription_checkout(
        product_handle="openclaw-ai-pro",
        selling_plan_id="gid://shopify/SellingPlan/5001",
        quantity=1,
    )
    assert cart.id == "gid://shopify/Cart/c1-987654321?key=abc123secret"
    assert cart.checkout_url == "https://lauburugrappling.myshopify.com/cart/c/c1-987654321"
    assert len(transport.requests) == 2


@pytest.mark.asyncio
async def test_hardware_bundle_cart_flow(mock_config, mock_cart_payload):
    transport = MockGraphQLTransport(responses=[
        httpx.Response(200, json={"data": {"cartCreate": {"cart": mock_cart_payload, "userErrors": []}}}),
        httpx.Response(200, json={"data": {"cartLinesAdd": {"cart": mock_cart_payload, "userErrors": []}}}),
    ])
    client = ShopifyClient(config=mock_config, transport=transport)
    service = ShopifyMonetizationService(client=client)

    items = [
        HardwareItemInput(
            variant_id="gid://shopify/ProductVariant/3001",
            quantity=1,
            node_role="Layer_3_Gateway",
        )
    ]
    cart = await service.create_hardware_bundle_cart(items=items)
    assert cart.total_quantity == 2

    cart_updated = await service.add_hardware_items_to_cart(
        cart_id=cart.id,
        items=[HardwareItemInput(variant_id="gid://shopify/ProductVariant/3003", quantity=1)],
    )
    assert cart_updated.id == cart.id


@pytest.mark.asyncio
async def test_verify_token_gated_access_granted(mock_config, mock_customer_gated_profile_payload):
    transport = MockGraphQLTransport(responses=[
        httpx.Response(200, json={"data": mock_customer_gated_profile_payload}),
    ])
    client = ShopifyClient(config=mock_config, transport=transport)
    service = ShopifyMonetizationService(client=client)

    grant = await service.verify_token_gated_access(
        customer_token="shpat_valid_subscriber_token",
        required_tier="tier_pro",
    )
    assert grant.allowed is True
    assert grant.tier == "PAID_PRO"
    assert grant.is_paid_subscriber is True
    assert "3d_spatial_grappling" in grant.granted_features
    assert "port_4000_hub" in grant.granted_features


@pytest.mark.asyncio
async def test_verify_token_gated_access_denied_free_user(mock_config):
    free_customer_payload = {
        "customer": {
            "id": "gid://shopify/Customer/9902",
            "email": "free_user@example.com",
            "tags": ["free_newsletter"],
            "orders": {"edges": []},
        }
    }
    transport = MockGraphQLTransport(responses=[
        httpx.Response(200, json={"data": free_customer_payload}),
    ])
    client = ShopifyClient(config=mock_config, transport=transport)
    service = ShopifyMonetizationService(client=client)

    grant = await service.verify_token_gated_access(
        customer_token="shpat_free_token",
        required_tier="tier_pro",
    )
    assert grant.allowed is False
    assert grant.tier == "FREE"
    assert grant.reason == "INSUFFICIENT_MEMBERSHIP_TIER"
    assert grant.checkout_upgrade_url is not None


@pytest.mark.asyncio
async def test_verify_token_gated_access_dev_token(mock_config):
    client = ShopifyClient(config=mock_config)
    service = ShopifyMonetizationService(client=client)

    grant = await service.verify_token_gated_access(
        customer_token="tok_dev_aaron_99",
        required_tier="tier_pro",
    )
    assert grant.allowed is True
    assert grant.is_paid_subscriber is True
    assert grant.tier == "PAID_PRO"


@pytest.mark.asyncio
async def test_verify_token_gated_access_empty_token(mock_config):
    client = ShopifyClient(config=mock_config)
    service = ShopifyMonetizationService(client=client)

    grant = await service.verify_token_gated_access(
        customer_token="",
        required_tier="tier_pro",
    )
    assert grant.allowed is False
    assert grant.reason == "MISSING_CUSTOMER_TOKEN"


def test_calculate_plan_profitability(mock_config):
    client = ShopifyClient(config=mock_config)
    service = ShopifyMonetizationService(client=client)

    analysis = service.calculate_plan_profitability(
        monthly_price_usd=29.00,
        monthly_compute_hours=10.0,
        is_heavy_moe=True,
    )
    assert analysis["target_70pct_met"] is True
    assert analysis["gross_margin_pct"] > 70.0
