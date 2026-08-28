"""
Async GraphQL client for Shopify Storefront, Admin, and Customer Account APIs.
Features:
  - Leaky-bucket rate limit tracking via extensions.cost.throttleStatus
  - Exponential backoff with jitter on HTTP 429 and GraphQL THROTTLED errors
  - Detailed error mapping into Shopify exception taxonomy
  - Dev token offline recognition for local testing
"""

import asyncio
import logging
import random
import time
from typing import Any, Dict, List, Optional
import httpx

from .config import ShopifyConfig, get_shopify_config
from .errors import (
    ShopifyAuthError,
    ShopifyGraphQLError,
    ShopifyRateLimitError,
    ShopifyUserError,
)

logger = logging.getLogger("shopify_headless.client")


class ShopifyClient:
    """
    High-performance, resilient async client for executing Shopify GraphQL operations.
    """

    def __init__(
        self,
        config: Optional[ShopifyConfig] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self.config = config or get_shopify_config()
        self.transport = transport
        # Leaky bucket state (cost points)
        self._available_cost: float = 1000.0
        self._max_cost: float = 1000.0
        self._restore_rate: float = 50.0  # cost points restored per second
        self._last_cost_update: float = time.time()
        self._cost_lock = asyncio.Lock()

    def is_dev_token(self, token: Optional[str]) -> bool:
        """Check if a token is a local development/testing bypass token."""
        if not token:
            return False
        t = token.strip()
        return (
            t.startswith("tok_dev_")
            or t.startswith("shpat_dev_")
            or "dev_aaron" in t
            or "test_token" in t
        )

    def _get_storefront_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.config.storefront_private_token:
            headers["Shopify-Storefront-Private-Token"] = self.config.storefront_private_token
        elif self.config.storefront_access_token:
            headers["X-Shopify-Storefront-Access-Token"] = self.config.storefront_access_token
        return headers

    def _get_admin_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.config.admin_access_token:
            headers["X-Shopify-Access-Token"] = self.config.admin_access_token
        return headers

    def _get_customer_account_headers(self, customer_token: str) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {customer_token.strip()}",
        }

    async def _update_and_throttle_cost(self, estimated_cost: float = 10.0) -> None:
        """Enforce client-side leaky bucket throttling prior to sending request."""
        async with self._cost_lock:
            now = time.time()
            elapsed = now - self._last_cost_update
            self._last_cost_update = now
            # Restore leaked points
            self._available_cost = min(
                self._max_cost,
                self._available_cost + (elapsed * self._restore_rate)
            )

            if self._available_cost < estimated_cost:
                deficit = estimated_cost - self._available_cost
                wait_time = deficit / max(1.0, self._restore_rate)
                logger.info(
                    "Client-side leaky bucket throttle: waiting %.2fs for %d cost headroom",
                    wait_time,
                    estimated_cost,
                )
                await asyncio.sleep(wait_time)
                self._available_cost = 0.0
                self._last_cost_update = time.time()
            else:
                self._available_cost -= estimated_cost

    def _process_cost_extensions(self, extensions: Dict[str, Any]) -> None:
        """Update available cost based on Shopify response extensions."""
        cost_info = extensions.get("cost", {})
        throttle_status = cost_info.get("throttleStatus")
        if throttle_status:
            try:
                self._available_cost = float(throttle_status.get("currentlyAvailable", 1000.0))
                self._max_cost = float(throttle_status.get("maximumAvailable", 1000.0))
                self._restore_rate = float(throttle_status.get("restoreRate", 50.0))
                self._last_cost_update = time.time()
            except (ValueError, TypeError):
                pass

    async def execute_storefront(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a GraphQL query/mutation against the Storefront API."""
        headers = self._get_storefront_headers()
        return await self._execute_http(
            endpoint=self.config.storefront_endpoint,
            query=query,
            variables=variables,
            headers=headers,
        )

    async def execute_admin(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a GraphQL query/mutation against the Admin API."""
        if not self.config.admin_access_token and not self.is_dev_token("dev"):
            logger.warning("Admin access token not set; request may fail unless using mock transport.")
        headers = self._get_admin_headers()
        return await self._execute_http(
            endpoint=self.config.admin_endpoint,
            query=query,
            variables=variables,
            headers=headers,
            is_admin=True,
        )

    async def execute_customer_account(
        self,
        query: str,
        customer_token: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a GraphQL query against the Customer Account API."""
        headers = self._get_customer_account_headers(customer_token)
        return await self._execute_http(
            endpoint=self.config.customer_account_endpoint,
            query=query,
            variables=variables,
            headers=headers,
        )

    async def _execute_http(
        self,
        endpoint: str,
        query: str,
        variables: Optional[Dict[str, Any]],
        headers: Dict[str, str],
        is_admin: bool = False,
    ) -> Dict[str, Any]:
        """Core HTTP dispatch loop with retry backoff and rate limit tracking."""
        payload = {"query": query, "variables": variables or {}}
        retries = 0

        while retries <= self.config.max_retries:
            # If Admin API, enforce client-side bucket throttle
            if is_admin:
                await self._update_and_throttle_cost(estimated_cost=10.0)

            try:
                client_kwargs: Dict[str, Any] = {
                    "timeout": self.config.timeout_seconds,
                }
                if self.transport is not None:
                    client_kwargs["transport"] = self.transport

                async with httpx.AsyncClient(**client_kwargs) as client:
                    response = await client.post(endpoint, json=payload, headers=headers)

                    # 1. Handle HTTP 429 Too Many Requests
                    if response.status_code == 429:
                        retry_after_str = response.headers.get("Retry-After", "2.0")
                        try:
                            retry_after = float(retry_after_str)
                        except ValueError:
                            retry_after = 2.0
                        logger.warning(
                            "Shopify HTTP 429 (Throttled). Retrying after %.2fs (attempt %d/%d)",
                            retry_after,
                            retries + 1,
                            self.config.max_retries,
                        )
                        retries += 1
                        if retries > self.config.max_retries:
                            raise ShopifyRateLimitError(
                                "Shopify rate limit exceeded; max retries reached.",
                                retry_after=retry_after,
                                status_code=429,
                            )
                        await asyncio.sleep(retry_after)
                        continue

                    # 2. Handle HTTP 401/403 Authentication Errors
                    if response.status_code in (401, 403):
                        raise ShopifyAuthError(
                            f"Shopify Authentication Error (HTTP {response.status_code}): {response.text}",
                            code=str(response.status_code),
                        )

                    # 3. Handle Other Non-200 HTTP Errors
                    if response.status_code != 200:
                        raise ShopifyGraphQLError(
                            f"HTTP {response.status_code} Error: {response.text}",
                            status_code=response.status_code,
                        )

                    body = response.json()

                    # 4. Handle top-level GraphQL errors
                    if "errors" in body and body["errors"]:
                        errors_list = body["errors"]
                        first_err = errors_list[0]
                        err_code = str(first_err.get("extensions", {}).get("code", ""))

                        if "THROTTLED" in err_code:
                            jitter = random.uniform(0.1, 0.5)
                            backoff = (self.config.backoff_factor ** retries) + jitter
                            logger.warning(
                                "GraphQL THROTTLED error. Backing off for %.2fs (attempt %d/%d)",
                                backoff,
                                retries + 1,
                                self.config.max_retries,
                            )
                            retries += 1
                            if retries > self.config.max_retries:
                                raise ShopifyRateLimitError(
                                    "Shopify GraphQL query throttled; max retries reached.",
                                    retry_after=backoff,
                                    errors=errors_list,
                                )
                            await asyncio.sleep(backoff)
                            continue

                        raise ShopifyGraphQLError(
                            message=first_err.get("message", "GraphQL Execution Error"),
                            errors=errors_list,
                            extensions=first_err.get("extensions", {}),
                        )

                    # 5. Extract and update cost metrics if present
                    extensions = body.get("extensions", {})
                    if extensions:
                        self._process_cost_extensions(extensions)

                    return body.get("data", {})

            except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
                retries += 1
                if retries > self.config.max_retries:
                    raise ShopifyGraphQLError(
                        f"Network failure after {self.config.max_retries} retries: {str(exc)}"
                    ) from exc
                jitter = random.uniform(0.1, 0.4)
                backoff = (self.config.backoff_factor ** retries) + jitter
                logger.warning(
                    "Network error (%s). Retrying in %.2fs (attempt %d/%d)...",
                    exc.__class__.__name__,
                    backoff,
                    retries,
                    self.config.max_retries,
                )
                await asyncio.sleep(backoff)

        raise ShopifyGraphQLError(
            f"Exceeded max retries ({self.config.max_retries}) for Shopify GraphQL operation."
        )

    @staticmethod
    def validate_user_errors(
        result_payload: Dict[str, Any],
        operation_key: str,
        user_error_field: str = "userErrors",
    ) -> None:
        """
        Inspects mutation result payload for domain-level userErrors / customerUserErrors.
        Raises ShopifyUserError if errors are present.
        """
        operation_data = result_payload.get(operation_key)
        if not operation_data or not isinstance(operation_data, dict):
            return

        errs: List[Dict[str, Any]] = (
            operation_data.get(user_error_field)
            or operation_data.get("customerUserErrors")
            or []
        )
        if errs:
            first = errs[0]
            msg = first.get("message", "Shopify operation user error")
            field = ".".join(first.get("field", [])) if isinstance(first.get("field"), list) else str(first.get("field"))
            code = first.get("code")
            raise ShopifyUserError(
                message=msg,
                user_errors=errs,
                field=field,
                code=code,
            )
