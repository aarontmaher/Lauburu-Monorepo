"""
Shopify Storefront GraphQL Mutations.
=====================================
Subsystem: 01_apps/user_facing_and_scaling/shopify_storefront/graphql/mutations.py
"""

CREATE_CART_MUTATION = """
mutation cartCreate($input: CartInput!) {
  cartCreate(input: $input) {
    cart {
      id
      checkoutUrl
      cost {
        totalAmount {
          amount
          currencyCode
        }
      }
      lines(first: 10) {
        edges {
          node {
            id
            quantity
            merchandise {
              ... on ProductVariant {
                id
                title
              }
            }
          }
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

CART_LINES_ADD_MUTATION = """
mutation cartLinesAdd($cartId: ID!, $lines: [CartLineInput!]!) {
  cartLinesAdd(cartId: $cartId, lines: $lines) {
    cart {
      id
      checkoutUrl
      cost {
        totalAmount {
          amount
          currencyCode
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""
