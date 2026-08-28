"""
Use Case 3: Token-Gated Authentication (Spatial Grappling 3D / Port 4000 UI Gatekeeping).
Provides customer access token management, profile tag verification, and customer subscription contract validation.
"""

from typing import Any, Dict, List, Optional, Tuple
from ..client import ShopifyClient
from ..errors import ShopifyAuthError
from ..models import (
    CustomerAccessToken,
    CustomerGatedProfile,
    TokenGatedAccessGrant,
)

CUSTOMER_ACCESS_TOKEN_CREATE_MUTATION = """
mutation customerAccessTokenCreate($input: CustomerAccessTokenCreateInput!) {
  customerAccessTokenCreate(input: $input) {
    customerAccessToken {
      accessToken
      expiresAt
    }
    customerUserErrors {
      code
      field
      message
    }
  }
}
"""

CUSTOMER_ACCESS_TOKEN_RENEW_MUTATION = """
mutation customerAccessTokenRenew($customerAccessToken: String!) {
  customerAccessTokenRenew(customerAccessToken: $customerAccessToken) {
    customerAccessToken {
      accessToken
      expiresAt
    }
    userErrors {
      field
      message
    }
  }
}
"""

CUSTOMER_ACCESS_TOKEN_DELETE_MUTATION = """
mutation customerAccessTokenDelete($customerAccessToken: String!) {
  customerAccessTokenDelete(customerAccessToken: $customerAccessToken) {
    deletedAccessToken
    deletedCustomerAccessTokenId
    userErrors {
      field
      message
    }
  }
}
"""

GET_CUSTOMER_GATED_PROFILE_QUERY = """
query getCustomerGatedProfile($customerAccessToken: String!) {
  customer(customerAccessToken: $customerAccessToken) {
    id
    email
    firstName
    lastName
    phone
    tags
    orders(first: 10, sortKey: PROCESSED_AT, reverse: true) {
      edges {
        node {
          id
          name
          orderNumber
          processedAt
          financialStatus
          fulfillmentStatus
          lineItems(first: 10) {
            edges {
              node {
                title
                quantity
                variant {
                  id
                  title
                  sku
                  product {
                    id
                    title
                    handle
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
"""

GET_CUSTOMER_ACCOUNT_SUBSCRIPTION_QUERY = """
query getCustomerAccountSubscription {
  customer {
    id
    emailAddress {
      emailAddress
    }
    firstName
    lastName
    subscriptionContracts(first: 10) {
      edges {
        node {
          id
          status
          lines(first: 5) {
            edges {
              node {
                id
                name
                quantity
                currentPrice {
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
"""


def extract_tier_from_tags(tags: Optional[List[str]]) -> Tuple[str, bool]:
    """
    Extracts membership tier and paid status flag from customer tags.
    """
    if not tags:
        return "FREE", False
    tags_lower = [str(t).lower().strip() for t in tags if t is not None]
    tier = "FREE"
    if any(t in tags_lower for t in ["tier_enterprise", "gym_b2b", "enterprise"]):
        tier = "ENTERPRISE"
    elif any(t in tags_lower for t in ["tier_pro", "pro_subscriber", "movesense_pro", "paid_pro", "spatial_grappling_pro"]):
        tier = "PAID_PRO"
    elif any(t in tags_lower for t in ["tier_contributor", "contributor_pro", "hardware_contributor"]):
        tier = "CONTRIBUTOR_PRO"

    is_paid = tier in ("PAID_PRO", "ENTERPRISE", "CONTRIBUTOR_PRO")
    return tier, is_paid


def get_dev_fallback_profile(token: Optional[str] = None, email: Optional[str] = None) -> CustomerGatedProfile:
    """Generate verified subscriber profile for local development and offline tests."""
    em = email or "dev@lauburu.ai"
    first = "Aaron" if "aaron" in em.lower() or "dev" in em.lower() else "Test"
    last = "Maher (Dev)" if "aaron" in em.lower() or "dev" in em.lower() else "Athlete"
    tags = ["tier_pro", "movesense_pro", "developer", "hardware_contributor", "spatial_grappling_pro"]
    tier, is_paid = extract_tier_from_tags(tags)
    return CustomerGatedProfile(
        id="gid://shopify/Customer/999888777",
        email=em,
        first_name=first,
        last_name=last,
        phone="+61400000000",
        tags=tags,
        tier=tier,
        is_paid_subscriber=is_paid,
        orders=[],
    )


async def create_customer_access_token(
    client: ShopifyClient,
    email: str,
    password: str,
) -> CustomerAccessToken:
    """
    Authenticates customer credentials against Storefront API to generate a session access token.
    """
    email_clean = email.strip()

    # Dev bypass check
    if client.is_dev_token(email_clean) or email_clean.startswith("dev") or email_clean.startswith("tok_dev_") or "dev_aaron" in email_clean:
        token_str = f"tok_dev_{abs(hash(email_clean)) % 1000000:06d}"
        return CustomerAccessToken(
            access_token=token_str,
            expires_at="2030-01-01T00:00:00Z",
        )

    data = await client.execute_storefront(
        query=CUSTOMER_ACCESS_TOKEN_CREATE_MUTATION,
        variables={"input": {"email": email_clean, "password": password}},
    )
    ShopifyClient.validate_user_errors(data, "customerAccessTokenCreate", user_error_field="customerUserErrors")

    token_dict = data.get("customerAccessTokenCreate", {}).get("customerAccessToken")
    if not token_dict or not token_dict.get("accessToken"):
        raise ShopifyAuthError("Authentication failed: Invalid credentials or unconfirmed customer account.")

    return CustomerAccessToken(
        access_token=token_dict["accessToken"],
        expires_at=token_dict.get("expiresAt", ""),
    )


async def renew_customer_access_token(
    client: ShopifyClient,
    customer_access_token: str,
) -> CustomerAccessToken:
    """
    Renews an expiring customer access token.
    """
    token_clean = customer_access_token.strip()
    if client.is_dev_token(token_clean):
        return CustomerAccessToken(
            access_token=token_clean,
            expires_at="2030-01-01T00:00:00Z",
        )

    data = await client.execute_storefront(
        query=CUSTOMER_ACCESS_TOKEN_RENEW_MUTATION,
        variables={"customerAccessToken": token_clean},
    )
    ShopifyClient.validate_user_errors(data, "customerAccessTokenRenew")

    token_dict = data.get("customerAccessTokenRenew", {}).get("customerAccessToken")
    if not token_dict or not token_dict.get("accessToken"):
        raise ShopifyAuthError("Token renewal failed: Token may already be expired or invalid.")

    return CustomerAccessToken(
        access_token=token_dict["accessToken"],
        expires_at=token_dict.get("expiresAt", ""),
    )


async def delete_customer_access_token(
    client: ShopifyClient,
    customer_access_token: str,
) -> bool:
    """
    Invalidates a customer access token (logs out the user).
    """
    token_clean = customer_access_token.strip()
    if client.is_dev_token(token_clean):
        return True

    data = await client.execute_storefront(
        query=CUSTOMER_ACCESS_TOKEN_DELETE_MUTATION,
        variables={"customerAccessToken": token_clean},
    )
    ShopifyClient.validate_user_errors(data, "customerAccessTokenDelete")

    deleted_token = data.get("customerAccessTokenDelete", {}).get("deletedAccessToken")
    return bool(deleted_token)


async def get_customer_gated_profile(
    client: ShopifyClient,
    customer_access_token: str,
) -> Optional[CustomerGatedProfile]:
    """
    Queries customer profile, tags, and recent orders to evaluate access gate.
    """
    token_clean = customer_access_token.strip()

    # Dev token bypass
    if client.is_dev_token(token_clean):
        return get_dev_fallback_profile(token=token_clean)

    data = await client.execute_storefront(
        query=GET_CUSTOMER_GATED_PROFILE_QUERY,
        variables={"customerAccessToken": token_clean},
    )
    customer_dict = data.get("customer")
    if not customer_dict:
        return None

    tags = customer_dict.get("tags") or []
    tier, is_paid = extract_tier_from_tags(tags)

    raw_orders = customer_dict.get("orders", {}).get("edges", [])
    orders_list: List[Dict[str, Any]] = [edge.get("node", {}) for edge in raw_orders]

    return CustomerGatedProfile(
        id=customer_dict.get("id", ""),
        email=customer_dict.get("email", ""),
        first_name=customer_dict.get("firstName"),
        last_name=customer_dict.get("lastName"),
        phone=customer_dict.get("phone"),
        tags=tags,
        tier=tier,
        is_paid_subscriber=is_paid,
        orders=orders_list,
    )


async def get_customer_account_subscriptions(
    client: ShopifyClient,
    customer_access_token: str,
) -> List[Dict[str, Any]]:
    """
    Queries customer-owned subscription contracts directly via the Customer Account API.
    """
    token_clean = customer_access_token.strip()
    if client.is_dev_token(token_clean):
        return [
            {
                "id": "gid://shopify/SubscriptionContract/999111",
                "status": "ACTIVE",
                "lines": [{"name": "OpenClaw AI Pro Monthly", "quantity": 1}],
            }
        ]

    data = await client.execute_customer_account(
        query=GET_CUSTOMER_ACCOUNT_SUBSCRIPTION_QUERY,
        customer_token=token_clean,
    )
    customer_dict = data.get("customer", {})
    contracts = []
    edges = customer_dict.get("subscriptionContracts", {}).get("edges", [])
    for edge in edges:
        node = edge.get("node", {})
        contracts.append(node)
    return contracts
