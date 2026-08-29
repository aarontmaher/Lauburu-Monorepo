"""
Membership Tiers & Hardware Bundles Catalog.
============================================
Subsystem: 01_apps/user_facing_and_scaling/shopify_storefront/presentation/pricing.py
"""

from typing import List
from ..core.models import MembershipTier, HardwareBundle

MEMBERSHIP_TIERS: List[MembershipTier] = [
    MembershipTier(
        tier_id="athlete_tier",
        name="Athlete Membership",
        price_usd_month=9.00,
        features=[
            "512Hz ECG & Zone 2 Coaching",
            "PTT Continuous Blood Pressure",
            "Overnight Sleep Score & HRV"
        ],
        shopify_variant_id="gid://shopify/ProductVariant/440912345001",
        is_popular=False
    ),
    MembershipTier(
        tier_id="pro_tier",
        name="Pro Athlete & Coach",
        price_usd_month=29.00,
        features=[
            "Everything in Athlete",
            "3,044 OPML Spatial Grappling 3D",
            "Combat Arena Multi-Mode Access",
            "Hermes 3 / LuCI Duelist Engine"
        ],
        shopify_variant_id="gid://shopify/ProductVariant/440912345002",
        is_popular=True
    ),
    MembershipTier(
        tier_id="gym_tier",
        name="Gym & Team License",
        price_usd_month=99.00,
        features=[
            "Unlimited Athletes (Up to 50)",
            "Live Tatami Kinematics Dashboard",
            "7-Node Mesh NOC Sync & PySpark",
            "Dedicated Airgap Hardware Gateway"
        ],
        shopify_variant_id="gid://shopify/ProductVariant/440912345003",
        is_popular=False
    ),
]

HARDWARE_BUNDLES: List[HardwareBundle] = [
    HardwareBundle(
        bundle_id="movesense_hr_plus",
        name="Movesense Medical HR+ Sensor",
        price_usd=149.00,
        sensor_model="Movesense 261030002013",
        strap_type="Bicep & Chest Dual-Strap",
        sample_rate_hz=512,
        shopify_variant_id="gid://shopify/ProductVariant/440912345101",
        in_stock=True
    ),
    HardwareBundle(
        bundle_id="tactical_mesh_kit",
        name="Lauburu Tactical Airgap Gateway",
        price_usd=299.00,
        sensor_model="GL-MT3600BE Router + Movesense HR+",
        strap_type="Tactical Bicep Sleeve",
        sample_rate_hz=512,
        shopify_variant_id="gid://shopify/ProductVariant/440912345102",
        in_stock=True
    ),
]
