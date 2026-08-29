"""
Shopify Storefront Configuration.
=================================
Subsystem: 01_apps/user_facing_and_scaling/shopify_storefront/core/config.py
"""

from dataclasses import dataclass
import os

@dataclass
class ShopifyConfig:
    shop_domain: str = os.getenv("SHOPIFY_SHOP_DOMAIN", "lauburu-biometrics.myshopify.com")
    storefront_token: str = os.getenv("SHOPIFY_STOREFRONT_TOKEN", "shpat_lauburu_storefront_live_2026")
    api_version: str = "2026-01"
    endpoint_url: str = f"https://{os.getenv('SHOPIFY_SHOP_DOMAIN', 'lauburu-biometrics.myshopify.com')}/api/2026-01/graphql.json"
