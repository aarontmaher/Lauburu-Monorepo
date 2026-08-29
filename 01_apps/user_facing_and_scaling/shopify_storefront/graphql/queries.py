"""
Shopify Storefront GraphQL Queries.
===================================
Subsystem: 01_apps/user_facing_and_scaling/shopify_storefront/graphql/queries.py
"""

GET_PRODUCTS_QUERY = """
query GetProducts($first: Int = 10) {
  products(first: $first) {
    edges {
      node {
        id
        title
        description
        priceRange {
          minVariantPrice {
            amount
            currencyCode
          }
        }
        variants(first: 5) {
          edges {
            node {
              id
              title
              price {
                amount
              }
              availableForSale
            }
          }
        }
      }
    }
  }
}
"""

GET_SUBSCRIPTION_PLANS_QUERY = """
query GetSubscriptionPlans {
  products(first: 5, query: "tag:membership") {
    edges {
      node {
        id
        title
        tags
        variants(first: 3) {
          edges {
            node {
              id
              title
              price {
                amount
              }
            }
          }
        }
      }
    }
  }
}
"""
