"""
Unit tests for Shopify Storefront Service in Port 4000 Hub.
Tests customer token verification, membership tier extraction, and dev token fallback.
"""

import pytest
from ..services.shopify_service import ShopifyService


@pytest.fixture
def shopify_service():
    return ShopifyService(
        store_domain="test-store.myshopify.com",
        storefront_token="pub_storefront_mock_token"
    )


@pytest.mark.asyncio
async def test_dev_token_verification(shopify_service):
    """Verify that dev tokens resolve to valid PAID_PRO profiles."""
    valid, profile = await shopify_service.verify_customer_access_token("tok_dev_123456")
    assert valid is True
    assert profile["valid"] is True
    assert profile["tier"] == "PAID_PRO"
    assert profile["is_paid_subscriber"] is True
    assert "tier_pro" in profile["tags"]

    # Shpat dev token
    valid_shpat, prof_shpat = await shopify_service.verify_customer_access_token("shpat_dev_abcdef")
    assert valid_shpat is True
    assert prof_shpat["is_paid_subscriber"] is True


@pytest.mark.asyncio
async def test_dev_credentials_authentication(shopify_service):
    """Verify that dev credentials resolve to valid customer access token and profile."""
    valid, result = await shopify_service.authenticate_customer_credentials("dev@lauburu.ai", "AnyPassword123")
    assert valid is True
    assert "token" in result
    assert result["profile"]["tier"] == "PAID_PRO"
    assert result["profile"]["is_paid_subscriber"] is True


def test_membership_tier_extraction(shopify_service):
    """Verify correct tag parsing into membership tiers."""
    tier_ent, paid_ent = shopify_service._extract_tier_from_tags(["tier_enterprise", "other_tag"])
    assert tier_ent == "ENTERPRISE"
    assert paid_ent is True

    tier_pro, paid_pro = shopify_service._extract_tier_from_tags(["movesense_pro"])
    assert tier_pro == "PAID_PRO"
    assert paid_pro is True

    tier_contrib, paid_contrib = shopify_service._extract_tier_from_tags(["tier_contributor"])
    assert tier_contrib == "CONTRIBUTOR_PRO"
    assert paid_contrib is True

    tier_free, paid_free = shopify_service._extract_tier_from_tags(["regular_customer", "newsletter"])
    assert tier_free == "FREE"
    assert paid_free is False


@pytest.mark.asyncio
async def test_empty_token_rejection(shopify_service):
    """Verify that empty tokens are rejected."""
    valid, result = await shopify_service.verify_customer_access_token("")
    assert valid is False
    assert result["valid"] is False
