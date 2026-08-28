"""
Data models for the Shopify Headless Monetization Engine.
Provides typed Pydantic models for queries, mutations, carts, lines, selling plans, and subscriptions.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Money(BaseModel):
    """Monetary amount with currency code."""
    amount: str = "0.00"
    currency_code: str = "USD"


class Attribute(BaseModel):
    """Key-value custom attribute for carts and line items."""
    key: str
    value: str


class CartLineInput(BaseModel):
    """Input representation for adding items to a Shopify cart."""
    merchandise_id: str
    quantity: int = 1
    selling_plan_id: Optional[str] = None
    attributes: Optional[List[Attribute]] = None

    def to_graphql_dict(self) -> Dict[str, Any]:
        """Format input for GraphQL mutation variables."""
        payload: Dict[str, Any] = {
            "merchandiseId": self.merchandise_id,
            "quantity": self.quantity,
        }
        if self.selling_plan_id:
            payload["sellingPlanId"] = self.selling_plan_id
        if self.attributes:
            payload["attributes"] = [{"key": a.key, "value": a.value} for a in self.attributes]
        return payload


class BuyerIdentityInput(BaseModel):
    """Buyer identity input associated with a cart."""
    email: Optional[str] = None
    phone: Optional[str] = None
    country_code: Optional[str] = None
    customer_access_token: Optional[str] = None

    def to_graphql_dict(self) -> Dict[str, Any]:
        """Format for cartBuyerIdentityUpdate or cartCreate mutation."""
        res: Dict[str, Any] = {}
        if self.email:
            res["email"] = self.email
        if self.phone:
            res["phone"] = self.phone
        if self.country_code:
            res["countryCode"] = self.country_code
        if self.customer_access_token:
            res["customerAccessToken"] = self.customer_access_token
        return res


class CartInput(BaseModel):
    """Payload input for cartCreate mutation."""
    lines: Optional[List[CartLineInput]] = None
    buyer_identity: Optional[BuyerIdentityInput] = None
    discount_codes: Optional[List[str]] = None
    attributes: Optional[List[Attribute]] = None

    def to_graphql_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if self.lines:
            payload["lines"] = [line.to_graphql_dict() for line in self.lines]
        if self.buyer_identity:
            payload["buyerIdentity"] = self.buyer_identity.to_graphql_dict()
        if self.discount_codes:
            payload["discountCodes"] = self.discount_codes
        if self.attributes:
            payload["attributes"] = [{"key": a.key, "value": a.value} for a in self.attributes]
        return payload


class SellingPlanPriceAdjustment(BaseModel):
    """Price modification applied by a selling plan."""
    order_count: Optional[int] = None
    adjustment_percentage: Optional[float] = None
    adjustment_amount: Optional[Money] = None
    price: Optional[Money] = None


class SellingPlan(BaseModel):
    """Represents a recurring subscription selling plan."""
    id: str
    name: str
    description: Optional[str] = None
    recurring_deliveries: Optional[bool] = None
    options: Optional[List[Dict[str, Any]]] = None
    price_adjustments: List[SellingPlanPriceAdjustment] = Field(default_factory=list)


class SellingPlanGroup(BaseModel):
    """Group of selling plans associated with a product."""
    name: str
    app_name: Optional[str] = None
    options: Optional[List[Dict[str, Any]]] = None
    selling_plans: List[SellingPlan] = Field(default_factory=list)


class ProductVariant(BaseModel):
    """Shopify product variant details."""
    id: str
    title: str
    sku: Optional[str] = None
    price: Optional[Money] = None
    product_title: Optional[str] = None
    product_handle: Optional[str] = None


class ProductWithSellingPlans(BaseModel):
    """Product model containing subscription selling plan groups."""
    id: str
    title: str
    description: Optional[str] = None
    requires_selling_plan: bool = False
    selling_plan_groups: List[SellingPlanGroup] = Field(default_factory=list)
    variants: List[ProductVariant] = Field(default_factory=list)


class CartCost(BaseModel):
    """Financial totals and subtotal for a cart."""
    subtotal_amount: Money
    total_amount: Money
    checkout_charge_amount: Optional[Money] = None


class CartLine(BaseModel):
    """Individual line item within a cart."""
    id: str
    quantity: int = 1
    merchandise: Optional[ProductVariant] = None
    selling_plan: Optional[SellingPlan] = None
    attributes: List[Attribute] = Field(default_factory=list)
    cost_total: Optional[Money] = None


class CartDiscountCode(BaseModel):
    """Applied discount code and validity status."""
    code: str
    applicable: bool = True


class Cart(BaseModel):
    """Comprehensive Shopify cart representation."""
    id: str
    checkout_url: str
    total_quantity: int = 0
    lines: List[CartLine] = Field(default_factory=list)
    cost: Optional[CartCost] = None
    buyer_identity: Optional[BuyerIdentityInput] = None
    discount_codes: List[CartDiscountCode] = Field(default_factory=list)


class SubscriptionContractLine(BaseModel):
    """Active line item in a subscription contract."""
    id: str
    title: str
    quantity: int = 1
    current_price: Money
    selling_plan_id: Optional[str] = None
    selling_plan_name: Optional[str] = None


class SubscriptionContract(BaseModel):
    """Recurring subscription contract details from Admin / Customer Account API."""
    id: str
    status: str
    created_at: Optional[str] = None
    next_billing_date: Optional[str] = None
    customer_id: Optional[str] = None
    customer_email: Optional[str] = None
    lines: List[SubscriptionContractLine] = Field(default_factory=list)


class CustomerAccessToken(BaseModel):
    """Session access token for customer-authenticated Storefront queries."""
    access_token: str
    expires_at: str


class CustomerGatedProfile(BaseModel):
    """Customer profile including membership tier and tags."""
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    tier: str = "FREE"
    is_paid_subscriber: bool = False
    orders: List[Dict[str, Any]] = Field(default_factory=list)


class TokenGatedAccessGrant(BaseModel):
    """Access grant decision for token-gated features (Spatial Grappling, Port 4000)."""
    allowed: bool
    customer_id: Optional[str] = None
    email: Optional[str] = None
    tier: str = "FREE"
    is_paid_subscriber: bool = False
    granted_features: List[str] = Field(default_factory=list)
    reason: Optional[str] = None
    checkout_upgrade_url: Optional[str] = None


class HardwareItemInput(BaseModel):
    """Convenience model for configuring hardware bundle items."""
    variant_id: str
    quantity: int = 1
    node_role: Optional[str] = None
    sensor_type: Optional[str] = None
    custom_attributes: Optional[Dict[str, str]] = None

    def to_cart_line_input(self) -> CartLineInput:
        attrs: List[Attribute] = []
        if self.node_role:
            attrs.append(Attribute(key="node_role", value=self.node_role))
        if self.sensor_type:
            attrs.append(Attribute(key="sensor_type", value=self.sensor_type))
        if self.custom_attributes:
            for k, v in self.custom_attributes.items():
                attrs.append(Attribute(key=k, value=v))
        return CartLineInput(
            merchandise_id=self.variant_id,
            quantity=self.quantity,
            attributes=attrs if attrs else None,
        )
