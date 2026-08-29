"""
Shopify Storefront Data Models.
===============================
Subsystem: 01_apps/user_facing_and_scaling/shopify_storefront/core/models.py
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class MembershipTier:
    tier_id: str
    name: str
    price_usd_month: float
    features: List[str]
    shopify_variant_id: str
    is_popular: bool = False

@dataclass
class HardwareBundle:
    bundle_id: str
    name: str
    price_usd: float
    sensor_model: str
    strap_type: str  # "Bicep" or "Chest"
    sample_rate_hz: int
    shopify_variant_id: str
    in_stock: bool = True

@dataclass
class CartLine:
    variant_id: str
    quantity: int
    title: str
    price_usd: float

@dataclass
class CheckoutSession:
    cart_id: str
    checkout_url: str
    total_amount_usd: float
    lines: List[CartLine] = field(default_factory=list)
    created_at_utc: str = ""
