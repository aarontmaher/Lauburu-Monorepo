"""
GraphQL queries and mutations for Shopify Headless Monetization Engine.
"""

from .subscriptions import (
    GET_PRODUCT_WITH_SELLING_PLANS_QUERY,
    CREATE_SUBSCRIPTION_CART_MUTATION,
    GET_CUSTOMER_SUBSCRIPTION_CONTRACTS_QUERY,
    get_product_with_selling_plans,
    create_subscription_cart,
    get_customer_subscription_contracts,
    parse_product_with_selling_plans,
    parse_cart_payload,
)
from .hardware_kit import (
    CREATE_HARDWARE_KIT_CART_MUTATION,
    ADD_HARDWARE_KIT_LINES_MUTATION,
    UPDATE_CART_BUYER_IDENTITY_MUTATION,
    UPDATE_CART_DISCOUNT_CODES_MUTATION,
    create_hardware_kit_cart,
    add_hardware_kit_lines,
    update_cart_buyer_identity,
    update_cart_discount_codes,
)
from .token_gating import (
    CUSTOMER_ACCESS_TOKEN_CREATE_MUTATION,
    CUSTOMER_ACCESS_TOKEN_RENEW_MUTATION,
    CUSTOMER_ACCESS_TOKEN_DELETE_MUTATION,
    GET_CUSTOMER_GATED_PROFILE_QUERY,
    GET_CUSTOMER_ACCOUNT_SUBSCRIPTION_QUERY,
    create_customer_access_token,
    renew_customer_access_token,
    delete_customer_access_token,
    get_customer_gated_profile,
    get_customer_account_subscriptions,
    extract_tier_from_tags,
    get_dev_fallback_profile,
)

__all__ = [
    "GET_PRODUCT_WITH_SELLING_PLANS_QUERY",
    "CREATE_SUBSCRIPTION_CART_MUTATION",
    "GET_CUSTOMER_SUBSCRIPTION_CONTRACTS_QUERY",
    "get_product_with_selling_plans",
    "create_subscription_cart",
    "get_customer_subscription_contracts",
    "parse_product_with_selling_plans",
    "parse_cart_payload",
    "CREATE_HARDWARE_KIT_CART_MUTATION",
    "ADD_HARDWARE_KIT_LINES_MUTATION",
    "UPDATE_CART_BUYER_IDENTITY_MUTATION",
    "UPDATE_CART_DISCOUNT_CODES_MUTATION",
    "create_hardware_kit_cart",
    "add_hardware_kit_lines",
    "update_cart_buyer_identity",
    "update_cart_discount_codes",
    "CUSTOMER_ACCESS_TOKEN_CREATE_MUTATION",
    "CUSTOMER_ACCESS_TOKEN_RENEW_MUTATION",
    "CUSTOMER_ACCESS_TOKEN_DELETE_MUTATION",
    "GET_CUSTOMER_GATED_PROFILE_QUERY",
    "GET_CUSTOMER_ACCOUNT_SUBSCRIPTION_QUERY",
    "create_customer_access_token",
    "renew_customer_access_token",
    "delete_customer_access_token",
    "get_customer_gated_profile",
    "get_customer_account_subscriptions",
    "extract_tier_from_tags",
    "get_dev_fallback_profile",
]
