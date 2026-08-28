"""
Use Case 2: Hardware Kit Cart (Lauburu Mesh Nodes: GL.iNet + Movesense ECG Bundles).
Provides GraphQL mutations for creating bundle carts with custom node attributes, progressive line additions,
buyer identity association, and discount code application.
"""

from typing import Any, Dict, List, Optional
from ..client import ShopifyClient
from ..models import (
    BuyerIdentityInput,
    Cart,
    CartInput,
    CartLineInput,
    HardwareItemInput,
)
from .subscriptions import parse_cart_payload

CREATE_HARDWARE_KIT_CART_MUTATION = """
mutation createHardwareKitCart($input: CartInput!) {
  cartCreate(input: $input) {
    cart {
      id
      checkoutUrl
      totalQuantity
      lines(first: 25) {
        edges {
          node {
            id
            quantity
            attributes {
              key
              value
            }
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
            cost {
              totalAmount {
                amount
                currencyCode
              }
            }
          }
        }
      }
      cost {
        subtotalAmount {
          amount
          currencyCode
        }
        totalAmount {
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

ADD_HARDWARE_KIT_LINES_MUTATION = """
mutation addHardwareKitLines($cartId: ID!, $lines: [CartLineInput!]!) {
  cartLinesAdd(cartId: $cartId, lines: $lines) {
    cart {
      id
      checkoutUrl
      totalQuantity
      lines(first: 25) {
        edges {
          node {
            id
            quantity
            attributes {
              key
              value
            }
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
            cost {
              totalAmount {
                amount
                currencyCode
              }
            }
          }
        }
      }
      cost {
        subtotalAmount {
          amount
          currencyCode
        }
        totalAmount {
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

UPDATE_CART_BUYER_IDENTITY_MUTATION = """
mutation updateCartBuyerIdentity($cartId: ID!, $buyerIdentity: CartBuyerIdentityInput!) {
  cartBuyerIdentityUpdate(cartId: $cartId, buyerIdentity: $buyerIdentity) {
    cart {
      id
      checkoutUrl
      totalQuantity
      lines(first: 25) {
        edges {
          node {
            id
            quantity
            attributes {
              key
              value
            }
            merchandise {
              ... on ProductVariant {
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
      cost {
        subtotalAmount {
          amount
          currencyCode
        }
        totalAmount {
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

UPDATE_CART_DISCOUNT_CODES_MUTATION = """
mutation updateCartDiscountCodes($cartId: ID!, $discountCodes: [String!]!) {
  cartDiscountCodesUpdate(cartId: $cartId, discountCodes: $discountCodes) {
    cart {
      id
      checkoutUrl
      totalQuantity
      lines(first: 25) {
        edges {
          node {
            id
            quantity
            attributes {
              key
              value
            }
            merchandise {
              ... on ProductVariant {
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
      cost {
        subtotalAmount {
          amount
          currencyCode
        }
        totalAmount {
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


async def create_hardware_kit_cart(
    client: ShopifyClient,
    items: List[HardwareItemInput],
    buyer_identity: Optional[BuyerIdentityInput] = None,
    discount_codes: Optional[List[str]] = None,
) -> Cart:
    """
    Creates a new Shopify checkout cart with multiple physical hardware bundle items.
    """
    lines_input: List[CartLineInput] = [item.to_cart_line_input() for item in items]
    cart_input = CartInput(
        lines=lines_input,
        buyer_identity=buyer_identity,
        discount_codes=discount_codes,
    )

    data = await client.execute_storefront(
        query=CREATE_HARDWARE_KIT_CART_MUTATION,
        variables={"input": cart_input.to_graphql_dict()},
    )
    ShopifyClient.validate_user_errors(data, "cartCreate")

    cart_raw = data.get("cartCreate", {}).get("cart", {})
    return parse_cart_payload(cart_raw)


async def add_hardware_kit_lines(
    client: ShopifyClient,
    cart_id: str,
    items: List[HardwareItemInput],
) -> Cart:
    """
    Appends additional hardware nodes or accessories to an existing cart.
    """
    lines_payload: List[Dict[str, Any]] = [
        item.to_cart_line_input().to_graphql_dict() for item in items
    ]

    data = await client.execute_storefront(
        query=ADD_HARDWARE_KIT_LINES_MUTATION,
        variables={"cartId": cart_id, "lines": lines_payload},
    )
    ShopifyClient.validate_user_errors(data, "cartLinesAdd")

    cart_raw = data.get("cartLinesAdd", {}).get("cart", {})
    return parse_cart_payload(cart_raw)


async def update_cart_buyer_identity(
    client: ShopifyClient,
    cart_id: str,
    buyer_identity: BuyerIdentityInput,
) -> Cart:
    """
    Updates buyer contact and shipping country preferences on a cart.
    """
    data = await client.execute_storefront(
        query=UPDATE_CART_BUYER_IDENTITY_MUTATION,
        variables={"cartId": cart_id, "buyerIdentity": buyer_identity.to_graphql_dict()},
    )
    ShopifyClient.validate_user_errors(data, "cartBuyerIdentityUpdate")

    cart_raw = data.get("cartBuyerIdentityUpdate", {}).get("cart", {})
    return parse_cart_payload(cart_raw)


async def update_cart_discount_codes(
    client: ShopifyClient,
    cart_id: str,
    discount_codes: List[str],
) -> Cart:
    """
    Applies discount codes (e.g. promo bundle discount) to a cart.
    """
    data = await client.execute_storefront(
        query=UPDATE_CART_DISCOUNT_CODES_MUTATION,
        variables={"cartId": cart_id, "discountCodes": discount_codes},
    )
    ShopifyClient.validate_user_errors(data, "cartDiscountCodesUpdate")

    cart_raw = data.get("cartDiscountCodesUpdate", {}).get("cart", {})
    return parse_cart_payload(cart_raw)
