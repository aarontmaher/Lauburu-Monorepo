"""
Lauburu Headless Shopify Storefront & Membership Suite.
======================================================
Subsystem: 01_apps/user_facing_and_scaling/shopify_storefront
Version: 1.0.0-CANONICAL

Headless commerce portal supporting athlete membership subscriptions
($9/mo Athlete, $29/mo Pro, $99/mo Gym Team), Movesense HR+ hardware bundles,
and Storefront GraphQL (2026-01) integration.

Subpackages:
- core: Config, data models, and cart sessions
- graphql: GraphQL client, queries, and mutations
- presentation: Pricing catalog, Textual TUI HUD, and store runners
"""

from .core import (
    ShopifyConfig,
    MembershipTier,
    HardwareBundle,
    CartLine,
    CheckoutSession,
)
from .graphql import (
    GET_PRODUCTS_QUERY,
    GET_SUBSCRIPTION_PLANS_QUERY,
    CREATE_CART_MUTATION,
    CART_LINES_ADD_MUTATION,
    ShopifyStorefrontClient,
)
from .presentation import (
    MEMBERSHIP_TIERS,
    HARDWARE_BUNDLES,
    StorefrontMembershipApp,
    run_storefront,
)

__version__ = "1.0.0"

__all__ = [
    "__version__",
    "ShopifyConfig",
    "MembershipTier",
    "HardwareBundle",
    "CartLine",
    "CheckoutSession",
    "GET_PRODUCTS_QUERY",
    "GET_SUBSCRIPTION_PLANS_QUERY",
    "CREATE_CART_MUTATION",
    "CART_LINES_ADD_MUTATION",
    "ShopifyStorefrontClient",
    "MEMBERSHIP_TIERS",
    "HARDWARE_BUNDLES",
    "StorefrontMembershipApp",
    "run_storefront",
]
