"""
High-Level Monetization Service orchestrating the 3 Core Business Use Cases:
1. Recurring Subscriptions (OpenClaw AI API)
2. Hardware Kit Carts (GL.iNet + Movesense Bundles)
3. Token-Gated UI Gatekeeping (Spatial Grappling 3D / Port 4000)
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from ..client import ShopifyClient
from ..config import ShopifyConfig
from ..errors import ShopifyAuthError, ShopifyError, ShopifyUserError
from ..models import (
    BuyerIdentityInput,
    Cart,
    CustomerAccessToken,
    CustomerGatedProfile,
    HardwareItemInput,
    ProductWithSellingPlans,
    SubscriptionContract,
    TokenGatedAccessGrant,
)
from ..queries.hardware_kit import (
    add_hardware_kit_lines,
    create_hardware_kit_cart,
    update_cart_buyer_identity,
    update_cart_discount_codes,
)
from ..queries.subscriptions import (
    create_subscription_cart,
    get_customer_subscription_contracts,
    get_product_with_selling_plans,
)
from ..queries.token_gating import (
    create_customer_access_token,
    delete_customer_access_token,
    get_customer_account_subscriptions,
    get_customer_gated_profile,
    renew_customer_access_token,
)
from .compute_offset import ComputeOffsetCalculator

logger = logging.getLogger("shopify_headless.monetization_service")


class ShopifyMonetizationService:
    """
    Unified domain gateway connecting client apps (Port 4000 Hub, Spatial Grappling 3D,
    and Shopify storefront) to headless Shopify commerce operations.
    """

    def __init__(
        self,
        client: Optional[ShopifyClient] = None,
        config: Optional[ShopifyConfig] = None,
    ):
        self.client = client or ShopifyClient(config=config)

    # -------------------------------------------------------------------------
    # Use Case 1: Recurring Subscriptions
    # -------------------------------------------------------------------------

    async def get_subscription_plans(self, product_handle: str) -> Optional[ProductWithSellingPlans]:
        """Fetch subscription plans, frequencies, and price adjustments for a product."""
        return await get_product_with_selling_plans(self.client, handle=product_handle)

    async def create_subscription_checkout(
        self,
        product_handle: str,
        selling_plan_id: str,
        variant_id: Optional[str] = None,
        quantity: int = 1,
        buyer_identity: Optional[BuyerIdentityInput] = None,
        discount_codes: Optional[List[str]] = None,
    ) -> Cart:
        """
        Creates a checkout cart for purchasing a recurring subscription.
        Automatically resolves the primary variant if variant_id is not specified.
        """
        target_variant_id = variant_id
        if not target_variant_id:
            product = await self.get_subscription_plans(product_handle)
            if not product or not product.variants:
                raise ShopifyError(f"No variants found for subscription product '{product_handle}'")
            target_variant_id = product.variants[0].id

        return await create_subscription_cart(
            client=self.client,
            variant_id=target_variant_id,
            selling_plan_id=selling_plan_id,
            quantity=quantity,
            buyer_identity=buyer_identity,
            discount_codes=discount_codes,
        )

    async def list_subscription_contracts(
        self,
        first: int = 10,
        query: Optional[str] = None,
    ) -> List[SubscriptionContract]:
        """List active/historical subscription contracts via Admin API."""
        return await get_customer_subscription_contracts(
            client=self.client,
            first=first,
            query=query,
        )

    # -------------------------------------------------------------------------
    # Use Case 2: Hardware Kit Carts
    # -------------------------------------------------------------------------

    async def create_hardware_bundle_cart(
        self,
        items: List[HardwareItemInput],
        buyer_identity: Optional[BuyerIdentityInput] = None,
        discount_codes: Optional[List[str]] = None,
    ) -> Cart:
        """
        Creates a checkout cart containing physical mesh hardware nodes and sensors.
        """
        return await create_hardware_kit_cart(
            client=self.client,
            items=items,
            buyer_identity=buyer_identity,
            discount_codes=discount_codes,
        )

    async def add_hardware_items_to_cart(
        self,
        cart_id: str,
        items: List[HardwareItemInput],
    ) -> Cart:
        """Appends additional nodes or accessories to an existing cart."""
        return await add_hardware_kit_lines(
            client=self.client,
            cart_id=cart_id,
            items=items,
        )

    async def update_cart_shipping_identity(
        self,
        cart_id: str,
        buyer_identity: BuyerIdentityInput,
    ) -> Cart:
        """Updates shipping address, contact, and country preferences on a cart."""
        return await update_cart_buyer_identity(
            client=self.client,
            cart_id=cart_id,
            buyer_identity=buyer_identity,
        )

    async def apply_cart_discounts(
        self,
        cart_id: str,
        discount_codes: List[str],
    ) -> Cart:
        """Applies promotional discount codes to a cart."""
        return await update_cart_discount_codes(
            client=self.client,
            cart_id=cart_id,
            discount_codes=discount_codes,
        )

    # -------------------------------------------------------------------------
    # Use Case 3: Token-Gated Authentication & UI Gatekeeper
    # -------------------------------------------------------------------------

    async def authenticate_customer(
        self,
        email: str,
        password: str,
    ) -> Tuple[CustomerAccessToken, Optional[CustomerGatedProfile]]:
        """
        Logs in customer, returning session token and verified profile.
        """
        token = await create_customer_access_token(self.client, email=email, password=password)
        profile = await get_customer_gated_profile(self.client, customer_access_token=token.access_token)
        return token, profile

    async def renew_token(self, token: str) -> CustomerAccessToken:
        """Renews an active customer session token."""
        return await renew_customer_access_token(self.client, customer_access_token=token)

    async def logout_customer(self, token: str) -> bool:
        """Logs out customer session."""
        return await delete_customer_access_token(self.client, customer_access_token=token)

    async def verify_token_gated_access(
        self,
        customer_token: str,
        required_tier: str = "tier_pro",
    ) -> TokenGatedAccessGrant:
        """
        Verifies customer token against required membership tier to unlock features
        like 3D Spatial Grappling, 512Hz ECG biometrics DSP, and Port 4000 Hub.
        """
        if not customer_token or not customer_token.strip():
            return TokenGatedAccessGrant(
                allowed=False,
                reason="MISSING_CUSTOMER_TOKEN",
                checkout_upgrade_url=f"https://{self.client.config.storedomain if hasattr(self.client.config, 'storedomain') else self.client.config.store_domain}/products/openclaw-ai-pro",
            )

        profile = await get_customer_gated_profile(self.client, customer_access_token=customer_token)
        if not profile:
            return TokenGatedAccessGrant(
                allowed=False,
                reason="INVALID_OR_EXPIRED_TOKEN",
                checkout_upgrade_url=f"https://{self.client.config.store_domain}/products/openclaw-ai-pro",
            )

        # Check tier compliance
        req_lower = required_tier.lower()
        has_access = False

        if req_lower in ("free", "all"):
            has_access = True
        elif req_lower in ("tier_pro", "paid_pro", "pro"):
            has_access = profile.is_paid_subscriber or profile.tier in ("PAID_PRO", "ENTERPRISE", "CONTRIBUTOR_PRO")
        elif req_lower in ("tier_enterprise", "enterprise"):
            has_access = profile.tier == "ENTERPRISE"
        elif req_lower in ("tier_contributor", "contributor_pro"):
            has_access = profile.tier in ("CONTRIBUTOR_PRO", "ENTERPRISE")
        else:
            # Custom tag match
            has_access = any(req_lower in str(t).lower() for t in profile.tags)

        if has_access:
            return TokenGatedAccessGrant(
                allowed=True,
                customer_id=profile.id,
                email=profile.email,
                tier=profile.tier,
                is_paid_subscriber=profile.is_paid_subscriber,
                granted_features=[
                    "3d_spatial_grappling",
                    "port_4000_hub",
                    "512hz_ecg_telemetry",
                    "lora_distillation_sync",
                ],
            )

        return TokenGatedAccessGrant(
            allowed=False,
            customer_id=profile.id,
            email=profile.email,
            tier=profile.tier,
            is_paid_subscriber=profile.is_paid_subscriber,
            reason="INSUFFICIENT_MEMBERSHIP_TIER",
            checkout_upgrade_url=f"https://{self.client.config.store_domain}/products/openclaw-ai-pro",
        )

    # -------------------------------------------------------------------------
    # Profitability & Compute Offset Modeling
    # -------------------------------------------------------------------------

    def calculate_plan_profitability(
        self,
        monthly_price_usd: float,
        monthly_compute_hours: float,
        is_heavy_moe: bool = True,
    ) -> Dict[str, Any]:
        """
        Calculates whether a subscription pricing plan meets the 70% gross margin target.
        """
        total_seconds = int(monthly_compute_hours * 3600)
        return ComputeOffsetCalculator.calculate_subscription_gross_margin(
            monthly_price_usd=monthly_price_usd,
            monthly_compute_seconds=total_seconds,
            is_heavy_moe=is_heavy_moe,
        )
