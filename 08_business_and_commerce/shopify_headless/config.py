"""
Configuration module for Shopify Headless Monetization Engine.
Loads environment variables with zero hardcoded credentials and sensible defaults.
"""

import os
from typing import Optional
from pydantic import BaseModel, Field


class ShopifyConfig(BaseModel):
    """
    Shopify Headless configuration container.
    Reads values from environment variables or custom overrides.
    """

    store_domain: str = Field(
        default_factory=lambda: os.environ.get("SHOPIFY_STORE_DOMAIN", "lauburugrappling.myshopify.com")
    )
    storefront_access_token: str = Field(
        default_factory=lambda: os.environ.get(
            "SHOPIFY_STOREFRONT_ACCESS_TOKEN",
            os.environ.get("SHOPIFY_STOREFRONT_TOKEN", "")
        )
    )
    storefront_private_token: str = Field(
        default_factory=lambda: os.environ.get("SHOPIFY_STOREFRONT_PRIVATE_TOKEN", "")
    )
    admin_access_token: str = Field(
        default_factory=lambda: os.environ.get("SHOPIFY_ADMIN_ACCESS_TOKEN", "")
    )
    api_version: str = Field(
        default_factory=lambda: os.environ.get("SHOPIFY_API_VERSION", "2026-01")
    )
    timeout_seconds: float = Field(
        default_factory=lambda: float(os.environ.get("SHOPIFY_TIMEOUT_SECONDS", "8.0"))
    )
    max_retries: int = Field(
        default_factory=lambda: int(os.environ.get("SHOPIFY_MAX_RETRIES", "3"))
    )
    backoff_factor: float = Field(
        default_factory=lambda: float(os.environ.get("SHOPIFY_BACKOFF_FACTOR", "1.5"))
    )

    @property
    def storefront_endpoint(self) -> str:
        """Construct full Storefront GraphQL endpoint URL."""
        return f"https://{self.store_domain}/api/{self.api_version}/graphql.json"

    @property
    def admin_endpoint(self) -> str:
        """Construct full Admin GraphQL endpoint URL."""
        return f"https://{self.store_domain}/admin/api/{self.api_version}/graphql.json"

    @property
    def customer_account_endpoint(self) -> str:
        """Construct full Customer Account GraphQL endpoint URL."""
        return f"https://{self.store_domain}/account/customer/api/{self.api_version}/graphql"


def get_shopify_config(**kwargs) -> ShopifyConfig:
    """Factory helper to obtain a ShopifyConfig instance with optional overrides."""
    return ShopifyConfig(**kwargs)
