"""
Unit tests for Use Case 3: Token-Gated Authentication (Spatial Grappling 3D / Port 4000 UI Gatekeeper).
"""

import httpx
import pytest

from shopify_headless.client import ShopifyClient
from shopify_headless.errors import ShopifyAuthError, ShopifyUserError
from shopify_headless.queries.token_gating import (
    create_customer_access_token,
    delete_customer_access_token,
    extract_tier_from_tags,
    get_customer_account_subscriptions,
    get_customer_gated_profile,
    get_dev_fallback_profile,
    renew_customer_access_token,
)
from .conftest import MockGraphQLTransport


def test_extract_tier_from_tags():
    tier, is_paid = extract_tier_from_tags(["tier_pro", "athlete"])
    assert tier == "PAID_PRO"
    assert is_paid is True

    tier, is_paid = extract_tier_from_tags(["gym_b2b", "owner"])
    assert tier == "ENTERPRISE"
    assert is_paid is True

    tier, is_paid = extract_tier_from_tags(["hardware_contributor"])
    assert tier == "CONTRIBUTOR_PRO"
    assert is_paid is True

    tier, is_paid = extract_tier_from_tags(["newsletter_subscriber"])
    assert tier == "FREE"
    assert is_paid is False

    # Verify graceful handling of None, empty, and non-string elements
    tier, is_paid = extract_tier_from_tags(None)
    assert tier == "FREE"
    assert is_paid is False

    tier, is_paid = extract_tier_from_tags([])
    assert tier == "FREE"
    assert is_paid is False

    tier, is_paid = extract_tier_from_tags([None, "tier_pro", 123, None])
    assert tier == "PAID_PRO"
    assert is_paid is True


def test_dev_fallback_profile():
    profile = get_dev_fallback_profile(email="dev_athlete@lauburu.ai")
    assert profile.email == "dev_athlete@lauburu.ai"
    assert profile.tier == "PAID_PRO"
    assert profile.is_paid_subscriber is True
    assert "spatial_grappling_pro" in profile.tags


@pytest.mark.asyncio
async def test_create_customer_access_token_dev_bypass(mock_config):
    client = ShopifyClient(config=mock_config)
    token = await create_customer_access_token(client, email="dev@lauburu.ai", password="any_password")
    assert token.access_token.startswith("tok_dev_")
    assert token.expires_at == "2030-01-01T00:00:00Z"


@pytest.mark.asyncio
async def test_create_customer_access_token_live_success(mock_config):
    auth_resp = {
        "customerAccessTokenCreate": {
            "customerAccessToken": {
                "accessToken": "shpat_live_token_778899",
                "expiresAt": "2026-10-01T00:00:00Z",
            },
            "customerUserErrors": [],
        }
    }
    transport = MockGraphQLTransport(responses=[httpx.Response(200, json={"data": auth_resp})])
    client = ShopifyClient(config=mock_config, transport=transport)

    token = await create_customer_access_token(client, email="customer@example.com", password="SecurePassword123!")
    assert token.access_token == "shpat_live_token_778899"
    assert token.expires_at == "2026-10-01T00:00:00Z"


@pytest.mark.asyncio
async def test_create_customer_access_token_failure_raises_user_error(mock_config):
    auth_err_resp = {
        "customerAccessTokenCreate": {
            "customerAccessToken": None,
            "customerUserErrors": [
                {
                    "code": "UNIDENTIFIED_CUSTOMER",
                    "field": ["input", "password"],
                    "message": "Unidentified customer",
                }
            ],
        }
    }
    transport = MockGraphQLTransport(responses=[httpx.Response(200, json={"data": auth_err_resp})])
    client = ShopifyClient(config=mock_config, transport=transport)

    with pytest.raises(ShopifyUserError) as exc_info:
        await create_customer_access_token(client, email="wrong@example.com", password="BadPassword")
    assert "Unidentified customer" in exc_info.value.message


@pytest.mark.asyncio
async def test_renew_and_delete_customer_access_token(mock_config):
    renew_resp = {
        "customerAccessTokenRenew": {
            "customerAccessToken": {
                "accessToken": "shpat_renewed_token_112233",
                "expiresAt": "2026-12-01T00:00:00Z",
            },
            "userErrors": [],
        }
    }
    delete_resp = {
        "customerAccessTokenDelete": {
            "deletedAccessToken": "shpat_renewed_token_112233",
            "deletedCustomerAccessTokenId": "gid://shopify/CustomerAccessToken/123",
            "userErrors": [],
        }
    }
    transport = MockGraphQLTransport(responses=[
        httpx.Response(200, json={"data": renew_resp}),
        httpx.Response(200, json={"data": delete_resp}),
    ])
    client = ShopifyClient(config=mock_config, transport=transport)

    renewed = await renew_customer_access_token(client, customer_access_token="shpat_old_token")
    assert renewed.access_token == "shpat_renewed_token_112233"

    deleted = await delete_customer_access_token(client, customer_access_token="shpat_renewed_token_112233")
    assert deleted is True


@pytest.mark.asyncio
async def test_get_customer_gated_profile_success(mock_config, mock_customer_gated_profile_payload):
    transport = MockGraphQLTransport(responses=[httpx.Response(200, json={"data": mock_customer_gated_profile_payload})])
    client = ShopifyClient(config=mock_config, transport=transport)

    profile = await get_customer_gated_profile(client, customer_access_token="shpat_valid_token_xyz")
    assert profile is not None
    assert profile.id == "gid://shopify/Customer/9901"
    assert profile.email == "aaron@lauburu.ai"
    assert profile.tier == "PAID_PRO"
    assert profile.is_paid_subscriber is True
    assert len(profile.orders) == 1
    assert profile.orders[0]["orderNumber"] == 1001


@pytest.mark.asyncio
async def test_get_customer_gated_profile_dev_token(mock_config):
    client = ShopifyClient(config=mock_config)
    profile = await get_customer_gated_profile(client, customer_access_token="tok_dev_456789")
    assert profile is not None
    assert profile.tier == "PAID_PRO"
    assert profile.is_paid_subscriber is True


@pytest.mark.asyncio
async def test_get_customer_gated_profile_handles_none_tags(mock_config):
    resp = {
        "customer": {
            "id": "gid://shopify/Customer/9902",
            "email": "notags@lauburu.ai",
            "firstName": "No",
            "lastName": "Tags",
            "phone": None,
            "tags": None,
            "orders": {"edges": []},
        }
    }
    transport = MockGraphQLTransport(responses=[httpx.Response(200, json={"data": resp})])
    client = ShopifyClient(config=mock_config, transport=transport)

    profile = await get_customer_gated_profile(client, customer_access_token="shpat_valid_token_none_tags")
    assert profile is not None
    assert profile.tier == "FREE"
    assert profile.is_paid_subscriber is False
    assert profile.tags == []


@pytest.mark.asyncio
async def test_get_customer_account_subscriptions(mock_config):
    ca_resp = {
        "customer": {
            "id": "gid://shopify/Customer/9901",
            "emailAddress": {"emailAddress": "athlete@lauburu.ai"},
            "subscriptionContracts": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/SubscriptionContract/5501",
                            "status": "ACTIVE",
                            "lines": {
                                "edges": [
                                    {
                                        "node": {
                                            "id": "gid://shopify/SubscriptionLine/4401",
                                            "name": "OpenClaw AI Pro Monthly",
                                            "quantity": 1,
                                            "currentPrice": {"amount": "29.00", "currencyCode": "USD"},
                                        }
                                    }
                                ]
                            },
                        }
                    }
                ]
            },
        }
    }
    transport = MockGraphQLTransport(responses=[httpx.Response(200, json={"data": ca_resp})])
    client = ShopifyClient(config=mock_config, transport=transport)

    subs = await get_customer_account_subscriptions(client, customer_access_token="cust_account_token_abc")
    assert len(subs) == 1
    assert subs[0]["id"] == "gid://shopify/SubscriptionContract/5501"
    assert subs[0]["status"] == "ACTIVE"
