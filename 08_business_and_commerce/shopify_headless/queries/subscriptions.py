"""
Use Case 1: Recurring Subscriptions (OpenClaw AI API & Cloud Access).
Provides GraphQL queries, mutations, and parsers for Storefront selling plans, subscription carts,
and Admin subscription contract tracking.
"""

from typing import Any, Dict, List, Optional
from ..client import ShopifyClient
from ..models import (
    Attribute,
    BuyerIdentityInput,
    Cart,
    CartCost,
    CartDiscountCode,
    CartLine,
    Money,
    ProductVariant,
    ProductWithSellingPlans,
    SellingPlan,
    SellingPlanGroup,
    SellingPlanPriceAdjustment,
    SubscriptionContract,
    SubscriptionContractLine,
)

GET_PRODUCT_WITH_SELLING_PLANS_QUERY = """
query getProductWithSellingPlans($handle: String!) {
  product(handle: $handle) {
    id
    title
    description
    requiresSellingPlan
    sellingPlanGroups(first: 10) {
      edges {
        node {
          name
          appName
          options {
            name
            values
          }
          sellingPlans(first: 10) {
            edges {
              node {
                id
                name
                description
                recurringDeliveries
                options {
                  name
                  value
                }
                priceAdjustments {
                  orderCount
                  adjustmentValue {
                    ... on SellingPlanPercentagePriceAdjustment {
                      adjustmentPercentage
                    }
                    ... on SellingPlanFixedAmountPriceAdjustment {
                      adjustmentAmount {
                        amount
                        currencyCode
                      }
                    }
                    ... on SellingPlanFixedPriceAdjustment {
                      price {
                        amount
                        currencyCode
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    variants(first: 10) {
      edges {
        node {
          id
          title
          sku
          price {
            amount
            currencyCode
          }
        }
      }
    }
  }
}
"""

CREATE_SUBSCRIPTION_CART_MUTATION = """
mutation createSubscriptionCart($cartInput: CartInput!) {
  cartCreate(input: $cartInput) {
    cart {
      id
      checkoutUrl
      totalQuantity
      lines(first: 10) {
        edges {
          node {
            id
            quantity
            merchandise {
              ... on ProductVariant {
                id
                title
                sku
                price {
                  amount
                  currencyCode
                }
                product {
                  title
                  handle
                }
              }
            }
            sellingPlanAllocation {
              sellingPlan {
                id
                name
                description
              }
              priceAdjustments {
                price {
                  amount
                  currencyCode
                }
                compareAtPrice {
                  amount
                  currencyCode
                }
                perDeliveryPrice {
                  amount
                  currencyCode
                }
              }
            }
          }
        }
      }
      cost {
        totalAmount {
          amount
          currencyCode
        }
        subtotalAmount {
          amount
          currencyCode
        }
        checkoutChargeAmount {
          amount
          currencyCode
        }
      }
      buyerIdentity {
        email
        phone
        countryCode
      }
      discountCodes {
        code
        applicable
      }
    }
    userErrors {
      field
      message
      code
    }
    warnings {
      code
      message
    }
  }
}
"""

GET_CUSTOMER_SUBSCRIPTION_CONTRACTS_QUERY = """
query getCustomerSubscriptionContracts($first: Int!, $query: String) {
  subscriptionContracts(first: $first, query: $query) {
    edges {
      node {
        id
        status
        createdAt
        nextBillingDate
        customer {
          id
          firstName
          lastName
          defaultEmailAddress {
            emailAddress
          }
        }
        lines(first: 10) {
          edges {
            node {
              id
              title
              quantity
              currentPrice {
                amount
                currencyCode
              }
              sellingPlanId
              sellingPlanName
            }
          }
        }
      }
    }
  }
}
"""


def parse_product_with_selling_plans(data: Dict[str, Any]) -> Optional[ProductWithSellingPlans]:
    """Parse GraphQL product payload into ProductWithSellingPlans model."""
    prod_data = data.get("product")
    if not prod_data:
        return None

    groups: List[SellingPlanGroup] = []
    raw_groups = prod_data.get("sellingPlanGroups", {}).get("edges", [])
    for g_edge in raw_groups:
        g_node = g_edge.get("node", {})
        plans: List[SellingPlan] = []
        raw_plans = g_node.get("sellingPlans", {}).get("edges", [])
        for p_edge in raw_plans:
            p_node = p_edge.get("node", {})
            adjustments: List[SellingPlanPriceAdjustment] = []
            for adj in p_node.get("priceAdjustments", []):
                val = adj.get("adjustmentValue", {})
                adjustments.append(
                    SellingPlanPriceAdjustment(
                        order_count=adj.get("orderCount"),
                        adjustment_percentage=val.get("adjustmentPercentage"),
                        adjustment_amount=(
                            Money(
                                amount=val["adjustmentAmount"]["amount"],
                                currency_code=val["adjustmentAmount"]["currencyCode"],
                            )
                            if "adjustmentAmount" in val and val["adjustmentAmount"]
                            else None
                        ),
                        price=(
                            Money(
                                amount=val["price"]["amount"],
                                currency_code=val["price"]["currencyCode"],
                            )
                            if "price" in val and val["price"]
                            else None
                        ),
                    )
                )
            plans.append(
                SellingPlan(
                    id=p_node.get("id", ""),
                    name=p_node.get("name", ""),
                    description=p_node.get("description"),
                    recurring_deliveries=p_node.get("recurringDeliveries"),
                    options=p_node.get("options"),
                    price_adjustments=adjustments,
                )
            )

        groups.append(
            SellingPlanGroup(
                name=g_node.get("name", ""),
                app_name=g_node.get("appName"),
                options=g_node.get("options"),
                selling_plans=plans,
            )
        )

    variants: List[ProductVariant] = []
    raw_variants = prod_data.get("variants", {}).get("edges", [])
    for v_edge in raw_variants:
        v_node = v_edge.get("node", {})
        price_dict = v_node.get("price", {})
        variants.append(
            ProductVariant(
                id=v_node.get("id", ""),
                title=v_node.get("title", ""),
                sku=v_node.get("sku"),
                price=Money(
                    amount=str(price_dict.get("amount", "0.00")),
                    currency_code=price_dict.get("currencyCode", "USD"),
                ) if price_dict else None,
                product_title=prod_data.get("title"),
            )
        )

    return ProductWithSellingPlans(
        id=prod_data.get("id", ""),
        title=prod_data.get("title", ""),
        description=prod_data.get("description"),
        requires_selling_plan=bool(prod_data.get("requiresSellingPlan", False)),
        selling_plan_groups=groups,
        variants=variants,
    )


def parse_cart_payload(cart_data: Dict[str, Any]) -> Cart:
    """Parse GraphQL cart object into Cart Pydantic model."""
    lines: List[CartLine] = []
    raw_lines = cart_data.get("lines", {}).get("edges", [])
    for l_edge in raw_lines:
        l_node = l_edge.get("node", {})
        m_node = l_node.get("merchandise", {}) or {}
        p_node = m_node.get("product", {}) or {}
        m_price = m_node.get("price", {}) or {}

        var_model = ProductVariant(
            id=m_node.get("id", ""),
            title=m_node.get("title", ""),
            sku=m_node.get("sku"),
            price=Money(
                amount=str(m_price.get("amount", "0.00")),
                currency_code=m_price.get("currencyCode", "USD"),
            ) if m_price else None,
            product_title=p_node.get("title"),
            product_handle=p_node.get("handle"),
        )

        plan_model: Optional[SellingPlan] = None
        plan_alloc = l_node.get("sellingPlanAllocation")
        if plan_alloc and plan_alloc.get("sellingPlan"):
            sp = plan_alloc["sellingPlan"]
            plan_model = SellingPlan(
                id=sp.get("id", ""),
                name=sp.get("name", ""),
                description=sp.get("description"),
            )

        attrs = [
            Attribute(key=a.get("key", ""), value=a.get("value", ""))
            for a in l_node.get("attributes", [])
        ]

        cost_total = None
        if "cost" in l_node and l_node["cost"].get("totalAmount"):
            cost_total = Money(
                amount=str(l_node["cost"]["totalAmount"].get("amount", "0.00")),
                currency_code=l_node["cost"]["totalAmount"].get("currencyCode", "USD"),
            )

        lines.append(
            CartLine(
                id=l_node.get("id", ""),
                quantity=int(l_node.get("quantity", 1)),
                merchandise=var_model,
                selling_plan=plan_model,
                attributes=attrs,
                cost_total=cost_total,
            )
        )

    cost_data = cart_data.get("cost", {})
    cost_model = CartCost(
        subtotal_amount=Money(
            amount=str(cost_data.get("subtotalAmount", {}).get("amount", "0.00")),
            currency_code=cost_data.get("subtotalAmount", {}).get("currencyCode", "USD"),
        ),
        total_amount=Money(
            amount=str(cost_data.get("totalAmount", {}).get("amount", "0.00")),
            currency_code=cost_data.get("totalAmount", {}).get("currencyCode", "USD"),
        ),
        checkout_charge_amount=(
            Money(
                amount=str(cost_data["checkoutChargeAmount"].get("amount", "0.00")),
                currency_code=cost_data["checkoutChargeAmount"].get("currencyCode", "USD"),
            )
            if cost_data.get("checkoutChargeAmount")
            else None
        ),
    )

    buyer_id_data = cart_data.get("buyerIdentity")
    buyer_id_model = (
        BuyerIdentityInput(
            email=buyer_id_data.get("email"),
            phone=buyer_id_data.get("phone"),
            country_code=buyer_id_data.get("countryCode"),
        )
        if buyer_id_data
        else None
    )

    discounts = [
        CartDiscountCode(
            code=d.get("code", ""),
            applicable=bool(d.get("applicable", True)),
        )
        for d in cart_data.get("discountCodes", [])
    ]

    return Cart(
        id=cart_data.get("id", ""),
        checkout_url=cart_data.get("checkoutUrl", ""),
        total_quantity=int(cart_data.get("totalQuantity", len(lines))),
        lines=lines,
        cost=cost_model,
        buyer_identity=buyer_id_model,
        discount_codes=discounts,
    )


async def get_product_with_selling_plans(
    client: ShopifyClient,
    handle: str,
) -> Optional[ProductWithSellingPlans]:
    """Fetch product details along with selling plan groups and subscription discounts."""
    data = await client.execute_storefront(
        query=GET_PRODUCT_WITH_SELLING_PLANS_QUERY,
        variables={"handle": handle},
    )
    return parse_product_with_selling_plans(data)


async def create_subscription_cart(
    client: ShopifyClient,
    variant_id: str,
    selling_plan_id: str,
    quantity: int = 1,
    buyer_identity: Optional[BuyerIdentityInput] = None,
    discount_codes: Optional[List[str]] = None,
) -> Cart:
    """
    Creates a new Shopify checkout cart with a recurring subscription line item.
    """
    cart_input: Dict[str, Any] = {
        "lines": [
            {
                "merchandiseId": variant_id,
                "sellingPlanId": selling_plan_id,
                "quantity": quantity,
            }
        ]
    }
    if buyer_identity:
        cart_input["buyerIdentity"] = buyer_identity.to_graphql_dict()
    if discount_codes:
        cart_input["discountCodes"] = discount_codes

    data = await client.execute_storefront(
        query=CREATE_SUBSCRIPTION_CART_MUTATION,
        variables={"cartInput": cart_input},
    )
    ShopifyClient.validate_user_errors(data, "cartCreate")

    cart_raw = data.get("cartCreate", {}).get("cart", {})
    return parse_cart_payload(cart_raw)


async def get_customer_subscription_contracts(
    client: ShopifyClient,
    first: int = 10,
    query: Optional[str] = None,
) -> List[SubscriptionContract]:
    """
    Queries active and historical customer subscription contracts via the Admin API.
    """
    variables: Dict[str, Any] = {"first": first}
    if query:
        variables["query"] = query

    data = await client.execute_admin(
        query=GET_CUSTOMER_SUBSCRIPTION_CONTRACTS_QUERY,
        variables=variables,
    )

    contracts: List[SubscriptionContract] = []
    edges = data.get("subscriptionContracts", {}).get("edges", [])
    for edge in edges:
        node = edge.get("node", {})
        customer_node = node.get("customer") or {}
        email = (
            customer_node.get("defaultEmailAddress", {}).get("emailAddress")
            if customer_node.get("defaultEmailAddress")
            else None
        )

        lines: List[SubscriptionContractLine] = []
        raw_lines = node.get("lines", {}).get("edges", [])
        for l_edge in raw_lines:
            l_node = l_edge.get("node", {})
            price_data = l_node.get("currentPrice", {})
            lines.append(
                SubscriptionContractLine(
                    id=l_node.get("id", ""),
                    title=l_node.get("title", ""),
                    quantity=int(l_node.get("quantity", 1)),
                    current_price=Money(
                        amount=str(price_data.get("amount", "0.00")),
                        currency_code=price_data.get("currencyCode", "USD"),
                    ),
                    selling_plan_id=l_node.get("sellingPlanId"),
                    selling_plan_name=l_node.get("sellingPlanName"),
                )
            )

        contracts.append(
            SubscriptionContract(
                id=node.get("id", ""),
                status=node.get("status", "ACTIVE"),
                created_at=node.get("createdAt"),
                next_billing_date=node.get("nextBillingDate"),
                customer_id=customer_node.get("id"),
                customer_email=email,
                lines=lines,
            )
        )

    return contracts
