"""
Unit tests for ShopifyConfig configuration loader.
"""

import os
from unittest import mock
import pytest

from shopify_headless.config import ShopifyConfig, get_shopify_config


def test_default_config():
    config = ShopifyConfig()
    assert config.store_domain == "lauburugrappling.myshopify.com"
    assert config.api_version == "2026-01"
    assert config.timeout_seconds == 8.0
    assert config.max_retries == 3
    assert config.backoff_factor == 1.5
    assert "https://lauburugrappling.myshopify.com/api/2026-01/graphql.json" == config.storefront_endpoint
    assert "https://lauburugrappling.myshopify.com/admin/api/2026-01/graphql.json" == config.admin_endpoint
    assert "https://lauburugrappling.myshopify.com/account/customer/api/2026-01/graphql" == config.customer_account_endpoint


def test_custom_config_overrides():
    config = get_shopify_config(
        store_domain="custom-mesh-store.myshopify.com",
        storefront_access_token="shpat_custom_storefront_123",
        storefront_private_token="shppriv_custom_456",
        admin_access_token="shpat_custom_admin_789",
        api_version="2025-10",
        timeout_seconds=12.5,
        max_retries=5,
        backoff_factor=2.0,
    )
    assert config.store_domain == "custom-mesh-store.myshopify.com"
    assert config.storefront_access_token == "shpat_custom_storefront_123"
    assert config.storefront_private_token == "shppriv_custom_456"
    assert config.admin_access_token == "shpat_custom_admin_789"
    assert config.api_version == "2025-10"
    assert config.timeout_seconds == 12.5
    assert config.max_retries == 5
    assert config.backoff_factor == 2.0
    assert config.storefront_endpoint == "https://custom-mesh-store.myshopify.com/api/2025-10/graphql.json"
    assert config.admin_endpoint == "https://custom-mesh-store.myshopify.com/admin/api/2025-10/graphql.json"


def test_config_from_env_vars():
    env_patch = {
        "SHOPIFY_STORE_DOMAIN": "env-mesh.myshopify.com",
        "SHOPIFY_STOREFRONT_ACCESS_TOKEN": "shpat_env_token_abc",
        "SHOPIFY_ADMIN_ACCESS_TOKEN": "shpat_env_admin_xyz",
        "SHOPIFY_API_VERSION": "2026-04",
        "SHOPIFY_TIMEOUT_SECONDS": "10.0",
        "SHOPIFY_MAX_RETRIES": "4",
        "SHOPIFY_BACKOFF_FACTOR": "1.2",
    }
    with mock.patch.dict(os.environ, env_patch, clear=True):
        config = get_shopify_config()
        assert config.store_domain == "env-mesh.myshopify.com"
        assert config.storefront_access_token == "shpat_env_token_abc"
        assert config.admin_access_token == "shpat_env_admin_xyz"
        assert config.api_version == "2026-04"
        assert config.timeout_seconds == 10.0
        assert config.max_retries == 4
        assert config.backoff_factor == 1.2
