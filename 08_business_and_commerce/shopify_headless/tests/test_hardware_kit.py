"""
Unit tests for Use Case 2: Hardware Kit Cart (Lauburu Mesh Nodes: GL.iNet + Movesense Bundles).
"""

import httpx
import pytest

from shopify_headless.client import ShopifyClient
from shopify_headless.errors import ShopifyUserError
from shopify_headless.models import BuyerIdentityInput, HardwareItemInput
from shopify_headless.queries.hardware_kit import (
    add_hardware_kit_lines,
    create_hardware_kit_cart,
    update_cart_buyer_identity,
    update_cart_discount_codes,
)
from .conftest import MockGraphQLTransport


@pytest.mark.asyncio
async def test_create_hardware_kit_cart_success(mock_config, mock_cart_payload):
    transport = MockGraphQLTransport(responses=[httpx.Response(200, json={"data": {"cartCreate": {"cart": mock_cart_payload, "userErrors": []}}})])
    client = ShopifyClient(config=mock_config, transport=transport)

    items = [
        HardwareItemInput(
            variant_id="gid://shopify/ProductVariant/3001",
            quantity=1,
            node_role="Layer_3_Gateway",
        ),
        HardwareItemInput(
            variant_id="gid://shopify/ProductVariant/3002",
            quantity=1,
            sensor_type="512Hz_ECG",
        ),
    ]
    buyer = BuyerIdentityInput(email="athlete@lauburu.ai", phone="+61400111222", country_code="AU")

    cart = await create_hardware_kit_cart(
        client=client,
        items=items,
        buyer_identity=buyer,
        discount_codes=["HARDWARE_PROMO_2026"],
    )

    assert cart.id == "gid://shopify/Cart/c1-987654321?key=abc123secret"
    assert cart.total_quantity == 2
    assert len(cart.lines) == 2
    assert cart.lines[0].merchandise.title == "GL.iNet MT3600BE Router Node"
    assert cart.lines[0].attributes[0].key == "node_role"
    assert cart.lines[0].attributes[0].value == "Layer_3_Gateway"
    assert cart.lines[1].merchandise.title == "Movesense Medical ECG Sensor"
    assert cart.lines[1].attributes[0].key == "sensor_type"
    assert cart.lines[1].attributes[0].value == "512Hz_ECG"
    assert cart.cost.total_amount.amount == "348.00"
    assert cart.buyer_identity.country_code == "AU"
    assert len(cart.discount_codes) == 1
    assert cart.discount_codes[0].code == "HARDWARE_PROMO_2026"


@pytest.mark.asyncio
async def test_add_hardware_kit_lines_success(mock_config, mock_cart_payload):
    transport = MockGraphQLTransport(responses=[httpx.Response(200, json={"data": {"cartLinesAdd": {"cart": mock_cart_payload, "userErrors": []}}})])
    client = ShopifyClient(config=mock_config, transport=transport)

    items = [
        HardwareItemInput(
            variant_id="gid://shopify/ProductVariant/3003",
            quantity=1,
            custom_attributes={"accessory": "Chest_Strap_L"},
        )
    ]
    cart = await add_hardware_kit_lines(client, cart_id="gid://shopify/Cart/c1-987654321?key=abc123secret", items=items)
    assert cart.id == "gid://shopify/Cart/c1-987654321?key=abc123secret"
    assert len(cart.lines) == 2


@pytest.mark.asyncio
async def test_update_cart_buyer_identity_success(mock_config):
    buyer_resp = {
        "cartBuyerIdentityUpdate": {
            "cart": {
                "id": "gid://shopify/Cart/c1-987654321?key=abc123secret",
                "checkoutUrl": "https://lauburugrappling.myshopify.com/cart/c/c1",
                "totalQuantity": 1,
                "lines": {"edges": []},
                "cost": {
                    "subtotalAmount": {"amount": "149.00", "currencyCode": "USD"},
                    "totalAmount": {"amount": "149.00", "currencyCode": "USD"},
                },
                "buyerIdentity": {"email": "updated@lauburu.ai", "countryCode": "US"},
                "discountCodes": [],
            },
            "userErrors": [],
        }
    }
    transport = MockGraphQLTransport(responses=[httpx.Response(200, json={"data": buyer_resp})])
    client = ShopifyClient(config=mock_config, transport=transport)

    cart = await update_cart_buyer_identity(
        client=client,
        cart_id="gid://shopify/Cart/c1-987654321?key=abc123secret",
        buyer_identity=BuyerIdentityInput(email="updated@lauburu.ai", country_code="US"),
    )
    assert cart.buyer_identity.email == "updated@lauburu.ai"
    assert cart.buyer_identity.country_code == "US"


@pytest.mark.asyncio
async def test_update_cart_discount_codes_success(mock_config):
    discount_resp = {
        "cartDiscountCodesUpdate": {
            "cart": {
                "id": "gid://shopify/Cart/c1-987654321?key=abc123secret",
                "checkoutUrl": "https://lauburugrappling.myshopify.com/cart/c/c1",
                "totalQuantity": 1,
                "lines": {"edges": []},
                "cost": {
                    "subtotalAmount": {"amount": "149.00", "currencyCode": "USD"},
                    "totalAmount": {"amount": "0.00", "currencyCode": "USD"},
                },
                "discountCodes": [{"code": "FREE_HARDWARE_BUNDLE", "applicable": True}],
            },
            "userErrors": [],
        }
    }
    transport = MockGraphQLTransport(responses=[httpx.Response(200, json={"data": discount_resp})])
    client = ShopifyClient(config=mock_config, transport=transport)

    cart = await update_cart_discount_codes(
        client=client,
        cart_id="gid://shopify/Cart/c1-987654321?key=abc123secret",
        discount_codes=["FREE_HARDWARE_BUNDLE"],
    )
    assert len(cart.discount_codes) == 1
    assert cart.discount_codes[0].code == "FREE_HARDWARE_BUNDLE"
    assert cart.cost.total_amount.amount == "0.00"
