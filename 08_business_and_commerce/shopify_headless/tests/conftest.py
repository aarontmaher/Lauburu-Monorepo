"""
Pytest fixtures and mock transport utilities for Shopify Headless Monetization tests.
"""

import json
from typing import Any, Callable, Dict, List, Optional
import httpx
import pytest

from shopify_headless.config import ShopifyConfig
from shopify_headless.client import ShopifyClient


class MockGraphQLTransport(httpx.AsyncBaseTransport):
    """
    Flexible mock async transport for intercepting GraphQL HTTP POST requests.
    Supports response queues, status code simulation, and request inspection.
    """

    def __init__(self, responses: Optional[List[httpx.Response]] = None, handler: Optional[Callable] = None):
        self.responses = responses or []
        self.handler = handler
        self.requests: List[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.handler:
            return self.handler(request)
        if self.responses:
            return self.responses.pop(0)
        # Default empty successful response
        return httpx.Response(200, json={"data": {}})


@pytest.fixture
def mock_config() -> ShopifyConfig:
    return ShopifyConfig(
        store_domain="lauburugrappling.myshopify.com",
        storefront_access_token="shpat_test_storefront_mock_token",
        admin_access_token="shpat_test_admin_mock_token",
        api_version="2026-01",
        timeout_seconds=5.0,
        max_retries=2,
        backoff_factor=0.01,  # Fast backoff for tests
    )


@pytest.fixture
def mock_product_with_selling_plans_payload() -> Dict[str, Any]:
    return {
        "product": {
            "id": "gid://shopify/Product/1001",
            "title": "OpenClaw AI Pro Compute Subscription",
            "description": "Unlimited local mesh routing, 70B MoE sharding, and 24/7 LoRA distillation.",
            "requiresSellingPlan": True,
            "sellingPlanGroups": {
                "edges": [
                    {
                        "node": {
                            "name": "OpenClaw Subscription Plans",
                            "appName": "Shopify Subscriptions",
                            "options": [{"name": "Frequency", "values": ["Monthly", "Annual"]}],
                            "sellingPlans": {
                                "edges": [
                                    {
                                        "node": {
                                            "id": "gid://shopify/SellingPlan/5001",
                                            "name": "Monthly Pro AI Access",
                                            "description": "Billed monthly at $29/mo",
                                            "recurringDeliveries": True,
                                            "options": [{"name": "Frequency", "value": "1 Month"}],
                                            "priceAdjustments": [
                                                {
                                                    "orderCount": None,
                                                    "adjustmentValue": {
                                                        "adjustmentPercentage": 10.0,
                                                        "adjustmentAmount": None,
                                                        "price": None,
                                                    },
                                                }
                                            ],
                                        }
                                    },
                                    {
                                        "node": {
                                            "id": "gid://shopify/SellingPlan/5002",
                                            "name": "Annual Pro AI Access",
                                            "description": "Billed annually with $0 Hardware Commitment",
                                            "recurringDeliveries": True,
                                            "options": [{"name": "Frequency", "value": "1 Year"}],
                                            "priceAdjustments": [
                                                {
                                                    "orderCount": None,
                                                    "adjustmentValue": {
                                                        "adjustmentPercentage": 25.0,
                                                        "adjustmentAmount": None,
                                                        "price": None,
                                                    },
                                                }
                                            ],
                                        }
                                    },
                                ]
                            },
                        }
                    }
                ]
            },
            "variants": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/ProductVariant/2001",
                            "title": "Pro Tier - Standard",
                            "sku": "OPENCLAW-PRO-SUB",
                            "price": {"amount": "29.00", "currencyCode": "USD"},
                        }
                    }
                ]
            },
        }
    }


@pytest.fixture
def mock_cart_payload() -> Dict[str, Any]:
    return {
        "id": "gid://shopify/Cart/c1-987654321?key=abc123secret",
        "checkoutUrl": "https://lauburugrappling.myshopify.com/cart/c/c1-987654321",
        "totalQuantity": 2,
        "lines": {
            "edges": [
                {
                    "node": {
                        "id": "gid://shopify/CartLine/l1",
                        "quantity": 1,
                        "attributes": [{"key": "node_role", "value": "Layer_3_Gateway"}],
                        "merchandise": {
                            "id": "gid://shopify/ProductVariant/3001",
                            "title": "GL.iNet MT3600BE Router Node",
                            "sku": "GLINET-MT3600BE",
                            "price": {"amount": "149.00", "currencyCode": "USD"},
                            "product": {
                                "title": "Lauburu Mesh Gateway Node",
                                "handle": "lauburu-mesh-gateway",
                            },
                        },
                        "cost": {"totalAmount": {"amount": "149.00", "currencyCode": "USD"}},
                    }
                },
                {
                    "node": {
                        "id": "gid://shopify/CartLine/l2",
                        "quantity": 1,
                        "attributes": [{"key": "sensor_type", "value": "512Hz_ECG"}],
                        "merchandise": {
                            "id": "gid://shopify/ProductVariant/3002",
                            "title": "Movesense Medical ECG Sensor",
                            "sku": "MOVESENSE-ECG-MD",
                            "price": {"amount": "199.00", "currencyCode": "USD"},
                            "product": {
                                "title": "Movesense Biometric Sensor",
                                "handle": "movesense-biometrics",
                            },
                        },
                        "cost": {"totalAmount": {"amount": "199.00", "currencyCode": "USD"}},
                    }
                },
            ]
        },
        "cost": {
            "subtotalAmount": {"amount": "348.00", "currencyCode": "USD"},
            "totalAmount": {"amount": "348.00", "currencyCode": "USD"},
            "checkoutChargeAmount": {"amount": "348.00", "currencyCode": "USD"},
        },
        "buyerIdentity": {
            "email": "athlete@lauburu.ai",
            "phone": "+61400111222",
            "countryCode": "AU",
        },
        "discountCodes": [{"code": "HARDWARE_PROMO_2026", "applicable": True}],
    }


@pytest.fixture
def mock_admin_subscription_contracts_payload() -> Dict[str, Any]:
    return {
        "subscriptionContracts": {
            "edges": [
                {
                    "node": {
                        "id": "gid://shopify/SubscriptionContract/8801",
                        "status": "ACTIVE",
                        "createdAt": "2026-01-15T10:00:00Z",
                        "nextBillingDate": "2026-09-15T10:00:00Z",
                        "customer": {
                            "id": "gid://shopify/Customer/9901",
                            "firstName": "Aaron",
                            "lastName": "Maher",
                            "defaultEmailAddress": {"emailAddress": "aaron@lauburu.ai"},
                        },
                        "lines": {
                            "edges": [
                                {
                                    "node": {
                                        "id": "gid://shopify/SubscriptionLine/7701",
                                        "title": "OpenClaw AI Pro Compute",
                                        "quantity": 1,
                                        "currentPrice": {"amount": "29.00", "currencyCode": "USD"},
                                        "sellingPlanId": "gid://shopify/SellingPlan/5001",
                                        "sellingPlanName": "Monthly Pro AI Access",
                                    }
                                }
                            ]
                        },
                    }
                }
            ]
        }
    }


@pytest.fixture
def mock_customer_gated_profile_payload() -> Dict[str, Any]:
    return {
        "customer": {
            "id": "gid://shopify/Customer/9901",
            "email": "aaron@lauburu.ai",
            "firstName": "Aaron",
            "lastName": "Maher",
            "phone": "+61400123456",
            "tags": ["tier_pro", "movesense_pro", "spatial_grappling_pro"],
            "orders": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Order/6601",
                            "name": "#1001",
                            "orderNumber": 1001,
                            "processedAt": "2026-08-01T12:00:00Z",
                            "financialStatus": "PAID",
                            "fulfillmentStatus": "FULFILLED",
                            "lineItems": {
                                "edges": [
                                    {
                                        "node": {
                                            "title": "OpenClaw AI Pro Annual Access",
                                            "quantity": 1,
                                            "variant": {
                                                "id": "gid://shopify/ProductVariant/2001",
                                                "title": "Annual Plan",
                                                "sku": "SUB-PRO-ANNUAL",
                                                "product": {
                                                    "id": "gid://shopify/Product/1001",
                                                    "title": "OpenClaw AI Pro Compute",
                                                    "handle": "openclaw-ai-pro",
                                                },
                                            },
                                        }
                                    }
                                ]
                            },
                        }
                    }
                ]
            },
        }
    }
