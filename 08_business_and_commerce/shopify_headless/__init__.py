"""
Shopify Headless Monetization Engine for the Lauburu Ecosystem.
Governs Storefront and Admin GraphQL integrations for recurring AI subscriptions,
hardware mesh node bundling, and token-gated UI authorization.
"""

from .config import ShopifyConfig, get_shopify_config
from .client import ShopifyClient
from .errors import (
    ShopifyError,
    ShopifyConfigError,
    ShopifyGraphQLError,
    ShopifyRateLimitError,
    ShopifyAuthError,
    ShopifyUserError,
)
from .models import (
    Money,
    Attribute,
    CartLineInput,
    BuyerIdentityInput,
    CartInput,
    HardwareItemInput,
    SellingPlanPriceAdjustment,
    SellingPlan,
    SellingPlanGroup,
    ProductVariant,
    ProductWithSellingPlans,
    CartCost,
    CartLine,
    CartDiscountCode,
    Cart,
    SubscriptionContractLine,
    SubscriptionContract,
    CustomerAccessToken,
    CustomerGatedProfile,
    TokenGatedAccessGrant,
)
from .queries import (
    get_product_with_selling_plans,
    create_subscription_cart,
    get_customer_subscription_contracts,
    create_hardware_kit_cart,
    add_hardware_kit_lines,
    update_cart_buyer_identity,
    update_cart_discount_codes,
    create_customer_access_token,
    renew_customer_access_token,
    delete_customer_access_token,
    get_customer_gated_profile,
    get_customer_account_subscriptions,
)
from .services import (
    ComputeOffsetCalculator,
    ShopifyMonetizationService,
)

__version__ = "1.0.0"

__all__ = [
    "ShopifyConfig",
    "get_shopify_config",
    "ShopifyClient",
    "ShopifyError",
    "ShopifyConfigError",
    "ShopifyGraphQLError",
    "ShopifyRateLimitError",
    "ShopifyAuthError",
    "ShopifyUserError",
    "Money",
    "Attribute",
    "CartLineInput",
    "BuyerIdentityInput",
    "CartInput",
    "HardwareItemInput",
    "SellingPlanPriceAdjustment",
    "SellingPlan",
    "SellingPlanGroup",
    "ProductVariant",
    "ProductWithSellingPlans",
    "CartCost",
    "CartLine",
    "CartDiscountCode",
    "Cart",
    "SubscriptionContractLine",
    "SubscriptionContract",
    "CustomerAccessToken",
    "CustomerGatedProfile",
    "TokenGatedAccessGrant",
    "get_product_with_selling_plans",
    "create_subscription_cart",
    "get_customer_subscription_contracts",
    "create_hardware_kit_cart",
    "add_hardware_kit_lines",
    "update_cart_buyer_identity",
    "update_cart_discount_codes",
    "create_customer_access_token",
    "renew_customer_access_token",
    "delete_customer_access_token",
    "get_customer_gated_profile",
    "get_customer_account_subscriptions",
    "ComputeOffsetCalculator",
    "ShopifyMonetizationService",
]
