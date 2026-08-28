"""
Unit tests for Use Case 1: Recurring Subscriptions (OpenClaw AI API & Cloud Access).
"""

import httpx
import pytest

from shopify_headless.client import ShopifyClient
from shopify_headless.errors import ShopifyUserError
from shopify_headless.models import BuyerIdentityInput
from shopify_headless.queries.subscriptions import (
    create_subscription_cart,
    get_customer_subscription_contracts,
    get_product_with_selling_plans,
)
from .conftest import MockGraphQLTransport


@pytest.mark.asyncio
async def test_get_product_with_selling_plans_success(mock_config, mock_product_with_selling_plans_payload):
    transport = MockGraphQLTransport(responses=[httpx.Response(200, json={"data": mock_product_with_selling_plans_payload})])
    client = ShopifyClient(config=mock_config, transport=transport)

    product = await get_product_with_selling_plans(client, handle="openclaw-ai-pro")
    assert product is not None
    assert product.id == "gid://shopify/Product/1001"
    assert product.title == "OpenClaw AI Pro Compute Subscription"
    assert product.requires_selling_plan is True
    assert len(product.selling_plan_groups) == 1

    group = product.selling_plan_groups[0]
    assert group.name == "OpenClaw Subscription Plans"
    assert len(group.selling_plans) == 2

    monthly_plan = group.selling_plans[0]
    assert monthly_plan.id == "gid://shopify/SellingPlan/5001"
    assert monthly_plan.name == "Monthly Pro AI Access"
    assert monthly_plan.recurring_deliveries is True
    assert len(monthly_plan.price_adjustments) == 1
    assert monthly_plan.price_adjustments[0].adjustment_percentage == 10.0

    assert len(product.variants) == 1
    assert product.variants[0].id == "gid://shopify/ProductVariant/2001"
    assert product.variants[0].price.amount == "29.00"


@pytest.mark.asyncio
async def test_create_subscription_cart_success(mock_config):
    cart_resp_payload = {
        "cartCreate": {
            "cart": {
                "id": "gid://shopify/Cart/c_sub_12345?key=sub_secret",
                "checkoutUrl": "https://lauburugrappling.myshopify.com/cart/c/c_sub_12345",
                "totalQuantity": 1,
                "lines": {
                    "edges": [
                        {
                            "node": {
                                "id": "gid://shopify/CartLine/sub_l1",
                                "quantity": 1,
                                "merchandise": {
                                    "id": "gid://shopify/ProductVariant/2001",
                                    "title": "Pro Tier - Monthly",
                                    "sku": "OPENCLAW-SUB-M",
                                    "price": {"amount": "29.00", "currencyCode": "USD"},
                                    "product": {"title": "OpenClaw AI Pro", "handle": "openclaw-ai-pro"},
                                },
                                "sellingPlanAllocation": {
                                    "sellingPlan": {
                                        "id": "gid://shopify/SellingPlan/5001",
                                        "name": "Monthly Pro AI Access",
                                        "description": "Billed monthly",
                                    },
                                    "priceAdjustments": [
                                        {"price": {"amount": "26.10", "currencyCode": "USD"}}
                                    ],
                                },
                            }
                        }
                    ]
                },
                "cost": {
                    "subtotalAmount": {"amount": "26.10", "currencyCode": "USD"},
                    "totalAmount": {"amount": "26.10", "currencyCode": "USD"},
                    "checkoutChargeAmount": {"amount": "26.10", "currencyCode": "USD"},
                },
                "buyerIdentity": {"email": "subscriber@lauburu.ai", "countryCode": "US"},
                "discountCodes": [],
            },
            "userErrors": [],
        }
    }
    transport = MockGraphQLTransport(responses=[httpx.Response(200, json={"data": cart_resp_payload})])
    client = ShopifyClient(config=mock_config, transport=transport)

    cart = await create_subscription_cart(
        client=client,
        variant_id="gid://shopify/ProductVariant/2001",
        selling_plan_id="gid://shopify/SellingPlan/5001",
        quantity=1,
        buyer_identity=BuyerIdentityInput(email="subscriber@lauburu.ai", country_code="US"),
    )

    assert cart.id == "gid://shopify/Cart/c_sub_12345?key=sub_secret"
    assert cart.checkout_url == "https://lauburugrappling.myshopify.com/cart/c/c_sub_12345"
    assert len(cart.lines) == 1
    line = cart.lines[0]
    assert line.merchandise.id == "gid://shopify/ProductVariant/2001"
    assert line.selling_plan is not None
    assert line.selling_plan.id == "gid://shopify/SellingPlan/5001"
    assert cart.cost.total_amount.amount == "26.10"


@pytest.mark.asyncio
async def test_create_subscription_cart_user_error(mock_config):
    err_payload = {
        "cartCreate": {
            "cart": None,
            "userErrors": [
                {
                    "field": ["input", "lines", "0", "sellingPlanId"],
                    "message": "Selling plan does not exist or is inactive",
                    "code": "INVALID",
                }
            ],
        }
    }
    transport = MockGraphQLTransport(responses=[httpx.Response(200, json={"data": err_payload})])
    client = ShopifyClient(config=mock_config, transport=transport)

    with pytest.raises(ShopifyUserError) as exc_info:
        await create_subscription_cart(
            client=client,
            variant_id="gid://shopify/ProductVariant/2001",
            selling_plan_id="gid://shopify/SellingPlan/invalid",
        )
    assert "Selling plan does not exist" in exc_info.value.message


@pytest.mark.asyncio
async def test_get_customer_subscription_contracts_success(mock_config, mock_admin_subscription_contracts_payload):
    transport = MockGraphQLTransport(responses=[httpx.Response(200, json={"data": mock_admin_subscription_contracts_payload})])
    client = ShopifyClient(config=mock_config, transport=transport)

    contracts = await get_customer_subscription_contracts(client, first=5, query="customer_id:9901")
    assert len(contracts) == 1
    c = contracts[0]
    assert c.id == "gid://shopify/SubscriptionContract/8801"
    assert c.status == "ACTIVE"
    assert c.customer_email == "aaron@lauburu.ai"
    assert len(c.lines) == 1
    assert c.lines[0].title == "OpenClaw AI Pro Compute"
    assert c.lines[0].current_price.amount == "29.00"
