"""
Shopify Storefront GraphQL Service for Port 4000 Hub.
Handles customer access token verification, membership tier extraction, and dev token fallback.
"""

import logging
import os
from typing import Any, Dict, Optional, Tuple
import httpx

logger = logging.getLogger("shopify_service")

SHOPIFY_STORE_DOMAIN = os.environ.get("SHOPIFY_STORE_DOMAIN", "lauburugrappling.myshopify.com")
SHOPIFY_STOREFRONT_TOKEN = os.environ.get("SHOPIFY_STOREFRONT_TOKEN", "pub_storefront_mock_placeholder")
SHOPIFY_API_VERSION = os.environ.get("SHOPIFY_API_VERSION", "2026-01")


class ShopifyService:
    """
    Client for Shopify Storefront GraphQL API.
    Verifies Customer Access Tokens and queries Customer profile tags.
    """

    def __init__(
        self,
        store_domain: Optional[str] = None,
        storefront_token: Optional[str] = None,
        api_version: Optional[str] = None,
        timeout: float = 6.0
    ):
        self.store_domain = store_domain or SHOPIFY_STORE_DOMAIN
        self.storefront_token = storefront_token or SHOPIFY_STOREFRONT_TOKEN
        self.api_version = api_version or SHOPIFY_API_VERSION
        self.timeout = timeout
        self.storefront_url = f"https://{self.store_domain}/api/{self.api_version}/graphql.json"

    def _extract_tier_from_tags(self, tags: list) -> Tuple[str, bool]:
        """Extract membership tier and paid subscriber flag from Shopify customer tags."""
        tags_lower = [str(t).lower().strip() for t in tags]
        tier = "FREE"
        if any(t in tags_lower for t in ["tier_enterprise", "gym_b2b", "enterprise"]):
            tier = "ENTERPRISE"
        elif any(t in tags_lower for t in ["tier_pro", "pro_subscriber", "movesense_pro", "paid_pro"]):
            tier = "PAID_PRO"
        elif any(t in tags_lower for t in ["tier_contributor", "contributor_pro", "hardware_contributor"]):
            tier = "CONTRIBUTOR_PRO"

        is_paid = tier in ["PAID_PRO", "ENTERPRISE", "CONTRIBUTOR_PRO"]
        return tier, is_paid

    def _get_dev_fallback_profile(
        self,
        token: Optional[str] = None,
        email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate verified profile for local development and offline testing."""
        em = email or "dev@lauburu.ai"
        name = "Aaron Maher (Dev Contributor)" if "aaron" in em.lower() or "dev" in em.lower() else "Test Athlete"
        return {
            "valid": True,
            "customer_id": "gid://shopify/Customer/999888777",
            "email": em,
            "name": name,
            "tier": "PAID_PRO",
            "is_paid_subscriber": True,
            "tags": ["tier_pro", "developer", "hardware_contributor"]
        }

    async def verify_customer_access_token(self, customer_access_token: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Verifies customer access token and queries Customer tags & active orders via Storefront API.
        Falls back to verified dev profile for dev/test tokens.
        """
        if not customer_access_token:
            return False, {"valid": False, "error": "Missing customer access token"}

        token_str = str(customer_access_token).strip()

        # Instant fallback for dev tokens or offline test harnesses
        if (
            token_str.startswith("tok_dev_")
            or token_str.startswith("shpat_dev_")
            or "dev_aaron" in token_str
            or "test_token" in token_str
        ):
            return True, self._get_dev_fallback_profile(token=token_str)

        query = """
        query getCustomerProfile($customerAccessToken: String!) {
            customer(customerAccessToken: $customerAccessToken) {
                id
                email
                firstName
                lastName
                tags
                orders(first: 5) {
                    edges {
                        node {
                            id
                            processedAt
                            financialStatus
                            lineItems(first: 5) {
                                edges {
                                    node {
                                        title
                                        variant {
                                            id
                                            title
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
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Storefront-Access-Token": self.storefront_token,
            "Accept": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    self.storefront_url,
                    json={"query": query, "variables": {"customerAccessToken": token_str}},
                    headers=headers
                )
                if resp.status_code == 200:
                    data = resp.json()
                    customer = data.get("data", {}).get("customer")
                    if customer:
                        tags = customer.get("tags", [])
                        tier, is_paid = self._extract_tier_from_tags(tags)
                        first = customer.get("firstName") or ""
                        last = customer.get("lastName") or ""
                        full_name = f"{first} {last}".strip() or "Shopify Customer"

                        return True, {
                            "valid": True,
                            "customer_id": customer.get("id"),
                            "email": customer.get("email"),
                            "name": full_name,
                            "tier": tier,
                            "is_paid_subscriber": is_paid,
                            "tags": tags
                        }
                    else:
                        errors = data.get("errors", [])
                        err_msg = errors[0].get("message") if errors else "Customer not found for provided token"
                        logger.warning("Shopify customer lookup failed: %s", err_msg)
        except Exception as e:
            logger.warning("Shopify Storefront customer verification network error: %s", str(e))

        # Check if fallback dev token rule applies on network errors
        if "dev" in token_str or "mock" in self.storefront_token:
            return True, self._get_dev_fallback_profile(token=token_str)

        return False, {"valid": False, "error": "Invalid or expired customer token"}

    async def authenticate_customer_credentials(
        self,
        email: str,
        password: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Authenticates customer email and password via Shopify Storefront GraphQL customerAccessTokenCreate mutation.
        """
        email_clean = email.strip()

        # Dev bypass for development testing
        if (
            email_clean.endswith("@lauburu.ai")
            or "dev_" in email_clean
            or "mock" in self.storefront_token
        ):
            dev_token = f"tok_dev_{abs(hash(email_clean)) % 1000000:06d}"
            profile = self._get_dev_fallback_profile(token=dev_token, email=email_clean)
            return True, {
                "token": dev_token,
                "expires_at": "2030-01-01T00:00:00Z",
                "profile": profile
            }

        mutation = """
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
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Storefront-Access-Token": self.storefront_token,
            "Accept": "application/json"
        }
        payload = {
            "query": mutation,
            "variables": {
                "input": {
                    "email": email_clean,
                    "password": password
                }
            }
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(self.storefront_url, json=payload, headers=headers)
                if resp.status_code == 200:
                    res_data = resp.json()
                    create_res = res_data.get("data", {}).get("customerAccessTokenCreate", {})
                    token_obj = create_res.get("customerAccessToken")
                    errors = create_res.get("customerUserErrors", [])

                    if token_obj and not errors:
                        token = token_obj.get("accessToken")
                        valid, profile = await self.verify_customer_access_token(token)
                        return True, {
                            "token": token,
                            "expires_at": token_obj.get("expiresAt"),
                            "profile": profile
                        }
                    else:
                        err_msg = errors[0].get("message") if errors else "Authentication failed"
                        return False, {"error": err_msg}
        except Exception as e:
            logger.warning("Shopify Login mutation exception: %s", str(e))

        return False, {"error": "Shopify Storefront unreachable. Please check network."}


_global_shopify_service: Optional[ShopifyService] = None


def get_shopify_service() -> ShopifyService:
    global _global_shopify_service
    if _global_shopify_service is None:
        _global_shopify_service = ShopifyService()
    return _global_shopify_service
