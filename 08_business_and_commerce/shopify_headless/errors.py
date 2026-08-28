"""
Exception taxonomy for the Shopify Headless Monetization Engine.
"""

from typing import Any, Dict, List, Optional


class ShopifyError(Exception):
    """Base exception for all Shopify headless commerce operations."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ShopifyConfigError(ShopifyError):
    """Raised when Shopify configuration is missing, invalid, or misconfigured."""
    pass


class ShopifyGraphQLError(ShopifyError):
    """Raised when a Shopify GraphQL request returns top-level errors or an HTTP error status."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        errors: Optional[List[Dict[str, Any]]] = None,
        extensions: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.errors = errors or []
        self.extensions = extensions or {}


class ShopifyRateLimitError(ShopifyGraphQLError):
    """Raised when Shopify API throttling occurs (HTTP 429 or GraphQL THROTTLED)."""

    def __init__(
        self,
        message: str,
        retry_after: float = 2.0,
        available_cost: Optional[float] = None,
        restore_rate: Optional[float] = None,
        status_code: Optional[int] = 429,
        errors: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(message, status_code=status_code, errors=errors)
        self.retry_after = retry_after
        self.available_cost = available_cost
        self.restore_rate = restore_rate


class ShopifyAuthError(ShopifyError):
    """Raised when authentication fails (invalid credentials, expired token, unauthorized scope)."""

    def __init__(self, message: str, code: Optional[str] = None):
        super().__init__(message)
        self.code = code


class ShopifyUserError(ShopifyError):
    """Raised when mutation returns domain-level userErrors or customerUserErrors."""

    def __init__(
        self,
        message: str,
        user_errors: Optional[List[Dict[str, Any]]] = None,
        field: Optional[str] = None,
        code: Optional[str] = None,
    ):
        super().__init__(message)
        self.user_errors = user_errors or []
        self.field = field
        self.code = code
